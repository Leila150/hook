"""Stable extension/dialect pipeline. Extensions transform source before AST parsing."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass
class Dialect:
    name:str
    keywords:dict
    operators:dict
    processors:list
class DialectEngine:
    def __init__(self):self.dialects={};self.active=None
    def register(self,dialect):self.dialects[dialect.name]=dialect;return dialect
    def activate(self,name):
        if name not in self.dialects:raise KeyError(name)
        self.active=self.dialects[name];return self.active
    def transform(self,source):
        d=self.active
        if not d:return source
        for old,new in d.keywords.items():
            source=source.replace(old,new)
        for processor in d.processors:source=processor(source)
        return source
class SyntaxExtension:
    def __init__(self,name,transform):self.name=name;self.transform=transform
class ExtensionPipeline:
    def __init__(self):self.items=[]
    def add(self,extension):self.items.append(extension);return extension
    def apply(self,source):
        for x in self.items:source=x.transform(source)
        return source
