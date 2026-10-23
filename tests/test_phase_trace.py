from __future__ import annotations

import csv
import importlib
import importlib.util
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tracer(clock):
    cls = importlib.import_module("vrptw.phase_trace").PhaseTrace
    return cls(SimpleNamespace(_t_start=100.0, _deadline=110.0), clock=lambda: clock.now)


def test_spans_conserve_exclusive_post_cutoff_time_without_double_counting(tmp_path):
    clock = SimpleNamespace(now=109.0)
    t = tracer(clock)

    def root():
        clock.now = 109.5
        t.call("child", child)
        clock.now = 112.0

    def child():
        clock.now = 111.0

    t.call("solve", root)
    path = tmp_path / "trace.csv"
    t.write(path)
    rows = list(csv.DictReader(path.open()))
    assert [r["name"] for r in rows] == ["solve", "child"]
    assert rows[1]["parent_id"] == rows[0]["id"]
    assert [float(r["post_cutoff_inclusive_sec"]) for r in rows] == [2.0, 1.0]
    assert [float(r["post_cutoff_exclusive_sec"]) for r in rows] == [1.0, 1.0]
    assert sum(float(r["post_cutoff_exclusive_sec"]) for r in rows) == 2.0
    assert all(float(r["solve_deadline_perf"]) == 110 for r in rows)
    with pytest.raises(FileExistsError):
        t.write(path)


def test_trace_preserves_exception_and_restores_instance_method():
    clock = SimpleNamespace(now=100.0)
    t = tracer(clock)

    class Worker:
        def work(self):
            clock.now += 1
            raise ValueError("original failure")

    worker = Worker()
    original = worker.work
    t.patch(worker, "work", "worker.work")
    with pytest.raises(ValueError, match="original failure"):
        t.call("solve", worker.work)
    t.restore()
    assert worker.work == original and "work" not in worker.__dict__
    assert t.stack == []
    assert len(t.events) == 2 and all(e["outcome"] == "ValueError" for e in t.events)


def test_trace_install_restores_module_aliases_and_never_wraps_numba_dispatchers():
    import vrptw.solvers as solvers

    local = importlib.import_module("vrptw.local_search")
    before = local._ejection_chain_eliminate
    repair = list(solvers.REPAIR)
    clock = SimpleNamespace(now=100.0)
    t = tracer(clock)
    t.install()
    assert local._ejection_chain_eliminate != before
    assert all(a != b for a, b in zip(solvers.REPAIR, repair, strict=True))
    t.restore()
    assert local._ejection_chain_eliminate is before and solvers.REPAIR == repair


def test_trace_audit_rejects_clock_parent_and_double_count_tampering(tmp_path):
    phase = importlib.import_module("vrptw.phase_trace")
    clock = SimpleNamespace(now=109.0)
    t = tracer(clock)
    t.call("solve", lambda: setattr(clock, "now", 111.0))
    path = tmp_path / "phase.csv"
    t.write(path)
    assert phase.audit_trace(path)["post_cutoff_sec"] == 1
    rows = list(csv.DictReader(path.open()))
    for key, bad in (("end_perf", "108"), ("parent_id", "123"), ("post_cutoff_exclusive_sec", "999")):
        original = rows[0][key]
        rows[0][key] = bad
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        with pytest.raises(ValueError):
            phase.audit_trace(path)
        rows[0][key] = original


@pytest.mark.parametrize("conflict", ["existing", "json", "profile"])
def test_cli_refuses_colliding_or_combined_instrumentation(monkeypatch, tmp_path, capsys, conflict):
    cli = load_script("benchmark")
    path = tmp_path / "trace.csv"
    args = [
        "benchmark",
        "--instance",
        "unused",
        "--output-json",
        str(tmp_path / "out.json"),
        "--phase-trace",
        str(path),
    ]
    if conflict == "existing":
        path.write_text("keep")
    elif conflict == "json":
        args[args.index("--output-json") + 1] = str(path)
    else:
        args.extend(["--profile", str(tmp_path / "pstats")])
    monkeypatch.setattr(cli.sys, "argv", args)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert {"existing": "Phase trace already exists", "json": "distinct", "profile": "combined"}[
        conflict
    ] in capsys.readouterr().err


def test_custom_schedule_prepare_and_phase_command_are_explicit(tmp_path):
    pilot = load_script("run_factor_contract_pilot")
    job = {**pilot.build_schedule(20261019)[0], "phase_traced": True}
    output = tmp_path / "pilot"
    plan = pilot.prepare(
        output,
        ROOT / "results/gnn_retraining_20261017/model_seed42/best.pt",
        20261019,
        jobs=[job],
        protocol_path=ROOT / "docs/return_timing_20261020.md",
    )
    assert plan["jobs"] == [job] and plan["search_budget_sec"] == 10
    command = pilot.command_for(output, plan, job)
    assert command[-2:] == ["--phase-trace", str(output / f"{job['run']}.phases.csv")]


def test_failure_selection_is_frozen_from_previous_nine_failures():
    runner = load_script("run_return_timing_diagnostic")
    previous = ROOT / "results/factor_contract_pilot_20261020_v2"
    jobs = runner.select_jobs(previous, traced=True)
    assert len(jobs) == 9 and all(j["phase_traced"] and j["time_limit"] == 10 for j in jobs)
    plain = runner.select_jobs(previous, traced=False)
    assert [j["source_run"] for j in jobs] == [j["source_run"] for j in plain]
    assert all(not j["phase_traced"] for j in plain)


def test_cli_trace_is_explicit_and_retains_original_solve_failure(monkeypatch, tmp_path):
    import numpy as np

    from vrptw import Inst
    from vrptw.ablation import AblationHybridSolver
    from vrptw.phase_trace import audit_trace

    cli = load_script("benchmark")
    data = np.zeros((3, 7))
    data[:, 0], data[:, 1], data[:, 5] = range(3), range(3), 100
    data[1:, 3] = 1
    inst = Inst({"name": "trace_fixture", "capacity": 10, "data": data})
    monkeypatch.setattr(cli, "load_solomon_instance", lambda *a: inst)
    monkeypatch.setattr(cli, "get_env_info", lambda: {})

    def fail(solver, **kwargs):
        solver._t_start = time.perf_counter()
        solver._deadline = solver._t_start + 10
        raise RuntimeError("original solve failure")

    monkeypatch.setattr(AblationHybridSolver, "solve", fail)
    output, trace = tmp_path / "raw.json", tmp_path / "spans.csv"
    args = [
        "benchmark",
        "--instance",
        str(ROOT / "pyproject.toml"),
        "--ablation",
        "F000000",
        "--time-limit",
        "10",
        "--output-json",
        str(output),
        "--phase-trace",
        str(trace),
    ]
    monkeypatch.setattr(cli.sys, "argv", args)
    assert cli.main() == 1
    raw = json.loads(output.read_text())
    assert raw["error"] == "RuntimeError: original solve failure"
    assert raw["metadata"]["phase_tracing"]["enabled"] is True
    assert raw["metadata"]["phase_tracing"]["sha256"] == cli.sha256_file(trace)
    assert audit_trace(trace)["spans"] == 1
