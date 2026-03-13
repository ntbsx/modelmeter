"""Core data contracts for analytics responses."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, computed_field


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


class DailyResponse(BaseModel):
    """Daily time-series response contract."""

    window_days: int | None = Field(default=None, ge=1)
    totals: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    total_cost_usd: float | None = None
    pricing_source: str | None = None
    daily: list[DailyUsage] = []


class ModelUsage(BaseModel):
    """Per-model usage aggregate."""

    model_id: str
    usage: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    total_interactions: int = Field(default=0, ge=0)
    cost_usd: float | None = None
    has_pricing: bool = False


class ModelsResponse(BaseModel):
    """Top models usage response contract."""

    window_days: int | None = Field(default=None, ge=1)
    totals: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    total_cost_usd: float | None = None
    pricing_source: str | None = None
    priced_models: int = Field(default=0, ge=0)
    unpriced_models: int = Field(default=0, ge=0)
    models: list[ModelUsage] = []


class ModelDetailResponse(BaseModel):
    """Single model detail response contract."""

    model_id: str
    window_days: int | None = Field(default=None, ge=1)
    usage: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    total_interactions: int = Field(default=0, ge=0)
    cost_usd: float | None = None
    pricing_source: str | None = None
    daily: list[DailyUsage] = []


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


class ProjectsResponse(BaseModel):
    """Top projects usage response contract."""

    window_days: int | None = Field(default=None, ge=1)
    totals: TokenUsage
    total_sessions: int = Field(default=0, ge=0)
    total_cost_usd: float | None = None
    pricing_source: str | None = None
    projects: list[ProjectUsage] = []


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
    sessions: list[ProjectSessionUsage] = []


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
    top_models: list[LiveModelUsage] = []
    top_tools: list[LiveToolUsage] = []
