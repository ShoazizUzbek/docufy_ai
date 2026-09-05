from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from ai_gateway.base import AIGatewayError
from ai_gateway.openai_compatible import OllamaClient, OpenAICompatibleClient


@override_settings(AI_GATEWAY_API_KEY='sk-test-key')
class AnthropicClientTests(SimpleTestCase):
    def test_separates_system_messages_from_conversation(self):
        from ai_gateway.anthropic_client import AnthropicClient

        client = AnthropicClient()

        fake_response = MagicMock()
        fake_response.content = [MagicMock(type='text', text='Paris is the capital.')]

        with patch('anthropic.Anthropic') as mock_anthropic_cls:
            mock_sdk_client = MagicMock()
            mock_sdk_client.messages.create.return_value = fake_response
            mock_anthropic_cls.return_value = mock_sdk_client

            result = client.chat([
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': 'What is the capital of France?'},
            ])

        self.assertEqual(result, 'Paris is the capital.')
        _, kwargs = mock_sdk_client.messages.create.call_args
        self.assertEqual(kwargs['system'], 'You are a helpful assistant.')
        self.assertEqual(kwargs['messages'], [{'role': 'user', 'content': 'What is the capital of France?'}])

    def test_omits_system_kwarg_when_no_system_message(self):
        from ai_gateway.anthropic_client import AnthropicClient

        client = AnthropicClient()
        fake_response = MagicMock()
        fake_response.content = [MagicMock(type='text', text='hi')]

        with patch('anthropic.Anthropic') as mock_anthropic_cls:
            mock_sdk_client = MagicMock()
            mock_sdk_client.messages.create.return_value = fake_response
            mock_anthropic_cls.return_value = mock_sdk_client

            client.chat([{'role': 'user', 'content': 'hello'}])

        _, kwargs = mock_sdk_client.messages.create.call_args
        self.assertNotIn('system', kwargs)


class OpenAICompatibleClientTests(SimpleTestCase):
    def test_chat_posts_expected_payload_and_parses_response(self):
        client = OpenAICompatibleClient(base_url='http://example.com/v1', model='some-model', api_key='key123')

        mock_response = MagicMock()
        mock_response.json.return_value = {'choices': [{'message': {'content': 'the reply'}}]}
        mock_response.raise_for_status.return_value = None

        with patch('requests.post', return_value=mock_response) as mock_post:
            result = client.chat([{'role': 'user', 'content': 'hi'}], temperature=0.5, max_tokens=200)

        self.assertEqual(result, 'the reply')
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], 'http://example.com/v1/chat/completions')
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer key123')
        self.assertEqual(kwargs['json']['model'], 'some-model')
        self.assertEqual(kwargs['json']['temperature'], 0.5)
        self.assertEqual(kwargs['json']['max_tokens'], 200)

    def test_request_failure_raises_ai_gateway_error(self):
        import requests

        client = OpenAICompatibleClient(base_url='http://example.com/v1', model='m')
        with patch('requests.post', side_effect=requests.ConnectionError('refused')):
            with self.assertRaises(AIGatewayError):
                client.chat([{'role': 'user', 'content': 'hi'}])

    def test_malformed_response_raises_ai_gateway_error(self):
        client = OpenAICompatibleClient(base_url='http://example.com/v1', model='m')
        mock_response = MagicMock()
        mock_response.json.return_value = {'unexpected': 'shape'}
        mock_response.raise_for_status.return_value = None

        with patch('requests.post', return_value=mock_response):
            with self.assertRaises(AIGatewayError):
                client.chat([{'role': 'user', 'content': 'hi'}])


class OllamaClientTests(SimpleTestCase):
    @override_settings(AI_GATEWAY_BASE_URL='', AI_GATEWAY_MODEL='')
    def test_defaults_to_local_ollama_and_qwen(self):
        client = OllamaClient()
        self.assertEqual(client.base_url, 'http://localhost:11434/v1')
        self.assertEqual(client.model, 'qwen2.5:7b-instruct')

    @override_settings(AI_GATEWAY_BASE_URL='http://custom-host:11434/v1', AI_GATEWAY_MODEL='gemma2:9b')
    def test_settings_override_defaults(self):
        client = OllamaClient()
        self.assertEqual(client.base_url, 'http://custom-host:11434/v1')
        self.assertEqual(client.model, 'gemma2:9b')
