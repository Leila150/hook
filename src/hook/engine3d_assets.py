"""Asset and collision helpers for the HOOK 3D engine.

Kept separate from the core renderer so the software renderer stays small and
portable on Android and other constrained hosts.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .engine3d import AABB, Color, Mesh3D, Ray3D, Texture2D, Transform, Vec3, mesh_bounds


@dataclass(frozen=True)
class Hit3D:
    distance: float
    point: Vec3
    normal: Vec3
    object: object | None = None


def ray_aabb(ray: Ray3D, box: AABB, max_distance=float("inf")) -> Hit3D | None:
    """Return the first ray/AABB hit using the slab algorithm."""
    tmin, tmax = 0.0, max_distance
    for origin, direction, lo, hi in (
        (ray.origin.x, ray.direction.x, box.minimum.x, box.maximum.x),
        (ray.origin.y, ray.direction.y, box.minimum.y, box.maximum.y),
        (ray.origin.z, ray.direction.z, box.minimum.z, box.maximum.z),
    ):
        if abs(direction) < 1e-12:
            if origin < lo or origin > hi:
                return None
            continue
        a, b = (lo-origin)/direction, (hi-origin)/direction
        if a > b: a, b = b, a
        tmin, tmax = max(tmin, a), min(tmax, b)
        if tmin > tmax: return None
    point = ray.at(tmin)
    eps=1e-6
    if abs(point.x-box.minimum.x)<eps: normal=Vec3(-1,0,0)
    elif abs(point.x-box.maximum.x)<eps: normal=Vec3(1,0,0)
    elif abs(point.y-box.minimum.y)<eps: normal=Vec3(0,-1,0)
    elif abs(point.y-box.maximum.y)<eps: normal=Vec3(0,1,0)
    elif abs(point.z-box.minimum.z)<eps: normal=Vec3(0,0,-1)
    else: normal=Vec3(0,0,1)
    return Hit3D(tmin, point, normal)


def ray_triangle(ray: Ray3D, a: Vec3, b: Vec3, c: Vec3, max_distance=float("inf")) -> Hit3D | None:
    """Moller-Trumbore ray/triangle intersection."""
    e1=b-a; e2=c-a; h=ray.direction.cross(e2); det=e1.dot(h)
    if abs(det)<1e-9: return None
    inv=1.0/det; s=ray.origin-a; u=inv*s.dot(h)
    if u<0 or u>1: return None
    q=s.cross(e1); v=inv*ray.direction.dot(q)
    if v<0 or u+v>1: return None
    t=inv*e2.dot(q)
    if t<0 or t>max_distance: return None
    return Hit3D(t,ray.at(t),e1.cross(e2).normalized())


def ray_mesh(ray: Ray3D, mesh: Mesh3D, transform: Transform | None=None, max_distance=float("inf")) -> Hit3D | None:
    """Find the nearest triangle hit in a mesh."""
    vs=mesh.transformed(transform or Transform()); best=None
    for i,j,k in mesh.triangles:
        hit=ray_triangle(ray,vs[i],vs[j],vs[k],max_distance if best is None else best.distance)
        if hit is not None and (best is None or hit.distance<best.distance): best=hit
    return best


class AssetLoader:
    """Central asset loader with intentionally small, dependency-free formats."""
    @staticmethod
    def mesh(path, material=None):
        suffix=Path(path).suffix.lower()
        if suffix==".obj": return Mesh3D.from_obj(path, material)
        raise ValueError(f"unsupported 3D mesh format: {suffix or '<none>'}; supported: .obj")

    @staticmethod
    def texture(path):
        suffix=Path(path).suffix.lower()
        if suffix==".ppm": return Texture2D.ppm(path)
        raise ValueError(f"unsupported texture format: {suffix or '<none>'}; supported: .ppm")


class CollisionWorld:
    """Simple broad-phase AABB world for small games and prototypes."""
    def __init__(self): self.items=[]
    def add(self,obj,box=None):
        box=box or mesh_bounds(obj.mesh,obj.transform)
        self.items.append((obj,box)); return obj
    def rebuild(self): self.items=[(o,mesh_bounds(o.mesh,o.transform)) for o,_ in self.items]
    def overlaps(self,box): return [o for o,b in self.items if b.intersects(box)]
    def raycast(self,ray,max_distance=float("inf")):
        best=None
        for obj,box in self.items:
            broad=ray_aabb(ray,box,max_distance if best is None else best.distance)
            if broad is None: continue
            hit=ray_mesh(ray,obj.mesh,obj.transform,max_distance if best is None else best.distance)
            if hit is not None and (best is None or hit.distance<best.distance): best=Hit3D(hit.distance,hit.point,hit.normal,obj)
        return best


__all__=["Hit3D","ray_aabb","ray_triangle","ray_mesh","AssetLoader","CollisionWorld"]
