"""Production-oriented web primitives used by HOOK 1.0."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import inspect
import json
import re


class Request:
    def __init__(self, method, path, headers=None, body=b""):
        self.method = method.upper()
        self.path = path
        parsed = urlparse(path)
        self.url = path
        self.query = parsed.query
        self.path_only = parsed.path
        self.headers = dict(headers or {})
        self.body = body

    @property
    def text(self):
        return self.body.decode("utf-8", "replace") if isinstance(self.body, bytes) else str(self.body)

    def json(self):
        return json.loads(self.text)

    def header(self, name, default=None):
        return self.headers.get(name, default)


class Response:
    def __init__(self, body="", status=200, headers=None):
        if isinstance(body, (dict, list, tuple)):
            body = json.dumps(body, ensure_ascii=False)
            base = {"Content-Type": "application/json; charset=utf-8"}
        elif not isinstance(body, bytes):
            body = str(body).encode("utf-8")
            base = {"Content-Type": "text/plain; charset=utf-8"}
        else:
            base = {"Content-Type": "application/octet-stream"}
        base.update(headers or {})
        self.body = body
        self.status = int(status)
        self.status_code = self.status
        self.headers = base

    @classmethod
    def json(cls, value, status=200, headers=None):
        return cls(value, status, headers)


class Router:
    def __init__(self):
        self.routes = []
        self.middleware = []

    def add(self, method, path, handler):
        method = method.upper()
        if not path.startswith("/"):
            raise ValueError("route paths must start with '/'")
        self.routes.append((method, path, handler))
        return handler

    def use(self, fn):
        if not callable(fn):
            raise TypeError("middleware must be callable")
        self.middleware.append(fn)
        return fn

    def match(self, method, path):
        method = method.upper()
        for m, pattern, handler in self.routes:
            if m != method:
                continue
            names = re.findall(r"\{(\w+)(?::\s*[^}]+)?\}", pattern)
            rx = re.escape(pattern)
            rx = re.sub(r"\\\{\\w\+(?::\\s*\[\^\\}\]\+)?\\\}", r"([^/]+)", rx)
            # Simpler, type-agnostic route compiler; typed route annotations are metadata.
            rx = re.sub(r"\\\{\\w+(?::\\s*[^}]+)?\\\}", r"([^/]+)", re.escape(pattern))
            hit = re.fullmatch(rx, path)
            if hit:
                return handler, dict(zip(names, hit.groups()))
        return None, {}


class WebApp:
    def __init__(self, router=None):
        self.router = router or Router()

    def route(self, path, method="GET"):
        return lambda fn: self.router.add(method, path, fn)

    def get(self, path): return self.route(path, "GET")
    def post(self, path): return self.route(path, "POST")
    def put(self, path): return self.route(path, "PUT")
    def patch(self, path): return self.route(path, "PATCH")
    def delete(self, path): return self.route(path, "DELETE")
    def use(self, fn): return self.router.use(fn)

    def _invoke(self, fn, req, params):
        value = fn(req, **params)
        return value

    def dispatch(self, req):
        fn, params = self.router.match(req.method, req.path_only)
        if not fn:
            return Response("Not Found", 404)

        def call(index, request):
            if index >= len(self.router.middleware):
                return self._invoke(fn, request, params)
            mw = self.router.middleware[index]
            try:
                result = mw(request, lambda r=request: call(index + 1, r))
            except TypeError:
                result = mw(lambda r=request: call(index + 1, r), request)
            return result

        result = call(0, req)
        return result if isinstance(result, Response) else Response(result)

    def serve(self, host="127.0.0.1", port=8000):
        app = self

        class Handler(BaseHTTPRequestHandler):
            def do_any(self):
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    req = Request(self.command, self.path, self.headers, self.rfile.read(length))
                    res = app.dispatch(req)
                except Exception as exc:
                    res = Response({"error": str(exc)}, 500)
                self.send_response(res.status)
                for key, value in res.headers.items():
                    self.send_header(key, str(value))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(res.body)

            do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = do_any
            def log_message(self, *args):
                return None

        ThreadingHTTPServer((host, int(port)), Handler).serve_forever()


__all__ = ["Request", "Response", "Router", "WebApp"]
