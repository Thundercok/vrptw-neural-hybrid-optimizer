from __future__ import annotations

import copy
import importlib
import json
import math
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from vrptw import Config, Inst, Plan, solvers
from vrptw.native_certification import NativeIncumbent


def api():
    return importlib.import_module("vrptw.supervisor")


@pytest.fixture
def case():
    data = np.zeros((4, 7))
    data[:, 0], data[:, 1], data[:, 5] = range(4), range(4), 100
    data[1:, 3] = 1
    inst = Inst({"name": "supervisor_fixture", "capacity": 10, "data": data})
    clock = SimpleNamespace(now=100.2)
    native = NativeIncumbent(inst, start=100.0, deadline=101.0, clock=lambda: clock.now)
    assert native.consider(Plan([[1, 2, 3]], inst), phase="initial")
    packet = {
        "sequence": 1,
        "token": "fixture",
        "start_perf": 100.0,
        "deadline_perf": 101.0,
        "routes": [[1, 2, 3]],
        "certificate": copy.deepcopy(native.diagnostics["certificate"]),
        "checkpoint": {"iterations": 7},
    }
    clock.now = 100.3
    return SimpleNamespace(inst=inst, clock=clock, packet=packet)


def admission(case):
    return api().SupervisorIncumbent(
        case.inst, start=100.0, deadline=101.0, token="fixture", clock=lambda: case.clock.now
    )


def test_native_observer_gets_only_valid_promotions_and_cannot_mutate_evidence(case):
    messages = []

    def observe(payload):
        messages.append(copy.deepcopy(payload))
        payload["routes"][0].clear()
        payload["certificate"]["validation"]["exact_cover"] = False

    tracker = NativeIncumbent(case.inst, start=100.0, deadline=101.0, clock=lambda: case.clock.now, on_capture=observe)
    assert tracker.consider(Plan([[1, 2, 3]], case.inst), phase="initial")
    assert not tracker.consider(Plan([[1, 2]], case.inst), phase="invalid")
    assert not tracker.consider(Plan([[1, 2, 3]], case.inst), phase="same")
    case.clock.now = 101
    assert not tracker.consider(Plan([[3, 2, 1]], case.inst), phase="late")
    assert len(messages) == 1 and messages[0]["routes"] == [[1, 2, 3]]
    assert tracker.finish().routes == [[1, 2, 3]]
    assert tracker.diagnostics["certificate"]["validation"]["exact_cover"] is True


@pytest.mark.parametrize("solver_cls", [solvers.ALNSSolver, solvers.HybridDDQNSolver])
def test_native_solver_uses_injected_parent_origin_and_not_a_new_budget(case, monkeypatch, solver_cls):
    parent = NativeIncumbent(case.inst, start=100.0, deadline=101.0, clock=lambda: case.clock.now)
    monkeypatch.setattr(solvers, "time", SimpleNamespace(perf_counter=lambda: case.clock.now))
    cfg = Config(
        time_limit=10,
        alns_iterations=0,
        hybrid_iterations=0,
        polish_iterations=0,
        per_beta_auto_scale=False,
        split_enabled=False,
        route_pool_limit=0,
        recombine_after_main_search=False,
        recombine_after_polish=False,
        macro_enabled=False,
    )
    solver = solver_cls(case.inst, cfg)
    case.clock.now = 101
    with pytest.raises(RuntimeError, match="no.*certified.*incumbent"):
        solver.solve(seed=42, init=Plan([[1, 2, 3]], case.inst), _certifier=parent)
    assert solver._t_start == 100 and solver._deadline == 101
    assert solver.native_certification["cutoff_sec"] == 1


def test_admission_recomputes_original_routes_and_records_parent_availability(case):
    supervisor = admission(case)
    assert supervisor.offer(case.packet)
    case.packet["routes"][0].clear()
    assert supervisor.finish().routes == [[1, 2, 3]]
    cert = supervisor.diagnostics["certificate"]
    assert cert["captured_sec"] == pytest.approx(0.3)
    assert cert["worker_captured_sec"] == pytest.approx(0.2)
    assert cert["receipt_sec"] == pytest.approx(0.3)
    assert supervisor.checkpoint == {"iterations": 7}


@pytest.mark.parametrize(
    "defect",
    [
        "token",
        "origin",
        "deadline",
        "nan",
        "future",
        "capture",
        "cutoff",
        "hash",
        "cost",
        "nv",
        "bool",
        "float",
        "cover",
        "capacity",
        "window",
        "return",
        "service",
        "sequence",
        "validation",
    ],
)
def test_admission_rejects_corrupt_or_infeasible_certificates(case, defect):
    packet = case.packet
    if defect == "token":
        packet["token"] = "foreign"
    elif defect == "origin":
        packet["start_perf"] = 99
    elif defect == "deadline":
        packet["deadline_perf"] = 102
    elif defect == "nan":
        packet["certificate"]["captured_sec"] = math.nan
    elif defect == "future":
        packet["certificate"]["captured_sec"] = 0.9
    elif defect == "capture":
        packet["certificate"]["captured_sec"] = -0.1
    elif defect == "cutoff":
        packet["certificate"]["cutoff_sec"] = 2
    elif defect == "hash":
        packet["certificate"]["routes_sha256"] = "wrong"
    elif defect == "cost":
        packet["certificate"]["td"] = -1
    elif defect == "nv":
        packet["certificate"]["nv"] = 2
    elif defect == "bool":
        packet["routes"][0][0] = True
    elif defect == "float":
        packet["routes"][0][0] = 1.0
    elif defect == "cover":
        packet["routes"] = [[1, 2]]
    elif defect == "capacity":
        case.inst.capacity = 1
    elif defect == "window":
        case.inst.due_times[1] = 0
    elif defect == "return":
        case.inst.due_times[0] = 1
    elif defect == "service":
        case.inst.service_times[1] = 1000
    elif defect == "sequence":
        packet["sequence"] = 3
    else:
        packet["certificate"]["validation"]["exact_cover"] = False
    with pytest.raises(api().SupervisorProtocolError):
        admission(case).offer(packet)


@pytest.mark.parametrize("stage", ["receipt", "validation", "hash"])
@pytest.mark.parametrize("finish", [101.0, 102.0])
def test_late_delivery_or_parent_work_never_creates_a_pre_cutoff_incumbent(case, monkeypatch, stage, finish):
    module = api()
    supervisor = admission(case)
    if stage == "receipt":
        case.clock.now = finish
    else:
        original = getattr(module, "validate_routes" if stage == "validation" else "routes_sha256")

        def delayed(*args):
            result = original(*args)
            case.clock.now = finish
            return result

        monkeypatch.setattr(module, "validate_routes" if stage == "validation" else "routes_sha256", delayed)
    assert not supervisor.offer(case.packet)
    with pytest.raises(RuntimeError, match="no.*certified.*incumbent"):
        supervisor.finish()


def test_late_or_fleet_worse_packet_cannot_replace_parent_fallback(case):
    supervisor = admission(case)
    assert supervisor.offer(case.packet)
    worse = NativeIncumbent(case.inst, start=100.0, deadline=101.0, clock=lambda: case.clock.now)
    assert worse.consider(Plan([[1], [2, 3]], case.inst), phase="worse")
    other = {**case.packet, "sequence": 2, "routes": [[1], [2, 3]], "certificate": worse.diagnostics["certificate"]}
    assert not supervisor.offer(other)
    case.clock.now = 102
    assert not supervisor.offer({**case.packet, "sequence": 3})
    assert supervisor.finish().routes == [[1, 2, 3]]


def test_worker_capture_cannot_precede_the_workers_start_receipt(case):
    supervisor = admission(case)
    supervisor.worker_received_perf = 100.25
    with pytest.raises(api().SupervisorProtocolError):
        supervisor.offer(case.packet)


@pytest.fixture
def worker_script(tmp_path):
    path = tmp_path / "fixture_worker.py"
    path.write_text("""import hashlib,json,os,signal,sys,time
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text()); s=Path(r['session_dir'])
if r['mode']=='setup_error': sys.exit(9)
if r['mode']=='setup_hang': time.sleep(60)
def write(name,obj):
 p=s/name; t=p.with_suffix('.pending'); t.write_text(json.dumps(obj)); os.replace(t,p)
ready={'identity':r['identity'],'cold_start_evidence':r['expected_cold'], 'worker_ready_perf':time.perf_counter(), 'entry':{'cwd':os.getcwd(),'work_entries':[],'cache_entries':[],'cache_dir':os.environ['NUMBA_CACHE_DIR']},'jit_environment':{k:os.environ[k] for k in ('NUMBA_DISABLE_JIT','NUMBA_CACHE_DIR','PYTHONHASHSEED')},'effective_numba':{'cache_dir':os.environ['NUMBA_CACHE_DIR'],'disable_jit':False}}
if r['mode']=='identity': ready['identity']={}
if r['mode']=='dirty': ready['entry']['work_entries']=['old_archive']
write('ready.json',ready)
while not (s/'start.json').exists(): time.sleep(.001)
start=json.loads((s/'start.json').read_text()); now=time.perf_counter()
write('ack.json',{**start,'worker_received_perf':now+(10 if r['mode']=='clock' else 0)})
if r['mode']=='late': time.sleep(.25)
if r['mode'] not in ('none','early','completion_only'):
 routes=[[1,2,3]]; certificate={'clock':'perf_counter','cutoff_sec':start['deadline_perf']-start['start_perf'],'routes_sha256':hashlib.sha256(json.dumps(routes,separators=(',',':')).encode()).hexdigest(),'nv':1,'td':6.0,'phase':'initial','iter':0,'captured_sec':now-start['start_perf'],'validation':{'exact_cover':True,'route_feasible':True,'objective_recomputed':True}}
 packet={**start,'sequence':1,'routes':routes,'certificate':certificate,'checkpoint':{'iterations':0}}
 if r['mode']=='corrupt': packet['certificate']['td']=-1
 if r['mode']=='pending': (s/'incumbent_000001.pending').write_text('{')
 else: write('incumbent_000001.json',packet)
if r['mode']=='early': sys.exit(7)
if r['mode'] in ('done','completion_only'):
 write('completion.json',{'token':r['token'],'identity':r['identity'],'counters':{'iterations':1},'routes':[[1,2,3]]})
 sys.exit(0)
if r['mode']=='resist': signal.signal(signal.SIGTERM,signal.SIG_IGN)
while True: time.sleep(60)
""")
    return path


@pytest.mark.parametrize(
    "mode",
    [
        "blocked",
        "resist",
        "none",
        "corrupt",
        "pending",
        "early",
        "dirty",
        "identity",
        "clock",
        "late",
        "setup_error",
        "setup_hang",
        "done",
        "completion_only",
    ],
)
def test_real_process_supervisor_cuts_off_and_reaps_worker(case, tmp_path, worker_script, mode):
    request = {"time_limit": 0.2, "identity": {"fixture": True}, "expected_cold": {}, "mode": mode}
    session = tmp_path / "session"
    before = time.perf_counter()
    plan, result = api().supervise(
        case.inst, worker_script, request, session, setup_timeout=0.1 if mode == "setup_hang" else 5
    )
    assert time.perf_counter() - before < 3
    assert result["worker_reaped"] and result["worker_returncode"] is not None
    assert result["cleanup_end_perf"] >= result["cleanup_start_perf"]
    assert json.loads((session / "launch.json").read_text())["worker_pid"] == result["worker_pid"]
    if result["runtime_sec"] is not None:
        assert result["cleanup_end_perf"] <= result["solve_start_perf"] + result["runtime_sec"]
        if result["stop_reason"] == "cutoff":
            assert result["cleanup_start_perf"] >= result["solve_deadline_perf"]
    assert result["resource_usage"]["parent_cpu_sec"] >= 0
    assert result["resource_usage"]["worker_cpu_sec"] >= 0
    assert (session / "request.json").is_file()
    if mode not in ("setup_error", "setup_hang"):
        entry = json.loads((session / "ready.json").read_text())["entry"]
        assert entry["cache_entries"] == []
        assert entry["cwd"] == str(session / "work")
    if mode in ("blocked", "resist"):
        assert plan.routes == [[1, 2, 3]] and "error" not in result
        assert 0.19 <= result["runtime_sec"] < 0.7
        assert result["native_certification"]["certificate"]["captured_sec"] < 0.2
        assert result["final_worker_counters"] is None and result["worker_checkpoint"] == {"iterations": 0}
        if mode == "resist":
            assert result["kill_sent"]
    elif mode == "done":
        assert plan.routes == [[1, 2, 3]] and "error" not in result
        assert result["runtime_sec"] < 0.19 and result["stop_reason"] == "worker_exit"
        assert result["final_worker_counters"] == {"iterations": 1}
    else:
        assert plan is None and result["error"]
    with pytest.raises(FileExistsError):
        api().supervise(case.inst, worker_script, request, session, setup_timeout=5)


def test_worker_exit_during_directory_scan_does_not_lose_a_delivered_packet(case, tmp_path, worker_script, monkeypatch):
    module = api()
    original_popen, original_glob = module.subprocess.Popen, Path.glob
    processes, dropped = [], []

    def popen(*args, **kwargs):
        process = original_popen(*args, **kwargs)
        processes.append(process)
        return process

    def glob(path, pattern):
        files = list(original_glob(path, pattern))
        if pattern == "incumbent_*.json" and files and not dropped:
            processes[0].wait(timeout=1)
            dropped.append(True)
            return iter(())
        return iter(files)

    monkeypatch.setattr(module.subprocess, "Popen", popen)
    monkeypatch.setattr(Path, "glob", glob)
    plan, result = module.supervise(
        case.inst,
        worker_script,
        {"time_limit": 0.3, "identity": {}, "expected_cold": {}, "mode": "done"},
        tmp_path / "session",
        setup_timeout=5,
    )
    assert dropped and plan is not None and "error" not in result


def test_ack_published_between_poll_and_packet_scan_is_not_a_protocol_failure(
    case, tmp_path, worker_script, monkeypatch
):
    original_exists = Path.exists
    delayed = []

    def exists(path):
        if path.name == "ack.json" and not delayed:
            limit = time.perf_counter() + 1
            while not original_exists(path.parent / "completion.json") and time.perf_counter() < limit:
                time.sleep(0.001)
            delayed.append(True)
            return False
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", exists)
    plan, result = api().supervise(
        case.inst,
        worker_script,
        {"time_limit": 0.3, "identity": {}, "expected_cold": {}, "mode": "done"},
        tmp_path / "session",
        setup_timeout=5,
    )
    assert delayed and plan is not None and "error" not in result
