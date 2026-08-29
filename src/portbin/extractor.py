from __future__ import annotations

import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path


def extract(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest)
    elif archive.suffix in (".tar", ".tgz", ".gz", ".bz2", ".xz"):
        with tarfile.open(archive) as tf:
            tf.extractall(dest, filter="data")
    elif archive.suffix == ".7z" or archive.name.endswith(".7z"):
        _extract_7z(archive, dest)
    else:
        raise ValueError(f"tipo de archivo no soportado: {archive.suffix}")
    _flatten(dest)


def _extract_7z(archive: Path, dest: Path) -> None:
    try:
        import py7zr

        with py7zr.SevenZipFile(archive, mode="r") as z:
            z.extractall(path=dest)
        return
    except ImportError:
        pass

    for cmd_name in ("7z", "7za"):
        if shutil.which(cmd_name):
            res = subprocess.run([cmd_name, "x", "-y", f"-o{dest}", str(archive)], capture_output=True, text=True)
            if res.returncode == 0:
                return
            raise RuntimeError(f"error al extraer .7z con {cmd_name}: {res.stderr.strip()}")

    res = subprocess.run(["tar", "-xf", str(archive), "-C", str(dest)], capture_output=True, text=True)
    if res.returncode == 0:
        return
    raise RuntimeError(f"no se pudo extraer .7z: py7zr no instalado y tar/7z fallaron ({res.stderr.strip()})")


def _flatten(dest: Path) -> None:
    children = list(dest.iterdir())
    if len(children) != 1 or not children[0].is_dir():
        return
    inner = children[0]
    for item in list(inner.iterdir()):
        shutil.move(str(item), str(dest / item.name))
    inner.rmdir()


def move(source: Path, dest: Path) -> None:
    if dest.exists():
        if dest.is_dir():
            shutil.rmtree(dest)
        else:
            dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest))