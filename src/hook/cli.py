"""Command line launcher for HOOK v0.1."""
import argparse, pathlib, sys
from .engine import Engine
from .errors import HookError

def main(argv=None):
    ap=argparse.ArgumentParser(prog="hook", description="HOOK programming language v0.1")
    ap.add_argument("file", nargs="?", help=".hk source file")
    ap.add_argument("-c","--code", help="execute HOOK source supplied on the command line")
    ap.add_argument("--version", action="version", version="HOOK 0.1.0")
    ns=ap.parse_args(argv)
    try:
        if ns.code is not None: Engine().run(ns.code); return 0
        if not ns.file:
            ap.error("provide a .hk file or --code")
        p=pathlib.Path(ns.file)
        if p.suffix != ".hk": ap.error("HOOK source files must use .hk")
        Engine(str(p)).run(p.read_text(encoding="utf-8")); return 0
    except HookError as e:
        print(e, file=sys.stderr); return 1
    except Exception as e:
        print(f"SystemError: {e}", file=sys.stderr); return 1

if __name__ == "__main__": raise SystemExit(main())
