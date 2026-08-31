from __future__ import annotations

import socket
import ssl
import subprocess
from collections.abc import Callable
from pathlib import Path
from urllib import request

from portbin import platform

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    tqdm = None


def download(url: str, dest: Path, progress: Callable[[bytes], None] | None = None) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if platform.is_windows() and _have_curl():
        try:
            _urllib_download(url, dest, progress)
            return dest
        except Exception:  # noqa: BLE001 - fallback a curl ante fallo de red/TLS
            pass
    _curl_download(url, dest)
    if progress:
        progress(b"")
    return dest


def _have_curl() -> bool:
    try:
        return subprocess.run(
            ["curl.exe", "--version"], capture_output=True, timeout=10
        ).returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def _curl_download(url: str, dest: Path) -> None:
    res = _run_curl(url, dest, resume=dest.exists() and dest.stat().st_size > 0)
    if res.returncode == 33 and dest.exists():
        dest.unlink()
        res = _run_curl(url, dest, resume=False)
    if res.returncode != 0:
        raise RuntimeError(f"curl falló ({res.returncode}): {res.stderr.strip() or res.stdout.strip()}")


def _run_curl(url: str, dest: Path, resume: bool) -> subprocess.CompletedProcess:
    command = [
        "curl.exe", "-sSL", "--fail", "--location",
        "--retry", "5", "--retry-delay", "2", "--retry-all-errors",
    ]
    if resume:
        command += ["-C", "-"]
    command += ["-o", str(dest), url]
    return subprocess.run(command, capture_output=True, text=True, timeout=600)


def _urllib_download(url: str, dest: Path, progress: Callable[[bytes], None] | None) -> None:
    socket.setdefaulttimeout(30)
    req = request.Request(url, headers={"User-Agent": "portbin"})
    context = _ssl_context()
    with request.urlopen(req, context=context) as resp, dest.open("wb") as fh:
        total = int(resp.headers.get("Content-Length") or 0)
        with _make_progress(total) as bar:
            while chunk := resp.read(64 * 1024):
                if progress:
                    progress(chunk)
                fh.write(chunk)
                if bar is not None:
                    bar.update(len(chunk))


def _make_progress(total: int):
    if tqdm is None or total <= 0:
        return _null_context()
    return tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc="Descargando",
        mininterval=0.1,
        dynamic_ncols=True,
    )


class _null_context:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


def _ssl_context() -> ssl.SSLContext | None:
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        return None
