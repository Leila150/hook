"""Small, deterministic stack VM used by HOOK's compiler pipeline.

The VM intentionally has no dependency on the interpreter. It is suitable for
unit tests, compiler bring-up, and future native/JIT backends.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Op:
    code: str
    arg: Any = None


class Bytecode:
    def __init__(self, ops=()):
        self.ops = list(ops)

    def emit(self, code: str, arg: Any = None) -> int:
        self.ops.append(Op(code, arg))
        return len(self.ops) - 1

    def patch(self, index: int, arg: Any) -> None:
        self.ops[index] = Op(self.ops[index].code, arg)


class VM:
    """A compact stack VM with safe name lookup and useful core operations."""
    def __init__(self):
        self.stack: list[Any] = []
        self.globals: dict[str, Any] = {}
        self.locals: dict[str, Any] = {}
        self.ip = 0

    def _load(self, name: str) -> Any:
        if name in self.locals:
            return self.locals[name]
        if name in self.globals:
            return self.globals[name]
        raise NameError(f"name '{name}' is not defined")

    def run(self, program: Bytecode, globals_: Mapping[str, Any] | None = None):
        if globals_ is not None:
            self.globals = dict(globals_)
        self.ip = 0
        self.stack.clear()
        while self.ip < len(program.ops):
            op = program.ops[self.ip]
            self.ip += 1
            code, arg = op.code, op.arg
            if code == 'CONST': self.stack.append(arg)
            elif code == 'LOAD': self.stack.append(self._load(str(arg)))
            elif code == 'STORE': self.globals[str(arg)] = self.stack.pop()
            elif code == 'STORE_LOCAL': self.locals[str(arg)] = self.stack.pop()
            elif code == 'POP': self.stack.pop()
            elif code == 'ADD': self._binary(lambda a,b: a+b)
            elif code == 'SUB': self._binary(lambda a,b: a-b)
            elif code == 'MUL': self._binary(lambda a,b: a*b)
            elif code == 'DIV': self._binary(lambda a,b: a/b)
            elif code == 'MOD': self._binary(lambda a,b: a%b)
            elif code == 'POW': self._binary(lambda a,b: a**b)
            elif code == 'EQ': self._binary(lambda a,b: a==b)
            elif code == 'NE': self._binary(lambda a,b: a!=b)
            elif code == 'LT': self._binary(lambda a,b: a<b)
            elif code == 'LE': self._binary(lambda a,b: a<=b)
            elif code == 'GT': self._binary(lambda a,b: a>b)
            elif code == 'GE': self._binary(lambda a,b: a>=b)
            elif code == 'NOT': self.stack.append(not self.stack.pop())
            elif code == 'JUMP': self.ip = int(arg)
            elif code == 'JUMP_IF_FALSE':
                if not self.stack.pop(): self.ip = int(arg)
            elif code == 'JUMP_IF_TRUE':
                if self.stack.pop(): self.ip = int(arg)
            elif code == 'RETURN': return self.stack.pop() if self.stack else None
            elif code == 'HALT': return self.stack.pop() if self.stack else None
            else: raise RuntimeError(f"unknown bytecode operation: {code}")
        return self.stack[-1] if self.stack else None

    def _binary(self, fn):
        b = self.stack.pop(); a = self.stack.pop(); self.stack.append(fn(a, b))
