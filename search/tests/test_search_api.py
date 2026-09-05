import uuid
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Organization, User
from documents.processing import vector_store

TEST_COLLECTION = f'test_docufy_chunks_{uuid.uuid4().hex[:8]}'


def _fake_embed(texts):
    vectors = []
    for text in texts:
        vector = [0.0] * 1024
        vector[hash(text) % 1024] = 1.0
        vectors.append(vector)
    return vectors


class FakeChunk:
    def __init__(self, id, index, text, page_number=1, section_heading='', hierarchy_path=''):
        self.id = id
        self.index = index
        self.text = text
        self.page_number = page_number
        self.section_heading = section_heading
        self.hierarchy_path = hierarchy_path


class FakeDocument:
    def __init__(self, id, organization_id, original_filename='doc.txt'):
        self.id = id
        self.organization_id = organization_id
        self.original_filename = original_filename


@override_settings(QDRANT_COLLECTION_NAME=TEST_COLLECTION)
@patch('documents.processing.vector_store.embed_texts', side_effect=_fake_embed)
class SearchAPITests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        try:
            vector_store.get_client().delete_collection(TEST_COLLECTION)
        except Exception:
            pass

    def setUp(self):
        self.org = Organization.objects.create(name='Acme', slug='acme')
        self.other_org = Organization.objects.create(name='Other', slug='other')
        self.user = User.objects.create_user(email='u@acme.com', password='pw12345', organization=self.org)
        self.client.force_authenticate(self.user)

    def _index_chunk(self, mock_embed, organization, text, **kwargs):
        document = FakeDocument(id=uuid.uuid4(), organization_id=organization.id, original_filename=kwargs.pop('original_filename', 'lease.txt'))
        chunk = FakeChunk(id=uuid.uuid4(), index=0, text=text, **kwargs)
        vector_store.upsert_chunks(document, [chunk])
        return document, chunk

    @patch('search.views.embed_query')
    def test_search_returns_matching_chunk(self, mock_embed_query, mock_embed):
        text = 'The tenant shall pay rent on the first of each month.'
        document, chunk = self._index_chunk(mock_embed, self.org, text, page_number=3, section_heading='Article 1', hierarchy_path='Chapter 1 > Article 1')
        mock_embed_query.return_value = _fake_embed([text])[0]

        response = self.client.post(reverse('search'), {'query': 'when is rent due'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        result = response.data[0]
        self.assertEqual(result['document_id'], str(document.id))
        self.assertEqual(result['page_number'], 3)
        self.assertEqual(result['section_heading'], 'Article 1')
        self.assertEqual(result['hierarchy_path'], 'Chapter 1 > Article 1')
        self.assertEqual(result['text'], text)
        self.assertIn('score', result)

    @patch('search.views.embed_query')
    def test_search_excludes_other_organizations(self, mock_embed_query, mock_embed):
        text = 'A very specific indemnification clause.'
        self._index_chunk(mock_embed, self.other_org, text)
        mock_embed_query.return_value = _fake_embed([text])[0]

        response = self.client.post(reverse('search'), {'query': 'indemnification'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_search_requires_authentication(self, mock_embed):
        self.client.force_authenticate(None)
        response = self.client.post(reverse('search'), {'query': 'anything'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_search_rejects_blank_query(self, mock_embed):
        response = self.client.post(reverse('search'), {'query': '   '}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_rejects_missing_query(self, mock_embed):
        response = self.client.post(reverse('search'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('search.views.embed_query')
    def test_search_respects_limit(self, mock_embed_query, mock_embed):
        texts = [f'Distinct clause number {i} about payment terms.' for i in range(5)]
        for text in texts:
            self._index_chunk(mock_embed, self.org, text)
        mock_embed_query.return_value = _fake_embed([texts[0]])[0]

        response = self.client.post(reverse('search'), {'query': 'payment terms', 'limit': 2}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
