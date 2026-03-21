"""Core data contracts for analytics responses."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, computed_field


def _default_str_list() -> list[str]:
    return []


def _default_dict_str_list() -> list[dict[str, str]]:
    return []


def _default_daily_usage_list() -> list[DailyUsage]:
    return []


def _default_model_usage_list() -> list[ModelUsage]:
    return []


def _default_provider_usage_list() -> list[ProviderUsage]:
    return []


def _default_project_usage_list() -> list[ProjectUsage]:
    return []


def _default_project_model_usage_list() -> list[ProjectModelUsage]:
    return []


def _default_project_session_usage_list() -> list[ProjectSessionUsage]:
    return []


def _default_session_usage_list() -> list[SessionUsage]:
    return []


def _default_session_model_usage_list() -> list[SessionModelUsage]:
    return []


def _default_live_model_usage_list() -> list[LiveModelUsage]:
    return []


def _default_live_tool_usage_list() -> list[LiveToolUsage]:
    return []


class SessionSummary(BaseModel):
    """Session summary for selection UI."""

    session_id: str
    title: str | None = None
    directory: str | None = None
    project_id: str | None = None
    project_name: str | None = None
    time_created: int = Field(default=0, ge=0)
    time_updated: int = Field(default=0, ge=0)
    time_archived: int | None = None
    message_count: int = Field(default=0, ge=0)
    model_count: int = Field(default=0, ge=0)
    token_count: int = Field(default=0, ge=0)
    cost_usd: float | None = None
    is_active: bool = False


class TokenUsage(BaseModel):
    """Token usage counters."""

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cache_read_tokens: int = Field(default=0, ge=0)
    cache_write_tokens: int = Field(default=0, ge=0)

    @computed_field
    @property
    def total_tokens(self) -> int:
        """Total tokens across all token categories."""
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )


class DailyUsage(BaseModel):
    """Daily aggregate usage."""

    day: date
    usage: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    cost_usd: float | None = None


class SummaryResponse(BaseModel):
    """Top-level summary response contract."""

    usage: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    window_days: int | None = Field(default=None, ge=1)
    cost_usd: float | None = None
    pricing_source: str | None = None
    source_scope: str | None = None
    sources_considered: list[str] = Field(default_factory=_default_str_list)
    sources_succeeded: list[str] = Field(default_factory=_default_str_list)
    sources_failed: list[dict[str, str]] = Field(default_factory=_default_dict_str_list)


class DailyResponse(BaseModel):
    """Daily time-series response contract."""

    window_days: int | None = Field(default=None, ge=1)
    totals: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    total_cost_usd: float | None = None
    pricing_source: str | None = None
    daily: list[DailyUsage] = Field(default_factory=_default_daily_usage_list)
    source_scope: str | None = None
    sources_considered: list[str] = Field(default_factory=_default_str_list)
    sources_succeeded: list[str] = Field(default_factory=_default_str_list)
    sources_failed: list[dict[str, str]] = Field(default_factory=_default_dict_str_list)


class ModelUsage(BaseModel):
    """Per-model usage aggregate."""

    model_id: str
    provider: str | None = None
    usage: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    total_interactions: int = Field(default=0, ge=0)
    cost_usd: float | None = None
    has_pricing: bool = False


class ModelsResponse(BaseModel):
    """Top models usage response contract."""

    window_days: int | None = Field(default=None, ge=1)
    models_offset: int = Field(default=0, ge=0)
    models_limit: int | None = Field(default=None, ge=1)
    models_returned: int = Field(default=0, ge=0)
    total_models: int = Field(default=0, ge=0)
    totals: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    total_cost_usd: float | None = None
    pricing_source: str | None = None
    priced_models: int = Field(default=0, ge=0)
    unpriced_models: int = Field(default=0, ge=0)
    models: list[ModelUsage] = Field(default_factory=_default_model_usage_list)
    source_scope: str | None = None
    sources_considered: list[str] = Field(default_factory=_default_str_list)
    sources_succeeded: list[str] = Field(default_factory=_default_str_list)
    sources_failed: list[dict[str, str]] = Field(default_factory=_default_dict_str_list)


class ModelDetailResponse(BaseModel):
    """Single model detail response contract."""

    model_id: str
    provider: str
    window_days: int | None = Field(default=None, ge=1)
    usage: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    total_interactions: int = Field(default=0, ge=0)
    cost_usd: float | None = None
    pricing_source: str | None = None
    daily: list[DailyUsage] = Field(default_factory=_default_daily_usage_list)
    source_scope: str | None = None
    sources_considered: list[str] = Field(default_factory=_default_str_list)
    sources_succeeded: list[str] = Field(default_factory=_default_str_list)
    sources_failed: list[dict[str, str]] = Field(default_factory=_default_dict_str_list)


class ProviderUsage(BaseModel):
    """Per-provider usage aggregate."""

    provider: str
    usage: TokenUsage
    total_models: int = Field(default=0, ge=0)
    total_interactions: int = Field(default=0, ge=0)
    cost_usd: float | None = None
    has_pricing: bool = False


class ProvidersResponse(BaseModel):
    """Top providers usage response contract."""

    window_days: int | None = Field(default=None, ge=1)
    providers_offset: int = Field(default=0, ge=0)
    providers_limit: int | None = Field(default=None, ge=1)
    providers_returned: int = Field(default=0, ge=0)
    total_providers: int = Field(default=0, ge=0)
    totals: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    total_cost_usd: float | None = None
    pricing_source: str | None = None
    providers: list[ProviderUsage] = Field(default_factory=_default_provider_usage_list)
    source_scope: str | None = None
    sources_considered: list[str] = Field(default_factory=_default_str_list)
    sources_succeeded: list[str] = Field(default_factory=_default_str_list)
    sources_failed: list[dict[str, str]] = Field(default_factory=_default_dict_str_list)


class ProjectUsage(BaseModel):
    """Per-project usage aggregate."""

    project_id: str
    project_name: str
    project_path: str | None = None
    usage: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    total_interactions: int = Field(default=0, ge=0)
    cost_usd: float | None = None
    has_pricing: bool = False
    sources: list[str] = Field(default_factory=_default_str_list)


class ProjectModelUsage(BaseModel):
    """Per-model usage within a single project, for date insights."""

    project_id: str
    model_id: str
    provider: str | None = None
    usage: TokenUsage
    total_interactions: int = Field(default=0, ge=0)
    cost_usd: float | None = None
    has_pricing: bool = False


class ProjectsResponse(BaseModel):
    """Top projects usage response contract."""

    window_days: int | None = Field(default=None, ge=1)
    projects_offset: int = Field(default=0, ge=0)
    projects_limit: int | None = Field(default=None, ge=1)
    projects_returned: int = Field(default=0, ge=0)
    total_projects: int = Field(default=0, ge=0)
    totals: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    total_cost_usd: float | None = None
    pricing_source: str | None = None
    projects: list[ProjectUsage] = Field(default_factory=_default_project_usage_list)
    source_scope: str | None = None
    sources_considered: list[str] = Field(default_factory=_default_str_list)
    sources_succeeded: list[str] = Field(default_factory=_default_str_list)
    sources_failed: list[dict[str, str]] = Field(default_factory=_default_dict_str_list)


class ProjectSessionUsage(BaseModel):
    """Per-session usage row for a project detail view."""

    session_id: str
    title: str | None = None
    directory: str | None = None
    last_updated_ms: int = Field(default=0, ge=0)
    usage: TokenUsage
    total_interactions: int = Field(default=0, ge=0)
    cost_usd: float | None = None
    has_pricing: bool = False


class ProjectDetailResponse(BaseModel):
    """Single project detail response contract."""

    project_id: str
    project_name: str
    project_path: str | None = None
    window_days: int | None = Field(default=None, ge=1)
    usage: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    sessions_offset: int = Field(default=0, ge=0)
    sessions_limit: int | None = Field(default=None, ge=1)
    sessions_returned: int = Field(default=0, ge=0)
    total_interactions: int = Field(default=0, ge=0)
    total_cost_usd: float | None = None
    pricing_source: str | None = None
    sessions: list[ProjectSessionUsage] = Field(default_factory=_default_project_session_usage_list)
    source_scope: str | None = None
    sources_considered: list[str] = Field(default_factory=_default_str_list)
    sources_succeeded: list[str] = Field(default_factory=_default_str_list)
    sources_failed: list[dict[str, str]] = Field(default_factory=_default_dict_str_list)


class LiveModelUsage(BaseModel):
    """Live model usage row."""

    model_id: str
    usage: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    total_interactions: int = Field(default=0, ge=0)
    cost_usd: float | None = None


class LiveToolUsage(BaseModel):
    """Live tool usage row."""

    tool_name: str
    total_calls: int = Field(default=0, ge=0)


class LiveActiveSession(BaseModel):
    """Active session metadata in live snapshot."""

    session_id: str
    title: str | None = None
    project_id: str | None = None
    project_name: str | None = None
    directory: str | None = None
    last_updated_ms: int = Field(default=0, ge=0)
    is_active: bool = False


class LiveSnapshotResponse(BaseModel):
    """Live snapshot response contract."""

    generated_at_ms: int = Field(default=0, ge=0)
    window_minutes: int = Field(default=60, ge=1)
    token_source: str
    total_interactions: int = Field(default=0, ge=0)
    total_sessions: int = Field(default=0, ge=0)
    usage: TokenUsage
    cost_usd: float | None = None
    pricing_source: str | None = None
    active_session: LiveActiveSession | None = None
    top_models: list[LiveModelUsage] = Field(default_factory=_default_live_model_usage_list)
    top_tools: list[LiveToolUsage] = Field(default_factory=_default_live_tool_usage_list)


class UpdateCheckResponse(BaseModel):
    """Update check response contract."""

    current_version: str
    latest_version: str | None = None
    update_available: bool = False
    release_tag: str | None = None
    release_url: str | None = None
    checked_at_ms: int = Field(default=0, ge=0)
    error: str | None = None


class SessionModelUsage(BaseModel):
    """Per-model usage within a single session, for date insights."""

    model_id: str
    provider: str | None = None
    usage: TokenUsage
    total_interactions: int = Field(default=0, ge=0)
    cost_usd: float | None = None
    has_pricing: bool = False


class SessionUsage(BaseModel):
    """Per-session usage for a single day."""

    session_id: str
    title: str | None = None
    project_id: str | None = None
    project_name: str | None = None
    models: list[SessionModelUsage] = Field(default_factory=_default_session_model_usage_list)
    total_tokens: int = Field(default=0, ge=0)
    total_interactions: int = Field(default=0, ge=0)
    cost_usd: float | None = None
    has_pricing: bool = False
    started_at: str | None = None


class DateInsightsResponse(BaseModel):
    """Date-specific usage breakdown contract."""

    day: date
    timezone_offset_minutes: int = Field(default=0, ge=-840, le=840)
    usage: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    total_interactions: int = Field(default=0, ge=0)
    cost_usd: float | None = None
    pricing_source: str | None = None
    models: list[ModelUsage] = Field(default_factory=_default_model_usage_list)
    providers: list[ProviderUsage] = Field(default_factory=_default_provider_usage_list)
    projects: list[ProjectUsage] = Field(default_factory=_default_project_usage_list)
    project_models: list[ProjectModelUsage] = Field(
        default_factory=_default_project_model_usage_list
    )
    sessions: list[SessionUsage] = Field(default_factory=_default_session_usage_list)
    source_scope: str | None = None
    sources_considered: list[str] = Field(default_factory=_default_str_list)
    sources_succeeded: list[str] = Field(default_factory=_default_str_list)
    sources_failed: list[dict[str, str]] = Field(default_factory=_default_dict_str_list)
