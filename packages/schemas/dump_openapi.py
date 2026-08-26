"""Dump the live OpenAPI document into this package."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    from finehelper_api.main import app

    out = Path(__file__).with_name("openapi.json")
    out.write_text(json.dumps(app.openapi(), indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
