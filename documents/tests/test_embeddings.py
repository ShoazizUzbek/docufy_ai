from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from documents.processing.embeddings import embed_query, embed_texts


class EmbedTextsTests(SimpleTestCase):
    def test_empty_input_returns_empty_list_without_loading_model(self):
        with patch('documents.processing.embeddings._get_model') as mock_get_model:
            self.assertEqual(embed_texts([]), [])
            mock_get_model.assert_not_called()

    @patch('documents.processing.embeddings._get_model')
    def test_encodes_with_normalization_and_returns_plain_lists(self, mock_get_model):
        mock_model = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_get_model.return_value = mock_model

        result = embed_texts(['hello', 'world'])

        mock_model.encode.assert_called_once_with(['hello', 'world'], normalize_embeddings=True, show_progress_bar=False)
        self.assertEqual(result, [[0.1, 0.2], [0.3, 0.4]])

    @patch('documents.processing.embeddings._get_model')
    def test_embed_query_returns_first_vector(self, mock_get_model):
        mock_model = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [[0.5, 0.6]]
        mock_get_model.return_value = mock_model

        self.assertEqual(embed_query('a question'), [0.5, 0.6])
