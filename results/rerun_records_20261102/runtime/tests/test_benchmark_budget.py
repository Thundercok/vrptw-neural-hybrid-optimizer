from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from vrptw import Config, Inst, operators, solvers
from vrptw import pool as route_pool
from vrptw.core import Plan

local_search_module = importlib.import_module("vrptw.local_search")

_SPEC = importlib.util.spec_from_file_location(
    "benchmark_cli", Path(__file__).resolve().parents[1] / "scripts" / "benchmark.py"
)
benchmark_cli = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(benchmark_cli)


def tiny_instance():
    data = np.zeros((5, 7), dtype=np.float64)
    data[:, 0] = np.arange(5)
    data[:, 1] = np.arange(5) * 2
    data[1:, 3] = 1
    data[:, 5] = 500
    return Inst({"name": "budget_test", "capacity": 100.0, "data": data})


@pytest.mark.parametrize("solver_cls", [solvers.ALNSSolver, solvers.HybridDDQNSolver])
@pytest.mark.parametrize("wall_clock_only", [False, True])
@pytest.mark.parametrize("iteration_cap", [1, 8])
def test_wall_clock_search_ignores_iteration_cap_and_patience(monkeypatch, solver_cls, wall_clock_only, iteration_cap):
    cfg = Config(
        alns_iterations=iteration_cap,
        hybrid_iterations=iteration_cap,
        early_stop_patience=1,
        time_limit=0.1,
        time_limit_main_loop_frac=1.0,
        wall_clock_only=wall_clock_only,
        adaptive_feasibility=False,
        macro_enabled=False,
        recombine_after_main_search=False,
        recombine_after_polish=False,
    )
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(solvers, "time", SimpleNamespace(perf_counter=lambda: clock.now))
    monkeypatch.setattr(solvers, "REPAIR", [lambda plan, removed, **kwargs: plan] * solvers.N_R)
    solver = solver_cls(tiny_instance(), cfg)

    def destroy(di, plan, size):
        clock.now += 0.025
        return plan, []

    monkeypatch.setattr(solver, "_destroy", destroy)
    if isinstance(solver, solvers.HybridDDQNSolver):
        solver.use_op_rl = False
        monkeypatch.setattr(solver, "_select_action", lambda *args: (0, False))
        monkeypatch.setattr(solver, "_local_search", lambda plan, **kwargs: plan)
        monkeypatch.setattr(solver, "_fixed_nv_polish", lambda plan, *args, **kwargs: plan)
        for method in (
            "_generate_dense_pool_columns",
            "_seed_savings_routes",
            "_seed_nv_targeted_construction",
            "_seed_pool_large_destroy",
        ):
            monkeypatch.setattr(solver, method, lambda *args, **kwargs: None)
    plan, _ = solver.solve(seed=42)
    assert plan.feasible
    # The fourth destroy reaches the deadline; its repair must never start and
    # that incomplete iteration must not be counted as completed search.
    assert solver.search_iterations == (3 if wall_clock_only else 1)
    assert solver.time_limit_hit is wall_clock_only


def test_wall_clock_mode_requires_a_finite_deadline():
    with pytest.raises(ValueError, match="wall_clock_only"):
        Config(wall_clock_only=True, time_limit_per_customer=0.0)
    with pytest.raises(ValueError, match="finite"):
        Config(time_limit=float("inf"))


def test_alns_does_not_report_neural_components():
    solver = solvers.ALNSSolver(tiny_instance(), Config())
    components = benchmark_cli.extract_instrumentation(solver, solver.cfg, "alns")["resolved_components"]
    for name in ("macro_ddqn", "micro_ddqn", "policy_gate", "lac", "gnn_edge_guidance", "route_pool", "gec"):
        assert components[name] is False, name


def test_gnn_flag_requires_a_loaded_model():
    solver = solvers.HybridDDQNSolver(tiny_instance(), Config(gnn_model_path="not-loaded.pt"))
    assert not benchmark_cli.extract_instrumentation(solver, solver.cfg, "full")["resolved_components"][
        "gnn_edge_guidance"
    ]


def test_cli_config_is_seeded_before_network_initialization():
    _, cfg = benchmark_cli.get_solver_and_config("full_no_gnn", 10, seed=47)
    assert cfg.seed == 47
    assert cfg.wall_clock_only


@pytest.mark.parametrize("routes, expected", [([[1, 2, 3, 4]], True), ([[1, 2, 3]], False), ([[1, 2, 3, 3]], False)])
def test_exact_cover_is_checked_separately_from_route_feasibility(routes, expected):
    plan = Plan(routes, tiny_instance())
    assert plan.feasible
    assert benchmark_cli.has_exact_cover(plan) is expected


@pytest.mark.parametrize(
    "method",
    [
        "_seed_savings_routes",
        "_seed_nv_targeted_construction",
        "_seed_pool_large_destroy",
        "_generate_dense_pool_columns",
    ],
)
def test_pool_seeding_does_no_work_after_deadline(monkeypatch, method):
    solver = solvers.HybridDDQNSolver(tiny_instance(), Config())
    monkeypatch.setattr(solver, "_out_of_time", lambda: True)
    pool = SimpleNamespace(
        add_route=lambda *args, **kwargs: pytest.fail("seeding after deadline"),
        add_plan=lambda *args, **kwargs: pytest.fail("seeding after deadline"),
    )
    plan = Plan([[1, 2, 3, 4]], solver.inst)
    if method == "_seed_nv_targeted_construction":
        getattr(solver, method)(pool, target_nv=1)
    elif method == "_seed_savings_routes":
        getattr(solver, method)(pool)
    else:
        getattr(solver, method)(plan, pool)


def test_milp_fallback_shares_remaining_budget(monkeypatch):
    inst = tiny_instance()
    cfg = Config(sp_time_limit=4.0)
    pool = route_pool.RoutePool(inst, cfg)
    plan = Plan([[1, 2, 3, 4]], inst)
    pool.add_plan(plan)
    clock = SimpleNamespace(now=100.0)
    limits = []
    monkeypatch.setattr(route_pool, "time", SimpleNamespace(perf_counter=lambda: clock.now))

    def milp(**kwargs):
        limits.append(kwargs["options"]["time_limit"])
        clock.now += 0.7
        return SimpleNamespace(x=None, status=1)

    monkeypatch.setattr(route_pool, "milp", milp)
    route_pool._milp_recombine(pool.records(plan), inst, cfg, deadline=101.0)
    assert limits == pytest.approx([1.0, 0.3])


def test_local_search_checks_deadline_between_neighborhoods(monkeypatch):
    plan = Plan([[1, 2, 3, 4]], tiny_instance())
    clock = SimpleNamespace(now=100.0)
    monkeypatch.setattr(local_search_module, "time", SimpleNamespace(perf_counter=lambda: clock.now))
    monkeypatch.setattr(local_search_module, "_two_opt_best", lambda route, inst, **kw: route)

    def relocate(*args, **kwargs):
        clock.now = 102.0
        return None

    monkeypatch.setattr(local_search_module, "_best_relocate", relocate)
    monkeypatch.setattr(local_search_module, "_best_or_opt", lambda *a, **kw: pytest.fail("started after deadline"))
    result = local_search_module.local_search(plan, deadline=101.0)
    assert result.feasible
    assert result.routes == plan.routes


def test_recombination_passes_deadline_to_local_search(monkeypatch):
    inst = tiny_instance()
    cfg = Config()
    plan = Plan([[1, 2, 3, 4]], inst)
    pool = route_pool.RoutePool(inst, cfg)
    monkeypatch.setattr(route_pool, "time", SimpleNamespace(perf_counter=lambda: 100.0))
    monkeypatch.setattr(route_pool, "_milp_recombine", lambda *a, **kw: plan.copy())
    deadlines = []

    def search(candidate, **kwargs):
        deadlines.append(kwargs.get("deadline"))
        return candidate

    monkeypatch.setattr(local_search_module, "local_search", search)
    route_pool.recombine_with_route_pool(plan, pool, cfg, nv_ceiling=1, deadline=101.0)
    assert deadlines == [101.0]


def test_alns_does_not_start_repair_after_destroy_expires(monkeypatch):
    inst = tiny_instance()
    initial = Plan([[1, 2, 3, 4]], inst)
    solver = solvers.ALNSSolver(inst, Config(time_limit=0.1, wall_clock_only=True))
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(solvers, "time", SimpleNamespace(perf_counter=lambda: clock.now))

    def destroy(*args):
        clock.now = 0.2
        return Plan([[1, 2, 3]], inst), [4]

    monkeypatch.setattr(solver, "_destroy", destroy)
    monkeypatch.setattr(solvers, "REPAIR", [lambda *a, **kw: pytest.fail("late repair")] * solvers.N_R)
    result, _ = solver.solve(seed=42, init=initial)
    assert result.routes == initial.routes
    assert solver.time_limit_hit


def test_alns_does_not_accept_a_late_candidate(monkeypatch):
    inst = tiny_instance()
    initial = Plan([[1], [2], [3], [4]], inst)
    solver = solvers.ALNSSolver(inst, Config(time_limit=0.1, wall_clock_only=True))
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(solvers, "time", SimpleNamespace(perf_counter=lambda: clock.now))
    monkeypatch.setattr(solver, "_destroy", lambda di, plan, size: (plan, []))

    def repair(*args, **kwargs):
        clock.now = 0.2
        return Plan([[1, 2, 3, 4]], inst)

    monkeypatch.setattr(solvers, "REPAIR", [repair] * solvers.N_R)
    result, _ = solver.solve(seed=42, init=initial)
    assert result.routes == initial.routes
    assert solver.time_limit_hit


def test_fixed_nv_polish_stops_between_destroy_and_repair(monkeypatch):
    solver = solvers.HybridDDQNSolver(tiny_instance(), Config())
    solver.gamma = 0.0
    solver._deadline = 0.1
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(solvers, "time", SimpleNamespace(perf_counter=lambda: clock.now))
    monkeypatch.setattr(solver, "_local_search", lambda plan, **kwargs: plan)

    def destroy(di, plan, size):
        clock.now = 0.2
        return plan, []

    monkeypatch.setattr(solver, "_destroy", destroy)
    monkeypatch.setattr(solvers, "REPAIR", [lambda *a, **kw: pytest.fail("late polish repair")] * solvers.N_R)
    initial = Plan([[1, 2, 3, 4]], solver.inst)
    pool = SimpleNamespace(add_plan=lambda *args: None)
    result = solver._fixed_nv_polish(initial, pool)
    assert result.routes == initial.routes
    assert solver.time_limit_hit


@pytest.mark.parametrize("repair", operators.REPAIR, ids=lambda fn: fn.__name__)
def test_repair_returns_no_partial_plan_after_deadline(monkeypatch, repair):
    monkeypatch.setattr(operators, "time", SimpleNamespace(perf_counter=lambda: 100.0), raising=False)
    partial = Plan([[1, 2]], tiny_instance())
    assert repair(partial, [3, 4], deadline=99.0) is None


def test_neural_shaw_does_no_work_after_deadline(monkeypatch):
    monkeypatch.setattr(operators, "time", SimpleNamespace(perf_counter=lambda: 100.0), raising=False)
    plan = Plan([[1, 2, 3, 4]], tiny_instance())
    candidate, removed = operators.op_neural_shaw(plan.copy(), 3, np.ones((5, 5)), deadline=99.0)
    assert candidate.routes == plan.routes
    assert removed == []


def test_or_opt_stops_between_route_pair_kernels(monkeypatch):
    plan = Plan([[1], [2], [3], [4]], tiny_instance())
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(local_search_module, "time", SimpleNamespace(perf_counter=lambda: clock.now))
    calls = []

    def kernel(*args):
        calls.append(1)
        clock.now = 2.0
        return 0.0, -1, 0, 0, 0, False

    monkeypatch.setattr(local_search_module, "_string_relocate_pair_numba", kernel)
    assert local_search_module._best_or_opt(plan, deadline=1.0) is None
    assert len(calls) == 1


@pytest.mark.parametrize("search_name", ["local_search", "td_inter_route_polish"])
def test_local_search_discards_a_neighborhood_result_completed_late(monkeypatch, search_name):
    plan = Plan([[1, 2, 3, 4]], tiny_instance())
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(local_search_module, "time", SimpleNamespace(perf_counter=lambda: clock.now))
    monkeypatch.setattr(local_search_module, "_two_opt_best", lambda route, inst, **kw: route)

    def relocate(*args, **kwargs):
        clock.now = 2.0
        return (0, 0, 0, 0), -1.0

    monkeypatch.setattr(local_search_module, "_best_relocate", relocate)
    monkeypatch.setattr(local_search_module, "_apply_relocate", lambda *a: pytest.fail("accepted late move"))
    result = getattr(local_search_module, search_name)(plan, deadline=1.0)
    assert result.routes == plan.routes


@pytest.mark.parametrize("name", ["merged_route_candidates", "_try_route_merge", "_build_merged_route"])
def test_merge_helpers_do_not_start_after_deadline(monkeypatch, name):
    monkeypatch.setattr(local_search_module, "time", SimpleNamespace(perf_counter=lambda: 100.0))
    inst = tiny_instance()
    args = ([1, 2], inst) if name == "_build_merged_route" else (Plan([[1, 2], [3, 4]], inst),)
    result = getattr(local_search_module, name)(*args, deadline=99.0)
    assert result == ([] if name == "merged_route_candidates" else None)


def test_local_search_does_not_eagerly_seed_merged_routes_after_deadline(monkeypatch):
    plan = Plan([[1, 2, 3, 4]], tiny_instance())
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(local_search_module, "time", SimpleNamespace(perf_counter=lambda: clock.now))

    def two_opt(route, inst, **kw):
        clock.now = 2.0
        return route

    monkeypatch.setattr(local_search_module, "_two_opt_best", two_opt)
    monkeypatch.setattr(local_search_module, "merged_route_candidates", lambda *a, **kw: pytest.fail("late seeding"))
    pool = SimpleNamespace(add_route=lambda *a: pytest.fail("late pool update"))
    result = local_search_module.local_search(plan, max_ls_moves=0, pool=pool, deadline=1.0)
    assert result.routes == plan.routes


@pytest.mark.parametrize("repair", operators.REPAIR, ids=lambda fn: fn.__name__)
def test_repair_can_cancel_after_partial_insertion(monkeypatch, repair):
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(operators, "time", SimpleNamespace(perf_counter=lambda: clock.now))

    def column(nodes, *args):
        clock.now = 2.0
        return np.zeros(len(nodes)), np.zeros(len(nodes)), np.zeros(len(nodes), dtype=np.int64)

    def fts(*args):
        clock.now = 2.0
        return 0.0, 0

    monkeypatch.setattr(operators, "_insert_costs_column_numba", column)
    monkeypatch.setattr(operators, "_fts_best_insert_position", fts)
    partial = Plan([[1, 2]], tiny_instance())
    assert repair(partial, [3, 4], deadline=1.0) is None
    assert clock.now == 2.0


@pytest.mark.parametrize("repair", operators.REPAIR, ids=lambda fn: fn.__name__)
def test_nonexpired_repair_matches_unbounded_behavior(monkeypatch, repair):
    monkeypatch.setattr(operators, "time", SimpleNamespace(perf_counter=lambda: 0.0))
    partial = Plan([[1, 2]], tiny_instance())
    expected = repair(partial.copy(), [3, 4])
    result = repair(partial.copy(), [3, 4], deadline=100.0)
    assert result.routes == expected.routes
    assert result.cost == expected.cost
    assert sorted(node for route in result.routes for node in route) == [1, 2, 3, 4]


@pytest.mark.parametrize("search_name", ["local_search", "td_inter_route_polish"])
def test_neighborhood_does_not_start_if_cache_build_expires(monkeypatch, search_name):
    plan = Plan([[1, 2, 3, 4]], tiny_instance())
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(local_search_module, "time", SimpleNamespace(perf_counter=lambda: clock.now))
    monkeypatch.setattr(local_search_module, "_two_opt_best", lambda route, inst, **kw: route)

    def cache(*args, **kwargs):
        clock.now = 2.0
        return None

    monkeypatch.setattr(local_search_module, "_PlanCache", SimpleNamespace(from_plan=cache))
    monkeypatch.setattr(local_search_module, "_best_relocate", lambda *a, **kw: pytest.fail("late neighborhood"))
    result = getattr(local_search_module, search_name)(plan, deadline=1.0)
    assert result.routes == plan.routes


@pytest.mark.parametrize("solver_cls", [solvers.ALNSSolver, solvers.HybridDDQNSolver])
@pytest.mark.parametrize("epoch_jump", [-3600.0, 0.0, 3600.0])
def test_native_budget_ignores_calendar_clock_changes(monkeypatch, solver_cls, epoch_jump):
    clock = SimpleNamespace(now=0.0, wall=1000.0, destroys=0)
    fake_time = SimpleNamespace(time=lambda: clock.wall, perf_counter=lambda: clock.now)
    for module in (solvers, route_pool, operators, local_search_module):
        monkeypatch.setattr(module, "time", fake_time)
    cfg = Config(
        time_limit=0.1,
        wall_clock_only=True,
        time_limit_main_loop_frac=1.0,
        adaptive_feasibility=False,
        macro_enabled=False,
        recombine_after_main_search=False,
        recombine_after_polish=False,
    )
    solver = solver_cls(tiny_instance(), cfg)
    monkeypatch.setattr(solvers, "REPAIR", [lambda plan, removed, **kwargs: plan] * solvers.N_R)

    def destroy(di, plan, size):
        clock.destroys += 1
        assert clock.destroys <= 5, "calendar clock prevented budget expiry"
        clock.now += 0.025
        clock.wall = 1000.0 + epoch_jump
        return plan, []

    monkeypatch.setattr(solver, "_destroy", destroy)
    if isinstance(solver, solvers.HybridDDQNSolver):
        solver.use_op_rl = False
        monkeypatch.setattr(solver, "_select_action", lambda *args: (0, False))
        monkeypatch.setattr(solver, "_local_search", lambda plan, **kwargs: plan)
        monkeypatch.setattr(solver, "_fixed_nv_polish", lambda plan, *args, **kwargs: plan)
        for method in (
            "_generate_dense_pool_columns",
            "_seed_savings_routes",
            "_seed_nv_targeted_construction",
            "_seed_pool_large_destroy",
        ):
            monkeypatch.setattr(solver, method, lambda *args, **kwargs: None)
    initial = Plan([[1, 2, 3, 4]], solver.inst)
    result, _ = solver.solve(seed=42, init=initial)
    assert result.routes == initial.routes
    assert solver.search_iterations == 3 and clock.destroys == 4 and solver.time_limit_hit
    assert all(0 <= point["t_sec"] <= clock.now for point in solver.trajectory_log)


@pytest.mark.parametrize("repair", operators.REPAIR, ids=lambda fn: fn.__name__)
def test_repair_deadline_uses_elapsed_clock_not_epoch(monkeypatch, repair):
    monkeypatch.setattr(operators, "time", SimpleNamespace(time=lambda: -1000.0, perf_counter=lambda: 2.0))
    assert repair(Plan([[1, 2]], tiny_instance()), [3, 4], deadline=1.0) is None


def test_pool_deadline_uses_elapsed_clock_not_epoch(monkeypatch):
    monkeypatch.setattr(route_pool, "time", SimpleNamespace(time=lambda: -1000.0, perf_counter=lambda: 2.0))
    plan = Plan([[1, 2, 3, 4]], tiny_instance())
    pool = SimpleNamespace(add_plan=lambda *a: pytest.fail("pool work after monotonic deadline"))
    result = route_pool.recombine_with_route_pool(plan, pool, Config(), deadline=1.0)
    assert result.routes == plan.routes


def test_local_search_deadline_uses_elapsed_clock_not_epoch(monkeypatch):
    monkeypatch.setattr(local_search_module, "time", SimpleNamespace(time=lambda: -1000.0, perf_counter=lambda: 2.0))
    monkeypatch.setattr(local_search_module, "_two_opt_best", lambda *a: pytest.fail("search after monotonic deadline"))
    plan = Plan([[1, 2, 3, 4]], tiny_instance())
    assert local_search_module.local_search(plan, deadline=1.0).routes == plan.routes
