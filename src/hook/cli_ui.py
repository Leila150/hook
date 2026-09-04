"""Terminal UI helpers for the HOOK CLI."""
from __future__ import annotations
import os
import sys

VERSION = "1.1.1"

def supports_color() -> bool:return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
def color(text: str, code: str) -> str:return text if not supports_color() else f"\033[{code}m{text}\033[0m"
def banner() -> None:print(color("HOOK","1;36") + color(f" — programming language v{VERSION}","1"))
def success(text: str) -> None:print(color("✓ ","1;32") + text)
def info(text: str) -> None:print(color("• ","1;36") + text)
def error(text: str) -> None:print(color("error: ","1;31") + text,file=sys.stderr)
