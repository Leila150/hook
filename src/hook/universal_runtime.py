"""Universal optional runtime adapters for HOOK.

The adapters are deliberately dependency-light: features that need third-party
libraries expose a small fallback instead of making HOOK itself depend on them.
"""
from __future__ import annotations

import json
import math
import time
import wave
from pathlib import Path
from types import SimpleNamespace


class Graphics:
    def __init__(self):
        self.backend = None
        try:
            import tkinter
            self.backend = tkinter
        except Exception:
            pass

    def window(self, title="HOOK", width=800, height=600):
        if not self.backend:
            raise RuntimeError("graphics backend is unavailable")
        root = self.backend.Tk()
        root.title(title)
        root.geometry(f"{width}x{height}")
        return root

    def canvas(self, root, width=800, height=600):
        c = self.backend.Canvas(root, width=width, height=height)
        c.pack()
        return c


class Audio:
    """Small WAV reader/writer; playback is intentionally backend-neutral."""
    def info(self, path):
        with wave.open(str(path), "rb") as w:
            return {"channels": w.getnchannels(), "sample_width": w.getsampwidth(),
                    "rate": w.getframerate(), "frames": w.getnframes(),
                    "duration": w.getnframes() / max(w.getframerate(), 1)}

    def read(self, path):
        with wave.open(str(path), "rb") as w:
            return SimpleNamespace(**self.info(path), frames=w.readframes(w.getnframes()))


class Input:
    def key(self, key, pressed=False):
        return bool(pressed)


class Physics:
    def __init__(self, gravity=9.80665):
        self.gravity = float(gravity)

    def fall(self, height, initial_velocity=0):
        h = float(height); v = float(initial_velocity)
        if h <= 0 and v <= 0: return 0.0
        return (-v + math.sqrt(max(0.0, v * v + 2 * self.gravity * h))) / self.gravity

    def position(self, y, velocity, seconds):
        return float(y) + float(velocity) * float(seconds) - 0.5 * self.gravity * float(seconds) ** 2

    def velocity(self, velocity, seconds):
        return float(velocity) - self.gravity * float(seconds)


class AI:
    """Dependency-free AI primitives plus optional provider adapters.

    ``json`` and tensor-like helpers are local; network model calls are exposed
    through a generic callable so HOOK does not hard-code a provider.
    """
    def __init__(self): self.models = {}

    def register(self, name, model):
        self.models[str(name)] = model
        return model

    def predict(self, model, value, **kwargs):
        target = self.models.get(model, model) if isinstance(model, str) else model
        if not callable(target): raise TypeError("AI model must be callable")
        return target(value, **kwargs)

    def pipeline(self, fn): return fn

    def softmax(self, values):
        xs = [float(x) for x in values]
        if not xs: return []
        m = max(xs); ex = [math.exp(x - m) for x in xs]; total = sum(ex)
        return [x / total for x in ex]

    def argmax(self, values): return max(range(len(values)), key=lambda i: values[i])


class AppRuntime:
    def __init__(self): self.started_at = None
    def start(self): self.started_at = time.time(); return self
    def uptime(self): return 0 if self.started_at is None else time.time() - self.started_at


class UniversalModules:
    def __init__(self):
        self.values = {
            "graphics": Graphics(), "audio": Audio(), "input": Input(),
            "physics": Physics(), "ai": AI(), "app_runtime": AppRuntime(),
        }


def install_universal_runtime(engine_cls):
    """Add universal modules without replacing the existing runtime layer."""
    if getattr(engine_cls, "_universal_runtime_installed", False):
        return engine_cls
    old = engine_cls._builtins

    def builtins(self):
        old(self)
        universal = UniversalModules()
        if hasattr(self, "standard_modules"):
            self.standard_modules.values.update(universal.values)
        else:
            self.standard_modules = universal
        for name, value in universal.values.items():
            self.root.values.setdefault(name, value)

    engine_cls._builtins = builtins
    engine_cls._universal_runtime_installed = True
    return engine_cls
