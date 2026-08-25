"""Initial smoke test verifying package configuration."""

import oopple


def test_version():
    assert oopple.__version__ == "0.1.0"
