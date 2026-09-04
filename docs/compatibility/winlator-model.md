# Winlator-style compatibility in HOOK

HOOK now has an optional compatibility orchestration layer based on the same broad architecture used by Winlator: an ARM64 Android/Linux host can prepare a guest root filesystem and launch an x86/x86_64 Windows application through PRoot, Box86/Box64, and Wine.

The important distinction is that HOOK does **not** bundle Wine, Box64, Box86, PRoot, Mesa, DXVK, or other third-party runtime binaries. It discovers components supplied by the device/user and composes them at launch time.

## Architecture

```text
HOOK CLI / application
        |
        v
Compatibility Runtime
        |
        +---- Android/ARM64 host detection
        |
        +---- guest RootFS
        |       |
        |       +---- PRoot filesystem boundary
        |
        +---- Box64 (x86_64) / Box86 (x86)
        |
        +---- Wine
        |
        +---- Windows .exe
```

On a typical ARM64 Android setup, the intended execution path is:

`Android ARM64 -> PRoot/rootfs -> Box64 -> x86_64 Wine -> Windows EXE`

This follows the architectural idea documented by Winlator: the host-side environment prepares the guest filesystem and process environment while Box64/Box86 provides architecture translation and Wine provides the Windows API/runtime layer.

## CLI

Check the detected components:

```text
hook compat status
```

Launch a Windows executable when the required components are installed:

```text
hook compat run /path/to/program.exe
hook compat run /path/to/program.exe --arg value
```

## Environment variables

Custom installations can be selected without changing HOOK source:

- `HOOK_ROOTFS` — guest root filesystem
- `HOOK_WINEPREFIX` — Wine prefix
- `HOOK_BOX64` — Box64 executable
- `HOOK_BOX86` — Box86 executable
- `HOOK_PROOT` — PRoot executable
- `HOOK_WINE` — Wine executable

## Why this matters for HOOK

This gives HOOK a practical path toward the same kind of universal execution experience: HOOK itself stays architecture-neutral while an installed compatibility backend handles foreign binaries. It also leaves room for future graphics/audio/container integrations without pretending that a Python package can replace native drivers or emulator/translation binaries.
