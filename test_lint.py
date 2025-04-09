import subprocess
import pytest

def test_flake8():
    """Проверка кода на соответствие PEP 8."""
    result = subprocess.run(["flake8", "."], capture_output=True, text=True)
    assert result.returncode == 0, f"Flake8 found issues:\n{result.stdout}"

def test_mypy():
    """Проверка типов."""
    result = subprocess.run(["mypy", "."], capture_output=True, text=True)
    assert result.returncode == 0, f"Mypy found issues:\n{result.stdout}"