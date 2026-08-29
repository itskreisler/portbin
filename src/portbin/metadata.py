from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib import request

from pydantic import BaseModel, ConfigDict, Field

from portbin import config as _cfg


class StepModel(BaseModel):
    """Modelo Pydantic para un paso individual del manifest."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(description="Tipo de paso: download, verify, extract, move, shim, run, path, env")
    platform: list[str] | str | None = Field(
        default=None, description="Plataformas aplicables al paso (ej: ['win32', 'linux'])"
    )
    url: str | None = Field(default=None, description="URL remota de descarga")
    dest: str | None = Field(default=None, description="Ruta de destino para descargar, extraer o mover")
    source: str | None = Field(default=None, description="Ruta de origen para mover o copiar")
    archive: str | None = Field(default=None, description="Ruta del archivo comprimido a extraer")
    file: str | None = Field(default=None, description="Ruta del archivo a verificar checksum")
    sha256: str | None = Field(default=None, description="Hash SHA256 esperado")
    name: str | None = Field(default=None, description="Nombre del ejecutable del shim o variable de entorno")
    command: str | None = Field(default=None, description="Comando a ejecutar o invocar")
    capture: bool | None = Field(default=None, description="Si es True captura la versión desde stdout")
    value: str | None = Field(default=None, description="Valor de ruta para PATH o variable de entorno")
    scope: str | None = Field(default=None, description="Alcance de configuración: 'user' o 'machine'")


class ManifestModel(BaseModel):
    """Modelo Pydantic que valida la estructura completa del manifest de una herramienta."""

    model_config = ConfigDict(extra="allow")

    tool: str = Field(description="Nombre identificador de la herramienta")
    platform: list[str] | str | None = Field(default=None, description="Plataformas soportadas")
    steps: list[StepModel] = Field(default_factory=list, description="Lista de pasos ordenados a ejecutar")


def validate_manifest(data: dict[str, Any]) -> dict[str, Any]:
    model = ManifestModel.model_validate(data)
    return model.model_dump(exclude_unset=True)

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
    current_os = sys.platform
    rel_paths = [
        f"{tool}/{current_os}.json",
        f"{tool}/universal.json",
        f"{tool}.json",
    ]
    if current_os.startswith("linux"):
        rel_paths.insert(1, f"{tool}/linux.json")
    elif current_os == "win32":
        rel_paths.insert(1, f"{tool}/win32.json")

    if local:
        for rel in rel_paths:
            path = local / rel
            if path.exists():
                return _read_json(path)

    for rel in rel_paths:
        cached = CACHE_MANIFESTS / rel
        if cached.exists():
            with cached.open(encoding="utf-8") as fh:
                return json.load(fh)

    for rel in rel_paths:
        url = _repo_url(f"manifests/{rel}")
        if url:
            try:
                data = json.loads(_fetch(url))
                cached = CACHE_MANIFESTS / rel
                cached.parent.mkdir(parents=True, exist_ok=True)
                with cached.open("w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=2)
                return data
            except Exception:
                continue

    raise SystemExit(f"manifest no encontrado para {tool}")


def current_version_from(manifest: dict[str, Any]) -> str | None:
    for step in manifest.get("steps", []):
        if step.get("type") == "run" and step.get("capture"):
            return step.get("captured_version")
    return None


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
        return validate_manifest(data)