import setup_path  # pylint: disable=unused-import


def f(x: int):
    return x * 2


def test_func():
    assert f(3) == 6
