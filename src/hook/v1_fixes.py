"""Correctness fixes for the HOOK 1.x runtime.

Only compatibility behaviour that cannot be expressed by the small legacy
engine is installed here. Core loop execution remains in engine.py.
"""
from __future__ import annotations
import asyncio
import threading


def install_v1_fixes(engine_cls):
    if getattr(engine_cls, "_hook_v1_fixes_installed", False):
        return engine_cls

    from .engine import Scope, HookFunction, HookObject, HookClass

    # HOOK assignment semantics: an unqualified assignment updates an existing
    # owner; a new assignment from a function belongs to the folder, while a
    # new top-level assignment belongs to phone-wide storage.
    def set_value(self, key, value, kind=None):
        if kind == "const":
            target = self if self.function else self.file_scope
            if key in target.const: raise RuntimeError(f"constant '{key}' cannot be reassigned")
            target.values[key] = value; target.const.add(key); return target
        if kind is None:
            owner = self._find_owner(key)
            target = owner or (self.folder_scope if self.function else self.phone_scope)
        elif kind == "local": target = self if self.function else self.file_scope
        elif kind == "global": target = self.file_scope if self.function else self.folder_scope
        elif kind == "all":
            if not self.function: raise SyntaxError("'all' variables are only valid inside functions")
            target = self.phone_scope
        elif kind == "reassign":
            target = self._find_owner(key)
            if target is None: raise NameError(f"cannot reassign undefined variable '{key}'")
        else: return original_set(self,key,value,kind)
        if key in target.const: raise RuntimeError(f"constant '{key}' cannot be reassigned")
        target.values[key] = value; return target

    original_set = Scope.set
    Scope.set = set_value

    # Async HOOK functions now yield a coroutine that runs the synchronous
    # evaluator off-thread instead of executing immediately at call time.
    async def call_async(self, args, kwargs):
        return await asyncio.to_thread(self._call, args, dict(kwargs))
    HookFunction._call_async = call_async

    # Use deterministic C3-style linearization for multiple inheritance.
    def mro(self):
        seqs=[list(base.mro()) for base in self.bases if hasattr(base,"mro")]+[list(self.bases)]
        result=[self]
        while any(seqs):
            seqs=[s for s in seqs if s]
            candidate=None
            for s in seqs:
                head=s[0]
                if not any(head in other[1:] for other in seqs): candidate=head;break
            if candidate is None: raise TypeError(f"inconsistent method resolution order for {self.name}")
            result.append(candidate)
            for s in seqs:
                if s and s[0] is candidate:s.pop(0)
        return result
    HookClass.mro = mro

    def find(self, key):
        for cls in self.mro():
            if key in cls.methods:return cls.methods[key]
        return None
    HookClass.find = find

    def get_attr(self,key):
        if key in self.attrs:return self.attrs[key]
        for cls in self.cls.mro():
            if key in cls.attrs:return cls.attrs[key]
            if key in cls.methods:
                fn=cls.methods[key]
                return lambda *a,**kw: fn(self,*a,**kw)
        raise AttributeError(f"object has no attribute '{key}'")
    HookObject.__getattr__ = get_attr

    def await_value(self, value):
        if not asyncio.iscoroutine(value): return value
        try: asyncio.get_running_loop()
        except RuntimeError: return asyncio.run(value)
        result=[]; error=[]
        def runner():
            try: result.append(asyncio.run(value))
            except BaseException as exc: error.append(exc)
        thread=threading.Thread(target=runner,daemon=True);thread.start();thread.join()
        if error: raise error[0]
        return result[0] if result else None
    engine_cls.await_value = await_value
    engine_cls._hook_v1_fixes_installed = True
    return engine_cls


__all__=["install_v1_fixes"]
