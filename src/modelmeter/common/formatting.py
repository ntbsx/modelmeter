"""Human-readable formatting helpers."""

from __future__ import annotations

from pathlib import Path


def format_tokens_human(value: int) -> str:
    """Format token counts with compact and exact forms."""
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        short = f"{value / 1_000_000_000:.1f}B"
    elif abs_value >= 1_000_000:
        short = f"{value / 1_000_000:.1f}M"
    elif abs_value >= 1_000:
        short = f"{value / 1_000:.1f}K"
    else:
        return f"{value:,}"

    return f"{short} ({value:,})"


def format_usd_human(value: float) -> str:
    """Format USD amounts with compact and exact forms."""
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        short = f"${value / 1_000_000_000:.1f}B"
    elif abs_value >= 1_000_000:
        short = f"${value / 1_000_000:.1f}M"
    elif abs_value >= 1_000:
        short = f"${value / 1_000:.1f}K"
    elif abs_value >= 1:
        short = f"${value:,.2f}"
    else:
        short = f"${value:,.6f}"

    exact = f"${value:,.6f}"
    if short == exact:
        return short
    return f"{short} ({exact})"


def format_pricing_source_human(source: str) -> str:
    """Format pricing source labels for human-readable CLI output."""
    if source.startswith("models.dev stale cache"):
        return "models.dev (stale cache)"
    if source.startswith("models.dev cache"):
        return "models.dev (cached)"
    if source.startswith("models.dev ("):
        return "models.dev (live)"

    return Path(source).name
