import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from ai_gateway import AIGatewayError
from core.models import Organization, User
from documents.models import Chunk, Document
from documents.processing.intelligence import analyze_document

TEMP_MEDIA_ROOT = tempfile.mkdtemp()

TEST_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT, STORAGES=TEST_STORAGES)
class AnalyzeDocumentTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.org = Organization.objects.create(name='Acme', slug='acme')
        self.user = User.objects.create_user(email='u@acme.com', password='pw12345', organization=self.org)
        self.document = Document.objects.create(
            organization=self.org,
            uploaded_by=self.user,
            file=SimpleUploadedFile('lease.txt', b'content'),
            original_filename='lease.txt',
            file_type=Document.FileType.TXT,
            file_size=7,
            status=Document.Status.READY,
        )
        Chunk.objects.create(
            document=self.document, index=0, page_number=1,
            text='This lease between Acme Corp and Jane Doe is effective January 1, 2026, for $5,000 per month.',
        )

    @patch('documents.processing.intelligence.ai_chat')
    def test_valid_response_sets_category_and_entities(self, mock_ai_chat):
        mock_ai_chat.return_value = (
            '{"category": "CONTRACT", "dates": ["January 1, 2026"], '
            '"amounts": ["$5,000"], "parties": ["Acme Corp", "Jane Doe"]}'
        )

        analyze_document(self.document)
        self.document.refresh_from_db()

        self.assertEqual(self.document.category, Document.Category.CONTRACT)
        self.assertEqual(self.document.entities['dates'], ['January 1, 2026'])
        self.assertEqual(self.document.entities['amounts'], ['$5,000'])
        self.assertEqual(self.document.entities['parties'], ['Acme Corp', 'Jane Doe'])

    @patch('documents.processing.intelligence.ai_chat')
    def test_markdown_fenced_json_still_parses(self, mock_ai_chat):
        mock_ai_chat.return_value = (
            '```json\n{"category": "REPORT", "dates": [], "amounts": [], "parties": []}\n```'
        )

        analyze_document(self.document)
        self.document.refresh_from_db()

        self.assertEqual(self.document.category, Document.Category.REPORT)

    @patch('documents.processing.intelligence.ai_chat')
    def test_invalid_category_falls_back_to_other(self, mock_ai_chat):
        mock_ai_chat.return_value = '{"category": "NOT_A_REAL_CATEGORY", "dates": [], "amounts": [], "parties": []}'

        analyze_document(self.document)
        self.document.refresh_from_db()

        self.assertEqual(self.document.category, Document.Category.OTHER)

    @patch('documents.processing.intelligence.ai_chat')
    def test_unparseable_response_leaves_document_unchanged(self, mock_ai_chat):
        mock_ai_chat.return_value = 'not json at all'

        analyze_document(self.document)
        self.document.refresh_from_db()

        self.assertEqual(self.document.category, '')
        self.assertEqual(self.document.entities, {})

    @patch('documents.processing.intelligence.ai_chat', side_effect=AIGatewayError('backend down'))
    def test_gateway_failure_leaves_document_unchanged_and_does_not_raise(self, mock_ai_chat):
        analyze_document(self.document)  # should not raise
        self.document.refresh_from_db()

        self.assertEqual(self.document.category, '')
        self.assertEqual(self.document.entities, {})

    @patch('documents.processing.intelligence.ai_chat')
    def test_document_with_no_chunks_skips_llm_call(self, mock_ai_chat):
        empty_document = Document.objects.create(
            organization=self.org,
            file=SimpleUploadedFile('empty.txt', b''),
            original_filename='empty.txt',
            file_type=Document.FileType.TXT,
            file_size=0,
            status=Document.Status.READY,
        )

        analyze_document(empty_document)

        mock_ai_chat.assert_not_called()

    @patch('documents.processing.intelligence.ai_chat')
    def test_non_string_entity_values_are_coerced_or_dropped(self, mock_ai_chat):
        mock_ai_chat.return_value = (
            '{"category": "CONTRACT", "dates": ["Jan 1"], "amounts": [5000, "$100"], '
            '"parties": [{"nested": "object"}, "Acme Corp"]}'
        )

        analyze_document(self.document)
        self.document.refresh_from_db()

        self.assertEqual(self.document.entities['amounts'], ['5000', '$100'])
        self.assertEqual(self.document.entities['parties'], ['Acme Corp'])
