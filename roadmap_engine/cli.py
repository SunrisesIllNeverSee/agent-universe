"""`python -m roadmap_engine` CLI."""
import argparse
import json
from pathlib import Path
import shutil
import sys

from .core import (RoadmapError, append_event, atomic_json, candidates,
                   contract_digest, digest, canon_bytes, execute_one, file_digest,
                   files_conflict, load, lock, non_conflicting_wave, now,
                   read_state, recover_interrupted, report, verify_existing,
                   write_state, run_argv)
from concurrent.futures import ThreadPoolExecutor
import shutil as _shutil


def sample_script():
    return '''"""Replace these sample actions with real workflow steps and checks."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "build"

def run(stage):
    DATA.mkdir(exist_ok=True)
    if stage == "prepare":
        (DATA / "input.json").write_text(json.dumps({"items": [1,2,3]}))
    elif stage == "build":
        items = json.loads((DATA / "input.json").read_text())["items"]
        (DATA / "output.json").write_text(json.dumps({"sum": sum(items)}))
    elif stage == "inspect":
        total = json.loads((DATA / "output.json").read_text())["sum"]
        (DATA / "inspection.txt").write_text(f"verified total={total}\\n")
    else:
        raise ValueError(stage)

def check(stage):
    if stage == "prepare":
        assert json.loads((DATA / "input.json").read_text())["items"] == [1,2,3]
    elif stage == "build":
        assert json.loads((DATA / "output.json").read_text())["sum"] == 6
    elif stage == "inspect":
        assert (DATA / "inspection.txt").read_text() == "verified total=6\\n"

if __name__ == "__main__":
    kind, stage = sys.argv[1:3]
    (run if kind == "run" else check)(stage)
'''


def template(name, projectname):
    # The generic content pipeline is deliberately workflow-neutral.
    goals = [
        ("PREPARE", "Prepare input artifact", [], "prepare", "build/input.json"),
        ("BUILD", "Transform input into output", ["PREPARE"], "build", "build/output.json"),
        ("INSPECT", "Verify and document output", ["BUILD"], "inspect", "build/inspection.txt"),
    ]
    tasks = []
    for k, goal, deps, stage, output in goals:
        tasks.append({"id": k, "phase": "P1" if k == "PREPARE" else "P2", "goal": goal,
                      "needs": deps, "scope": "local", "executor": {"type": "command", "argv": [sys.executable, "steps/workflow.py", "run", stage]},
                      "checks": [{"argv": [sys.executable, "steps/workflow.py", "check", stage]}], "outputs": [output]})
    tasks.append({"id": "APPROVE", "phase": "P3", "goal": "Obtain owner authorization before any external release", "needs": ["INSPECT"], "scope": "approval", "executor": {"type": "manual"}})
    return {"schema_version": 1, "project": projectname, "description": "Starter workflow; adapt the goals, scripts and checks to your actual process", "tasks": tasks}


def setup(args):
    project = Path(args.path).expanduser().resolve()
    project.mkdir(parents=True, exist_ok=True)
    road = project / "roadmap.json"
    if road.exists():
        raise RoadmapError(f"Refusing to overwrite {road}")
    steps = project / "steps" / "workflow.py"
    if steps.exists():
        raise RoadmapError(f"Refusing to overwrite {steps}")
    steps.parent.mkdir(parents=True, exist_ok=True)
    steps.write_text(sample_script(), encoding="utf-8")
    atomic_json(road, template("pipeline", args.name or project.name))
    (project / ".gitignore").write_text(".roadmap/\nbuild/\n__pycache__/\n", encoding="utf-8") if not (project / ".gitignore").exists() else None
    print(f"Initialized {project}\nEdit {road} and {steps} to define your workflow.")


def state_for(args):
    p, data, index = load(args.project)
    return p, data, index, read_state(p, data)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="roadmapctl", description="Portable, evidence-gated roadmap runner")
    parser.add_argument("--project", default=".", help="Project directory containing roadmap.json")
    sub = parser.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init", help="Create a new, fully runnable example roadmap")
    init.add_argument("path")
    init.add_argument("--name", default=None)
    for name in ("validate", "status", "next", "run", "resume", "verify", "blockers", "render", "refresh", "drift", "migrate"):
        sp = sub.add_parser(name)
        if name in {"run", "resume"}:
            sp.add_argument("--max-tasks", type=int, default=100, help="Limit tasks per run")
            sp.add_argument("--parallel", type=int, default=1, help="Max concurrent non-conflicting tasks (v2 lanes)")
    retry = sub.add_parser("retry", help="Explicitly authorize a retry of failed/interrupted task")
    retry.add_argument("task")
    retry.add_argument("--acknowledge-side-effects", action="store_true", required=True)
    attest = sub.add_parser("attest", help="Attest a manual approval gate using a real evidence file")
    attest.add_argument("task")
    attest.add_argument("--evidence", required=True)
    for sp_name in ("migrate",):
        # migrate created above in the loop; add its flag here
        pass
    mig = None
    for sp in sub.choices.values() if hasattr(sub, "choices") else []:
        pass

    for sp in getattr(sub, "_name_parser_map", getattr(sub, "choices", {})).values():
        if getattr(sp, "prog", "").endswith("migrate"):
            sp.add_argument("--rollback", action="store_true", help="Restore the pre-migration roadmap backup")
    args = parser.parse_args(argv)
    try:
        if args.action == "init":
            setup(args)
            return 0
        p, data, index, st = state_for(args)
        if args.action == "validate":
            print("VALID schema/DAG:", len(data["tasks"]), "tasks")
            return 0
        if args.action in {"status", "next", "blockers"}:
            if args.action == "status":
                for t in data["tasks"]:
                    print(f"{st['tasks'][t['id']]['status'].upper():12s} {t['id']:20s} [{t['phase']}] {t['goal']}")
            if args.action == "next":
                for t in candidates(data, st):
                    print(t["id"], "—", t["goal"])
            if args.action == "blockers":
                for k, v in st["tasks"].items():
                    if v["status"] in {"blocked", "interrupted", "failed"}:
                        print(k, v["status"], v.get("reason", ""))
            return 0
        if args.action == "verify":
            errs = verify_existing(p, data, st)
            if errs:
                for e in errs:
                    print("FAIL", e)
                return 2
            print("PASS: all recorded completions have consistent contracts, dependency receipts and output hashes")
            return 0
        if args.action == "render":
            print(report(p, data, st))
            return 0
        if args.action == "drift":
            """Detect contract/artifact drift between roadmap, receipts and state."""
            drifted = []
            idx = {t["id"]: t for t in data["tasks"]}
            for k, v in st["tasks"].items():
                if v["status"] != "passed":
                    continue
                rf = p / ".roadmap" / "receipts" / f"{k}.json"
                if not rf.exists():
                    drifted.append(f"{k}: PASSED but receipt missing")
                    continue
                rec = json.loads(rf.read_text(encoding="utf-8"))
                want = rec.get("contract_sha256")
                valid = {digest(canon_bytes(idx[k])), contract_digest(idx[k])}
                valid.update(idx[k].get("prior_contract_sha256") or [])
                if want not in valid:
                    drifted.append(f"{k}: contract changed after PASS")
                for rel, hv in (rec.get("outputs") or {}).items():
                    f = p / rel
                    if not f.is_file() or file_digest(f) != hv:
                        drifted.append(f"{k}: artifact drifted {rel}")
            for k in drifted:
                print("DRIFT", k)
            print("drift-free" if not drifted else f"{len(drifted)} drifted task(s)")
            return 0 if not drifted else 3
        if args.action == "migrate":
            road = p / "roadmap.json"
            backup = p / ".roadmap" / "roadmap.v1.bak"
            if args.rollback:
                if not backup.is_file():
                    raise RoadmapError("No migration backup to roll back to")
                _shutil.copy2(backup, road)
                miglog = p / ".roadmap" / "migrations"
                (miglog / "rollback.log").write_text(now() + " rollback applied\n", encoding="utf-8")
                print("Rolled back to pre-migration roadmap")
                return 0
            if data["schema_version"] != 1:
                raise RoadmapError("Nothing to migrate (schema_version is not 1)")
            backup.parent.mkdir(parents=True, exist_ok=True)
            _shutil.copy2(road, backup)
            mapping = {}
            new_data = dict(data, schema_version=2)
            for t in new_data["tasks"]:
                mapping[t["id"]] = {
                    "legacy_sha256": digest(canon_bytes(t)),
                    "core_sha256": contract_digest(t),
                }
            atomic_json(road, new_data)
            (p / ".roadmap" / "migrations").mkdir(parents=True, exist_ok=True)
            atomic_json(p / ".roadmap" / "migrations" / f"v1-to-v2-{now().replace(':', '')}.json",
                        {"from": 1, "to": 2, "at": now(), "tasks": mapping})
            print(f"Migrated roadmap to schema_version 2 ({len(mapping)} tasks; backup at .roadmap/roadmap.v1.bak)")
            errs = verify_existing(p, new_data, st)
            if errs:
                print("WARNING: receipts invalid after migration:", *errs, sep="\n  ")
                return 3
            print("All existing receipts remain valid")
            return 0
        with lock(p):
            p, data, index, st = state_for(args)
            n = recover_interrupted(p, st)
            if n:
                print(f"Recovered {n} interrupted tasks; explicit inspected retry required")
            errs = verify_existing(p, data, st)
            if errs:
                raise RoadmapError("Refusing to proceed: accepted evidence invalid:\n" + "\n".join(errs))
            if args.action == "refresh":
                if not data.get("observer"):
                    raise RoadmapError("No observer configured in roadmap.json")
                logdir = p / ".roadmap" / "logs"
                logdir.mkdir(parents=True, exist_ok=True)
                rc = run_argv(p, data["observer"], 120, logdir / "refresh.log")
                if rc:
                    raise RoadmapError(f"Observer failed with exit {rc}; inspect .roadmap/logs/refresh.log")
                print("Observation refreshed; task pass/approval states unchanged")
                print(report(p, data, st))
                return 0
            if args.action in {"run", "resume"}:
                if args.max_tasks < 1:
                    raise RoadmapError("max-tasks must be positive")
                workers = max(1, args.parallel)
                count = 0
                while count < args.max_tasks:
                    ready = candidates(data, st)
                    if not ready:
                        break
                    wave, deferred = non_conflicting_wave(ready)
                    batch = wave[:workers]
                    if not batch:
                        break
                    if len(batch) == 1:
                        task = batch[0]
                        print("EXECUTING", task["id"], "—", task["goal"], flush=True)
                        ok = execute_one(p, data, st, task)
                        print("PASS" if ok else "HELD", task["id"], flush=True)
                        count += 1
                    else:
                        print("WAVE", [t["id"] for t in batch], flush=True)
                        with ThreadPoolExecutor(max_workers=len(batch)) as pool:
                            results = list(pool.map(lambda t: execute_one(p, data, st, t), batch))
                        for t, ok in zip(batch, results):
                            print(("PASS" if ok else "HELD"), t["id"], flush=True)
                            count += 1
                    if ok:
                        # Later task commands may modify previously accepted outputs;
                        # stop before executing a successor if any receipt has gone stale.
                        errs = verify_existing(p, data, st)
                        if errs:
                            raise RoadmapError("Post-task receipt validation failed:\n" + "\n".join(errs))
                print("Cycle complete; tasks processed:", count)
                print(report(p, data, st))
                return 0 if not any(v["status"] in {"failed", "interrupted"} for v in st["tasks"].values()) else 3
            if args.action == "retry":
                if not args.acknowledge_side_effects:
                    raise RoadmapError("Explicit --acknowledge-side-effects required")
                if args.task not in index:
                    raise RoadmapError("Unknown task")
                state = st["tasks"][args.task]
                if state["status"] not in {"failed", "interrupted"}:
                    raise RoadmapError("Retry allowed only for failed/interrupted tasks")
                state["status"] = "pending"
                state.pop("reason", None)
                write_state(p, st)
                append_event(p, {"type": "explicit_retry", "task": args.task})
                print("Eligible to retry after dependency checks:", args.task)
                return 0
            if args.action == "attest":
                if args.task not in index:
                    raise RoadmapError("Unknown task")
                task = index[args.task]
                if task["executor"]["type"] != "manual" or task.get("scope") != "approval":
                    raise RoadmapError("Attestation only available for manual approval gates")
                if st["tasks"][args.task]["status"] == "passed":
                    raise RoadmapError("Manual gate is already passed; cannot silently replace its evidence")
                if not all(st["tasks"][x]["status"] == "passed" for x in task.get("needs", [])):
                    raise RoadmapError("Manual gate prerequisites have not passed")
                ev = Path(args.evidence).resolve()
                if not ev.is_file():
                    raise RoadmapError("Evidence file not found")
                evidence_ref = str(ev)
                rec = {"task": args.task, "status": "passed", "at": now(), "contract_sha256": digest(canon_bytes(task)), "outputs": {}, "attested_evidence": {"path": evidence_ref, "sha256": file_digest(ev)}, "assurance": "operator-attested"}
                atomic_json(p / ".roadmap" / "receipts" / (args.task + ".json"), rec)
                st["tasks"][args.task].update(status="passed", finished=now(), receipt=f".roadmap/receipts/{args.task}.json")
                st["tasks"][args.task].pop("reason", None)
                write_state(p, st)
                append_event(p, {"type": "attested", "task": args.task, "evidence": evidence_ref})
                report(p, data, st)
                print("Attested manual gate (local operator assertion):", args.task)
                return 0
    except (RoadmapError, ValueError, OSError) as e:
        print("ERROR:", e, file=sys.stderr)
        return 2
    return 0
