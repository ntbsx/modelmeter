from __future__ import annotations

from pathlib import Path


def test_vite_proxy_preserves_api_prefix() -> None:
    config_path = Path(__file__).resolve().parent.parent / "web" / "vite.config.ts"
    content = config_path.read_text(encoding="utf-8")

    assert "'/api'" in content
    assert "target: 'http://127.0.0.1:8000'" in content
    assert "path.replace(/^\\/api/, '')" not in content
