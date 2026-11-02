from __future__ import annotations

import importlib.util
import time
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_route_edges_include_depot_arcs():
    m = load("measure_gnn_recall")
    assert m.route_edges([[1, 2], [3]]) == {(0, 1), (1, 2), (2, 0), (0, 3), (3, 0)}


def test_edge_counts_exclude_self_loops_and_apply_the_threshold():
    m = load("measure_gnn_recall")
    heatmap = np.array([[0.9, 0.5, 0.0], [0.0, 0.9, 0.5], [0.5, 0.0, 0.9]])
    assert m.edge_counts(heatmap, {(0, 1), (1, 2), (2, 1)}, 0.1) == (2, 3, 3, 6)


def test_pooling_is_micro_aggregated():
    m = load("measure_gnn_recall")
    base = {"customers": 100, "threshold": 0.01, "source": "PyVRP-ILS", "candidates": 100}
    rows = [
        {**base, "retained_edges": 1, "edges": 1, "retained_candidates": 10},
        {**base, "retained_edges": 1, "edges": 3, "retained_candidates": 30},
    ]
    row = m.pool_by_size(rows)[0]
    assert row["edge_recall"] == pytest.approx(0.5) and row["candidate_retention"] == pytest.approx(0.2)


def test_timers_are_exclusive_of_nested_calls():
    m = load("measure_component_cost")
    timers = m.Timers()
    inner = timers.wrap(lambda: time.sleep(0.02), "inner")

    def outer_body():
        inner()
        time.sleep(0.02)

    timers.wrap(outer_body, "outer")()
    assert timers.calls == {"inner": 1, "outer": 1}
    assert timers.seconds["inner"] >= 0.018 and 0.018 <= timers.seconds["outer"] < 0.035


class FakeCfg:
    lac_warmup = 2


class FakeLac:
    cfg = FakeCfg()

    def __init__(self):
        self.step = 0

    def decide(self, feats, cur_best_cost, tau=None, *, sa_probability=None):
        self.step += 1
        return self.step % 2 == 0, 0.9 if self.step == 3 else 0.1


def test_lac_activity_separates_warmup_and_classifier_approvals():
    m = load("measure_component_cost")
    lac = FakeLac()
    activity = m.LacActivity()
    activity.wrap(lac)
    for _ in range(4):
        lac.decide(None, 1.0, tau=0.5, sa_probability=0.0)
    assert activity.counts == {"consulted": 4, "warmup": 1, "classifier_approved": 1, "accepted": 2}
