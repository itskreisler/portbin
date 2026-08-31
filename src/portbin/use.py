from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from portbin import downloader, extractor, metadata, platform


def cache_dir() -> Path:
    return platform.temp_dir() / "portbin" / "pbx"


def use(tool: str, args: list[str]) -> int:
    manifest = metadata.load_manifest(tool)
    pbx = manifest.get("pbx")
    if not pbx or not pbx.get("command"):
        raise SystemExit(f"la herramienta '{tool}' no define 'pbx.command'")

    cache = cache_dir() / tool
    command = _ensure_binary(cache, manifest, pbx["command"])
    return subprocess.run([str(command), *args], cwd=os.getcwd()).returncode


def remove(tool: str) -> int:
    cache = cache_dir() / tool
    if cache.exists():
        shutil.rmtree(cache)
        print(f"  limpiado cache pbx: {cache}")
    else:
        print(f"  sin cache pbx para '{tool}'")
    return 0


def clean_all() -> int:
    root = cache_dir()
    if not root.exists():
        print("  sin cache pbx")
        return 0
    shutil.rmtree(root)
    print(f"  cache pbx limpiado: {root}")
    return 0


def _ensure_binary(cache: Path, manifest: dict, rel_command: str) -> Path:
    command = (cache / rel_command).resolve()
    if command.exists():
        return command
    url = _download_url(manifest)
    if cache.exists():
        shutil.rmtree(cache)
    archive = platform.temp_dir() / "portbin" / f"pbx-{cache.name}.zip"
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
