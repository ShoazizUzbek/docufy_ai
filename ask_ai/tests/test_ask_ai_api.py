import uuid
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Organization, User


class AskAIAPITests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme', slug='acme')
        self.user = User.objects.create_user(email='u@acme.com', password='pw12345', organization=self.org)
        self.client.force_authenticate(self.user)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        response = self.client.post(reverse('ask-ai'), {'question': 'anything'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rejects_blank_question(self):
        response = self.client.post(reverse('ask-ai'), {'question': '   '}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_missing_question(self):
        response = self.client.post(reverse('ask-ai'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('ask_ai.views.answer_question')
    def test_returns_serialized_answer_and_passes_org_scope(self, mock_answer_question):
        mock_answer_question.return_value = {
            'answer': 'Rent is due on the 1st.',
            'confident': True,
            'citations': [{
                'index': 1, 'chunk_id': 'abc', 'document_id': 'doc1', 'original_filename': 'lease.txt',
                'page_number': 2, 'section_heading': 'Rent', 'hierarchy_path': 'Ch1 > Rent',
                'text': 'Rent is due...', 'score': 0.9,
            }],
            'sources': [],
            'follow_up_questions': ['What about late fees?'],
        }

        response = self.client.post(reverse('ask-ai'), {'question': 'When is rent due?'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['answer'], 'Rent is due on the 1st.')
        self.assertTrue(response.data['confident'])
        self.assertEqual(len(response.data['citations']), 1)
        self.assertEqual(response.data['follow_up_questions'], ['What about late fees?'])

        _, kwargs = mock_answer_question.call_args
        self.assertEqual(kwargs['question'], 'When is rent due?')
        self.assertEqual(kwargs['organization_id'], self.org.id)
        self.assertEqual(kwargs['conversation_history'], [])
        self.assertIsNone(kwargs['document_id'])

    @patch('ask_ai.views.answer_question')
    def test_passes_document_id_through_when_provided(self, mock_answer_question):
        mock_answer_question.return_value = {
            'answer': 'ok', 'confident': True, 'citations': [], 'sources': [], 'follow_up_questions': [],
        }
        document_id = uuid.uuid4()

        self.client.post(
            reverse('ask-ai'),
            {'question': 'What does this document say about rent?', 'document_id': str(document_id)},
            format='json',
        )

        _, kwargs = mock_answer_question.call_args
        self.assertEqual(kwargs['document_id'], document_id)

    def test_rejects_malformed_document_id(self):
        response = self.client.post(
            reverse('ask-ai'),
            {'question': 'x', 'document_id': 'not-a-uuid'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('ask_ai.views.answer_question')
    def test_passes_conversation_history_through(self, mock_answer_question):
        mock_answer_question.return_value = {
            'answer': 'ok', 'confident': True, 'citations': [], 'sources': [], 'follow_up_questions': [],
        }

        self.client.post(
            reverse('ask-ai'),
            {
                'question': 'And after that?',
                'conversation_history': [{'question': 'What is the term?', 'answer': 'Twelve months.'}],
            },
            format='json',
        )

        _, kwargs = mock_answer_question.call_args
        self.assertEqual(
            kwargs['conversation_history'],
            [{'question': 'What is the term?', 'answer': 'Twelve months.'}],
        )

    def test_rejects_malformed_conversation_history(self):
        response = self.client.post(
            reverse('ask-ai'),
            {'question': 'x', 'conversation_history': [{'question': 'only a question, no answer'}]},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
