from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from portbin import downloader, extractor, metadata, platform


def cache_dir() -> Path:
    return platform.temp_dir() / "portbin" / "pbx"


def record_path() -> Path:
    return platform.temp_dir() / "portbin" / "pbx.json"


def use(tool: str, args: list[str]) -> int:
    manifest = metadata.load_manifest(tool)
    pbx = manifest.get("pbx") or {}
    cache = cache_dir() / tool

    bin_dir = pbx.get("bin_dir")
    command = pbx.get("command")
    if bin_dir:
        if not args:
            raise SystemExit(
                f"'pbx use {tool}' requiere el nombre de un binario, ej: pbx use {tool} gcc --version"
            )
        binary, args = args[0], args[1:]
        rel = f"{bin_dir}/{binary}.exe"
    elif command:
        rel = command
    else:
        raise SystemExit(f"la herramienta '{tool}' no define 'pbx.command' ni 'pbx.bin_dir'")

    exe = _ensure_binary(cache, manifest, rel)
    _record(tool, pbx)
    return subprocess.run([str(exe), *args], cwd=os.getcwd()).returncode


def list_pbx() -> int:
    reg = _load_record().get("tools", {})
    out: list[str] = []
    seen: set[str] = set()
    for e in metadata._index_entries():
        m = e.get("manifest") or {}
        pbx = m.get("pbx")
        if not pbx:
            continue
        tool = m.get("tool") or metadata._tool_of(e.get("path", ""))
        if not tool or tool in seen:
            continue
        seen.add(tool)
        entry = reg.get(tool, {})
        how = f"bin_dir: {entry.get('bin_dir') or pbx['bin_dir']}" if pbx.get("bin_dir") else f"command: {pbx['command']}"
        if entry.get("bins"):
            out.append(f"{tool}  ({how})  binarios: {', '.join(entry['bins'])}")
        else:
            state = "cacheado" if (cache_dir() / tool).exists() else "-"
            out.append(f"{tool}  ({how})  {state}")
    if not out:
        print("sin herramientas con soporte pbx en el indice")
        return 0
    print("\n".join(out))
    return 0


def remove(tool: str) -> int:
    cache = cache_dir() / tool
    if cache.exists():
        shutil.rmtree(cache)
        print(f"  limpiado cache pbx: {cache}")
    else:
        print(f"  sin cache pbx para '{tool}'")
    _unrecord(tool)
    return 0


def clean_all() -> int:
    root = cache_dir()
    if root.exists():
        shutil.rmtree(root)
        print(f"  cache pbx limpiado: {root}")
    else:
        print("  sin cache pbx")
    _clear_record()
    return 0


def _ensure_binary(cache: Path, manifest: dict, rel_command: str) -> Path:
    command = (cache / rel_command).resolve()
    if command.exists():
        return command
    url = _download_url(manifest)
    if cache.exists():
        shutil.rmtree(cache)
    archive = platform.temp_dir() / "portbin" / _asset_name(url)
    if archive.exists():
        archive.unlink()
    print(f"  descargando {manifest.get('tool')} a cache temporal…")
    downloader.download(url, archive)
    extractor.extract(archive, cache)
    archive.unlink()
    if not command.exists():
        raise SystemExit(f"no se encontró '{rel_command}' tras preparar el cache de {manifest.get('tool')}")
    return command


def _download_url(manifest: dict) -> str:
    for step in manifest.get("steps", []):
        if step.get("type") == "download" and step.get("url"):
            return step["url"]
    raise SystemExit(f"el manifest de '{manifest.get('tool')}' no tiene paso 'download'")


def _asset_name(url: str) -> str:
    return url.split("?")[0].rstrip("/").split("/")[-1] or "archive.bin"


def _load_record() -> dict:
    p = record_path()
    if not p.exists():
        return {"tools": {}}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"tools": {}}


def _save_record(data: dict) -> None:
    record_path().parent.mkdir(parents=True, exist_ok=True)
    record_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def _record(tool: str, pbx: dict) -> None:
    data = _load_record()
    entry: dict = {}
    if pbx.get("bin_dir"):
        entry["bin_dir"] = pbx["bin_dir"]
        bins = (cache_dir() / tool / pbx["bin_dir"])
        if bins.is_dir():
            entry["bins"] = sorted(p.stem for p in bins.glob("*.exe"))
    elif pbx.get("command"):
        entry["command"] = pbx["command"]
    data.setdefault("tools", {})[tool] = entry
    _save_record(data)


def _unrecord(tool: str) -> None:
    data = _load_record()
    data.get("tools", {}).pop(tool, None)
    _save_record(data)


def _clear_record() -> None:
    _save_record({"tools": {}})
