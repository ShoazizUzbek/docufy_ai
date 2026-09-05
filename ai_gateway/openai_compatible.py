from django.conf import settings

from .base import AIGatewayClient, AIGatewayError


class OpenAICompatibleClient(AIGatewayClient):
    """Works with any OpenAI-style /chat/completions endpoint — OpenAI
    itself, or a local Ollama server, which mimics that API."""

    def __init__(self, base_url: str, model: str, api_key: str | None = None):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.api_key = api_key

    def chat(self, messages: list[dict], *, temperature: float = 0.0, max_tokens: int = 1024) -> str:
        import requests

        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        try:
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json={
                    'model': self.model,
                    'messages': messages,
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                },
                timeout=120,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise AIGatewayError(f'AI Gateway request to {self.base_url} failed: {exc}') from exc

        data = response.json()
        try:
            return data['choices'][0]['message']['content']
        except (KeyError, IndexError) as exc:
            raise AIGatewayError(f'Unexpected AI Gateway response shape: {data}') from exc


# Qwen2.5's multilingual training covers Uzbek/Russian/English (and many
# more) noticeably better than Gemma's, which matters here since that's
# this platform's target language mix — hence the default over Gemma.
# Swap via AI_GATEWAY_MODEL (e.g. "gemma2:9b") without touching code.
DEFAULT_OLLAMA_MODEL = 'qwen2.5:7b-instruct'
DEFAULT_OLLAMA_BASE_URL = 'http://localhost:11434/v1'


class OllamaClient(OpenAICompatibleClient):
    def __init__(self, base_url: str | None = None, model: str | None = None):
        super().__init__(
            base_url=base_url or settings.AI_GATEWAY_BASE_URL or DEFAULT_OLLAMA_BASE_URL,
            model=model or settings.AI_GATEWAY_MODEL or DEFAULT_OLLAMA_MODEL,
            # Ollama ignores the key but requires the header to be well-formed.
            api_key='ollama',
        )
