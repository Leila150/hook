"""HOOK command-line interface."""
from __future__ import annotations
import argparse
import pathlib
import subprocess
import sys

from .cli_ui import banner, error, info
from .engine import Engine, hook_print
from .runtime_extensions import install_engine_extensions
from .errors import HookError
from .compat import WinlatorRuntime, CompatibilityError, detect_components, host_arch, is_android
from .tooling import Formatter, Linter

install_engine_extensions(Engine)
VERSION = "1.1.1"


def _run_file(path):
    path = pathlib.Path(path)
    if not path.exists():
        error(f"file not found: {path}"); return 1
    if not path.is_file():
        error(f"not a file: {path}"); return 1
    if path.suffix != ".hk":
        error("HOOK source files must use .hk"); return 1
    try:
        Engine(str(path)).run(path.read_text(encoding="utf-8")); return 0
    except HookError as exc:
        error(str(exc)); return 1
    except Exception as exc:
        error(f"SystemError: {exc}"); return 1


def _check_file(path):
    path = pathlib.Path(path)
    if not path.is_file(): error(f"file not found: {path}"); return 1
    source = path.read_text(encoding="utf-8")
    diagnostics = Linter().check(source)
    if not diagnostics:
        print(f"OK: {path}"); return 0
    for d in diagnostics:
        print(f"{d.severity}: {path}:{d.line}:{d.column}: {d.message}")
    return 1 if any(d.severity == "error" for d in diagnostics) else 0


def _format_file(path, write=False):
    path = pathlib.Path(path)
    if not path.is_file(): error(f"file not found: {path}"); return 1
    old = path.read_text(encoding="utf-8")
    new = Formatter().format(old)
    if write:
        path.write_text(new, encoding="utf-8"); print(f"formatted: {path}")
    else:
        sys.stdout.write(new)
    return 0


def _new_project(name):
    root = pathlib.Path(name)
    root.mkdir(parents=True, exist_ok=True)
    main = root / "main.hk"
    if not main.exists():
        main.write_text('print("Hello from HOOK!")\n', encoding="utf-8")
    info(f"created HOOK project: {root}")
    return 0


def _run_repl():
    from .repl import REPL
    return REPL().run()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="hook", description="HOOK programming language")
    parser.add_argument("file", nargs="?", help="HOOK source file (.hk)")
    parser.add_argument("-c", "--code", help="execute HOOK source directly")
    parser.add_argument("--version", action="store_true", help="show HOOK version")
    parser.add_argument("command", nargs="?", choices=("run", "repl", "version", "check", "fmt", "new", "test", "build", "mobile", "compat"))
    parser.add_argument("args", nargs=argparse.REMAINDER)
    ns = parser.parse_args(argv)

    if ns.version or ns.command == "version":
        print(f"HOOK {VERSION}")
        return 0
    if ns.code is not None:
        try:
            Engine("<command>").run(ns.code)
            return 0
        except HookError as exc:
            error(str(exc)); return 1
        except Exception as exc:
            error(f"SystemError: {exc}"); return 1
    if ns.command == "repl":
        return _run_repl()
    if ns.command == "run":
        if not ns.args:
            error("usage: hook run <file.hk>"); return 2
        return _run_file(ns.args[0])
    if ns.command == "check":
        if not ns.args:
            error("usage: hook check <file.hk>"); return 2
        return _check_file(ns.args[0])
    if ns.command == "fmt":
        if not ns.args:
            error("usage: hook fmt <file.hk> [--write]"); return 2
        return _format_file(ns.args[0], "--write" in ns.args[1:])
    if ns.command == "new":
        return _new_project(ns.args[0] if ns.args else "hook-project")
    if ns.command == "test":
        return subprocess.call([sys.executable, "-m", "pytest"] + ns.args)
    if ns.command == "build":
        from .toolchain import build_project
        return build_project(ns.args[0] if ns.args else ".")
    if ns.command == "mobile":
        from .toolchain import mobile_build
        if not ns.args:
            error("usage: hook mobile build <android|ios>"); return 2
        if ns.args[0] != "build" or len(ns.args) < 2:
            error("usage: hook mobile build <android|ios>"); return 2
        return mobile_build(ns.args[1])
    if ns.command == "compat":
        from .toolchain import compatibility_command
        return compatibility_command(ns.args)
    if ns.file:
        return _run_file(ns.file)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
