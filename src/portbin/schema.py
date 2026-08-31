from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, ValidationError

Scope = Literal["user", "machine"]


class _StepBase(BaseModel):
    model_config = {
        "extra": "forbid",
        "title": "Step",
    }


class DownloadStep(_StepBase):
    """Descarga un archivo remoto a una ruta local."""

    type: Literal["download"]
    url: str = Field(description="URL del archivo a descargar.")
    dest: str = Field(description="Ruta local de destino (admite %TEMP%/, ~/ y vars de entorno).")


class VerifyStep(_StepBase):
    """Comprueba el checksum SHA-256 de un archivo descargado."""

    type: Literal["verify"]
    file: str = Field(description="Ruta del archivo a verificar.")
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$", description="Checksum SHA-256 esperado (64 hex).")


class ExtractStep(_StepBase):
    """Extrae un archivo comprimido (zip/tar/tgz/gz/bz2/xz/7z)."""

    type: Literal["extract"]
    archive: str = Field(description="Ruta del archivo comprimido. Directorio interno único se aplana.")
    dest: str = Field(description="Directorio de destino de la extracción.")


class MoveStep(_StepBase):
    """Mueve (o renombra) un archivo o directorio a su ubicación final."""

    type: Literal["move"]
    source: str = Field(description="Ruta de origen a mover.")
    dest: str = Field(description="Ruta final. Si existe, se reemplaza.")


class RunStep(_StepBase):
    """Ejecuta un comando tras la instalación. Con capture, guarda la primera línea de salida."""

    type: Literal["run"]
    command: str = Field(description="Comando a ejecutar (shell).")
    capture: bool = Field(default=False, description="Si true, guarda la primera línea de stdout como versión.")
    captured_version: str | None = Field(default=None, description="Versión capturada (relleno automático).")


class ShimStep(_StepBase):
    """Crea un shim .cmd en el bin dir que invoca el binario instalado."""

    type: Literal["shim"]
    name: str = Field(description="Nombre del shim (crea <name>.cmd).")
    command: str = Field(description="Comando que invoca el binario real.")
    scope: Scope = Field(default="machine", description="Alcance de variables/path relacionadas.")
    bin: str | None = Field(default=None, description="Override del directorio de shims.")


class PathStep(_StepBase):
    """Agrega un directorio al PATH del sistema o del usuario."""

    type: Literal["path"]
    value: str = Field(description="Directorio a agregar al PATH.")
    scope: Scope = Field(default="machine", description="Alcance: 'user' o 'machine' (requiere admin).")


class EnvStep(_StepBase):
    """Define una variable de entorno persistente."""

    type: Literal["env"]
    name: str = Field(description="Nombre de la variable de entorno.")
    value: str = Field(description="Valor de la variable.")
    scope: Scope = Field(default="machine", description="Alcance de la variable.")


Step = Annotated[
    DownloadStep | VerifyStep | ExtractStep | MoveStep | RunStep | ShimStep | PathStep | EnvStep,
    Field(discriminator="type"),
]


class Manifest(BaseModel):
    """Manifest de una herramienta portátil. Define pasos de instalación por plataforma.

    Estructura: manifests/<tool>/<plataforma>.json donde plataforma es
    'win32', 'linux', 'darwin' o 'universal'. index.json agrupa todos los manifests.
    """

    tool: str = Field(min_length=1, description="Nombre de la herramienta (identificador único).")
    platform: str | list[str] | None = Field(
        default=None, description="Plataforma(s) soportadas: win32/linux/darwin/universal."
    )
    version: str | None = Field(default=None, description="Versión o canal del build (ej. 'release').")
    note: str | None = Field(default=None, description="Nota informativa libre.")
    steps: list[Step] = Field(
        default_factory=list,
        description="Secuencia de pasos de instalación: download, verify, extract, move, run, shim, path, env.",
    )


def validate_manifest(data: dict[str, Any], *, source: str = "manifest") -> Manifest:
    try:
        return Manifest.model_validate(data)
    except ValidationError as exc:
        detail = "\n".join(
            f"  - {'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise SystemExit(f"manifest inválido ({source}):\n{detail}") from exc


def schema_json() -> str:
    import json

    return json.dumps(Manifest.model_json_schema(), indent=2)
