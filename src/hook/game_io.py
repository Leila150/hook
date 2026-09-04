"""Cross-platform input and audio abstractions with optional host adapters."""
from __future__ import annotations
from dataclasses import dataclass, field
import platform, time, wave

@dataclass
class InputState:
    keys:set[str]=field(default_factory=set)
    mouse_buttons:set[int]=field(default_factory=set)
    mouse_position:tuple[float,float]=(0.,0.)
    def pressed(self,key): return key.lower() in {k.lower() for k in self.keys}

class InputManager:
    def __init__(self): self.state=InputState(); self._previous=set()
    def press(self,key): self.state.keys.add(str(key)); return self
    def release(self,key): self.state.keys.discard(str(key)); return self
    def set_mouse(self,x,y): self.state.mouse_position=(float(x),float(y)); return self
    def update(self): self._previous=set(self.state.keys); return self
    def down(self,key): return self.state.pressed(key)
    def just_pressed(self,key): return self.state.pressed(key) and key not in self._previous

@dataclass
class Sound:
    path:str; volume:float=1.; loop:bool=False

class AudioManager:
    def __init__(self): self.sounds={}; self.backend=self._detect()
    def _detect(self):
        try:
            import pygame
            return 'pygame'
        except Exception:return 'wave'
    def load(self,name,path): self.sounds[name]=Sound(str(path)); return self.sounds[name]
    def duration(self,path):
        with wave.open(str(path),'rb') as w:return w.getnframes()/float(w.getframerate()) if w.getframerate() else 0.
    def play(self,name,volume=1.,loop=False):
        s=self.sounds[name]; s.volume=volume; s.loop=loop
        if self.backend=='pygame':
            import pygame; pygame.mixer.Sound(s.path).play(-1 if loop else 0)
        return s
    def stop(self,name=None):
        if self.backend=='pygame':
            import pygame; pygame.mixer.stop()

@dataclass
class Clock:
    target_fps:float=60.; last:float=field(default_factory=time.perf_counter)
    def tick(self):
        now=time.perf_counter(); dt=now-self.last; minimum=1./self.target_fps if self.target_fps>0 else 0
        if dt<minimum: time.sleep(minimum-dt); now=time.perf_counter(); dt=now-self.last
        self.last=now; return dt

__all__=['InputState','InputManager','Sound','AudioManager','Clock']
