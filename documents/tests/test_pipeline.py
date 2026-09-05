import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from core.models import Organization, User
from documents.models import Document
from documents.processing.pipeline import process_document

TEMP_MEDIA_ROOT = tempfile.mkdtemp()

TEST_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT, STORAGES=TEST_STORAGES)
@patch('documents.processing.pipeline.analyze_document')
@patch('documents.processing.pipeline.upsert_chunks')
@patch('documents.processing.pipeline.delete_document_vectors')
class ProcessDocumentPipelineTests(TestCase):
    """Extraction/chunking correctness. Embedding + Qdrant upsert, and
    document analysis (classification/entities), are mocked here (see
    documents/tests/test_vector_store.py and test_intelligence.py for
    those layers) so this suite stays fast and doesn't need the BGE-M3
    model loaded or a real AI Gateway call."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.org = Organization.objects.create(name='Acme', slug='acme')
        self.user = User.objects.create_user(email='u@acme.com', password='pw12345', organization=self.org)

    def _make_document(self, filename, content: bytes, file_type):
        return Document.objects.create(
            organization=self.org,
            uploaded_by=self.user,
            file=SimpleUploadedFile(filename, content),
            original_filename=filename,
            file_type=file_type,
            file_size=len(content),
        )

    def test_txt_document_is_processed_to_ready_with_chunks(self, mock_delete_vectors, mock_upsert_chunks, mock_analyze):
        content = (
            'Chapter 1: Introduction\n\n'
            'This agreement sets out the terms between the parties involved in the transaction.\n\n'
            'Article 1\n\n'
            'Each party shall act in good faith and comply with applicable law at all times.'
        ).encode('utf-8')
        document = self._make_document('contract.txt', content, Document.FileType.TXT)

        process_document(str(document.id))
        document.refresh_from_db()

        self.assertEqual(document.status, Document.Status.READY)
        self.assertEqual(document.error_message, '')
        self.assertEqual(document.page_count, 1)

        chunks = list(document.chunks.order_by('index'))
        self.assertGreater(len(chunks), 0)
        self.assertTrue(any(c.hierarchy_path.startswith('Chapter 1') for c in chunks))
        self.assertEqual([c.index for c in chunks], list(range(len(chunks))))

    def test_ready_document_is_embedded_and_indexed(self, mock_delete_vectors, mock_upsert_chunks, mock_analyze):
        document = self._make_document('contract.txt', b'A single paragraph of contract text.', Document.FileType.TXT)

        process_document(str(document.id))

        mock_delete_vectors.assert_called_once_with(document.id)
        mock_upsert_chunks.assert_called_once()
        (called_document, called_chunks), _ = mock_upsert_chunks.call_args
        self.assertEqual(called_document.id, document.id)
        self.assertEqual([c.id for c in called_chunks], list(document.chunks.values_list('id', flat=True)))

    def test_ready_document_is_analyzed(self, mock_delete_vectors, mock_upsert_chunks, mock_analyze):
        document = self._make_document('contract.txt', b'A single paragraph of contract text.', Document.FileType.TXT)

        process_document(str(document.id))

        mock_analyze.assert_called_once()
        (called_document,), _ = mock_analyze.call_args
        self.assertEqual(called_document.id, document.id)

    def test_analysis_failure_does_not_fail_the_document(self, mock_delete_vectors, mock_upsert_chunks, mock_analyze):
        mock_analyze.side_effect = RuntimeError('LLM analysis blew up')
        document = self._make_document('contract.txt', b'A single paragraph of contract text.', Document.FileType.TXT)

        process_document(str(document.id))
        document.refresh_from_db()

        self.assertEqual(document.status, Document.Status.READY)

    def test_embedding_failure_marks_document_failed(self, mock_delete_vectors, mock_upsert_chunks, mock_analyze):
        mock_upsert_chunks.side_effect = RuntimeError('Qdrant unreachable')
        document = self._make_document('contract.txt', b'A single paragraph of contract text.', Document.FileType.TXT)

        process_document(str(document.id))
        document.refresh_from_db()

        self.assertEqual(document.status, Document.Status.FAILED)
        self.assertIn('Qdrant unreachable', document.error_message)

    def test_empty_txt_document_marks_document_failed(self, mock_delete_vectors, mock_upsert_chunks, mock_analyze):
        document = self._make_document('empty.txt', b'   \n\n  ', Document.FileType.TXT)

        process_document(str(document.id))
        document.refresh_from_db()

        self.assertEqual(document.status, Document.Status.FAILED)
        self.assertNotEqual(document.error_message, '')
        self.assertEqual(document.chunks.count(), 0)
        mock_upsert_chunks.assert_not_called()

    def test_reprocessing_replaces_old_chunks(self, mock_delete_vectors, mock_upsert_chunks, mock_analyze):
        document = self._make_document('doc.txt', b'First version of the paragraph text here.', Document.FileType.TXT)
        process_document(str(document.id))
        first_chunk_ids = set(document.chunks.values_list('id', flat=True))
        self.assertTrue(first_chunk_ids)

        with document.file.open('wb') as f:
            f.write(b'Completely different second version of the paragraph text.')
        document.save()

        process_document(str(document.id))
        second_chunk_ids = set(document.chunks.values_list('id', flat=True))

        self.assertTrue(second_chunk_ids)
        self.assertEqual(first_chunk_ids & second_chunk_ids, set())
        self.assertEqual(mock_delete_vectors.call_count, 2)

    @patch('documents.processing.extractors.run_ocr')
    def test_image_document_uses_ocr_and_reaches_ready(self, mock_run_ocr, mock_delete_vectors, mock_upsert_chunks, mock_analyze):
        mock_run_ocr.return_value = ['Chapter 1', 'Recognized text from a scanned page.']

        from PIL import Image
        from io import BytesIO

        buf = BytesIO()
        Image.new('RGB', (100, 100), color='white').save(buf, format='PNG')
        document = self._make_document('scan.png', buf.getvalue(), Document.FileType.IMAGE)

        process_document(str(document.id))
        document.refresh_from_db()

        self.assertEqual(document.status, Document.Status.READY)
        self.assertTrue(mock_run_ocr.called)
        self.assertGreater(document.chunks.count(), 0)

    def test_missing_document_id_is_a_no_op(self, mock_delete_vectors, mock_upsert_chunks, mock_analyze):
        # Should not raise.
        process_document('00000000-0000-0000-0000-000000000000')
        mock_upsert_chunks.assert_not_called()
