from __future__ import annotations

import shutil
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
    else:
        raise ValueError(f"tipo de archivo no soportado: {archive.suffix}")
    _flatten(dest)


def _flatten(dest: Path) -> None:
    children = list(dest.iterdir())
    if len(children) != 1 or not children[0].is_dir():
        return
    inner = children[0]
    if not (inner / "bin").is_dir() and not any((inner / n).is_file() for n in ("bin", "bin.exe")):
        return
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