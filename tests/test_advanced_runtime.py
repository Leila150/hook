import json
from pathlib import Path

from hook.ai_advanced import CharTokenizer, Linear, LayerNorm, TinyTransformer, Tensor
from hook.graphics_runtime import Camera, Mesh, SoftwareRenderer, Vec3
from hook.package_manager import Version, satisfies


def test_semver_constraints():
    assert Version.parse("1.2.3") > Version.parse("1.2.2")
    assert satisfies("1.4.0", "^1.2.0")
    assert not satisfies("2.0.0", "^1.2.0")
    assert satisfies("1.2.9", "~1.2.0")


def test_tensor_matmul_and_reshape():
    x=Tensor([[1,2],[3,4]])
    y=Tensor([[2,0],[1,2]])
    assert x.matmul(y).tolist()==[[4.0,4.0],[10.0,8.0]]
    assert x.reshape(4).shape==(4,)


def test_transformer_forward_and_checkpoint(tmp_path):
    tok=CharTokenizer("hello")
    model=TinyTransformer(len(tok.vocab),dim=4,hidden=8,layers=1,heads=1,seed=1)
    logits=model(tok.encode("hello"))
    assert logits.shape==(5,len(tok.vocab))
    p=tmp_path/"model.json"; model.save(p)
    assert json.loads(p.read_text())


def test_graphics_projection_and_renderer(tmp_path):
    camera=Camera(position=Vec3(0,0,-5))
    assert camera.project(Vec3(0,0,0),100,100) is not None
    r=SoftwareRenderer(64,64)
    pixels=r.render(Mesh.cube(1),Vec3(0,0,3))
    assert any(v for row in pixels for v in row)
    r.write_pgm(tmp_path/"cube.pgm",pixels)
    assert (tmp_path/"cube.pgm").exists()
