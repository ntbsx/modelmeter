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


def provider_from_model_id_and_provider_field(
    model_id: str,
    provider_id: str | None = None,
) -> str:
    """
    Resolve provider label from model_id and optional providerID field.

    Priority:
    1. Use providerID from message data if available and valid
    2. Fall back to heuristic pattern matching on model_id

    Args:
        model_id: Model identifier string (e.g., "gpt-4o", "claude-3-opus")
        provider_id: Optional providerID from message JSON

    Returns:
        Normalized provider name (e.g., "openai", "github-copilot", "opencode")
    """
    if provider_id:
        normalized = provider_id.strip().lower()
        if normalized and normalized != "unknown":
            return normalized

    return provider_from_model_id(model_id)
