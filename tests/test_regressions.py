import asyncio

from hook.engine import Engine, Scope
from hook.web_framework import Request, Response, Router, WebApp
from hook.package_manager import PackageManager
from hook.ai_advanced import MultiHeadAttention, Tensor


def test_assignment_updates_existing_owner():
    engine = Engine()
    engine.root.values["x"] = 1
    engine.expr("x + 1", engine.root)
    engine.root.set("x", 2)
    assert engine.root.get("x") == 2


def test_web_typed_route_params_and_middleware_errors():
    app = WebApp(Router())
    seen = []
    def middleware(req, nxt):
        seen.append(req.path_only)
        return nxt(req)
    app.use(middleware)
    @app.get("/users/{id: num}")
    def user(req, id): return {"id": id}
    result = app.dispatch(Request("GET", "/users/12"))
    assert result.status == 200 and b'"id": 12' in result.body
    assert seen == ["/users/12"]
    assert app.dispatch(Request("GET", "/users/nope")).status == 404


def test_async_route():
    app = WebApp()
    @app.get("/async")
    async def route(req): return Response("ok")
    result = asyncio.run(app.dispatch_async(Request("GET", "/async")))
    assert result.body == b"ok"


def test_package_constraints_intersect(tmp_path):
    pm = PackageManager(tmp_path)
    pm.create("shared", "1.5.0")
    pm.create("a", "1.0.0", {"shared": ">=1.0"})
    pm.create("b", "1.0.0", {"shared": "<2.0"})
    result = pm.resolve({"a": "1.0.0", "b": "1.0.0"})
    assert result["shared"].version == "1.5.0"


def test_multi_head_attention_uses_all_heads():
    x = Tensor([[0.1, 0.2, 0.3, 0.4], [0.4, 0.3, 0.2, 0.1]])
    attention = MultiHeadAttention(4, heads=2, seed=7)
    out = attention(x)
    assert out.shape == (2, 4)


def test_request_invalid_json_is_value_error():
    try:
        Request("POST", "/", body=b"{").json()
    except ValueError as exc:
        assert "invalid JSON" in str(exc)
    else:
        raise AssertionError("invalid JSON was accepted")
