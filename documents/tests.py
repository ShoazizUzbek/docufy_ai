import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Organization, User
from .models import Document

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

    def test_upload_creates_document_with_uploaded_status(self):
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
