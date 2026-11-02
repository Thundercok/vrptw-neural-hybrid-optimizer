"""Fleet minimisation by the full-budget GES: results stay feasible and it reads no reference."""

import time

import numpy as np

from vrptw.config import Config
from vrptw.core import Inst
from vrptw.ges import _best_ejection, fleet_lower_bound, ges_minimize
from vrptw.heuristics import build_greedy
from vrptw.local_search import _covers_all_customers


def random_instance(n=60, seed=7, width=120.0, capacity=60.0):
    rng = np.random.default_rng(seed)
    rows = [[0, 50, 50, 0, 0, 1000, 0]]
    for i in range(1, n + 1):
        ready = float(rng.uniform(100, 700))  # every customer reachable from the depot
        rows.append([i, *rng.uniform(0, 100, 2), float(rng.integers(1, 20)), ready, ready + width, 10])
    return Inst({"name": "rand", "data": np.array(rows), "capacity": capacity})


def test_ges_removes_routes_and_stays_feasible():
    inst = random_instance()
    start = build_greedy(inst, "ges")
    best = ges_minimize(start, time.perf_counter() + 2.0, 1)
    assert best.nv < start.nv
    assert best.nv >= fleet_lower_bound(inst)
    assert best.feasible and _covers_all_customers(best.routes, inst)


def test_ges_respects_deadline():
    inst = random_instance(width=30.0)
    t = time.perf_counter()
    best = ges_minimize(build_greedy(inst, "ges"), t + 0.5, 1)
    assert time.perf_counter() - t < 1.5
    assert best.feasible


def test_ejection_can_skip_a_kept_customer():
    # Route 1-2-3 is capacity-full; only ejecting the non-adjacent pair 1 and 3 admits v=4.
    rows = [
        [0, 0, 0, 0, 0, 1000, 0],
        [1, 1, 0, 5, 0, 1000, 0],
        [2, 2, 0, 1, 0, 1000, 0],
        [3, 3, 0, 5, 0, 1000, 0],
        [4, 4, 0, 10, 0, 1000, 0],
    ]
    inst = Inst({"name": "pair", "data": np.array(rows, dtype=float), "capacity": 11.0})
    routes = np.zeros((1, 8), dtype=np.int64)
    routes[0, :3] = [1, 2, 3]
    size = 10
    penalty = np.ones(5, dtype=np.int64)
    penalty[2] = 100
    psum, r, ins, mask = _best_ejection(
        4, routes, np.array([3], dtype=np.int64), penalty, 5, inst.demands, inst.capacity, inst.ready_times,
        inst.due_times, inst.service_times, inst.dist, np.zeros(size), np.zeros(size), 10000,
    )
    assert (r, int(psum)) == (0, 2)
    assert mask[0] and not mask[1] and mask[2]


def test_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("VRPTW_GES_PHASE", raising=False)
    assert Config().ges_phase_enabled is False
    monkeypatch.setenv("VRPTW_GES_PHASE", "1")
    assert Config().ges_phase_enabled is True
