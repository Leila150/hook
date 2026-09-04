"""Terminal UI helpers for the HOOK CLI."""
from __future__ import annotations

import os
import sys


def supports_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def color(text: str, code: str) -> str:
    if not supports_color():
        return text
    return f"\033[{code}m{text}\033[0m"


def banner() -> None:
    print(color("HOOK", "1;36") + color(" — programming language v0.1.0", "1"))


def success(text: str) -> None:
    print(color("✓ ", "1;32") + text)


def info(text: str) -> None:
    print(color("• ", "1;36") + text)


def error(text: str) -> None:
    print(color("error: ", "1;31") + text, file=sys.stderr)
