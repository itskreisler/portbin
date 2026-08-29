from __future__ import annotations

import json
from typing import Any

from portbin import metadata


def load() -> dict[str, Any]:
    path = metadata.CACHE_DIR / "tools.json"
    if not path.exists():
        return {"tools": {}}
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write(tool: str, version: str, paths: list[str] | None = None) -> None:
    data = load()
    data["tools"][tool] = {"current": version, "paths": paths or []}
    metadata.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with (metadata.CACHE_DIR / "tools.json").open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def remove(tool: str) -> None:
    data = load()
    data["tools"].pop(tool, None)
    with (metadata.CACHE_DIR / "tools.json").open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)