"""Correctness fixes for the HOOK 1.0 compatibility layer."""
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
            target = self
            if not self.function:
                target = self.file_scope
            if key in target.const:
                raise RuntimeError(f"constant '{key}' cannot be reassigned")
            target.values[key] = value
            target.const.add(key)
            return target
        return old_set(self, key, value, kind)

    Scope.set = set_value

    old_await = engine_cls.await_value

    def await_value(self, value):
        if not asyncio.iscoroutine(value):
            return value
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(value)

        # A HOOK async function can be invoked while another event loop is
        # active. Run the nested coroutine on a dedicated thread instead of
        # returning a coroutine object or attempting nested asyncio.run().
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
