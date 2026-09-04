"""Compatibility runtime inspired by Winlator's Android execution model.

HOOK does not ship third-party Wine/Box64/PRoot binaries. Instead this module
orchestrates an installed ARM64 root filesystem plus PRoot, Box64/Box86 and
Wine when those components are available on the host. This keeps HOOK legal,
small, and usable with system-provided compatibility layers.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import os
from pathlib import Path
import platform
import shutil
import subprocess
from typing import Iterable, Mapping


@dataclass(frozen=True)
class Component:
    name: str
    path: str | None
    available: bool
    version: str = ""


@dataclass
class CompatibilityConfig:
    rootfs: Path | None = None
    wine_prefix: Path | None = None
    box64: str | None = None
    box86: str | None = None
    proot: str | None = None
    wine: str | None = None
    environment: dict[str, str] = field(default_factory=dict)
    box64_args: list[str] = field(default_factory=list)


class CompatibilityError(RuntimeError):
    pass


def _which(*names: str) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _version(path: str | None) -> str:
    if not path:
        return ""
    try:
        p = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=3)
        return (p.stdout or p.stderr).splitlines()[0][:200] if p.returncode == 0 else ""
    except Exception:
        return ""


def detect_components() -> dict[str, Component]:
    """Detect the compatibility-layer pieces without requiring them."""
    paths = {
        "proot": _which("proot"),
        "box64": _which("box64"),
        "box86": _which("box86"),
        "wine": _which("wine", "wine64"),
    }
    return {
        name: Component(name, path, path is not None, _version(path))
        for name, path in paths.items()
    }


def is_android() -> bool:
    return bool(os.environ.get("ANDROID_ROOT") or os.environ.get("ANDROID_DATA")) or platform.system().lower() == "android"


def host_arch() -> str:
    return platform.machine().lower()


class WinlatorRuntime:
    """Prepare and launch a Windows program using a Winlator-like stack.

    On ARM64 the intended path is:
        Android/ARM64 -> PRoot/rootfs -> Box64 -> x86_64 Wine -> Windows EXE

    On 32-bit x86 guests Box86 may be selected instead. Graphics/audio servers
    remain host integrations; HOOK only prepares the process environment.
    """

    def __init__(self, config: CompatibilityConfig | None = None):
        self.config = config or CompatibilityConfig()
        self.components = detect_components()

    def configure_from_environment(self) -> "WinlatorRuntime":
        env = os.environ
        if not self.config.rootfs:
            raw = env.get("HOOK_ROOTFS") or env.get("WINLATOR_ROOTFS")
            if raw:
                self.config.rootfs = Path(raw).expanduser().resolve()
        if not self.config.wine_prefix:
            raw = env.get("WINEPREFIX") or env.get("HOOK_WINEPREFIX")
            if raw:
                self.config.wine_prefix = Path(raw).expanduser().resolve()
        self.config.box64 = self.config.box64 or env.get("HOOK_BOX64") or self.components["box64"].path
        self.config.box86 = self.config.box86 or env.get("HOOK_BOX86") or self.components["box86"].path
        self.config.proot = self.config.proot or env.get("HOOK_PROOT") or self.components["proot"].path
        self.config.wine = self.config.wine or env.get("HOOK_WINE") or self.components["wine"].path
        return self

    def validate(self) -> list[str]:
        self.configure_from_environment()
        missing: list[str] = []
        if self.config.rootfs and not self.config.rootfs.exists():
            missing.append("rootfs")
        if not self.config.box64 and not self.config.box86:
            missing.append("box64/box86")
        if not self.config.wine:
            missing.append("wine")
        return missing

    def environment(self, extra: Mapping[str, str] | None = None) -> dict[str, str]:
        self.configure_from_environment()
        result = dict(os.environ)
        if self.config.rootfs:
            result["HOOK_ROOTFS"] = str(self.config.rootfs)
            result.setdefault("PATH", "")
            result["PATH"] = f"{self.config.rootfs / 'usr/bin'}:{result['PATH']}"
            result["LD_LIBRARY_PATH"] = f"{self.config.rootfs / 'usr/lib'}:{result.get('LD_LIBRARY_PATH', '')}"
        if self.config.wine_prefix:
            self.config.wine_prefix.mkdir(parents=True, exist_ok=True)
            result["WINEPREFIX"] = str(self.config.wine_prefix)
        result.update(self.config.environment)
        if extra:
            result.update({str(k): str(v) for k, v in extra.items()})
        return result

    def command(self, executable: str | Path, args: Iterable[str] = ()) -> list[str]:
        self.configure_from_environment()
        exe = str(Path(executable).expanduser())
        args = [str(a) for a in args]
        wine = self.config.wine
        if not wine:
            raise CompatibilityError("Wine is not available")
        translator = self.config.box64 if host_arch() in {"aarch64", "arm64"} else None
        if translator:
            inner = [wine, exe, *args]
            command = [translator, *self.config.box64_args, *inner]
        else:
            command = [wine, exe, *args]
        if self.config.proot and self.config.rootfs:
            # PRoot makes the rootfs appear as the guest filesystem while
            # preserving the host process model, matching the core Winlator idea.
            command = [self.config.proot, "-r", str(self.config.rootfs), "--", *command]
        return command

    def run(self, executable: str | Path, args: Iterable[str] = (), *, extra_env: Mapping[str, str] | None = None) -> int:
        missing = self.validate()
        if missing:
            raise CompatibilityError("missing compatibility components: " + ", ".join(missing))
        command = self.command(executable, args)
        return subprocess.run(command, env=self.environment(extra_env)).returncode


__all__ = [
    "Component", "CompatibilityConfig", "CompatibilityError", "detect_components",
    "is_android", "host_arch", "WinlatorRuntime",
]
