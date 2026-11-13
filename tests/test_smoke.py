import display_location


def test_version():
    assert display_location.__version__ == "1.0.0"


def test_main_module_imports():
    from display_location import __main__

    assert __main__.parse_args([]) is not None
