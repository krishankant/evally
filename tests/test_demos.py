"""The concept pages' demo maths, checked with Node (the demos run in the browser)."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_kappa_demo_maths():
    out = subprocess.run(["node", str(ROOT / "tests/demos/check-kappa.js"), str(ROOT / "concepts/demos/kappa.js")],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "all checks pass" in out.stdout
