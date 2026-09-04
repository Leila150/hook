"""Graphics, GUI, audio and game foundations with backend-neutral interfaces."""
from __future__ import annotations
import time
class Color:
    def __init__(self,r=255,g=255,b=255,a=255):self.r,self.g,self.b,self.a=r,g,b,a
class Vec2:
    def __init__(self,x=0,y=0):self.x,self.y=x,y
    def __add__(self,o):return Vec2(self.x+o.x,self.y+o.y)
    def __sub__(self,o):return Vec2(self.x-o.x,self.y-o.y)
class Entity:
    def __init__(self,name='entity',position=None):self.name=name;self.position=position or Vec2();self.velocity=Vec2();self.active=True
    def update(self,dt):self.position=self.position+self.velocity
class Scene:
    def __init__(self):self.entities=[]
    def add(self,e):self.entities.append(e);return e
    def update(self,dt):
        for e in self.entities:
            if e.active:e.update(dt)
class Game:
    def __init__(self):self.scene=Scene();self.running=False;self.time=0
    def tick(self,dt):self.time+=dt;self.scene.update(dt)
    def run(self,seconds=None,fps=60):
        self.running=True;start=time.monotonic();last=start
        while self.running and (seconds is None or time.monotonic()-start<seconds):
            now=time.monotonic();self.tick(now-last);last=now;time.sleep(max(0,1/fps-(time.monotonic()-now)))
    def stop(self):self.running=False
class GUI:
    def __init__(self,title='HOOK'):self.title=title;self.widgets=[]
    def add(self,widget):self.widgets.append(widget);return widget
class Audio:
    def play(self,path,loop=False):return {'path':path,'loop':loop,'playing':True}
