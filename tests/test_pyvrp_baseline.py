from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from vrptw import Config, Inst
from vrptw import pyvrp_baseline as baseline
from vrptw.core import Plan

pytestmark = pytest.mark.skipif(importlib.util.find_spec("pyvrp") is None, reason="requires the optional baselines extra")

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pyvrp_benchmark_cli", ROOT / "scripts/benchmark.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def instance():
    data = np.zeros((4, 7), dtype=np.float64)
    data[:, 0] = np.arange(4)
    data[:, 1] = [0.0, 1.123456789, 2.246813579, 3.141592654]
    data[1:, 3] = 1.0
    data[:, 5] = 100.0
    return Inst({"name": "pyvrp_toy", "capacity": 10.0, "data": data})


def solver_for(inst=None, budget=0.2):
    pytest.importorskip("pyvrp")
    return baseline.PyVRPSolver(inst or instance(), Config(time_limit=budget, seed=42))


def test_model_preserves_fleet_first_windows_service_and_client_mapping():
    inst = instance()
    inst.ready_times[1] = 0.123456789
    inst.service_times[1] = 0.234567891
    solver = solver_for(inst)
    data, quantized = solver._build_model()
    vehicle = data.vehicle_type(0)
    assert vehicle.num_available == inst.n
    assert vehicle.fixed_cost == quantized.travel_bound + 1
    assert vehicle.unit_distance_cost == 1 and vehicle.unit_duration_cost == 0
    assert vehicle.start_late == 0 and vehicle.tw_late == quantized.due[0]
    for idx, client in enumerate(data.clients(), start=1):
        assert client.location == idx and client.delivery == [int(inst.demands[idx])]
        assert client.required
        assert client.tw_early / quantized.scale >= inst.ready_times[idx]
        assert client.service_duration / quantized.scale >= inst.service_times[idx]
    assert np.array_equal(data.distance_matrix(0), quantized.distance)
    exact_transit = inst.dist + inst.service_times[:, None]
    duration = data.duration_matrix(0) + np.array([0, *[c.service_duration for c in data.clients()]])[:, None]
    assert np.all(duration / quantized.scale >= exact_transit - 1e-12)


def test_real_seed_reaches_pyvrp_and_fractional_budget_is_not_restarted(monkeypatch):
    solver = solver_for()
    reference = Plan([[1, 2, 3]], solver.inst)
    assert reference.feasible and reference.cost > 0
    original = solver.pyvrp.solve
    seeds = []

    def solve(*args, **kwargs):
        seeds.append(kwargs["seed"])
        assert kwargs["initial_solution"] is None
        return original(*args, **kwargs)

    monkeypatch.setattr(solver.pyvrp, "solve", solve)
    plan, _ = solver.solve(seed=47)
    assert seeds == [47]
    assert plan.feasible and sorted(node for route in plan.routes for node in route) == [1, 2, 3]
    assert solver.diagnostics["seed"] == 47
    assert solver.diagnostics["requested_budget_sec"] == 0.2
    assert solver.diagnostics["incumbent_capture_sec"] < 0.2
    assert solver.diagnostics["selected_integer_objective"] == (
        plan.nv * solver.diagnostics["fleet_cost"] + solver.diagnostics["selected_integer_distance"]
    )
    assert solver.elapsed_sec >= 0.2 and solver.search_iterations > 0


def test_model_build_expiry_prevents_starting_backend(monkeypatch):
    solver = solver_for(budget=0.1)
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(baseline, "time", SimpleNamespace(perf_counter=lambda: clock.now))
    original = solver._build_model

    def build():
        model = original()
        clock.now = 1.0
        return model

    monkeypatch.setattr(solver, "_build_model", build)
    monkeypatch.setattr(solver.pyvrp, "solve", lambda *a, **k: pytest.fail("late backend call"))
    with pytest.raises(baseline.PyVRPNoSolutionError, match="budget"):
        solver.solve()
    assert solver.diagnostics["status"] == "budget_exhausted_before_search"


def test_initialisation_and_late_final_solution_cannot_escape_deadline(monkeypatch):
    solver = solver_for(budget=0.1)
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(baseline, "time", SimpleNamespace(perf_counter=lambda: clock.now))

    def solve(data, stop, **kwargs):
        clock.now = 1.0
        assert stop(0)
        kwargs["params"].ils.callbacks.on_start(SimpleNamespace(initial_solution=None))
        return SimpleNamespace(num_iterations=0, runtime=0.0, best=object())

    monkeypatch.setattr(solver.pyvrp, "solve", solve)
    with pytest.raises(baseline.PyVRPNoSolutionError):
        solver.solve()
    assert solver.time_limit_hit and solver._best_plan is None


@pytest.mark.parametrize("stage", ["before", "copy", "validation"])
def test_late_callback_is_rejected_even_when_feasible(monkeypatch, stage):
    solver = solver_for(budget=1)
    solver._start, solver._deadline = 0.0, 1.0
    clock = SimpleNamespace(now=2.0 if stage == "before" else 0.0)
    monkeypatch.setattr(baseline, "time", SimpleNamespace(perf_counter=lambda: clock.now))

    def routes(solution):
        if stage == "copy":
            clock.now = 2.0
        return [[1, 2, 3]]

    def plan(*args):
        clock.now = 2.0
        return SimpleNamespace(feasible=True, cost=1.0, nv=1)

    monkeypatch.setattr(solver, "_read_routes", routes)
    if stage == "validation":
        monkeypatch.setattr(baseline, "Plan", plan)
    solution = SimpleNamespace(is_feasible=lambda: True, distance=lambda: 1, fixed_vehicle_cost=lambda: 1)
    solver._capture_solution(solution)
    assert solver._best_plan is None


@pytest.mark.parametrize("field", ["demand", "depot", "overflow"])
def test_unsupported_input_fails_closed(field):
    inst = instance()
    if field == "demand":
        inst.demands[1] = 1.5
    elif field == "depot":
        inst.service_times[0] = 1
    else:
        inst.dist *= 1e16
    with pytest.raises(ValueError):
        solver_for(inst).solve()


def test_final_customer_service_and_depot_return_are_enforced():
    inst = instance()
    inst.service_times[1:] = 100
    with pytest.raises(baseline.PyVRPNoSolutionError):
        solver_for(inst).solve()


def test_unified_cli_exposes_no_neural_components():
    cls, cfg = cli.get_solver_and_config("pyvrp", 0.25, seed=47)
    assert cls is baseline.PyVRPSolver and cfg.time_limit == 0.25
    assert not any(cli.extract_instrumentation(cls(instance(), cfg), cfg, "pyvrp")["resolved_components"].values())


@pytest.mark.parametrize("has_solution", [True, False])
def test_cli_records_adapter_on_success_and_failure(monkeypatch, tmp_path, has_solution):
    inst = instance()
    input_path, output = tmp_path / "instance.txt", tmp_path / "out.json"
    input_path.write_text("fixture")
    monkeypatch.setattr(cli, "load_solomon_instance", lambda path: inst)

    def solve(solver, seed=None):
        solver.diagnostics = {"seed": seed, "pyvrp_version": "0.14.1"}
        if not has_solution:
            raise baseline.PyVRPNoSolutionError("no timely incumbent")
        return Plan([[1, 2, 3]], inst), []

    monkeypatch.setattr(baseline.PyVRPSolver, "solve", solve)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark.py",
            "--instance",
            str(input_path),
            "--ablation",
            "pyvrp",
            "--seed",
            "47",
            "--output-json",
            str(output),
        ],
    )
    assert cli.main() == (0 if has_solution else 1)
    payload = json.loads(output.read_text())
    assert payload["adapter"]["seed"] == 47 and payload["feasible"] is has_solution


@pytest.mark.parametrize("extra", [["--gnn-model", "unused.pt"], ["--budget-mode", "capped"]])
def test_cli_rejects_conflicting_modes(monkeypatch, tmp_path, extra):
    path, out = tmp_path / "instance.txt", tmp_path / "out.json"
    path.write_text("fixture")
    monkeypatch.setattr(
        sys, "argv", ["benchmark.py", "--instance", str(path), "--ablation", "pyvrp", *extra, "--output-json", str(out)]
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2 and not out.exists()
