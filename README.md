# HOOK

HOOK is an indentation-based general-purpose programming language. This repository contains the first runnable implementation, **v0.1.0**.

## v0.1 scope

- indentation-based syntax; no `end` keyword
- `if` / `elif` / `else` with `then`
- `while`, `for`, `foreach`, `repeat`, `until`, `forever` with `do`
- `break` and `break N`; intentionally no `continue`
- `text`, `num`, `decimal`, `boolean`, `None`, `Any`, `All`
- heterogeneous `list` (`[]`), `unique` (`()`), `data` (`{}`), and `group` (backticks)
- `local`, `global`, `all`, `const`, and `reassign`
- `function`, `func`, `def`, typed/default/variadic parameters, returns
- classes, constructors, methods and inheritance foundations
- arithmetic, comparison, logical and bitwise operators
- exceptions, `raise`, `try`, `except`/`catch`, `finally`
- first-class functions and `do value`

The interpreter is intentionally the v0.1 execution backend. Bytecode and native compilation remain later implementation phases.

## Running

```text
python -m hook.cli examples/v0.1/hello.hk
```

Or embed it:

```python
from hook import run
run('print("Hello from HOOK!")')
```
