from __future__ import annotations

import os
import subprocess
from typing import Any

from portbin import checksum, downloader, environment, extractor, platform

HANDLERS: dict[str, Any] = {}
VERBOSE = False


def verbose_on() -> None:
    global VERBOSE
    VERBOSE = True


def step(step_type: str):
    def deco(fn):
        HANDLERS[step_type] = fn
        return fn

    return deco


def run(manifest: dict[str, Any], confirm: bool = True, scope: str | None = None,
        bin_dir: str | None = None, prefix: str | None = None) -> bool:
    steps = manifest.get("steps", [])
    cloned = False
    if scope or bin_dir or prefix:
        cloned = True
        steps = [dict(s) for s in steps]
        for s in steps:
            if scope and s.get("type") in ("path", "env"):
                s["scope"] = scope
            if s.get("type") == "move":
                if "dest" in s:
                    s["dest"] = platform.translate_path(s["dest"], bin_dir, prefix)
                if "source" in s:
                    s["source"] = platform.translate_path(s["source"], bin_dir, prefix)
            elif s.get("type") == "extract":
                s["dest"] = platform.translate_path(s["dest"], bin_dir, prefix)
            elif s.get("type") == "shim":
                if "command" in s:
                    s["command"] = platform.translate_command(s["command"], bin_dir, prefix)
                if bin_dir:
                    s["bin"] = bin_dir
            elif s.get("type") == "run" and bin_dir:
                s["_bin_dir"] = bin_dir
            elif s.get("type") == "path":
                s["value"] = platform.translate_path(s["value"], bin_dir, prefix)
    for i, s in enumerate(steps):
        handler = HANDLERS.get(s.get("type"))
        if handler is None:
            raise SystemExit(f"step {i} tipo desconocido: {s.get('type')}")
        print(f"[{i}] {s.get('type')}: {s}")
        if confirm:
            answer = input("  ejecutar? [Y/n] ")
            if answer.lower() in ("n", "no"):
                continue
        handler(s, manifest)
    if cloned:
        for orig, copy in zip(manifest.get("steps", []), steps, strict=True):
            if copy.get("captured_version") is not None:
                orig["captured_version"] = copy["captured_version"]
            if "_bin_dir" in copy:
                orig.pop("_bin_dir", None)
    platform.cleanup_temp()
    return True


@step("download")
def _download(s: dict, m: dict) -> None:
    dest = platform.expand(s["dest"])
    path = platform.resolve_path(dest)

    def progress(chunk: bytes) -> None:
        if VERBOSE:
            print(f"  +{len(chunk):,} bytes -> {path}")

    downloader.download(s["url"], path, progress=progress if VERBOSE else None)
    if VERBOSE:
        print(f"  descarga completa: {path.stat().st_size:,} bytes")


@step("verify")
def _verify(s: dict, m: dict) -> None:
    path = platform.expand(s["file"])
    if not checksum.verify(platform.resolve_path(path), s["sha256"]):
        raise SystemExit(f"checksum inválido: {path}")


@step("extract")
def _extract(s: dict, m: dict) -> None:
    archive = platform.expand(s["archive"])
    dest = platform.expand(s["dest"])
    extractor.extract(platform.resolve_path(archive), platform.resolve_path(dest))


@step("move")
def _move(s: dict, m: dict) -> None:
    extractor.move(platform.resolve_path(platform.expand(s["source"])), platform.resolve_path(platform.expand(s["dest"])))


@step("run")
def _run(s: dict, m: dict) -> None:
    cmd = platform.expand_command(s["command"])
    env = None
    if s.get("_bin_dir"):
        env = dict(os.environ)
        env["PATH"] = platform.expand(s["_bin_dir"]) + os.pathsep + env.get("PATH", "")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
    if s.get("capture"):
        if res.returncode == 0 and res.stdout:
            s["captured_version"] = res.stdout.strip().splitlines()[0]


@step("shim")
def _shim(s: dict, m: dict) -> None:
    bin_dir = platform.resolve_path(s["bin"]) if s.get("bin") else platform.default_bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)
    exe = f"{s['name']}.cmd"
    content = f"@echo off\r\n{platform.expand_command(s['command'])} %*\r\n"
    (bin_dir / exe).write_text(content, encoding="utf-8")


@step("path")
def _path(s: dict, m: dict) -> None:
    environment.add_path(platform.expand(s["value"]), scope=s.get("scope", "machine"))


@step("env")
def _env(s: dict, m: dict) -> None:
    environment.set_var(s["name"], platform.expand(s["value"]), scope=s.get("scope", "machine"))


def uninstall(manifest: dict[str, Any], confirm: bool = True, bin_dir: str | None = None,
              prefix: str | None = None) -> bool:
    import shutil

    for s in reversed(manifest.get("steps", [])):
        t = s.get("type")
        if t == "move":
            dest = platform.resolve_path(platform.translate_path(s["dest"], bin_dir, prefix))
            if dest.exists():
                print(f"  borrando {dest}")
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            parent = dest.parent
            if parent.exists():
                try:
                    parent.rmdir()
                except OSError:
                    pass
        elif t == "extract":
            dest = platform.resolve_path(platform.translate_path(s["dest"], bin_dir, prefix))
            if dest.exists():
                print(f"  borrando {dest}")
                shutil.rmtree(dest)
        elif t == "shim":
            target = bin_dir if bin_dir else (s.get("bin") if s.get("bin") else platform.default_bin_dir())
            bin_dir_p = platform.resolve_path(target)
            exe = bin_dir_p / f"{s['name']}.cmd"
            if exe.exists():
                print(f"  borrando {exe}")
                exe.unlink()
    return True


install = run