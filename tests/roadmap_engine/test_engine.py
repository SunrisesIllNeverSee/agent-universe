import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from roadmap_engine.core import RoadmapError, validate_contract

SRC = Path(__file__).resolve().parents[2]


class RoadmapEngineTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.project = Path(self.t.name) / "project"
        self.invoke("init", str(self.project), success=True, project=False)

    def invoke(self, *args, success=None, project=True):
        env = dict(os.environ, PYTHONPATH=str(SRC))
        cmd = [sys.executable, "-m", "roadmap_engine"]
        if project:
            cmd += ["--project", str(self.project)]
        cmd += list(args)
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if success is True:
            self.assertEqual(r.returncode, 0, (r.stdout, r.stderr))
        if success is False:
            self.assertNotEqual(r.returncode, 0, (r.stdout, r.stderr))
        return r

    def state(self):
        return json.loads((self.project / ".roadmap" / "state.json").read_text())

    def roadmap(self):
        return json.loads((self.project / "roadmap.json").read_text())

    def put_roadmap(self, data):
        (self.project / "roadmap.json").write_text(json.dumps(data))

    def test_successful_three_task_execution_and_held_approval(self):
        self.invoke("validate", success=True)
        self.invoke("run", success=True)
        s = self.state()["tasks"]
        for k in ["PREPARE", "BUILD", "INSPECT"]:
            self.assertEqual(s[k]["status"], "passed")
        self.assertEqual(s["APPROVE"]["status"], "blocked")
        self.invoke("verify", success=True)
        self.invoke("resume", success=True)
        self.assertEqual(self.state()["tasks"]["PREPARE"]["attempt"], 1)
        self.assertTrue((self.project / "ROADMAP_STATUS.md").is_file())

    def test_tampering_with_accepted_artifact_fails_closed(self):
        self.invoke("run", success=True)
        (self.project / "build" / "output.json").write_text("not what was verified")
        self.invoke("verify", success=False)
        self.invoke("resume", success=False)

    def test_dep_cycle_and_missing_dep_rejected(self):
        d = self.roadmap()
        d["tasks"][0]["needs"] = ["BUILD"]
        self.put_roadmap(d)
        self.invoke("validate", success=False)
        d["tasks"][0]["needs"] = ["MISSING"]
        self.put_roadmap(d)
        self.invoke("validate", success=False)

    def test_output_escape_rejected(self):
        d = self.roadmap()
        d["tasks"][0]["outputs"] = ["../outside.txt"]
        self.put_roadmap(d)
        self.invoke("validate", success=False)

    def test_fail_then_explicit_retry_and_continue(self):
        d = self.roadmap()
        d["tasks"][0]["checks"][0]["argv"] = [sys.executable, "-c", "import sys; sys.exit(1)"]
        self.put_roadmap(d)
        self.invoke("run", success=False)
        self.assertEqual(self.state()["tasks"]["PREPARE"]["status"], "failed")
        self.assertEqual(self.state()["tasks"]["BUILD"]["status"], "pending")
        d["tasks"][0]["checks"][0]["argv"] = [sys.executable, "steps/workflow.py", "check", "prepare"]
        self.put_roadmap(d)
        self.invoke("retry", "PREPARE", "--acknowledge-side-effects", success=True)
        self.invoke("resume", success=True)
        self.assertEqual(self.state()["tasks"]["PREPARE"]["attempt"], 2)
        self.invoke("verify", success=True)

    def test_crash_recovery_refuses_silent_replay(self):
        self.invoke("run", "--max-tasks", "1", success=True)
        path = self.project / ".roadmap" / "state.json"
        d = self.state()
        d["tasks"]["BUILD"]["status"] = "running"
        path.write_text(json.dumps(d))
        self.invoke("resume", success=False)
        self.assertEqual(self.state()["tasks"]["BUILD"]["status"], "interrupted")
        self.invoke("retry", "BUILD", "--acknowledge-side-effects", success=True)
        self.invoke("resume", success=True)
        self.invoke("verify", success=True)

    def test_attestation_uses_file_evidence_and_detects_tamper(self):
        self.invoke("run", success=True)
        evidence = self.project / "owner-approved.txt"
        evidence.write_text("I explicitly approve this sample completion")
        self.invoke("attest", "APPROVE", "--evidence", str(evidence), success=True)
        self.invoke("verify", success=True)
        self.invoke("attest", "APPROVE", "--evidence", str(evidence), success=False)
        evidence.write_text("modified")
        self.invoke("verify", success=False)

    def test_independent_ready_task_runs_despite_other_failure(self):
        d = self.roadmap()
        d["tasks"][0]["checks"][0]["argv"] = [sys.executable, "-c", "import sys; sys.exit(1)"]
        d["tasks"].append({"id": "SECOND", "phase": "P1", "goal": "Execute independent branch", "needs": [], "scope": "local",
                           "executor": {"type": "command", "argv": [sys.executable, "steps/workflow.py", "run", "prepare"]},
                           "checks": [{"argv": [sys.executable, "steps/workflow.py", "check", "prepare"]}], "outputs": ["build/input.json"]})
        self.put_roadmap(d)
        self.invoke("run", success=False)
        self.assertEqual(self.state()["tasks"]["PREPARE"]["status"], "failed")
        self.assertEqual(self.state()["tasks"]["SECOND"]["status"], "passed")

    def test_task_contract_change_invalidates_past_pass(self):
        self.invoke("run", success=True)
        d = self.roadmap()
        d["tasks"][0]["goal"] = "New unchecked requirement"
        self.put_roadmap(d)
        self.invoke("verify", success=False)


if __name__ == "__main__":
    unittest.main()
