# HOOK 1.1

HOOK is a general-purpose programming language designed around four goals: **Easy, Powerful, Extensible, Universal.**

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

The CLI now provides project creation, source checking, formatting, tests, build/toolchain entry points, mobile project generation, and compatibility-runtime management.

## Termux

HOOK has a Termux package recipe and an automated package repository. Until HOOK is accepted into the official Termux repositories, add the HOOK repository once:

```sh
bash packaging/termux/add-repo.sh
pkg update
pkg install hook
```

After installation:

```sh
hook --version
hook repl
hook new hello
hook run hello/main.hk
```

The package installs the `hook` command and the HOOK runtime and depends on Termux's `python` package. The package is architecture-independent because the language runtime is Python-based.

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

## License

MIT
