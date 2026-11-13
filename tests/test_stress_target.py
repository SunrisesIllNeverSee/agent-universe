import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.stress_target import stress_target


def test_default_is_local():
    assert stress_target({}) == "http://127.0.0.1:8300"


@pytest.mark.parametrize("url", [
    "https://signomy.xyz", "https://agent-universe-production.up.railway.app",
    "http://127.0.0.1.example.com", "http://192.0.2.1",
])
def test_remote_targets_require_explicit_opt_in(url):
    with pytest.raises(ValueError, match="explicit"):
        stress_target({"CIVITAE_URL": url})


def test_remote_target_with_explicit_opt_in():
    assert stress_target({
        "CIVITAE_URL": "https://example.com/",
        "CIVITAE_STRESS_ALLOW_REMOTE": "1",
    }) == "https://example.com"


@pytest.mark.parametrize("url", ["ftp://example.com", "https://user:password@example.com", "https://example.com/?key=abc", "https://example.com/#x"])
def test_invalid_targets_are_rejected(url):
    with pytest.raises(ValueError):
        stress_target({"CIVITAE_URL": url, "CIVITAE_STRESS_ALLOW_REMOTE": "1"})


def test_script_exits_before_network_or_report_creation(tmp_path):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    (tmp_path / "stress_test.py").write_text((scripts / "stress_test.py").read_text())
    (tmp_path / "stress_target.py").write_text((scripts / "stress_target.py").read_text())
    (tmp_path / "requests.py").write_text(
        "def __getattr__(name):\n    raise AssertionError('network must not be called')\n"
    )
    env = {**os.environ, "CIVITAE_URL": "https://example.com"}
    env.pop("CIVITAE_STRESS_ALLOW_REMOTE", None)
    result = subprocess.run([sys.executable, str(tmp_path / "stress_test.py")],
                            env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert "requires explicit" in result.stderr
    assert not (tmp_path / "reports").exists()
