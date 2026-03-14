from pathlib import Path

from modelmeter.config.settings import AppSettings


def test_default_opencode_data_dir() -> None:
    settings = AppSettings()
    assert settings.opencode_data_dir == Path.home() / ".local" / "share" / "opencode"


def test_default_source_registry_file() -> None:
    settings = AppSettings()
    assert settings.source_registry_file == Path.home() / ".config" / "modelmeter" / "sources.json"
