from pathlib import Path

from modelmeter.config.settings import AppSettings


def test_default_opencode_data_dir() -> None:
    settings = AppSettings()
    assert settings.opencode_data_dir == Path.home() / ".local" / "share" / "opencode"
