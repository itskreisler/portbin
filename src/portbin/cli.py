from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from portbin import config, environment, installer, metadata, platform, registry


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="portbin", description="Gestor de herramientas declarativo con pasos.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Imprime detalle de cada paso")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Lista herramientas registradas")
    sub.add_parser("available", help="Lista manifests disponibles para instalar")
    p_cfg = sub.add_parser("config", help="Muestra o fija config por defecto (scope/bin-dir/prefix)")
    p_cfg.add_argument("--scope", choices=["user", "machine"])
    p_cfg.add_argument("--bin-dir")
    p_cfg.add_argument("--prefix")
    p_cfg.add_argument("--repo")
    sub.add_parser("index", help="Regenera index.json desde manifests locales")
    sub.add_parser("check", help="Muestra estado del entorno: plataforma, bin dir, registros")

    p_add = sub.add_parser("add", help="Instala una herramienta desde su manifest")
    p_add.add_argument("tool")
    p_add.add_argument("--yes", action="store_true", help="No preguntar")
    p_add.add_argument("--scope", choices=["user", "machine"], help="Fuerza scope de pasos path/env")
    p_add.add_argument("--bin-dir", help="Directorio de shims (default ~/.local/bin)")
    p_add.add_argument("--prefix", help="Raiz de payload (default ~/.local/share/portbin/tools)")

    p_upd = sub.add_parser("update", help="Reinstala una herramienta")
    p_upd.add_argument("tool")
    p_upd.add_argument("--yes", action="store_true", help="No preguntar")
    p_upd.add_argument("--scope", choices=["user", "machine"], help="Fuerza scope de pasos path/env")
    p_upd.add_argument("--bin-dir", help="Directorio de shims (default ~/.local/bin)")
    p_upd.add_argument("--prefix", help="Raiz de payload (default ~/.local/share/portbin/tools)")

    p_rm = sub.add_parser("remove", help="Desinstala una herramienta")
    p_rm.add_argument("tool")
    p_rm.add_argument("--yes", action="store_true", help="No preguntar")
    p_rm.add_argument("--bin-dir", help="Directorio de shims usado al instalar")
    p_rm.add_argument("--prefix", help="Raiz de payload usada al instalar")

    return parser


def _warn_if_system_write(manifest: dict, tool: str) -> None:
    touches_system = any(
        step.get("type") in ("path", "env") and step.get("scope", "machine") == "machine"
        for step in manifest.get("steps", [])
    )
    if touches_system and not environment.is_admin():
        print(
            f"[aviso] {tool}: pasos del manifest escriben en el PATH/variables de SISTEMA.\n"
            "        Si es necesario, ejecuta este comando como administrador.",
            file=sys.stderr,
        )


def _tool_ok(manifest: dict) -> bool:
    for s in manifest.get("steps", []):
        if s.get("type") == "shim":
            exe = platform.default_bin_dir() / f"{s['name']}.cmd"
            if not exe.exists():
                return False
        if s.get("type") == "move":
            if not platform.resolve_path(s["dest"]).exists():
                return False
    return True


def _cmd_add(tool: str, yes: bool, scope: str | None = None, bin_dir: str | None = None,
             prefix: str | None = None) -> int:
    opts = config.merge(scope, bin_dir, prefix)
    scope, bin_dir, prefix = opts["scope"], opts["bin_dir"], opts["prefix"]
    manifest = metadata.load_manifest(tool)
    installed = tool in registry.load().get("tools", {})
    if installed and _tool_ok(manifest):
        print(f"{tool} ya está instalado y OK. Usa `portbin update {tool}` o `remove`+`add`.")
        return 0
    if installed and not _tool_ok(manifest):
        print(f"{tool} registrado pero con archivos faltantes. Reparando...")
    _warn_if_system_write(manifest, tool)
    before = {
        platform.translate_path(s["value"], bin_dir, prefix): environment.path_contains(
            platform.translate_path(s["value"], bin_dir, prefix), scope=s.get("scope", "machine")
        )
        for s in manifest.get("steps", [])
        if s.get("type") == "path"
    }
    result = installer.install(manifest, confirm=not yes, scope=scope, bin_dir=bin_dir, prefix=prefix)
    if result:
        added = []
        for value, existed in before.items():
            if existed:
                continue
            if environment.path_contains(value, scope="machine") or environment.path_contains(value, scope="user"):
                added.append(value)
        registry.write(manifest["tool"], metadata.current_version_from(manifest) or "unknown", added)
        return 0
    return 1


def _cmd_update(tool: str, yes: bool, scope: str | None = None, bin_dir: str | None = None,
                prefix: str | None = None) -> int:
    opts = config.merge(scope, bin_dir, prefix)
    scope, bin_dir, prefix = opts["scope"], opts["bin_dir"], opts["prefix"]
    manifest = metadata.load_manifest(tool)
    _warn_if_system_write(manifest, tool)
    result = installer.install(manifest, confirm=not yes, scope=scope, bin_dir=bin_dir, prefix=prefix)
    if result:
        stored = registry.load().get("tools", {}).get(tool, {}).get("paths", [])
        registry.write(manifest["tool"], metadata.current_version_from(manifest) or "unknown", stored)
        return 0
    return 1


def _cmd_remove(tool: str, yes: bool, bin_dir: str | None = None, prefix: str | None = None) -> int:
    opts = config.merge(None, bin_dir, prefix)
    bin_dir, prefix = opts["bin_dir"], opts["prefix"]
    manifest = metadata.load_manifest(tool)
    _warn_if_system_write(manifest, tool)
    if not yes:
        answer = input(f"Quitar {tool}? [y/N] ")
        if answer.lower() not in ("y", "yes"):
            return 0

    data = registry.load()
    others = data.get("tools", {})
    removed = others.pop(tool, {})
    added_paths = set(removed.get("paths", []))
    shared = {v.lower() for info in others.values() for v in info.get("paths", [])}

    for value in added_paths:
        if value.rstrip("\\/").lower() in shared:
            continue
        print(f"  quitando del PATH: {value}")
        environment.remove_path(value, scope="machine") or environment.remove_path(value, scope="user")

    for s in manifest.get("steps", []):
        if s.get("type") == "env":
            print(f"  quitando variable: {s['name']}")
            environment.del_var(s["name"])

    installer.uninstall(manifest, confirm=True, bin_dir=bin_dir, prefix=prefix)
    registry.remove(tool)
    return 0


def _cmd_available() -> int:
    tools = metadata.available_tools()
    if not tools:
        print("sin tools en index (falta repo o manifests locales)")
        return 0
    rows = []
    for tool in tools:
        try:
            data = metadata.load_manifest(tool)
        except SystemExit:
            continue
        steps = data.get("steps", [])
        steps_desc = " -> ".join(s.get("type") for s in steps)
        has_sha = any(s.get("type") == "verify" for s in steps)
        state = "instalado" if tool in registry.load().get("tools", {}) else "disponible"
        rows.append((tool, steps_desc, "si" if has_sha else "no", state))
    widths = [max(len(r[i]) for r in rows) for i in range(4)]
    for tool, steps_desc, sha, state in rows:
        print(f"{tool:<{widths[0]}}  pasos:{steps_desc:<{widths[1]}}  checksum:{sha:<{widths[2]}}  {state}")
    return 0


def _cmd_index() -> int:
    import json

    local = metadata._local_manifests_dir()
    if local is None:
        print("no hay dir local de manifests (usa PORTBIN_MANIFESTS o corre desde el repo)")
        return 1
    tools = {p.stem: {"updated": "?"} for p in sorted(local.glob("*.json"))}
    data = {"tools": tools}
    idx = local / "index.json"
    with idx.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    print(f"index regenerado: {idx} ({len(tools)} tools)")
    return 0


def _cmd_check() -> int:
    import os

    bin_dir = platform.default_bin_dir()
    data = registry.load()
    tools = data.get("tools", {})
    cfg = config.load()

    for k, v in platform.info().items():
        print(f"{k:<12} {v}")
    print(f"{'admin':<12} {platform.is_admin()}")
    print(f"{'temp':<12} {platform.temp_dir()}")
    print(f"{'bin_dir':<12} {bin_dir}")
    print(f"{'prefix':<12} {cfg['prefix']}")
    print(f"{'scope':<12} {cfg['scope']}")
    print(f"{'repo':<12} {cfg['repo'] or '(no configurado)'}")
    print(f"{'config':<12} {config.path()}")

    print(f"{'bin_dir estado':<12} {'existe' if bin_dir.exists() else 'NO existe'}")
    if bin_dir.exists():
        for name in sorted(os.listdir(bin_dir)):
            full = bin_dir / name
            print(f"  {'dir ' if full.is_dir() else 'file'} {name}")

    print(f"{'registro':<12} {metadata.CACHE_DIR / 'tools.json'}  ({'existe' if (metadata.CACHE_DIR / 'tools.json').exists() else 'no existe'})")
    for name, info in sorted(tools.items()):
        print(f"  {name}: {info.get('current') or '?'}")
    return 0


def _cmd_list() -> int:
    data = registry.load()
    tools = data.get("tools", {})
    if not tools:
        print("sin herramientas registradas")
        return 0

    rows: list[tuple[str, str, str, str, str]] = []
    for name, info in sorted(tools.items()):
        manifest = None
        try:
            manifest = metadata.load_manifest(name)
        except SystemExit:
            pass
        version = (info.get("current") or "?").split()[0] if info.get("current") else "?"
        exe, payload, state = "?", "?", "ok"
        for s in (manifest or {}).get("steps", []):
            if s.get("type") == "shim":
                exe = str(platform.default_bin_dir() / f"{s['name']}.cmd")
            if s.get("type") == "move":
                payload = platform.expand(s["dest"])
        if manifest is None:
            state = "sin manifest"
        else:
            missing = [p for p in (exe, payload) if p != "?" and not platform.resolve_path(p).exists()]
            if missing:
                state = "faltan archivos"
        rows.append((name, version, exe, payload, state))

    widths = [max(len(r[i]) for r in rows) for i in range(5)]
    for name, version, exe, payload, state in rows:
        print(
            f"{name:<{widths[0]}}  {version:<{widths[1]}}  {exe:<{widths[2]}}  "
            f"{payload:<{widths[3]}}  {state}"
        )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.verbose:
        installer.verbose_on()
    if args.command == "add":
        return _cmd_add(args.tool, args.yes, args.scope, args.bin_dir, args.prefix)
    if args.command == "update":
        return _cmd_update(args.tool, args.yes, args.scope, args.bin_dir, args.prefix)
    if args.command == "remove":
        return _cmd_remove(args.tool, args.yes, args.bin_dir, args.prefix)
    if args.command == "list":
        return _cmd_list()
    if args.command == "check":
        return _cmd_check()
    if args.command == "available":
        return _cmd_available()
    if args.command == "config":
        cfg = config.save(
            getattr(args, "scope", None),
            getattr(args, "bin_dir", None),
            getattr(args, "prefix", None),
            getattr(args, "repo", None),
        )
        for k, v in cfg.items():
            print(f"{k} = {v}")
        return 0
    if args.command == "index":
        return _cmd_index()
    return 2