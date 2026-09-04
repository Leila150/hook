"""Portable HOOK 3D engine.

The renderer is dependency-free and CPU based, with explicit backend adapters for
OpenGL/Vulkan. Optional native backends never masquerade as available hardware.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import json, math, shutil
from pathlib import Path
from typing import Callable, Iterable

@dataclass(frozen=True)
class Vec3:
    x: float; y: float; z: float
    def __add__(self,o): return Vec3(self.x+o.x,self.y+o.y,self.z+o.z)
    def __sub__(self,o): return Vec3(self.x-o.x,self.y-o.y,self.z-o.z)
    def __mul__(self,s): return Vec3(self.x*s,self.y*s,self.z*s)
    __rmul__=__mul__
    def __truediv__(self,s): return Vec3(self.x/s,self.y/s,self.z/s)
    def dot(self,o): return self.x*o.x+self.y*o.y+self.z*o.z
    def cross(self,o): return Vec3(self.y*o.z-self.z*o.y,self.z*o.x-self.x*o.z,self.x*o.y-self.y*o.x)
    def length(self): return math.sqrt(self.dot(self))
    def normalized(self):
        n=self.length(); return self if n==0 else self/n
    def lerp(self,o,t): return self+(o-self)*t

@dataclass(frozen=True)
class Color:
    r: float=1.; g: float=1.; b: float=1.; a: float=1.
    def clamped(self): return Color(*(max(0.,min(1.,v)) for v in (self.r,self.g,self.b,self.a)))
    def __mul__(self,s): return Color(self.r*s,self.g*s,self.b*s,self.a)

@dataclass(frozen=True)
class Vec2:
    x: float; y: float

@dataclass
class Texture2D:
    width:int; height:int; pixels:list[Color]
    def sample(self,u,v):
        if not self.pixels: return Color()
        u%=1.; v%=1.; x=min(self.width-1,max(0,int(u*(self.width-1)+.5))); y=min(self.height-1,max(0,int((1-v)*(self.height-1)+.5)))
        return self.pixels[y*self.width+x]
    @classmethod
    def solid(cls,color,width=1,height=1): return cls(width,height,[color]*(width*height))
    @classmethod
    def ppm(cls,path):
        data=Path(path).read_bytes(); parts=data.split()
        if parts[0] not in (b'P3',b'P6'): raise ValueError('unsupported PPM')
        # P3 is straightforward; P6 is parsed after the header.
        if parts[0]==b'P3':
            w,h,m=map(int,parts[1:4]); vals=list(map(int,parts[4:])); pix=[Color(vals[i]/m,vals[i+1]/m,vals[i+2]/m) for i in range(0,min(len(vals),w*h*3),3)]; return cls(w,h,pix)
        header_end=0; count=0
        for _ in range(4): header_end=data.find(b'\n',header_end)+1; count+=1
        lines=data[:header_end].split(); w,h,m=map(int,lines[1:4]); raw=data[header_end:]; pix=[Color(raw[i]/m,raw[i+1]/m,raw[i+2]/m) for i in range(0,min(len(raw),w*h*3),3)]; return cls(w,h,pix)

@dataclass
class Transform:
    position:Vec3=field(default_factory=lambda:Vec3(0,0,0)); rotation:Vec3=field(default_factory=lambda:Vec3(0,0,0)); scale:Vec3=field(default_factory=lambda:Vec3(1,1,1))
    def apply(self,p):
        q=Vec3(p.x*self.scale.x,p.y*self.scale.y,p.z*self.scale.z); rx,ry,rz=map(math.radians,(self.rotation.x,self.rotation.y,self.rotation.z)); cx,sx=math.cos(rx),math.sin(rx); cy,sy=math.cos(ry),math.sin(ry); cz,sz=math.cos(rz),math.sin(rz)
        q=Vec3(q.x,cx*q.y-sx*q.z,sx*q.y+cx*q.z); q=Vec3(cy*q.x+sy*q.z,q.y,-sy*q.x+cy*q.z); return Vec3(cz*q.x-sz*q.y,sz*q.x+cz*q.y,q.z)+self.position

@dataclass
class Material:
    color:Color=Color(); emission:float=0.; wireframe:bool=False; texture:Texture2D|None=None; shader:Callable|None=None

@dataclass
class Mesh3D:
    vertices:list[Vec3]; triangles:list[tuple[int,int,int]]; uvs:list[Vec2]=field(default_factory=list); normals:list[Vec3]=field(default_factory=list); material:Material=field(default_factory=Material)
    @classmethod
    def cube(cls,size=1.,material=None):
        s=float(size)/2; v=[Vec3(x*s,y*s,z*s) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]; t=[(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(3,2,6),(3,6,7),(1,5,6),(1,6,2),(0,3,7),(0,7,4)]; return cls(v,t,material=material or Material())
    @classmethod
    def from_obj(cls,path,material=None):
        vs=[]; ts=[]; uv=[]
        for line in Path(path).read_text(encoding='utf-8',errors='replace').splitlines():
            p=line.strip().split();
            if not p or p[0]=='#': continue
            if p[0]=='v': vs.append(Vec3(*map(float,p[1:4])))
            elif p[0]=='vt': uv.append(Vec2(float(p[1]),float(p[2])))
            elif p[0]=='f':
                ids=[int(x.split('/')[0])-1 for x in p[1:]]
                for i in range(1,len(ids)-1): ts.append((ids[0],ids[i],ids[i+1]))
        return cls(vs,ts,material=material or Material())
    def transformed(self,t): return [t.apply(v) for v in self.vertices]

def _rotate_inverse(q,r):
    rx,ry,rz=map(math.radians,(-r.x,-r.y,-r.z)); cx,sx=math.cos(rx),math.sin(rx); cy,sy=math.cos(ry),math.sin(ry); cz,sz=math.cos(rz),math.sin(rz); q=Vec3(q.x,cx*q.y-sx*q.z,sx*q.y+cx*q.z); q=Vec3(cy*q.x+sy*q.z,q.y,-sy*q.x+cy*q.z); return Vec3(cz*q.x-sz*q.y,sz*q.x+cz*q.y,q.z)

@dataclass
class Camera3D:
    position:Vec3=field(default_factory=lambda:Vec3(0,0,-5)); rotation:Vec3=field(default_factory=lambda:Vec3(0,0,0)); fov:float=70.; near:float=.05; far:float=10000.
    def view(self,p): return _rotate_inverse(p-self.position,self.rotation)
    def project(self,p,width,height):
        q=self.view(p)
        if q.z<=self.near or q.z>=self.far: return None
        f=1./math.tan(math.radians(self.fov)/2); return (width/2+(q.x*f/q.z)*width/2,height/2-(q.y*f/q.z)*height/2,q.z)
    def move(self,forward=0,right=0,up=0,speed=1.):
        yaw=math.radians(self.rotation.y); self.position=self.position+Vec3(math.sin(yaw)*forward+math.cos(yaw)*right,up,math.cos(yaw)*forward-math.sin(yaw)*right)*speed
    def look_at(self,target):
        d=target-self.position; self.rotation=Vec3(math.degrees(math.atan2(d.y,math.sqrt(d.x*d.x+d.z*d.z))),math.degrees(math.atan2(d.x,d.z)),self.rotation.z)

@dataclass
class Light:
    position:Vec3=field(default_factory=lambda:Vec3(2,3,-4)); color:Color=Color(1,1,1,1); intensity:float=1.; ambient:float=.15
@dataclass
class DirectionalLight:
    direction:Vec3=field(default_factory=lambda:Vec3(-1,-1,-1)); color:Color=Color(); intensity:float=1.; ambient:float=.15
@dataclass
class Ray3D:
    origin:Vec3; direction:Vec3
    def __post_init__(self): object.__setattr__(self,'direction',self.direction.normalized())
    def at(self,t): return self.origin+self.direction*t
@dataclass(frozen=True)
class AABB:
    minimum:Vec3; maximum:Vec3
    def intersects(self,o): return self.minimum.x<=o.maximum.x and self.maximum.x>=o.minimum.x and self.minimum.y<=o.maximum.y and self.maximum.y>=o.minimum.y and self.minimum.z<=o.maximum.z and self.maximum.z>=o.minimum.z

def mesh_bounds(mesh,transform=None):
    vs=mesh.transformed(transform or Transform()); return AABB(Vec3(min(v.x for v in vs),min(v.y for v in vs),min(v.z for v in vs)),Vec3(max(v.x for v in vs),max(v.y for v in vs),max(v.z for v in vs)))

@dataclass
class Object3D:
    mesh:Mesh3D; transform:Transform=field(default_factory=Transform); name:str='object'; visible:bool=True; tag:str=''; layer:int=0
@dataclass
class Keyframe:
    time:float; value:Vec3
class AnimationTrack:
    def __init__(self,keyframes=()): self.keyframes=sorted(list(keyframes),key=lambda k:k.time)
    def sample(self,time):
        if not self.keyframes: return Vec3(0,0,0)
        if time<=self.keyframes[0].time:return self.keyframes[0].value
        if time>=self.keyframes[-1].time:return self.keyframes[-1].value
        for a,b in zip(self.keyframes,self.keyframes[1:]):
            if a.time<=time<=b.time: return a.value.lerp(b.value,(time-a.time)/(b.time-a.time))
@dataclass
class Animation:
    tracks:dict[str,AnimationTrack]=field(default_factory=dict); duration:float=0.; loop:bool=True
    def apply(self,obj,time):
        if self.duration and self.loop: time=time%self.duration
        if 'position' in self.tracks: obj.transform.position=self.tracks['position'].sample(time)
        if 'rotation' in self.tracks: obj.transform.rotation=self.tracks['rotation'].sample(time)
        if 'scale' in self.tracks: obj.transform.scale=self.tracks['scale'].sample(time)

class Scene3D:
    def __init__(self): self.objects=[]; self.lights=[Light()]; self.directional_lights=[]; self.camera=Camera3D(); self.skybox=Color(.04,.04,.06,1); self.animations={}
    def add(self,obj): self.objects.append(obj); return obj
    def cube(self,name='cube',size=1.,position=None): o=Object3D(Mesh3D.cube(size),name=name); o.transform.position=position or Vec3(0,0,0); return self.add(o)
    def clear(self): self.objects.clear()
    def animate(self,name,animation): self.animations[name]=animation
    def update(self,time):
        for o in self.objects:
            if o.name in self.animations:self.animations[o.name].apply(o,time)

class Software3DRenderer:
    def __init__(self,width=640,height=480): self.width=int(width); self.height=int(height); self.clear_color=Color(.04,.04,.06,1)
    def _shade(self,n,p,m,scene,u=.5,v=.5):
        base=m.texture.sample(u,v) if m.texture else m.color; r=base.r*m.emission; g=base.g*m.emission; b=base.b*m.emission
        lights=scene.lights
        for l in lights:
            d=(l.position-p).normalized(); f=l.ambient+max(0,n.dot(d))*l.intensity; r+=base.r*l.color.r*f; g+=base.g*l.color.g*f; b+=base.b*l.color.b*f
        for l in scene.directional_lights:
            d=(l.direction*-1).normalized(); f=l.ambient+max(0,n.dot(d))*l.intensity; r+=base.r*l.color.r*f; g+=base.g*l.color.g*f; b+=base.b*l.color.b*f
        if not lights and not scene.directional_lights:r,g,b=base.r,base.g,base.b
        return bytes((int(max(0,min(1,r))*255),int(max(0,min(1,g))*255),int(max(0,min(1,b))*255)))
    def render(self,scene):
        w,h=self.width,self.height; bg=scene.skybox.clamped(); pixels=[bytearray([int(bg.r*255),int(bg.g*255),int(bg.b*255)])*w for _ in range(h)]; depth=[[float('inf')]*w for _ in range(h)]
        for obj in scene.objects:
            if not obj.visible:continue
            verts=obj.mesh.transformed(obj.transform)
            for a,b,c in obj.mesh.triangles:
                world=(verts[a],verts[b],verts[c]); n=(world[1]-world[0]).cross(world[2]-world[0]).normalized(); view=(world[0]-scene.camera.position).normalized()
                if n.dot(view)>=0:continue
                pts=[scene.camera.project(p,w,h) for p in world]
                if any(p is None for p in pts):continue
                ax,ay=pts[0][:2]; bx,by=pts[1][:2]; cx,cy=pts[2][:2]; den=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
                if abs(den)<1e-9:continue
                lx=max(0,int(min(ax,bx,cx))); hx=min(w-1,int(max(ax,bx,cx))); ly=max(0,int(min(ay,by,cy))); hy=min(h-1,int(max(ay,by,cy)))
                for y in range(ly,hy+1):
                    for x in range(lx,hx+1):
                        u=((by-cy)*(x-cx)+(cx-bx)*(y-cy))/den; v=((cy-ay)*(x-cx)+(ax-cx)*(y-cy))/den
                        if u<0 or v<0 or u+v>1:continue
                        ww=1-u-v; z=u*pts[0][2]+v*pts[1][2]+ww*pts[2][2]
                        if z>=depth[y][x]:continue
                        uv=(None,None)
                        if len(obj.mesh.uvs)>=max(a,b,c)+1: uv=(obj.mesh.uvs[a].x*ww+obj.mesh.uvs[b].x*u+obj.mesh.uvs[c].x*v,obj.mesh.uvs[a].y*ww+obj.mesh.uvs[b].y*u+obj.mesh.uvs[c].y*v)
                        rgb=self._shade(n,world[0],obj.mesh.material,scene,*(uv if uv[0] is not None else (.5,.5))); depth[y][x]=z; pixels[y][x*3:x*3+3]=rgb
        return bytes(b for row in pixels for b in row)
    def write_ppm(self,path,rgb): Path(path).write_bytes(f'P6\n{self.width} {self.height}\n255\n'.encode()+rgb)

class GraphicsBackend:
    name='software'
    def available(self): return True
    def info(self): return {'name':self.name,'available':self.available()}
class OpenGLBackend(GraphicsBackend):
    name='opengl'
    def available(self): return bool(shutil.which('glxinfo') or shutil.which('eglinfo') or shutil.which('glxgears'))
class VulkanBackend(GraphicsBackend):
    name='vulkan'
    def available(self): return bool(shutil.which('vulkaninfo'))
class GPU3DBackend:
    def __init__(self): self.backends=[VulkanBackend(),OpenGLBackend()]; self.backend=next((b.name for b in self.backends if b.available()),None)
    @property
    def available(self): return self.backend is not None
    def info(self): return {'available':self.available,'backend':self.backend,'candidates':[b.info() for b in self.backends]}

class Engine3D:
    def __init__(self,width=640,height=480,backend='auto'):
        self.scene=Scene3D(); self.renderer=Software3DRenderer(width,height); self.gpu=GPU3DBackend(); self.backend=backend
    def add_cube(self,name='cube',size=1,position=None):return self.scene.cube(name,size,position)
    def frame(self,time=None):
        if time is not None:self.scene.update(time)
        return self.renderer.render(self.scene)
    def save_frame(self,path,time=None):self.renderer.write_ppm(path,self.frame(time));return path
    def backend_info(self):return self.gpu.info()

__all__=['Vec3','Vec2','Color','Texture2D','Transform','Material','Mesh3D','Camera3D','Light','DirectionalLight','Ray3D','AABB','mesh_bounds','Object3D','Keyframe','AnimationTrack','Animation','Scene3D','Software3DRenderer','GraphicsBackend','OpenGLBackend','VulkanBackend','GPU3DBackend','Engine3D']
