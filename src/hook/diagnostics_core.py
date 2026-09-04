"""Source-aware diagnostics, traceback frames and source maps."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class SourcePosition:
    file: str; line: int; column: int = 1

@dataclass
class TraceFrame:
    function: str; position: SourcePosition; source: str = ""

@dataclass
class Diagnostic:
    severity: str; message: str; position: SourcePosition; code: str = "HOOK000"

class SourceMap:
    def __init__(self): self.entries=[]
    def add(self,generated,original): self.entries.append((generated,original))
    def resolve(self,line):
        candidates=[x for x in self.entries if x[0] <= line]
        return max(candidates,key=lambda x:x[0])[1] if candidates else None

class DiagnosticEngine:
    def __init__(self): self.items=[]
    def error(self,message,file,line,column=1,code="HOOK000"):
        d=Diagnostic("error",message,SourcePosition(str(file),line,column),code); self.items.append(d); return d
    def warning(self,message,file,line,column=1,code="HOOK001"):
        d=Diagnostic("warning",message,SourcePosition(str(file),line,column),code); self.items.append(d); return d
    def clear(self): self.items.clear()
    def format(self):
        return "\n".join(f"{d.position.file}:{d.position.line}:{d.position.column}: {d.severity} [{d.code}] {d.message}" for d in self.items)

class TracebackBuilder:
    def __init__(self): self.frames=[]
    def push(self,function,file,line,column=1,source=""): self.frames.append(TraceFrame(function,SourcePosition(str(file),line,column),source)); return self
    def pop(self):
        if self.frames: self.frames.pop()
        return self
    def render(self):
        return "\n".join(f"  at {f.function} ({f.position.file}:{f.position.line}:{f.position.column})" for f in reversed(self.frames))
