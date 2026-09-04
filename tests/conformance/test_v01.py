from hook.engine import Engine


def test_basics():
    e=Engine(); e.run('local x = 10\nlocal y = 2\nlocal z = x * y')
    assert e.root.get('z') == 20


def test_if_and_function():
    e=Engine(); e.run('function add(a: num, b: num) do\n    return a + b\nlocal result = add(2, 3)')
    assert e.root.get('result') == 5


def test_for_and_break():
    e=Engine(); e.run('local total = 0\nfor i in range(1, 10) do\n    total = total + i\n    if i == 4 then\n        break')
    assert e.root.get('total') == 10


def test_collections():
    e=Engine(); e.run('local a = [1, "x", 2.5]\nlocal b = (1, "x")\nlocal c = {"name": "hook"}')
    assert e.root.get('a')[1] == 'x'
    assert e.root.get('b')[0] == 1
    assert e.root.get('c')['name'] == 'hook'
