from __future__ import annotations

import json
from pathlib import Path

from portbin import platform


def root() -> Path:
    return Path.home() / ".config" / "portbin"


def path() -> Path:
    return root() / "portbin.json"


def defaults() -> dict[str, str]:
    return {
        "scope": "user",
        "bin_dir": str(platform.default_bin_dir()),
        "prefix": str(platform.default_prefix()),
        "repo": "",
    }


def load() -> dict[str, str]:
    cfg = defaults()
    if path().exists():
        with path().open(encoding="utf-8") as fh:
            cfg.update(json.load(fh))
    return cfg


def save(scope: str | None = None, bin_dir: str | None = None, prefix: str | None = None,
         repo: str | None = None) -> dict[str, str]:
    cfg = load()
    if scope:
        cfg["scope"] = scope
    if bin_dir:
        cfg["bin_dir"] = bin_dir
    if prefix:
        cfg["prefix"] = prefix
    if repo is not None:
        cfg["repo"] = repo
    path().parent.mkdir(parents=True, exist_ok=True)
    with path().open("w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
    return cfg


def merge(scope: str | None = None, bin_dir: str | None = None, prefix: str | None = None) -> dict[str, str]:
    cfg = load()
    return {
        "scope": scope or cfg["scope"],
        "bin_dir": bin_dir or cfg["bin_dir"],
        "prefix": prefix or cfg["prefix"],
    }