import pytest


def test_import_bdist_wheel() -> None:
    with pytest.warns(DeprecationWarning, match="module has been removed"):
        from wheel.bdist_wheel import bdist_wheel  # noqa: F401
