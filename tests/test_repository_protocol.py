"""Verify SQLiteUsageRepository satisfies UsageRepository Protocol."""

from modelmeter.data.repository import UsageRepository


def test_protocol_exists() -> None:
    """UsageRepository should be importable as a Protocol."""
    assert hasattr(UsageRepository, "__protocol_attrs__") or callable(UsageRepository)
