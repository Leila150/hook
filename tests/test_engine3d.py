import tempfile
from pathlib import Path
from hook.engine3d import Camera3D, Engine3D, Mesh3D, Transform, Vec3


def test_vec3_math():
    a=Vec3(1,2,3); b=Vec3(2,0,1)
    assert a+b == Vec3(3,2,4)
    assert a.cross(b) == Vec3(2,5,-4)
    assert round(a.dot(b),6)==5


def test_camera_projection():
    p=Camera3D().project(Vec3(0,0,2),800,600)
    assert p is not None and abs(p[0]-400)<1e-6 and abs(p[1]-300)<1e-6


def test_cube_transform():
    mesh=Mesh3D.cube(2)
    points=mesh.transformed(Transform(position=Vec3(1,2,3),scale=Vec3(2,2,2)))
    assert len(points)==8
    assert points[0]==Vec3(-1,0,1)


def test_engine_renders_frame():
    e=Engine3D(96,72)
    e.add_cube(position=Vec3(0,0,3))
    frame=e.frame()
    assert len(frame)==96*72*3
    assert any(v != frame[0] for v in frame)


def test_save_frame():
    e=Engine3D(32,24); e.add_cube(position=Vec3(0,0,3))
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"frame.ppm"
        e.save_frame(p)
        assert p.exists() and p.read_bytes().startswith(b"P6\n32 24\n255\n")
