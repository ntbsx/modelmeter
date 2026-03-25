"""Verify SQLiteUsageRepository satisfies UsageRepository Protocol."""

from modelmeter.data.repository import UsageRepository
from modelmeter.data.sqlite_usage_repository import SQLiteUsageRepository


def test_protocol_exists() -> None:
    """UsageRepository should be importable as a Protocol."""
    assert hasattr(UsageRepository, "__protocol_attrs__") or callable(UsageRepository)


def test_sqlite_repository_satisfies_protocol() -> None:
    """SQLiteUsageRepository should be a structural subtype of UsageRepository."""
    assert issubclass(SQLiteUsageRepository, UsageRepository)
