"""Native build/project helpers. They invoke installed toolchains only."""
from __future__ import annotations
from dataclasses import dataclass
import os,shutil,subprocess
from pathlib import Path
@dataclass(frozen=True)
class BuildTarget:
 name:str; compiler:str|None; linker:str|None; triple:str|None
class NativeBuilder:
 def __init__(self,cc=None,cxx=None):self.cc=cc or shutil.which('cc') or shutil.which('clang');self.cxx=cxx or shutil.which('c++') or shutil.which('clang++')
 def available(self):return bool(self.cc)
 def compile_c(self,source,output,flags=(),link_flags=()):
  if not self.cc:raise RuntimeError('no C compiler found')
  cmd=[self.cc,*map(str,flags),str(source),'-o',str(output),*map(str,link_flags)];return subprocess.run(cmd,check=True).returncode
 def compile_cpp(self,source,output,flags=(),link_flags=()):
  if not self.cxx:raise RuntimeError('no C++ compiler found')
  return subprocess.run([self.cxx,*map(str,flags),str(source),'-o',str(output),*map(str,link_flags)],check=True).returncode
 def target(self):return BuildTarget('native',self.cc,self.cxx,None)

def find_android_sdk():return os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
def find_android_ndk():
 sdk=find_android_sdk()
 if not sdk:return os.environ.get('ANDROID_NDK_HOME')
 p=Path(sdk)/'ndk';
 if p.exists():
  vs=sorted(p.iterdir());return str(vs[-1]) if vs else None
 return None
class AndroidProject:
 def __init__(self,root,package='hook.app',name='HOOK App'):self.root=Path(root);self.package=package;self.name=name
 def generate(self):
  self.root.mkdir(parents=True,exist_ok=True);src=self.root/'app/src/main/java'/Path(*self.package.split('.'));src.mkdir(parents=True,exist_ok=True);manifest=self.root/'app/src/main/AndroidManifest.xml';manifest.parent.mkdir(parents=True,exist_ok=True);manifest.write_text(f'<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="{self.package}"><application android:theme="@android:style/Theme.Material.Light.NoActionBar" android:label="{self.name}"><activity android:name=".MainActivity" android:exported="true"><intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter></activity></application></manifest>');(src/'MainActivity.java').write_text(f'package {self.package};\nimport android.app.Activity; import android.os.Bundle;\npublic class MainActivity extends Activity {{ @Override public void onCreate(Bundle b) {{ super.onCreate(b); }} }}\n');(self.root/'settings.gradle').write_text('pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\ndependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }\nrootProject.name="HOOKApp"\ninclude ":app"\n');(self.root/'app/build.gradle').write_text('plugins { id "com.android.application" version "8.5.2" }\n\nandroid { namespace "'+self.package+'"; compileSdk 35\n defaultConfig { applicationId "'+self.package+'"; minSdk 23; targetSdk 35; versionCode 1; versionName "0.1.0" } }\n');return self.root
__all__=['BuildTarget','NativeBuilder','find_android_sdk','find_android_ndk','AndroidProject']
