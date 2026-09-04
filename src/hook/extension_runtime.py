"""Execution hooks for HOOK extensions.

Extensions always receive the active scope. Operators receive evaluated values
rather than source reconstructed with repr().
"""
from __future__ import annotations
import re


def install_extension_runtime(engine_cls):
    if getattr(engine_cls, "_extension_runtime_installed", False):
        return engine_cls
    old_builtins = engine_cls._builtins
    old_expr = engine_cls.expr
    old_exec = engine_cls.exec_block

    def builtins(self):
        old_builtins(self)
        self.root.values["__hook_execute_block__"] = lambda nodes, scope=None: self.exec_block(nodes, scope or self.root)
        def custom_operator(name, left, right):
            ext = self.extensions.resolve(name, "Operator")
            if ext is None: raise RuntimeError(f"unknown HOOK operator '{name}'")
            obj = ext() if callable(ext) else ext
            handler = getattr(obj, "apply", None) or getattr(obj, "operate", None) or getattr(obj, "run", None)
            if handler is None: raise RuntimeError(f"operator '{name}' has no apply/operate/run method")
            return handler(left, right)
        self.root.values["__hook_operator__"] = custom_operator

    def expr(self, text, scope=None):
        s = text.strip()
        for d in self.extensions.operators():
            m = re.fullmatch(r"(.+?)\s+" + re.escape(d.name) + r"\s+(.+)", s)
            if m and d.name not in {"and", "or", "not", "nand", "nor", "xor", "xnor", "in", "is"}:
                left = old_expr(self, m.group(1), scope)
                right = old_expr(self, m.group(2), scope)
                return self.root.values["__hook_operator__"](d.name, left, right)
        return old_expr(self, text, scope)

    def exec_block(self, nodes, scope):
        prepared = []
        for n in nodes:
            text = n.text.strip(); transformed = text
            for d in list(self.extensions.processors()):
                if d.name in {"do", "then", "const"}: continue
                ext = d.value
                if not callable(ext): continue
                obj = ext(); fn = getattr(obj, "process", None)
                if fn:
                    result = fn(transformed)
                    if isinstance(result, str): transformed = result
            if transformed != text:
                from .engine import Node
                n = Node(transformed, n.line, n.indent, n.children); text = transformed
            keyword = text.split(None, 1)[0] if text else ""
            definition = self.extensions.resolve(keyword, "Statement")
            if definition is not None:
                obj = definition() if callable(definition) else definition
                handler = getattr(obj, "execute", None) or getattr(obj, "run", None)
                if handler is None: raise RuntimeError(f"statement '{keyword}' has no execute/run method")
                result = handler(text, n.children, scope)
                if result is not None: scope.values["_result"] = result
                continue
            loop_def = self.extensions.resolve(keyword, "Loop")
            if loop_def is not None:
                obj = loop_def() if callable(loop_def) else loop_def
                handler = getattr(obj, "execute", None) or getattr(obj, "run", None)
                if handler is None: raise RuntimeError(f"loop '{keyword}' has no execute/run method")
                result = handler(text, n.children, scope)
                if result is not None: scope.values["_result"] = result
                continue
            prepared.append(n)
        return old_exec(self, prepared, scope)

    engine_cls._builtins = builtins
    engine_cls.expr = expr
    engine_cls.exec_block = exec_block
    engine_cls._extension_runtime_installed = True
    return engine_cls
