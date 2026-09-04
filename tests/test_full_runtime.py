from pathlib import Path

from hook.full_runtime import (
    TensorValue, LinearLayer, ReLULayer, SoftmaxLayer, NeuralModel,
    SGDOptimizer, AdamOptimizer, compile_c, find_native_compiler,
    AndroidProject, GameEntity, Database, format_hook, lint_hook,
    SourceMap, Profiler, Debugger, LSPServer, ProjectManifest,
)
from hook.completion import Serializer


def test_autograd():
    x = TensorValue(3.0)
    y = x * x + x
    y.backward()
    assert y.data == 12.0
    assert x.grad == 7.0


def test_neural_layers_and_optimizers():
    model = NeuralModel(LinearLayer(2, 3, seed=1), ReLULayer(), SoftmaxLayer())
    out = model([1, 2])
    assert len(out) == 3
    assert abs(sum(out) - 1) < 1e-9
    p = model.parameters[0]; p.grad = 1; old = p.value
    SGDOptimizer(model.parameters, lr=.1).step(); assert p.value != old
    p.grad = 1; AdamOptimizer(model.parameters).step()


def test_serializer_and_project(tmp_path):
    p = tmp_path / "data.hkd"
    Serializer.save(p, {"x": [1, 2]})
    assert Serializer.load(p)["x"] == [1, 2]
    assert ProjectManifest("demo").save(tmp_path).exists()


def test_game_database_and_tooling(tmp_path):
    e = GameEntity(vx=2); e.update(.5); assert e.x == 1
    db = Database(); db.execute("create table t(x integer)"); db.execute("insert into t values (?)", (4,))
    assert db.execute("select x from t")[0]["x"] == 4; db.close()
    assert format_hook("if True then\n    print(1)\n") == "if True then\n    print(1)\n"
    assert lint_hook("x = 1  \n")


def test_debug_lsp_and_sourcemap():
    sm = SourceMap(); sm.add(3, "main.hk", 9, 2); assert sm.resolve(3).source_line == 9
    d = Debugger(); d.breakpoint(4); assert d.should_break(4); d.clear(4); assert not d.should_break(4)
    r = LSPServer().handle({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}})
    assert r["result"]["capabilities"]["hoverProvider"] is True


def test_native_compiler_if_available(tmp_path):
    if not find_native_compiler(): return
    out = tmp_path / "libhook.so"; compile_c("int hook_add(int a,int b){return a+b;}\n", str(out), shared=True); assert out.exists()


def test_android_project_generation(tmp_path):
    root = AndroidProject(tmp_path / "app", "com.example.hook"); root.write()
    assert (tmp_path / "app/app/build.gradle").exists()
    assert (tmp_path / "app/app/src/main/AndroidManifest.xml").exists()
