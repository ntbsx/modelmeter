from __future__ import annotations

import pytest

from modelmeter.core.providers import (
    provider_from_model_id,
    provider_from_model_id_and_provider_field,
)


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


class TestProviderFromProviderField:
    """Tests for provider detection using providerID field."""

    def test_provider_from_providerid_field_github_copilot(self) -> None:
        """GitHub Copilot models should be detected from providerID."""
        assert (
            provider_from_model_id_and_provider_field("gpt-5.3-codex", "github-copilot")
            == "github-copilot"
        )

        assert (
            provider_from_model_id_and_provider_field("claude-sonnet-4.5", "github-copilot")
            == "github-copilot"
        )

        assert (
            provider_from_model_id_and_provider_field("gpt-5.4", "GitHub-Copilot")
            == "github-copilot"
        )

    def test_provider_from_providerid_field_opencode(self) -> None:
        """OpenCode proxied models should be detected from providerID."""
        assert (
            provider_from_model_id_and_provider_field("minimax-m2.5-free", "opencode") == "opencode"
        )

        assert provider_from_model_id_and_provider_field("big-pickle", "opencode") == "opencode"

        assert (
            provider_from_model_id_and_provider_field("mimo-v2-flash-free", "OpenCode")
            == "opencode"
        )

    def test_fallback_to_pattern_matching_when_no_providerid(self) -> None:
        """Should fall back to pattern matching when providerID is None."""
        assert provider_from_model_id_and_provider_field("gpt-4o", None) == "openai"

        assert provider_from_model_id_and_provider_field("gpt-4o-mini", None) == "openai"

        assert provider_from_model_id_and_provider_field("claude-3-opus", None) == "anthropic"

        assert provider_from_model_id_and_provider_field("gemini-pro", None) == "google"

    def test_fallback_when_providerid_is_unknown(self) -> None:
        """Should fall back to pattern matching when providerID is 'unknown'."""
        assert provider_from_model_id_and_provider_field("gpt-4o", "unknown") == "openai"

        assert provider_from_model_id_and_provider_field("claude-3-opus", "unknown") == "anthropic"

    def test_providerid_takes_precedence_over_pattern(self) -> None:
        """providerID should take precedence even when pattern matches."""
        assert (
            provider_from_model_id_and_provider_field("gpt-5.3-codex", "github-copilot")
            == "github-copilot"
        )

        assert (
            provider_from_model_id_and_provider_field("claude-sonnet-4.5", "github-copilot")
            == "github-copilot"
        )

    def test_unknown_model_without_providerid(self) -> None:
        """Unknown models without providerID should return 'unknown'."""
        assert provider_from_model_id_and_provider_field("random-model-123", None) == "unknown"

        assert provider_from_model_id_and_provider_field("big-pickle", None) == "unknown"

    def test_empty_and_whitespace_providerid(self) -> None:
        """Empty or whitespace providerID should fall back to pattern."""
        assert provider_from_model_id_and_provider_field("gpt-4o", "") == "openai"

        assert provider_from_model_id_and_provider_field("gpt-4o", "   ") == "openai"

    def test_backwards_compatibility(self) -> None:
        """Original function should still work for existing code."""
        assert provider_from_model_id("gpt-4o") == "openai"
        assert provider_from_model_id("claude-3-opus") == "anthropic"
        assert provider_from_model_id("gemini-pro") == "google"
        assert provider_from_model_id("unknown-model") == "unknown"
