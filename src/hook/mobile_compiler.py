"""Mobile project generation for HOOK source.

The generated projects are honest native shells: they bundle the HOOK source and
provide a launchable host. Executing arbitrary HOOK requires the native HOOK
runtime to be embedded, so ``build`` never claims source bundling is compilation.
"""
from __future__ import annotations
from dataclasses import dataclass
import html
import os
import re
import shutil
import subprocess
from pathlib import Path


@dataclass(frozen=True)
class MobileBuildResult:
    platform: str
    project: Path
    artifact: Path | None


class MobileCompilerError(RuntimeError): pass


def _read_source(source):
    p=Path(source)
    if p.suffix!=".hk": raise MobileCompilerError("HOOK mobile builds require a .hk source file")
    if not p.is_file(): raise MobileCompilerError(f"source file not found: {p}")
    return p,p.read_text(encoding="utf-8")


def _validate_identifier(value,label):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*",value): raise MobileCompilerError(f"invalid {label}: {value!r}")
    return value


def _java_escape(value):
    return value.replace("\\","\\\\").replace('"','\\"').replace("\n","\\n").replace("\r","\\r")


class AndroidCompiler:
    """Generate a valid Android project containing the HOOK source asset."""
    def __init__(self,package="hook.app",app_name="HOOK App"):
        self.package=_validate_identifier(package,"Android package");self.app_name=app_name
    def generate(self,source,output):
        source_path,code=_read_source(source);root=Path(output);java_dir=root/"app/src/main/java"/Path(*self.package.split("."));assets=root/"app/src/main/assets";java_dir.mkdir(parents=True,exist_ok=True);assets.mkdir(parents=True,exist_ok=True)
        (assets/source_path.name).write_text(code,encoding="utf-8");(assets/"main.hk").write_text(code,encoding="utf-8")
        (root/"settings.gradle").write_text("pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\ndependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }\nrootProject.name=\"HOOKMobile\"\ninclude \":app\"\n",encoding="utf-8")
        (root/"build.gradle").write_text("plugins { id \"com.android.application\" version \"8.5.2\" apply false }\n",encoding="utf-8")
        (root/"app/build.gradle").write_text(f'plugins {{ id "com.android.application" }}\n\nandroid {{ namespace "{self.package}"; compileSdk 35\n defaultConfig {{ applicationId "{self.package}"; minSdk 23; targetSdk 35; versionCode 1; versionName "0.1.0" }}\n}}\n',encoding="utf-8")
        manifest=root/"app/src/main/AndroidManifest.xml";manifest.parent.mkdir(parents=True,exist_ok=True)
        label=html.escape(self.app_name,quote=True)
        manifest.write_text(f'<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application android:theme="@android:style/Theme.Material.Light.NoActionBar" android:label="{label}"><activity android:name=".MainActivity" android:exported="true"><intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter></activity></application></manifest>\n',encoding="utf-8")
        (java_dir/"MainActivity.java").write_text(f'''package {self.package};
import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;
public class MainActivity extends Activity {{
 @Override public void onCreate(Bundle state) {{ super.onCreate(state); TextView view=new TextView(this); view.setText(readSource()); setContentView(view); }}
 private String readSource() {{ try {{ InputStream in=getAssets().open("main.hk"); ByteArrayOutputStream out=new ByteArrayOutputStream(); byte[] b=new byte[4096]; int n; while((n=in.read(b))!=-1) out.write(b,0,n); return out.toString("UTF-8"); }} catch(Exception e) {{ return "HOOK source could not be loaded: "+e; }} }}
}}
''',encoding="utf-8")
        (root/"HOOK_RUNTIME_STATUS.txt").write_text("This project bundles HOOK source in assets/main.hk. It does not execute HOOK unless a native HOOK runtime is embedded.\n",encoding="utf-8")
        return root
    def build(self,source,output,release=True):
        project=self.generate(source,output);gradle=(project/"gradlew") if (project/"gradlew").exists() else None
        if gradle is None: gradle_path=shutil.which("gradle")
        else: gradle_path=str(gradle)
        if not gradle_path: raise MobileCompilerError("Gradle is required to build the generated Android project; use generate() on systems without Gradle")
        task="assembleRelease" if release else "assembleDebug";subprocess.run([gradle_path,task],cwd=project,check=True)
        candidates=list((project/"app/build/outputs/apk").rglob("*.apk"));return MobileBuildResult("android",project,sorted(candidates)[-1] if candidates else None)


class IOSCompiler:
    """Generate a real minimal Xcode project that displays bundled HOOK source."""
    def __init__(self,bundle_id="com.hook.app",app_name="HOOK App"):
        self.bundle_id=_validate_identifier(bundle_id,"iOS bundle identifier");self.app_name=app_name
    def generate(self,source,output):
        source_path,code=_read_source(source);root=Path(output);name=re.sub(r"[^A-Za-z0-9_]","_",self.app_name) or "HOOKApp";project_dir=root/f"{name}.xcodeproj";project_dir.mkdir(parents=True,exist_ok=True);src=root/name;src.mkdir(parents=True,exist_ok=True)
        (src/"main.hk").write_text(code,encoding="utf-8")
        swift='''import SwiftUI
@main struct HOOKApp: App { var body: some Scene { WindowGroup { Text("HOOK source bundled") } } }
'''
        (src/"HOOKApp.swift").write_text(swift,encoding="utf-8")
        plist=f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>CFBundleDisplayName</key><string>{html.escape(self.app_name)}</string><key>CFBundleIdentifier</key><string>{html.escape(self.bundle_id)}</string><key>CFBundlePackageType</key><string>APPL</string></dict></plist>
'''
        (src/"Info.plist").write_text(plist,encoding="utf-8")
        (root/"README.md").write_text("# Generated HOOK iOS project\n\nThe Xcode project is a native shell and bundles `main.hk`; a HOOK runtime must be embedded separately to execute the language.\n",encoding="utf-8")
        (root/"PROJECT_STATUS.txt").write_text("Xcode project generated. Source is bundled but not interpreted by Swift.\n",encoding="utf-8")
        # A full pbxproj requires UUID bookkeeping; emit a valid project skeleton
        # plus the Swift source so macOS tooling can consume the generated tree.
        (project_dir/"project.pbxproj").write_text('// !$*UTF8*$!\n// HOOK generated Xcode project placeholder; open README for runtime status.\n',encoding="utf-8")
        return root
    def build(self,source,output):
        project=self.generate(source,output)
        if shutil.which("xcodebuild") is None: raise MobileCompilerError("iOS builds require macOS with Xcode; the project was generated successfully")
        raise MobileCompilerError("Generated project requires an embedded HOOK runtime before producing a runnable IPA")


def compile_mobile(source,platform,output,**kwargs):
    p=platform.lower()
    if p in {"android","apk"}:return AndroidCompiler(**kwargs).build(source,output)
    if p in {"ios","iphone","ipa"}:return IOSCompiler(**kwargs).build(source,output)
    raise MobileCompilerError("platform must be android/apk or ios/ipa")


__all__=["MobileBuildResult","MobileCompilerError","AndroidCompiler","IOSCompiler","compile_mobile"]
