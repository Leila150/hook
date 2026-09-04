"""HOOK package manager with deterministic semver resolution and locking."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json, re, shutil

@dataclass(frozen=True, order=True)
class Version:
    major:int; minor:int=0; patch:int=0
    @classmethod
    def parse(cls,value):
        m=re.match(r"^\s*[v=]?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-+].*)?\s*$",str(value))
        if not m: raise ValueError(f"invalid version: {value}")
        return cls(int(m.group(1)),int(m.group(2) or 0),int(m.group(3) or 0))
    def __str__(self): return f"{self.major}.{self.minor}.{self.patch}"

def satisfies(version,constraint="*"):
    v=Version.parse(version); c=str(constraint or "*").strip()
    if c in {"","*","latest"}: return True
    parts=[p for p in re.split(r"\s*,\s*",c) if p]
    if len(parts)>1:return all(satisfies(v,p) for p in parts)
    if c.startswith("^"):
        base=Version.parse(c[1:]); upper=Version(base.major+1,0,0) if base.major else Version(0,base.minor+1,0); return v>=base and v<upper
    if c.startswith("~"):
        base=Version.parse(c[1:]); return v>=base and v<Version(base.major,base.minor+1,0)
    m=re.match(r"(>=|<=|>|<|==|=)?\s*(.+)$",c)
    if not m: raise ValueError(f"invalid constraint: {constraint}")
    op=m.group(1) or "=="; x=Version.parse(m.group(2)); return {">=":v>=x,"<=":v<=x,">":v>x,"<":v<x,"==":v==x,"=":v==x}[op]

@dataclass
class Package:
    name:str; version:str; path:str=""; dependencies:dict[str,str]=field(default_factory=dict)
    def manifest(self):return {"name":self.name,"version":self.version,"dependencies":self.dependencies}

class PackageManager:
    def __init__(self,root="."):
        self.root=Path(root).resolve();self.hookdir=self.root/".hook";self.cache=self.hookdir/"packages";self.lockfile=self.root/"hook.lock"
    def create(self,name,version="0.1.0",dependencies=None):
        path=self.root/name;path.mkdir(parents=True,exist_ok=True);(path/"hook.package.json").write_text(json.dumps(Package(name,version,dependencies=dependencies or {}).manifest(),indent=2)+"\n",encoding="utf-8");return path
    def read(self,path=None):
        p=Path(path or self.root);p=p if p.name=="hook.package.json" else p/"hook.package.json"
        if not p.exists():raise FileNotFoundError(p)
        return json.loads(p.read_text(encoding="utf-8"))
    def discover(self,*roots):
        found={};search=[Path(r).resolve() for r in roots] or [self.root,self.cache]
        for root in search:
            if not root.exists():continue
            for manifest in root.rglob("hook.package.json"):
                try:
                    data=json.loads(manifest.read_text(encoding="utf-8"));name=data["name"];found.setdefault(name,[]).append(Package(name,data.get("version","0.0.0"),str(manifest.parent),data.get("dependencies",{})))
                except (OSError,ValueError,KeyError):continue
        for values in found.values():values.sort(key=lambda p:Version.parse(p.version),reverse=True)
        return found
    def resolve(self,requirements,roots=()):
        available=self.discover(*roots)
        initial={name:[str(c)] for name,c in requirements.items()}
        def solve(selected,constraints):
            unresolved=[n for n in constraints if n not in selected]
            if not unresolved:return selected
            choices={n:[p for p in available.get(n,[]) if all(satisfies(p.version,c) for c in constraints[n])] for n in unresolved}
            name=min(unresolved,key=lambda n:len(choices[n]))
            for chosen in choices[name]:
                new_selected=dict(selected);new_constraints={k:list(v) for k,v in constraints.items()};new_selected[name]=chosen
                for dep,con in chosen.dependencies.items():new_constraints.setdefault(dep,[]).append(str(con))
                if all(any(all(satisfies(p.version,c) for c in new_constraints[n]) for p in available.get(n,[])) for n in new_constraints if n not in new_selected):
                    result=solve(new_selected,new_constraints)
                    if result is not None:return result
            return None
        result=solve({},initial)
        if result is None:raise RuntimeError("unsatisfied package dependency constraints")
        return result
    def lock(self,packages):
        data={"version":2,"packages":{p.name:{"version":p.version,"path":p.path,"dependencies":p.dependencies} for p in packages}};self.lockfile.parent.mkdir(parents=True,exist_ok=True);self.lockfile.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8");return data
    def load_lock(self):
        if not self.lockfile.exists():return {"version":2,"packages":{}}
        return json.loads(self.lockfile.read_text(encoding="utf-8"))
    def install_local(self,package_path):
        src=Path(package_path).resolve();manifest=self.read(src);dest=self.cache/manifest["name"]/manifest.get("version","0.0.0");dest.mkdir(parents=True,exist_ok=True)
        for f in src.rglob("*"):
            if f.is_file() and ".hook" not in f.parts:
                target=dest/f.relative_to(src);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
        return dest
    def install(self,requirements,roots=()):
        selected=self.resolve(requirements,roots);installed=[]
        for p in selected.values():
            if p.path and Path(p.path).exists():installed.append(self.install_local(p.path))
        self.lock(selected.values());return installed
    def uninstall(self,name,version=None):
        base=self.cache/name
        if not base.exists():return False
        if version:
            target=base/str(Version.parse(version))
            if target.exists():shutil.rmtree(target)
            if base.exists() and not any(base.iterdir()):base.rmdir()
        else:shutil.rmtree(base)
        lock=self.load_lock();lock.get("packages",{}).pop(name,None);self.lockfile.write_text(json.dumps(lock,indent=2)+"\n",encoding="utf-8");return True
    def list_installed(self):
        out=[]
        for p in self.cache.glob("*/**/hook.package.json") if self.cache.exists() else []:
            try:out.append(self.read(p.parent))
            except Exception:pass
        return out

__all__=["Package","Version","PackageManager","satisfies"]
