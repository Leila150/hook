"""HOOK toolchain discovery, project configuration and native/Android builds."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os, platform, shutil, subprocess, tomllib

TARGETS=("android-arm64","android-arm","linux-x86_64","linux-arm64","windows-x86_64","macos-arm64","macos-x86_64")
TRIPLES={"linux-x86_64":"x86_64-linux-gnu","linux-arm64":"aarch64-linux-gnu","android-arm64":"aarch64-linux-android","android-arm":"armv7a-linux-androideabi","windows-x86_64":"x86_64-w64-windows-gnu","macos-arm64":"aarch64-apple-darwin","macos-x86_64":"x86_64-apple-darwin"}

@dataclass(frozen=True)
class Tool:
    name:str; path:str; version:str=""

def _version(binary):
    try:
        p=subprocess.run([binary,"--version"],capture_output=True,text=True,timeout=5)
        return (p.stdout or p.stderr).splitlines()[0] if p.returncode==0 else ""
    except Exception:return ""

def find_tool(*names):
    for name in names:
        p=shutil.which(name)
        if p:return Tool(name,p,_version(p))
    return None

class Project:
    def __init__(self,root="."):
        self.root=Path(root).resolve(); self.config={}
    def load(self):
        p=self.root/"hook.toml"
        self.config=tomllib.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        return self.config
    def validate(self):
        self.load(); return self.root.exists() and (not self.config or self.config.get("project",{}).get("name",self.root.name))
    def write(self,name=None,version="0.1.0",entry="main.hk"):
        self.root.mkdir(parents=True,exist_ok=True); n=name or self.root.name
        (self.root/"hook.toml").write_text(f'[project]\nname = "{n}"\nversion = "{version}"\nentry = "{entry}"\n\n[build]\ntarget = "host"\n',encoding="utf-8"); return self.root/"hook.toml"

class AndroidToolchain:
    def __init__(self,android_sdk=None):
        raw=android_sdk or os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
        self.android_sdk=Path(raw).resolve() if raw else None
    def target(self,abi="arm64"):return f"android-{abi}"
    def available(self):
        return bool(self.android_sdk and self.android_sdk.exists() and (self.android_sdk/"platform-tools").exists())
    def sdkmanager(self): return find_tool("sdkmanager")
    def adb(self): return find_tool("adb") or (Tool("adb",str(self.android_sdk/"platform-tools/adb")) if self.android_sdk and (self.android_sdk/"platform-tools/adb").exists() else None)
    def manifest(self,package="app",name="HOOK App",version="0.1.0"):return {"package":package,"name":name,"version":version,"min_sdk":24,"target_sdk":35}
    def build_plan(self,package="app",abi="arm64"):return {"target":self.target(abi),"package":package,"artifacts":["classes.dex","AndroidManifest.xml","resources.arsc"]}
    def generate(self,root,package="app",name="HookApp",version="0.1.0"):
        from .full_runtime import AndroidProject
        return AndroidProject(Path(root),package,name).write()
    def build(self,root,package="app",name="HookApp"):
        project=self.generate(root,package,name); gradle=shutil.which("gradle") or shutil.which("gradlew")
        if not gradle: raise RuntimeError("Gradle is required to build an Android APK")
        subprocess.run([gradle,"assembleDebug"],cwd=project,check=True)
        candidates=list((project/"app/build/outputs/apk/debug").glob("*.apk"))
        if not candidates: raise RuntimeError("Gradle completed but no APK was produced")
        return candidates[0]

class Codegen:
    def __init__(self,target):
        if target not in TARGETS:raise ValueError(f"unsupported target: {target}")
        self.target=target
    def triple(self):return TRIPLES[self.target]
    def compiler(self):
        if self.target.startswith("windows"):return find_tool("clang","gcc")
        return find_tool("clang","gcc","cc")
    def available(self):return self.compiler() is not None
    def compile_c(self,source,output,shared=False,extra_args=()):
        tool=self.compiler()
        if not tool:raise RuntimeError(f"no compiler available for {self.target}")
        cmd=[tool.path,"-O2",*extra_args]
        if shared:cmd += ["-shared"] + ([] if self.target.startswith("windows") else ["-fPIC"])
        cmd += ["-x","c","-","-o",str(output)]
        p=subprocess.run(cmd,input=source,text=True,capture_output=True)
        if p.returncode:raise RuntimeError(p.stderr.strip() or "native compilation failed")
        return Path(output)

__all__=["TARGETS","TRIPLES","Tool","find_tool","Project","AndroidToolchain","Codegen"]
