from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from ai_gateway import AIGatewayError, ai_chat
from ai_gateway.anthropic_client import AnthropicClient
from ai_gateway.factory import get_client
from ai_gateway.openai_compatible import OllamaClient


class GetClientTests(SimpleTestCase):
    @override_settings(AI_GATEWAY_PROVIDER='anthropic', AI_GATEWAY_API_KEY='sk-test')
    def test_anthropic_provider_returns_anthropic_client(self):
        self.assertIsInstance(get_client(), AnthropicClient)

    @override_settings(AI_GATEWAY_PROVIDER='ollama')
    def test_ollama_provider_returns_ollama_client(self):
        self.assertIsInstance(get_client(), OllamaClient)

    @override_settings(AI_GATEWAY_PROVIDER='not-a-real-provider')
    def test_unknown_provider_raises(self):
        with self.assertRaises(AIGatewayError):
            get_client()

    @override_settings(AI_GATEWAY_PROVIDER='anthropic', AI_GATEWAY_API_KEY='')
    def test_anthropic_without_api_key_raises(self):
        with self.assertRaises(AIGatewayError):
            get_client()


class AiChatTests(SimpleTestCase):
    @override_settings(AI_GATEWAY_PROVIDER='ollama')
    @patch('ai_gateway.factory.get_client')
    def test_routes_to_configured_client(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.return_value = 'the answer'
        mock_get_client.return_value = mock_client

        result = ai_chat([{'role': 'user', 'content': 'hi'}])

        self.assertEqual(result, 'the answer')
        mock_client.chat.assert_called_once()

    @override_settings(AI_GATEWAY_PROVIDER='ollama')
    @patch('ai_gateway.factory.get_client')
    def test_context_is_injected_as_leading_system_message(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.return_value = 'ok'
        mock_get_client.return_value = mock_client

        ai_chat([{'role': 'user', 'content': 'question'}], context='some grounding text')

        sent_messages = mock_client.chat.call_args[0][0]
        self.assertEqual(sent_messages[0], {'role': 'system', 'content': 'some grounding text'})
        self.assertEqual(sent_messages[1], {'role': 'user', 'content': 'question'})

    @override_settings(AI_GATEWAY_PROVIDER='ollama')
    @patch('ai_gateway.factory.get_client')
    def test_no_context_leaves_messages_untouched(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.return_value = 'ok'
        mock_get_client.return_value = mock_client

        original = [{'role': 'user', 'content': 'question'}]
        ai_chat(original)

        sent_messages = mock_client.chat.call_args[0][0]
        self.assertEqual(sent_messages, original)
