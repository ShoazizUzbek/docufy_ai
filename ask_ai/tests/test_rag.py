import uuid
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from ai_gateway import AIGatewayError
from ask_ai.rag import (
    NO_DOCUMENT_CONTENT_MESSAGE,
    NO_DOCUMENTS_MESSAGE,
    NO_MATCH_MESSAGE,
    UNAVAILABLE_MESSAGE,
    answer_question,
)


class FakePoint:
    def __init__(self, chunk_id, score, **payload_fields):
        self.id = chunk_id
        self.score = score
        self.payload = {
            'document_id': str(uuid.uuid4()),
            'original_filename': 'lease.txt',
            'page_number': 1,
            'section_heading': '',
            'hierarchy_path': '',
            'text': 'Some chunk text.',
            **payload_fields,
        }


def _points(*scored_texts):
    return [FakePoint(uuid.uuid4(), score, text=text) for score, text in scored_texts]


@override_settings(RAG_TOP_K=5, RAG_MIN_SCORE=0.3)
@patch('ask_ai.rag.embed_query', return_value=[0.0] * 1024)
class AnswerQuestionTests(SimpleTestCase):
    @patch('ask_ai.rag.search_chunks', return_value=[])
    def test_no_indexed_chunks_returns_no_documents_message(self, mock_search, mock_embed):
        result = answer_question('anything?', organization_id=uuid.uuid4())

        self.assertEqual(result['answer'], NO_DOCUMENTS_MESSAGE)
        self.assertFalse(result['confident'])
        self.assertEqual(result['citations'], [])
        self.assertEqual(result['sources'], [])

    @patch('ask_ai.rag.search_chunks', return_value=[])
    def test_no_chunks_scoped_to_a_document_returns_document_specific_message(self, mock_search, mock_embed):
        document_id = uuid.uuid4()
        result = answer_question('anything?', organization_id=uuid.uuid4(), document_id=document_id)

        self.assertEqual(result['answer'], NO_DOCUMENT_CONTENT_MESSAGE)
        mock_search.assert_called_once()
        self.assertEqual(mock_search.call_args.kwargs['document_id'], document_id)

    @patch('ask_ai.rag.search_chunks')
    def test_weak_top_score_skips_llm_and_returns_no_match(self, mock_search, mock_embed):
        mock_search.return_value = _points((0.1, 'Unrelated text.'))

        with patch('ask_ai.rag.ai_chat') as mock_ai_chat:
            result = answer_question('anything?', organization_id=uuid.uuid4())
            mock_ai_chat.assert_not_called()

        self.assertEqual(result['answer'], NO_MATCH_MESSAGE)
        self.assertFalse(result['confident'])
        self.assertEqual(result['citations'], [])
        self.assertEqual(len(result['sources']), 1)

    @patch('ask_ai.rag.ai_chat')
    @patch('ask_ai.rag.search_chunks')
    def test_confident_answer_with_valid_citation(self, mock_search, mock_ai_chat, mock_embed):
        mock_search.return_value = _points(
            (0.9, 'Rent is due on the first of the month.'),
            (0.5, 'The property must be maintained.'),
        )
        mock_ai_chat.return_value = (
            '{"answer": "Rent is due on the 1st.", "cited_sources": [1], '
            '"confident": true, "follow_up_questions": ["What is the penalty for late rent?"]}'
        )

        result = answer_question('When is rent due?', organization_id=uuid.uuid4())

        self.assertEqual(result['answer'], 'Rent is due on the 1st.')
        self.assertTrue(result['confident'])
        self.assertEqual(len(result['citations']), 1)
        self.assertEqual(result['citations'][0]['index'], 1)
        self.assertEqual(len(result['sources']), 2)
        self.assertEqual(result['follow_up_questions'], ['What is the penalty for late rent?'])

    @patch('ask_ai.rag.ai_chat')
    @patch('ask_ai.rag.search_chunks')
    def test_llm_wrapping_json_in_markdown_fence_still_parses(self, mock_search, mock_ai_chat, mock_embed):
        mock_search.return_value = _points((0.9, 'Some relevant text.'))
        mock_ai_chat.return_value = (
            '```json\n{"answer": "Yes.", "cited_sources": [1], "confident": true, '
            '"follow_up_questions": []}\n```'
        )

        result = answer_question('Is it true?', organization_id=uuid.uuid4())

        self.assertEqual(result['answer'], 'Yes.')
        self.assertTrue(result['confident'])

    @patch('ask_ai.rag.ai_chat')
    @patch('ask_ai.rag.search_chunks')
    def test_confident_flag_downgraded_when_no_citations(self, mock_search, mock_ai_chat, mock_embed):
        mock_search.return_value = _points((0.9, 'Some relevant text.'))
        mock_ai_chat.return_value = '{"answer": "I think so.", "cited_sources": [], "confident": true, "follow_up_questions": []}'

        result = answer_question('Is it true?', organization_id=uuid.uuid4())

        self.assertFalse(result['confident'])
        self.assertEqual(result['citations'], [])

    @patch('ask_ai.rag.ai_chat')
    @patch('ask_ai.rag.search_chunks')
    def test_unparseable_llm_response_falls_back_to_raw_text(self, mock_search, mock_ai_chat, mock_embed):
        mock_search.return_value = _points((0.9, 'Some relevant text.'))
        mock_ai_chat.return_value = 'This is not JSON at all.'

        result = answer_question('Is it true?', organization_id=uuid.uuid4())

        self.assertEqual(result['answer'], 'This is not JSON at all.')
        self.assertFalse(result['confident'])
        self.assertEqual(result['citations'], [])
        self.assertEqual(len(result['sources']), 1)

    @patch('ask_ai.rag.ai_chat', side_effect=AIGatewayError('backend down'))
    @patch('ask_ai.rag.search_chunks')
    def test_ai_gateway_error_returns_unavailable_message(self, mock_search, mock_ai_chat, mock_embed):
        mock_search.return_value = _points((0.9, 'Some relevant text.'))

        result = answer_question('Is it true?', organization_id=uuid.uuid4())

        self.assertEqual(result['answer'], UNAVAILABLE_MESSAGE)
        self.assertFalse(result['confident'])
        self.assertEqual(len(result['sources']), 1)

    @patch('ask_ai.rag.ai_chat')
    @patch('ask_ai.rag.search_chunks')
    def test_conversation_history_included_in_messages_sent_to_llm(self, mock_search, mock_ai_chat, mock_embed):
        mock_search.return_value = _points((0.9, 'Some relevant text.'))
        mock_ai_chat.return_value = '{"answer": "ok", "cited_sources": [1], "confident": true, "follow_up_questions": []}'

        answer_question(
            'And after that?',
            organization_id=uuid.uuid4(),
            conversation_history=[{'question': 'What is the term?', 'answer': 'Twelve months.'}],
        )

        messages = mock_ai_chat.call_args[0][0]
        contents = [(m['role'], m['content']) for m in messages]
        self.assertIn(('user', 'What is the term?'), contents)
        self.assertIn(('assistant', 'Twelve months.'), contents)
        self.assertEqual(contents[-1], ('user', 'And after that?'))
