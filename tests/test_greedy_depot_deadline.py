from __future__ import annotations

from pathlib import Path

import numpy as np

from vrptw import Inst
from vrptw.core import load_solomon_instance
from vrptw.heuristics import build_greedy
from vrptw.native_certification import validate_routes

ROOT = Path(__file__).resolve().parents[1]


def _line_instance(depot_due: float) -> Inst:
    # Depot at 0, customers at 10 and 20 on a line; serving both on one route
    # returns to the depot at 40 + 2 service = 42.
    # columns: id, x, y, demand, ready, due, service
    data = np.array(
        [
            [0, 0.0, 0.0, 0.0, 0.0, depot_due, 0.0],
            [1, 10.0, 0.0, 1.0, 0.0, 100.0, 1.0],
            [2, 20.0, 0.0, 1.0, 0.0, 100.0, 1.0],
        ]
    )
    return Inst({"name": "line", "data": data, "capacity": 10.0})


def test_greedy_respects_depot_return_deadline():
    inst = _line_instance(depot_due=41.0)
    plan = build_greedy(inst, "test")
    assert validate_routes(plan.routes, inst) is not None
    assert len(plan.routes) == 2


def test_greedy_still_merges_when_depot_deadline_allows():
    inst = _line_instance(depot_due=42.0)
    plan = build_greedy(inst, "test")
    assert validate_routes(plan.routes, inst) is not None
    assert len(plan.routes) == 1


def test_greedy_is_feasible_on_r1_2_5():
    inst = load_solomon_instance(str(ROOT / "data/Gehring_Homberger/homberger_200_customer_instances/R1_2_5.TXT"))
    plan = build_greedy(inst, "test")
    assert validate_routes(plan.routes, inst) is not None
