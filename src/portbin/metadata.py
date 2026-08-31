from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib import request

from portbin import config as _cfg
from portbin import schema as _schema

CACHE_DIR = _cfg.root()
CACHE_MANIFESTS = CACHE_DIR / "manifests"


def _local_manifests_dir() -> Path | None:
    override = os.environ.get("PORTBIN_MANIFESTS")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        return None
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


def _normalize_index(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [e for e in raw if isinstance(e, dict)]
    if isinstance(raw, dict) and isinstance(raw.get("tools"), dict):
        return []
    return []


def _index_entries() -> list[dict[str, Any]]:
    local = _local_manifests_dir()
    if local:
        idx = local / "index.json"
        if idx.exists():
            with idx.open(encoding="utf-8") as fh:
                return _normalize_index(json.load(fh))
    url = _repo_url("manifests/index.json")
    if url:
        try:
            return _normalize_index(json.loads(_fetch(url)))
        except Exception:
            return []
    return []


def _entries_for_tool(entries: list[dict[str, Any]], tool: str) -> list[dict[str, Any]]:
    return [e for e in entries if _tool_of(e.get("path", "")) == tool]


def _tool_of(path: str) -> str:
    return Path(path).parent.name if Path(path).parts else ""


def _current_platform() -> str:
    return sys.platform


def _select_manifest(entries: list[dict[str, Any]], tool: str) -> dict[str, Any] | None:
    matches = _entries_for_tool(entries, tool)
    if not matches:
        return None
    for e in matches:
        if _platform_of(e.get("path", "")) == _current_platform():
            return e.get("manifest")
    for e in matches:
        if _platform_of(e.get("path", "")) == "universal":
            return e.get("manifest")
    return matches[0].get("manifest")


def _platform_of(path: str) -> str:
    return Path(path).stem


def index() -> list[dict[str, Any]]:
    return _index_entries()


def available_tools() -> list[str]:
    tools = {_tool_of(e.get("path", "")) for e in _index_entries()}
    return sorted(t for t in tools if t)


def load_manifest(tool: str) -> dict[str, Any]:
    local = _local_manifests_dir()
    if local:
        entries = _index_entries()
        selected = _select_manifest(entries, tool)
        if selected is not None:
            _schema.validate_manifest(selected, source=f"{tool} (index)")
            return selected
        matches = sorted(local.glob(f"{tool}/**/*.json"))
        for m in matches:
            if _platform_of(str(m.relative_to(local))) in (_current_platform(), "universal"):
                data = _read_json(m)
                _schema.validate_manifest(data, source=str(m))
                return data
        if matches:
            return _read_json(matches[0])
    url = _repo_url("manifests/index.json")
    if url:
        try:
            entries = _normalize_index(json.loads(_fetch(url)))
            selected = _select_manifest(entries, tool)
            if selected is not None:
                _schema.validate_manifest(selected, source=f"{tool} (index)")
                return selected
        except SystemExit:
            raise
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
