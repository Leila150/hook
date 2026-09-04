"""Developer tooling for HOOK: formatter, linter, diagnostics and profiler."""
from __future__ import annotations
import re, time
from dataclasses import dataclass, field

@dataclass
class Diagnostic:
    severity: str; message: str; line: int = 0; column: int = 1

class Formatter:
    def format(self, source: str, spaces=4) -> str:
        out=[]
        for raw in source.splitlines():
            text=raw.strip()
            if not text: out.append(""); continue
            indent=len(raw)-len(raw.lstrip(" "))
            out.append(" " * indent + text)
        return "\n".join(out) + ("\n" if source.endswith("\n") else "")

class Linter:
    def check(self, source: str) -> list[Diagnostic]:
        diagnostics=[]; stack=[0]
        for no, raw in enumerate(source.splitlines(),1):
            if not raw.strip() or raw.lstrip().startswith(("#","--")): continue
            indent=len(raw)-len(raw.lstrip(" "))
            if "\t" in raw[:indent]: diagnostics.append(Diagnostic("error","tabs are not allowed; use spaces",no))
            if indent>stack[-1]: stack.append(indent)
            while indent<stack[-1]: stack.pop()
            if indent!=stack[-1]: diagnostics.append(Diagnostic("error","inconsistent indentation",no))
            if re.match(r"^(if|elif|while|for|foreach|repeat|until|forever)\\b", raw.strip()):
                keyword=raw.strip().split()[0]
                if not raw.strip().endswith("do") and keyword not in ("else",): diagnostics.append(Diagnostic("warning",f"{keyword} block should end with 'do'",no))
        return diagnostics

@dataclass
class ProfileRecord:
    name: str; calls: int=0; seconds: float=0.0

class Profiler:
    def __init__(self): self.records={}
    def measure(self,name,fn,*args,**kwargs):
        start=time.perf_counter(); self.records.setdefault(name,ProfileRecord(name)).calls+=1
        try: return fn(*args,**kwargs)
        finally: self.records[name].seconds += time.perf_counter()-start
    def report(self): return sorted((r for r in self.records.values()), key=lambda r:r.seconds, reverse=True)

class TestRunner:
    def run(self, tests):
        results=[]
        for name, fn in tests.items():
            start=time.perf_counter()
            try: fn(); results.append({"name":name,"passed":True,"seconds":time.perf_counter()-start})
            except Exception as exc: results.append({"name":name,"passed":False,"error":str(exc),"seconds":time.perf_counter()-start})
        return results
