from hook.completion import ExpressionVM, Value, ModuleResolver, TargetResolver, Serializer, CompletePipeline


def test_expression_vm_arithmetic_comparison_and_calls():
    vm=ExpressionVM({"double":lambda x:x*2})
    assert vm.run("2 + 3 * 4")==14
    assert vm.run("2 < 3 and 4 == 4") is True
    assert vm.run("double(6)")==12


def test_autograd():
    x=Value(3); y=x*x+x
    y.backward()
    assert y.data==12
    assert x.grad==7


def test_module_resolver(tmp_path):
    (tmp_path/"hello.hk").write_text("print(1)\n",encoding="utf-8")
    spec=ModuleResolver([tmp_path]).resolve("hello")
    assert spec.path.name=="hello.hk"


def test_target_resolver():
    assert TargetResolver().resolve("android-arm64").triple=="aarch64-linux-android"


def test_serializer(tmp_path):
    p=tmp_path/"data.hkd"
    Serializer.save(p,{"x":[1,2,3]})
    assert Serializer.load(p)=={"x":[1,2,3]}


def test_pipeline_rejects_tabs():
    result=CompletePipeline().compile("\tprint(1)")
    assert not result.ok()
