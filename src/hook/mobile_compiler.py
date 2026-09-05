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

def _pbx_quote(value):
    return '"'+value.replace('\\','\\\\').replace('"','\\"')+'"'

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
        manifest=root/"app/src/main/AndroidManifest.xml";manifest.parent.mkdir(parents=True,exist_ok=True);label=html.escape(self.app_name,quote=True)
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
        project=self.generate(source,output);gradle=(project/"gradlew") if (project/"gradlew").exists() else None;gradle_path=str(gradle) if gradle else shutil.which("gradle")
        if not gradle_path: raise MobileCompilerError("Gradle is required to build the generated Android project; use generate() on systems without Gradle")
        task="assembleRelease" if release else "assembleDebug";subprocess.run([gradle_path,task],cwd=project,check=True)
        candidates=list((project/"app/build/outputs/apk").rglob("*.apk"));return MobileBuildResult("android",project,sorted(candidates)[-1] if candidates else None)

class IOSCompiler:
    """Generate a genuine, parseable Xcode project containing the HOOK shell."""
    def __init__(self,bundle_id="com.hook.app",app_name="HOOK App"):
        self.bundle_id=_validate_identifier(bundle_id,"iOS bundle identifier");self.app_name=app_name
    def generate(self,source,output):
        source_path,code=_read_source(source);root=Path(output);name=re.sub(r"[^A-Za-z0-9_]","_",self.app_name) or "HOOKApp";project_dir=root/f"{name}.xcodeproj";project_dir.mkdir(parents=True,exist_ok=True);src=root/name;src.mkdir(parents=True,exist_ok=True)
        (src/"main.hk").write_text(code,encoding="utf-8")
        (src/"HOOKApp.swift").write_text('import SwiftUI\n@main struct HOOKApp: App { var body: some Scene { WindowGroup { Text("HOOK source bundled") } } }\n',encoding="utf-8")
        (src/"Info.plist").write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>CFBundleDisplayName</key><string>{html.escape(self.app_name)}</string><key>CFBundleIdentifier</key><string>{html.escape(self.bundle_id)}</string><key>CFBundlePackageType</key><string>APPL</string></dict></plist>
''',encoding="utf-8")
        (root/"README.md").write_text("# Generated HOOK iOS project\n\nThe Xcode project is a native shell and bundles `main.hk`; a HOOK runtime must be embedded separately to execute the language.\n",encoding="utf-8")
        (root/"PROJECT_STATUS.txt").write_text("Xcode project generated. Source is bundled but not interpreted by Swift.\n",encoding="utf-8")
        # Do not emit a comment-only placeholder: Xcode reports that as
        # "unsupported Xcode version (0)". Emit the OpenStep object graph that
        # Xcode expects, including a project object, target, build phases,
        # configuration lists, and file references.
        qname=_pbx_quote(name)
        project=f'''// !$*UTF8*$!
{{
    archiveVersion = 1;
    classes = {{}};
    objectVersion = 77;
    objects = {{
        A10000010000000000000001 = {{isa = PBXBuildFile; fileRef = A10000020000000000000002; }};
        A10000020000000000000002 = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = HOOKApp.swift; sourceTree = "<group>"; }};
        A10000030000000000000003 = {{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = {name}.app; sourceTree = BUILT_PRODUCTS_DIR; }};
        A10000040000000000000004 = {{isa = PBXFrameworksBuildPhase; buildActionMask = 2147483647; files = (); runOnlyForDeploymentPostprocessing = 0; }};
        A10000050000000000000005 = {{isa = PBXGroup; children = (A10000020000000000000002); name = {qname}; sourceTree = "<group>"; }};
        A10000060000000000000006 = {{isa = PBXGroup; children = (A10000050000000000000005, A10000030000000000000003); sourceTree = "<group>"; }};
        A10000070000000000000007 = {{isa = PBXNativeTarget; buildConfigurationList = A10000080000000000000008; buildPhases = (A10000090000000000000009, A10000040000000000000004, A100000A000000000000000A); buildRules = (); dependencies = (); name = {qname}; productName = {qname}; productReference = A10000030000000000000003; productType = "com.apple.product-type.application"; }};
        A10000080000000000000008 = {{isa = XCConfigurationList; buildConfigurations = (A100000D000000000000000D, A100000E000000000000000E); defaultConfigurationIsVisible = 0; defaultConfigurationName = Release; }};
        A10000090000000000000009 = {{isa = PBXSourcesBuildPhase; buildActionMask = 2147483647; files = (A10000010000000000000001); runOnlyForDeploymentPostprocessing = 0; }};
        A100000A000000000000000A = {{isa = PBXResourcesBuildPhase; buildActionMask = 2147483647; files = (); runOnlyForDeploymentPostprocessing = 0; }};
        A100000B000000000000000B = {{isa = PBXProject; attributes = {{ LastSwiftUpdateCheck = 2630; LastUpgradeCheck = 2630; TargetAttributes = {{ A10000070000000000000007 = {{ CreatedOnToolsVersion = 26.0; }}; }}; }}; buildConfigurationList = A100000C000000000000000C; compatibilityVersion = "Xcode 3.2"; developmentRegion = en; hasScannedForEncodings = 0; knownRegions = (en, Base); mainGroup = A10000060000000000000006; productRefGroup = A10000060000000000000006; projectDirPath = ""; projectRoot = ""; targets = (A10000070000000000000007); }};
        A100000C000000000000000C = {{isa = XCConfigurationList; buildConfigurations = (A100000F000000000000000F, A10000100000000000000010); defaultConfigurationIsVisible = 0; defaultConfigurationName = Release; }};
        A100000D000000000000000D = {{isa = XCBuildConfiguration; buildSettings = {{ CLANG_ENABLE_MODULES = YES; CODE_SIGN_STYLE = Automatic; CURRENT_PROJECT_VERSION = 1; GENERATE_INFOPLIST_FILE = YES; INFOPLIST_KEY_CFBundleDisplayName = {qname}; IPHONEOS_DEPLOYMENT_TARGET = 15.0; LD_RUNPATH_SEARCH_PATHS = ("$(inherited)", "@executable_path/Frameworks"); PRODUCT_BUNDLE_IDENTIFIER = {self.bundle_id}; PRODUCT_NAME = "$(TARGET_NAME)"; SWIFT_VERSION = 5.0; TARGETED_DEVICE_FAMILY = "1,2"; }}; name = Debug; }};
        A100000E000000000000000E = {{isa = XCBuildConfiguration; buildSettings = {{ CLANG_ENABLE_MODULES = YES; CODE_SIGN_STYLE = Automatic; CURRENT_PROJECT_VERSION = 1; GENERATE_INFOPLIST_FILE = YES; INFOPLIST_KEY_CFBundleDisplayName = {qname}; IPHONEOS_DEPLOYMENT_TARGET = 15.0; LD_RUNPATH_SEARCH_PATHS = ("$(inherited)", "@executable_path/Frameworks"); PRODUCT_BUNDLE_IDENTIFIER = {self.bundle_id}; PRODUCT_NAME = "$(TARGET_NAME)"; SWIFT_OPTIMIZATION_LEVEL = "-O"; SWIFT_VERSION = 5.0; TARGETED_DEVICE_FAMILY = "1,2"; }}; name = Release; }};
        A100000F000000000000000F = {{isa = XCBuildConfiguration; buildSettings = {{ CLANG_ENABLE_MODULES = YES; SWIFT_VERSION = 5.0; }}; name = Debug; }};
        A10000100000000000000010 = {{isa = XCBuildConfiguration; buildSettings = {{ CLANG_ENABLE_MODULES = YES; SWIFT_VERSION = 5.0; }}; name = Release; }};
    }};
    rootObject = A100000B000000000000000B;
}}
'''
        (project_dir/"project.pbxproj").write_text(project,encoding="utf-8")
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
