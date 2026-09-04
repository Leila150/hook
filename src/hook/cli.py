"""HOOK 1.0 command-line interface."""
from __future__ import annotations
import argparse
import pathlib
from .cli_ui import banner, error, info
from .engine import Engine
from .runtime_extensions import install_engine_extensions
from .errors import HookError

install_engine_extensions(Engine)
VERSION = "1.0.0"


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
    info("HOOK 1.0 interactive mode. Type :help for commands, :quit to exit.")
    e = Engine()
    while True:
        try:
            s = input("hook> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        c = s.strip().lower()
        if c in {":quit", ":q", ":exit"}:
            return 0
        if c in {":help", ":h"}:
            print(":help  show help\n:quit  exit HOOK\n:version  show version\n:features  list runtime features\n:clear  clear terminal")
            continue
        if c == ":version":
            print(f"HOOK {VERSION}")
            continue
        if c == ":features":
            print("\n".join(e.features.names()))
            continue
        if c == ":clear":
            print("\033[2J\033[H", end="")
            continue
        if not s.strip():
            continue
        try:
            e.run(s)
        except HookError as exc:
            error(str(exc))
        except Exception as exc:
            error(f"SystemError: {exc}")


def build_parser():
    p = argparse.ArgumentParser(
        prog="hook",
        description="HOOK 1.0 — easy, powerful, extensible, universal.",
    )
    p.add_argument("target", nargs="?", help="repl, run, or a .hk source file")
    p.add_argument("file", nargs="?", help=".hk source file when using run")
    p.add_argument("-c", "--code", metavar="CODE", help="execute HOOK source")
    p.add_argument("--version", action="version", version=f"HOOK {VERSION}")
    return p


def main(argv=None) -> int:
    p = build_parser()
    ns = p.parse_args(argv)
    if ns.target == "repl":
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
    if ns.target == "run":
        if not ns.file:
            error("run requires a .hk file")
            return 2
        return _run_file(pathlib.Path(ns.file))
    if ns.target is None:
        p.print_help()
        return 0
    return _run_file(pathlib.Path(ns.target))


if __name__ == "__main__":
    raise SystemExit(main())
