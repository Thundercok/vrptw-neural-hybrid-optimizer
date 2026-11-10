from __future__ import annotations

import importlib
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from vrptw import Inst
from vrptw.core import Plan

local = importlib.import_module("vrptw.local_search")
HELPERS = ("_best_relocate", "_best_swap", "_best_swap_21", "_cross_exchange", "_cross_tail")


@pytest.fixture
def plan():
    data = np.zeros((7, 7))
    data[:, 0] = range(7)
    data[:, 1:3] = [(0, 0), (1, 0), (2, 0), (1, 1), (2, 1), (1, 2), (2, 2)]
    data[1:, 3], data[:, 5] = 1, 1000
    inst = Inst({"name": "deadline_scan", "capacity": 100, "data": data})
    inst.max_dist = 100
    return Plan([[1, 2], [3, 4], [5, 6]], inst)


@pytest.mark.parametrize("name", HELPERS)
def test_expired_scan_never_constructs_cache(monkeypatch, plan, name):
    monkeypatch.setattr(local.time, "perf_counter", lambda: 10.0)
    cache = Mock(side_effect=AssertionError("cache after cutoff"))
    monkeypatch.setattr(local._PlanCache, "from_plan", cache)
    assert getattr(local, name)(plan, deadline=10.0) is None
    cache.assert_not_called()


@pytest.mark.parametrize("name", HELPERS)
@pytest.mark.parametrize("pruned", [False, True])
def test_mid_scan_stops_after_crossing_kernel_without_late_cache_or_proposal(monkeypatch, plan, name, pruned):
    cache = local._PlanCache.from_plan(plan)
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(local.time, "perf_counter", lambda: clock.now)
    kernels = {
        "_best_relocate": (
            "_best_insert_in_route_numba",
            "_best_insert_in_route_pruned_numba",
            (-100.0, -1.0, 0),
            (-1.0, 0),
        ),
        "_best_swap": ("_swap_evaluate_numba", "_swap_evaluate_pruned_numba", (-1.0, 0, 0), (-1.0, 0, 0)),
        "_best_swap_21": ("_swap_21_evaluate_numba", "_swap_21_evaluate_numba", (-1.0, 21, 0, 0), (-1.0, 21, 0, 0)),
        "_cross_exchange": (
            "_cross_exchange_pair_numba",
            "_cross_exchange_pair_pruned_numba",
            (-1.0, 0, 1, 0, 1),
            (-1.0, 0, 1, 0, 1),
        ),
        "_cross_tail": ("_cross_tail_pair_numba", "_cross_tail_pair_pruned_numba", (-1.0, 1, 1), (-1.0, 1, 1)),
    }
    plain, guided, result, pruned_result = kernels[name]

    def cross(*args):
        clock.now = 1.0
        return pruned_result if pruned else result

    kernel = Mock(side_effect=cross)
    monkeypatch.setattr(local, guided if pruned else plain, kernel)
    options = {"heatmap": np.ones((7, 7)), "pruning_threshold": 0.5} if pruned else {}
    assert getattr(local, name)(plan, cache=cache, deadline=1.0, **options) is None
    assert kernel.call_count == 1
    assert cache.scan_memo == {}


@pytest.mark.parametrize("name", ["local_search", "td_inter_route_polish"])
def test_search_forwards_deadline_to_every_neighborhood(monkeypatch, plan, name):
    monkeypatch.setattr(local.time, "perf_counter", lambda: 0.0)
    monkeypatch.setattr(local, "_two_opt_best", lambda route, inst, **kw: route[:])
    spies = {}
    for helper in (*HELPERS, "_best_or_opt", "_intra_route_or_opt", "_try_route_compact", "_try_route_merge"):
        spy = Mock(return_value=None)
        spies[helper] = spy
        monkeypatch.setattr(local, helper, spy)
    getattr(local, name)(plan, max_passes=1, deadline=5.0)
    for helper in HELPERS:
        assert spies[helper].call_count > 0, helper
        assert all(c.kwargs.get("deadline") == 5.0 for c in spies[helper].call_args_list), helper


@pytest.mark.parametrize("name", ["local_search", "td_inter_route_polish"])
def test_expired_search_skips_initial_feasibility(monkeypatch, name):
    class Bomb:
        @property
        def feasible(self):
            raise AssertionError("feasibility work after cutoff")

    plan = Bomb()
    monkeypatch.setattr(local.time, "perf_counter", lambda: 10.0)
    assert getattr(local, name)(plan, deadline=10.0) is plan


def test_two_opt_never_starts_expired_kernel_and_discards_late_output(monkeypatch, plan):
    clock = SimpleNamespace(now=1.0)
    monkeypatch.setattr(local.time, "perf_counter", lambda: clock.now)
    kernel = Mock(side_effect=AssertionError("late kernel"))
    monkeypatch.setattr(local, "_two_opt_best_numba", kernel)
    route = [1, 2, 3, 4]
    assert local._two_opt_best(route, plan.inst, deadline=1.0) == route
    kernel.assert_not_called()
    clock.now = 0.0

    def cross(*a):
        clock.now = 1.0
        return np.array(route[::-1]), -1.0

    kernel.side_effect = cross
    assert local._two_opt_best(route, plan.inst, deadline=1.0) == route
    assert kernel.call_count == 1


@pytest.mark.parametrize("name", HELPERS)
def test_cache_build_expiry_stops_before_dispatch(monkeypatch, plan, name):
    cache = local._PlanCache.from_plan(plan)
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(local.time, "perf_counter", lambda: clock.now)

    def build(*a, **kw):
        clock.now = 1.0
        return cache

    monkeypatch.setattr(local._PlanCache, "from_plan", build)
    kernel_names = (
        "_best_insert_in_route_numba",
        "_swap_evaluate_numba",
        "_swap_21_evaluate_numba",
        "_cross_exchange_pair_numba",
        "_cross_tail_pair_numba",
    )
    kernels = [Mock(side_effect=AssertionError("dispatch after cache expired")) for _ in kernel_names]
    for key, kernel in zip(kernel_names, kernels, strict=True):
        monkeypatch.setattr(local, key, kernel)
    assert getattr(local, name)(plan, deadline=1.0) is None
    assert all(k.call_count == 0 for k in kernels)


@pytest.mark.parametrize("name", ["_cross_exchange", "_cross_tail"])
@pytest.mark.parametrize("pruned", [False, True])
def test_cross_scan_checks_between_cost_kernel_and_pair_kernel(monkeypatch, plan, name, pruned):
    cache = local._PlanCache.from_plan(plan)
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(local.time, "perf_counter", lambda: clock.now)

    def cost(*a):
        clock.now = 1.0
        return 0.0

    evaluate = Mock(side_effect=AssertionError("pair scan after cost expired"))
    cost_spy = Mock(side_effect=cost)
    monkeypatch.setattr(local, "_route_cost", cost_spy)
    stem = "_cross_exchange_pair" if name == "_cross_exchange" else "_cross_tail_pair"
    monkeypatch.setattr(local, stem + ("_pruned_numba" if pruned else "_numba"), evaluate)
    options = {"heatmap": np.ones((7, 7)), "pruning_threshold": 0.5} if pruned else {}
    assert getattr(local, name)(plan, cache=cache, deadline=1.0, **options) is None
    assert cost_spy.call_count == 1 and evaluate.call_count == 0
