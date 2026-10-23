from __future__ import annotations

import copy
import importlib
import math

import numpy as np
import pytest


def api():
    return importlib.import_module("vrptw.sweep_statistics")


def row(name, case, seed, nv, td=100.0, *, group="g", size=100, cutoff=300):
    return {
        "instance": name,
        "case_id": case,
        "seed": seed,
        "cutoff_sec": cutoff,
        "customers": size,
        "geometry_sha256": group,
        "available": nv is not None,
        "nv": nv,
        "td": td if nv is not None else None,
        "integrity_ok": True,
        "return_ok": True,
        "binding_ok": True,
    }


def metadata(rows):
    return {r["instance"]: {"customers": r["customers"], "geometry_sha256": r["geometry_sha256"]} for r in rows}


def test_paired_failures_fleet_and_seed_matched_distance():
    m = api()
    # Exactly one same-fleet pair; a mean-fleet match cannot create another TD pair.
    rows = [
        row("a", "T", 42, 1, 90),
        row("a", "C", 42, 1, 100),
        row("a", "T", 43, 2, 1),
        row("a", "C", 43, 1, 100),
        row("a", "T", 44, None),
        row("a", "C", 44, None),
        row("b", "T", 42, 1),
        row("b", "C", 42, None),
        row("b", "T", 43, None),
        row("b", "C", 43, 1),
        row("b", "T", 44, 1),
        row("b", "C", 44, 2),
    ]
    meta = metadata(rows)
    draws = m.make_draws(meta, [42, 43, 44], 100, 20261019)
    result = m.analyze_pair(rows, meta, ["a", "b"], "T", "C", 300, draws, {100: 1})
    p = result["point"]
    assert p["fleet_score"] == pytest.approx(0)
    assert p["both_failed_pairs"] == 1 and p["matched_pairs"] == 1 and p["matched_instances"] == 1
    assert p["td_pct_unweighted"] == pytest.approx(-10)
    assert p["td_pct_stratified"] == pytest.approx(-10)
    assert p["complete_seed_instances"] == 0 and p["mean_nv_wtl"] == {"win": 0, "tie": 0, "loss": 0}
    assert result["intervals"]["td_pct"]["suppressed"]
    assert result["intervals"]["td_pct"]["undefined_replicates"] > 0


def test_complete_five_seed_nv_counts_and_sample_sd():
    m = api()
    rows = []
    for seed, nv in zip(range(42, 47), [1, 2, 3, 4, 5], strict=True):
        rows.extend([row("a", "T", seed, nv), row("a", "C", seed, nv + 1)])
    meta = metadata(rows)
    draws = m.make_draws(meta, list(range(42, 47)), 25, 1)
    result = m.analyze_pair(rows, meta, ["a"], "T", "C", 300, draws, {100: 1})
    assert result["point"]["mean_nv_wtl"] == {"win": 1, "tie": 0, "loss": 0}
    assert result["point"]["fleet_score"] == 1
    summary = next(r for r in m.seed_summary(rows) if r["case_id"] == "T" and r["metric"] == "nv")
    assert summary["mean"] == summary["median"] == 3
    assert summary["sample_sd"] == pytest.approx(math.sqrt(2.5))
    assert (summary["minimum"], summary["maximum"], summary["valid_runs"]) == (1, 5, 5)
    td = m.seed_summary(rows)
    assert all(r["fleet"] is not None for r in td if r["metric"] == "td_at_nv")


def test_global_draws_preserve_clusters_multiplicity_and_seed_pairing():
    m = api()
    meta = {
        "a": {"customers": 100, "geometry_sha256": "x"},
        "b": {"customers": 100, "geometry_sha256": "x"},
        "c": {"customers": 100, "geometry_sha256": "y"},
        "d": {"customers": 200, "geometry_sha256": "z"},
    }
    draws = m.make_draws(meta, [43, 42], 40, 20261019)
    again = m.make_draws(meta, [42, 43], 40, 20261019)
    assert np.array_equal(draws["seed_indices"], again["seed_indices"])
    counts, seeds = m.draw_weights(meta, ["a", "b", "c", "d"], draws)
    assert np.array_equal(counts[:, 0], counts[:, 1])
    assert np.any(counts[:, 0] == 2) and np.any(counts[:, 0] == 0)
    assert np.all(seeds.sum(axis=1) == 2)
    subset, _ = m.draw_weights(meta, ["a", "c"], draws)
    assert np.array_equal(subset, counts[:, [0, 2]])


def test_vectorized_bootstrap_matches_independent_scalar_loop_with_unequal_clusters():
    m = api()
    rows = []
    specs = [
        ("a", "x", 100, [1, 2], [2, 1]),
        ("b", "x", 100, [2, 2], [2, 2]),
        ("c", "y", 100, [4, 2], [3, 3]),
        ("d", "z", 200, [1, 1], [2, 1]),
    ]
    for name, group, size, t, c in specs:
        for j, seed in enumerate([42, 43]):
            rows.extend(
                [row(name, "T", seed, t[j], group=group, size=size), row(name, "C", seed, c[j], group=group, size=size)]
            )
    meta = metadata(rows)
    names = list(meta)
    draws = m.make_draws(meta, [42, 43], 40, 9)
    weights = {100: 0.75, 200: 0.25}
    result = m.analyze_pair(rows, meta, names, "T", "C", 300, draws, weights)
    counts, seed_counts = m.draw_weights(meta, names, draws)
    reference = []
    indexed = {(r["instance"], r["case_id"], r["seed"]): r for r in rows}
    for b in range(40):
        total = 0
        for size, weight in weights.items():
            samples = []
            for i, name in enumerate(names):
                if meta[name]["customers"] != size:
                    continue
                values = []
                for s, seed in enumerate(draws["seeds"]):
                    t = indexed[name, "T", seed]["nv"]
                    c = indexed[name, "C", seed]["nv"]
                    values.extend([int(c > t) - int(c < t)] * int(seed_counts[b, s]))
                samples.extend([sum(values) / len(values)] * int(counts[b, i]))
            total += weight * sum(samples) / len(samples)
        reference.append(total)
    assert np.allclose(result["replicates"]["fleet_score"], reference)


def test_conditional_td_bootstrap_matches_scalar_seed_and_geometry_resampling():
    m = api()
    rows = []
    for name, group, size in [("a", "x", 100), ("b", "x", 100), ("c", "y", 100), ("d", "z", 200)]:
        for seed in (42, 43, 44):
            nv = 2 if name == "c" and seed == 44 else 1
            rows.extend(
                [
                    row(name, "T", seed, nv, 70.0 + seed + len(name), group=group, size=size),
                    row(name, "C", seed, 1, 100.0 + 2 * seed, group=group, size=size),
                ]
            )
    meta = metadata(rows)
    names = list(meta)
    draws = m.make_draws(meta, [42, 43, 44], 50, 19)
    result = m.analyze_pair(rows, meta, names, "T", "C", 300, draws, {100: 0.8, 200: 0.2})
    indexed = {(r["instance"], r["case_id"], r["seed"]): r for r in rows}
    reference = []
    for b in range(50):
        total = 0.0
        for size, weight in {100: 0.8, 200: 0.2}.items():
            sampled = []
            for gi in draws["group_indices"][size][b]:
                group = draws["groups"][size][gi]
                for name in names:
                    if meta[name] != {"customers": size, "geometry_sha256": group}:
                        continue
                    values = []
                    for si in draws["seed_indices"][b]:
                        seed = draws["seeds"][si]
                        t = indexed[name, "T", seed]
                        c = indexed[name, "C", seed]
                        if t["nv"] == c["nv"]:
                            values.append(100 * (t["td"] - c["td"]) / c["td"])
                    if values:
                        sampled.append(sum(values) / len(values))
            total += weight * sum(sampled) / len(sampled)
        reference.append(total)
    assert np.allclose(result["replicates"]["td_pct"], reference)


def test_stratified_conditional_td_does_not_silently_renormalize_missing_size():
    m = api()
    rows = [
        row("a", "T", 42, 1, 90),
        row("a", "C", 42, 1, 100),
        row("b", "T", 42, 1, size=200),
        row("b", "C", 42, 2, size=200),
    ]
    meta = metadata(rows)
    draws = m.make_draws(meta, [42], 10, 1)
    result = m.analyze_pair(rows, meta, ["a", "b"], "T", "C", 300, draws, {100: 0.75, 200: 0.25})
    assert result["point"]["td_pct_unweighted"] == -10
    assert result["point"]["td_pct_stratified"] is None
    assert result["intervals"]["td_pct"]["suppressed"]


def test_bonferroni_percentile_levels_are_exact_and_undefined_draws_are_kept():
    m = api()
    values = np.arange(10001, dtype=float)
    ci = m.percentile_interval(values, 8)
    assert ci["lower"] == pytest.approx(31.25) and ci["upper"] == pytest.approx(9968.75)
    assert ci["level"] == pytest.approx(1 - 0.05 / 8)
    values[0] = np.nan
    ci = m.percentile_interval(values, 8)
    assert ci["suppressed"] and ci["undefined_replicates"] == 1 and ci["lower"] is None


def test_equal_mean_fleet_does_not_create_seed_level_td_matches():
    m = api()
    rows = [row("a", "T", 42, 1), row("a", "T", 43, 3), row("a", "C", 42, 3), row("a", "C", 43, 1)]
    meta = metadata(rows)
    draws = m.make_draws(meta, [42, 43], 10, 1)
    result = m.analyze_pair(rows, meta, ["a"], "T", "C", 300, draws, {100: 1})
    assert result["point"]["mean_nv_wtl"]["tie"] == 1
    assert result["point"]["matched_pairs"] == 0 and result["point"]["td_pct_unweighted"] is None


def test_zero_distance_denominator_is_explicitly_undefined():
    m = api()
    rows = [row("a", "T", 42, 1, 0), row("a", "C", 42, 1, 0)]
    meta = metadata(rows)
    draws = m.make_draws(meta, [42], 10, 1)
    result = m.analyze_pair(rows, meta, ["a"], "T", "C", 300, draws, {100: 1})
    assert result["point"]["matched_pairs"] == 1 and result["point"]["td_raw_stratified"] == 0
    assert result["point"]["td_pct_stratified"] is None and result["intervals"]["td_pct"]["suppressed"]


def test_bundle_interaction_uses_raw_nv_and_reports_complete_seed_selection():
    m = api()
    rows = []
    for case, nv in [("F111111", 2), ("F110000", 3), ("F001111", 4), ("F000000", 6)]:
        rows.extend([row("a", case, 42, nv), row("a", case, 43, None if case == "F001111" else nv)])
    meta = metadata(rows)
    draws = m.make_draws(meta, [42, 43], 100, 4)
    result = m.analyze_interaction(
        rows, meta, ["a"], {"F111111": 1, "F110000": -1, "F001111": -1, "F000000": 1}, 300, draws, {100: 1}
    )
    assert result["point"]["nv_interaction"] == 1 and result["point"]["eligible_seed_units"] == 1
    assert result["intervals"]["nv_interaction"]["suppressed"]


@pytest.mark.parametrize(
    "defect", ["duplicate", "missing_pair", "protocol", "nv_bool", "td_nan", "geometry", "availability"]
)
def test_invalid_or_unpaired_input_is_rejected(defect):
    m = api()
    rows = [row("a", "T", 42, 1), row("a", "C", 42, 1)]
    meta = metadata(rows)
    if defect == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif defect == "missing_pair":
        rows.pop()
    elif defect == "protocol":
        rows[0]["integrity_ok"] = False
    elif defect == "nv_bool":
        rows[0]["nv"] = True
    elif defect == "td_nan":
        rows[0]["td"] = float("nan")
    elif defect == "geometry":
        rows[0]["geometry_sha256"] = "other"
    elif defect == "availability":
        rows[0]["available"] = False
    draws = m.make_draws(meta, [42], 3, 1)
    with pytest.raises(ValueError):
        m.analyze_pair(rows, meta, ["a"], "T", "C", 300, draws, {100: 1})
