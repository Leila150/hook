"""Winlator-inspired compatibility/container orchestration for HOOK.

HOOK orchestrates installed Wine/Box64/Box86/PRoot components; it does not
bundle proprietary or third-party runtime binaries.
"""
from __future__ import annotations
from dataclasses import dataclass,field,asdict
import json,os,platform,shutil,subprocess
from pathlib import Path
from typing import Iterable,Mapping
@dataclass(frozen=True)
class Component:
 name:str; path:str|None; available:bool; version:str=''
@dataclass
class CompatibilityConfig:
 rootfs:Path|None=None; wine_prefix:Path|None=None; box64:str|None=None; box86:str|None=None; proot:str|None=None; wine:str|None=None; environment:dict[str,str]=field(default_factory=dict); box64_args:list[str]=field(default_factory=list); box86_args:list[str]=field(default_factory=list); graphics:str='auto'; audio:str='auto'
class CompatibilityError(RuntimeError):pass
def _which(*names):
 for n in names:
  p=shutil.which(n)
  if p:return p
def _version(path):
 if not path:return ''
 try:
  p=subprocess.run([path,'--version'],capture_output=True,text=True,timeout=3);return (p.stdout or p.stderr).splitlines()[0][:200] if p.returncode==0 else ''
 except Exception:return ''
def detect_components():
 names={'proot':('proot',),'box64':('box64',),'box86':('box86',),'wine':('wine','wine64'),'vulkan':('vulkaninfo',),'opengl':('glxinfo','eglinfo'),'pulseaudio':('pulseaudio',),'alsa':('aplay',)}
 return {k:Component(k,(p:=_which(*v)),bool(p),_version(p)) for k,v in names.items()}
def is_android():return bool(os.environ.get('ANDROID_ROOT') or os.environ.get('ANDROID_DATA')) or platform.system().lower()=='android'
def host_arch():return platform.machine().lower()
class ArchitectureTranslator:
 def __init__(self,box64=None,box86=None):self.box64=box64;self.box86=box86
 def select(self,guest='x86_64'):
  return self.box64 if guest in ('x86_64','amd64') else self.box86 if guest in ('x86','i386','i686') else None
class WineRuntime:
 def __init__(self,wine=None,prefix=None):self.wine=wine;self.prefix=Path(prefix).expanduser() if prefix else None
 def env(self):
  e=dict(os.environ)
  if self.prefix:self.prefix.mkdir(parents=True,exist_ok=True);e['WINEPREFIX']=str(self.prefix)
  return e
 def command(self,exe,args=()):
  if not self.wine:raise CompatibilityError('Wine is not available')
  return [self.wine,str(exe),*[str(a) for a in args]]
class ContainerProfile:
 def __init__(self,name,config):self.name=name;self.config=config
 def to_json(self):
  d=asdict(self.config);d['rootfs']=str(d['rootfs']) if d['rootfs'] else None;d['wine_prefix']=str(d['wine_prefix']) if d['wine_prefix'] else None;return {'version':1,'name':self.name,'config':d}
class WinlatorRuntime:
 def __init__(self,config=None,profile_dir=None):self.config=config or CompatibilityConfig();self.components=detect_components();self.profile_dir=Path(profile_dir or (Path.home()/'.hook'/'compat'));self.profile_dir.mkdir(parents=True,exist_ok=True)
 def configure_from_environment(self):
  e=os.environ
  for attr,keys in [('rootfs',('HOOK_ROOTFS','WINLATOR_ROOTFS')),('wine_prefix',('WINEPREFIX','HOOK_WINEPREFIX'))]:
   if not getattr(self.config,attr):
    if (v:=next((e[k] for k in keys if e.get(k)),None)):setattr(self.config,attr,Path(v).expanduser().resolve())
  self.config.box64=self.config.box64 or e.get('HOOK_BOX64') or self.components['box64'].path;self.config.box86=self.config.box86 or e.get('HOOK_BOX86') or self.components['box86'].path;self.config.proot=self.config.proot or e.get('HOOK_PROOT') or self.components['proot'].path;self.config.wine=self.config.wine or e.get('HOOK_WINE') or self.components['wine'].path;return self
 def validate(self,guest='x86_64'):
  self.configure_from_environment();missing=[]
  if self.config.rootfs and not self.config.rootfs.exists():missing.append('rootfs')
  if not ArchitectureTranslator(self.config.box64,self.config.box86).select(guest):missing.append('box64' if guest in ('x86_64','amd64') else 'box86')
  if not self.config.wine:missing.append('wine')
  return missing
 def environment(self,extra=None):
  self.configure_from_environment();r=dict(os.environ)
  if self.config.rootfs:r['HOOK_ROOTFS']=str(self.config.rootfs);r['PATH']=f"{self.config.rootfs/'usr/bin'}:{r.get('PATH','')}";r['LD_LIBRARY_PATH']=f"{self.config.rootfs/'usr/lib'}:{r.get('LD_LIBRARY_PATH','')}"
  if self.config.wine_prefix:self.config.wine_prefix.mkdir(parents=True,exist_ok=True);r['WINEPREFIX']=str(self.config.wine_prefix)
  r.update(self.config.environment);r.update({str(k):str(v) for k,v in (extra or {}).items()});return r
 def command(self,executable,args=(),guest='x86_64'):
  self.configure_from_environment();wine=self.config.wine
  if not wine:raise CompatibilityError('Wine is not available')
  tr=ArchitectureTranslator(self.config.box64,self.config.box86).select(guest);cmd=[wine,str(Path(executable).expanduser()),*[str(a) for a in args]]
  if tr:cmd=[tr,*((self.config.box64_args if guest in ('x86_64','amd64') else self.config.box86_args)),*cmd]
  if self.config.proot and self.config.rootfs:cmd=[self.config.proot,'-r',str(self.config.rootfs),'--',*cmd]
  return cmd
 def run(self,executable,args=(),extra_env=None,guest='x86_64'): 
  missing=self.validate(guest)
  if missing:raise CompatibilityError('missing compatibility components: '+', '.join(missing))
  return subprocess.run(self.command(executable,args,guest),env=self.environment(extra_env)).returncode
 def create_profile(self,name,config=None):
  p=ContainerProfile(name,config or self.config);dest=self.profile_dir/f'{name}.json';dest.write_text(json.dumps(p.to_json(),indent=2));return dest
 def load_profile(self,name):
  d=json.loads((self.profile_dir/f'{name}.json').read_text());c=d['config'];c['rootfs']=Path(c['rootfs']) if c.get('rootfs') else None;c['wine_prefix']=Path(c['wine_prefix']) if c.get('wine_prefix') else None;return ContainerProfile(d['name'],CompatibilityConfig(**c))
 def list_profiles(self):return sorted(p.stem for p in self.profile_dir.glob('*.json'))
 def doctor(self):return {'android':is_android(),'host_arch':host_arch(),'components':{k:asdict(v) for k,v in self.components.items()}}
__all__=['Component','CompatibilityConfig','CompatibilityError','detect_components','is_android','host_arch','ArchitectureTranslator','WineRuntime','ContainerProfile','WinlatorRuntime']
