from __future__ import annotations

import io
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

try:
    import py7zr
except ImportError:  # pragma: no cover
    py7zr = None


def extract(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest)
    elif archive.suffix in (".tar", ".tgz", ".gz", ".bz2", ".xz"):
        with tarfile.open(archive) as tf:
            tf.extractall(dest, filter="data")
    elif is_7z(archive):
        if py7zr is None:  # pragma: no cover
            raise RuntimeError("py7zr no está instalado; no se puede extraer 7z")
        try:
            sz, fh = _open_7z(archive)
            try:
                sz.extractall(path=dest)
            finally:
                if fh is not None:
                    fh.close()
        except Exception:
            if not _is_sfx(archive):
                raise
            _run_sfx(archive, dest)
    else:
        raise ValueError(f"tipo de archivo no soportado: {archive}")
    _flatten(dest)


def is_7z(archive: Path) -> bool:
    name = archive.name
    if name.endswith(".7z.exe") or name.endswith(".7z"):
        return True
    try:
        head = archive.open("rb").read(6)
    except OSError:
        return False
    return head[:6] in (b"7z\xbc\xaf'\x1c", b"\x4dZ\x90\x00")


def list_contents(archive: Path) -> list[str]:
    """Lee el contenido de un archivo comprimido sin descomprimir (zip/tar/7z/SFX)."""
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            return zf.namelist()
    if archive.suffix in (".tar", ".tgz", ".gz", ".bz2", ".xz"):
        with tarfile.open(archive) as tf:
            return tf.getnames()
    if is_7z(archive):
        if py7zr is None:  # pragma: no cover
            raise RuntimeError("py7zr no está instalado; no se puede leer 7z")
        sz, fh = _open_7z(archive)
        try:
            return sz.getnames()
        finally:
            if fh is not None:
                fh.close()
    raise ValueError(f"tipo de archivo no soportado: {archive}")


def _open_7z(archive: Path):
    data = archive.read_bytes()
    offset = data.find(b"7z\xbc\xaf\x27\x1c")
    if offset < 0:
        raise ValueError(f"archivo 7z inválido: {archive}")
    return py7zr.SevenZipFile(io.BytesIO(data[offset:])), None


def _is_sfx(archive: Path) -> bool:
    return archive.name.lower().endswith(".exe")


def _run_sfx(archive: Path, dest: Path) -> None:
    res = subprocess.run([str(archive), f"-o{dest}", "-y"], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"SFX {archive.name} falló ({res.returncode}): {res.stderr.strip() or res.stdout.strip()}"
        )


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
