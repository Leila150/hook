from hook.vm_core import Bytecode, Op, VM


def test_vm_load_uses_local_without_global_keyerror():
    vm = VM()
    vm.locals["x"] = 7
    code = Bytecode([Op("LOAD", "x"), Op("HALT")])
    assert vm.run(code) == 7


def test_vm_arithmetic_and_comparisons():
    code = Bytecode()
    code.emit("CONST", 2)
    code.emit("CONST", 3)
    code.emit("ADD")
    code.emit("CONST", 5)
    code.emit("EQ")
    code.emit("HALT")
    assert VM().run(code) is True


def test_vm_jump():
    code = Bytecode()
    code.emit("CONST", False)
    jump = code.emit("JUMP_IF_FALSE", None)
    code.emit("CONST", "bad")
    target = len(code.ops)
    code.emit("CONST", "ok")
    code.emit("HALT")
    code.patch(jump, target)
    assert VM().run(code) == "ok"
