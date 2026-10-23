"""Shared-clock external adapters and fail-closed descendant ownership."""

from __future__ import annotations

import importlib
import importlib.util
import json
import signal
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from vrptw import Config, Inst
from vrptw import neurolkh_baseline as neuro
from vrptw import pyvrp_baseline as pybaseline
from vrptw.native_certification import NativeIncumbent

ROOT = Path(__file__).resolve().parents[1]


def inst(n=3):
    data = np.zeros((n + 1, 7))
    data[:, 0], data[:, 1], data[:, 5] = range(n + 1), np.arange(n + 1) / 10, 100
    data[1:, 3] = 1
    return Inst({"name": "external_supervised_fixture", "capacity": 100, "data": data})


def load_script(name):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


@pytest.mark.parametrize("expired", [False, True])
def test_pyvrp_uses_parent_clock_and_publishes_only_before_cutoff(monkeypatch, expired):
    pytest.importorskip("pyvrp")
    solver = pybaseline.PyVRPSolver(inst(), Config(time_limit=10, seed=47))
    clock = SimpleNamespace(now=101.0 if expired else 100.2)
    monkeypatch.setattr(pybaseline, "time", SimpleNamespace(perf_counter=lambda: clock.now))
    packets = []
    tracker = NativeIncumbent(solver.inst, start=100, deadline=101, clock=lambda: clock.now, on_capture=packets.append)
    original = solver._build_model
    calls = []

    def build():
        assert not expired, "an already expired parent must not start model building"
        return original()

    def backend(data, **kwargs):
        calls.append(kwargs["seed"])
        clock.now = 100.3
        solution = SimpleNamespace(is_feasible=lambda: True, distance=lambda: 100, fixed_vehicle_cost=lambda: 1)
        kwargs["params"].ils.callbacks.on_start(SimpleNamespace(initial_solution=solution))
        clock.now = 102
        assert kwargs["stop"](0)
        kwargs["params"].ils.callbacks.on_best(solution)
        return SimpleNamespace(num_iterations=7, runtime=1.8, best=object())

    monkeypatch.setattr(solver, "_build_model", build)
    monkeypatch.setattr(solver, "_read_routes", lambda solution: [[1, 2, 3]])
    monkeypatch.setattr(solver.pyvrp, "solve", backend)
    if expired:
        with pytest.raises(RuntimeError, match="budget|certified"):
            solver.solve(seed=47, _certifier=tracker)
        assert calls == packets == []
    else:
        plan, _ = solver.solve(seed=47, _certifier=tracker)
        assert calls == [47] and len(packets) == 1 and plan.routes == [[1, 2, 3]]
        assert packets[0]["certificate"]["captured_sec"] == pytest.approx(0.3)
        assert solver.native_certification["status"] == "certified"
    assert solver._start == 100 and solver._deadline == 101


@pytest.mark.parametrize("expired", [False, True])
def test_neurolkh_inherits_clock_and_captures_original_tours(monkeypatch, tmp_path, expired):
    solver = neuro.NeuroLKHSolver.__new__(neuro.NeuroLKHSolver)
    solver.inst, solver.assets, solver.root = inst(25), {}, tmp_path
    solver.cfg = Config(time_limit=10, output_dir=str(tmp_path / "output"))
    solver.torch = SimpleNamespace(manual_seed=lambda seed: None)
    clock = SimpleNamespace(now=101 if expired else 100.2)
    monkeypatch.setattr(neuro, "time", SimpleNamespace(perf_counter=lambda: clock.now, sleep=lambda duration: None))
    packets = []

    def publish(payload):
        packets.append(payload)
        clock.now = 102

    tracker = NativeIncumbent(solver.inst, start=100, deadline=101, clock=lambda: clock.now, on_capture=publish)

    def infer():
        assert not expired, "an already expired parent must not start inference"
        edges = neuro.neural_features(solver.inst)[2]
        return edges, edges

    def popen(argv, *, cwd, **kwargs):
        n = 25 + 25
        (cwd / "incumbent.tour").write_text("TOUR_SECTION\n" + "\n".join(map(str, range(1, n + 1))) + "\n-1\nEOF\n")
        return SimpleNamespace(poll=lambda: None, returncode=-15)

    monkeypatch.setattr(solver, "_infer", infer)
    monkeypatch.setattr(neuro.subprocess, "Popen", popen)
    monkeypatch.setattr(solver, "_stop_process", lambda process: None)
    if expired:
        with pytest.raises(RuntimeError, match="budget|certified"):
            solver.solve(seed=47, _certifier=tracker)
        assert packets == []
    else:
        plan, _ = solver.solve(seed=47, _certifier=tracker)
        assert len(packets) == 1 and plan.routes == [list(range(1, 26))]
        assert packets[0]["certificate"]["captured_sec"] < 1
        assert solver.native_certification["status"] == "certified"
    assert solver._start == 100 and solver._deadline == 101


@pytest.mark.parametrize("case", ["pyvrp", "neurolkh"])
def test_supervised_cli_binds_external_assets_and_unknown_counts(tmp_path, monkeypatch, case):
    cli = load_script("benchmark_supervised")
    seen = []
    identity = {"adapter": case, "pin": "fixture"}
    monkeypatch.setattr(cli, "backend_identity", lambda name, cfg: identity)
    monkeypatch.setattr(cli.native_cli, "get_env_info", lambda: {"source_sha256": "source"})

    def supervise(instance, worker, request, session):
        seen.append(request)
        return None, {"runtime_sec": 10.01, "final_worker_counters": None, "error": "fixture"}

    monkeypatch.setattr(cli, "supervise", supervise)
    output = tmp_path / "result.json"
    args = [
        "supervised",
        "--instance",
        str(ROOT / "data/Solomon/c101.txt"),
        "--ablation",
        case,
        "--time-limit",
        "10",
        "--session-dir",
        str(tmp_path / "session"),
        "--output-json",
        str(output),
    ]
    if case == "neurolkh":
        args.extend(["--neurolkh-root", str(tmp_path)])
    monkeypatch.setattr(sys, "argv", args)
    assert cli.main() == 1
    assert seen[0]["identity"]["backend_identity"] == identity
    assert seen[0].get("descendant_cleanup_required", False) is (case == "neurolkh")
    raw = json.loads(output.read_text())
    assert raw["execution_mode"] == "external_supervisor_v1" and raw["iterations"] is None
    if case == "neurolkh":
        assert raw["requested_config"]["neurolkh_root"] == str(tmp_path.resolve())


@pytest.mark.parametrize("defect", ["missing_root", "native_root", "external_gnn"])
def test_external_cli_guards_never_launch_solver(tmp_path, monkeypatch, defect):
    cli = load_script("benchmark_supervised")
    monkeypatch.setattr(cli, "supervise", lambda *a, **kw: pytest.fail("negative CLI test launched supervision"))
    args = [
        "supervised",
        "--instance",
        str(ROOT / "data/Solomon/c101.txt"),
        "--ablation",
        "neurolkh" if defect == "missing_root" else "alns" if defect == "native_root" else "pyvrp",
        "--time-limit",
        "10",
        "--session-dir",
        str(tmp_path / "session"),
        "--output-json",
        str(tmp_path / "result.json"),
    ]
    if defect == "native_root":
        args.extend(["--neurolkh-root", str(tmp_path)])
    if defect == "external_gnn":
        args.extend(["--gnn-model", str(ROOT / "results/gnn_retraining_20261017/model_seed42/best.pt")])
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit) as caught:
        cli.main()
    assert caught.value.code == 2


@pytest.mark.parametrize("case", ["pyvrp", "neurolkh"])
@pytest.mark.parametrize("drift", [False, True])
def test_worker_checks_backend_pin_and_labels_unavailable_iterations(tmp_path, monkeypatch, case, drift):
    worker = load_script("native_supervisor_worker")
    session = tmp_path / "session"
    session.mkdir()
    instance = inst()
    _, cfg = worker.cli.get_solver_and_config(case, 10)
    cfg.output_dir = str(session / "work/archive")
    if case == "neurolkh":
        cfg.neurolkh_root = str(tmp_path)
    backend = {"adapter": case, "pin": "frozen"}
    identity = {
        "case": case,
        "seed": 42,
        "requested_config": asdict(cfg),
        "source_sha256": "source",
        "instance_sha256": "input",
        "gnn_model_sha256": None,
        "backend_identity": backend,
    }
    request = {
        "session_dir": str(session),
        "identity": identity,
        "instance": "input.txt",
        "gnn_model": None,
        "time_limit": 10,
        "token": "token",
        "neurolkh_root": str(tmp_path),
    }
    import time

    start = time.perf_counter()
    (session / "request.json").write_text(json.dumps(request))
    (session / "start.json").write_text(
        json.dumps({"token": "token", "start_perf": start, "deadline_perf": start + 10})
    )

    class Solver:
        def __init__(self, instance, cfg):
            self.cfg, self.search_iterations, self.diagnostics = cfg, 99, {"status": "searching"}

        def solve(self, *, seed, _certifier, **kwargs):
            from vrptw import Plan

            assert ("_process_owner" in kwargs) is (case == "neurolkh")
            assert _certifier.consider(Plan([[1, 2, 3]], instance), phase="fixture")
            self.native_certification = _certifier.diagnostics
            return _certifier.finish(), []

    monkeypatch.setattr(worker.cli, "get_solver_and_config", lambda *a, **kw: (Solver, cfg))
    monkeypatch.setattr(worker.cli, "load_solomon_instance", lambda *a: instance)
    monkeypatch.setattr(worker.cli, "sha256_file", lambda *a: "input")
    monkeypatch.setattr(worker.cli, "extract_instrumentation", lambda *a: {})
    environment = {
        "source_sha256": "source",
        "process_entry": {
            "cwd": str(session / "work"),
            "cwd_entries": [],
            "cache_dir": str(session / "cache"),
            "cache_entries": [],
        },
        "jit_environment": {},
        "numba": {},
    }
    monkeypatch.setattr(worker.cli, "get_env_info", lambda: environment)
    monkeypatch.setattr(worker, "backend_identity", lambda *a: {"pin": "wrong"} if drift else backend)
    monkeypatch.setattr(sys, "argv", ["worker", str(session / "request.json")])
    assert worker.main() == (1 if drift else 0)
    if drift:
        assert not (session / "ready.json").exists()
    else:
        packet = json.loads((session / "incumbent_000001.json").read_text())
        assert packet["checkpoint"]["iterations"] is None
        assert packet["checkpoint"]["adapter_diagnostics"] == {"status": "searching"}
        if case == "neurolkh":
            assert json.loads((session / "descendant_cleanup.json").read_text())["all_reaped"]


def test_pyvrp_version_drift_is_refused_before_launch(monkeypatch):
    import importlib.metadata

    cli = load_script("benchmark_supervised")
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "changed")
    with pytest.raises(ValueError, match="Expected PyVRP"):
        cli.backend_identity("pyvrp", Config())


def test_shared_audit_checks_the_declared_execution_mode():
    pilot = load_script("run_supervisor_pilot")
    output = ROOT / "results/supervisor_pilot_20261020"
    plan = json.loads((output / "plan.json").read_text())
    job = next(j for j in plan["jobs"] if j["ablation"] == "alns")
    raw = json.loads((output / job["run"] / "result.json").read_text())
    raw["execution_mode"] = "external_supervisor_v1"
    verdict, errors = pilot.audit(output, job, plan, raw, execution_mode="external_supervisor_v1")
    assert all(verdict.values()) and errors == []
    assert not pilot.audit(output, job, plan, raw)[0]["provenance_ok"]


def owner_api():
    return importlib.import_module("vrptw.supervised_process")


@pytest.mark.parametrize("mode", ["normal", "resist", "already_exited", "during_spawn"])
def test_owned_child_is_reaped_and_cleanup_is_bound(tmp_path, monkeypatch, mode):
    module = owner_api()
    identity = {"case": "fixture"}
    owner = module.BackendProcesses(tmp_path, identity=identity, token="token")
    previous = signal.getsignal(signal.SIGTERM)
    owner.install()
    original = module.subprocess.Popen
    child_code = "import time; time.sleep(60)"
    if mode == "resist":
        child_code = f"import signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path({str(tmp_path / 'ready')!r}).touch();time.sleep(60)"
    if mode == "already_exited":
        child_code = "pass"
    if mode == "during_spawn":

        def start(*args, **kwargs):
            process = original(*args, **kwargs)
            owner.request_stop()
            return process

        monkeypatch.setattr(module.subprocess, "Popen", start)
    process = None
    try:
        process = owner.spawn([sys.executable, "-c", child_code])
        if mode == "resist":
            import time

            deadline = time.perf_counter() + 5
            while not (tmp_path / "ready").exists() and time.perf_counter() < deadline:
                time.sleep(0.001)
            assert (tmp_path / "ready").exists()
        if mode == "already_exited":
            process.wait(timeout=5)
        owner.close()
        record = json.loads((tmp_path / "descendant_cleanup.json").read_text())
        assert record["token"] == "token" and record["identity"] == identity
        assert record["all_reaped"] and record["descendant_cpu_sec"] >= 0
        assert len(record["processes"]) == 1 and record["processes"][0]["reaped"]
        assert process.returncode is not None
        if mode == "resist":
            assert record["processes"][0]["kill_sent"]
        owner.request_stop()
        assert owner.spawn([sys.executable, "-c", "pass"]) is None
        assert signal.getsignal(signal.SIGTERM) == previous
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        signal.signal(signal.SIGTERM, previous)


@pytest.mark.parametrize("defect", [None, "missing", "token", "identity", "worker", "unreaped", "event_hash", "future"])
def test_parent_checks_descendant_evidence_without_promoting_routes(tmp_path, defect):
    module = owner_api()
    supervisor = importlib.import_module("vrptw.supervisor")
    owner = module.BackendProcesses(tmp_path, identity={"case": "fixture"}, token="token")
    process = owner.spawn([sys.executable, "-c", "pass"])
    process.wait(timeout=5)
    owner.close()
    path = tmp_path / "descendant_cleanup.json"
    record = json.loads(path.read_text())
    worker_pid = record["worker_pid"]
    if defect == "missing":
        path.unlink()
    elif defect:
        if defect == "token":
            record["token"] = "other"
        elif defect == "identity":
            record["identity"] = {}
        elif defect == "worker":
            record["worker_pid"] += 1
        elif defect == "unreaped":
            record["processes"][0]["reaped"] = False
        elif defect == "event_hash":
            record["processes"][0]["stop_sha256"] = "wrong"
        elif defect == "future":
            record["closed_perf"] += 1e6
        path.write_text(json.dumps(record))
    request = {"identity": {"case": "fixture"}, "token": "token"}
    if defect:
        with pytest.raises(supervisor.SupervisorProtocolError):
            supervisor.check_descendant_cleanup(tmp_path, request, worker_pid)
    else:
        assert supervisor.check_descendant_cleanup(tmp_path, request, worker_pid)["all_reaped"]


def test_owned_spawn_cannot_escape_the_worker_process_group(tmp_path, monkeypatch):
    module = owner_api()
    owner = module.BackendProcesses(tmp_path, identity={}, token="token")
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **kw: pytest.fail("escaped group launched"))
    with pytest.raises(ValueError):
        owner.spawn(["fixture"], start_new_session=True)
    owner.close()


@pytest.mark.parametrize("resist", [False, True])
@pytest.mark.parametrize("corrupt", [False, True])
def test_real_supervisor_reaps_owned_grandchild_at_cutoff(tmp_path, resist, corrupt):
    from vrptw.supervisor import supervise

    worker = tmp_path / "grandchild_fixture.py"
    worker.write_text(
        """import hashlib,json,os,sys,time
from pathlib import Path
sys.path.insert(0, ROOT_SRC)
from vrptw.supervisor import atomic_json
from vrptw.supervised_process import BackendProcesses
r=json.loads(Path(sys.argv[1]).read_text());s=Path(r['session_dir'])
owner=BackendProcesses(s,identity=r['identity'],token=r['token']);owner.install()
atomic_json(s/'ready.json',{'identity':r['identity'],'cold_start_evidence':{},'worker_ready_perf':time.perf_counter(),'entry':{'cwd':os.getcwd(),'work_entries':[],'cache_entries':[],'cache_dir':os.environ['NUMBA_CACHE_DIR']},'jit_environment':{k:os.environ[k] for k in ('NUMBA_DISABLE_JIT','NUMBA_CACHE_DIR','PYTHONHASHSEED')},'effective_numba':{'cache_dir':os.environ['NUMBA_CACHE_DIR'],'disable_jit':False}})
try:
 while not (s/'start.json').exists():time.sleep(.001)
 start=json.loads((s/'start.json').read_text())
 atomic_json(s/'ack.json',{**start,'worker_received_perf':time.perf_counter()})
 child="import signal,time;from pathlib import Path;"+("signal.signal(signal.SIGTERM,signal.SIG_IGN);" if r['resist'] else "")+f"Path({str(s/'child_ready')!r}).touch();time.sleep(60)"
 process=owner.spawn([sys.executable,'-c',child])
 while not (s/'child_ready').exists() and time.perf_counter()<start['deadline_perf']:time.sleep(.001)
 routes=[[1,2,3]];now=time.perf_counter()
 cert={'clock':'perf_counter','cutoff_sec':start['deadline_perf']-start['start_perf'],'captured_sec':now-start['start_perf'],'nv':1,'td':.6,'phase':'fixture','iter':0,'routes_sha256':hashlib.sha256(json.dumps(routes,separators=(',',':')).encode()).hexdigest(),'validation':{'exact_cover':True,'route_feasible':True,'objective_recomputed':True}}
 atomic_json(s/'incumbent_000001.json',{**start,'sequence':1,'routes':routes,'certificate':cert})
 while time.perf_counter()<start['deadline_perf'] and not owner.stop_requested:time.sleep(.001)
finally:
 owner.close()
 if r['corrupt']:(s/'descendant_cleanup.json').unlink()
""".replace("ROOT_SRC", repr(str(ROOT / "src")))
    )
    session = tmp_path / "session"
    request = {
        "time_limit": 0.4,
        "identity": {"fixture": True},
        "expected_cold": {},
        "descendant_cleanup_required": True,
        "resist": resist,
        "corrupt": corrupt,
    }
    plan, result = supervise(inst(), worker, request, session, setup_timeout=10)
    if corrupt:
        assert plan is None and not result["descendants_reaped"] and "descendant cleanup" in result["error"]
        assert result["native_certification"]["certificate"] is not None
        assert result["worker_reaped"]
        return
    assert "error" not in result, result
    assert plan is not None and result["worker_reaped"] and result["descendants_reaped"]
    assert 0.39 <= result["runtime_sec"] < 1.5
    entry = result["descendant_cleanup"]["processes"][0]
    assert entry["reaped"] and entry["returncode"] is not None
    if resist:
        assert entry["kill_sent"]
