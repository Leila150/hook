from pathlib import Path

def test_3d_public_foundations(tmp_path):
    from hook import Engine3D, Vec3D, Mesh3D, PhysicsWorld3D, RigidBody3D, ShaderLibrary, save_scene, load_scene
    e=Engine3D(64,64); o=e.add_cube('box',2,Vec3D(0,0,4)); assert len(e.frame())==64*64*3
    world=PhysicsWorld3D(); body=world.body(o,gravity=False); body.velocity=Vec3D(1,0,0); world.step(1); assert o.transform.position.x>0
    lib=ShaderLibrary().builtin(); assert lib.has('unlit')
    p=tmp_path/'scene.json';save_scene(e.scene,p); s=load_scene(p);assert len(s.objects)==1

def test_compat_profile(tmp_path):
    from hook import CompatibilityConfig, WinlatorRuntime
    rt=WinlatorRuntime(CompatibilityConfig(), profile_dir=tmp_path); p=rt.create_profile('demo'); assert p.exists(); assert rt.list_profiles()==['demo']; assert rt.load_profile('demo').name=='demo'

def test_android_project(tmp_path):
    from hook import AndroidProject
    root=AndroidProject(tmp_path/'app','com.example.hook').generate(); assert (root/'settings.gradle').exists(); assert (root/'app/src/main/AndroidManifest.xml').exists()
