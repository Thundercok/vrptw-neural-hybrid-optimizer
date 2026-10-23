from __future__ import annotations

import copy
import importlib.util
import json
import signal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def api():
    spec = importlib.util.spec_from_file_location("sweep_executor", ROOT / "scripts/run_sweep.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def toy(tmp_path, monkeypatch):
    m = api()
    jobs = []
    for i in range(3):
        jobs.append(
            {
                "run": f"job{i}",
                "instance": "A",
                "input_key": "a.txt",
                "case_id": "ALNS-Base",
                "ablation": "alns",
                "seed": 42 + i,
                "time_limit": 10,
                "cutoff_sec": 10,
                "customers": 100,
                "geometry_sha256": "g",
                "binding_sha256": "fixture",
                "uses": ["primary"],
                "command": ["fixture", str(i)],
            }
        )
    plan = {"jobs": jobs, "source_sha256": "source", "manifest_sha256": "manifest", "inputs": {}, "backends": {}}
    calls = []
    monkeypatch.setattr(m, "load", lambda output: copy.deepcopy(plan))
    monkeypatch.setattr(m, "check", lambda *a, **kw: None)

    def execute(output, plan, job):
        calls.append(job["run"])
        directory = output / job["run"]
        (directory / "result.json").write_text(json.dumps({"fixture": job["run"]}))
        (directory / "cli_process.json").write_text(json.dumps({"returncode": 0}))
        return {"returncode": 0, "child_wall_sec": 10.1, "child_cpu_sec": 9.9}

    def audit(output, plan, job, receipt):
        raw = json.loads((output / job["run"] / "result.json").read_text())
        assert raw["fixture"] == job["run"]
        return {
            "run": job["run"],
            "instance": job["instance"],
            "case_id": job["case_id"],
            "seed": job["seed"],
            "cutoff_sec": job["time_limit"],
            "customers": 100,
            "geometry_sha256": "g",
            "integrity_ok": True,
            "available": True,
            "return_ok": True,
            "binding_ok": True,
            "nv": 1,
            "td": 100.0,
            "error_kind": None,
            "result_sha256": m.sha256(output / job["run"] / "result.json"),
        }

    return m, tmp_path, plan, calls, execute, audit


def test_resume_never_reexecutes_committed_jobs_and_rebuilds_csv(toy):
    m, out, plan, calls, execute, audit = toy
    assert m.run(out, max_jobs=1, execute=execute, auditor=audit)["completed_jobs"] == 1
    (out / "records.csv").write_text("corrupted derived view")
    assert m.run(out, execute=execute, auditor=audit)["completed_jobs"] == 3
    assert calls == ["job0", "job1", "job2"]
    assert "corrupted" not in (out / "records.csv").read_text()
    m.run(out, execute=execute, auditor=audit)
    assert calls == ["job0", "job1", "job2"]


def test_known_algorithm_failure_is_committed_once(toy):
    m, out, plan, calls, execute, audit = toy

    def failure(*args):
        result = audit(*args)
        result.update(available=False, binding_ok=False, nv=None, td=None, error_kind="NativeNoSolutionError")
        return result

    m.run(out, max_jobs=1, execute=execute, auditor=failure)
    m.run(out, max_jobs=1, execute=execute, auditor=failure)
    assert calls == ["job0", "job1"]
    assert json.loads((out / "job0/completed.json").read_text())["record"]["available"] is False


def test_ambiguous_intent_blocks_resume_without_spawning(toy):
    m, out, plan, calls, execute, audit = toy
    directory = out / "job0"
    directory.mkdir()
    (directory / "started.json").write_text("{}")
    with pytest.raises(ValueError, match="incomplete|ambiguous|intent"):
        m.run(out, execute=execute, auditor=audit)
    assert calls == []


def test_out_of_order_existing_artifact_blocks_before_dispatch(toy):
    m, out, plan, calls, execute, audit = toy
    (out / "job2").mkdir()
    with pytest.raises(ValueError):
        m.run(out, execute=execute, auditor=audit)
    assert calls == []


def test_receipt_before_crash_is_finalized_without_a_second_execution(toy, monkeypatch):
    m, out, plan, calls, execute, audit = toy
    original = m.commit

    def crash(*args, **kwargs):
        raise RuntimeError("crash before commit")

    monkeypatch.setattr(m, "commit", crash)
    with pytest.raises(RuntimeError):
        m.run(out, max_jobs=1, execute=execute, auditor=audit)
    assert (out / "job0/execution.json").exists() and calls == ["job0"]
    (out / "job0/completed.crash.pending").write_text("{")
    monkeypatch.setattr(m, "commit", original)
    m.run(out, max_jobs=1, execute=execute, auditor=audit)
    assert calls == ["job0", "job1"] and (out / "job0/completed.crash.pending").read_text() == "{"


@pytest.mark.parametrize("filename", ["result.json", "execution.json", "completed.json", "evidence.json"])
def test_committed_evidence_tamper_stops_before_next_dispatch(toy, filename):
    m, out, plan, calls, execute, audit = toy
    m.run(out, max_jobs=1, execute=execute, auditor=audit)
    p = out / "job0" / filename
    p.write_text(p.read_text() + " ")
    with pytest.raises(ValueError):
        m.run(out, execute=execute, auditor=audit)
    assert calls == ["job0"]


def test_protocol_failure_is_retained_and_stops_subsequent_jobs(toy):
    m, out, plan, calls, execute, audit = toy

    def invalid(*args):
        record = audit(*args)
        record["integrity_ok"] = False
        return record

    with pytest.raises(ValueError, match="protocol"):
        m.run(out, execute=execute, auditor=invalid)
    assert calls == ["job0"] and (out / "job0/completed.json").exists()
    with pytest.raises(ValueError):
        m.run(out, execute=execute, auditor=invalid)
    assert calls == ["job0"]


def test_exclusive_lock_prevents_a_second_runner(toy):
    m, out, plan, calls, execute, audit = toy
    with m.exclusive_lock(out):
        with pytest.raises(ValueError, match="lock|runner"):
            m.run(out, execute=execute, auditor=audit)
    assert calls == []


def test_sigint_finishes_current_job_then_stops(toy):
    m, out, plan, calls, execute, audit = toy
    previous = signal.getsignal(signal.SIGINT)

    def stop(*args):
        receipt = execute(*args)
        signal.raise_signal(signal.SIGINT)
        return receipt

    status = m.run(out, execute=stop, auditor=audit)
    assert status["status"] == "stopped_after_job" and calls == ["job0"]
    assert (out / "job0/completed.json").exists() and signal.getsignal(signal.SIGINT) == previous


def test_prepare_refuses_existing_output_before_mutation(tmp_path):
    m = api()
    marker = tmp_path / "keep"
    marker.write_text("old")
    with pytest.raises(FileExistsError):
        m.prepare(tmp_path)
    assert marker.read_text() == "old" and list(tmp_path.iterdir()) == [marker]


def test_full_preparation_binds_exact_schedule_and_no_solver_runs(tmp_path, monkeypatch):
    m = api()
    monkeypatch.setattr(m, "run", lambda *a, **kw: pytest.fail("prepare dispatched jobs"))
    for cls in (
        m.cli.native_cli.ALNSSolver,
        m.cli.native_cli.PyVRPSolver,
        m.cli.native_cli.NeuroLKHSolver,
        m.common.factor.AblationHybridSolver,
    ):
        monkeypatch.setattr(cls, "solve", lambda *a, **kw: pytest.fail("prepare called a solver"))
    output = tmp_path / "prepared"
    plan = m.prepare(output)
    assert len(plan["jobs"]) == 8620 and sum(j["time_limit"] for j in plan["jobs"]) == 2365600
    assert len({(j["instance"], j["case_id"], j["seed"], j["time_limit"]) for j in plan["jobs"]}) == 8620
    assert sum(j["uses"] == ["primary", "ablation"] for j in plan["jobs"]) == 180
    assert all(j["command"] and j["binding_sha256"] for j in plan["jobs"])
    assert not any((output / j["run"]).exists() for j in plan["jobs"])
    assert plan["policy"]["automatic_launch"] is False
    m.check(output, plan)
    modified = copy.deepcopy(plan)
    modified["jobs"][0]["seed"] = 99
    with pytest.raises(ValueError):
        m.check(output, modified)
    with pytest.raises(ValueError):
        m.check(output, plan, modified["jobs"][0])
    altered = copy.deepcopy(plan["jobs"][0])
    altered["command"] = ["unexpected-executable"]
    altered["declaration_sha256"] = m.hashlib.sha256(
        m.encode({k: v for k, v in altered.items() if k != "declaration_sha256"})
    ).hexdigest()
    with pytest.raises(ValueError):
        m.check(output, plan, altered)
    with monkeypatch.context() as patch:
        patch.setattr(m, "hardware", lambda: {"changed": True})
        with pytest.raises(ValueError):
            m.check(output, plan)
    with monkeypatch.context() as patch:
        patch.setattr(m.cli, "backend_identity", lambda *a: {"changed": True})
        with pytest.raises(ValueError):
            m.check(output, plan)
    for filename in ("gnn_checkpoint.pt", "training_metadata.json", next(iter(plan["inputs"].values()))["snapshot"]):
        path = output / filename
        data = path.read_bytes()
        path.write_bytes(data + b" ")
        with pytest.raises(ValueError):
            m.check(output, plan)
        path.write_bytes(data)
    binding = next((output / "bindings").glob("*.json"))
    binding.write_text(binding.read_text() + " ")
    with pytest.raises(ValueError):
        m.check(output, plan)


def test_source_drift_after_dispatch_remains_blocked_on_resume(toy, monkeypatch):
    m, out, plan, calls, execute, audit = toy

    def check(*args):
        if calls:
            raise ValueError("source drift")

    monkeypatch.setattr(m, "check", check)
    with pytest.raises(ValueError, match="source drift"):
        m.run(out, execute=execute, auditor=audit)
    assert (out / "job0/integrity_error.json").exists() and calls == ["job0"]
    monkeypatch.setattr(m, "check", lambda *args: None)
    with pytest.raises(ValueError, match="drift recorded"):
        m.run(out, execute=execute, auditor=audit)
    assert calls == ["job0"]


@pytest.mark.parametrize("watchdog", [False, True])
def test_owned_cli_session_and_watchdog_signal_only_owned_process(toy, monkeypatch, watchdog):
    m, out, plan, calls, execute, audit = toy
    job = plan["jobs"][0]
    (out / job["run"]).mkdir()
    events = []

    class Process:
        pid = 12345
        returncode = None

        def wait(self, timeout):
            events.append(("wait", timeout))
            if watchdog and self.returncode is None:
                self.returncode = 130
                raise m.subprocess.TimeoutExpired("fixture", timeout)
            self.returncode = 130 if watchdog else 0
            return self.returncode

        def send_signal(self, sig):
            events.append(("signal", sig))

    def launch(command, **kwargs):
        assert command == job["command"] and kwargs["start_new_session"] is True
        assert kwargs["cwd"] == ROOT
        assert all(kwargs["env"][key] == "1" for key in m.common.native.THREADS)
        return Process()

    monkeypatch.setattr(m.subprocess, "Popen", launch)
    if watchdog:
        with pytest.raises(m.subprocess.TimeoutExpired):
            m.execute_job(out, plan, job)
        assert events == [("wait", 190), ("signal", signal.SIGINT), ("wait", 10)]
    else:
        receipt = m.execute_job(out, plan, job)
        assert receipt["returncode"] == 0 and receipt["child_wall_sec"] >= 0 and receipt["child_cpu_sec"] >= 0
        assert events == [("wait", 190)]
    process = json.loads((out / job["run"] / "cli_process.json").read_text())
    assert process["watchdog_fired"] is watchdog and process["returncode"] == (130 if watchdog else 0)


@pytest.mark.parametrize(
    "case",
    [
        "success",
        "return_late",
        "no_solution",
        "binding_drift",
        "missing_checkpoint_request_drift",
        "unknown_error",
        "cleanup_failure",
        "wrong_returncode",
    ],
)
def test_real_audit_classification_keeps_failure_and_integrity_separate(toy, monkeypatch, case):
    m, out, plan, calls, execute, audit = toy
    job = plan["jobs"][0]
    (out / job["run"]).mkdir()
    (out / "bindings").mkdir()
    binding = {"requested_config": {}, "effective_config": {}, "module_configs": {}}
    digest = m.hashlib.sha256(m.encode(binding)).hexdigest()
    job["binding_sha256"] = digest
    plan["bindings"] = {digest: f"bindings/{digest}.json"}
    m.publish(out / plan["bindings"][digest], binding)
    gates = dict.fromkeys(
        ("provenance_ok", "cold_ok", "clock_ok", "cleanup_ok", "binding_ok", "certification_ok", "budget_ok"), True
    )
    raw = {
        "feasible": True,
        "nv": 1,
        "td": 100.0,
        "routes": [[1]],
        "worker_checkpoint": {},
        "error": None,
        "requested_config": {},
    }
    (out / job["run"] / "session").mkdir()
    m.publish(out / job["run"] / "session/request.json", {"identity": {"requested_config": {}}})
    code = 0
    if case in ("no_solution", "unknown_error", "missing_checkpoint_request_drift"):
        raw.update(
            feasible=False,
            nv=None,
            td=None,
            routes=None,
            worker_checkpoint=None,
            error=("UnexpectedError" if case == "unknown_error" else "NativeNoSolutionError") + ": no incumbent",
        )
        gates.update(binding_ok=False, certification_ok=False)
        code = 1
    if case == "missing_checkpoint_request_drift":
        raw["requested_config"] = {"seed": 99}
    if case == "return_late":
        gates["budget_ok"] = False
    if case == "binding_drift":
        gates["binding_ok"] = False
    if case == "cleanup_failure":
        gates["cleanup_ok"] = False
    if case == "wrong_returncode":
        code = 1
    m.publish(out / job["run"] / "result.json", raw)
    monkeypatch.setattr(m.common, "audit", lambda *args: (gates, []))
    result = m.audit_job(out, plan, job, {"returncode": code, "child_wall_sec": 11.0, "child_cpu_sec": 10.0})
    assert result["integrity_ok"] is (case in ("success", "return_late", "no_solution"))
    assert result["available"] is (case not in ("no_solution", "unknown_error", "missing_checkpoint_request_drift"))
    assert result["return_ok"] is (case != "return_late")
    if case == "no_solution":
        assert result["binding_ok"] is False and result["nv"] is None
