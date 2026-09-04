"""HOOK's first-class language extension system.

Extension categories are explicit: Type, Error, Statement, Loop, Operator,
Language, and Processor. Processor is the miscellaneous language-processing
category.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import re

CATEGORIES = ("Type", "Error", "Statement", "Loop", "Operator", "Language", "Processor")

@dataclass
class ExtensionDefinition:
    name: str
    category: str
    value: Any = None
    bases: tuple[str, ...] = ()
    replaces: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

class ExtensionBase: category = "Processor"
class Type(ExtensionBase): category = "Type"
class Error(ExtensionBase): category = "Error"
class Statement(ExtensionBase): category = "Statement"
class Loop(ExtensionBase): category = "Loop"
class Operator(ExtensionBase): category = "Operator"
class Language(ExtensionBase): category = "Language"
class Processor(ExtensionBase): category = "Processor"
class ExtensionConflict(Exception): pass

class ExtensionRegistry:
    """Runtime registry for all HOOK language extensions and dialects."""
    def __init__(self):
        self.items = {c: {} for c in CATEGORIES}
        self.active = {c: {} for c in CATEGORIES}
        self.dialects: dict[str, ExtensionDefinition] = {}
        self.conflicts: dict[tuple[str, str], list[ExtensionDefinition]] = {}

    def _category(self, category):
        if category not in CATEGORIES: raise ValueError(f"unknown extension category: {category}")
        return category
    def register(self, name, category, value=None, bases=(), replaces=None, **metadata):
        category=self._category(category); d=ExtensionDefinition(str(name),category,value,tuple(map(str,bases)),replaces,metadata)
        old=self.items[category].get(d.name)
        if old is not None and old.value is not value:
            self.conflicts.setdefault((category,d.name),[old]).append(d); return d
        self.items[category][d.name]=d; self.active[category][replaces or d.name]=d
        if category=="Language": self.dialects[d.name]=d
        return d
    def register_class(self, cls, category=None):
        category=category or getattr(cls,"extension_category",None)
        if category not in CATEGORIES:return None
        bases=tuple(getattr(b,"name",getattr(b,"__name__",str(b))) for b in getattr(cls,"bases",()))
        return self.register(getattr(cls,"name",cls.__name__),category,cls,bases=bases)
    def resolve(self,name,category=None):
        if category:
            category=self._category(category); d=self.active[category].get(name) or self.items[category].get(name)
            return d.value if d else None
        for category in CATEGORIES:
            d=self.active[category].get(name)
            if d:return d.value
        return None
    def choose(self,name,category,extension_name):
        category=self._category(category); d=self.items[category].get(extension_name)
        if d is None:raise KeyError(extension_name)
        self.active[category][name]=d; return d.value
    def replace(self,target,replacement,category):
        category=self._category(category); d=replacement if isinstance(replacement,ExtensionDefinition) else self.items[category].get(str(replacement))
        if d is None:raise KeyError(replacement)
        self.active[category][target]=d; d.replaces=target; return d.value
    def unregister(self,name,category):
        category=self._category(category); self.items[category].pop(name,None)
        for key,d in list(self.active[category].items()):
            if d.name==name:self.active[category].pop(key,None)
    def list(self,category=None):
        if category:return list(self.items[self._category(category)].values())
        return [d for c in CATEGORIES for d in self.items[c].values()]
    def processors(self):return self.list("Processor")
    def statements(self):return self.list("Statement")
    def loops(self):return self.list("Loop")
    def operators(self):return self.list("Operator")
    def types(self):return self.list("Type")
    def errors(self):return self.list("Error")
    def languages(self):return self.list("Language")
    def dialect(self,name,bases=(),**metadata):
        bases=tuple(bases) if bases else ("Language",)
        if "Language" not in bases and not any(str(x) in self.dialects for x in bases):raise TypeError("a HOOK dialect must inherit from Language")
        return self.register(name,"Language",None,bases=bases,**metadata)
    def snapshot(self):return {c:[d.name for d in self.list(c)] for c in CATEGORIES}

BUILTIN_PROCESSORS=("do","then","const")

def install_extension_system(engine_cls):
    if getattr(engine_cls,"_extension_system_installed",False):return engine_cls
    old_builtins=engine_cls._builtins; old_exec=engine_cls.exec_block
    def builtins(self):
        old_builtins(self)
        from .engine import HookType
        self.extensions=ExtensionRegistry()
        for name in CATEGORIES:
            self.root.values[name]=HookType(name); self.types[name]=self.root.values[name]
        for name in BUILTIN_PROCESSORS:self.extensions.register(name,"Processor",name)
        self.root.values["extensions"]=self.extensions
    def exec_block(self,nodes,scope):
        # The language extension system permits symbolic extension names such
        # as class -+(Language, dialect_1):. The core class syntax still uses
        # identifiers, so temporarily give symbolic classes an internal name.
        aliases={}; prepared=[]
        for n in nodes:
            m=re.match(r"^class\s+([^A-Za-z_\s][^\s]*)\s*\(",n.text)
            if m:
                original=m.group(1); internal="__hook_symbolic_"+str(abs(hash(original)))
                aliases[internal]=original
                from .engine import Node
                prepared.append(Node(n.text.replace("class "+original,"class "+internal,1),n.line,n.indent,n.children))
            else: prepared.append(n)
        before=set(scope.values)
        result=old_exec(self,prepared,scope)
        for internal,original in aliases.items():
            if internal in scope.values:
                value=scope.values.pop(internal); value.name=original; scope.values[original]=value
        for name,value in list(scope.values.items()):
            if name in before or not hasattr(value,"bases"):continue
            bases=getattr(value,"bases",()); base_names={getattr(b,"name",str(b)) for b in bases}
            category=next((c for c in CATEGORIES if c in base_names),None)
            if category:self.extensions.register(name,category,value,bases=tuple(base_names))
        return result
    engine_cls._builtins=builtins; engine_cls.exec_block=exec_block; engine_cls._extension_system_installed=True
    return engine_cls
