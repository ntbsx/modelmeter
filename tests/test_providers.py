from __future__ import annotations

import pytest

from modelmeter.core.providers import provider_from_model_id


@pytest.mark.parametrize(
    ("model_id", "expected_provider"),
    [
        ("anthropic/claude-sonnet-4-5", "anthropic"),
        ("openai/gpt-5", "openai"),
        ("gpt-5.3-codex", "openai"),
        ("claude-opus-4-5", "anthropic"),
        ("gemini-3-pro-preview", "google"),
        ("grok-3", "xai"),
        ("unknown", "unknown"),
        ("big-pickle", "unknown"),
    ],
)
def test_provider_from_model_id(model_id: str, expected_provider: str) -> None:
    assert provider_from_model_id(model_id) == expected_provider
