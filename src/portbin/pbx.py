from __future__ import annotations

import argparse
import sys

from portbin import use


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pbx",
        description="Ejecuta temporalmente herramientas de portbin desde el directorio temporal sin tocar el PATH.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    u = sub.add_parser("use", help="descarga a temp (si falta) y ejecuta la herramienta.")
    u.add_argument("tool", help="Nombre de la herramienta (ej. fresh).")
    u.add_argument("args", nargs=argparse.REMAINDER, help="Argumentos pasados al binario.")

    r = sub.add_parser("remove", help="Elimina el cache temporal de una herramienta.")
    r.add_argument("tool", help="Nombre de la herramienta.")

    c = sub.add_parser("clean", help="Elimina el cache temporal (cache = todo, o el nombre de una herramienta).")
    c.add_argument("target", help="'cache' para borrar todo, o el nombre de una herramienta.")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "use":
        return use.use(args.tool, args.args)
    if args.command == "remove":
        return use.remove(args.tool)
    if args.command == "clean":
        if args.target == "cache":
            return use.clean_all()
        return use.remove(args.target)
    return 2


if __name__ == "__main__":
    sys.exit(main())
