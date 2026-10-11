"""Private falsifier for the mission existence oracle (do not publish).

Runs tests/test_mission_existence_oracle.py twice in-process (TestClient, temp
data root from tests/conftest.py, synthetic ids/keys only):
  1. against the current code           -> expect all GREEN
  2. with the pre-fix gate re-injected   -> expect RED (oracle reopened)
The pre-fix behaviour is simulated by a throwaway pytest plugin that patches
app.routes.missions so unknown ids give 404 and foreign-owned ids give 403.
No network, no live hosts, no files outside a temp dir are touched.
"""
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = "tests/test_mission_existence_oracle.py"

PLUGIN = textwrap.dedent('''
    import pytest
    from fastapi import HTTPException

    @pytest.fixture(autouse=True)
    def _old_gate(monkeypatch):
        from app.routes import missions as m

        def old_gate(request, mission_id, mission):
            agent_id = m._acting_agent_id(request)
            if mission is None:
                return m.JSONResponse({"error": "Mission not found"}, status_code=404)
            if agent_id is not None and not m._agent_may_mutate(agent_id, mission):
                raise HTTPException(403, "Only the mission owner or an operator may modify this mission")
            return None

        def old_authorize(request, mission):
            if not m._agent_may_mutate(m._acting_agent_id(request), mission):
                raise HTTPException(403, "Only the mission owner or an operator may modify this mission")

        monkeypatch.setattr(m, "_mission_gate", old_gate)
        monkeypatch.setattr(m, "_authorize_mission_mutation", old_authorize)
        yield
''')


def run(extra_env=None, plugin_dir=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(ROOT), plugin_dir, env.get("PYTHONPATH")]))
    cmd = [sys.executable, "-m", "pytest", TARGET, "-q", "-p", "no:cacheprovider"]
    if plugin_dir:
        cmd += ["-p", "oracle_old_gate"]
    p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    return p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-300:]


if __name__ == "__main__":
    print("current code :", run())
    with tempfile.TemporaryDirectory() as d:
        Path(d, "oracle_old_gate.py").write_text(PLUGIN)
        print("pre-fix gate :", run(plugin_dir=d))
