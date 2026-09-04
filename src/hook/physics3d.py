"""Small deterministic 3D physics layer for HOOK games and simulations."""
from __future__ import annotations
from dataclasses import dataclass, field
from .engine3d import AABB, Object3D, Vec3, mesh_bounds

@dataclass
class RigidBody3D:
    object:Object3D
    mass:float=1.0
    velocity:Vec3=field(default_factory=lambda:Vec3(0,0,0))
    acceleration:Vec3=field(default_factory=lambda:Vec3(0,0,0))
    gravity:bool=True
    static:bool=False
    restitution:float=.15
    friction:float=.8
    grounded:bool=False
    @property
    def inv_mass(self): return 0. if self.static or self.mass<=0 else 1./self.mass

class PhysicsWorld3D:
    def __init__(self,gravity=Vec3(0,-9.81,0)):
        self.gravity=gravity; self.bodies=[]; self.colliders=[]
    def add(self,body): self.bodies.append(body); return body
    def add_static(self,obj,box=None): self.colliders.append((obj,box or mesh_bounds(obj.mesh,obj.transform))); return obj
    def _box(self,b): return mesh_bounds(b.object.mesh,b.object.transform)
    def step(self,dt):
        dt=max(0.,float(dt))
        for b in self.bodies:
            if b.static: continue
            a=b.acceleration+(self.gravity if b.gravity else Vec3(0,0,0)); b.velocity=b.velocity+a*dt; b.object.transform.position=b.object.transform.position+b.velocity*dt; b.grounded=False
            box=self._box(b)
            for _,other in self.colliders:
                if not box.intersects(other): continue
                if box.minimum.y<other.maximum.y and b.velocity.y<=0:
                    delta=other.maximum.y-box.minimum.y; b.object.transform.position=b.object.transform.position+Vec3(0,delta,0); b.velocity=Vec3(b.velocity.x,-b.velocity.y*b.restitution,b.velocity.z); b.grounded=True
                    if abs(b.velocity.y)<.05:b.velocity=Vec3(b.velocity.x,0,b.velocity.z)
                box=self._box(b)
        return self
    def body(self,obj,**kwargs): return self.add(RigidBody3D(obj,**kwargs))

@dataclass(frozen=True)
class SphereCollider:
    center:Vec3; radius:float
    def overlaps_aabb(self,box):
        x=max(box.minimum.x,min(self.center.x,box.maximum.x)); y=max(box.minimum.y,min(self.center.y,box.maximum.y)); z=max(box.minimum.z,min(self.center.z,box.maximum.z)); d=Vec3(self.center.x-x,self.center.y-y,self.center.z-z); return d.dot(d)<=self.radius*self.radius

__all__=['RigidBody3D','PhysicsWorld3D','SphereCollider']
