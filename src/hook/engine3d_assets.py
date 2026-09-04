"""3D assets, raycasting and broad-phase collision helpers."""
from __future__ import annotations
from dataclasses import dataclass
import base64,json,struct
from pathlib import Path
from .engine3d import AABB, Color, Mesh3D, Ray3D, Texture2D, Transform, Vec2, Vec3, mesh_bounds
@dataclass(frozen=True)
class Hit3D:
    distance:float; point:Vec3; normal:Vec3; object:object|None=None
def ray_aabb(ray,box,max_distance=float('inf')):
    tmin,tmax=0.,max_distance
    for o,d,lo,hi in ((ray.origin.x,ray.direction.x,box.minimum.x,box.maximum.x),(ray.origin.y,ray.direction.y,box.minimum.y,box.maximum.y),(ray.origin.z,ray.direction.z,box.minimum.z,box.maximum.z)):
        if abs(d)<1e-12:
            if o<lo or o>hi:return None
            continue
        a,b=(lo-o)/d,(hi-o)/d
        if a>b:a,b=b,a
        tmin,tmax=max(tmin,a),min(tmax,b)
        if tmin>tmax:return None
    p=ray.at(tmin); eps=1e-6; n=Vec3(-1,0,0) if abs(p.x-box.minimum.x)<eps else Vec3(1,0,0) if abs(p.x-box.maximum.x)<eps else Vec3(0,-1,0) if abs(p.y-box.minimum.y)<eps else Vec3(0,1,0) if abs(p.y-box.maximum.y)<eps else Vec3(0,0,-1) if abs(p.z-box.minimum.z)<eps else Vec3(0,0,1); return Hit3D(tmin,p,n)
def ray_triangle(ray,a,b,c,max_distance=float('inf')):
    e1=b-a;e2=c-a;h=ray.direction.cross(e2);det=e1.dot(h)
    if abs(det)<1e-9:return None
    inv=1./det;s=ray.origin-a;u=inv*s.dot(h)
    if u<0 or u>1:return None
    q=s.cross(e1);v=inv*ray.direction.dot(q)
    if v<0 or u+v>1:return None
    t=inv*e2.dot(q); return None if t<0 or t>max_distance else Hit3D(t,ray.at(t),e1.cross(e2).normalized())
def ray_mesh(ray,mesh,transform=None,max_distance=float('inf')):
    vs=mesh.transformed(transform or Transform());best=None
    for i,j,k in mesh.triangles:
        h=ray_triangle(ray,vs[i],vs[j],vs[k],max_distance if best is None else best.distance)
        if h and (best is None or h.distance<best.distance):best=h
    return best
def _decode(doc,base,index):
    b=doc['buffers'][index]; u=b.get('uri','')
    return base64.b64decode(u.split(',',1)[1]) if u.startswith('data:') else ((Path(base)/u).read_bytes() if u else b'')
def load_gltf(path,material=None):
    path=Path(path);doc=json.loads(path.read_text(encoding='utf-8')); blobs=[_decode(doc,path.parent,i) for i in range(len(doc.get('buffers',[])))];out=[]
    for gm in doc.get('meshes',[]):
        for prim in gm.get('primitives',[]):
            attrs=prim.get('attributes',{}); ap=doc['accessors'][attrs['POSITION']]; bv=doc['bufferViews'][ap['bufferView']]; raw=blobs[bv['buffer']]; off=bv.get('byteOffset',0)+ap.get('byteOffset',0); stride=bv.get('byteStride',12); vs=[Vec3(*struct.unpack_from('<3f',raw,off+i*stride)) for i in range(ap['count'])]
            if 'indices' in prim:
                ai=doc['accessors'][prim['indices']];bi=doc['bufferViews'][ai['bufferView']];raw=blobs[bi['buffer']];typ={5121:'B',5123:'H',5125:'I'}.get(ai['componentType']);
                if not typ:raise ValueError('unsupported GLTF index type')
                off=bi.get('byteOffset',0)+ai.get('byteOffset',0);size=struct.calcsize('<'+typ);ids=[struct.unpack_from('<'+typ,raw,off+i*size)[0] for i in range(ai['count'])]
            else:ids=list(range(len(vs)))
            out.append(Mesh3D(vs,[tuple(ids[i:i+3]) for i in range(0,len(ids)-2,3)],material=material or Material()))
    return out
class AssetLoader:
    @staticmethod
    def mesh(path,material=None):
        s=Path(path).suffix.lower()
        if s=='.obj':return Mesh3D.from_obj(path,material)
        if s=='.gltf':
            m=load_gltf(path,material);return m[0] if m else Mesh3D([],[])
        raise ValueError(f'unsupported 3D mesh format: {s}; supported: .obj, .gltf')
    @staticmethod
    def meshes(path,material=None):return load_gltf(path,material) if Path(path).suffix.lower()=='.gltf' else [AssetLoader.mesh(path,material)]
    @staticmethod
    def texture(path):
        s=Path(path).suffix.lower()
        if s=='.ppm':return Texture2D.ppm(path)
        try:
            from PIL import Image
            if s in {'.png','.jpg','.jpeg','.bmp','.webp'}:
                im=Image.open(path).convert('RGBA');return Texture2D(im.width,im.height,[Color(r/255,g/255,b/255,a/255) for r,g,b,a in im.getdata()])
        except ImportError:pass
        raise ValueError('unsupported texture; use .ppm or install Pillow')
class CollisionWorld:
    def __init__(self):self.items=[]
    def add(self,obj,box=None):self.items.append((obj,box or mesh_bounds(obj.mesh,obj.transform)));return obj
    def rebuild(self):self.items=[(o,mesh_bounds(o.mesh,o.transform)) for o,_ in self.items]
    def overlaps(self,box):return [o for o,b in self.items if b.intersects(box)]
    def raycast(self,ray,max_distance=float('inf')):
        best=None
        for obj,box in self.items:
            if ray_aabb(ray,box,max_distance if best is None else best.distance) is None:continue
            h=ray_mesh(ray,obj.mesh,obj.transform,max_distance if best is None else best.distance)
            if h and (best is None or h.distance<best.distance):best=Hit3D(h.distance,h.point,h.normal,obj)
        return best
from .engine3d import Material
__all__=['Hit3D','ray_aabb','ray_triangle','ray_mesh','load_gltf','AssetLoader','CollisionWorld']
