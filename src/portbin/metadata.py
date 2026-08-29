from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib import request

from portbin import config as _cfg

CACHE_DIR = _cfg.root()
CACHE_MANIFESTS = CACHE_DIR / "manifests"


def _local_manifests_dir() -> Path | None:
    override = os.environ.get("PORTBIN_MANIFESTS")
    if override:
        return Path(override)
    here = Path(__file__).resolve().parent
    candidates = [
        Path.cwd() / "manifests",
        here.parent.parent.parent / "manifests",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return None


def _repo_url(path: str) -> str | None:
    base = _cfg.load().get("repo")
    if not base:
        return None
    return base.rstrip("/") + "/" + path.lstrip("/")


def _fetch(url: str) -> str:
    req = request.Request(url, headers={"User-Agent": "portbin"})
    with request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def index() -> dict[str, Any]:
    local = _local_manifests_dir()
    if local:
        idx = local / "index.json"
        if idx.exists():
            with idx.open(encoding="utf-8") as fh:
                return json.load(fh)
    url = _repo_url("manifests/index.json")
    if url:
        try:
            return json.loads(_fetch(url))
        except Exception:
            return {"tools": {}}
    return {"tools": {}}


def available_tools() -> list[str]:
    return sorted(index().get("tools", {}).keys())


def load_manifest(tool: str) -> dict[str, Any]:
    local = _local_manifests_dir()
    if local:
        path = local / f"{tool}.json"
        if path.exists():
            return _read_json(path)
    cached = CACHE_MANIFESTS / f"{tool}.json"
    if cached.exists():
        with cached.open(encoding="utf-8") as fh:
            return json.load(fh)
    url = _repo_url(f"manifests/{tool}.json")
    if url:
        try:
            data = json.loads(_fetch(url))
            CACHE_MANIFESTS.mkdir(parents=True, exist_ok=True)
            with cached.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            return data
        except Exception as exc:
            raise SystemExit(f"no se pudo obtener manifest de {tool}: {exc}") from exc
    raise SystemExit(f"manifest no encontrado para {tool}")


def current_version_from(manifest: dict[str, Any]) -> str | None:
    for step in manifest.get("steps", []):
        if step.get("type") == "run" and step.get("capture"):
            return step.get("captured_version")
    return None


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)