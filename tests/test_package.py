import subprocess
import sys

import traveler_quartet


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "traveler_quartet", *args],
        capture_output=True,
        text=True,
    )


def test_the_package_exposes_its_version():
    assert traveler_quartet.__version__ == "0.0.1"


def test_the_command_prints_the_version():
    result = _run("--version")
    assert result.returncode == 0
    assert "0.0.1" in result.stdout


def test_a_mode_that_is_not_built_yet_says_so_and_fails():
    for mode in ("play", "cli", "tournament"):
        result = _run(mode)
        assert result.returncode == 1
        assert "not built yet" in result.stderr


def test_an_unknown_mode_is_refused():
    assert _run("fly").returncode == 2
