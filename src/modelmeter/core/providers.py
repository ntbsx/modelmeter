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

    return "unknown"
