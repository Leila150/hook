"""AST-safe HOOK dialect and syntax-extension system."""
from __future__ import annotations
from dataclasses import dataclass, field
import re
from typing import Callable

@dataclass
class Dialect:
    name: str
    keywords: dict[str, str] = field(default_factory=dict)
    operators: dict[str, str] = field(default_factory=dict)
    processors: list[Callable[[str], str]] = field(default_factory=list)
    statements: dict[str, str] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

class DialectEngine:
    def __init__(self): self.dialects={}; self.active=None
    def register(self,dialect):
        if dialect.name in self.dialects: raise ValueError(f"dialect '{dialect.name}' is already registered")
        self.dialects[dialect.name]=dialect; return dialect
    def activate(self,name):
        if name not in self.dialects: raise KeyError(name)
        self.active=self.dialects[name]; return self.active
    @staticmethod
    def _replace_identifier(line,mapping):
        if not mapping:return line
        parts=re.split(r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|#[^\n]*|--[^\n]*)',line)
        for i in range(0,len(parts),2):
            for old,new in mapping.items(): parts[i]=re.sub(rf"\b{re.escape(old)}\b",new,parts[i])
        return "".join(parts)
    def transform(self,source):
        d=self.active
        if not d:return source
        out=[]
        for raw in source.splitlines(keepends=True):
            nl="\n" if raw.endswith("\n") else ""; body=raw[:-1] if nl else raw
            body=self._replace_identifier(body,{**d.keywords,**d.statements})
            body=self._replace_identifier(body,d.operators)
            for processor in d.processors: body=processor(body)
            out.append(body+nl)
        return "".join(out)
    def compile(self,source,name=None):
        if name is not None:self.activate(name)
        return self.transform(source)

class SyntaxExtension:
    def __init__(self,name,transform,priority=0): self.name=name; self.transform=transform; self.priority=priority
class ExtensionPipeline:
    def __init__(self): self.items=[]
    def add(self,extension): self.items.append(extension); self.items.sort(key=lambda x:x.priority); return extension
    def remove(self,name): self.items=[x for x in self.items if x.name!=name]
    def apply(self,source):
        for x in self.items: source=x.transform(source)
        return source
