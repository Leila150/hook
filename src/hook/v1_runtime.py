"""HOOK 1.0 integration layer.

This module turns the previously separate runtime subsystems into one public
runtime surface.  It deliberately keeps the language syntax in ``engine.py``
and provides adapters for HTTP, JSON, filesystem, concurrency, AI, games,
native interop, tooling, and package loading.
"""
from __future__ import annotations

import asyncio
import json as _json
import math
import os
import random
import re
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from .web_framework import Request, Response, Router, WebApp
from .concurrency import CancellationToken, Channel, TaskGroup, Scheduler, Mutex, Atom
from .ai_core import Tensor, tensor, softmax, argmax, relu, sigmoid, linear, Sequential, ModelRegistry
from .ai_training import Parameter, Optimizer, SGD, Adam, mse, binary_cross_entropy, Dataset
from .game_runtime import Color, Vec2, Entity, Scene, Game, GUI, Audio
from .interop import NativeLibrary, CInterop, CppInterop, RustInterop, ABI
from .memory import Pointer, MemoryManager, Unsafe
from .native_bindings import Ownership, Binding, NativeBindings
from .tooling import Formatter, Linter, Diagnostic, Profiler, TestRunner
from .package_manager import Package, PackageManager
from .dialects import Dialect, DialectEngine, SyntaxExtension, ExtensionPipeline

VERSION = "1.0.0"
LANGUAGE = "HOOK"


class Module:
    """Small attribute namespace used for built-in HOOK modules."""
    def __init__(self, name: str, **values: Any):
        self.__name__ = name
        self.__dict__.update(values)

    def __repr__(self) -> str:
        return f"module {self.__name__}"


class FeatureRegistry:
    """Registry of capabilities available to a HOOK runtime."""
    def __init__(self):
        self._features: dict[str, Any] = {}

    def register(self, name: str, value: Any) -> Any:
        self._features[name] = value
        return value

    def get(self, name: str, default: Any = None) -> Any:
        return self._features.get(name, default)

    def has(self, name: str) -> bool:
        return name in self._features

    def names(self) -> list[str]:
        return sorted(self._features)

    def __contains__(self, name: str) -> bool:
        return name in self._features

    def __getitem__(self, name: str) -> Any:
        return self._features[name]


class JSONModule(Module):
    def __init__(self):
        super().__init__("json", loads=_json.loads, dumps=_json.dumps,
                         load=_json.load, dump=_json.dump)


class OSModule(Module):
    def __init__(self):
        super().__init__("os", getcwd=os.getcwd, chdir=os.chdir,
                         listdir=os.listdir, makedirs=os.makedirs,
                         remove=os.remove, rename=os.rename, path=os.path,
                         environ=os.environ)


class MathModule(Module):
    def __init__(self):
        values = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
        super().__init__("math", **values)


class RandomModule(Module):
    def __init__(self):
        super().__init__("random", random=random.random, randint=random.randint,
                         choice=random.choice, choices=random.choices,
                         shuffle=random.shuffle, sample=random.sample,
                         uniform=random.uniform, seed=random.seed)


class PathModule(Module):
    def __init__(self):
        super().__init__("path", Path=Path, cwd=Path.cwd,
                         exists=lambda p: Path(p).exists(),
                         is_file=lambda p: Path(p).is_file(),
                         is_dir=lambda p: Path(p).is_dir())


class TimeModule(Module):
    def __init__(self):
        super().__init__("time", time=time.time, monotonic=time.monotonic,
                         sleep=time.sleep, perf_counter=time.perf_counter)


class AsyncModule(Module):
    def __init__(self):
        super().__init__("async", sleep=asyncio.sleep,
                         gather=asyncio.gather, create_task=asyncio.create_task)


def build_modules(engine) -> dict[str, Module]:
    app = WebApp()
    router = Router()
    modules = {
        "json": JSONModule(),
        "os": OSModule(),
        "math": MathModule(),
        "random": RandomModule(),
        "path": PathModule(),
        "time": TimeModule(),
        "async": AsyncModule(),
        "web": Module("web", app=app, router=router, Request=Request,
                       Response=Response, WebApp=WebApp, Router=Router),
        "api": Module("api", app=app, router=router),
        "concurrency": Module("concurrency", CancellationToken=CancellationToken,
                               Channel=Channel, TaskGroup=TaskGroup,
                               Scheduler=Scheduler, Mutex=Mutex, Atom=Atom),
        "ai": Module("ai", Tensor=Tensor, tensor=tensor, softmax=softmax,
                      argmax=argmax, relu=relu, sigmoid=sigmoid, linear=linear,
                      Sequential=Sequential, ModelRegistry=ModelRegistry,
                      Parameter=Parameter, Optimizer=Optimizer, SGD=SGD, Adam=Adam,
                      mse=mse, binary_cross_entropy=binary_cross_entropy,
                      Dataset=Dataset),
        "game": Module("game", Color=Color, Vec2=Vec2, Entity=Entity,
                        Scene=Scene, Game=Game, GUI=GUI, Audio=Audio),
        "native": Module("native", NativeLibrary=NativeLibrary, CInterop=CInterop,
                          CppInterop=CppInterop, RustInterop=RustInterop, ABI=ABI,
                          Ownership=Ownership, Binding=Binding,
                          NativeBindings=NativeBindings),
        "memory": Module("memory", Pointer=Pointer, MemoryManager=MemoryManager,
                          Unsafe=Unsafe),
        "tooling": Module("tooling", Formatter=Formatter, Linter=Linter,
                           Diagnostic=Diagnostic, Profiler=Profiler,
                           TestRunner=TestRunner),
        "packages": Module("packages", Package=Package, PackageManager=PackageManager),
        "dialects": Module("dialects", Dialect=Dialect, DialectEngine=DialectEngine,
                            SyntaxExtension=SyntaxExtension,
                            ExtensionPipeline=ExtensionPipeline),
    }
    return modules


def _safe_type(value):
    return type(value).__name__


def _feature_snapshot(engine):
    return {
        "language": LANGUAGE,
        "version": VERSION,
        "filename": engine.filename,
        "modules": sorted(getattr(engine, "modules", {})),
        "types": sorted(getattr(engine, "types", {})),
    }


def install_v1_runtime(engine_cls):
    """Install the 1.0 integration layer exactly once."""
    if getattr(engine_cls, "_hook_v1_installed", False):
        return engine_cls

    old_builtins = engine_cls._builtins
    old_exec = engine_cls.exec_block

    def builtins(self):
        old_builtins(self)
        self.modules = build_modules(self)
        self.features = FeatureRegistry()
        for name, module in self.modules.items():
            self.features.register(name, module)
        self.root.values.update(self.modules)
        self.root.values.update({
            "HOOK_VERSION": VERSION,
            "version": lambda: VERSION,
            "features": lambda: self.features.names(),
            "feature": lambda name: self.features.get(name),
            "typeof": _safe_type,
            "isinstance": isinstance,
            "enumerate": enumerate,
            "zip": zip,
            "sorted": sorted,
            "reversed": reversed,
            "any": any,
            "all": all,
            "open": open,
            "Path": Path,
            "env": os.environ,
            "sleep": time.sleep,
            "now": time.time,
            "snapshot": lambda: _feature_snapshot(self),
        })

    def exec_block(self, nodes, scope):
        # Module imports are resolved before the legacy executor sees them.
        remaining = []
        for node in nodes:
            text = node.text.strip()
            m = re.fullmatch(r"(?:from\s+([A-Za-z_]\w*)\s+)?import\s+([A-Za-z_]\w*)", text)
            if m:
                module_name, imported = m.group(1), m.group(2)
                if module_name:
                    module = self.modules.get(module_name)
                    if module is None:
                        remaining.append(node)
                        continue
                    value = getattr(module, imported, None)
                    if value is None:
                        raise ImportError(f"cannot import '{imported}' from '{module_name}'")
                    scope.values[imported] = value
                else:
                    module = self.modules.get(imported)
                    if module is None:
                        remaining.append(node)
                    else:
                        scope.values[imported] = module
                continue
            remaining.append(node)
        return old_exec(self, remaining, scope)

    engine_cls._builtins = builtins
    engine_cls.exec_block = exec_block
    engine_cls._hook_v1_installed = True
    return engine_cls


__all__ = [
    "VERSION", "LANGUAGE", "Module", "FeatureRegistry", "install_v1_runtime",
]
