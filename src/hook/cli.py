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
VERSION = "1.1.0"


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
    entry = root / "main.hk"
    if not entry.exists():
        entry.write_text('print("Hello from HOOK!")\n', encoding="utf-8")
    config = root / "hook.toml"
    if not config.exists():
        config.write_text('[project]\nname = "' + root.name + '"\nversion = "1.0.0"\nentry = "main.hk"\n', encoding="utf-8")
    print(f"created HOOK project: {root}")
    return 0


def _test(path="tests"):
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", path], check=False)
        return p.returncode
    except Exception as exc:
        error(f"test runner failed: {exc}"); return 1


def _compat_status():
    print(f"host: {host_arch()} | android: {'yes' if is_android() else 'no'}")
    for n, c in detect_components().items():
        print(f"{n}: {'available' if c.available else 'missing'}" + (f" — {c.version}" if c.version else ""))
    return 0


def _compat_run(executable, args):
    try: return WinlatorRuntime().run(executable, args)
    except CompatibilityError as exc:
        error(str(exc)); info("Set HOOK_ROOTFS, HOOK_WINEPREFIX and component paths for a custom compatibility environment."); return 1
    except Exception as exc:
        error(f"CompatibilityError: {exc}"); return 1


def _mobile(args):
    try:
        from .mobile_compiler import compile_mobile
        result = compile_mobile(args.source, args.platform, args.output, package=args.package, app_name=args.name)
        print(f"generated {result.platform} project: {result.project}")
        if result.artifact: print(f"artifact: {result.artifact}")
        return 0
    except Exception as exc:
        error(f"mobile build failed: {exc}"); return 1


def repl():
    banner(); info(f"HOOK {VERSION} interactive mode. Type :help for commands, :quit to exit."); e = Engine()
    while True:
        try: s = input("hook> ")
        except (EOFError, KeyboardInterrupt): print(); return 0
        c = s.strip().lower()
        if c in {":quit", ":q", ":exit"}: return 0
        if c in {":help", ":h"}:
            print(":help  :quit  :version  :features  :clear"); continue
        if c == ":version": print(f"HOOK {VERSION}"); continue
        if c == ":features": print("\n".join(e.features.names())); continue
        if c == ":clear": print("\033[2J\033[H", end=""); continue
        if not s.strip(): continue
        try:
            # Expressions are evaluated directly so their resulting value is
            # visible in the REPL, while statements continue through Engine.
            try:
                result = e.expr(s, e.root)
            except Exception:
                e.run(s)
            else:
                if result is not None:
                    hook_print(result)
        except HookError as exc: error(str(exc))
        except Exception as exc: error(f"SystemError: {exc}")


def build_parser():
    p = argparse.ArgumentParser(prog="hook", description="HOOK — easy, powerful, extensible, universal.")
    p.add_argument("target", nargs="?", help="command or .hk source file")
    p.add_argument("args", nargs="*", help="command arguments")
    p.add_argument("-c", "--code", metavar="CODE", help="execute HOOK source")
    p.add_argument("--write", action="store_true", help="write formatted output back to the source file (fmt)")
    p.add_argument("--version", action="version", version=f"HOOK {VERSION}")
    return p


def main(argv=None):
    ns = build_parser().parse_args(argv)
    if ns.code is not None:
        try: Engine().run(ns.code); return 0
        except HookError as exc: error(str(exc)); return 1
        except Exception as exc: error(f"SystemError: {exc}"); return 1
    cmd = ns.target
    args = ns.args
    if cmd in {None, "help", "--help", "-h"}:
        build_parser().print_help(); print("\nCommands: run repl check fmt new test build mobile compat version env")
        return 0
    if cmd == "version": print(f"HOOK {VERSION}"); return 0
    if cmd == "repl": return repl()
    if cmd == "run": return _run_file(args[0]) if args else 2
    if cmd == "check": return _check_file(args[0]) if args else 2
    if cmd == "fmt": return _format_file(args[0], ns.write) if args else 2
    if cmd == "new": return _new_project(args[0]) if args else 2
    if cmd == "test": return _test(args[0] if args else "tests")
    if cmd == "build":
        try:
            from .build_system import NativeBuilder
            b = NativeBuilder(); print(b); return 0
        except Exception as exc: error(str(exc)); return 1
    if cmd == "mobile":
        if len(args) < 3 or args[0] != "build": error("usage: hook mobile build <android|ios> <file.hk> [--output DIR]"); return 2
        platform, source = args[1], args[2]
        output = pathlib.Path("build/mobile")
        package = "com.hook.app"; name = "HOOK App"
        i = 3
        while i < len(args):
            if args[i] == "--output" and i + 1 < len(args): output = pathlib.Path(args[i+1]); i += 2; continue
            if args[i] == "--package" and i + 1 < len(args): package = args[i+1]; i += 2; continue
            if args[i] == "--name" and i + 1 < len(args): name = args[i+1]; i += 2; continue
            i += 1
        class A: pass
        a=A(); a.platform=platform; a.source=source; a.output=output; a.package=package; a.name=name
        return _mobile(a)
    if cmd == "compat":
        rt = WinlatorRuntime(); action = args[0] if args else "status"; rest = args[1:]
        if action == "status": return _compat_status()
        if action == "doctor": print(rt.doctor()); return 0
        if action == "list": print("\n".join(rt.list_profiles()) or "No compatibility profiles."); return 0
        if action == "create":
            if not rest: error("compat create requires a profile name"); return 2
            print(rt.create_profile(rest[0])); return 0
        if action == "inspect":
            if not rest: error("compat inspect requires a profile name"); return 2
            try: print(rt.load_profile(rest[0]).to_json()); return 0
            except Exception as exc: error(str(exc)); return 1
        if action == "run":
            if not rest: error("compat run requires an executable path"); return 2
            return _compat_run(rest[0], rest[1:])
        error(f"unknown compat action: {action}"); return 2
    return _run_file(pathlib.Path(cmd))


if __name__ == "__main__": raise SystemExit(main())
