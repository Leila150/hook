"""Command line interface for HOOK v0.1."""
from __future__ import annotations

import argparse
import pathlib
import sys

from .cli_ui import banner, error, info, success
from .engine import Engine
from .errors import HookError

VERSION = "0.1.0"


def _run_file(path: pathlib.Path) -> int:
    if not path.exists():
        error(f"file not found: {path}")
        return 1
    if not path.is_file():
        error(f"not a file: {path}")
        return 1
    if path.suffix != ".hk":
        error("HOOK source files must use .hk")
        return 1
    try:
        Engine(str(path)).run(path.read_text(encoding="utf-8"))
        return 0
    except HookError as exc:
        error(str(exc))
        return 1
    except Exception as exc:
        error(f"SystemError: {exc}")
        return 1


def repl() -> int:
    banner()
    info("Interactive mode. Type :help for commands, :quit to exit.")
    engine = Engine()
    while True:
        try:
            source = input("hook> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        command = source.strip().lower()
        if command in {":quit", ":q", ":exit"}:
            return 0
        if command in {":help", ":h"}:
            print(":help  show this help")
            print(":quit  exit HOOK")
            print(":version  show version")
            print(":clear  clear the terminal")
            continue
        if command == ":version":
            print(f"HOOK {VERSION}")
            continue
        if command == ":clear":
            print("\033[2J\033[H", end="")
            continue
        if not source.strip():
            continue
        try:
            engine.run(source)
        except HookError as exc:
            error(str(exc))
        except Exception as exc:
            error(f"SystemError: {exc}")
    

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hook",
        description="HOOK programming language — simple, powerful, extensible.",
        epilog="Examples: hook hello.hk | hook -c 'print(30)' | hook repl",
    )
    parser.add_argument("command", nargs="?", choices=["repl", "run"], help="command to execute")
    parser.add_argument("file", nargs="?", help=".hk source file")
    parser.add_argument("-c", "--code", metavar="CODE", help="execute HOOK source supplied on the command line")
    parser.add_argument("--version", action="version", version=f"HOOK {VERSION}")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)

    if ns.command == "repl":
        return repl()

    if ns.code is not None:
        try:
            Engine().run(ns.code)
            return 0
        except HookError as exc:
            error(str(exc))
            return 1
        except Exception as exc:
            error(f"SystemError: {exc}")
            return 1

    target = ns.file or (ns.command if ns.command == "run" else None)
    if target is None:
        parser.print_help()
        return 0
    if ns.command == "run" and ns.file is None:
        error("run requires a .hk file")
        return 2
    return _run_file(pathlib.Path(target))


if __name__ == "__main__":
    raise SystemExit(main())
