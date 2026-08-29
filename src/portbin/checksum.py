from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path, chunk: int = 64 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def verify(path: Path, expected: str) -> bool:
    return sha256_file(path).lower() == expected.lower()