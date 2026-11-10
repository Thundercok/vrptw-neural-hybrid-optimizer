from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from vrptw import Config, Inst, solvers
from vrptw.core import Plan


@pytest.fixture
def case(monkeypatch):
    data = np.zeros((4, 7), dtype=np.float64)
    data[:, 0] = np.arange(4)
    data[1:, 1:3] = [(1, 0), (0, 1), (2, 0)]
    data[1:, 3], data[:, 5] = 1, 100
    inst = Inst({"name": "native_certificate", "capacity": 10.0, "data": data})
    clock = SimpleNamespace(now=100.0)
    monkeypatch.setattr(solvers, "time", SimpleNamespace(perf_counter=lambda: clock.now))
    return SimpleNamespace(
        inst=inst,
        initial=Plan([[1, 2, 3]], inst),
        better=Plan([[2, 1, 3]], inst),
        clock=clock,
    )


def make_solver(case, monkeypatch, solver_cls, **overrides):
    options = dict(
        time_limit=1.0,
        alns_iterations=0,
        hybrid_iterations=0,
        per_beta_auto_scale=False,
        adaptive_feasibility=False,
        macro_enabled=False,
        split_enabled=False,
        recombine_after_main_search=False,
        recombine_after_polish=False,
    )
    options.update(overrides)
    solver = solver_cls(case.inst, Config(**options))
    if isinstance(solver, solvers.HybridDDQNSolver):
        solver.use_op_rl = False
        monkeypatch.setattr(solver, "_select_action", lambda *a: (0, False))
        monkeypatch.setattr(solver, "_local_search", lambda plan, **kw: plan)
        monkeypatch.setattr(solver, "_fixed_nv_polish", lambda plan, *a, **kw: plan)
        monkeypatch.setattr(solver, "_try_gec_route_reduction", lambda *a, **kw: None)
        monkeypatch.setattr(solvers, "_try_route_merge", lambda *a, **kw: None)
        for method in (
            "_generate_dense_pool_columns",
            "_seed_savings_routes",
            "_seed_nv_targeted_construction",
            "_seed_pool_large_destroy",
        ):
            monkeypatch.setattr(solver, method, lambda *a, **kw: None)
    return solver


@pytest.mark.parametrize("solver_cls", [solvers.ALNSSolver, solvers.HybridDDQNSolver])
@pytest.mark.parametrize("finish", [101.0, 102.0])
def test_initial_construction_at_or_after_cutoff_is_an_explicit_failure(case, monkeypatch, solver_cls, finish):
    solver = make_solver(case, monkeypatch, solver_cls)

    def build(*a, **kw):
        case.clock.now = finish
        return case.initial

    monkeypatch.setattr(solvers, "build_greedy", build)
    with pytest.raises(RuntimeError, match="no.*certified.*incumbent"):
        solver.solve(seed=42)
    assert solver.native_certification["status"] == "no_certified_incumbent"
    assert solver.native_certification["certificate"] is None
    assert solver.time_limit_hit
    assert solver.trajectory_log == []


@pytest.mark.parametrize("solver_cls", [solvers.ALNSSolver, solvers.HybridDDQNSolver])
@pytest.mark.parametrize("routes", [[[1, 2]], [[1, 2, 2]], [[1, 2, 3, 3]]])
def test_route_feasible_but_inexact_initial_plan_is_rejected(case, monkeypatch, solver_cls, routes):
    solver = make_solver(case, monkeypatch, solver_cls)
    initial = Plan(routes, case.inst)
    assert initial.feasible
    with pytest.raises(RuntimeError, match="no.*certified.*incumbent"):
        solver.solve(seed=42, init=initial)


@pytest.mark.parametrize("finish", [100.5, 101.0, 102.0])
def test_hybrid_tail_cannot_replace_certified_incumbent_with_late_routes(case, monkeypatch, finish):
    solver = make_solver(case, monkeypatch, solvers.HybridDDQNSolver)

    def polish(plan, *a, **kw):
        case.clock.now = finish
        # Simulate a helper mutating its input, including its cached objective.
        plan.routes[:] = [r[:] for r in case.better.routes]
        plan.invalidate()
        return plan

    monkeypatch.setattr(solver, "_fixed_nv_polish", polish)
    result, _ = solver.solve(seed=42, init=case.initial)
    expected = case.better if finish < 101 else case.initial
    assert result.routes == expected.routes
    cert = solver.native_certification["certificate"]
    assert cert["nv"] == result.nv and cert["td"] == pytest.approx(result.cost)
    assert cert["captured_sec"] < cert["cutoff_sec"] == 1.0
    assert (
        cert["routes_sha256"] == hashlib.sha256(json.dumps(result.routes, separators=(",", ":")).encode()).hexdigest()
    )
    assert all(p["t_sec"] < 1.0 for p in solver.trajectory_log)


@pytest.mark.parametrize("finish", [100.5, 101.0, 102.0])
def test_alns_search_retains_only_certified_improvements(case, monkeypatch, finish):
    solver = make_solver(case, monkeypatch, solvers.ALNSSolver, alns_iterations=1)
    monkeypatch.setattr(solver, "_destroy", lambda di, plan, size: (plan, []))

    def repair(*a, **kw):
        case.clock.now = finish
        return case.better

    monkeypatch.setattr(solvers, "REPAIR", [repair] * solvers.N_R)
    result, _ = solver.solve(seed=42, init=case.initial)
    assert result.routes == (case.better if finish < 101 else case.initial).routes
    assert solver.native_certification["certificate"]["captured_sec"] < 1


@pytest.fixture
def tracker(case):
    module = importlib.import_module("vrptw.native_certification")
    return module.NativeIncumbent(case.inst, start=100.0, deadline=101.0, clock=lambda: case.clock.now)


def test_certifier_ignores_plan_caches_and_owns_a_route_snapshot(case, tracker):
    case.initial._cost, case.initial._ok = -999.0, False
    assert tracker.consider(case.initial, phase="initial")
    expected = Plan([[1, 2, 3]], case.inst).cost
    case.initial.routes[0][:] = [1]
    result = tracker.finish()
    assert result.routes == [[1, 2, 3]] and result.cost == pytest.approx(expected)
    assert result.feasible
    assert tracker.diagnostics["certificate"]["clock"] == "perf_counter"


@pytest.mark.parametrize("defect", ["capacity", "window", "return", "service", "nan", "infinite", "foreign"])
def test_certifier_rechecks_original_feasibility_despite_stale_flags(case, tracker, defect):
    candidate = case.initial.copy()
    candidate._ok, candidate._cost = True, 0.0
    if defect == "capacity":
        case.inst.capacity = 2
    elif defect == "window":
        case.inst.due_times[2] = 0.5
    elif defect == "return":
        case.inst.due_times[0] = 4
    elif defect == "service":
        case.inst.service_times[2] = 100
    elif defect == "nan":
        case.inst.ready_times[2] = np.nan
    elif defect == "infinite":
        case.inst.dist[1, 2] = np.inf
    else:
        candidate.inst = Inst(
            {
                "name": "foreign",
                "capacity": 10,
                "data": np.column_stack([np.arange(4), np.zeros((4, 4)), np.full(4, 100), np.zeros(4)]),
            }
        )
    assert not tracker.consider(candidate, phase="test")
    with pytest.raises(RuntimeError, match="no.*certified.*incumbent"):
        tracker.finish()


@pytest.mark.parametrize("node", [0, -1, 4, 1.5, True, "1"])
def test_certifier_rejects_invalid_ids_without_truncation(case, tracker, node):
    candidate = Plan([[node, 2, 3]], case.inst)
    assert not tracker.consider(candidate, phase="test")


@pytest.mark.parametrize("stage", ["validation", "hash"])
@pytest.mark.parametrize("finish", [100.9999, 101.0, 102.0])
def test_full_validation_and_hash_must_finish_strictly_before_cutoff(case, tracker, monkeypatch, stage, finish):
    module = importlib.import_module("vrptw.native_certification")
    assert tracker.consider(case.initial, phase="initial")
    original = module.validate_routes if stage == "validation" else module.routes_sha256

    def delayed(*a, **kw):
        result = original(*a, **kw)
        case.clock.now = finish
        return result

    monkeypatch.setattr(module, "validate_routes" if stage == "validation" else "routes_sha256", delayed)
    assert tracker.consider(case.better, phase="tail") is (finish < 101)
    assert tracker.finish().routes == (case.better if finish < 101 else case.initial).routes


def test_certified_objective_is_fleet_first_and_worse_results_do_not_replace_it(case, tracker):
    assert tracker.consider(Plan([[1], [2, 3]], case.inst), phase="initial")
    assert tracker.consider(case.initial, phase="fleet_reduction")
    assert tracker.consider(case.better, phase="distance")
    assert not tracker.consider(case.initial, phase="worse")
    assert tracker.finish().routes == case.better.routes
    assert len(tracker.trajectory) == 3


@pytest.mark.parametrize("solver_cls", [solvers.ALNSSolver, solvers.HybridDDQNSolver])
def test_native_solver_rejects_candidate_whose_certification_crosses_cutoff(case, monkeypatch, solver_cls):
    module = importlib.import_module("vrptw.native_certification")
    validate = module.validate_routes
    solver = make_solver(case, monkeypatch, solver_cls, alns_iterations=1, hybrid_iterations=1)
    monkeypatch.setattr(solver, "_destroy", lambda di, plan, size: (plan, []))
    monkeypatch.setattr(solvers, "REPAIR", [lambda *a, **kw: case.better] * solvers.N_R)

    def delayed(routes, inst):
        cost = validate(routes, inst)
        if tuple(map(tuple, routes)) == tuple(map(tuple, case.better.routes)):
            case.clock.now = 101.0
        return cost

    monkeypatch.setattr(module, "validate_routes", delayed)
    result, _ = solver.solve(seed=42, init=case.initial)
    assert result.routes == case.initial.routes
    assert solver.native_certification["rejected_late"] > 0
    assert len(solver.trajectory_log) == 1


@pytest.mark.parametrize("solver_cls", [solvers.ALNSSolver, solvers.HybridDDQNSolver])
def test_inference_and_derived_budget_are_inside_certification_interval(case, monkeypatch, solver_cls):
    import torch

    from vrptw import gnn

    solver = make_solver(case, monkeypatch, solver_cls, time_limit=None, time_limit_per_customer=0.25)

    class Model:
        def eval(self):
            pass

        def __call__(self, *args):
            case.clock.now += 0.75  # Exactly the complete 3-customer budget.
            return torch.zeros((1, 4, 4))

    solver.gnn_model = Model()
    monkeypatch.setattr(gnn, "get_gnn_features", lambda _: (torch.zeros(1),) * 3)
    monkeypatch.setattr(solvers, "build_greedy", lambda *a, **kw: case.initial)
    with pytest.raises(RuntimeError, match="no.*certified.*incumbent"):
        solver.solve(seed=42)
    assert solver.native_certification["cutoff_sec"] == 0.75


@pytest.mark.parametrize("finish", [100.6, 101.2])
@pytest.mark.parametrize("child_failure", [False, True])
@pytest.mark.parametrize("child_improvement", [False, True])
def test_split_reconcile_keeps_parent_certificate_clock_and_fallback(
    case, monkeypatch, finish, child_failure, child_improvement
):
    module = importlib.import_module("vrptw.native_certification")
    data = np.zeros((201, 7))
    data[:, 0], data[:, 1], data[:, 5] = np.arange(201), np.arange(201) / 100, 1000
    data[1:, 3] = 1
    case.inst = Inst({"name": "split_certificate", "capacity": 200, "data": data})
    initial = Plan([[3, 2, 1, *range(4, 101)], list(range(101, 201))], case.inst)
    solver = make_solver(case, monkeypatch, solvers.HybridDDQNSolver, split_enabled=True)
    monkeypatch.setattr(solver, "_split_routes_gnn_guided", lambda _: ([0], [1]))
    calls = []

    class Child:
        def __init__(self, inst, cfg):
            self.inst = inst

        def solve(self, *, init, _deadline, **kw):
            calls.append(_deadline)
            case.clock.now = 100.2 if len(calls) == 1 else finish
            if child_failure:
                raise module.NativeNoSolutionError("child cutoff")
            return (Plan([sorted(r) for r in init.routes], self.inst) if child_improvement else init), []

    monkeypatch.setattr(solvers, "HybridDDQNSolver", Child)
    result, _ = solver.solve(seed=42, init=initial)
    improved = child_improvement and not child_failure and finish < 101
    assert result.routes == ([sorted(r) for r in initial.routes] if improved else initial.routes)
    assert len(calls) == 2
    assert calls[0] == pytest.approx(100 + 1 / 3)
    assert calls[1] == pytest.approx(100.6)
    assert solver._t_start == 100.0
    assert solver.native_certification["cutoff_sec"] == 1.0
    assert solver.native_certification["certificate"]["captured_sec"] == pytest.approx(0.6 if improved else 0.0)
    assert solver.native_certification["elapsed_sec"] == pytest.approx(finish - 100)
    assert len(solver.trajectory_log) == (2 if improved else 1)


def test_fixed_nv_helper_saves_internal_improvement_before_a_later_overrun(case, monkeypatch):
    solver = make_solver(case, monkeypatch, solvers.HybridDDQNSolver)
    monkeypatch.setattr(solver, "_fixed_nv_polish", solvers.HybridDDQNSolver._fixed_nv_polish.__get__(solver))

    def ls(*a, **kw):
        case.clock.now = 100.2
        return case.better

    def destroy(di, plan, size):
        case.clock.now = 102
        return plan, []

    monkeypatch.setattr(solver, "_local_search", ls)
    monkeypatch.setattr(solver, "_destroy", destroy)
    result, _ = solver.solve(seed=42, init=case.initial)
    assert result.routes == case.better.routes
    assert solver.native_certification["certificate"]["phase"] == "fixed_nv_polish"
    assert solver.native_certification["certificate"]["captured_sec"] == pytest.approx(0.2)


def test_committed_helper_saves_internal_improvement_before_its_caller_returns_late(case, monkeypatch):
    solver = make_solver(case, monkeypatch, solvers.HybridDDQNSolver, penalty_search_enabled=False)
    initial = Plan([[1], [2, 3]], case.inst)
    monkeypatch.setattr(solver, "_destroy", lambda di, plan, size: (plan, []))

    def repair(*a, **kw):
        case.clock.now = 100.2
        return case.better

    def polish(plan, pool, **kw):
        reduced = solver._committed_nv_search(plan, pool, target_nv=1)
        case.clock.now = 102
        return reduced

    monkeypatch.setattr(solvers, "REPAIR", [repair] * solvers.N_R)
    monkeypatch.setattr(solver, "_fixed_nv_polish", polish)
    result, _ = solver.solve(seed=42, init=initial)
    assert result.routes == case.better.routes
    assert solver.native_certification["certificate"]["phase"] == "committed_nv_search"
    assert solver.native_certification["certificate"]["captured_sec"] == pytest.approx(0.2)


@pytest.mark.parametrize("solver_cls", [solvers.ALNSSolver, solvers.HybridDDQNSolver])
def test_certification_resets_between_independent_solves_and_supports_unbounded_mode(case, monkeypatch, solver_cls):
    solver = make_solver(case, monkeypatch, solver_cls, time_limit=None, time_limit_per_customer=0)
    result, _ = solver.solve(seed=42, init=case.better)
    assert result.routes == case.better.routes
    assert solver.native_certification["certificate"]["cutoff_sec"] is None
    result, _ = solver.solve(seed=43, init=case.initial)
    assert result.routes == case.initial.routes
    assert len(solver.trajectory_log) == 1


@pytest.mark.parametrize("failure", [False, True])
def test_cli_exports_native_certification_on_success_and_failure(case, monkeypatch, tmp_path, failure):
    spec = importlib.util.spec_from_file_location(
        "certification_cli", Path(__file__).resolve().parents[1] / "scripts/benchmark.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    input_path, output = tmp_path / "input.txt", tmp_path / "result.json"
    input_path.write_text("fixture")
    solver = make_solver(case, monkeypatch, solvers.ALNSSolver)
    if failure:

        def build(*a, **kw):
            case.clock.now += 2
            return case.initial

        monkeypatch.setattr(solvers, "build_greedy", build)
    else:
        monkeypatch.setattr(solvers, "build_greedy", lambda *a, **kw: case.initial)
    monkeypatch.setattr(cli, "get_env_info", lambda: {})
    monkeypatch.setattr(cli, "load_solomon_instance", lambda _: case.inst)
    monkeypatch.setattr(cli, "get_solver_and_config", lambda *a, **kw: (lambda inst, cfg: solver, solver.cfg))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark",
            "--instance",
            str(input_path),
            "--ablation",
            "alns",
            "--time-limit",
            "1",
            "--output-json",
            str(output),
        ],
    )
    assert cli.main() == int(failure)
    payload = json.loads(output.read_text())
    assert payload["native_certification"] == solver.native_certification
    assert payload["native_certification"]["status"] == ("no_certified_incumbent" if failure else "certified")
    assert payload["feasible"] is not failure
