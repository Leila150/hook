# HOOK Extensions

HOOK has exactly seven first-class extension categories:

- `Type` — custom types.
- `Error` — custom errors.
- `Statement` — new or replacement statements.
- `Loop` — new or replacement loop constructs.
- `Operator` — symbolic and word operators.
- `Language` — complete HOOK dialects. A dialect must ultimately inherit from `Language`.
- `Processor` — miscellaneous language-processing extensions.

## Processor

`Processor` is deliberately a miscellaneous category. It is not a second statement or operator system. The v0.1 built-in processors are:

- `do`
- `then`
- `const`

Other constructs stay in their own categories even when their implementation uses processing machinery.

## Examples

```hook
class Money(Type):
    ...

class MyError(Error):
    ...

class otherwise(Statement):
    ...

class repeat_more(Loop):
    ...

class contains(Operator):
    ...

class my_processor(Processor):
    ...

class dialect_1(Language):
    ...

class dialect_2(Language, dialect_1):
    ...
```

Language extension names may also be symbolic, allowing dialect declarations such as:

```hook
class -+(Language, dialect_1):
    ...
```

The runtime keeps separate registries for all seven categories, supports explicit replacement and conflict selection, and exposes `extensions.snapshot()` for diagnostics.
