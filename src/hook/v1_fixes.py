"""Correctness fixes for the HOOK 1.x runtime."""
from __future__ import annotations
import asyncio
import threading


def install_v1_fixes(engine_cls):
    if getattr(engine_cls, "_hook_v1_fixes_installed", False):
        return engine_cls

    # Scope and loop semantics belong to engine.py; do not monkey-patch them.
    def await_value(self, value):
        if not asyncio.iscoroutine(value):
            return value
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(value)
        result, error = [], []
        def runner():
            try:
                result.append(asyncio.run(value))
            except BaseException as exc:
                error.append(exc)
        thread = threading.Thread(target=runner, daemon=True)
        thread.start(); thread.join()
        if error:
            raise error[0]
        return result[0] if result else None

    engine_cls.await_value = await_value
    engine_cls._hook_v1_fixes_installed = True
    return engine_cls


__all__ = ["install_v1_fixes"]
