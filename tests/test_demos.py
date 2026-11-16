"""The concept pages' demo maths, checked with Node (the demos run in the browser)."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DEMOS = ["kappa", "position-bias", "bootstrap", "sample-size"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("name", DEMOS)
def test_demo_maths(name):
    out = subprocess.run(["node", str(ROOT / f"tests/demos/check-{name}.js"), str(ROOT / f"concepts/demos/{name}.js")],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "all checks pass" in out.stdout
