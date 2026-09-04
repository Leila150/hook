from hook import Engine, VERSION, FeatureRegistry


def test_version():
    assert VERSION == "1.0.0"


def test_basic_execution(capsys):
    Engine().run('print("hello")')
    assert capsys.readouterr().out == "hello\n"


def test_arithmetic(capsys):
    Engine().run('local x = 10\nlocal y = 20\nprint(x + y)')
    assert capsys.readouterr().out == "30\n"


def test_condition_and_function(capsys):
    source = '''
function add(a: num, b: num) do
    return a + b
local result = add(2, 3)
if result == 5 then
    print("PASS")
'''
    Engine().run(source)
    assert capsys.readouterr().out == "PASS\n"


def test_modules_are_available():
    e = Engine()
    assert e.features.has("json")
    assert e.features.has("web")
    assert e.features.has("ai")
    assert e.features.has("game")
    assert e.features.has("native")
    assert e.features.has("concurrency")


def test_from_import(capsys):
    Engine().run('from math import sqrt\nprint(sqrt(16))')
    assert capsys.readouterr().out == "4.0\n"
