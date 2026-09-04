from hook.engine3d import Mesh3D, Transform, Vec3, Ray3D, AABB
from hook.engine3d_assets import CollisionWorld, ray_aabb, ray_mesh


def test_ray_aabb():
    hit=ray_aabb(Ray3D(Vec3(0,0,-5),Vec3(0,0,1)),AABB(Vec3(-1,-1,-1),Vec3(1,1,1)))
    assert hit is not None
    assert round(hit.distance,6)==4
    assert hit.normal==Vec3(0,0,-1)


def test_ray_mesh():
    mesh=Mesh3D.cube(2)
    hit=ray_mesh(Ray3D(Vec3(0,0,-5),Vec3(0,0,1)),mesh,Transform())
    assert hit is not None
    assert 3.9 < hit.distance < 4.1


def test_collision_world():
    mesh=Mesh3D.cube(2)
    class Obj: pass
    obj=Obj(); obj.mesh=mesh; obj.transform=Transform(position=Vec3(0,0,3))
    world=CollisionWorld(); world.add(obj)
    assert world.overlaps(AABB(Vec3(-.5,-.5,2.5),Vec3(.5,.5,3.5))) == [obj]
    hit=world.raycast(Ray3D(Vec3(0,0,-5),Vec3(0,0,1)))
    assert hit is not None and hit.object is obj
