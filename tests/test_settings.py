from pathlib import Path

from modelmeter.config.settings import AppSettings


def test_default_opencode_data_dir() -> None:
    settings = AppSettings()
    assert settings.opencode_data_dir == Path.home() / ".local" / "share" / "opencode"


def test_update_check_is_enabled_by_default() -> None:
    settings = AppSettings()
    assert settings.update_check_enabled is True
    assert (
        settings.update_check_url == "https://api.github.com/repos/ntbsx/modelmeter/releases/latest"
    )
