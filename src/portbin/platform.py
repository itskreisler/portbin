from __future__ import annotations

import os
import platform as _pyplatform
import sys
from pathlib import Path


def is_windows() -> bool:
    return sys.platform == "win32"


def info() -> dict[str, str]:
    return {
        "os": _pyplatform.system(),
        "release": _pyplatform.release(),
        "version": _pyplatform.version(),
        "arch": _pyplatform.machine(),
        "python": _pyplatform.python_version(),
        "python_exe": sys.executable,
        "cwd": str(Path.cwd()),
        "home": str(Path.home()),
    }


def is_admin() -> bool:
    if is_windows():
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return hasattr(os, "geteuid") and os.geteuid() == 0


def expand(value: str) -> str:
    value = os.path.expandvars(value)
    if value.startswith("~"):
        value = os.path.expanduser(value)
    return value


def resolve_path(value: str) -> Path:
    return Path(expand(value))


def expand_command(value: str) -> str:
    return " ".join(expand(part) for part in value.split())


def default_bin_dir() -> Path:
    return Path(os.path.join(str(Path.home()), ".local", "bin"))


def default_prefix() -> Path:
    return Path.home() / ".local" / "share" / "portbin" / "tools"


def translate_path(value: str, bin_dir: str | None = None, prefix: str | None = None) -> str:
    out = _norm(expand(value))
    if prefix:
        old = _norm(default_prefix())
        out = out.replace(old + "/", _norm(prefix) + "/").replace(old, _norm(prefix))
    if bin_dir:
        old = _norm(default_bin_dir())
        out = out.replace(old + "/", _norm(bin_dir) + "/").replace(old, _norm(bin_dir))
    return str(Path(out))


def translate_command(value: str, bin_dir: str | None = None, prefix: str | None = None) -> str:
    parts: list[str] = []
    for token in value.split():
        out = expand(token).replace("\\", "/")
        if prefix:
            old = _norm(default_prefix())
            out = out.replace(old + "/", _norm(prefix) + "/").replace(old, _norm(prefix))
        if bin_dir:
            old = _norm(default_bin_dir())
            out = out.replace(old + "/", _norm(bin_dir) + "/").replace(old, _norm(bin_dir))
        parts.append(out)
    return " ".join(parts)


def _norm(p: str) -> str:
    return str(Path(p)).replace("\\", "/")


def temp_dir() -> Path:
    if "TEMP" in os.environ:
        return Path(os.environ["TEMP"])
    if is_windows():
        return Path(os.environ.get("TMP", r"C:\Windows\Temp"))
    return Path("/tmp")


def temp_stage_dir() -> Path:
    return temp_dir() / "portbin"


def cleanup_temp() -> None:
    stage = temp_stage_dir()
    if stage.exists():
        import shutil

        shutil.rmtree(stage, ignore_errors=True)