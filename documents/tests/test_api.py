import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Organization, User
from documents.models import Chunk, Document

TEMP_MEDIA_ROOT = tempfile.mkdtemp()

TEST_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT, STORAGES=TEST_STORAGES)
class DocumentUploadAPITests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.org = Organization.objects.create(name='Acme', slug='acme')
        self.other_org = Organization.objects.create(name='Other', slug='other')
        self.user = User.objects.create_user(
            email='user@acme.com', password='pw12345', organization=self.org,
        )
        self.other_user = User.objects.create_user(
            email='user@other.com', password='pw12345', organization=self.other_org,
        )
        self.client.force_authenticate(self.user)

    @patch('documents.views.process_document_task')
    def test_upload_creates_document_and_queues_processing(self, mock_task):
        file = SimpleUploadedFile('report.txt', b'hello world', content_type='text/plain')
        response = self.client.post(reverse('document-list'), {'file': file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], Document.Status.UPLOADED)
        self.assertEqual(response.data['file_type'], Document.FileType.TXT)
        self.assertEqual(response.data['original_filename'], 'report.txt')

        document = Document.objects.get(pk=response.data['id'])
        self.assertEqual(document.organization, self.org)
        self.assertEqual(document.uploaded_by, self.user)
        self.assertEqual(document.file_size, 11)
        mock_task.delay.assert_called_once_with(str(document.id))

    def test_upload_rejects_unsupported_extension(self):
        file = SimpleUploadedFile('malware.exe', b'MZ', content_type='application/octet-stream')
        response = self.client.post(reverse('document-list'), {'file': file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)

    def test_upload_requires_authentication(self):
        self.client.force_authenticate(None)
        file = SimpleUploadedFile('report.txt', b'hello world', content_type='text/plain')
        response = self.client.post(reverse('document-list'), {'file': file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_includes_category_and_entities(self):
        document = Document.objects.create(
            organization=self.org, uploaded_by=self.user,
            file=SimpleUploadedFile('lease.txt', b'lease text'),
            original_filename='lease.txt', file_type=Document.FileType.TXT, file_size=10,
            status=Document.Status.READY, category=Document.Category.CONTRACT,
            entities={'dates': ['Jan 1, 2026'], 'amounts': ['$500'], 'parties': ['Acme Corp']},
        )

        response = self.client.get(reverse('document-detail', args=[document.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['category'], 'CONTRACT')
        self.assertEqual(response.data['entities']['parties'], ['Acme Corp'])

    def test_list_only_returns_documents_for_own_organization(self):
        Document.objects.create(
            organization=self.org, uploaded_by=self.user,
            file=SimpleUploadedFile('mine.txt', b'mine'),
            original_filename='mine.txt', file_type=Document.FileType.TXT, file_size=4,
        )
        Document.objects.create(
            organization=self.other_org, uploaded_by=self.other_user,
            file=SimpleUploadedFile('theirs.txt', b'theirs'),
            original_filename='theirs.txt', file_type=Document.FileType.TXT, file_size=6,
        )

        response = self.client.get(reverse('document-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        filenames = [doc['original_filename'] for doc in response.data]
        self.assertEqual(filenames, ['mine.txt'])


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT, STORAGES=TEST_STORAGES)
class DocumentContentAPITests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.org = Organization.objects.create(name='Acme', slug='acme')
        self.other_org = Organization.objects.create(name='Other', slug='other')
        self.user = User.objects.create_user(email='u@acme.com', password='pw12345', organization=self.org)
        self.client.force_authenticate(self.user)

    def _make_document(self, organization, filename='doc.txt'):
        return Document.objects.create(
            organization=organization,
            file=SimpleUploadedFile(filename, b'content'),
            original_filename=filename,
            file_type=Document.FileType.TXT,
            file_size=7,
            status=Document.Status.READY,
        )

    def test_groups_chunks_by_page_in_order(self):
        document = self._make_document(self.org)
        Chunk.objects.create(document=document, index=1, page_number=1, text='second on page 1')
        Chunk.objects.create(document=document, index=0, page_number=1, text='first on page 1')
        Chunk.objects.create(document=document, index=2, page_number=2, text='first on page 2')

        response = self.client.get(reverse('document-content', args=[document.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([p['page_number'] for p in response.data], [1, 2])
        self.assertEqual(
            [c['text'] for c in response.data[0]['chunks']],
            ['first on page 1', 'second on page 1'],
        )
        self.assertEqual(len(response.data[1]['chunks']), 1)

    def test_document_with_no_chunks_returns_empty_list(self):
        document = self._make_document(self.org)
        response = self.client.get(reverse('document-content', args=[document.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_cannot_access_another_organizations_document_content(self):
        other_document = self._make_document(self.other_org)
        Chunk.objects.create(document=other_document, index=0, page_number=1, text='secret')

        response = self.client.get(reverse('document-content', args=[other_document.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_requires_authentication(self):
        document = self._make_document(self.org)
        self.client.force_authenticate(None)
        response = self.client.get(reverse('document-content', args=[document.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
