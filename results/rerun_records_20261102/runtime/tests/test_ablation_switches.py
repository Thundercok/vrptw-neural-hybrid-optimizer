"""Disabled SP/split cannot leak through secondary search paths."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest

from vrptw import Config, Inst, solvers
from vrptw import pool as pool_module
from vrptw.core import Plan
from vrptw.split_controller import SplitController

ROOT = Path(__file__).resolve().parents[1]
MODES = [{}, {"nv_ceiling": 2}, {"nv_target": 1}, {"td_only": True, "nv_ceiling": 2}]


@pytest.fixture
def case():
    data = np.zeros((5, 7), dtype=np.float64)
    data[:, 0] = np.arange(5)
    data[:, 1:3] = [(0, 0), (1, 0), (2, 0), (0, 1), (0, 2)]
    data[1:, 3], data[:, 5] = 1, 1000
    inst = Inst({"name": "switch_contract_toy", "capacity": 10.0, "data": data})
    return inst, Plan([[1, 2], [3, 4]], inst)


def config(**changes):
    options = dict(
        hybrid_iterations=3,
        adaptive_feasibility=False,
        macro_enabled=False,
        split_enabled=False,
        lac_enabled=False,
        per_beta_auto_scale=False,
        pool_recombine_enabled=False,
        recombine_after_main_search=True,
        recombine_after_polish=True,
        recombine_interval=1,
        rl_recombine_min_routes=1,
        time_limit_per_customer=0.0,
    )
    options.update(changes)
    return Config(**options)


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("mode", MODES)
def test_public_recombination_obeys_global_flag_before_pool_access(monkeypatch, case, enabled, mode):
    inst, plan = case
    cfg = config(pool_recombine_enabled=enabled)
    pool = pool_module.RoutePool(inst, cfg)
    add = Mock(wraps=pool.add_plan)
    records = Mock(wraps=pool.records)
    monkeypatch.setattr(pool, "add_plan", add)
    monkeypatch.setattr(pool, "records", records)
    milp = Mock(return_value=plan)
    greedy = Mock(return_value=plan)
    monkeypatch.setattr(pool_module, "_milp_recombine", milp)
    monkeypatch.setattr(pool_module, "_greedy_recombine", greedy)
    local = importlib.import_module("vrptw.local_search")
    monkeypatch.setattr(local, "local_search", lambda p, **kw: p)
    stats = {"calls": 0}
    result = pool_module.recombine_with_route_pool(plan, pool, cfg, _stats=stats, **mode)
    assert result.routes == plan.routes and plan.feasible
    if enabled:
        add.assert_called_once_with(plan)
        assert milp.call_count > 0
    else:
        assert result is plan
        add.assert_not_called()
        records.assert_not_called()
        milp.assert_not_called()
        greedy.assert_not_called()
        assert not pool._routes and not pool._milp_cache and stats == {"calls": 0}


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("mode", MODES)
def test_hybrid_dispatcher_obeys_global_flag(monkeypatch, case, enabled, mode):
    inst, plan = case
    solver = object.__new__(solvers.HybridDDQNSolver)
    cfg = config(pool_recombine_enabled=enabled)
    solver._deadline = 123.0
    pool = pool_module.RoutePool(inst, cfg)
    dispatch = Mock(return_value=plan)
    monkeypatch.setattr(solvers, "recombine_with_route_pool", dispatch)
    assert solver._recombine_with_pool(plan, pool, cfg, **mode) is plan
    if enabled:
        dispatch.assert_called_once_with(plan, pool, cfg, deadline=123.0, **mode)
    else:
        dispatch.assert_not_called()


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("helper", ["dense", "savings", "targeted", "destroy"])
def test_sp_specific_seeding_is_disabled_without_pool_or_rng_work(monkeypatch, case, enabled, helper):
    inst, plan = case
    solver = object.__new__(solvers.HybridDDQNSolver)
    solver.cfg, solver.inst = config(pool_recombine_enabled=enabled), inst
    solver._deadline = None
    solver._destroy = Mock(return_value=(plan.copy(), []))
    monkeypatch.setattr(solvers, "REPAIR", [lambda *a, **kw: plan] * solvers.N_R)
    monkeypatch.setattr(solvers, "merged_route_candidates", lambda *a, **kw: [])
    monkeypatch.setattr(solvers, "_try_route_merge", lambda *a, **kw: None)
    pool = Mock()
    before_rng = solvers.random.getstate()
    if helper == "dense":
        solver._generate_dense_pool_columns(plan, pool)
    elif helper == "savings":
        solver._seed_savings_routes(pool, n_randomizations=1)
    elif helper == "targeted":
        solver._seed_nv_targeted_construction(pool, target_nv=1, n_trials=1)
    else:
        solver._seed_pool_large_destroy(plan, pool, n_seeds=1)
    if enabled:
        assert pool.add_route.call_count > 0
    else:
        assert pool.mock_calls == [] and solvers.random.getstate() == before_rng
        solver._destroy.assert_not_called()


def lightweight_solver(monkeypatch, case, **changes):
    inst, plan = case
    solver = solvers.RuleMicroHybridSolver(inst, config(**changes))
    monkeypatch.setattr(solver, "_select_action", lambda *a: (0, False))
    monkeypatch.setattr(solver, "_rule_micro_select", lambda *a: (0, 0))
    monkeypatch.setattr(solver, "_destroy", lambda di, p, size: (p, []))
    monkeypatch.setattr(solvers, "REPAIR", [lambda p, *a, **kw: p] * solvers.N_R)
    monkeypatch.setattr(solver, "_refine_candidate", lambda p, *a: p)
    monkeypatch.setattr(solver, "_local_search", lambda p, **kw: p)
    monkeypatch.setattr(solver, "_fixed_nv_polish", lambda p, *a, **kw: p)
    monkeypatch.setattr(solver, "_try_gec_route_reduction", lambda *a: None)
    monkeypatch.setattr(solver.ls_budget, "should_trigger", lambda *a: False)
    monkeypatch.setattr(solvers, "_try_route_merge", lambda *a, **kw: None)
    monkeypatch.setattr(solvers, "merged_route_candidates", lambda *a, **kw: [])
    monkeypatch.setattr(solvers, "_ejection_chain_eliminate", lambda *a, **kw: None)
    monkeypatch.setattr(solvers, "_buffered_route_elimination", lambda p, **kw: p)
    monkeypatch.setattr(solvers, "_iterative_route_elimination", lambda p, *a, **kw: p)
    monkeypatch.setattr(solvers, "td_converge_polish", lambda p, **kw: p)
    monkeypatch.setattr(solvers, "td_inter_route_polish", lambda p, **kw: p)
    monkeypatch.setattr(solvers, "recombine_with_route_pool", lambda p, *a, **kw: p)
    local = importlib.import_module("vrptw.local_search")
    monkeypatch.setattr(local, "_buffered_route_elimination", lambda p, **kw: p)
    return solver, plan


@pytest.mark.parametrize("enabled", [False, True])
def test_committed_search_restarts_and_inner_recombination_obey_switch(monkeypatch, case, enabled):
    solver, plan = lightweight_solver(monkeypatch, case, pool_recombine_enabled=enabled, hybrid_iterations=16)
    solver.heatmap = None
    pool = pool_module.RoutePool(solver.inst, solver.cfg)
    backend = Mock(side_effect=lambda p, *a, **kw: p)
    monkeypatch.setattr(solvers, "recombine_with_route_pool", backend)
    assert solver._committed_nv_search(plan, pool, target_nv=1, n_iters=500) is None
    if enabled:
        assert any(c.kwargs.get("nv_target") == 1 for c in backend.call_args_list)
        assert any(c.kwargs.get("nv_ceiling") == 2 for c in backend.call_args_list)
    else:
        backend.assert_not_called()


@pytest.mark.parametrize("enabled", [False, True])
def test_real_main_and_tail_paths_obey_sp_switch(monkeypatch, case, enabled):
    solver, plan = lightweight_solver(monkeypatch, case, pool_recombine_enabled=enabled, hybrid_iterations=16)
    # Keep committed search separate so its own regression proves both restart and inner paths.
    monkeypatch.setattr(solver, "_committed_nv_search", lambda *a, **kw: None)
    dispatches = []

    def backend(p, *a, **kw):
        dispatches.append((solver.search_iterations, kw))
        return p

    monkeypatch.setattr(solvers, "recombine_with_route_pool", backend)
    result, _ = solver.solve(seed=42, init=plan)
    assert solver.search_iterations == 16 and result.routes == plan.routes and result.feasible
    if enabled:
        assert any(it < 16 for it, _ in dispatches)  # periodic main-loop query
        tail = [kw for it, kw in dispatches if it == 16]
        assert any(kw.get("nv_target") == 1 for kw in tail)
        assert sum(bool(kw.get("td_only")) for kw in tail) >= 2
    else:
        assert dispatches == [] and solver.sp_stats["calls"] == 0


@pytest.mark.parametrize("enabled,frozen", [(False, False), (True, False), (True, True)])
def test_real_main_and_final_split_calls_obey_switch_and_frozen(monkeypatch, case, enabled, frozen):
    solver, plan = lightweight_solver(
        monkeypatch, case, split_enabled=enabled, split_trigger_after=0, split_trigger_interval=1
    )
    controller = Mock()
    controller.try_split.return_value = None
    module = importlib.import_module("vrptw.split_controller")
    monkeypatch.setattr(module, "SplitController", lambda *a, **kw: controller)
    result, _ = solver.solve(seed=42, init=plan, frozen=frozen)
    assert result.routes == plan.routes and solver.search_iterations == 3
    assert controller.try_split.call_count == (3 if enabled and not frozen else 0)


@pytest.mark.parametrize("enabled", [False, True])
def test_direct_split_stops_before_episode_replay_or_training(monkeypatch, case, enabled):
    inst, plan = case
    controller = SplitController(config(split_enabled=enabled), inst)
    transition = dict(state=np.zeros(18), action=0, reward=0.0, next_state=np.zeros(18), done=1.0, is_forced=False)
    episode = Mock(return_value=([[1, 2, 3, 4]], [transition]))
    train = Mock()
    monkeypatch.setattr(controller, "_run_episode", episode)
    monkeypatch.setattr(controller, "train_step", train)
    weights = {k: v.clone() for k, v in controller.q.state_dict().items()}
    result = controller.try_split(plan, plan.nv)
    if enabled:
        episode.assert_called_once()
        train.assert_called_once_with()
        assert len(controller.buf) == 1 and result is not None and result.nv == 1
    else:
        assert result is None and len(controller.buf) == 0 and controller.step == 0
        episode.assert_not_called()
        train.assert_not_called()
        assert all((v == weights[k]).all() for k, v in controller.q.state_dict().items())


@pytest.mark.parametrize("branch", ["full", "full_no_pool"])
def test_cli_explicit_sp_binding_and_effective_metadata(case, branch):
    spec = importlib.util.spec_from_file_location("switch_cli", ROOT / "scripts/benchmark.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    cls, cfg = cli.get_solver_and_config(branch, 10, seed=42)
    assert cfg.pool_recombine_enabled is (branch == "full")
    for enabled in (False, True):
        cfg.pool_recombine_enabled = enabled
        cfg.split_enabled = enabled
        solver = cls(case[0], cfg)
        components = cli.extract_instrumentation(solver, solver.cfg, branch)["resolved_components"]
        assert components["route_pool"] is enabled
        assert components["learned_split"] is enabled
