from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"

SPECS = ["portbin.spec", "pbx.spec"]


def main() -> None:
    for spec in SPECS:
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", spec, "--noconfirm", "--clean"],
            cwd=ROOT,
            check=True,
        )
    exes = sorted(p.name for p in DIST.glob("*.exe"))
    print(f"build OK: {', '.join(exes)}")


if __name__ == "__main__":
    main()
