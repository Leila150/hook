# HOOK 1.0 Specification

## Core syntax

HOOK source files use `.hk` and indentation. Blocks do not require `end`, `endif`, or similar terminators.

```hook
if condition then
    print("yes")
elif other then
    print("other")
else
    print("no")
```

Functions accept positional, keyword, default, variadic, and typed parameters. `function`, `func`, and `def` are aliases.

## Types

The core runtime names are `text`, `num`, `decimal`, `boolean`, `None`, `Any`, `All`, `list`, `unique`, `data`, `group`, `Object`, `Type`, `Concept`, `Operator`, and `Loop`.

`num` is an integer type and `decimal` is a floating-point type. The collection types may contain mixed values.

## Scope

`local`, `global`, and `all` select the intended persistence scope according to the language rules. A `const` binding is immutable after declaration. `reassign` requires an existing binding.

## Control flow

HOOK supports `if`/`elif`/`else`, `while`, `for`, `foreach`, `repeat`, `until`, and `forever`. Loops may have `else` and `finally` blocks. `break N` exits N nested loops. There is intentionally no `continue` keyword.

## Exceptions

`try`, `except`/`catch`, `finally`, and `raise` are available. The runtime exposes a structured HOOK exception hierarchy and supports custom exception types through the extension system.

## Modules

The 1.0 runtime provides built-in modules for JSON, OS access, mathematics, randomness, paths, time, async operations, web/API routing, concurrency, AI, games, native interop, memory, tooling, packages, and dialects.

```hook
import json
from math import sqrt

print(json.dumps({"root": sqrt(49)}))
```

## Web/API

A route can be declared directly in HOOK:

```hook
import web

api GET "/hello" do
    return {"message": "Hello from HOOK"}

serve "127.0.0.1" 8000
```

Route parameters support the same `{name: type}` notation exposed by the router.

## Extensibility

Extensions can provide types, errors, statements, loops, operators, languages/dialects, and processors. Extension conflicts are explicit and can be resolved by the developer.

## Runtime philosophy

HOOK 1.0 keeps platform backends modular. The public language and runtime API are stable while native, GPU, Android, graphics, and advanced AI backends can evolve independently.
