from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from vrptw import Config, Inst
from vrptw import benchmark as legacy_benchmark
from vrptw import ortools_baseline as baseline
from vrptw.config import ALGO_ORTOOLS
from vrptw.core import Plan

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ortools_benchmark_cli", ROOT / "scripts/benchmark.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def instance():
    data = np.zeros((4, 7), dtype=np.float64)
    data[:, 0] = np.arange(4)
    data[:, 1] = [0.0, 1.123456789, 2.246813579, 3.141592654]
    data[1:, 3] = 1.0
    data[:, 5] = 100.0
    return Inst({"name": "baseline_toy", "capacity": 10.0, "data": data})


def test_fleet_cost_dominates_every_possible_travel_difference():
    inst = instance()
    data = baseline.prepare_ortools_data(inst)
    assert data.travel_bound == 2 * inst.n * int(data.distance.max())
    assert data.fleet_cost == data.travel_bound + 1
    for fleet in range(1, inst.n):
        assert fleet * data.fleet_cost + data.travel_bound < (fleet + 1) * data.fleet_cost


def test_time_rounding_is_conservative_and_distance_error_is_bounded():
    inst = instance()
    inst.ready_times[1] = 0.123456789
    inst.due_times[1] = 90.123456789
    inst.service_times[1] = 0.234567891
    data = baseline.prepare_ortools_data(inst)
    assert np.all(data.ready / data.scale >= inst.ready_times)
    assert np.all(data.due / data.scale <= inst.due_times)
    exact = inst.dist + inst.service_times[:, None]
    assert np.all(data.transit / data.scale >= exact - 1e-12)
    assert np.abs(data.distance / data.scale - inst.dist).max() <= 0.5 / data.scale + 1e-12


@pytest.mark.parametrize("field", ["demand", "capacity", "depot_ready", "depot_service"])
def test_unsupported_input_is_rejected_not_silently_truncated(field):
    inst = instance()
    if field == "demand":
        inst.demands[1] = 1.5
    elif field == "capacity":
        inst.capacity = 10.5
    elif field == "depot_ready":
        inst.ready_times[0] = 1.0
    else:
        inst.service_times[0] = 1.0
    with pytest.raises(ValueError):
        baseline.prepare_ortools_data(inst)


def test_integer_objective_overflow_is_rejected():
    inst = instance()
    inst.dist[:] *= 1e16
    with pytest.raises(ValueError, match="overflow|range"):
        baseline.prepare_ortools_data(inst)


def test_fractional_budget_and_real_cp_seed_are_applied(monkeypatch):
    pywrapcp = pytest.importorskip("ortools.constraint_solver.pywrapcp")
    original = pywrapcp.Solver.ReSeed
    seeds = []

    def reseed(solver, seed):
        seeds.append(seed)
        return original(solver, seed)

    monkeypatch.setattr(pywrapcp.Solver, "ReSeed", reseed)
    inst = instance()
    # This unit checks fractional API forwarding, not cold-start JIT latency.
    reference = Plan([[1, 2, 3]], inst)
    assert reference.feasible and reference.cost > 0
    solver = baseline.ORToolsSolver(inst, Config(time_limit=0.2, ortools_time_limit=99, seed=42))
    plan, _ = solver.solve(seed=47)
    assert plan.feasible and sorted(node for route in plan.routes for node in route) == [1, 2, 3]
    assert seeds == [47]
    diagnostics = solver.diagnostics
    assert 0 < diagnostics["search_budget_ns"] < 200_000_000
    assert diagnostics["cp_seed"] == 47
    assert diagnostics["requested_budget_sec"] == 0.2
    assert diagnostics["model_build_sec"] > 0
    assert diagnostics["search_sec"] > 0
    assert diagnostics["postprocess_sec"] >= 0
    assert diagnostics["incumbent_capture_sec"] <= 0.2
    assert solver.elapsed_sec >= diagnostics["model_build_sec"] + diagnostics["search_sec"]
    assert solver.search_iterations == 0  # CP branches are not ALNS iterations.


def test_model_build_consumes_budget_and_cannot_launch_unlimited_search(monkeypatch):
    pytest.importorskip("ortools")
    solver = baseline.ORToolsSolver(instance(), Config(time_limit=0.1))
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(baseline, "time", SimpleNamespace(perf_counter=lambda: clock.now))
    original = solver._build_model

    def build(data):
        result = original(data)
        clock.now = 1.0
        return result

    monkeypatch.setattr(solver, "_build_model", build)
    monkeypatch.setattr(solver.pywrapcp.RoutingModel, "SolveWithParameters", lambda *a: pytest.fail("late search"))
    with pytest.raises(baseline.ORToolsNoSolutionError, match="budget"):
        solver.solve(seed=42)
    assert solver.diagnostics["status"] == "budget_exhausted_before_search"
    assert solver.diagnostics["search_sec"] == 0


@pytest.mark.parametrize("expires_during_copy", [False, True])
def test_late_solution_callback_cannot_replace_the_incumbent(monkeypatch, expires_during_copy):
    pytest.importorskip("ortools")
    solver = baseline.ORToolsSolver(instance(), Config(time_limit=1.0))
    solver._start = 0.0
    solver._deadline = 1.0
    clock = SimpleNamespace(now=0.0 if expires_during_copy else 2.0)
    monkeypatch.setattr(baseline, "time", SimpleNamespace(perf_counter=lambda: clock.now))

    def routes(*args):
        clock.now = 2.0
        return [[1, 2, 3]]

    monkeypatch.setattr(solver, "_read_routes", routes)
    routing = SimpleNamespace(CostVar=lambda: SimpleNamespace(Value=lambda: 1))
    solver._capture_solution(None, routing)
    assert solver._best_routes is None


def test_depot_return_and_last_customer_service_are_enforced():
    pytest.importorskip("ortools")
    inst = instance()
    inst.due_times[0] = 2.0
    inst.horizon = 2.0
    solver = baseline.ORToolsSolver(inst, Config(time_limit=0.1))
    with pytest.raises(baseline.ORToolsNoSolutionError):
        solver.solve(seed=42)


def test_unified_cli_exposes_ortools_without_neural_components():
    solver_cls, cfg = cli.get_solver_and_config("ortools", 0.25, seed=47)
    assert solver_cls is baseline.ORToolsSolver
    assert cfg.time_limit == cfg.ortools_time_limit == 0.25
    solver = solver_cls(instance(), cfg)
    assert not any(cli.extract_instrumentation(solver, cfg, "ortools")["resolved_components"].values())


def test_legacy_caller_preserves_requested_budget_and_run_seed(monkeypatch):
    inst = instance()
    cfg = Config(seed=42, time_limit=80.0)
    captured = []

    def run(actual_inst, actual_cfg):
        assert actual_inst is inst
        captured.append((actual_cfg.seed, actual_cfg.time_limit, actual_cfg.ortools_time_limit))
        return Plan([[1, 2, 3]], inst, ALGO_ORTOOLS), 0.01

    monkeypatch.setattr(legacy_benchmark, "run_ortools", run)
    legacy_benchmark.run_instance(inst, ALGO_ORTOOLS, cfg, seed=47, ddqn_time=2.5)
    assert captured == [(47, 2.5, 2.5)]
    assert cfg.seed == 42 and cfg.time_limit == 80.0


@pytest.mark.parametrize("has_solution", [True, False])
def test_cli_records_adapter_provenance_on_success_and_failure(monkeypatch, tmp_path, has_solution):
    pytest.importorskip("ortools")
    inst = instance()
    input_path = tmp_path / "instance.txt"
    input_path.write_text("fixture")
    output = tmp_path / "output.json"
    monkeypatch.setattr(cli, "load_solomon_instance", lambda path: inst)

    def solve(solver, seed=None):
        solver.diagnostics = {"status": "completed" if has_solution else "no_incumbent", "cp_seed": seed}
        if not has_solution:
            raise baseline.ORToolsNoSolutionError("no timely incumbent")
        plan = Plan([[1, 2, 3]], inst)
        return plan, [plan.cost]

    monkeypatch.setattr(baseline.ORToolsSolver, "solve", solve)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark.py",
            "--instance",
            str(input_path),
            "--ablation",
            "ortools",
            "--seed",
            "47",
            "--time-limit",
            "0.25",
            "--output-json",
            str(output),
        ],
    )
    assert cli.main() == (0 if has_solution else 1)
    payload = json.loads(output.read_text())
    assert payload["adapter"]["cp_seed"] == 47
    assert payload["metadata"]["time_limit"] == 0.25
    assert payload["requested_config"]["ortools_time_limit"] == 0.25
    assert payload["feasible"] is has_solution
    if has_solution:
        assert not any(payload["resolved_components"].values())
    else:
        assert "ORToolsNoSolutionError" in payload["error"]


@pytest.mark.parametrize("extra", [["--gnn-model", "not-loaded.pt"], ["--budget-mode", "capped"]])
def test_cli_rejects_incompatible_modes_for_the_external_baseline(monkeypatch, tmp_path, extra):
    input_path = tmp_path / "instance.txt"
    input_path.write_text("fixture")
    output = tmp_path / "output.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark.py",
            "--instance",
            str(input_path),
            "--ablation",
            "ortools",
            *extra,
            "--output-json",
            str(output),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2 and not output.exists()
