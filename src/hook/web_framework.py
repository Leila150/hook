"""Web routing/middleware foundation for HOOK's web package."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
import json,re
class Request:
    def __init__(self,method,path,headers=None,body=b''):self.method=method;self.path=path;self.query=urlparse(path).query;self.headers=dict(headers or {});self.body=body
    def json(self):return json.loads(self.body.decode())
class Response:
    def __init__(self,body='',status=200,headers=None):self.body=body if isinstance(body,bytes) else str(body).encode();self.status=status;self.headers=headers or {'Content-Type':'text/plain; charset=utf-8'}
class Router:
    def __init__(self):self.routes=[];self.middleware=[]
    def add(self,method,path,handler):self.routes.append((method.upper(),path,handler));return handler
    def use(self,fn):self.middleware.append(fn);return fn
    def match(self,method,path):
        for m,pattern,handler in self.routes:
            if m!=method.upper():continue
            names=re.findall(r'\{(\w+)(?::\s*[^}]+)?\}',pattern);rx=re.sub(r'\{\w+(?::\s*[^}]+)?\}',r'([^/]+)',pattern)
            hit=re.fullmatch(rx,path)
            if hit:return handler,dict(zip(names,hit.groups()))
        return None,{}
class WebApp:
    def __init__(self):self.router=Router()
    def route(self,path,method='GET'):
        return lambda fn:self.router.add(method,path,fn)
    def serve(self,host='127.0.0.1',port=8000):
        app=self
        class H(BaseHTTPRequestHandler):
            def do_any(self):
                length=int(self.headers.get('Content-Length','0'));req=Request(self.command,self.path,self.headers,self.rfile.read(length));fn,params=app.router.match(req.method,urlparse(req.path).path)
                if not fn:res=Response('Not Found',404)
                else:
                    try:res=fn(req,**params);res=res if isinstance(res,Response) else Response(json.dumps(res) if isinstance(res,(dict,list)) else res,headers={'Content-Type':'application/json' if isinstance(res,(dict,list)) else 'text/plain'})
                    except Exception as e:res=Response(str(e),500)
                self.send_response(res.status)
                for k,v in res.headers.items():self.send_header(k,v)
                self.end_headers();self.wfile.write(res.body)
            do_GET=do_POST=do_PUT=do_PATCH=do_DELETE=do_any
            def log_message(self,*a):pass
        server=ThreadingHTTPServer((host,int(port)),H);server.serve_forever()
