import pytest


def test_import_bdist_wheel() -> None:
    with pytest.warns(FutureWarning, match="no longer the canonical location"):
        from wheel.bdist_wheel import bdist_wheel  # noqa: F401
