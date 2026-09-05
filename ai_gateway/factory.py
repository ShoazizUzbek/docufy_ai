from django.conf import settings

from .base import AIGatewayClient, AIGatewayError


def get_client() -> AIGatewayClient:
    """Not cached — constructing a client is cheap (no network calls, no
    model loading), so every call picks up the current settings, which
    keeps this trivial to test against different providers."""
    provider = settings.AI_GATEWAY_PROVIDER

    if provider == 'anthropic':
        from .anthropic_client import AnthropicClient

        return AnthropicClient()

    if provider == 'ollama':
        from .openai_compatible import OllamaClient

        return OllamaClient()

    raise AIGatewayError(
        f"Unknown AI_GATEWAY_PROVIDER {provider!r}. Expected 'anthropic' or 'ollama'."
    )


def ai_chat(
    messages: list[dict],
    context: str | None = None,
    *,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> str:
    """Provider-agnostic chat completion — routes to whichever backend
    AI_GATEWAY_PROVIDER selects (Anthropic's hosted API, or a local model
    via Ollama), so callers never need to know which.

    `context` is optional grounding text (e.g. retrieved document
    excerpts for RAG) injected as a leading system message; `messages` is
    the actual conversation.
    """
    if context:
        messages = [{'role': 'system', 'content': context}, *messages]
    return get_client().chat(messages, temperature=temperature, max_tokens=max_tokens)
