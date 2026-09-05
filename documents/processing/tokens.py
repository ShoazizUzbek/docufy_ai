import re

_TOKEN_RE = re.compile(r"\S+")


def estimate_tokens(text: str) -> int:
    """Whitespace-token count, used as a cheap proxy for model tokens.

    Good enough to target the 200-500 "token" chunk size from the spec
    without depending on a specific tokenizer here; Phase 3 will re-derive
    exact counts from the BGE-M3 tokenizer at embedding time.
    """
    return len(_TOKEN_RE.findall(text))
