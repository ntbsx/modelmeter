"""Model pricing loading and cost calculation utilities."""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from modelmeter.config.settings import AppSettings
from modelmeter.core.models import TokenUsage


@dataclass(frozen=True)
class ModelPricing:
    """Per-million token pricing for one model."""

    input_per_million: float
    output_per_million: float
    cache_read_per_million: float
    cache_write_per_million: float


def _pick_number(raw: dict[str, Any], *keys: str) -> float:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, int | float):
            return float(value)
    return 0.0


def _parse_pricing_payload(payload: Any) -> dict[str, ModelPricing]:
    if not isinstance(payload, dict):
        return {}

    parsed: dict[str, ModelPricing] = {}
    raw_payload = cast(dict[object, object], payload)

    for raw_model_id, raw_pricing in raw_payload.items():
        model_id = str(raw_model_id)
        if not isinstance(raw_pricing, dict):
            continue

        typed_pricing = cast(dict[object, object], raw_pricing)
        pricing_dict: dict[str, Any] = {str(k): v for k, v in typed_pricing.items()}

        parsed[model_id] = ModelPricing(
            input_per_million=_pick_number(pricing_dict, "input", "input_per_million"),
            output_per_million=_pick_number(pricing_dict, "output", "output_per_million"),
            cache_read_per_million=_pick_number(
                pricing_dict,
                "cache_read",
                "cacheRead",
                "cache_read_per_million",
            ),
            cache_write_per_million=_pick_number(
                pricing_dict,
                "cache_write",
                "cacheWrite",
                "cache_write_per_million",
            ),
        )

    return parsed


def _parse_models_dev_payload(payload: Any) -> dict[str, ModelPricing]:
    if not isinstance(payload, dict):
        return {}

    parsed: dict[str, ModelPricing] = {}
    providers = cast(dict[object, object], payload)

    for provider_data in providers.values():
        if not isinstance(provider_data, dict):
            continue
        provider_map = cast(dict[object, object], provider_data)
        models = provider_map.get("models")
        if not isinstance(models, dict):
            continue

        for model_data in cast(dict[object, object], models).values():
            if not isinstance(model_data, dict):
                continue

            model_map = cast(dict[object, object], model_data)
            model_id_raw = model_map.get("id")
            cost_raw = model_map.get("cost")
            if not isinstance(model_id_raw, str) or not isinstance(cost_raw, dict):
                continue

            model_id = model_id_raw
            cost_map = {str(k): v for k, v in cast(dict[object, object], cost_raw).items()}
            parsed[model_id] = ModelPricing(
                input_per_million=_pick_number(cost_map, "input", "input_per_million"),
                output_per_million=_pick_number(cost_map, "output", "output_per_million"),
                cache_read_per_million=_pick_number(
                    cost_map,
                    "cache_read",
                    "cacheRead",
                    "cache_read_per_million",
                ),
                cache_write_per_million=_pick_number(
                    cost_map,
                    "cache_write",
                    "cacheWrite",
                    "cache_write_per_million",
                ),
            )

    return parsed


def _load_pricing_file(path: Path) -> dict[str, ModelPricing]:
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return _parse_pricing_payload(payload)


def _cache_path() -> Path:
    return Path.home() / ".cache" / "modelmeter" / "models_dev_api.json"


def _load_cache(path: Path, ttl_hours: int) -> tuple[dict[str, Any] | None, bool]:
    if not path.exists():
        return None, False

    try:
        cached = json.loads(path.read_text())
    except (OSError, ValueError):
        return None, False

    if not isinstance(cached, dict):
        return None, False

    cached_map = cast(dict[str, Any], cached)

    fetched_at = cached_map.get("fetched_at")
    payload = cached_map.get("payload")
    if not isinstance(fetched_at, int | float):
        return None, False
    if payload is None:
        return None, False

    age_seconds = time.time() - float(fetched_at)
    ttl_seconds = ttl_hours * 3600
    is_fresh = age_seconds <= ttl_seconds
    return {"payload": payload}, is_fresh


def _write_cache(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wrapped = {
        "fetched_at": int(time.time()),
        "payload": payload,
    }
    path.write_text(json.dumps(wrapped))


def _fetch_models_dev(url: str, timeout_seconds: int) -> dict[str, Any] | None:
    request = urllib.request.Request(url, headers={"User-Agent": "modelmeter/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.load(response)
    except (OSError, ValueError):
        return None

    if isinstance(payload, dict):
        return cast(dict[str, Any], payload)
    return None


def load_pricing_book(
    *,
    settings: AppSettings,
    pricing_file_override: Path | None = None,
) -> tuple[dict[str, ModelPricing], str | None]:
    """Load pricing definitions and return (pricing_book, source)."""
    candidates: list[Path] = []
    if pricing_file_override is not None:
        candidates.append(pricing_file_override)
    elif settings.pricing_file is not None:
        candidates.append(settings.pricing_file)
    else:
        candidates.extend(
            [
                Path.cwd() / "models.json",
                Path.home() / ".config" / "modelmeter" / "models.json",
            ]
        )

    for candidate in candidates:
        if not candidate.exists():
            continue

        pricing_book = _load_pricing_file(candidate)
        if pricing_book:
            return pricing_book, str(candidate)

    if settings.pricing_remote_fallback:
        cache_file = _cache_path()
        cached, fresh = _load_cache(cache_file, ttl_hours=settings.pricing_cache_ttl_hours)
        if cached is not None and fresh:
            pricing_book = _parse_models_dev_payload(cached["payload"])
            if pricing_book:
                return pricing_book, f"models.dev cache ({cache_file})"

        remote_payload = _fetch_models_dev(
            settings.pricing_remote_url,
            timeout_seconds=settings.pricing_remote_timeout_seconds,
        )
        if remote_payload is not None:
            _write_cache(cache_file, remote_payload)
            pricing_book = _parse_models_dev_payload(remote_payload)
            if pricing_book:
                return pricing_book, f"models.dev ({settings.pricing_remote_url})"

        if cached is not None:
            pricing_book = _parse_models_dev_payload(cached["payload"])
            if pricing_book:
                return pricing_book, f"models.dev stale cache ({cache_file})"

    return {}, None


def calculate_usage_cost(usage: TokenUsage, pricing: ModelPricing) -> float:
    """Calculate USD cost from usage and per-million rates."""
    return (
        usage.input_tokens * pricing.input_per_million
        + usage.output_tokens * pricing.output_per_million
        + usage.cache_read_tokens * pricing.cache_read_per_million
        + usage.cache_write_tokens * pricing.cache_write_per_million
    ) / 1_000_000
