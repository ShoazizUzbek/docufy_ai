from abc import ABC, abstractmethod


class AIGatewayError(Exception):
    """Raised when the configured LLM backend fails or is misconfigured."""


class AIGatewayClient(ABC):
    @abstractmethod
    def chat(self, messages: list[dict], *, temperature: float = 0.0, max_tokens: int = 1024) -> str:
        """`messages` is a list of {"role": "system"|"user"|"assistant", "content": str}.
        Returns the assistant's reply as plain text."""
