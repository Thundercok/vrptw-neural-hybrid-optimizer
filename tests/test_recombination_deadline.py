from __future__ import annotations

import importlib
from types import SimpleNamespace

import numpy as np
import pytest

from vrptw import Config, Inst
from vrptw import pool as route_pool
from vrptw.core import Plan

local_search_module = importlib.import_module("vrptw.local_search")
MODES = [{"td_only": True, "nv_ceiling": 1}, {}, {"nv_ceiling": 1}]


@pytest.fixture
def recombination(monkeypatch):
    data = np.zeros((4, 7), dtype=np.float64)
    data[:, 0] = np.arange(4)
    data[1:, 1:3] = [(1, 0), (0, 1), (2, 0)]
    data[1:, 3] = 1
    data[:, 5] = 100
    inst = Inst({"name": "late_recombination", "capacity": 10.0, "data": data})
    incumbent = Plan([[1, 2, 3]], inst)
    candidate = Plan([[2, 1, 3]], inst)
    assert incumbent.feasible and candidate.feasible and candidate.dominates(incumbent)
    cfg = Config()
    pool = route_pool.RoutePool(inst, cfg)
    pool.add_plan(candidate)
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(route_pool, "time", SimpleNamespace(perf_counter=lambda: clock.now))
    monkeypatch.setattr(local_search_module, "local_search", lambda plan, **kwargs: plan)
    return SimpleNamespace(inst=inst, incumbent=incumbent, candidate=candidate, cfg=cfg, pool=pool, clock=clock)


@pytest.mark.parametrize("mode", MODES, ids=["td_only", "standard", "nv_target"])
@pytest.mark.parametrize("stage", ["milp", "greedy"])
@pytest.mark.parametrize("finish", [0.5, 1.0, 2.0])
def test_recombination_accepts_only_before_deadline(monkeypatch, recombination, mode, stage, finish):
    ctx = recombination

    def completed(*args, **kwargs):
        ctx.clock.now = finish
        return ctx.candidate

    monkeypatch.setattr(route_pool, "_milp_recombine", completed if stage == "milp" else lambda *a, **kw: None)
    monkeypatch.setattr(route_pool, "_greedy_recombine", completed)
    result = route_pool.recombine_with_route_pool(ctx.incumbent, ctx.pool, ctx.cfg, deadline=1.0, **mode)
    assert result.routes == (ctx.candidate.routes if finish < 1.0 else ctx.incumbent.routes)
    assert ctx.incumbent.routes == [[1, 2, 3]]


@pytest.mark.parametrize("mode", MODES, ids=["td_only", "standard", "nv_target"])
def test_recombination_without_deadline_still_accepts_improvement(monkeypatch, recombination, mode):
    ctx = recombination

    def completed(*args, **kwargs):
        ctx.clock.now = 2.0
        return ctx.candidate

    monkeypatch.setattr(route_pool, "_milp_recombine", completed)
    result = route_pool.recombine_with_route_pool(ctx.incumbent, ctx.pool, ctx.cfg, **mode)
    assert result.routes == ctx.candidate.routes


def test_recombination_discards_local_search_completed_after_deadline(monkeypatch, recombination):
    ctx = recombination
    monkeypatch.setattr(route_pool, "_milp_recombine", lambda *a, **kw: ctx.candidate)

    def late_search(candidate, **kwargs):
        ctx.clock.now = 2.0
        return candidate

    monkeypatch.setattr(local_search_module, "local_search", late_search)
    result = route_pool.recombine_with_route_pool(ctx.incumbent, ctx.pool, ctx.cfg, nv_ceiling=1, deadline=1.0)
    assert result.routes == ctx.incumbent.routes


@pytest.mark.parametrize("mode", MODES, ids=["td_only", "standard", "nv_target"])
def test_recombination_rechecks_deadline_after_validation(monkeypatch, recombination, mode):
    ctx = recombination
    monkeypatch.setattr(route_pool, "_milp_recombine", lambda *a, **kw: ctx.candidate)
    feasible = Plan.feasible.fget
    dominates = Plan.dominates

    def checked(plan):
        result = feasible(plan)
        if plan is ctx.candidate:
            ctx.clock.now = 2.0
        return result

    def compared(plan, other):
        result = dominates(plan, other)
        ctx.clock.now = 2.0
        return result

    monkeypatch.setattr(Plan, "feasible", property(checked))
    monkeypatch.setattr(Plan, "dominates", compared)
    result = route_pool.recombine_with_route_pool(ctx.incumbent, ctx.pool, ctx.cfg, deadline=1.0, **mode)
    assert result.routes == ctx.incumbent.routes


@pytest.mark.parametrize("fallback", [False, True])
def test_milp_discards_late_backend_result_without_caching(monkeypatch, recombination, fallback):
    ctx = recombination
    calls = []
    cache = {}
    stats = {}
    recs = ctx.pool.records(ctx.incumbent)

    def milp(**kwargs):
        calls.append(kwargs["options"]["time_limit"])
        if fallback and len(calls) == 1:
            ctx.clock.now = 0.25
            return SimpleNamespace(x=None, status=1)
        ctx.clock.now = 2.0
        return SimpleNamespace(x=np.ones(len(recs)), status=0)

    monkeypatch.setattr(route_pool, "milp", milp)
    monkeypatch.setattr(route_pool, "_cleanup_duplicate_nodes", lambda *a: pytest.fail("late postprocessing"))
    result = route_pool._milp_recombine(recs, ctx.inst, ctx.cfg, _cache=cache, _stats=stats, deadline=1.0)
    assert result is None
    assert cache == {}
    assert calls == ([1.0, 0.75] if fallback else [1.0])
    assert stats["calls"] == len(calls)


@pytest.mark.parametrize("cache_hit", [False, True])
def test_milp_rechecks_deadline_after_plan_validation(monkeypatch, recombination, cache_hit):
    ctx = recombination
    cache = {}
    recs = ctx.pool.records(ctx.incumbent)
    monkeypatch.setattr(route_pool, "milp", lambda **kw: SimpleNamespace(x=np.ones(len(recs)), status=0))
    if cache_hit:
        assert route_pool._milp_recombine(recs, ctx.inst, ctx.cfg, _cache=cache) is not None
        monkeypatch.setattr(route_pool, "milp", lambda **kw: pytest.fail("cache miss"))
    existing = cache.copy()
    validations = []

    def exact_cover(plan):
        validations.append(plan)
        if cache_hit or len(validations) == 2:
            ctx.clock.now = 2.0
        return True

    monkeypatch.setattr(route_pool, "_is_exact_cover", exact_cover)
    result = route_pool._milp_recombine(recs, ctx.inst, ctx.cfg, _cache=cache, deadline=1.0)
    assert result is None
    assert cache == existing
