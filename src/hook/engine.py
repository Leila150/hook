"""HOOK v0.1 execution engine.

This module intentionally keeps the v0.1 syntax while providing the runtime
features that make variables, types, persistent data, HTTP and async useful.
"""
from __future__ import annotations

import asyncio
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any as PyAny

from .errors import *


@dataclass
class Token:
    kind: str
    value: str
    line: int
    column: int

    def __str__(self):
        return self.value or self.kind

    __repr__ = __str__


class Lexer:
    def __init__(self, source):
        self.source = source

    def tokenize(self):
        out, stack = [], [0]
        pat = re.compile(
            r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\b\d+(?:\.\d+)?\b|'
            r'[A-Za-z_]\w*|==|!=|<=|>=|\*\*|//|<<|>>|\?\?|!<=|!>=|!<|!>|'
            r'[+\-*/%&|^~<>=(),.\[\]{}:`]'
        )
        lines = self.source.splitlines()
        for no, raw in enumerate(lines, 1):
            if not raw.strip() or raw.lstrip().startswith(("#", "--")):
                continue
            n = len(raw) - len(raw.lstrip(" "))
            if "\t" in raw[:n]:
                raise SyntaxError("tabs are not allowed; use spaces", no)
            if n > stack[-1]:
                stack.append(n)
                out.append(Token("INDENT", "", no, 1))
            while n < stack[-1]:
                stack.pop()
                out.append(Token("DEDENT", "", no, 1))
            if n != stack[-1]:
                raise SyntaxError("inconsistent indentation", no)
            for m in pat.finditer(raw[n:]):
                v = m.group()
                kind = "STRING" if v[0] in "\"'" else (
                    "NUMBER" if v[0].isdigit() else
                    ("IDENT" if v[0].isalpha() or v[0] == "_" else "OP")
                )
                out.append(Token(kind, v, no, n + m.start() + 1))
            out.append(Token("NEWLINE", "", no, len(raw) + 1))
        while len(stack) > 1:
            stack.pop()
            out.append(Token("DEDENT", "", len(lines) + 1, 1))
        out.append(Token("EOF", "", len(lines) + 1, 1))
        return out


@dataclass
class Node:
    text: str
    line: int
    indent: int
    children: list

    def __repr__(self):
        return f"Node({self.text!r}, line={self.line})"


def hook_repr(value):
    if isinstance(value, HookType):
        return value.name
    if isinstance(value, HookErrorType):
        return value.name
    if isinstance(value, HookClass):
        return f"class {value.name}"
    if isinstance(value, HookFunction):
        return f"async function {value.name}" if value.async_ else f"function {value.name}"
    if isinstance(value, HookObject):
        return f"<{value.cls.name} object>"
    if isinstance(value, HookError):
        return str(value)
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "[" + ", ".join(hook_repr(v) for v in value) + "]"
    if isinstance(value, tuple):
        return "(" + ", ".join(hook_repr(v) for v in value) + ("," if len(value) == 1 else "") + ")"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{hook_repr(k)}: {hook_repr(v)}" for k, v in value.items()) + "}"
    return str(value)


def hook_print(*values, sep=" ", end="\n"):
    print(sep.join(hook_repr(v) for v in values), end=end)


class HookType:
    def __init__(self, name, converter=None, py_types=()):
        self.name = name
        self.converter = converter
        self.py_types = py_types

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __call__(self, *args):
        if self.converter is None:
            return self
        if len(args) != 1:
            raise TypeError(f"{self.name} conversion expects one value")
        return self.converter(args[0])


class HookErrorType(HookType):
    def __init__(self, name, error_cls):
        super().__init__(name)
        self.error_cls = error_cls

    def __call__(self, message="", *args, **kwargs):
        return self.error_cls(message, *args, **kwargs)


class Parser:
    def __init__(self, source):
        self.source = source
        self.lines = []
        for no, raw in enumerate(source.splitlines(), 1):
            if not raw.strip() or raw.lstrip().startswith(("#", "--")):
                continue
            n = len(raw) - len(raw.lstrip(" "))
            self.lines.append(Node(raw[n:].strip(), no, n, []))
        self.pos = 0

    def parse(self):
        return self._block(self.lines[0].indent)[0] if self.lines else []

    def _block(self, indent):
        nodes = []
        while self.pos < len(self.lines):
            n = self.lines[self.pos]
            if n.indent < indent:
                break
            if n.indent > indent:
                raise SyntaxError("unexpected indentation", n.line)
            self.pos += 1
            if self.pos < len(self.lines) and self.lines[self.pos].indent > indent:
                n.children = self._block(self.lines[self.pos].indent)[0]
            nodes.append(n)
        return nodes, self.pos


def _strip(s, word):
    return s[:-len(word)].rstrip() if s.rstrip().endswith(word) else s.strip()


def _expr(s):
    s = s.strip()
    s = re.sub(r"\btrue\b", "True", s, flags=re.I)
    s = re.sub(r"\bfalse\b", "False", s, flags=re.I)
    for op, fn in (("!<=", "__not_le__"), ("!>=", "__not_ge__"), ("!<", "__not_lt__"), ("!>", "__not_gt__")):
        s = re.sub(r"(.+?)\s+" + re.escape(op) + r"\s+(.+)", lambda m: f"{fn}({m.group(1)}, {m.group(2)})", s)
    s = s.replace(" ?? ", " or ")
    for word, repl in (
        ("nand", "(not ({a} and {b}))"),
        ("nor", "(not ({a} or {b}))"),
        ("xor", "(bool({a}) != bool({b}))"),
        ("xnor", "(bool({a}) == bool({b}))"),
    ):
        m = re.fullmatch(r"(.+?)\s+" + word + r"\s+(.+)", s)
        if m:
            s = repl.format(a=m.group(1), b=m.group(2))
    s = re.sub(r"\bdec\s+(-?\d+(?:\.\d+)?)", r"dec(\1)", s)
    return s


class Scope:
    def __init__(self, parent=None, file_scope=None, folder_scope=None, phone_scope=None, function=False):
        self.parent = parent
        self.values = {}
        self.const = set()
        self.types = {}
        self.file_scope = file_scope if file_scope is not None else (parent.file_scope if parent else self)
        self.folder_scope = folder_scope if folder_scope is not None else (parent.folder_scope if parent else self)
        self.phone_scope = phone_scope if phone_scope is not None else (parent.phone_scope if parent else self)
        self.function = function

    def get(self, key):
        if key in self.values:
            return self.values[key]
        if self.parent:
            return self.parent.get(key)
        raise NameError(f"name '{key}' is not defined")

    def exists(self, key):
        try:
            self.get(key)
            return True
        except NameError:
            return False

    def set(self, key, value, kind=None, const=False):
        if key in self.const:
            raise RuntimeError(f"constant '{key}' cannot be reassigned")
        if kind == "local":
            target = self if self.function else self.file_scope
        elif kind == "global":
            target = self.file_scope if self.function else self.folder_scope
        elif kind == "all":
            if not self.function:
                raise SyntaxError("'all' variables are only valid inside functions")
            target = self.phone_scope
        elif kind == "reassign":
            target = self._find_owner(key)
            if target is None:
                raise NameError(f"cannot reassign undefined variable '{key}'")
        else:
            target = self.phone_scope
        if key in target.const:
            raise RuntimeError(f"constant '{key}' cannot be reassigned")
        target.values[key] = value
        if const:
            target.const.add(key)
        return target

    def _find_owner(self, key):
        p = self
        while p:
            if key in p.values:
                return p
            p = p.parent
        return None


class HKDStore:
    """Small JSON-backed implementation of HOOK's persistent .hkd data."""
    def __init__(self, filename=None):
        self.filename = Path(filename).resolve() if filename else None

    @property
    def path(self):
        return self.filename.parent / "data.hkd" if self.filename else Path("data.hkd").resolve()

    def load(self, allowed=True):
        if not allowed or not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return raw.get("data", raw) if isinstance(raw, dict) else {}
        except (OSError, ValueError):
            raise FileError(f"invalid HKD data: {self.path}")

    def save(self, value, scope_kind="global", owner=None):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {"version": 1, "scope": scope_kind, "owner": owner, "data": value}
        self.path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2, default=hook_repr), encoding="utf-8")


class HTTPResponse:
    def __init__(self, status, headers, body, url):
        self.status = status
        self.status_code = status
        self.headers = dict(headers)
        self.body = body
        self.url = url

    def text(self):
        return self.body

    def json(self):
        try:
            return json.loads(self.body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"response is not JSON: {exc}")

    def __repr__(self):
        return f"HTTPResponse({self.status}, {self.url!r})"


def _http_request(method, url, data=None, headers=None, timeout=30):
    headers = dict(headers or {})
    payload = None
    if data is not None:
        if isinstance(data, (dict, list)):
            payload = json.dumps(data).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        elif isinstance(data, str):
            payload = data.encode("utf-8")
        elif isinstance(data, bytes):
            payload = data
        else:
            payload = str(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=float(timeout)) as response:
            return HTTPResponse(response.status, response.headers, response.read().decode("utf-8", "replace"), response.geturl())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return HTTPResponse(exc.code, exc.headers, body, url)
    except urllib.error.URLError as exc:
        raise ExecutionError(f"HTTP request failed: {exc.reason}") from exc


class HTTPClient:
    def request(self, method, url, data=None, headers=None, timeout=30):
        return _http_request(method, url, data, headers, timeout)

    def get(self, url, **kwargs): return self.request("GET", url, **kwargs)
    def post(self, url, **kwargs): return self.request("POST", url, **kwargs)
    def put(self, url, **kwargs): return self.request("PUT", url, **kwargs)
    def patch(self, url, **kwargs): return self.request("PATCH", url, **kwargs)
    def delete(self, url, **kwargs): return self.request("DELETE", url, **kwargs)
    def head(self, url, **kwargs): return self.request("HEAD", url, **kwargs)


class AsyncHTTPClient:
    async def request(self, method, url, data=None, headers=None, timeout=30):
        return await asyncio.to_thread(_http_request, method, url, data, headers, timeout)

    async def get(self, url, **kwargs): return await self.request("GET", url, **kwargs)
    async def post(self, url, **kwargs): return await self.request("POST", url, **kwargs)
    async def put(self, url, **kwargs): return await self.request("PUT", url, **kwargs)
    async def patch(self, url, **kwargs): return await self.request("PATCH", url, **kwargs)
    async def delete(self, url, **kwargs): return await self.request("DELETE", url, **kwargs)
    async def head(self, url, **kwargs): return await self.request("HEAD", url, **kwargs)


class AwaitableValue:
    def __init__(self, value): self.value = value
    def __await__(self):
        async def done(): return self.value
        return done().__await__()


class ParserError(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value): self.value = value


class BreakSignal(Exception):
    def __init__(self, count=1): self.count = count


class HookFunction:
    def __init__(self, name, params, body, closure, engine, async_=False):
        self.name, self.params, self.body = name, params, body
        self.closure, self.engine, self.async_ = closure, engine, async_

    def __str__(self):
        return f"async function {self.name}" if self.async_ else f"function {self.name}"

    __repr__ = __str__

    def _call(self, args, kwargs):
        s = Scope(self.closure, function=True)
        pos = 0
        for name, typ, default, vararg in self.params:
            if vararg:
                val = list(args[pos:]); pos = len(args)
            elif pos < len(args):
                val = args[pos]; pos += 1
            elif name in kwargs:
                val = kwargs.pop(name)
            elif default is not None:
                val = self.engine.expr(default, s)
            else:
                raise FunctionError(f"missing argument '{name}'")
            if typ and typ not in ("Any", "All") and not self.engine.check_type(val, typ):
                raise TypeError(f"argument '{name}' must be {typ}, got {self.engine.type_name(val)}")
            s.values[name] = val
        if kwargs:
            raise FunctionError(f"unexpected arguments: {', '.join(kwargs)}")
        try:
            self.engine.exec_block(self.body, s)
        except ReturnSignal as r:
            return r.value
        return None

    async def _call_async(self, args, kwargs):
        return self._call(args, kwargs)

    def __call__(self, *args, **kwargs):
        if self.async_:
            return self._call_async(args, kwargs)
        return self._call(args, kwargs)


class HookClass:
    def __init__(self, name, bases, body, engine, scope):
        self.name, self.bases, self.methods, self.attrs = name, bases, {}, {}
        self.engine = engine
        for n in body:
            if re.match(r"^(?:async\s+)?(?:function|func|def)\s+", n.text):
                f = engine.make_function(n, scope); self.methods[f.name] = f
            elif "=" in n.text:
                k, v = n.text.split("=", 1); self.attrs[k.strip()] = engine.expr(v, scope)

    def __str__(self): return f"class {self.name}"
    __repr__ = __str__

    def __call__(self, *args, **kwargs):
        o = HookObject(self)
        init = self.find("__init__") or self.find("init")
        if init: init(o, *args, **kwargs)
        return o

    def find(self, key):
        if key in self.methods: return self.methods[key]
        for base in self.bases:
            if base and hasattr(base, "find"):
                found = base.find(key)
                if found: return found
        return None


class HookObject:
    def __init__(self, cls):
        object.__setattr__(self, "cls", cls)
        object.__setattr__(self, "attrs", {})

    def __str__(self): return f"<{self.cls.name} object>"
    __repr__ = __str__

    def __getattr__(self, key):
        if key in self.attrs: return self.attrs[key]
        c = self.cls
        while c:
            if key in c.attrs: return c.attrs[key]
            f = c.find(key)
            if f: return lambda *a, **kw: f(self, *a, **kw)
            c = c.bases[0] if c.bases else None
        raise AttributeError(f"object has no attribute '{key}'")

    def __setattr__(self, key, value): self.attrs[key] = value


class Engine:
    def __init__(self, filename=None):
        self.filename = str(Path(filename).resolve()) if filename else None
        self.hkd = HKDStore(filename)
        self.file_scope = Scope()
        self.folder_scope = Scope()
        self.phone_scope = Scope()
        self.file_scope.file_scope = self.file_scope; self.file_scope.folder_scope = self.folder_scope; self.file_scope.phone_scope = self.phone_scope
        self.folder_scope.file_scope = self.file_scope; self.folder_scope.folder_scope = self.folder_scope; self.folder_scope.phone_scope = self.phone_scope
        self.phone_scope.file_scope = self.file_scope; self.phone_scope.folder_scope = self.folder_scope; self.phone_scope.phone_scope = self.phone_scope
        self.root = self.file_scope
        self._builtins()
        self._load_hkd()

    def _builtins(self):
        def rng(a, b=None, step=1):
            return list(range(a, b, step)) if b is not None else list(range(1, a + 1, step))
        type_defs = {
            "text": HookType("text", str, (str,)), "num": HookType("num", int, (int,)),
            "decimal": HookType("decimal", float, (float, int)), "boolean": HookType("boolean", bool, (bool,)),
            "None": HookType("None", lambda _: None, (type(None),)), "Any": HookType("Any"), "All": HookType("All"),
            "list": HookType("list", list, (list,)), "unique": HookType("unique", tuple, (tuple,)),
            "data": HookType("data", dict, (dict,)), "group": HookType("group"),
            "Object": HookType("Object"), "Type": HookType("Type"), "Concept": HookType("Concept"),
            "Operator": HookType("Operator"), "Loop": HookType("Loop"),
        }
        self.types = type_defs
        errors = {name: HookErrorType(name, cls) for name, cls in ERRORS.items()}
        self.root.values.update({
            "True": True, "False": False, "None": None, "print": hook_print, "input": input,
            "len": len, "range": rng, "abs": abs, "min": min, "max": max, "sum": sum, "round": round,
            "bool": bool, "str": str, "int": int, "float": float,
            "text": type_defs["text"], "num": type_defs["num"], "decimal": type_defs["decimal"], "dec": type_defs["decimal"],
            "boolean": type_defs["boolean"], "list": type_defs["list"], "unique": type_defs["unique"],
            "data": type_defs["data"], "group": type_defs["group"], "Object": type_defs["Object"], "Type": type_defs["Type"],
            "Concept": type_defs["Concept"], "Operator": type_defs["Operator"], "Loop": type_defs["Loop"],
            "type": self.type_name, "convert": self.convert,
            "__not_le__": lambda a,b: not a <= b, "__not_ge__": lambda a,b: not a >= b,
            "__not_lt__": lambda a,b: not a < b, "__not_gt__": lambda a,b: not a > b,
            "http": HTTPClient(), "async_http": AsyncHTTPClient(), "await": self.await_value,
        })
        self.root.values.update(errors)

    def _load_hkd(self):
        if not self.filename or not self.hkd.path.exists(): return
        try:
            raw = json.loads(self.hkd.path.read_text(encoding="utf-8"))
            scope = raw.get("scope", "global") if isinstance(raw, dict) else "global"
            owner = raw.get("owner") if isinstance(raw, dict) else None
            if scope == "local" and owner and owner != self.filename: return
            target = self.file_scope if scope == "local" else self.folder_scope if scope == "global" else self.phone_scope
            data = raw.get("data", {}) if isinstance(raw, dict) else {}
            if isinstance(data, dict): target.values.update(data)
        except (OSError, ValueError):
            raise FileError(f"invalid HKD data: {self.hkd.path}")

    def type_name(self, value):
        if isinstance(value, HookType): return "Type"
        if isinstance(value, HookClass): return value.name
        if isinstance(value, HookFunction): return "function"
        if isinstance(value, HookObject): return value.cls.name
        if isinstance(value, HookError): return value.__class__.__name__
        if value is None: return "None"
        if isinstance(value, bool): return "boolean"
        if isinstance(value, int) and not isinstance(value, bool): return "num"
        if isinstance(value, float): return "decimal"
        if isinstance(value, str): return "text"
        if isinstance(value, list): return "list"
        if isinstance(value, tuple): return "unique"
        if isinstance(value, dict): return "data"
        return value.__class__.__name__

    def check_type(self, value, typ):
        if isinstance(typ, HookType): typ = typ.name
        if typ in ("Any", "All"): return True
        if typ == "decimal": return isinstance(value, (int, float)) and not isinstance(value, bool)
        if typ == "num": return isinstance(value, int) and not isinstance(value, bool)
        if typ == "boolean": return isinstance(value, bool) or value in (0, 1)
        return self.type_name(value) == typ

    def convert(self, value, target):
        name = target.name if isinstance(target, HookType) else str(target)
        converters = {"text": str, "num": int, "decimal": float, "dec": float, "boolean": bool,
                      "list": list, "unique": tuple, "data": dict}
        if name not in converters: raise TypeError(f"cannot convert to {name}")
        try: return converters[name](value)
        except Exception as exc: raise ValueError(str(exc)) from exc

    def await_value(self, value):
        if asyncio.iscoroutine(value):
            try: loop = asyncio.get_running_loop()
            except RuntimeError: loop = None
            if loop and loop.is_running(): return value
            return asyncio.run(value)
        if isinstance(value, AwaitableValue): return value.value
        return value

    def expr(self, source, scope):
        try:
            env, chain = {}, []
            p = scope
            while p: chain.append(p); p = p.parent
            for q in reversed(chain): env.update(q.values)
            return eval(_expr(source), {"__builtins__": {}}, env)
        except HookError: raise
        except NameError as exc: raise NameError(str(exc)) from exc
        except Exception as exc: raise ExecutionError(str(exc)) from exc

    def make_function(self, node, scope):
        m = re.match(r"(?:async\s+)?(?:function|func|def)\s+([A-Za-z_]\w*)\s*\((.*?)\)", node.text)
        if not m: raise SyntaxError("invalid function declaration", node.line)
        params = []
        for raw in [x.strip() for x in m.group(2).split(",") if x.strip()]:
            vararg = raw.startswith("*"); raw = raw[1:].strip() if vararg else raw
            default = None
            if "=" in raw: raw, default = raw.split("=", 1); raw, default = raw.strip(), default.strip()
            typ = None
            if ":" in raw: raw, typ = raw.split(":", 1); raw, typ = raw.strip(), typ.strip()
            params.append((raw, typ, default, vararg))
        return HookFunction(m.group(1), params, node.children or [], scope, self, node.text.startswith("async"))

    def assign(self, lhs, value, scope, kind=None, declared_type=None):
        lhs = lhs.strip()
        if re.fullmatch(r"[A-Za-z_]\w*", lhs):
            if declared_type and not self.check_type(value, declared_type):
                raise TypeError(f"variable '{lhs}' must be {declared_type}, got {self.type_name(value)}")
            target = scope.set(lhs, value, kind)
            if isinstance(value, dict):
                hkind = "local" if kind == "local" else "global" if kind == "global" else "all" if kind == "all" else "phone"
                owner = self.filename if hkind == "local" else None
                self.hkd.save(value, hkind, owner)
            return
        m = re.fullmatch(r"(.+)\.([A-Za-z_]\w*)", lhs)
        if m:
            setattr(self.expr(m.group(1), scope), m.group(2), value); return
        raise SyntaxError("invalid assignment target")

    def _clauses(self, nodes, i, prefixes):
        j, found = i + 1, {}
        while j < len(nodes) and any(nodes[j].text == p or nodes[j].text.startswith(p + " ") for p in prefixes):
            found[nodes[j].text.split()[0]] = nodes[j]; j += 1
        return found, j

    def _run_loop_body(self, node, scope):
        try: self.exec_block(node.children or [], Scope(scope))
        except BreakSignal as b: return b
        return None

    def exec_block(self, nodes, scope):
        i = 0
        while i < len(nodes):
            n, s = nodes[i], nodes[i].text
            if s in ("else", "finally") or s.startswith(("elif ", "except ", "catch ")):
                i += 1; continue

            m = re.match(r"^(local|global|all|const|reassign)\s+(.+?)\s*=\s*(.*)$", s)
            if m:
                lhs, rhs = m.group(2), m.group(3); declared = None
                if ":" in lhs and re.fullmatch(r"[A-Za-z_]\w*\s*:\s*[A-Za-z_]\w*", lhs):
                    lhs, declared = [x.strip() for x in lhs.split(":", 1)]
                self.assign(lhs, self.expr(rhs, scope), scope, m.group(1), declared); i += 1; continue

            if re.match(r"^(?:async\s+)?(?:function|func|def)\s+", s):
                f = self.make_function(n, scope); scope.values[f.name] = f; i += 1; continue

            if s.startswith("class "):
                m = re.match(r"class\s+([A-Za-z_]\w*)\s*\((.*?)\):?$", s)
                if not m: raise SyntaxError("invalid class declaration", n.line)
                bases = [scope.get(x.strip()) for x in m.group(2).split(",") if x.strip() and scope.exists(x.strip())]
                scope.values[m.group(1)] = HookClass(m.group(1), bases, n.children or [], self, scope); i += 1; continue

            if s.startswith("if "):
                chain, j = [n], i + 1
                while j < len(nodes) and (nodes[j].text.startswith("elif ") or nodes[j].text == "else"):
                    chain.append(nodes[j]); j += 1
                for c in chain:
                    cond = c.text == "else" or self.expr(_strip(c.text[2:].strip(), "then"), scope)
                    if cond: self.exec_block(c.children or [], Scope(scope)); break
                i = j; continue

            if s == "try":
                clauses, j = self._clauses(nodes, i, ["except", "catch", "finally"]); err = None
                try: self.exec_block(n.children or [], Scope(scope))
                except Exception as exc: err = exc
                if err:
                    handled = False
                    for key, c in clauses.items():
                        if key == "finally": continue
                        head = c.text.split(None, 1)[1] if " " in c.text else ""
                        if not head or head == "*" or head == err.__class__.__name__:
                            self.exec_block(c.children or [], Scope(scope)); handled = True; break
                    if not handled: raise err
                if "finally" in clauses: self.exec_block(clauses["finally"].children or [], Scope(scope))
                i = j; continue

            if s.startswith(("while ", "for ", "foreach ", "repeat", "forever", "until ")):
                clauses, j = self._clauses(nodes, i, ["else", "finally"]); broke = False; error = None
                try:
                    if s.startswith("while "):
                        while self.expr(_strip(s[6:].strip(), "do"), scope):
                            b = self._run_loop_body(n, scope)
                            if b:
                                if b.count > 1: b.count -= 1; raise b
                                broke = True; break
                    elif s.startswith(("for ", "foreach ")):
                        m = re.match(r"(?:for|foreach)\s+([A-Za-z_]\w*)\s+in\s+(.+?)\s+do$", s)
                        if not m: raise SyntaxError("invalid for/foreach loop", n.line)
                        for value in self.expr(m.group(2), scope):
                            scope.values[m.group(1)] = value; b = self._run_loop_body(n, scope)
                            if b:
                                if b.count > 1: b.count -= 1; raise b
                                broke = True; break
                    elif s.startswith("repeat"):
                        m = re.match(r"repeat(?:\s+(\d+))?\s*do$", s)
                        if not m: raise SyntaxError("invalid repeat loop", n.line)
                        count, k = int(m.group(1)) if m.group(1) else None, 0
                        while count is None or k < count:
                            b = self._run_loop_body(n, scope)
                            if b:
                                if b.count > 1: b.count -= 1; raise b
                                broke = True; break
                            k += 1
                    elif s.startswith("forever"):
                        while True:
                            b = self._run_loop_body(n, scope)
                            if b:
                                if b.count > 1: b.count -= 1; raise b
                                broke = True; break
                    else:
                        while not self.expr(_strip(s[6:].strip(), "do"), scope):
                            b = self._run_loop_body(n, scope)
                            if b:
                                if b.count > 1: b.count -= 1; raise b
                                broke = True; break
                except Exception as exc: error = exc
                finally:
                    if "finally" in clauses: self.exec_block(clauses["finally"].children or [], Scope(scope))
                if error is not None: raise error
                if "else" in clauses and not broke: self.exec_block(clauses["else"].children or [], Scope(scope))
                i = j; continue

            if s.startswith("return"):
                r = s[6:].strip()
                value = tuple(self.expr(x.strip(), scope) for x in r.split(",")) if "," in r else (self.expr(r, scope) if r else None)
                raise ReturnSignal(value)
            if s.startswith("break"):
                parts = s.split(); raise BreakSignal(int(parts[1]) if len(parts) > 1 else 1)
            if s.startswith("raise "):
                e = self.expr(s[6:].strip(), scope); raise e if isinstance(e, Exception) else RuntimeError(str(e))
            if s.startswith("await "):
                self.await_value(self.expr(s[6:].strip(), scope)); i += 1; continue
            if s.startswith("do "):
                self.expr(s[3:], scope); i += 1; continue
            if "=" in s and not any(x in s for x in ("==", "!=", "<=", ">=")):
                lhs, rhs = s.split("=", 1); self.assign(lhs, self.expr(rhs, scope), scope); i += 1; continue
            self.expr(s, scope); i += 1

    def run(self, source):
        self.exec_block(Parser(source).parse(), self.root)
        return self.root


def compile_source(source, filename=None):
    return Parser(source).parse()


def execute(source, filename=None, scope=None):
    e = Engine(filename)
    if scope is not None: e.root = scope
    e.run(source)
    return e.root


def run(source_or_path):
    p = Path(source_or_path)
    if p.exists() and p.suffix == ".hk":
        return Engine(str(p)).run(p.read_text(encoding="utf-8"))
    return Engine().run(str(source_or_path))
