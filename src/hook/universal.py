"""Unified optional subsystems for building HOOK applications and games."""
from __future__ import annotations
from .engine3d import Engine3D
from .physics3d import PhysicsWorld3D
from .game_io import InputManager,AudioManager,Clock
from .shaders3d import ShaderLibrary
class UniversalRuntime:
    def __init__(self,width=800,height=600):
        self.graphics=Engine3D(width,height);self.physics=PhysicsWorld3D();self.input=InputManager();self.audio=AudioManager();self.clock=Clock();self.shaders=ShaderLibrary().builtin();self.running=False;self.time=0.
    def step(self,dt=None):
        if dt is None:dt=self.clock.tick()
        self.time+=dt;self.input.update();self.physics.step(dt);self.graphics.scene.update(self.time);return dt
    def frame(self):return self.graphics.frame()
    def run(self,steps=None):
        self.running=True;i=0
        while self.running and (steps is None or i<steps):self.step();i+=1
        return i
    def stop(self):self.running=False
__all__=['UniversalRuntime']
