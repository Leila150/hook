"""Platform/toolchain abstractions: Android packaging, native targets and project builds."""
from __future__ import annotations
from pathlib import Path
import json,zipfile
TARGETS=('android-arm64','android-arm','linux-x86_64','linux-arm64','windows-x86_64','macos-arm64','macos-x86_64')
class Project:
    def __init__(self,root='.'):
        self.root=Path(root);self.config={}
    def load(self):
        p=self.root/'hook.toml'
        if p.exists():
            import tomllib;self.config=tomllib.loads(p.read_text())
        return self.config
    def validate(self):return bool(self.root.exists())
class AndroidToolchain:
    def __init__(self,android_sdk=None):self.android_sdk=Path(android_sdk) if android_sdk else None
    def target(self,abi='arm64'):return f'android-{abi}'
    def manifest(self,package='app',name='HOOK App',version='0.1.0'):
        return {'package':package,'name':name,'version':version,'min_sdk':24,'target_sdk':35}
    def build_plan(self,package='app',abi='arm64'):return {'target':self.target(abi),'package':package,'artifacts':['classes.dex','AndroidManifest.xml','resources.arsc']}
class Codegen:
    def __init__(self,target):
        if target not in TARGETS:raise ValueError(f'unsupported target: {target}')
        self.target=target
    def triple(self):
        return {'linux-x86_64':'x86_64-linux-gnu','linux-arm64':'aarch64-linux-gnu','android-arm64':'aarch64-linux-android','android-arm':'armv7a-linux-androideabi','windows-x86_64':'x86_64-w64-windows-gnu','macos-arm64':'aarch64-apple-darwin','macos-x86_64':'x86_64-apple-darwin'}[self.target]
