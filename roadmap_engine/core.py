"""Small, conservative roadmap executor using only the Python standard library.

The roadmap JSON is the authoritative *desired* plan; state and receipts are
verified execution evidence. No model completion claims, privileged external
operations, or production actions are inferred from an exit code.
"""
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import uuid

ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,79}$")
PHASE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,79}$")
SUCCESS = "passed"
STATUSES = {"pending", "running", "passed", "failed", "interrupted", "blocked"}


class RoadmapError(Exception):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def canon_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(json.dumps(obj, indent=2, sort_keys=True).encode("utf-8") + b"\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def assert_safe_path(project, rel):
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        raise RoadmapError("Expected a project-relative path: " + repr(rel))
    resolved = (project / rel).resolve()
    if not resolved.is_relative_to(project.resolve()):
        raise RoadmapError("Path escapes project: " + rel)
    return resolved


def validate_contract(data, project):
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise RoadmapError("roadmap.json schema_version must equal 1")
    if not isinstance(data.get("project"), str) or not data["project"].strip():
        raise RoadmapError("Missing project name")
    tasks = data.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise RoadmapError("tasks must be a nonempty array")
    seen = set()
    for t in tasks:
        if not isinstance(t, dict) or not ID.fullmatch(str(t.get("id", ""))):
            raise RoadmapError("Task requires an ID (letters/numbers/_/-)")
        k = t["id"]
        if k in seen:
            raise RoadmapError("Duplicate task " + k)
        seen.add(k)
        if not isinstance(t.get("goal"), str) or not t["goal"].strip():
            raise RoadmapError(f"{k}: goal required")
        if not PHASE.fullmatch(str(t.get("phase", ""))):
            raise RoadmapError(f"{k}: phase required")
        if not isinstance(t.get("needs", []), list) or any(not isinstance(x, str) for x in t.get("needs", [])):
            raise RoadmapError(f"{k}: needs must be a list of task IDs")
        if len(set(t.get("needs", []))) != len(t.get("needs", [])):
            raise RoadmapError(f"{k}: repeated dependency")
        if t.get("scope", "local") not in {"local", "approval"}:
            raise RoadmapError(f"{k}: scope must be local or approval")
        ex = t.get("executor")
        if not isinstance(ex, dict) or ex.get("type") not in {"command", "manual"}:
            raise RoadmapError(f"{k}: executor.type must be command or manual")
        if ex["type"] == "command":
            if t.get("scope", "local") != "local":
                raise RoadmapError(f"{k}: approval actions may not run automatically")
            check_argv(ex.get("argv"), k)
            check_cwd(project, ex.get("cwd", "."), k)
            checks = t.get("checks")
            if not isinstance(checks, list) or not checks:
                raise RoadmapError(f"{k}: at least one independent check command required")
            for c in checks:
                if not isinstance(c, dict):
                    raise RoadmapError(f"{k}: check must be an object")
                check_argv(c.get("argv"), k)
                check_cwd(project, c.get("cwd", "."), k)
            if not isinstance(t.get("outputs"), list) or not t["outputs"]:
                raise RoadmapError(f"{k}: at least one output artifact required")
            for path in t["outputs"]:
                assert_safe_path(project, path)
        else:
            if t.get("scope") != "approval":
                raise RoadmapError(f"{k}: manual tasks must have scope=approval")
        if "timeout_seconds" in t:
            if not isinstance(t["timeout_seconds"], (int, float)) or t["timeout_seconds"] <= 0 or t["timeout_seconds"] > 86400:
                raise RoadmapError(f"{k}: timeout_seconds must be 1..86400")
    if "observer" in data:
        obs = data["observer"]
        if not isinstance(obs, dict) or obs.get("type") != "command":
            raise RoadmapError("observer must be a command configuration")
        check_argv(obs.get("argv"), "observer")
        check_cwd(project, obs.get("cwd", "."), "observer")
    index = {t["id"]: t for t in tasks}
    visit = {}
    def walk(k):
        if visit.get(k) == 1:
            raise RoadmapError("Dependency cycle includes " + k)
        if visit.get(k) == 2:
            return
        visit[k] = 1
        for p in index[k].get("needs", []):
            if p not in index:
                raise RoadmapError(f"{k}: unknown prerequisite {p}")
            walk(p)
        visit[k] = 2
    for k in index:
        walk(k)
    return index


def check_argv(argv, k):
    if not isinstance(argv, list) or not argv or any(not isinstance(a, str) or not a for a in argv):
        raise RoadmapError(f"{k}: argv must be nonempty string array (never shell command string)")


def check_cwd(project, cwd, k):
    p = assert_safe_path(project, cwd)
    if not p.is_dir():
        raise RoadmapError(f"{k}: cwd does not exist: {cwd}")
    return p


def load(project):
    project = Path(project).resolve()
    p = project / "roadmap.json"
    if not p.is_file():
        raise RoadmapError(f"No roadmap.json at {p} (run `init`)")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        raise RoadmapError("Cannot read roadmap: " + str(e)) from e
    index = validate_contract(data, project)
    return project, data, index


def blank_state(data):
    return {"format": 1, "project": data["project"], "tasks": {t["id"]: {"status": "pending", "attempt": 0} for t in data["tasks"]}, "last_update": now()}


def read_state(project, data):
    f = project / ".roadmap" / "state.json"
    if f.exists():
        st = json.loads(f.read_text(encoding="utf-8"))
        if st.get("project") != data["project"] or st.get("format") != 1:
            raise RoadmapError("State doesn't match project; manual migration required")
        for t in data["tasks"]:
            if t["id"] not in st["tasks"]:
                st["tasks"][t["id"]] = {"status": "pending", "attempt": 0}
        removed = set(st["tasks"]) - {t["id"] for t in data["tasks"]}
        if removed:
            raise RoadmapError("Cannot delete task IDs from a started roadmap without state migration: " + ", ".join(sorted(removed)))
        for entry in st["tasks"].values():
            if entry.get("status") not in STATUSES:
                raise RoadmapError("Invalid persisted task state")
        return st
    return blank_state(data)


def write_state(project, st):
    st["last_update"] = now()
    atomic_json(project / ".roadmap" / "state.json", st)


def append_event(project, payload):
    path = project / ".roadmap" / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"at": now(), **payload}
    with open(path, "ab") as f:
        f.write(canon_bytes(payload) + b"\n")
        f.flush()
        os.fsync(f.fileno())


@contextlib.contextmanager
def lock(project):
    """Cross-process advisory lock; releases on process crash (Unix incl. macOS)."""
    import fcntl
    p = project / ".roadmap" / "runner.lock"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a+") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise RoadmapError("Another controller holds the project lock") from e
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def candidates(data, st):
    tasks = data["tasks"]
    return [t for t in tasks if st["tasks"][t["id"]]["status"] == "pending" and all(st["tasks"][p]["status"] == SUCCESS for p in t.get("needs", []))]


def git_sha(project):
    p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project, capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


def run_argv(project, cfg, timeout, log):
    p = check_cwd(project, cfg.get("cwd", "."), "runtime")
    with open(log, "ab") as out:
        out.write(("\n=== " + now() + " " + repr(cfg["argv"]) + " ===\n").encode())
        out.flush()
        try:
            result = subprocess.run(cfg["argv"], cwd=p, stdout=out, stderr=subprocess.STDOUT, timeout=timeout, shell=False)
            return result.returncode
        except subprocess.TimeoutExpired:
            out.write(b"\nTIMEOUT\n")
            return 124
        except FileNotFoundError as e:
            out.write((str(e) + "\n").encode())
            return 127


def verify_existing(project, data, st):
    """Check all passed receipt references and stored output hashes; no commands run."""
    errors = []
    idx = {t["id"]: t for t in data["tasks"]}
    for k, s in st["tasks"].items():
        if s["status"] != SUCCESS:
            continue
        for dep in idx[k].get("needs", []):
            if st["tasks"][dep]["status"] != SUCCESS:
                errors.append(f"{k}: passed without dependency {dep}")
        rf = project / ".roadmap" / "receipts" / (k + ".json")
        if not rf.exists():
            errors.append(f"{k}: receipt missing")
            continue
        try:
            rec = json.loads(rf.read_text(encoding="utf-8"))
            if rec.get("task") != k or rec.get("status") != "passed":
                errors.append(f"{k}: receipt identity/status invalid")
            if rec.get("contract_sha256") != digest(canon_bytes(idx[k])):
                errors.append(f"{k}: task contract changed after PASS (requires controlled amendment)")
            for path, hash_value in rec.get("outputs", {}).items():
                artifact = assert_safe_path(project, path)
                if not artifact.is_file() or file_digest(artifact) != hash_value:
                    errors.append(f"{k}: evidence artifact missing/changed: {path}")
            if idx[k]["executor"]["type"] == "command":
                if not rec.get("outputs"):
                    errors.append(f"{k}: empty output proof")
                if rec.get("executor_exit") != 0 or len(rec.get("checks", [])) != len(idx[k]["checks"]) or any(c.get("exit_code") != 0 for c in rec.get("checks", [])):
                    errors.append(f"{k}: failed/missing check recorded as PASS")
            else:
                evidence = rec.get("attested_evidence", {})
                if not evidence or not Path(evidence.get("path", "")).is_file() or file_digest(Path(evidence["path"])) != evidence.get("sha256"):
                    errors.append(f"{k}: manually attested evidence missing/modified")
        except (ValueError, OSError, RoadmapError) as e:
            errors.append(f"{k}: invalid receipt: {e}")
    return errors


def recover_interrupted(project, st):
    count = 0
    for k, s in st["tasks"].items():
        if s["status"] == "running":
            s["status"] = "interrupted"
            s["reason"] = "Uncertain prior side effects; operator must inspect and explicitly retry."
            append_event(project, {"type": "interrupted", "task": k})
            count += 1
    if count:
        write_state(project, st)
    return count


def execute_one(project, data, st, task):
    k = task["id"]
    s = st["tasks"][k]
    if task["executor"]["type"] == "manual":
        s["status"] = "blocked"
        s["reason"] = "OWNER_AUTHORIZATION_REQUIRED: complete externally, then attest with evidence"
        write_state(project, st)
        append_event(project, {"type": "manual_gate", "task": k})
        return False
    s.update(status="running", attempt=s.get("attempt", 0) + 1, started=now(), start_sha=git_sha(project))
    write_state(project, st)
    append_event(project, {"type": "start", "task": k, "attempt": s["attempt"]})
    logs = project / ".roadmap" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / f"{k}-{s['attempt']}.log"
    timeout = task.get("timeout_seconds", 600)
    rc = run_argv(project, task["executor"], timeout, log)
    checks = []
    if rc == 0:
        for n, check in enumerate(task["checks"], 1):
            c = run_argv(project, check, timeout, log)
            checks.append({"number": n, "exit_code": c})
            if c:
                rc = c
                break
    outputs = {}
    if rc == 0:
        for rel in task["outputs"]:
            p = assert_safe_path(project, rel)
            if not p.is_file():
                rc = 2
                with open(log, "ab") as o:
                    o.write(("Missing output artifact: " + rel + "\n").encode())
                break
            outputs[rel] = file_digest(p)
    if rc:
        s.update(status="failed", reason=f"Command/check/artifact validation failed (exit {rc}); inspect {log.relative_to(project)}", finished=now())
        write_state(project, st)
        append_event(project, {"type": "failed", "task": k, "exit_code": rc, "log": str(log.relative_to(project))})
        return False
    rec = {"task": k, "status": "passed", "attempt": s["attempt"], "at": now(), "contract_sha256": digest(canon_bytes(task)), "start_sha": s.get("start_sha"), "end_sha": git_sha(project), "executor_exit": 0, "checks": checks, "outputs": outputs, "log": str(log.relative_to(project)), "assurance": "local-command-and-checks"}
    atomic_json(project / ".roadmap" / "receipts" / (k + ".json"), rec)
    s.update(status="passed", finished=now(), receipt=f".roadmap/receipts/{k}.json", end_sha=rec["end_sha"])
    s.pop("reason", None)
    write_state(project, st)
    append_event(project, {"type": "passed", "task": k, "receipt": s["receipt"]})
    return True


def report(project, data, st):
    header = [f"# {data['project']} — Executable Roadmap", "", f"Generated: {now()}", "", "| Phase | Task | Status | Goal |", "|---|---|---|---|"]
    for task in data["tasks"]:
        s = st["tasks"][task["id"]]
        header.append("| " + " | ".join([task["phase"], task["id"], s["status"].upper(), task["goal"].replace("|", "\\|").replace("\n", " ")]) + " |")
    header += ["", "## Next eligible work", ""]
    ready = candidates(data, st)
    header += ["- " + t["id"] + ": " + t["goal"] for t in ready] if ready else ["No immediately eligible tasks."]
    header += ["", "## Held tasks", ""]
    header += ["- " + k + ": " + s.get("reason", s["status"]) for k, s in st["tasks"].items() if s["status"] in {"blocked", "failed", "interrupted"}] or ["None."]
    if data.get("observer") and (project / "tracking" / "OBSERVED_STATUS.md").is_file():
        header += ["", "---", "", "## External observations (read-only, not controller PASS)", ""]
        header += (project / "tracking" / "OBSERVED_STATUS.md").read_text(encoding="utf-8").splitlines()
    (project / "ROADMAP_STATUS.md").write_text("\n".join(header) + "\n", encoding="utf-8")
    return project / "ROADMAP_STATUS.md"
