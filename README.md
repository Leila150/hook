# HOOK 1.0

HOOK is a general-purpose programming language designed around four goals: **Easy, Powerful, Extensible, Universal.**

## 1.0

HOOK 1.0 consolidates the language interpreter and its runtime subsystems into one public API. The project includes foundations for:

- indentation-based `.hk` source with no `end` keyword
- variables, constants, functions, closures, classes and inheritance
- typed parameters, conversions and heterogeneous collections
- conditions, loops, nested `break N`, exceptions and `finally`
- first-class functions and execution helpers
- persistent `.hkd` data storage
- HTTP client and web application primitives
- API routing primitives
- asynchronous execution and concurrency primitives
- tensors, neural-network primitives, optimizers and datasets
- 2D game/application primitives, vectors, scenes, entities and audio metadata
- C/C++/Rust native interop, pointers and memory primitives
- packages, extensions, statements, loops, operators, processors and dialects
- compiler/bytecode foundations and a core VM
- formatter, linter, diagnostics, profiler and test-runner foundations
- cross-platform/native/Android toolchain metadata
- a standard module surface for `json`, `os`, `math`, `random`, `path`, `time`, `async`, `web`, `api`, `ai`, `game`, `native`, `memory`, `tooling`, `packages`, and `dialects`

## Example

```hook
local x = 10
local y = 20

function add(a: num, b: num) do
    return a + b

if add(x, y) == 30 then
    print("HOOK 1.0 works!")
```

## Module imports

```hook
import json
from math import sqrt

print(sqrt(81))
```

The built-in modules are exposed through the same runtime and can also be accessed directly from an `Engine` instance.

## CLI

```text
hook file.hk
hook run file.hk
hook -c 'print("hello")'
hook repl
hook --version
```

## Status

1.0 is the first integrated public release line. The repository intentionally keeps low-level compiler, native, graphics, Android, GPU and advanced AI components modular so they can evolve without changing the core HOOK language syntax.

The goal is not to fake completeness with placeholders: each subsystem is exposed as a real Python runtime component, while deeper platform backends can be added independently.

## License

MIT
