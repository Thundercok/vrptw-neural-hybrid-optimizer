from __future__ import annotations

import importlib.util
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


@pytest.mark.parametrize("problem", ["external", "budget", "session", "output", "collision", "ancestor"])
def test_supervised_cli_refuses_unsupported_or_overwriting_requests(tmp_path, monkeypatch, capsys, problem):
    cli = load_script("benchmark_supervised")
    # A missing parser guard must never launch a real solve from this unit test.
    monkeypatch.setattr(
        cli,
        "supervise",
        lambda *a, **kw: (None, {"error": "unit-test stub", "runtime_sec": 0.0, "final_worker_counters": None}),
    )
    session, output = tmp_path / "session", tmp_path / "result.json"
    args = [
        "supervised",
        "--instance",
        str(ROOT / "data/Solomon/c101.txt"),
        "--ablation",
        "alns",
        "--time-limit",
        "10",
        "--session-dir",
        str(session),
        "--output-json",
        str(output),
    ]
    if problem == "external":
        args[args.index("alns")] = "ortools"
    elif problem == "budget":
        args[args.index("10")] = "nan"
    elif problem == "session":
        session.mkdir()
    elif problem == "output":
        output.write_text("preserve")
    elif problem == "collision":
        args[args.index(str(output))] = str(session / "start.json")
    else:
        args[args.index(str(session))] = str(output / "session")
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2 and capsys.readouterr().err
    if problem == "output":
        assert output.read_text() == "preserve"


def test_cli_binds_full_config_identity_and_marks_unknown_final_counters(tmp_path, monkeypatch):
    cli = load_script("benchmark_supervised")
    observed = []

    def supervise(inst, worker, request, session):
        observed.append((worker, request, session))
        return None, {"error": "NativeNoSolutionError: fixture", "runtime_sec": 10.01, "final_worker_counters": None}

    monkeypatch.setattr(cli, "supervise", supervise)
    monkeypatch.setattr(cli.native_cli, "get_env_info", lambda: {"source_sha256": "fixture_source"})
    output, session = tmp_path / "result.json", tmp_path / "session"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "supervised",
            "--instance",
            str(ROOT / "data/Solomon/c101.txt"),
            "--ablation",
            "F000000",
            "--time-limit",
            "10",
            "--session-dir",
            str(session),
            "--output-json",
            str(output),
        ],
    )
    assert cli.main() == 1
    worker, request, actual_session = observed[0]
    assert worker == ROOT / "scripts/native_supervisor_worker.py" and actual_session == session
    identity = request["identity"]
    assert identity["source_sha256"] == "fixture_source" and identity["seed"] == 42
    assert identity["case"] == "F000000" and identity["requested_config"]["hybrid_iterations"] == 10000
    assert identity["requested_config"]["output_dir"] == str(session / "work/archive")
    raw = json.loads(output.read_text())
    assert not raw["feasible"] and raw["execution_mode"] == "native_supervisor_v1"
    assert raw["iterations"] is None and raw["instrumentation"] is None
    assert raw["metadata"]["hard_return_deadline"] is False


@pytest.mark.parametrize("defect", [None, "config", "input", "source", "model"])
def test_real_worker_entry_binds_setup_and_publishes_the_injected_certifier(tmp_path, monkeypatch, defect):
    import numpy as np

    from vrptw import Inst, Plan
    from vrptw.supervisor import atomic_json

    worker = load_script("native_supervisor_worker")
    cli = worker.cli
    session = tmp_path / "session"
    session.mkdir()
    data = np.zeros((4, 7))
    data[:, 0], data[:, 1], data[:, 5] = range(4), range(4), 100
    data[1:, 3] = 1
    inst = Inst({"name": "worker_unit_fixture", "capacity": 10, "data": data})
    _, cfg = cli.get_solver_and_config("alns", 10, seed=42)
    cfg.output_dir = str(session / "work/archive")
    observed = []

    class Solver:
        gnn_model = None

        def __init__(self, inst, cfg):
            self.cfg, self.search_iterations = cfg, 0

        def solve(self, *, seed, _certifier):
            observed.append((seed, _certifier.start, _certifier.deadline))
            assert _certifier.consider(Plan([[1, 2, 3]], inst), phase="initial")
            self.native_certification = _certifier.diagnostics
            return _certifier.finish(), []

    path = ROOT / "data/Solomon/c101.txt"
    identity = {
        "case": "alns",
        "seed": 42,
        "requested_config": asdict(cfg),
        "source_sha256": "unit_source",
        "instance_sha256": cli.sha256_file(path),
        "gnn_model_sha256": None,
    }
    request = {
        "session_dir": str(session),
        "identity": identity,
        "instance": str(path),
        "gnn_model": None,
        "time_limit": 10,
        "token": "unit_token",
    }
    if defect == "config":
        identity["requested_config"]["seed"] = 99
    elif defect == "input":
        identity["instance_sha256"] = "wrong"
    elif defect == "source":
        identity["source_sha256"] = "wrong"
    elif defect == "model":
        identity["gnn_model_sha256"] = "wrong"
    start = time.perf_counter()
    atomic_json(session / "request.json", request)
    atomic_json(session / "start.json", {"token": "unit_token", "start_perf": start, "deadline_perf": start + 10})
    environment = {
        "source_sha256": "unit_source",
        "process_entry": {
            "cwd": str(session / "work"),
            "cwd_entries": [],
            "cache_dir": str(session / "cache"),
            "cache_entries": [],
        },
        "jit_environment": {},
        "numba": {},
    }
    monkeypatch.setattr(cli, "get_solver_and_config", lambda *a, **kw: (Solver, cfg))
    monkeypatch.setattr(cli, "load_solomon_instance", lambda *a: inst)
    monkeypatch.setattr(cli, "get_env_info", lambda: environment)
    monkeypatch.setattr(cli, "cold_start_state", lambda *a: {})
    monkeypatch.setattr(cli, "extract_instrumentation", lambda *a: {"unit_checkpoint": True})
    monkeypatch.setattr(sys, "argv", ["worker", str(session / "request.json")])
    result = worker.main()
    completion = json.loads((session / "completion.json").read_text())
    if defect is not None:
        assert result == 1 and completion["error"] and not (session / "ready.json").exists()
    else:
        assert result == 0 and observed == [(42, start, start + 10)]
        packet = json.loads((session / "incumbent_000001.json").read_text())
        assert packet["start_perf"] == start and packet["routes"] == [[1, 2, 3]]
        assert packet["certificate"]["captured_sec"] < 10
        assert packet["checkpoint"]["instrumentation"] == {"unit_checkpoint": True}
        assert completion["counters"]["iterations"] == 0
