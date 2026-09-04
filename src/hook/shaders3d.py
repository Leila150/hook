"""Backend-neutral shader abstraction for HOOK 3D."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable
from .engine3d import Color, Vec3
@dataclass
class ShaderContext:
    position:Vec3; normal:Vec3; uv:tuple[float,float]=(0.,0.); color:Color=Color(); time:float=0.; uniforms:dict=field(default_factory=dict)
@dataclass
class Shader:
    vertex:Callable|None=None
    fragment:Callable|None=None
    uniforms:dict=field(default_factory=dict)
    def shade(self,ctx):
        if self.fragment:return self.fragment(ctx)
        return ctx.color
class ShaderLibrary:
    def __init__(self):self._items={}
    def register(self,name,shader):self._items[str(name)]=shader;return shader
    def get(self,name):return self._items[name]
    def has(self,name):return name in self._items
    def remove(self,name):self._items.pop(name,None)
    def list(self):return sorted(self._items)
    def builtin(self):
        self.register('unlit',Shader(fragment=lambda c:c.color))
        self.register('normal',Shader(fragment=lambda c:Color(abs(c.normal.x),abs(c.normal.y),abs(c.normal.z),1)))
        return self
__all__=['ShaderContext','Shader','ShaderLibrary']
