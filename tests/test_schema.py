import json
from pathlib import Path

from modelmeter.core.models import SummaryResponse, TokenUsage


def test_summary_schema_stability(tmp_path: Path):
    """Ensure the JSON schema output of models doesn't break web consumers accidentally."""
    usage = TokenUsage(
        input_tokens=100, output_tokens=50, cache_read_tokens=10, cache_write_tokens=0
    )
    summary = SummaryResponse(
        usage=usage, total_sessions=5, window_days=7, cost_usd=1.23, pricing_source="test"
    )

    dumped = json.loads(summary.model_dump_json())

    assert dumped["total_sessions"] == 5
    assert dumped["window_days"] == 7
    assert dumped["cost_usd"] == 1.23
    assert dumped["pricing_source"] == "test"
    assert dumped["usage"]["input_tokens"] == 100
    assert dumped["usage"]["output_tokens"] == 50
    assert dumped["usage"]["cache_read_tokens"] == 10
    assert dumped["usage"]["cache_write_tokens"] == 0
    assert dumped["usage"]["total_tokens"] == 160
