from __future__ import annotations

import hashlib
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: uv run python scripts/write_openapi_hash.py <openapi-path> <output-path>")
        return 1

    openapi_path = Path(sys.argv[1]).resolve()
    output_path = Path(sys.argv[2]).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256(openapi_path.read_bytes()).hexdigest()
    output_path.write_text(f"{digest}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
