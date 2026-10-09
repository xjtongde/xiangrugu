"""Public package and module-entry-point contract for Task 1."""

from __future__ import annotations

import subprocess
import sys


def test_package_is_importable() -> None:
    """Removing the installed project package must make this test fail."""
    result = subprocess.run(
        [sys.executable, "-c", "import xiangrugu_datamgmt"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_module_help_is_available() -> None:
    """Removing the module entry point must make this test fail."""
    result = subprocess.run(
        [sys.executable, "-m", "xiangrugu_datamgmt", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "xiangrugu-datamgmt" in result.stdout
