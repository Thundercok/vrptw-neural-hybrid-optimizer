"""Factor bindings and GEC-off semantics, including forced secondary paths."""

from __future__ import annotations

import importlib
import importlib.util
from dataclasses import asdict
from itertools import product
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
import torch

from vrptw import Config, Inst, solvers
from vrptw.core import Plan
from vrptw.pool import RoutePool

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "results/gnn_retraining_20261017/model_seed42/best.pt"
local = importlib.import_module("vrptw.local_search")


def cli_module():
    spec = importlib.util.spec_from_file_location("factor_cli", ROOT / "scripts/benchmark.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    return cli


@pytest.fixture
def case():
    data = np.zeros((5, 7), dtype=np.float64)
    data[:, 0] = np.arange(5)
    data[:, 1:3] = [(0, 0), (1, 0), (2, 0), (0, 1), (0, 2)]
    data[1:, 3], data[:, 5] = 1, 1000
    inst = Inst({"name": "factor_contract_toy", "capacity": 10.0, "data": data})
    return inst, Plan([[1, 2, 4, 3]], inst)


@pytest.mark.parametrize("enabled", [False, True])
def test_hybrid_gec_off_retains_direct_insertion_but_forbids_displacement(case, enabled):
    inst, _ = case
    inst.capacity = 6.0
    inst.demands[:] = [0, 3, 2, 3, 4]
    plan = Plan([[1], [2, 3], [4]], inst)
    cfg = Config()
    cfg.gec_enabled = enabled
    solver = solvers.HybridDDQNSolver(inst, cfg)
    result = solver._try_gec_route_reduction(plan)
    if enabled:
        assert result is not None and result.feasible and result.nv == 2
    else:
        assert result is None
    # A directly insertable target must still be reduced with GEC disabled.
    inst.demands[:] = [0, 1, 1, 1, 1]
    direct = solver._try_gec_route_reduction(Plan([[1], [2, 3, 4]], inst))
    assert direct is not None and direct.feasible and direct.nv == 1


@pytest.mark.parametrize("enabled", [False, True])
def test_deep_chain_off_clamps_depth_even_with_explicit_large_depth(monkeypatch, case, enabled):
    inst, _ = case
    plan = Plan([[1, 2], [3, 4]], inst)
    chain = Mock(return_value=None)
    monkeypatch.setattr(local, "_try_chain_elimination", chain)
    local._ejection_chain_eliminate(plan, max_depth=99, gec_enabled=enabled)
    assert chain.call_count == 2
    assert all(c.kwargs["max_depth"] == (99 if enabled else 1) for c in chain.call_args_list)


@pytest.mark.parametrize("enabled,hard", product([False, True], repeat=2))
def test_buffered_off_forbids_ejection_and_ges_even_in_hard_mode(monkeypatch, case, enabled, hard):
    inst, _ = case
    plan = Plan([[1, 2], [3, 4]], inst)
    beam, ges = Mock(return_value=None), Mock(return_value=None)
    monkeypatch.setattr(local, "_try_buffered_route_elimination", beam)
    monkeypatch.setattr(local, "_guided_ejection_search", ges)
    result = local._buffered_route_elimination(plan, hard_mode=hard, gec_enabled=enabled)
    assert result.routes == plan.routes and beam.call_count == 2
    assert all((c.kwargs["max_ejections"] > 0) is enabled for c in beam.call_args_list)
    assert ges.call_count == (2 if enabled else 0)


def test_zero_ejection_beam_never_expands_displacement(monkeypatch, case):
    inst, _ = case
    plan = Plan([[1], [2, 3, 4]], inst)
    monkeypatch.setattr(local, "_insertion_options", lambda *a: [])
    ejections = Mock(side_effect=AssertionError("disabled displacement"))
    monkeypatch.setattr(local, "_buffered_ejection_options", ejections)
    assert local._try_buffered_route_elimination(plan, 0, max_ejections=0) is None
    ejections.assert_not_called()


@pytest.mark.parametrize("macro,micro", product([0, 1], repeat=2))
def test_controllers_compose_and_only_enabled_networks_infer_or_update(monkeypatch, case, macro, micro):
    binding = importlib.import_module("vrptw.ablation")
    cls, cfg = binding.bind_ablation(
        f"F00{macro}{micro}00",
        Config(
            hybrid_iterations=4,
            segment_size=1,
            time_limit_per_customer=0.0,
            adaptive_feasibility=False,
            per_beta_auto_scale=False,
            ctrl_start=2,
            ctrl_start_floor=1,
            ctrl_eps_start=0.0,
            ctrl_batch=1,
            op_warmup=0,
            op_eps_start=0.0,
            op_batch=1,
        ),
    )
    inst, initial = case
    solver = cls(inst, cfg)
    isolate(monkeypatch, solver, initial)
    spies = {}
    for name, controller in (("macro", solver.ctrl), ("micro", solver.op_ctrl)):
        for operation in ("act", "observe", "train_step"):
            spy = Mock(wraps=getattr(controller, operation))
            monkeypatch.setattr(controller, operation, spy)
            spies[name, operation] = spy
        spy = Mock(wraps=controller.q.forward)
        monkeypatch.setattr(controller.q, "forward", spy)
        spies[name, "forward"] = spy
    before = {
        name: {k: v.clone() for k, v in c.q.state_dict().items()}
        for name, c in (("macro", solver.ctrl), ("micro", solver.op_ctrl))
    }
    result, _ = solver.solve(seed=42, init=initial, shared_norm=SimpleNamespace(normalize=lambda v: 1.0))
    assert result.feasible and solver.search_iterations == 4 and solver.use_rl
    assert solver.cfg.macro_enabled and not solver.cfg.split_enabled
    for name, enabled, c in (("macro", macro, solver.ctrl), ("micro", micro, solver.op_ctrl)):
        for operation in ("act", "forward", "observe", "train_step"):
            assert (spies[name, operation].call_count > 0) is bool(enabled)
        assert (len(c.buf) > 0) is bool(enabled)
        changed = any(not torch.equal(v, before[name][k]) for k, v in c.q.state_dict().items())
        assert changed is bool(enabled)
    counts = solver.controller_counts
    assert counts["micro_ddqn"] == (4 if micro else 0)
    assert counts["micro_rule"] == (0 if micro else 4)
    assert counts["macro_ddqn"] == (3 if macro else 0)
    assert counts["macro_rule"] == (0 if macro else 3)


def isolate(monkeypatch, solver, initial):
    monkeypatch.setattr(solver, "_destroy", lambda di, p, size: (p, []))
    monkeypatch.setattr(solvers, "REPAIR", [lambda *a, **kw: initial.copy()] * solvers.N_R)
    monkeypatch.setattr(solver, "_local_search", lambda p, **kw: p)
    monkeypatch.setattr(solver, "_fixed_nv_polish", lambda p, *a, **kw: p)
    monkeypatch.setattr(solver.ls_budget, "should_trigger", lambda *a: False)


@pytest.mark.parametrize("macro", [0, 1])
def test_macro_policies_share_eligibility_and_pool_opportunity(monkeypatch, case, macro):
    binding = importlib.import_module("vrptw.ablation")
    cls, cfg = binding.bind_ablation(
        f"F01{macro}000", Config(ctrl_start=20, ctrl_start_floor=10, plateau_start=20, rl_recombine_min_routes=1)
    )
    inst, plan = case
    solver = cls(inst, cfg)
    pool = RoutePool(inst, cfg)
    pool._routes = {i: None for i in range(100)}
    monkeypatch.setattr(solvers, "_fleet_fill", lambda *a: 0.9)
    act = Mock(return_value=solvers.MODE_POOL_RECOMBINE)
    monkeypatch.setattr(solver.ctrl, "act", act)
    assert solver._select_action(None, plan, plan, 9, 0.5, pool, False) == (0, False)
    act.assert_not_called()
    mode, active = solver._select_action(None, plan, plan, 20, 0.5, pool, False)
    assert mode == solvers.MODE_POOL_RECOMBINE and active is bool(macro)
    backend = Mock(return_value=plan)
    monkeypatch.setattr(solvers, "recombine_with_route_pool", backend)
    solver._refine_candidate(plan, mode, pool, plan, plan, 20, 0)
    backend.assert_called_once()


@pytest.mark.parametrize("enabled", [False, True])
def test_lac_is_independent_when_both_routing_controllers_are_rule(monkeypatch, case, enabled):
    binding = importlib.import_module("vrptw.ablation")
    cls, cfg = binding.bind_ablation(
        f"F0000{int(enabled)}0",
        Config(
            hybrid_iterations=1,
            adaptive_feasibility=False,
            per_beta_auto_scale=False,
            time_limit_per_customer=0.0,
            lac_warmup=1,
        ),
    )
    inst, initial = case
    solver = cls(inst, cfg)
    isolate(monkeypatch, solver, initial)
    candidate = Plan([[1, 4, 2, 3]], inst)
    assert candidate.cost > initial.cost and candidate.feasible
    monkeypatch.setattr(solvers, "REPAIR", [lambda *a, **kw: candidate] * solvers.N_R)
    result, _ = solver.solve(seed=42, init=initial)
    assert result.feasible and solver.lac.step == int(enabled)


def planned_cells():
    spec = importlib.util.spec_from_file_location("factor_design", ROOT / "scripts/prepare_ablation_design.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_cells()


@pytest.mark.parametrize("case_id,cell", planned_cells().items())
def test_all_planned_cells_have_explicit_independent_cli_bindings(case, case_id, cell):
    levels = cell["levels"]
    cli = cli_module()
    cls, cfg = cli.get_solver_and_config(case_id, 60, seed=43, gnn_model=MODEL if levels[-1] else None)
    assert [
        int(cfg.gec_enabled),
        int(cfg.pool_recombine_enabled),
        int(levels[2]),
        int(levels[3]),
        int(cfg.lac_enabled),
        int(bool(cfg.gnn_model_path)),
    ] == levels
    assert cfg.ablation_case == case_id and cfg.macro_enabled and not cfg.split_enabled
    assert not cfg.adaptive_scale_bypass and not cfg.distilled_weights_path
    assert cfg.time_limit == 60 and cfg.seed == 43
    solver = cls(case[0], cfg)
    assert solver.use_rl and solver.ctrl.use_rl is bool(levels[2]) and solver.op_ctrl.use_rl is bool(levels[3])
    metadata = cli.extract_instrumentation(solver, solver.cfg, case_id)
    assert metadata["macro_policy"] == ("ddqn" if levels[2] else "rule")
    assert metadata["micro_policy"] == ("ddqn" if levels[3] else "rule")
    assert metadata["resolved_components"]["gec"] is bool(levels[0])
    assert metadata["resolved_components"]["macro_ddqn"] is bool(levels[2])
    assert metadata["resolved_components"]["micro_ddqn"] is bool(levels[3])
    assert metadata["controller_counts"] == {}


@pytest.mark.parametrize("bad", ["F00000", "F0000000", "F000002", "F00000x", "f000000"])
def test_malformed_factor_cases_are_rejected(bad):
    binding = importlib.import_module("vrptw.ablation")
    with pytest.raises(ValueError):
        binding.bind_ablation(bad, Config())


@pytest.mark.parametrize("case_id,model", [("F000001", None), ("F000000", MODEL)])
def test_gnn_bit_requires_explicit_matching_model(case_id, model):
    binding = importlib.import_module("vrptw.ablation")
    with pytest.raises(ValueError):
        binding.bind_ablation(case_id, Config(), gnn_model=model)


def test_bad_gnn_hash_and_transfer_weights_are_rejected(tmp_path):
    binding = importlib.import_module("vrptw.ablation")
    bad = tmp_path / "bad.pt"
    bad.write_bytes(b"wrong identity")
    with pytest.raises(ValueError, match="SHA|hash|checkpoint"):
        binding.bind_ablation("F000001", Config(), gnn_model=bad)
    with pytest.raises(ValueError, match="transfer|weight"):
        binding.bind_ablation("F000000", Config(distilled_weights_path="old_weights.pt"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("gec_enabled", True),
        ("split_enabled", True),
        ("macro_enabled", False),
        ("adaptive_scale_bypass", True),
        ("lac_enabled", True),
    ],
)
def test_bound_configuration_drift_is_rejected_before_search(case, field, value):
    binding = importlib.import_module("vrptw.ablation")
    cls, cfg = binding.bind_ablation("F000000", Config())
    setattr(cfg, field, value)
    with pytest.raises(ValueError):
        cls(case[0], cfg)


@pytest.mark.parametrize("branch", ["full_no_macro", "full_no_gec"])
def test_legacy_loco_aliases_have_correct_component_scope(branch):
    cli = cli_module()
    cls, cfg = cli.get_solver_and_config(branch, 60)
    if branch == "full_no_macro":
        assert cls is solvers.RuleMacroHybridSolver and cfg.macro_enabled
    else:
        assert not cfg.gec_enabled and cfg.gec_max_depth == 3


@pytest.mark.parametrize("enabled,phase", product([False, True], ["committed", "main_tail"]))
def test_real_hybrid_paths_forward_gec_scope_to_chain_and_buffer(monkeypatch, case, enabled, phase):
    inst, _ = case
    initial = Plan([[1, 2], [3, 4]], inst)
    cfg = Config(
        hybrid_iterations=16,
        adaptive_feasibility=False,
        per_beta_auto_scale=False,
        pool_recombine_enabled=False,
        split_enabled=False,
        lac_enabled=False,
        recombine_after_main_search=False,
        recombine_after_polish=False,
        time_limit_per_customer=0.0,
    )
    cfg.gec_enabled = enabled
    solver = solvers.RuleMicroHybridSolver(inst, cfg)
    isolate(monkeypatch, solver, initial)
    monkeypatch.setattr(solver, "_refine_candidate", lambda p, *a: p)
    monkeypatch.setattr(solver, "_try_gec_route_reduction", lambda *a: None)
    chain = Mock(return_value=None)
    buffered = Mock(side_effect=lambda p, *a, **kw: p)
    monkeypatch.setattr(solvers, "_ejection_chain_eliminate", chain)
    monkeypatch.setattr(solvers, "_buffered_route_elimination", buffered)
    monkeypatch.setattr(local, "_buffered_route_elimination", buffered)
    monkeypatch.setattr(solvers, "_iterative_route_elimination", lambda p, *a, **kw: p)
    monkeypatch.setattr(solvers, "td_converge_polish", lambda p, **kw: p)
    monkeypatch.setattr(solvers, "td_inter_route_polish", lambda p, **kw: p)
    if phase == "committed":
        solver._committed_nv_search(initial, RoutePool(inst, cfg), target_nv=1)
    else:
        monkeypatch.setattr(solver, "_committed_nv_search", lambda *a, **kw: Plan([[1, 2, 3, 4]], inst))
        solver.solve(seed=42, init=initial)
        assert solver.search_iterations == 16 and chain.call_count >= 2
    assert chain.call_count and buffered.call_count
    assert all(c.kwargs.get("gec_enabled", True) is enabled for c in chain.call_args_list + buffered.call_args_list)


@pytest.mark.parametrize("macro,micro", product([0, 1], repeat=2))
def test_frozen_bindings_never_enqueue_or_train(monkeypatch, case, macro, micro):
    binding = importlib.import_module("vrptw.ablation")
    cls, cfg = binding.bind_ablation(
        f"F00{macro}{micro}00",
        Config(
            hybrid_iterations=4,
            segment_size=1,
            adaptive_feasibility=False,
            per_beta_auto_scale=False,
            time_limit_per_customer=0.0,
            ctrl_start=2,
            ctrl_start_floor=1,
        ),
    )
    inst, initial = case
    solver = cls(inst, cfg)
    isolate(monkeypatch, solver, initial)
    for c in (solver.ctrl, solver.op_ctrl):
        monkeypatch.setattr(c, "observe", Mock(side_effect=AssertionError("frozen replay")))
        monkeypatch.setattr(c, "train_step", Mock(side_effect=AssertionError("frozen training")))
    solver.solve(seed=42, init=initial, frozen=True)
    assert len(solver.ctrl.buf) == len(solver.op_ctrl.buf) == 0


def test_binding_does_not_mutate_base_config():
    binding = importlib.import_module("vrptw.ablation")
    cfg = Config()
    before = asdict(cfg)
    binding.bind_ablation("F000000", cfg)
    assert asdict(cfg) == before


def test_gnn_loading_and_search_guard_prevent_silent_fallback_or_off_guidance(monkeypatch, case, tmp_path):
    binding = importlib.import_module("vrptw.ablation")
    inst, initial = case
    cls, off = binding.bind_ablation("F000000", Config())
    solver = cls(inst, off)
    with pytest.raises(ValueError):
        solver.load_gnn_model(str(MODEL))
    solver.gnn_model = object()
    with pytest.raises(ValueError):
        solver.solve(init=initial)
    cls, on = binding.bind_ablation(
        "F000001",
        Config(hybrid_iterations=1, adaptive_feasibility=False, per_beta_auto_scale=False, time_limit_per_customer=0.0),
        gnn_model=MODEL,
    )
    solver = cls(inst, on)
    with pytest.raises(ValueError):
        solver.solve(init=initial)
    wrong = tmp_path / "wrong.pt"
    wrong.write_bytes(b"wrong")
    with pytest.raises(ValueError):
        solver.load_gnn_model(str(wrong))
    solver.load_gnn_model(str(MODEL))
    assert solver.gnn_model is not None
    isolate(monkeypatch, solver, initial)
    forward = Mock(wraps=solver.gnn_model.forward)
    monkeypatch.setattr(solver.gnn_model, "forward", forward)
    assert solver.solve(seed=42, init=initial)[0].feasible
    forward.assert_called_once()


def test_factor_solver_rejects_direct_controller_weight_transfer(case):
    binding = importlib.import_module("vrptw.ablation")
    cls, cfg = binding.bind_ablation("F000000", Config())
    solver = cls(case[0], cfg)
    with pytest.raises(ValueError, match="transfer|fresh|cold"):
        solver.load_weights(solver.clone_weights())


def test_instrumentation_records_actual_nested_pool_and_controller_configs(case):
    binding = importlib.import_module("vrptw.ablation")
    cls, cfg = binding.bind_ablation("F010000", Config())
    inst, _ = case
    solver = cls(inst, cfg)
    solver.pool = RoutePool(inst, cfg)
    solver.cfg.segment_size = 999
    metadata = cli_module().extract_instrumentation(solver, solver.cfg, cfg.ablation_case)
    actual = metadata["module_configs"]
    assert actual["route_pool"] == asdict(solver.pool.cfg)
    assert actual["macro"] == asdict(solver.ctrl.cfg)
    assert actual["micro"] == asdict(solver.op_ctrl.cfg)
    assert actual["lac"] == asdict(solver.lac.cfg)
    assert actual["route_pool"]["route_pool_limit"] != solver.cfg.route_pool_limit
    assert actual["macro"]["segment_size"] != solver.cfg.segment_size


def test_model_contract_revalidation_is_charged_inside_native_cutoff(monkeypatch, case):
    binding = importlib.import_module("vrptw.ablation")
    cls, cfg = binding.bind_ablation(
        "F000001", Config(time_limit=0.1, hybrid_iterations=1, adaptive_feasibility=False), gnn_model=MODEL
    )
    inst, initial = case
    solver = cls(inst, cfg)
    solver.load_gnn_model(str(MODEL))
    clock = SimpleNamespace(now=100.0)
    timer = SimpleNamespace(perf_counter=lambda: clock.now)
    monkeypatch.setattr(solvers, "time", timer)
    check = binding._check_model

    def slow_check(path):
        clock.now += 0.2
        return check(path)

    monkeypatch.setattr(binding, "_check_model", slow_check)
    with pytest.raises(solvers.NativeNoSolutionError):
        solver.solve(seed=42, init=initial)
    assert solver._t_start == 100.0 and solver._deadline == pytest.approx(100.1)


@pytest.mark.parametrize("attribute,value", [("use_op_rule", True), ("macro_policy", "rule")])
def test_live_controller_selection_cannot_drift_from_binding(monkeypatch, case, attribute, value):
    binding = importlib.import_module("vrptw.ablation")
    cls, cfg = binding.bind_ablation(
        "F001100",
        Config(hybrid_iterations=1, adaptive_feasibility=False, per_beta_auto_scale=False, time_limit_per_customer=0.0),
    )
    inst, initial = case
    solver = cls(inst, cfg)
    isolate(monkeypatch, solver, initial)
    setattr(solver, attribute, value)
    with pytest.raises(ValueError, match="[Cc]ontroller|[Cc]onfiguration"):
        solver.solve(seed=42, init=initial)
