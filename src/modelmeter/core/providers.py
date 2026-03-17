"""Provider attribution helpers."""

from __future__ import annotations


def provider_from_model_id(model_id: str) -> str:
    """Resolve provider label from a model id string."""
    normalized = model_id.strip().lower()
    if not normalized or normalized == "unknown":
        return "unknown"

    if "/" in normalized:
        provider = normalized.split("/", maxsplit=1)[0].strip()
        return provider if provider else "unknown"

    heuristic_prefixes: tuple[tuple[str, str], ...] = (
        ("gpt-", "openai"),
        ("o1", "openai"),
        ("o3", "openai"),
        ("o4", "openai"),
        ("text-embedding-", "openai"),
        ("dall-e-", "openai"),
        ("whisper-", "openai"),
        ("tts-", "openai"),
        ("claude-", "anthropic"),
        ("gemini-", "google"),
        ("grok-", "xai"),
    )
    for prefix, provider in heuristic_prefixes:
        if normalized.startswith(prefix):
            return provider

    return "unknown"
