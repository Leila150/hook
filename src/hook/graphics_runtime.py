"""HOOK dependency-free 3D geometry and software rendering."""
from __future__ import annotations
from dataclasses import dataclass, field
import math, shutil, subprocess

@dataclass(frozen=True)
class Vec3:
    x:float; y:float; z:float
    def __add__(self,o):return Vec3(self.x+o.x,self.y+o.y,self.z+o.z)
    def __sub__(self,o):return Vec3(self.x-o.x,self.y-o.y,self.z-o.z)
    def __mul__(self,s):return Vec3(self.x*s,self.y*s,self.z*s)
    def dot(self,o):return self.x*o.x+self.y*o.y+self.z*o.z
    def cross(self,o):return Vec3(self.y*o.z-self.z*o.y,self.z*o.x-self.x*o.z,self.x*o.y-self.y*o.x)
    def norm(self):return math.sqrt(self.dot(self))
    def normalized(self):
        n=self.norm();return self if n==0 else self*(1/n)

@dataclass
class Camera:
    position:Vec3=field(default_factory=lambda:Vec3(0,0,-5)); fov:float=70; near:float=.1; far:float=1000
    def project(self,p,width,height):
        q=p-self.position
        if q.z<=self.near or q.z>self.far:return None
        f=1/math.tan(math.radians(self.fov)/2);return (width/2+(q.x*f/q.z)*width/2,height/2-(q.y*f/q.z)*height/2,q.z)

class Mesh:
    def __init__(self,vertices,faces):self.vertices=list(vertices);self.faces=list(faces)
    @classmethod
    def cube(cls,size=1):
        s=size/2;v=[Vec3(x*s,y*s,z*s) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]];f=[(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(3,2,6),(3,6,7),(1,5,6),(1,6,2),(0,3,7),(0,7,4)];return cls(v,f)

class SoftwareRenderer:
    def __init__(self,width=320,height=240):self.width=width;self.height=height;self.camera=Camera()
    def render(self,mesh,position=Vec3(0,0,0)):
        zbuf=[[float('inf')]*self.width for _ in range(self.height)];pixels=[[0]*self.width for _ in range(self.height)]
        pts=[self.camera.project(v+position,self.width,self.height) for v in mesh.vertices]
        for face in mesh.faces:
            tri=[pts[i] for i in face]
            if any(p is None for p in tri):continue
            ax,ay=tri[0][:2];bx,by=tri[1][:2];cx,cy=tri[2][:2];den=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
            if den==0:continue
            lo_x=max(0,int(min(p[0] for p in tri)));hi_x=min(self.width-1,int(max(p[0] for p in tri)));lo_y=max(0,int(min(p[1] for p in tri)));hi_y=min(self.height-1,int(max(p[1] for p in tri)))
            for y in range(lo_y,hi_y+1):
                for x in range(lo_x,hi_x+1):
                    u=((by-cy)*(x-cx)+(cx-bx)*(y-cy))/den;v=((cy-ay)*(x-cx)+(ax-cx)*(y-cy))/den;w=1-u-v
                    if u>=0 and v>=0 and w>=0:
                        depth=u*tri[0][2]+v*tri[1][2]+w*tri[2][2]
                        if depth<zbuf[y][x]:zbuf[y][x]=depth;pixels[y][x]=255
        return pixels
    def write_pgm(self,path,pixels):
        with open(path,'wb') as f:f.write(f'P5\n{self.width} {self.height}\n255\n'.encode());f.write(bytes(v for row in pixels for v in row))

class GPUBackend:
    def __init__(self):self.backend=self.detect()
    @staticmethod
    def detect():
        for name in ('vulkaninfo','clinfo','nvidia-smi'):
            if shutil.which(name):return name
        return None
    @property
    def available(self):return self.backend is not None
    def info(self):
        if not self.backend:return {'available':False,'backend':None}
        try:r=subprocess.run([self.backend,'--version'],capture_output=True,text=True,timeout=3);version=(r.stdout or r.stderr).splitlines()[0] if r.returncode==0 else ''
        except Exception:version=''
        return {'available':True,'backend':self.backend,'version':version}

__all__=['Vec3','Camera','Mesh','SoftwareRenderer','GPUBackend']
