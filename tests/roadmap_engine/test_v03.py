"""Roadmap Engine v0.3 — long-run execution semantics.

Covers: dependent chains, branching, parallel non-conflicting lanes,
file-claim conflicts, failure isolation, resume/dedup, retry policy,
stale receipts, contract drift, schema migration, adapter boundary,
files-scope enforcement, unauthorized-scope rejection, state restore.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SRC = Path(__file__).resolve().parents[2]

TASK_CMD = [sys.executable, "steps/wf.py"]


def write_steps(project):
    steps = project / "steps"
    steps.mkdir(parents=True, exist_ok=True)
    (steps / "wf.py").write_text('''import json, sys
from pathlib import Path
R = Path(__file__).resolve().parents[1]
R.joinpath("out").mkdir(exist_ok=True)
kind, name = sys.argv[1:3]
if kind == "produce":
    R.joinpath("out", name + ".json").write_text(json.dumps({"task": name}))
elif kind == "check":
    d = json.loads(R.joinpath("out", name + ".json").read_text())
    assert d["task"] == name
elif kind == "fail":
    sys.exit(3)
elif kind == "outside":
    R.joinpath("outside-evil.json").write_text("{}")
elif kind == "marker":
    R.joinpath("out", "marker.txt").write_text("run")
else:
    raise ValueError(kind + name)
''', encoding="utf-8")


def make_project(tasks, tmp):
    project = Path(tmp) / "proj"
    project.mkdir(parents=True)
    write_steps(project)
    road = {"schema_version": 2, "project": "v03-test", "tasks": tasks}
    (project / "roadmap.json").write_text(json.dumps(road), encoding="utf-8")
    return project


def cmd_task(k, stage=None, deps=(), **extra):
    t = {"id": k, "phase": "P", "goal": k + " goal",
         "needs": list(deps), "scope": "local",
         "executor": {"type": "command", "argv": TASK_CMD + ["produce", stage or k]},
         "checks": [{"argv": TASK_CMD + ["check", stage or k]}],
         "outputs": [f"out/{stage or k}.json"]}
    t.update(extra)
    return t


class V03(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)

    def invoke(self, project, *args, success=None, env=None):
        e = dict(os.environ, PYTHONPATH=str(SRC))
        if env:
            e.update(env)
        r = subprocess.run([sys.executable, "-m", "roadmap_engine", "--project", str(project)] + list(args),
                           capture_output=True, text=True, env=e)
        if success is True:
            self.assertEqual(r.returncode, 0, (r.stdout, r.stderr))
        if success is False:
            self.assertNotEqual(r.returncode, 0, (r.stdout, r.stderr))
        return r

    def state(self, project):
        return json.loads((project / ".roadmap" / "state.json").read_text())

    # ── dependent chain + branching ──
    def test_chain_and_branches(self):
        proj = make_project([
            cmd_task("AA"), cmd_task("B1", deps=["AA"]), cmd_task("B2", deps=["AA"]),
            cmd_task("CC", deps=["B1", "B2"]),
        ], self.t.name)
        self.invoke(proj, "run", success=True)
        st = self.state(proj)["tasks"]
        self.assertTrue(all(v["status"] == "passed" for v in st.values()))
        self.assertTrue(all((proj / ".roadmap" / "receipts" / f"{k}.json").exists() for k in st))

    # ── failure isolation: dependent held, independent proceeds ──
    def test_failure_isolation(self):
        proj = make_project([
            cmd_task("OK1"),
            {"id": "BAD", "phase": "P", "goal": "fails", "needs": [], "scope": "local",
             "executor": {"type": "command", "argv": TASK_CMD + ["fail", "x"]},
             "checks": [{"argv": TASK_CMD + ["check", "x"]}], "outputs": ["out/x.json"]},
            cmd_task("DOWN", deps=["BAD"]),
            cmd_task("OK2"),
        ], self.t.name)
        # BAD runs `produce fail` which exits 3
        r = self.invoke(proj, "run")
        self.assertEqual(r.returncode, 3)
        st = self.state(proj)["tasks"]
        self.assertEqual(st["OK1"]["status"], "passed")
        self.assertEqual(st["OK2"]["status"], "passed")
        self.assertEqual(st["BAD"]["status"], "failed")
        self.assertEqual(st["DOWN"]["status"], "pending")

    # ── resume does not re-execute ──
    def test_resume_no_duplicate(self):
        proj = make_project([cmd_task("AA"), cmd_task("BB", deps=["AA"])], self.t.name)
        self.invoke(proj, "run", success=True)
        r2 = self.invoke(proj, "run", success=True)
        self.assertIn("tasks processed: 0", r2.stdout)

    # ── interrupted → explicit retry required ──
    def test_interrupted_requires_retry(self):
        proj = make_project([cmd_task("AA")], self.t.name)
        sd = proj / ".roadmap"
        sd.mkdir()
        (sd / "state.json").write_text(json.dumps({
            "format": 1, "project": "v03-test",
            "tasks": {"AA": {"status": "running", "attempt": 1}}, "last_update": "x"}))
        r = self.invoke(proj, "run")
        self.assertIn("Recovered 1 interrupted", r.stdout)
        st = self.state(proj)["tasks"]["AA"]
        self.assertEqual(st["status"], "interrupted")
        r2 = self.invoke(proj, "run")
        self.assertIn("tasks processed: 0", r2.stdout)
        self.invoke(proj, "retry", "AA", "--acknowledge-side-effects", success=True)
        self.invoke(proj, "run", success=True)
        self.assertEqual(self.state(proj)["tasks"]["AA"]["status"], "passed")

    # ── stale receipt / modified artifact detected ──
    def test_stale_artifact_detected(self):
        proj = make_project([cmd_task("AA")], self.t.name)
        self.invoke(proj, "run", success=True)
        (proj / "out" / "AA.json").write_text('{"tampered": true}')
        self.invoke(proj, "verify", success=False)

    # ── contract change → drift report ──
    def test_contract_change_drift(self):
        proj = make_project([cmd_task("AA")], self.t.name)
        self.invoke(proj, "run", success=True)
        road = json.loads((proj / "roadmap.json").read_text())
        road["tasks"][0]["goal"] = "changed goal"  # core field — real contract change
        (proj / "roadmap.json").write_text(json.dumps(road))
        r = self.invoke(proj, "drift", success=False)
        self.assertIn("contract changed", r.stdout)
        # metadata-only change does NOT drift the receipt
        road = json.loads((proj / "roadmap.json").read_text())
        road["tasks"][0]["goal"] = "AA goal"
        road["tasks"][0]["risk"] = "low"
        road["tasks"][0]["acceptance"] = "any note"
        (proj / "roadmap.json").write_text(json.dumps(road))
        self.invoke(proj, "drift", success=True)

    # ── migration v1→v2 preserves receipts ──
    def test_migration_preserves_receipts(self):
        proj = make_project([cmd_task("AA")], self.t.name)
        road = json.loads((proj / "roadmap.json").read_text())
        road["schema_version"] = 1
        (proj / "roadmap.json").write_text(json.dumps(road))
        self.invoke(proj, "run", success=True)
        self.invoke(proj, "migrate", success=True)
        self.invoke(proj, "verify", success=True)  # receipts still validate after migration
        self.assertEqual(json.loads((proj / "roadmap.json").read_text())["schema_version"], 2)
        # rollback restores v1
        self.invoke(proj, "migrate", "--rollback", success=True)
        self.assertEqual(json.loads((proj / "roadmap.json").read_text())["schema_version"], 1)

    # ── adapter boundary: missing adapter blocks, present adapter runs ──
    def test_adapter_boundary(self):
        tasks = [{"id": "AD", "phase": "P", "goal": "adapter task", "needs": [],
                  "scope": "local",
                  "executor": {"type": "adapter", "adapter": "nope", "params": {}},
                  "checks": [{"argv": TASK_CMD + ["check", "AD"]}],
                  "outputs": ["out/AD.json"]}]
        proj = make_project(tasks, self.t.name)
        self.invoke(proj, "run", success=True)  # blocked, not failed
        self.assertEqual(self.state(proj)["tasks"]["AD"]["status"], "blocked")
        # provide adapter → runs
        (proj / "adapters").mkdir()
        (proj / "adapters" / "nope.json").write_text(json.dumps(
            {"argv": TASK_CMD + ["produce", "AD"]}))
        # blocked tasks don't auto-clear: reset manually
        st = self.state(proj)
        st["tasks"]["AD"]["status"] = "pending"
        (proj / ".roadmap" / "state.json").write_text(json.dumps(st))
        self.invoke(proj, "run", success=True)
        self.assertEqual(self.state(proj)["tasks"]["AD"]["status"], "passed")

    # ── files scope enforcement ──
    def test_files_scope_enforced(self):
        t = cmd_task("AA", stage="outside", files=["out/"])
        t["outputs"] = ["outside-evil.json"]
        proj = make_project([t], self.t.name)
        r = self.invoke(proj, "run", success=False)
        st = self.state(proj)["tasks"]["AA"]
        self.assertEqual(st["status"], "failed")

    # ── parallel lanes: disjoint files run in wave, overlap serializes ──
    def test_parallel_lanes(self):
        proj = make_project([
            cmd_task("X1", files=["out/X1.json"], lane="L1"),
            cmd_task("X2", files=["out/X2.json"], lane="L2"),
            cmd_task("YY", files=["out/"], lane="L3"),  # overlaps both
        ], self.t.name)
        r = self.invoke(proj, "run", "--parallel", "2", success=True)
        self.assertIn("WAVE", r.stdout)
        st = self.state(proj)["tasks"]
        self.assertTrue(all(v["status"] == "passed" for v in st.values()))

    # ── retry policy ──
    def test_retry_policy(self):
        t = {"id": "RR", "phase": "P", "goal": "fails then retries", "needs": [], "scope": "local",
         "executor": {"type": "command", "argv": TASK_CMD + ["fail", "x"]},
         "checks": [{"argv": TASK_CMD + ["check", "x"]}], "outputs": ["out/x.json"],
         "retry": {"max_attempts": 2, "backoff_seconds": 0}}
        proj = make_project([t], self.t.name)
        self.invoke(proj, "run")
        st = self.state(proj)["tasks"]["RR"]
        self.assertEqual(st["status"], "failed")
        self.assertEqual(st["attempt"], 2)

    # ── approval scope cannot be automatic ──
    def test_approval_never_auto(self):
        tasks = [{"id": "G", "phase": "P", "goal": "gate", "needs": [], "scope": "approval",
                  "executor": {"type": "command", "argv": ["echo", "x"]}}]
        proj = make_project(tasks, self.t.name)
        self.invoke(proj, "validate", success=False)

    # ── restart restores state ──
    def test_restart_restores_state(self):
        proj = make_project([cmd_task("AA"), cmd_task("BB", deps=["AA"])], self.t.name)
        self.invoke(proj, "run", "--max-tasks", "1", success=True)
        self.assertEqual(self.state(proj)["tasks"]["AA"]["status"], "passed")
        self.assertEqual(self.state(proj)["tasks"]["BB"]["status"], "pending")
        self.invoke(proj, "run", success=True)
        self.assertEqual(self.state(proj)["tasks"]["BB"]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
