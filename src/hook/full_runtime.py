"""HOOK full-runtime services.

This module turns the previously described foundations into usable, dependency-free
Python implementations. Optional native tools are detected at runtime rather than
being faked.
"""
from __future__ import annotations

import asyncio
import ctypes
import json
import math
import os
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Iterable


# ---------------------------------------------------------------------------
# Autograd + neural-network runtime
# ---------------------------------------------------------------------------
class TensorValue:
    def __init__(self, data: Any, parents=(), backward=None, requires_grad=True):
        self.data = data if isinstance(data, list) else float(data)
        self.parents = tuple(parents)
        self.grad = 0.0
        self.requires_grad = requires_grad
        self._backward = backward or (lambda: None)

    def _scalar(self):
        if isinstance(self.data, list):
            raise TypeError("expected scalar tensor")
        return self.data

    def __add__(self, other):
        other = other if isinstance(other, TensorValue) else TensorValue(other, requires_grad=False)
        out = TensorValue(self._scalar() + other._scalar(), (self, other))
        def bw():
            if self.requires_grad: self.grad += out.grad
            if other.requires_grad: other.grad += out.grad
        out._backward = bw
        return out
    __radd__ = __add__

    def __neg__(self):
        out = TensorValue(-self._scalar(), (self,))
        out._backward = lambda: setattr(self, "grad", self.grad - out.grad)
        return out

    def __sub__(self, other): return self + (-other if isinstance(other, TensorValue) else -TensorValue(other, requires_grad=False))
    def __rsub__(self, other): return TensorValue(other, requires_grad=False) + (-self)

    def __mul__(self, other):
        other = other if isinstance(other, TensorValue) else TensorValue(other, requires_grad=False)
        out = TensorValue(self._scalar() * other._scalar(), (self, other))
        def bw():
            if self.requires_grad: self.grad += other._scalar() * out.grad
            if other.requires_grad: other.grad += self._scalar() * out.grad
        out._backward = bw
        return out
    __rmul__ = __mul__

    def __truediv__(self, other):
        other = other if isinstance(other, TensorValue) else TensorValue(other, requires_grad=False)
        return self * other.pow(-1)

    def pow(self, exponent):
        x = self._scalar()
        out = TensorValue(x ** exponent, (self,))
        out._backward = lambda: setattr(self, "grad", self.grad + exponent * (x ** (exponent - 1)) * out.grad)
        return out

    def backward(self):
        topo, seen = [], set()
        def visit(v):
            if id(v) in seen: return
            seen.add(id(v))
            for p in v.parents: visit(p)
            topo.append(v)
        visit(self)
        self.grad = 1.0
        for v in reversed(topo): v._backward()


@dataclass
class ParameterValue:
    value: float
    grad: float = 0.0


class LinearLayer:
    def __init__(self, inputs: int, outputs: int, seed: int | None = None):
        import random
        r = random.Random(seed)
        scale = math.sqrt(2.0 / max(1, inputs))
        self.weights = [[ParameterValue(r.uniform(-scale, scale)) for _ in range(inputs)] for _ in range(outputs)]
        self.bias = [ParameterValue(0.0) for _ in range(outputs)]

    @property
    def parameters(self): return [p for row in self.weights for p in row] + self.bias

    def __call__(self, x: Iterable[float]):
        x = list(map(float, x))
        return [sum(p.value * v for p, v in zip(row, x)) + b.value for row, b in zip(self.weights, self.bias)]


class ReLULayer:
    def __call__(self, x): return [max(0.0, float(v)) for v in x]


class SoftmaxLayer:
    def __call__(self, x):
        m = max(x); e = [math.exp(v - m) for v in x]; s = sum(e)
        return [v / s for v in e]


class NeuralModel:
    def __init__(self, *layers): self.layers = list(layers)
    def __call__(self, x):
        for layer in self.layers: x = layer(x)
        return x
    @property
    def parameters(self):
        return [p for l in self.layers if hasattr(l, "parameters") for p in l.parameters]
    def state_dict(self):
        out=[]
        for l in self.layers:
            if isinstance(l, LinearLayer):
                out.append({"type":"linear","weights":[[p.value for p in row] for row in l.weights],"bias":[p.value for p in l.bias]})
            else: out.append({"type":type(l).__name__})
        return out
    def save(self, path): Path(path).write_text(json.dumps(self.state_dict(), indent=2), encoding="utf-8")


class SGDOptimizer:
    def __init__(self, parameters, lr=0.01): self.parameters=list(parameters); self.lr=float(lr)
    def zero_grad(self):
        for p in self.parameters: p.grad=0.0
    def step(self):
        for p in self.parameters: p.value -= self.lr*p.grad


class AdamOptimizer(SGDOptimizer):
    def __init__(self, parameters, lr=0.001, beta1=0.9, beta2=0.999, eps=1e-8):
        super().__init__(parameters, lr); self.b1=beta1; self.b2=beta2; self.eps=eps; self.t=0; self.m={}; self.v={}
    def step(self):
        self.t += 1
        for p in self.parameters:
            k=id(p); self.m[k]=self.b1*self.m.get(k,0)+(1-self.b1)*p.grad; self.v[k]=self.b2*self.v.get(k,0)+(1-self.b2)*p.grad*p.grad
            mh=self.m[k]/(1-self.b1**self.t); vh=self.v[k]/(1-self.b2**self.t); p.value -= self.lr*mh/(math.sqrt(vh)+self.eps)


def mse_loss(pred, target):
    p,t=list(pred),list(target); return sum((a-b)**2 for a,b in zip(p,t))/max(1,len(p))


def cross_entropy(pred, target_index):
    probs=SoftmaxLayer()(pred); return -math.log(max(probs[int(target_index)],1e-15))


# ---------------------------------------------------------------------------
# Native compilation and FFI
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class NativeToolchain:
    compiler: str
    linker: str
    target: str


def find_native_compiler():
    for c in ("clang", "gcc", "cc"):
        p=shutil.which(c)
        if p: return p
    return None


def compile_c(source: str, output: str, *, shared=False, extra_args=()):
    compiler=find_native_compiler()
    if not compiler: raise RuntimeError("no C compiler found (install clang or gcc)")
    cmd=[compiler, "-O2", *extra_args]
    if shared: cmd += ["-shared", "-fPIC"]
    cmd += ["-x", "c", "-", "-o", output]
    r=subprocess.run(cmd,input=source,text=True,capture_output=True)
    if r.returncode: raise RuntimeError(r.stderr.strip() or "native compilation failed")
    return output


def load_library(path): return ctypes.CDLL(str(path))


class CFFI:
    def __init__(self, library): self.library=ctypes.CDLL(str(library))
    def function(self, name, restype=ctypes.c_int, argtypes=()):
        fn=getattr(self.library,name); fn.restype=restype; fn.argtypes=list(argtypes); return fn


# ---------------------------------------------------------------------------
# Android build project generator
# ---------------------------------------------------------------------------
@dataclass
class AndroidProject:
    root: Path
    package: str
    application: str = "HookApp"

    def write(self):
        root=self.root; src=root/"app/src/main/java"/Path(self.package.replace(".","/")); src.mkdir(parents=True,exist_ok=True)
        (root/"settings.gradle").write_text("pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\ndependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }\nrootProject.name='HookApp'\ninclude ':app'\n",encoding="utf-8")
        (root/"build.gradle").write_text("plugins { id 'com.android.application' version '8.5.2' apply false }\n",encoding="utf-8")
        (root/"app/build.gradle").write_text("plugins { id 'com.android.application' }\n\nandroid { namespace '%s'; compileSdk 35\n defaultConfig { applicationId '%s'; minSdk 23; targetSdk 35; versionCode 1; versionName '1.0' } }\n"%(self.package,self.package),encoding="utf-8")
        (src/(self.application+".java")).write_text("package %s;\nimport android.app.Activity;\nimport android.os.Bundle;\npublic class %s extends Activity { public void onCreate(Bundle b){super.onCreate(b);} }\n"%(self.package,self.application),encoding="utf-8")
        manifest=root/"app/src/main/AndroidManifest.xml"; manifest.parent.mkdir(parents=True,exist_ok=True)
        manifest.write_text("<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\"><application android:theme=\"@android:style/Theme.Material.Light.NoActionBar\" android:label=\"%s\"><activity android:name=\".%s\" android:exported=\"true\"><intent-filter><action android:name=\"android.intent.action.MAIN\"/><category android:name=\"android.intent.category.LAUNCHER\"/></intent-filter></activity></application></manifest>"%(self.application,self.application),encoding="utf-8")
        return root

    def build(self):
        self.write(); gradle=shutil.which("gradle") or shutil.which("./gradlew")
        if not gradle: raise RuntimeError("Android project generated; Gradle is not installed, so APK build cannot run here")
        return subprocess.run([gradle,"assembleDebug"],cwd=self.root,check=True).returncode


# ---------------------------------------------------------------------------
# GUI + 2D game primitives
# ---------------------------------------------------------------------------
class GUIRuntime:
    def window(self,title="HOOK",width=800,height=600):
        import tkinter as tk
        root=tk.Tk(); root.title(title); root.geometry(f"{width}x{height}"); return root
    def label(self,root,text):
        import tkinter as tk
        w=tk.Label(root,text=text); w.pack(); return w
    def button(self,root,text,command):
        import tkinter as tk
        w=tk.Button(root,text=text,command=command); w.pack(); return w


@dataclass
class GameEntity:
    x: float=0.0; y: float=0.0; vx: float=0.0; vy: float=0.0; width: float=32; height: float=32
    def update(self,dt,gravity=0): self.x+=self.vx*dt; self.y+=self.vy*dt; self.vy+=gravity*dt
    def intersects(self,other): return not (self.x+self.width<other.x or other.x+other.width<self.x or self.y+self.height<other.y or other.y+other.height<self.y)


class GameRuntime:
    def __init__(self,width=800,height=600): self.width=width; self.height=height; self.entities=[]; self.running=False
    def add(self,e): self.entities.append(e); return e
    def step(self,dt):
        for e in self.entities: e.update(dt)
    def run(self,fps=60,frames=None):
        self.running=True; dt=1.0/fps; n=0
        while self.running and (frames is None or n<frames): self.step(dt); n+=1; time.sleep(dt)
    def stop(self): self.running=False


# ---------------------------------------------------------------------------
# Database, sockets and process APIs
# ---------------------------------------------------------------------------
class Database:
    def __init__(self,path=":memory:"): self.connection=sqlite3.connect(path,check_same_thread=False); self.connection.row_factory=sqlite3.Row
    def execute(self,sql,params=()):
        cur=self.connection.execute(sql,params); self.connection.commit(); return [dict(r) for r in cur.fetchall()]
    def close(self): self.connection.close()


class TCPServer:
    def __init__(self,host="127.0.0.1",port=0): self.host=host; self.port=port; self.sock=None
    def serve(self,handler,backlog=64):
        self.sock=socket.socket(); self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); self.sock.bind((self.host,self.port)); self.port=self.sock.getsockname()[1]; self.sock.listen(backlog)
        while True:
            conn,addr=self.sock.accept(); threading.Thread(target=handler,args=(conn,addr),daemon=True).start()
    def close(self):
        if self.sock: self.sock.close()


# ---------------------------------------------------------------------------
# Tooling: formatter, linter, profiler, debugger, LSP
# ---------------------------------------------------------------------------
def format_hook(source: str, indent_size=4):
    out=[]; level=0
    for raw in source.splitlines():
        s=raw.strip()
        if not s: out.append(""); continue
        if s.startswith(("elif ","else", "finally")): level=max(0,level-1)
        out.append(" "*(level*indent_size)+s)
        if s.endswith(("then","do",":")): level+=1
    return "\n".join(out)+("\n" if source.endswith("\n") else "")


def lint_hook(source: str):
    diagnostics=[]
    for n,line in enumerate(source.splitlines(),1):
        if "\t" in line: diagnostics.append({"line":n,"code":"H001","message":"tabs are not allowed; use spaces"})
        if line.rstrip()!=line: diagnostics.append({"line":n,"code":"H002","message":"trailing whitespace"})
    return diagnostics


class Profiler:
    def __init__(self): self.records={}
    def measure(self,name,fn,*args,**kwargs):
        t=time.perf_counter(); result=fn(*args,**kwargs); elapsed=time.perf_counter()-t; self.records[name]=self.records.get(name,0)+elapsed; return result
    def report(self): return dict(sorted(self.records.items(),key=lambda x:x[1],reverse=True))


class Debugger:
    def __init__(self): self.breakpoints=set(); self.paused=False
    def breakpoint(self,line): self.breakpoints.add(int(line))
    def clear(self,line): self.breakpoints.discard(int(line))
    def should_break(self,line): return int(line) in self.breakpoints


class LSPServer:
    """Small stdio JSON-RPC LSP implementation for editors."""
    def __init__(self): self.documents={}
    def handle(self,msg):
        method=msg.get("method"); params=msg.get("params",{}); rid=msg.get("id")
        if method=="initialize": result={"capabilities":{"textDocumentSync":1,"documentFormattingProvider":True,"hoverProvider":True}}
        elif method=="textDocument/didOpen": self.documents[params["textDocument"]["uri"]]=params["textDocument"]["text"]; result=None
        elif method=="textDocument/didChange":
            td=params["textDocument"]; self.documents[td["uri"]]=params["contentChanges"][-1]["text"]; result=None
        elif method=="textDocument/formatting":
            uri=params["textDocument"]["uri"]; text=format_hook(self.documents.get(uri,"")); result=[{"range":{"start":{"line":0,"character":0},"end":{"line":10**6,"character":0}},"newText":text}]
        elif method=="shutdown": result=None
        else: result=None
        return {"jsonrpc":"2.0","id":rid,"result":result} if rid is not None else None


# ---------------------------------------------------------------------------
# Package and project tooling
# ---------------------------------------------------------------------------
@dataclass
class ProjectManifest:
    name: str
    version: str = "0.1.0"
    entry: str = "main.hk"
    dependencies: dict = field(default_factory=dict)

    def save(self,root):
        p=Path(root)/"hook.toml"
        lines=[f'name = {json.dumps(self.name)}',f'version = {json.dumps(self.version)}',f'entry = {json.dumps(self.entry)}','[dependencies]']
        lines += [f'{k} = {json.dumps(v)}' for k,v in self.dependencies.items()]
        p.write_text("\n".join(lines)+"\n",encoding="utf-8"); return p


class PackageInstaller:
    def __init__(self,root=None): self.root=Path(root or Path.home()/".hook"/"packages"); self.root.mkdir(parents=True,exist_ok=True)
    def install_local(self,source,name=None):
        src=Path(source); name=name or src.stem; dst=self.root/name; dst.mkdir(parents=True,exist_ok=True)
        if src.is_dir(): shutil.copytree(src,dst,dirs_exist_ok=True)
        else: shutil.copy2(src,dst/src.name)
        return dst
    def list(self): return sorted(p.name for p in self.root.iterdir())


# ---------------------------------------------------------------------------
# Source maps and execution diagnostics
# ---------------------------------------------------------------------------
@dataclass
class SourceSpan:
    generated_line:int; source_file:str; source_line:int; source_column:int=1

class SourceMap:
    def __init__(self): self.spans={}
    def add(self,generated_line,source_file,source_line,source_column=1): self.spans[int(generated_line)]=SourceSpan(generated_line,source_file,source_line,source_column)
    def resolve(self,line): return self.spans.get(int(line))


def exception_report(exc, source_file=None):
    return {"type":type(exc).__name__,"message":str(exc),"source":source_file,"traceback":traceback.format_exc()}


__all__=[
    "TensorValue","ParameterValue","LinearLayer","ReLULayer","SoftmaxLayer","NeuralModel","SGDOptimizer","AdamOptimizer","mse_loss","cross_entropy",
    "NativeToolchain","find_native_compiler","compile_c","load_library","CFFI","AndroidProject","GUIRuntime","GameEntity","GameRuntime",
    "Database","TCPServer","format_hook","lint_hook","Profiler","Debugger","LSPServer","ProjectManifest","PackageInstaller","SourceSpan","SourceMap","exception_report",
]
