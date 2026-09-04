# HOOK 1.1.1

HOOK is a general-purpose programming language designed around four goals: **Easy, Powerful, Extensible, Universal.**

HOOK is its own language and runtime. It is **not distributed as a Python package**. Python is currently an implementation dependency of the runtime; users install HOOK itself through its CLI/package distribution.

## CLI

```text
hook file.hk
hook run file.hk
hook -c 'print("hello")'
hook repl
hook version
hook check file.hk
hook fmt file.hk
hook fmt file.hk --write
hook new my-project
hook test
hook build
hook mobile build android main.hk --output build/android
hook mobile build ios main.hk --output build/ios
hook compat status
hook compat doctor
hook compat list
hook compat create gaming
hook compat inspect gaming
hook compat run program.exe
```

The CLI provides project creation, source checking, formatting, tests, build/toolchain entry points, mobile project generation, and compatibility-runtime management.

## Termux

HOOK can be installed through Termux's normal `pkg` package manager from the HOOK APT repository. Until HOOK is accepted into the official Termux repositories, the custom repository must be bootstrapped once.

### Fresh Termux installation

Run this directly in Termux:

```sh
curl -fsSL https://raw.githubusercontent.com/Leila150/hook/main/packaging/termux/install.sh | bash
```

Then verify:

```sh
hook --version
hook repl
```

The installer adds the HOOK APT repository, runs `pkg update`, and installs the `hook` package. After that, future upgrades use the normal package manager:

```sh
pkg update
pkg upgrade hook
```

The Termux package installs the HOOK runtime source and `hook` launcher directly. It does not invoke `pip` or install a Python distribution package.

### Manual repository setup

If you prefer not to pipe a script to Bash:

```sh
curl -fsSL https://raw.githubusercontent.com/Leila150/hook/main/packaging/termux/add-repo.sh -o $TMPDIR/hook-add-repo.sh
bash $TMPDIR/hook-add-repo.sh
pkg update
pkg install hook
```

## Example

```hook
local x = 10
local y = 20

function add(a: num, b: num) do
    return a + b

if add(x, y) == 30 then
    print("HOOK works!")
```

## Modules

```hook
import json
from math import sqrt

print(sqrt(81))
```

## Project

HOOK uses indentation-based `.hk` source with no `end` keyword and provides variables, functions, classes, inheritance, exceptions, persistent data, HTTP/API primitives, concurrency, AI foundations, 2D/3D graphics, physics, native interop, packages, extensions, compiler/VM foundations, and mobile build foundations.

## Mobile

`hook mobile build` generates Android and iOS application projects and bundles the original `.hk` source. Android builds require an Android/Gradle toolchain; iOS builds require Xcode on macOS. The current mobile launcher is a packaging/runtime foundation and does not yet translate arbitrary HOOK source into native machine code.

## Development

For repository development, run the source tree directly instead of installing it with `pip`:

```sh
export PYTHONPATH="$PWD/src"
python -m hook.cli version
python -m pytest
```

## License

MIT
