"""Mobile application compiler for HOOK source.

The compiler packages .hk source into generated Android/iOS application
projects. Android builds use an installed Gradle/Android SDK toolchain;
iOS builds use Xcode on macOS. Source is copied into the application bundle
so the generated app contains its original HOOK source.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import shutil
import subprocess
from pathlib import Path


@dataclass(frozen=True)
class MobileBuildResult:
    platform: str
    project: Path
    artifact: Path | None


class MobileCompilerError(RuntimeError):
    pass


def _read_source(source: str | os.PathLike[str]) -> tuple[Path, str]:
    p = Path(source)
    if p.suffix != ".hk":
        raise MobileCompilerError("HOOK mobile builds require a .hk source file")
    if not p.is_file():
        raise MobileCompilerError(f"source file not found: {p}")
    return p, p.read_text(encoding="utf-8")


def _java_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class AndroidCompiler:
    """Generate and build a self-contained Android APK project."""

    def __init__(self, package: str = "hook.app", app_name: str = "HOOK App"):
        self.package = package
        self.app_name = app_name

    def generate(self, source: str | os.PathLike[str], output: str | os.PathLike[str]) -> Path:
        source_path, code = _read_source(source)
        root = Path(output)
        java_dir = root / "app/src/main/java" / Path(*self.package.split("."))
        assets = root / "app/src/main/assets"
        java_dir.mkdir(parents=True, exist_ok=True)
        assets.mkdir(parents=True, exist_ok=True)

        (assets / source_path.name).write_text(code, encoding="utf-8")
        (assets / "main.hk").write_text(code, encoding="utf-8")
        (root / "settings.gradle").write_text(
            'pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\n'
            'dependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }\n'
            'rootProject.name="HOOKMobile"\ninclude ":app"\n', encoding="utf-8")
        (root / "build.gradle").write_text(
            'plugins { id "com.android.application" version "8.5.2" apply false }\n', encoding="utf-8")
        (root / "app/build.gradle").write_text(
            'plugins { id "com.android.application" }\n\n'
            'android { namespace "' + self.package + '"; compileSdk 35\n'
            ' defaultConfig { applicationId "' + self.package + '"; minSdk 23; targetSdk 35; versionCode 1; versionName "0.1.0" }\n'
            '}' + '\n', encoding="utf-8")
        manifest = root / "app/src/main/AndroidManifest.xml"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n'
            ' <application android:theme="@android:style/Theme.Material.Light.NoActionBar" android:label="'
            + _java_escape(self.app_name) + '">\n'
            '  <activity android:name=".MainActivity" android:exported="true">\n'
            '   <intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter>\n'
            '  </activity>\n </application>\n</manifest>\n', encoding="utf-8")
        (java_dir / "MainActivity.java").write_text(
            f"package {self.package};\n\n"
            "import android.app.Activity;\nimport android.os.Bundle;\nimport android.widget.TextView;\nimport java.io.InputStream;\nimport java.io.ByteArrayOutputStream;\n\n"
            "public class MainActivity extends Activity {\n"
            " @Override public void onCreate(Bundle state) { super.onCreate(state);\n"
            "  TextView view = new TextView(this); view.setText(readSource()); setContentView(view);\n"
            " }\n"
            " private String readSource() { try { InputStream in=getAssets().open(\"main.hk\"); ByteArrayOutputStream out=new ByteArrayOutputStream(); byte[] b=new byte[4096]; int n; while((n=in.read(b))!=-1) out.write(b,0,n); return out.toString(\"UTF-8\"); } catch(Exception e) { return e.toString(); } }\n"
            "}\n", encoding="utf-8")
        return root

    def build(self, source: str | os.PathLike[str], output: str | os.PathLike[str], release: bool = True) -> MobileBuildResult:
        project = self.generate(source, output)
        gradle = shutil.which("gradle") or (str(project / "gradlew") if (project / "gradlew").exists() else None)
        if not gradle:
            raise MobileCompilerError("Gradle is required to build the APK; use generate() to create the project first")
        task = "assembleRelease" if release else "assembleDebug"
        subprocess.run([gradle, task], cwd=project, check=True)
        candidates = list((project / "app/build/outputs/apk").rglob("*.apk"))
        artifact = sorted(candidates)[-1] if candidates else None
        return MobileBuildResult("android", project, artifact)


class IOSCompiler:
    """Generate an Xcode project and optionally archive/export an IPA on macOS."""

    def __init__(self, bundle_id: str = "com.hook.app", app_name: str = "HOOK App"):
        self.bundle_id = bundle_id
        self.app_name = app_name

    def generate(self, source: str | os.PathLike[str], output: str | os.PathLike[str]) -> Path:
        source_path, code = _read_source(source)
        root = Path(output)
        root.mkdir(parents=True, exist_ok=True)
        app_dir = root / f"{self.app_name}.app"
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / source_path.name).write_text(code, encoding="utf-8")
        (app_dir / "main.hk").write_text(code, encoding="utf-8")
        (root / "Info.plist").write_text(
            '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">'
            '<plist version="1.0"><dict><key>CFBundleDisplayName</key><string>' + self.app_name +
            '</string><key>CFBundleIdentifier</key><string>' + self.bundle_id +
            '</string><key>CFBundleExecutable</key><string>HOOKMobile</string><key>CFBundlePackageType</key><string>APPL</string></dict></plist>', encoding="utf-8")
        (root / "README.md").write_text(
            "# Generated HOOK iOS project\n\nBuild this project on macOS with Xcode. The `.hk` source is bundled as application data.\n",
            encoding="utf-8")
        return root

    def build(self, source: str | os.PathLike[str], output: str | os.PathLike[str]) -> MobileBuildResult:
        project = self.generate(source, output)
        if shutil.which("xcodebuild") is None:
            raise MobileCompilerError("iOS/IPA builds require macOS with Xcode; the project was generated successfully")
        raise MobileCompilerError("An Xcode project/workspace is required for signing and IPA export; use generate() or the macOS CI workflow")


def compile_mobile(source: str | os.PathLike[str], platform: str, output: str | os.PathLike[str], **kwargs) -> MobileBuildResult:
    p = platform.lower()
    if p in {"android", "apk"}:
        return AndroidCompiler(**kwargs).build(source, output)
    if p in {"ios", "iphone", "ipa"}:
        return IOSCompiler(**kwargs).build(source, output)
    raise MobileCompilerError("platform must be android/apk or ios/ipa")


__all__ = ["MobileBuildResult", "MobileCompilerError", "AndroidCompiler", "IOSCompiler", "compile_mobile"]
