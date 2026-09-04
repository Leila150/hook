"""HOOK project manifest and lifecycle helpers."""
from __future__ import annotations
from dataclasses import dataclass,field,asdict
import json,subprocess
from pathlib import Path
@dataclass
class HookProject:
 name:str='hook-project';version:str='0.1.0';entry:str='main.hk';dependencies:dict[str,str]=field(default_factory=dict);targets:list[str]=field(default_factory=lambda:['python'])
 @classmethod
 def load(cls,path='hook.toml'):
  p=Path(path)
  if not p.exists():return cls()
  text=p.read_text(encoding='utf-8');d={}
  # Minimal TOML reader for the project fields, with stdlib-only fallback.
  try:
   import tomllib; data=tomllib.loads(text);d=data.get('project',data)
  except Exception:
   for line in text.splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
     k,v=line.split('=',1);d[k.strip()]=v.strip().strip('"')
  return cls(name=d.get('name','hook-project'),version=d.get('version','0.1.0'),entry=d.get('entry','main.hk'),dependencies=d.get('dependencies',{}),targets=d.get('targets',['python']))
 def save(self,path='hook.toml'):
  p=Path(path);p.write_text('[project]\nname = "'+self.name+'"\nversion = "'+self.version+'"\nentry = "'+self.entry+'"\n\n[project.dependencies]\n'+''.join(f'{k} = "{v}"\n' for k,v in self.dependencies.items()),encoding='utf-8');return p
 def run(self,hook='hook'):
  return subprocess.run([hook,self.entry]).returncode
 def test(self):return subprocess.run(['python','-m','pytest']).returncode
__all__=['HookProject']
