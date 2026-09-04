"""HOOK 3D engine foundation with a software fallback and optional GPU path.

The design deliberately mirrors a mobile compatibility stack: HOOK owns the
scene/geometry API, while optional native/GPU backends are detected at runtime.
It never pretends that a GPU backend exists when it does not.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math, shutil
from typing import Iterable


@dataclass(frozen=True)
class Vec3:
    x: float; y: float; z: float
    def __add__(self, o): return Vec3(self.x+o.x, self.y+o.y, self.z+o.z)
    def __sub__(self, o): return Vec3(self.x-o.x, self.y-o.y, self.z-o.z)
    def __mul__(self, s): return Vec3(self.x*s, self.y*s, self.z*s)
    __rmul__ = __mul__
    def __truediv__(self, s): return Vec3(self.x/s, self.y/s, self.z/s)
    def dot(self, o): return self.x*o.x+self.y*o.y+self.z*o.z
    def cross(self, o): return Vec3(self.y*o.z-self.z*o.y, self.z*o.x-self.x*o.z, self.x*o.y-self.y*o.x)
    def length(self): return math.sqrt(self.dot(self))
    def normalized(self):
        n=self.length(); return self if n == 0 else self/n


@dataclass(frozen=True)
class Color:
    r: float=1.0; g: float=1.0; b: float=1.0; a: float=1.0
    def clamped(self): return Color(*(max(0.0,min(1.0,v)) for v in (self.r,self.g,self.b,self.a)))


@dataclass
class Transform:
    position: Vec3 = field(default_factory=lambda: Vec3(0,0,0))
    rotation: Vec3 = field(default_factory=lambda: Vec3(0,0,0))
    scale: Vec3 = field(default_factory=lambda: Vec3(1,1,1))
    def apply(self, p: Vec3) -> Vec3:
        q=Vec3(p.x*self.scale.x,p.y*self.scale.y,p.z*self.scale.z)
        rx,ry,rz=map(math.radians,(self.rotation.x,self.rotation.y,self.rotation.z))
        cx,sx=math.cos(rx),math.sin(rx); cy,sy=math.cos(ry),math.sin(ry); cz,sz=math.cos(rz),math.sin(rz)
        q=Vec3(q.x,cx*q.y-sx*q.z,sx*q.y+cx*q.z)
        q=Vec3(cy*q.x+sy*q.z,q.y,-sy*q.x+cy*q.z)
        q=Vec3(cz*q.x-sz*q.y,sz*q.x+cz*q.y,q.z)
        return q+self.position


@dataclass(frozen=True)
class Material:
    color: Color=Color()
    emission: float=0.0
    wireframe: bool=False


@dataclass
class Mesh3D:
    vertices: list[Vec3]
    triangles: list[tuple[int,int,int]]
    normals: list[Vec3] = field(default_factory=list)
    material: Material = field(default_factory=Material)

    @classmethod
    def cube(cls, size=1.0, material=None):
        s=float(size)/2
        v=[Vec3(x*s,y*s,z*s) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        t=[(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(3,2,6),(3,6,7),(1,5,6),(1,6,2),(0,3,7),(0,7,4)]
        return cls(v,t,material=material or Material())

    def transformed(self, transform): return [transform.apply(v) for v in self.vertices]


@dataclass
class Camera3D:
    position: Vec3=field(default_factory=lambda: Vec3(0,0,-5))
    rotation: Vec3=field(default_factory=lambda: Vec3(0,0,0))
    fov: float=70.0
    near: float=0.05
    far: float=10000.0

    def _view(self,p):
        q=p-self.position
        # inverse Euler rotation
        rx,ry,rz=map(math.radians,(-self.rotation.x,-self.rotation.y,-self.rotation.z))
        cx,sx=math.cos(rx),math.sin(rx); cy,sy=math.cos(ry),math.sin(ry); cz,sz=math.cos(rz),math.sin(rz)
        q=Vec3(q.x,cx*q.y-sx*q.z,sx*q.y+cx*q.z)
        q=Vec3(cy*q.x+sy*q.z,q.y,-sy*q.x+cy*q.z)
        return Vec3(cz*q.x-sz*q.y,sz*q.x+cz*q.y,q.z)

    def project(self,p,width,height):
        q=self._view(p)
        if q.z <= self.near or q.z >= self.far: return None
        f=1.0/math.tan(math.radians(self.fov)/2)
        return (width/2+(q.x*f/q.z)*width/2, height/2-(q.y*f/q.z)*height/2, q.z)


@dataclass
class Light:
    position: Vec3=field(default_factory=lambda: Vec3(2,3,-4))
    color: Color=Color(1,1,1,1)
    intensity: float=1.0
    ambient: float=0.15


@dataclass
class Object3D:
    mesh: Mesh3D
    transform: Transform=field(default_factory=Transform)
    name: str="object"
    visible: bool=True


class Scene3D:
    def __init__(self):
        self.objects=[]; self.lights=[Light()]; self.camera=Camera3D()
    def add(self,obj): self.objects.append(obj); return obj
    def cube(self,name="cube",size=1.0,position=None):
        o=Object3D(Mesh3D.cube(size),name=name)
        if position is not None: o.transform.position=position
        return self.add(o)
    def clear(self): self.objects.clear()


class Software3DRenderer:
    """CPU renderer: triangle rasterization, depth buffer and basic Lambert light."""
    def __init__(self,width=640,height=480):
        self.width=int(width); self.height=int(height)
        self.clear_color=Color(0.04,0.04,0.06,1)
    def _shade(self,normal,point,material,light):
        direction=(light.position-point).normalized()
        diffuse=max(0.0,normal.dot(direction))*light.intensity
        return material.color.r*(light.ambient+diffuse),material.color.g*(light.ambient+diffuse),material.color.b*(light.ambient+diffuse)
    def render(self,scene):
        w,h=self.width,self.height
        bg=scene.camera
        base=self.clear_color.clamped()
        pixels=[bytearray([int(base.r*255),int(base.g*255),int(base.b*255)])*w for _ in range(h)]
        depth=[[float('inf')]*w for _ in range(h)]
        for obj in scene.objects:
            if not obj.visible: continue
            verts=obj.mesh.transformed(obj.transform)
            for a,b,c in obj.mesh.triangles:
                world=(verts[a],verts[b],verts[c])
                normal=(world[1]-world[0]).cross(world[2]-world[0]).normalized()
                # Back-face culling in camera space.
                view=(world[0]-scene.camera.position).normalized()
                if normal.dot(view) >= 0: continue
                pts=[scene.camera.project(p,w,h) for p in world]
                if any(p is None for p in pts): continue
                ax,ay=pts[0][:2]; bx,by=pts[1][:2]; cx,cy=pts[2][:2]
                den=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
                if abs(den)<1e-9: continue
                lx=max(0,int(min(ax,bx,cx))); hx=min(w-1,int(max(ax,bx,cx)))
                ly=max(0,int(min(ay,by,cy))); hy=min(h-1,int(max(ay,by,cy)))
                sr=sg=sb=0.0
                if scene.lights: sr,sg,sb=self._shade(normal,world[0],obj.mesh.material,scene.lights[0])
                else: sr,sg,sb=obj.mesh.material.color.r,obj.mesh.material.color.g,obj.mesh.material.color.b
                rgb=bytes((int(max(0,min(1,sr))*255),int(max(0,min(1,sg))*255),int(max(0,min(1,sb))*255)))
                for y in range(ly,hy+1):
                    row=pixels[y]
                    for x in range(lx,hx+1):
                        u=((by-cy)*(x-cx)+(cx-bx)*(y-cy))/den
                        v=((cy-ay)*(x-cx)+(ax-cx)*(y-cy))/den
                        if u<0 or v<0 or u+v>1: continue
                        ww=1-u-v; z=u*pts[0][2]+v*pts[1][2]+ww*pts[2][2]
                        if z<depth[y][x]: depth[y][x]=z; row[x*3:x*3+3]=rgb
        return bytes(b for row in pixels for b in row)
    def write_ppm(self,path,rgb):
        with open(path,'wb') as f: f.write(f"P6\n{self.width} {self.height}\n255\n".encode()); f.write(rgb)


class GPU3DBackend:
    """Detects real graphics backends; rendering remains explicit about availability."""
    def __init__(self): self.backend=self.detect()
    @staticmethod
    def detect():
        for tool in ("vulkaninfo","glxinfo","eglinfo"):
            if shutil.which(tool): return tool
        return None
    @property
    def available(self): return self.backend is not None
    def info(self): return {"available":self.available,"backend":self.backend}


class Engine3D:
    def __init__(self,width=640,height=480):
        self.scene=Scene3D(); self.renderer=Software3DRenderer(width,height); self.gpu=GPU3DBackend()
    def add_cube(self,name="cube",size=1,position=None): return self.scene.cube(name,size,position)
    def frame(self): return self.renderer.render(self.scene)
    def save_frame(self,path):
        rgb=self.frame(); self.renderer.write_ppm(path,rgb); return path


__all__=["Vec3","Color","Transform","Material","Mesh3D","Camera3D","Light","Object3D","Scene3D","Software3DRenderer","GPU3DBackend","Engine3D"]
