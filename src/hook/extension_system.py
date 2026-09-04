"""HOOK's first-class language extension system.

Extension categories are deliberately small and explicit:
Type, Error, Statement, Loop, Operator, Language, and Processor.
Processor is the miscellaneous language-processing category.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

CATEGORIES = ("Type", "Error", "Statement", "Loop", "Operator", "Language", "Processor")

@dataclass
class ExtensionDefinition:
    name: str
    category: str
    value: Any = None
    bases: tuple[str, ...] = ()
    replaces: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

class ExtensionBase:
    category = "Processor"
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.extension_category = getattr(cls, "category", cls.__name__)

class Type(ExtensionBase): category = "Type"
class Error(ExtensionBase): category = "Error"
class Statement(ExtensionBase): category = "Statement"
class Loop(ExtensionBase): category = "Loop"
class Operator(ExtensionBase): category = "Operator"
class Language(ExtensionBase): category = "Language"
class Processor(ExtensionBase): category = "Processor"

class ExtensionConflict(Exception): pass

class ExtensionRegistry:
    """Registry for language extensions and dialect composition."""
    def __init__(self):
        self.items = {c: {} for c in CATEGORIES}
        self.active = {c: {} for c in CATEGORIES}
        self.dialects: dict[str, ExtensionDefinition] = {}
        self.conflicts: dict[str, list[ExtensionDefinition]] = {}

    def _category(self, category: str) -> str:
        if category not in CATEGORIES: raise ValueError(f"unknown extension category: {category}")
        return category

    def register(self, name, category, value=None, bases=(), replaces=None, **metadata):
        category = self._category(category)
        d = ExtensionDefinition(str(name), category, value, tuple(map(str, bases)), replaces, metadata)
        bucket = self.items[category]
        if d.name in bucket and bucket[d.name].value is not value:
            self.conflicts.setdefault(d.name, [bucket[d.name]]).append(d)
            return d
        bucket[d.name] = d
        if replaces:
            self.active[category][replaces] = d
        else:
            self.active[category][d.name] = d
        if category == "Language": self.dialects[d.name] = d
        return d

    def register_class(self, cls):
        category = getattr(cls, "extension_category", None)
        if category not in CATEGORIES: return None
        bases = tuple(getattr(b, "name", getattr(b, "__name__", str(b))) for b in getattr(cls, "bases", ()))
        return self.register(cls.name, category, cls, bases=bases)

    def resolve(self, name, category=None):
        if category:
            self._category(category)
            d = self.active[category].get(name) or self.items[category].get(name)
            if d: return d.value
        for c in CATEGORIES:
            d = self.active[c].get(name)
            if d: return d.value
        return None

    def choose(self, name, category, extension_name):
        """Explicitly resolve a collision; HOOK never guesses between packages."""
        category = self._category(category)
        candidates = self.items[category]
        if extension_name not in candidates: raise KeyError(extension_name)
        if name not in self.conflicts: self.conflicts[name] = [candidates[extension_name]]
        chosen = candidates[extension_name]
        self.active[category][name] = chosen
        return chosen.value

    def unregister(self, name, category):
        category = self._category(category)
        self.items[category].pop(name, None)
        self.active[category].pop(name, None)

    def list(self, category=None):
        if category:
            self._category(category)
            return list(self.items[category].values())
        return [d for c in CATEGORIES for d in self.items[c].values()]

    def processors(self): return self.list("Processor")
    def statements(self): return self.list("Statement")
    def loops(self): return self.list("Loop")
    def operators(self): return self.list("Operator")
    def types(self): return self.list("Type")
    def errors(self): return self.list("Error")
    def languages(self): return self.list("Language")

    def dialect(self, name, bases=(), **metadata):
        bases = tuple(bases) if bases else ("Language",)
        if "Language" not in bases and not any(str(x) in self.dialects for x in bases):
            raise TypeError("a HOOK dialect must inherit from Language")
        return self.register(name, "Language", metadata, bases=bases, **metadata)

    def snapshot(self):
        return {c: [d.name for d in self.list(c)] for c in CATEGORIES}

# The Processor category is intentionally miscellaneous. These are the v0.1
# built-ins that participate in syntax processing rather than being statements,
# loops, operators, types, errors, or languages.
BUILTIN_PROCESSORS = (
    "do", "then", "const",
)


def install_extension_system(engine_cls):
    """Install first-class extension registration into Engine."""
    if getattr(engine_cls, "_extension_system_installed", False): return engine_cls
    old_builtins = engine_cls._builtins
    old_exec = engine_cls.exec_block

    def builtins(self):
        old_builtins(self)
        self.extensions = ExtensionRegistry()
        # Language-level extension parents are HOOK values, so they can be
        # inherited from inside .hk files without exposing Python classes.
        for name in CATEGORIES:
            self.types.setdefault(name, self.root.values.get(name))
            self.root.values[name] = self.root.values.get(name) or self.types.get(name)
        for name in BUILTIN_PROCESSORS:
            self.extensions.register(name, "Processor", name)
        self.root.values["extensions"] = self.extensions
        self.root.values["Extension"] = ExtensionBase

    def exec_block(self, nodes, scope):
        before = set(scope.values)
        result = old_exec(self, nodes, scope)
        for name, value in list(scope.values.items()):
            if name in before: continue
            if not hasattr(value, "bases"): continue
            bases = getattr(value, "bases", ())
            base_names = {getattr(b, "name", getattr(b, "name", str(b))) for b in bases}
            category = next((c for c in CATEGORIES if c in base_names), None)
            if category:
                self.extensions.register(name, category, value, bases=tuple(base_names))
                if category == "Language": self.extensions.dialects[name] = self.extensions.items[category][name]
        return result

    engine_cls._builtins = builtins
    engine_cls.exec_block = exec_block
    engine_cls._extension_system_installed = True
    return engine_cls
