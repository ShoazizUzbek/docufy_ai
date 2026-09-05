from django.conf import settings

from .base import AIGatewayClient, AIGatewayError

DEFAULT_MODEL = 'claude-sonnet-5'


class AnthropicClient(AIGatewayClient):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.AI_GATEWAY_API_KEY
        self.model = model or settings.AI_GATEWAY_MODEL or DEFAULT_MODEL
        if not self.api_key:
            raise AIGatewayError(
                'AI_GATEWAY_API_KEY is not configured. Set it in .env to use the Anthropic provider, '
                'or set AI_GATEWAY_PROVIDER=ollama to use a local model instead.'
            )

    def chat(self, messages: list[dict], *, temperature: float = 0.0, max_tokens: int = 1024) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        system_parts = [m['content'] for m in messages if m['role'] == 'system']
        conversation = [{'role': m['role'], 'content': m['content']} for m in messages if m['role'] != 'system']

        kwargs = {
            'model': self.model,
            'messages': conversation,
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
        if system_parts:
            kwargs['system'] = '\n\n'.join(system_parts)

        try:
            response = client.messages.create(**kwargs)
        except anthropic.APIError as exc:
            raise AIGatewayError(f'Anthropic API request failed: {exc}') from exc

        return ''.join(block.text for block in response.content if block.type == 'text')
