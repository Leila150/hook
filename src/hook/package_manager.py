"""HOOK package manifests, dependency resolution, lockfiles and local registry."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json, re

@dataclass
class Package:
    name: str; version: str; path: str = ""; dependencies: dict[str,str] = field(default_factory=dict)
    def manifest(self): return {"name":self.name,"version":self.version,"dependencies":self.dependencies}

class Version:
    def __init__(self, value):
        self.parts=tuple(int(x) for x in re.findall(r"\d+",value)[:3])
    def __lt__(self,o): return self.parts < o.parts
    def __eq__(self,o): return self.parts == o.parts

class PackageManager:
    def __init__(self, root="."):
        self.root=Path(root).resolve(); self.hookdir=self.root/".hook"; self.cache=self.hookdir/"packages"; self.lockfile=self.root/"hook.lock"
    def create(self,name,version="0.1.0"):
        path=self.root/name; path.mkdir(parents=True,exist_ok=True)
        manifest=Package(name,version).manifest(); (path/"hook.package.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8"); return path
    def read(self,path=None):
        p=Path(path or self.root)/"hook.package.json"
        if not p.exists(): raise FileNotFoundError(p)
        return json.loads(p.read_text(encoding="utf-8"))
    def lock(self,packages):
        data={"version":1,"packages":{p.name:{"version":p.version,"path":p.path,"dependencies":p.dependencies} for p in packages}}
        self.lockfile.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8"); return data
    def load_lock(self):
        if not self.lockfile.exists(): return {"version":1,"packages":{}}
        return json.loads(self.lockfile.read_text(encoding="utf-8"))
    def install_local(self,package_path):
        src=Path(package_path).resolve(); manifest=self.read(src); dest=self.cache/manifest["name"]; dest.mkdir(parents=True,exist_ok=True)
        for f in src.rglob("*"):
            if f.is_file() and ".hook" not in f.parts:
                target=dest/f.relative_to(src); target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(f.read_bytes())
        return dest
