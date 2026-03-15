"""Fetch current usage/status from AI provider APIs."""

from __future__ import annotations

import httpx

from modelmeter.config.settings import AppSettings
from modelmeter.core.models import (
    ProvidersUsageResponse,
    ProviderRateLimits,
    ProviderStatusResponse,
)

_ANTHROPIC_MODELS_URL = "https://api.anthropic.com/v1/models"
_ANTHROPIC_VERSION = "2023-06-01"

_OPENAI_MODELS_URL = "https://api.openai.com/v1/models"


def _fetch_anthropic_status(api_key: str, timeout: int) -> ProviderStatusResponse:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": _ANTHROPIC_VERSION,
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(_ANTHROPIC_MODELS_URL, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code == 401:
            return ProviderStatusResponse(
                provider="anthropic",
                configured=True,
                status="error",
                error="Invalid API key (401 Unauthorized)",
            )
        return ProviderStatusResponse(
            provider="anthropic",
            configured=True,
            status="error",
            error=f"HTTP {status_code}: {exc.response.text[:200]}",
        )
    except httpx.RequestError as exc:
        return ProviderStatusResponse(
            provider="anthropic",
            configured=True,
            status="error",
            error=f"Request failed: {exc}",
        )

    data = response.json()
    model_ids = [m.get("id", "") for m in data.get("data", []) if m.get("id")]

    rate_limits = ProviderRateLimits(
        requests_limit=_int_header(response, "anthropic-ratelimit-requests-limit"),
        requests_remaining=_int_header(response, "anthropic-ratelimit-requests-remaining"),
        tokens_limit=_int_header(response, "anthropic-ratelimit-tokens-limit"),
        tokens_remaining=_int_header(response, "anthropic-ratelimit-tokens-remaining"),
    )

    return ProviderStatusResponse(
        provider="anthropic",
        configured=True,
        status="ok",
        models_count=len(model_ids),
        models=model_ids,
        rate_limits=rate_limits,
    )


def _fetch_openai_status(api_key: str, timeout: int) -> ProviderStatusResponse:
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(_OPENAI_MODELS_URL, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code == 401:
            return ProviderStatusResponse(
                provider="openai",
                configured=True,
                status="error",
                error="Invalid API key (401 Unauthorized)",
            )
        return ProviderStatusResponse(
            provider="openai",
            configured=True,
            status="error",
            error=f"HTTP {status_code}: {exc.response.text[:200]}",
        )
    except httpx.RequestError as exc:
        return ProviderStatusResponse(
            provider="openai",
            configured=True,
            status="error",
            error=f"Request failed: {exc}",
        )

    data = response.json()
    model_ids = sorted({m.get("id", "") for m in data.get("data", []) if m.get("id")})

    rate_limits = ProviderRateLimits(
        requests_limit=_int_header(response, "x-ratelimit-limit-requests"),
        requests_remaining=_int_header(response, "x-ratelimit-remaining-requests"),
        tokens_limit=_int_header(response, "x-ratelimit-limit-tokens"),
        tokens_remaining=_int_header(response, "x-ratelimit-remaining-tokens"),
    )

    return ProviderStatusResponse(
        provider="openai",
        configured=True,
        status="ok",
        models_count=len(model_ids),
        models=model_ids,
        rate_limits=rate_limits,
    )


def _int_header(response: httpx.Response, header: str) -> int | None:
    value = response.headers.get(header)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def get_providers_usage(settings: AppSettings) -> ProvidersUsageResponse:
    """Fetch current usage/status from configured AI providers."""
    timeout = settings.provider_usage_timeout_seconds
    providers: list[ProviderStatusResponse] = []

    if settings.anthropic_api_key:
        providers.append(_fetch_anthropic_status(settings.anthropic_api_key, timeout))
    else:
        providers.append(ProviderStatusResponse(provider="anthropic", configured=False))

    if settings.openai_api_key:
        providers.append(_fetch_openai_status(settings.openai_api_key, timeout))
    else:
        providers.append(ProviderStatusResponse(provider="openai", configured=False))

    return ProvidersUsageResponse(providers=providers)
