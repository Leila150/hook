"""Portable JSON scene and project serialization for HOOK 3D."""
from __future__ import annotations
import json
from pathlib import Path
from .engine3d import Color, Mesh3D, Object3D, Scene3D, Transform, Vec3

def _vec(v): return [v.x,v.y,v.z]
def save_scene(scene,path):
    data={'version':1,'skybox':vars(scene.skybox),'camera':{'position':_vec(scene.camera.position),'rotation':_vec(scene.camera.rotation),'fov':scene.camera.fov,'near':scene.camera.near,'far':scene.camera.far},'objects':[]}
    for o in scene.objects:
        data['objects'].append({'name':o.name,'tag':o.tag,'layer':o.layer,'visible':o.visible,'transform':{'position':_vec(o.transform.position),'rotation':_vec(o.transform.rotation),'scale':_vec(o.transform.scale)},'mesh':{'vertices':[_vec(v) for v in o.mesh.vertices],'triangles':[list(t) for t in o.mesh.triangles]}})
    Path(path).write_text(json.dumps(data,indent=2),encoding='utf-8'); return path

def load_scene(path):
    data=json.loads(Path(path).read_text(encoding='utf-8')); s=Scene3D(); s.skybox=Color(**data.get('skybox',{})); c=data.get('camera',{}); s.camera.position=Vec3(*c.get('position',[0,0,-5])); s.camera.rotation=Vec3(*c.get('rotation',[0,0,0])); s.camera.fov=c.get('fov',70); s.camera.near=c.get('near',.05); s.camera.far=c.get('far',10000)
    for d in data.get('objects',[]):
        m=d['mesh']; o=Object3D(Mesh3D([Vec3(*v) for v in m['vertices']],[tuple(t) for t in m['triangles']]),name=d.get('name','object'),tag=d.get('tag',''),layer=d.get('layer',0),visible=d.get('visible',True)); t=d.get('transform',{}); o.transform=Transform(Vec3(*t.get('position',[0,0,0])),Vec3(*t.get('rotation',[0,0,0])),Vec3(*t.get('scale',[1,1,1]))); s.add(o)
    return s

__all__=['save_scene','load_scene']
