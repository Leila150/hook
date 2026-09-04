from __future__ import annotations
import asyncio, ctypes, importlib, json, mmap, os, shutil, socket, subprocess, threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

class Namespace(SimpleNamespace):
    def __repr__(self): return "{" + ", ".join(f"{k}: {v!r}" for k,v in self.__dict__.items()) + "}"
class FileSystem:
    def read(self,p,encoding="utf-8"): return Path(p).read_text(encoding=encoding)
    def write(self,p,d,encoding="utf-8"):
        p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(str(d),encoding=encoding); return p
    def append(self,p,d,encoding="utf-8"):
        p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
        with p.open("a",encoding=encoding) as f:f.write(str(d))
        return p
    def bytes(self,p): return Path(p).read_bytes()
    def write_bytes(self,p,d): Path(p).write_bytes(bytes(d)); return Path(p)
    def exists(self,p): return Path(p).exists()
    def list(self,p="."): return [str(x) for x in Path(p).iterdir()]
    def mkdir(self,p): Path(p).mkdir(parents=True,exist_ok=True); return Path(p)
    def delete(self,p):
        x=Path(p); shutil.rmtree(x) if x.is_dir() else x.unlink(missing_ok=True)
    def copy(self,a,b): return shutil.copy2(a,b)
    def move(self,a,b): return shutil.move(a,b)
    def cwd(self): return os.getcwd()
    def absolute(self,p): return str(Path(p).resolve())
class Process:
    run=staticmethod(subprocess.run); popen=staticmethod(subprocess.Popen); call=staticmethod(subprocess.call); check_output=staticmethod(subprocess.check_output)
class Native:
    sizeof=staticmethod(ctypes.sizeof); cast=staticmethod(ctypes.cast); pointer=staticmethod(ctypes.pointer); c=ctypes
    @staticmethod
    def library(p): return ctypes.CDLL(p)
class Memory:
    allocate=staticmethod(ctypes.create_string_buffer); sizeof=staticmethod(ctypes.sizeof); mmap=staticmethod(mmap.mmap)
def make_math():
    import math
    return Namespace(**{n:getattr(math,n) for n in dir(math) if not n.startswith('_')})
def make_collections():
    import collections
    return Namespace(unique=lambda x:tuple(dict.fromkeys(x)),group=lambda x,n=1:[x[i:i+n] for i in range(0,len(x),n)],Counter=collections.Counter,deque=collections.deque)
def make_tensor():
    try:
        n=importlib.import_module('numpy'); return Namespace(array=n.array,zeros=n.zeros,ones=n.ones,arange=n.arange,reshape=n.reshape,raw=n)
    except ImportError: return Namespace(array=lambda x:list(x),zeros=lambda n:[0]*n,ones=lambda n:[1]*n,arange=lambda n:list(range(n)),reshape=lambda x,*s:x)
class AsyncRuntime:
    sleep=staticmethod(asyncio.sleep); gather=staticmethod(asyncio.gather); create_task=staticmethod(asyncio.create_task); run=staticmethod(asyncio.run); run_sync=staticmethod(asyncio.run)
class ThreadRuntime:
    def __init__(self,max_workers=None): self.pool=ThreadPoolExecutor(max_workers=max_workers)
    def submit(self,fn,*a,**kw): return self.pool.submit(fn,*a,**kw)
    def map(self,fn,v): return list(self.pool.map(fn,v))
    def shutdown(self,wait=True): self.pool.shutdown(wait=wait)
class ProcessRuntime:
    def __init__(self,max_workers=None): self.pool=ProcessPoolExecutor(max_workers=max_workers)
    def submit(self,fn,*a,**kw): return self.pool.submit(fn,*a,**kw)
    def map(self,fn,v): return list(self.pool.map(fn,v))
    def shutdown(self,wait=True): self.pool.shutdown(wait=wait)
class EventBus:
    def __init__(self): self._e={}; self._lock=threading.RLock()
    def on(self,n,f):
        with self._lock:self._e.setdefault(n,[]).append(f)
        return f
    def once(self,n,f):
        def w(*a,**kw): self.off(n,w); return f(*a,**kw)
        return self.on(n,w)
    def off(self,n,f):
        with self._lock:
            if n in self._e and f in self._e[n]: self._e[n].remove(f)
    def emit(self,n,*a,**kw):
        with self._lock:x=list(self._e.get(n,()))
        return [f(*a,**kw) for f in x]
@dataclass
class Route: method:str; path:str; handler:object
class APIServer:
    def __init__(self,host='127.0.0.1',port=8000): self.host=host; self.port=port; self.routes=[]; self.server=None
    def route(self,m,p,h): self.routes.append(Route(m.upper(),p,h)); return h
    def get(self,p,h): return self.route('GET',p,h)
    def post(self,p,h): return self.route('POST',p,h)
    def put(self,p,h): return self.route('PUT',p,h)
    def patch(self,p,h): return self.route('PATCH',p,h)
    def delete(self,p,h): return self.route('DELETE',p,h)
    def _match(self,p,a):
        x=[z for z in p.strip('/').split('/') if z]; y=[z for z in a.strip('/').split('/') if z]
        if len(x)!=len(y): return None
        d={}
        for u,v in zip(x,y):
            if u.startswith('{') and u.endswith('}'): d[u[1:-1].split(':',1)[0]]=v
            elif u!=v:return None
        return d
    def start(self,background=False):
        owner=self
        class H(BaseHTTPRequestHandler):
            def log_message(self,*a): pass
            def do_any(self):
                q=urlparse(self.path); n=int(self.headers.get('Content-Length',0) or 0); b=self.rfile.read(n).decode('utf-8','replace')
                try:b=json.loads(b) if b else None
                except json.JSONDecodeError:pass
                for r in owner.routes:
                    params=owner._match(r.path,q.path)
                    if r.method==self.command and params is not None:
                        try:v=r.handler(params,b,self.headers,parse_qs(q.query))
                        except TypeError:v=r.handler(params)
                        status,v=v if isinstance(v,tuple) and len(v)==2 else (200,v)
                        out=json.dumps(v).encode() if isinstance(v,(dict,list)) else str(v).encode()
                        self.send_response(status); self.send_header('Content-Type','application/json' if isinstance(v,(dict,list)) else 'text/plain'); self.send_header('Content-Length',str(len(out))); self.end_headers(); self.wfile.write(out); return
                self.send_response(404); self.end_headers()
            do_GET=do_POST=do_PUT=do_PATCH=do_DELETE=do_any
        self.server=ThreadingHTTPServer((self.host,self.port),H)
        if background: threading.Thread(target=self.server.serve_forever,daemon=True).start(); return self
        self.server.serve_forever(); return self
    def stop(self):
        if self.server:self.server.shutdown(); self.server.server_close()
class Web:
    def __init__(self): self.api=APIServer()
    def serve(self,html,host='127.0.0.1',port=8000): s=APIServer(host,port); s.get('/',lambda *_:html); return s.start()
class GUI:
    def available(self):
        try: import tkinter; return True
        except Exception:return False
    def window(self,title='HOOK',width=800,height=600):
        import tkinter as tk; r=tk.Tk(); r.title(title); r.geometry(f'{width}x{height}'); return r
    def label(self,r,text):
        import tkinter as tk; w=tk.Label(r,text=text); w.pack(); return w
    def button(self,r,text,command):
        import tkinter as tk; w=tk.Button(r,text=text,command=command); w.pack(); return w
class App:
    def __init__(self,name='HOOK App'): self.name=name; self.window=None
    def desktop(self,**kw): self.window=GUI().window(self.name,**kw); return self.window
    def run(self):
        if self.window:self.window.mainloop()
class Game:
    def __init__(self,title='HOOK Game',width=800,height=600): self.title=title; self.width=width; self.height=height; self.running=False; self.events=EventBus()
    def on(self,e,f): return self.events.on(e,f)
    def start(self): self.running=True; self.events.emit('start'); return self
    def stop(self): self.running=False; self.events.emit('stop')
class ExtensionRegistry:
    def __init__(self): self.statements={}; self.operators={}; self.types={}; self.loops={}; self.errors={}; self.dialects={}; self.behaviors={}
    def statement(self,n,h,replace=None): self.statements[n]=h; return n
    def operator(self,n,h): self.operators[n]=h; return n
    def type(self,n,d): self.types[n]=d; return d
    def loop(self,n,h): self.loops[n]=h; return h
    def error(self,n,e): self.errors[n]=e; return e
    def dialect(self,n,**r): self.dialects[n]=r; return r
    def behavior(self,n,h): self.behaviors[n]=h; return h
class PackageLoader:
    def __init__(self,e): self.engine=e; self.loaded={}
    def find(self,n):
        b=Path(self.engine.filename).parent if self.engine.filename else Path.cwd()
        for p in (b/(n+'.hk'),b/n/'__init__.hk',Path(n)/'__init__.hk',Path(n+'.hk')):
            if p.exists():return p.resolve()
        raise ImportError(f"package '{n}' not found")
    def load(self,n):
        if n in self.loaded:return self.loaded[n]
        p=self.find(n); from .engine import Engine; e=Engine(str(p)); e.run(p.read_text(encoding='utf-8')); x=Namespace(**e.root.values); self.loaded[n]=x; return x
class Network:
    socket=socket
    @staticmethod
    def tcp(host,port,timeout=None): return socket.create_connection((host,port),timeout)
class JSON:
    dumps=staticmethod(json.dumps); loads=staticmethod(json.loads); dump=staticmethod(json.dump); load=staticmethod(json.load)
class StandardModules:
    def __init__(self,e):
        self.values={'filesystem':FileSystem(),'fs':FileSystem(),'process':Process,'native':Native(),'memory':Memory(),'math':make_math(),'collections':make_collections(),'tensor':make_tensor(),'async':AsyncRuntime(),'async_runtime':AsyncRuntime(),'thread':ThreadRuntime(),'process_pool':ProcessRuntime(),'events':EventBus(),'event':EventBus(),'web':Web(),'api':APIServer(),'gui':GUI(),'app':App(),'game':Game(),'network':Network(),'json':JSON(),'extensions':ExtensionRegistry()}
        self.stdlib={'os','sys','re','time','datetime','pathlib','random','statistics','itertools','functools','typing','threading','subprocess','socket','json','sqlite3'}
    def get(self,n):
        if n in self.values:return self.values[n]
        if n in self.stdlib:
            m=importlib.import_module(n); self.values[n]=m; return m
        return None
def install_engine_extensions(cls):
    if getattr(cls,'_extensions_installed',False):return cls
    oldb,olde=cls._builtins,cls.exec_block
    def builtins(self):
        oldb(self); self.standard_modules=StandardModules(self); self.package_loader=PackageLoader(self); self.extensions=ExtensionRegistry(); self.root.values.update({'module':self.standard_modules,'packages':self.package_loader,'extensions':self.extensions})
    def exec_block(self,nodes,scope):
        keep=[]
        for n in nodes:
            s=n.text.strip(); m=__import__('re').match(r'^import\s+([A-Za-z_]\w*)$',s)
            if m:
                v=self.standard_modules.get(m.group(1)) or self.package_loader.load(m.group(1)); scope.values[m.group(1)]=v; continue
            m=__import__('re').match(r'^from\s+([A-Za-z_]\w*)\s+import\s+(.+)$',s)
            if m:
                v=self.standard_modules.get(m.group(1)) or self.package_loader.load(m.group(1))
                for x in m.group(2).split(','): scope.values[x.strip()]=getattr(v,x.strip())
                continue
            keep.append(n)
        return olde(self,keep,scope)
    cls._builtins=builtins; cls.exec_block=exec_block; cls._extensions_installed=True; return cls
