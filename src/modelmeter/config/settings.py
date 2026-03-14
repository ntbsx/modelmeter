"""Runtime settings for ModelMeter."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from modelmeter.common.version import get_base_version, get_product_version


class AppSettings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="MODELMETER_", extra="ignore")

    app_name: str = "modelmeter"
    opencode_data_dir: Path = Field(default=Path.home() / ".local" / "share" / "opencode")
    opencode_db_path: Path | None = None
    pricing_file: Path | None = None
    pricing_remote_fallback: bool = True
    pricing_remote_url: str = "https://models.dev/api.json"
    pricing_remote_timeout_seconds: int = Field(default=8, ge=1, le=60)
    pricing_cache_ttl_hours: int = Field(default=24, ge=1, le=168)
    update_check_enabled: bool = True
    update_check_url: str = (
        "https://gitlab.com/api/v4/projects/ntbsdev%2Fmodelmeter/releases/permalink/latest"
    )
    update_check_timeout_seconds: int = Field(default=8, ge=1, le=60)

    @property
    def app_version(self) -> str:
        return get_base_version()

    @property
    def app_runtime_version(self) -> str:
        return get_product_version()
