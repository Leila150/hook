"""Production-oriented web primitives used by HOOK."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import asyncio
import inspect
import json
import re


class Request:
    def __init__(self, method, path, headers=None, body=b""):
        self.method = method.upper(); self.path = path; parsed = urlparse(path)
        self.url = path; self.query = parsed.query; self.path_only = parsed.path
        self.headers = dict(headers or {}); self.body = body
    @property
    def text(self): return self.body.decode("utf-8", "replace") if isinstance(self.body, bytes) else str(self.body)
    def json(self):
        try: return json.loads(self.text)
        except (TypeError, ValueError) as exc: raise ValueError("invalid JSON request body") from exc
    def header(self, name, default=None):
        for key, value in self.headers.items():
            if key.lower() == name.lower(): return value
        return default


class Response:
    def __init__(self, body="", status=200, headers=None):
        if isinstance(body, (dict, list, tuple)):
            body=json.dumps(body, ensure_ascii=False); base={"Content-Type":"application/json; charset=utf-8"}
        elif not isinstance(body, bytes): body=str(body).encode("utf-8"); base={"Content-Type":"text/plain; charset=utf-8"}
        else: base={"Content-Type":"application/octet-stream"}
        base.update(headers or {}); self.body=body; self.status=self.status_code=int(status); self.headers=base
    @classmethod
    def json(cls,value,status=200,headers=None): return cls(value,status,headers)


class Router:
    def __init__(self): self.routes=[]; self.middleware=[]
    def add(self,method,path,handler):
        method=method.upper()
        if not path.startswith("/"): raise ValueError("route paths must start with '/'")
        self.routes.append((method,path,handler)); return handler
    def use(self,fn):
        if not callable(fn): raise TypeError("middleware must be callable")
        self.middleware.append(fn); return fn
    def match(self,method,path):
        method=method.upper()
        for m,pattern,handler in self.routes:
            if m!=method: continue
            names=[]; parts=[]; pos=0
            for hit in re.finditer(r"\{(\w+)(?::\s*([^}]+))?\}",pattern):
                parts.append(re.escape(pattern[pos:hit.start()])); name,typ=hit.group(1),hit.group(2); names.append((name,typ)); parts.append(r"([^/]+)"); pos=hit.end()
            parts.append(re.escape(pattern[pos:])); hit=re.fullmatch("".join(parts),path)
            if not hit: continue
            values=hit.groups(); converted=[]
            try:
                for (_,typ),value in zip(names,values):
                    if typ in {"num","int"}: value=int(value)
                    elif typ in {"decimal","dec","float"}: value=float(value)
                    elif typ in {"boolean","bool"}:
                        if value.lower() not in {"true","false","1","0"}: raise ValueError
                        value=value.lower() in {"true","1"}
                    converted.append(value)
            except ValueError: continue
            return handler,{name:value for (name,_),value in zip(names,converted)}
        return None,{}


class WebApp:
    def __init__(self,router=None): self.router=router or Router(); self.server=None
    def route(self,path,method="GET"): return lambda fn:self.router.add(method,path,fn)
    def get(self,path): return self.route(path,"GET")
    def post(self,path): return self.route(path,"POST")
    def put(self,path): return self.route(path,"PUT")
    def patch(self,path): return self.route(path,"PATCH")
    def delete(self,path): return self.route(path,"DELETE")
    def use(self,fn): return self.router.use(fn)
    async def _invoke_async(self,fn,req,params):
        value=fn(req,**params)
        return await value if inspect.isawaitable(value) else value
    def _invoke(self,fn,req,params):
        value=fn(req,**params)
        if inspect.isawaitable(value):
            try: asyncio.get_running_loop()
            except RuntimeError: return asyncio.run(value)
            raise RuntimeError("async route requires dispatch_async() while an event loop is running")
        return value
    async def dispatch_async(self,req):
        fn,params=self.router.match(req.method,req.path_only)
        if not fn:return Response("Not Found",404)
        async def call(index,request):
            if index>=len(self.router.middleware): return await self._invoke_async(fn,request,params)
            mw=self.router.middleware[index]
            if inspect.iscoroutinefunction(mw): return await mw(request,lambda r=request:call(index+1,r))
            result=mw(request,lambda r=request:call(index+1,r))
            return await result if inspect.isawaitable(result) else result
        result=await call(0,req); return result if isinstance(result,Response) else Response(result)
    def dispatch(self,req):
        fn,params=self.router.match(req.method,req.path_only)
        if not fn:return Response("Not Found",404)
        def call(index,request):
            if index>=len(self.router.middleware): return self._invoke(fn,request,params)
            mw=self.router.middleware[index]
            try: signature=inspect.signature(mw)
            except (TypeError,ValueError): signature=None
            if signature is not None:
                positional=[p for p in signature.parameters.values() if p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
                if len(positional)<2: result=mw(lambda r=request:call(index+1,r))
                else: result=mw(request,lambda r=request:call(index+1,r))
            else: result=mw(request,lambda r=request:call(index+1,r))
            if inspect.isawaitable(result): raise RuntimeError("async middleware requires dispatch_async()")
            return result
        result=call(0,req); return result if isinstance(result,Response) else Response(result)
    def serve(self,host="127.0.0.1",port=8000):
        app=self
        class Handler(BaseHTTPRequestHandler):
            def do_any(self):
                try:
                    length=int(self.headers.get("Content-Length","0")); req=Request(self.command,self.path,self.headers,self.rfile.read(length)); res=app.dispatch(req)
                except Exception as exc: res=Response({"error":str(exc)},500)
                self.send_response(res.status)
                for key,value in res.headers.items(): self.send_header(key,str(value))
                self.end_headers()
                if self.command!="HEAD": self.wfile.write(res.body)
            do_GET=do_POST=do_PUT=do_PATCH=do_DELETE=do_HEAD=do_OPTIONS=do_any
            def log_message(self,*args): return None
        self.server=ThreadingHTTPServer((host,int(port)),Handler); self.server.serve_forever()
    def stop(self):
        if self.server: self.server.shutdown(); self.server.server_close(); self.server=None


__all__=["Request","Response","Router","WebApp"]
