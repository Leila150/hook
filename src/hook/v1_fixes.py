"""Correctness fixes for the HOOK 1.x runtime."""
from __future__ import annotations

import asyncio
import threading


def install_v1_fixes(engine_cls):
    if getattr(engine_cls, "_hook_v1_fixes_installed", False):
        return engine_cls

    from .engine import Scope
    old_set = Scope.set

    def set_value(self, key, value, kind=None):
        if kind == "const":
            target = self if self.function else self.file_scope
            if key in target.const:
                raise RuntimeError(f"constant '{key}' cannot be reassigned")
            target.values[key] = value
            target.const.add(key)
            return target

        # An unqualified assignment updates an existing variable instead of
        # silently creating a new phone-global shadow. If the name does not
        # exist yet, preserve HOOK's scope rules: function code creates a
        # folder-global and top-level code creates a phone-global.
        if kind is None:
            owner = self._find_owner(key)
            if owner is not None:
                if key in owner.const:
                    raise RuntimeError(f"constant '{key}' cannot be reassigned")
                owner.values[key] = value
                return owner
            target = self.folder_scope if self.function else self.phone_scope
            if key in target.const:
                raise RuntimeError(f"constant '{key}' cannot be reassigned")
            target.values[key] = value
            return target

        return old_set(self, key, value, kind)

    Scope.set = set_value

    # Loop bodies execute in the current scope. Creating a fresh child scope
    # made ordinary assignments such as `total = total + i` disappear after
    # every iteration and could turn stateful loops into infinite loops.
    def run_loop_body(self, node, scope):
        try:
            self.exec_block(node.children or [], scope)
        except Exception as exc:
            from .engine import BreakSignal
            if isinstance(exc, BreakSignal):
                return exc
            raise
        return None

    engine_cls._run_loop_body = run_loop_body

    old_await = engine_cls.await_value

    def await_value(self, value):
        if not asyncio.iscoroutine(value):
            return value
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(value)

        result = []
        error = []

        def runner():
            try:
                result.append(asyncio.run(value))
            except BaseException as exc:
                error.append(exc)

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join()
        if error:
            raise error[0]
        return result[0] if result else None

    engine_cls.await_value = await_value
    engine_cls._hook_v1_fixes_installed = True
    return engine_cls


__all__ = ["install_v1_fixes"]
