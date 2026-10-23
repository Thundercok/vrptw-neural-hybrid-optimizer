"""LAC adds predictive rescue to SA; it cannot veto SA for the same probability/draw."""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
import torch

from vrptw import Config, Inst, solvers
from vrptw.core import Plan
from vrptw.rl import LearnedAcceptanceCriterion

ROOT = Path(__file__).resolve().parents[1]


class ConstantPrediction(torch.nn.Module):
    def __init__(self, value):
        super().__init__()
        self.value = value
        self.calls = 0

    def forward(self, features):
        self.calls += 1
        return features.new_tensor([[self.value]])


def criterion(prediction=0.0, **kwargs):
    options = dict(lac_warmup=1, lac_horizon=2, lac_train_freq=1000)
    options.update(kwargs)
    lac = LearnedAcceptanceCriterion(Config(**options))
    lac.net = ConstantPrediction(prediction)
    return lac


def features(probability):
    values = np.zeros(9, dtype=np.float32)
    values[-1] = probability
    return values


@pytest.mark.parametrize("probability", [0.125, 0.5, 0.875, 1.0])
def test_low_prediction_cannot_veto_sa(monkeypatch, probability):
    lac = criterion(prediction=0.0)
    draw = Mock(return_value=probability / 2)
    monkeypatch.setattr("vrptw.rl.random.random", draw)
    accepted, prediction = lac.decide(features(probability), 100.0)
    assert accepted and prediction == 0.0
    assert lac.accept_count == 1
    draw.assert_called_once_with()


@pytest.mark.parametrize("probability,uniform", [(0.0, 0.01), (0.5, 0.5), (0.5, 0.75)])
def test_no_fixed_rescue_when_sa_and_predictor_reject(monkeypatch, probability, uniform):
    lac = criterion(prediction=0.0)
    monkeypatch.setattr("vrptw.rl.random.random", lambda: uniform)
    assert lac.decide(features(probability), 100.0)[0] is False
    assert lac.accept_count == 0


@pytest.mark.parametrize("threshold", [None, 0.5, 0.75])
def test_prediction_at_threshold_rescues_without_an_extra_random_draw(monkeypatch, threshold):
    lac = criterion(prediction=0.5 if threshold is None else threshold)
    draw = Mock(side_effect=AssertionError("predictive acceptance needs no RNG draw"))
    monkeypatch.setattr("vrptw.rl.random.random", draw)
    accepted, prediction = lac.decide(features(0.0), 100.0, tau=threshold)
    assert accepted and prediction == (0.5 if threshold is None else threshold)
    assert lac.accept_count == 1
    draw.assert_not_called()


@pytest.mark.parametrize("uniform,accepted", [(0.1, True), (0.9, False)])
def test_warmup_uses_only_sa_before_existing_boundary(monkeypatch, uniform, accepted):
    lac = criterion(prediction=1.0, lac_warmup=2)
    monkeypatch.setattr("vrptw.rl.random.random", lambda: uniform)
    decision, score = lac.decide(features(0.5), 100.0)
    assert decision is accepted and score == 0.5
    assert lac.net.calls == 0 and lac.step == 1
    assert lac.accept_count == int(accepted)


def test_predictive_override_starts_at_existing_warmup_boundary(monkeypatch):
    lac = criterion(prediction=1.0, lac_warmup=2)
    monkeypatch.setattr("vrptw.rl.random.random", lambda: 0.9)
    assert lac.decide(features(0.0), 100.0)[0] is False
    assert lac.decide(features(0.0), 100.0)[0] is True
    assert lac.net.calls == 1 and lac.accept_count == 1


@pytest.mark.parametrize("warmup", [1, 300])
@pytest.mark.parametrize(
    "probability,uniform,accepted", [(0.5000000001, 0.5, True), (0.4999999999, 0.4999999999, False)]
)
def test_original_sa_precision_is_not_replaced_by_float32_features(monkeypatch, warmup, probability, uniform, accepted):
    lac = criterion(prediction=0.0, lac_warmup=warmup)
    values = features(probability)
    assert float(values[-1]) == 0.5 and float(values[-1]) != probability
    monkeypatch.setattr("vrptw.rl.random.random", lambda: uniform)
    decision, score = lac.decide(values, 100.0, sa_probability=probability)
    assert decision is accepted
    assert score == (probability if warmup == 300 else 0.0)


def test_all_queries_queue_snapshots_and_horizon_counts_decisions(monkeypatch):
    lac = criterion(prediction=0.0)
    monkeypatch.setattr("vrptw.rl.random.random", lambda: 0.9)
    values = features(0.0)
    lac.decide(values, 100.0)
    values[0] = 123.0
    assert lac._pending[0][0][0] == 0.0
    for _ in range(5):
        lac.observe(90.0)
    assert lac.step == 1 and len(lac._train_buf) == 0
    lac.decide(features(0.0), 90.0)
    lac.observe(90.0)
    assert len(lac._train_buf) == 0
    lac.decide(features(0.0), 90.0)
    lac.observe(90.0)
    assert [label for _, label in lac._train_buf] == [1.0]
    lac.decide(features(0.0), 90.0)
    lac.observe(90.0)
    assert [label for _, label in lac._train_buf] == [1.0, 0.0]
    assert lac.accept_count == 0 and len(lac._pending) == 2


def tiny_case():
    data = np.zeros((5, 7), dtype=np.float64)
    data[:, 0] = np.arange(5)
    data[:, 1:3] = [(0, 0), (1, 0), (2, 0), (0, 1), (0, 2)]
    data[1:, 3], data[:, 5] = 1, 1000
    inst = Inst({"name": "lac_contract_toy", "capacity": 10.0, "data": data})
    return inst, Plan([[1, 2, 4, 3]], inst), Plan([[1, 4, 2, 3]], inst)


@pytest.mark.parametrize(
    "enabled,frozen,guard",
    [(True, False, None), (False, False, None), (True, True, None), (True, False, "fleet"), (True, False, "window")],
)
def test_solver_uses_original_sa_probability_and_preserves_gates(monkeypatch, enabled, frozen, guard):
    inst, initial, candidate = tiny_case()
    if guard == "fleet":
        candidate = Plan([[1, 2], [3, 4]], inst)
        assert candidate.feasible and candidate.nv > initial.nv
    elif guard == "window":
        inst.due_times[2] = 3.0
        assert not candidate.feasible
    else:
        assert candidate.feasible and candidate.nv == initial.nv and candidate.cost > initial.cost
    assert initial.feasible
    cfg = Config(
        hybrid_iterations=1,
        temp_control=1.0,
        lac_enabled=enabled,
        lac_warmup=1,
        adaptive_feasibility=False,
        macro_enabled=False,
        split_enabled=False,
        per_beta_auto_scale=False,
        pool_recombine_enabled=False,
        recombine_after_main_search=False,
        recombine_after_polish=False,
        time_limit_per_customer=0.0,
    )
    lac = criterion(prediction=1.0 if guard else 0.0)
    captured = {}
    original_features, original_decide = lac.features, lac.decide

    def make_features(**kwargs):
        captured["features"] = kwargs
        return original_features(**kwargs)

    def decide(*args, **kwargs):
        captured["decision"] = kwargs
        return original_decide(*args, **kwargs)

    monkeypatch.setattr(lac, "features", make_features)
    monkeypatch.setattr(lac, "decide", decide)
    monkeypatch.setattr(solvers, "LearnedAcceptanceCriterion", lambda *a, **kw: lac)
    solver = solvers.RuleMicroHybridSolver(inst, cfg)
    monkeypatch.setattr(solver, "_select_action", lambda *a: (0, False))
    monkeypatch.setattr(solver, "_rule_micro_select", lambda *a: (0, 0))
    monkeypatch.setattr(solver, "_destroy", lambda di, plan, size: (plan, []))
    monkeypatch.setattr(solvers, "REPAIR", [lambda *a, **kw: candidate] * solvers.N_R)
    monkeypatch.setattr(solver, "_refine_candidate", lambda cand, *a: cand)
    monkeypatch.setattr(solver, "_try_gec_route_reduction", lambda *a: None)
    monkeypatch.setattr(solver.ls_budget, "should_trigger", lambda *a: False)
    monkeypatch.setattr(solver, "_local_search", lambda plan, **kw: plan)
    monkeypatch.setattr(solver, "_fixed_nv_polish", lambda plan, *a, **kw: plan)
    for method in (
        "_generate_dense_pool_columns",
        "_seed_savings_routes",
        "_seed_nv_targeted_construction",
        "_seed_pool_large_destroy",
    ):
        monkeypatch.setattr(solver, method, lambda *a, **kw: None)
    monkeypatch.setattr("vrptw.rl.random.random", lambda: 0.5)
    result, _ = solver.solve(seed=42, init=initial, frozen=frozen)
    assert solver.search_iterations == 1
    assert solver.solver_history[0]["accepted"] is (guard is None)
    assert result.feasible and result.nv == initial.nv
    if enabled and not frozen and guard is None:
        f = captured["features"]
        expected = math.exp(-f["cost_delta"] / max(f["temp"], 1e-6))
        assert captured["decision"]["sa_probability"] == expected
        assert lac.step == 1
    else:
        assert captured == {} and lac.step == 0


@pytest.mark.parametrize(
    "branch,policy", [("full_no_gnn", "sa_or_predictive_v1"), ("full_no_lac", None), ("alns", None)]
)
def test_cli_records_policy_identity_for_future_runs(branch, policy):
    spec = importlib.util.spec_from_file_location("lac_cli", ROOT / "scripts/benchmark.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    cls, cfg = cli.get_solver_and_config(branch, 10, seed=42)
    inst, _, _ = tiny_case()
    solver = cls(inst, cfg)
    assert cli.extract_instrumentation(solver, cfg, branch)["lac_policy"] == policy
