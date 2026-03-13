from __future__ import annotations

import json
import sys
from pathlib import Path

from modelmeter.api.app import create_app


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: uv run python scripts/export_openapi.py <output-path>")
        return 1

    output_path = Path(sys.argv[1]).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    app = create_app()
    schema = app.openapi()
    output_path.write_text(f"{json.dumps(schema, indent=2, sort_keys=True)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
