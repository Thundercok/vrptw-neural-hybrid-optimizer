"""Registered paired instance/geometry/seed estimands; no benchmark execution."""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def nullable(value):
    return float(value) if np.isfinite(value) else None


def validate_records(rows, metadata=None):
    indexed = {}
    observed = {}
    for row in rows:
        key = (row["instance"], row["case_id"], row["seed"], row["cutoff_sec"])
        require(key not in indexed, "duplicate statistical cell")
        require(
            type(row["seed"]) is int and type(row["cutoff_sec"]) is int and row["cutoff_sec"] > 0,
            "invalid cell identity",
        )
        require(
            isinstance(row["instance"], str) and row["instance"] and isinstance(row["case_id"], str) and row["case_id"],
            "invalid labels",
        )
        require(
            type(row["customers"]) is int
            and row["customers"] > 0
            and isinstance(row["geometry_sha256"], str)
            and row["geometry_sha256"],
            "invalid geometry metadata",
        )
        require(
            all(type(row[k]) is bool for k in ("available", "integrity_ok", "return_ok", "binding_ok")), "invalid flags"
        )
        require(row["integrity_ok"], "protocol-invalid data cannot enter inference")
        if row["available"]:
            require(
                type(row["nv"]) is int and row["nv"] > 0 and finite(row["td"]) and row["td"] >= 0,
                "invalid available objective",
            )
        else:
            require(row["nv"] is None and row["td"] is None, "failure has invented objectives")
        identity = {"customers": row["customers"], "geometry_sha256": row["geometry_sha256"]}
        require(observed.get(row["instance"], identity) == identity, "inconsistent instance geometry")
        if metadata is not None:
            require(
                row["instance"] in metadata and all(metadata[row["instance"]][k] == v for k, v in identity.items()),
                "geometry identity mismatch",
            )
        observed[row["instance"]] = identity
        indexed[key] = row
    return indexed


def make_draws(metadata, seeds, replicates=10000, seed=20261019):
    require(type(replicates) is int and replicates > 0, "invalid replicate count")
    labels = sorted(seeds)
    require(labels and len(labels) == len(set(labels)) and all(type(s) is int for s in labels), "invalid seed labels")
    require(metadata, "empty instance universe")
    rng = np.random.default_rng(seed)
    groups = {
        size: sorted({r["geometry_sha256"] for r in metadata.values() if r["customers"] == size})
        for size in sorted({r["customers"] for r in metadata.values()})
    }
    return {
        "seeds": labels,
        "seed_indices": rng.integers(0, len(labels), size=(replicates, len(labels))),
        "groups": groups,
        "group_indices": {size: rng.integers(0, len(ids), size=(replicates, len(ids))) for size, ids in groups.items()},
        "rng_seed": seed,
    }


def draw_weights(metadata, names, draws):
    require(len(names) == len(set(names)) and names, "duplicate/empty instance selection")
    selected = np.asarray(draws["seed_indices"])
    labels = draws["seeds"]
    require(
        selected.ndim == 2
        and selected.shape[1] == len(labels)
        and np.issubdtype(selected.dtype, np.integer)
        and np.all((0 <= selected) & (selected < len(labels))),
        "invalid seed draws",
    )
    seed_counts = (selected[:, :, None] == np.arange(len(labels))).sum(axis=1)
    counts = np.zeros((len(selected), len(names)), dtype=np.int64)
    for i, name in enumerate(names):
        entry = metadata[name]
        size = entry["customers"]
        groups = draws["groups"][size]
        group_index = groups.index(entry["geometry_sha256"])
        indices = np.asarray(draws["group_indices"][size])
        require(
            indices.shape == (len(selected), len(groups))
            and np.issubdtype(indices.dtype, np.integer)
            and np.all((0 <= indices) & (indices < len(groups))),
            "invalid geometry draws",
        )
        counts[:, i] = (indices == group_index).sum(axis=1)
    return counts, seed_counts


def _stratify(values, counts, metadata, names, weights):
    sizes = np.array([metadata[n]["customers"] for n in names])
    require(
        set(weights) == set(sizes)
        and all(finite(w) and w > 0 for w in weights.values())
        and math.isclose(sum(weights.values()), 1, abs_tol=1e-12),
        "invalid fixed stratum weights",
    )
    result = np.zeros(values.shape[1])
    for size, weight in weights.items():
        keep = sizes == size
        v, c = values[keep], counts[:, keep].T
        denominator = (c * np.isfinite(v)).sum(axis=0)
        numerator = (c * np.nan_to_num(v, nan=0)).sum(axis=0)
        mean = np.divide(
            numerator, denominator, out=np.full_like(numerator, np.nan, dtype=float), where=denominator > 0
        )
        result += weight * mean
    return result


def _seed_mean(values, valid, seed_counts):
    denominator = valid.astype(int) @ seed_counts.T
    numerator = np.where(valid, values, 0) @ seed_counts.T
    return np.divide(numerator, denominator, out=np.full_like(numerator, np.nan, dtype=float), where=denominator > 0)


def percentile_interval(values, family_size=1):
    require(type(family_size) is int and family_size > 0, "invalid comparison family")
    values = np.asarray(values, dtype=float)
    require(values.ndim == 1 and len(values) > 0, "empty or malformed bootstrap")
    undefined = int((~np.isfinite(values)).sum())
    lower, upper = (
        (None, None)
        if undefined
        else map(float, np.quantile(values, [0.025 / family_size, 1 - 0.025 / family_size], method="linear"))
    )
    return {
        "lower": lower,
        "upper": upper,
        "level": 1 - 0.05 / family_size,
        "family_size": family_size,
        "undefined_replicates": undefined,
        "suppressed": bool(undefined),
    }


def _cube(rows, metadata, names, cases, cutoff, seeds):
    indexed = validate_records(rows, metadata)
    nv, td, available = [], [], []
    for case in cases:
        chosen = []
        for name in names:
            require(all((name, case, s, cutoff) in indexed for s in seeds), "missing paired cell")
            chosen.append([indexed[name, case, s, cutoff] for s in seeds])
        available.append(np.array([[r["available"] for r in line] for line in chosen], dtype=bool))
        nv.append(np.array([[r["nv"] if r["available"] else np.nan for r in line] for line in chosen]))
        td.append(np.array([[r["td"] if r["available"] else np.nan for r in line] for line in chosen], dtype=float))
    return np.array(nv), np.array(td), np.array(available)


def analyze_pair(rows, metadata, names, treatment, control, cutoff, draws, weights, family_size=1):
    nv, td, available = _cube(rows, metadata, names, [treatment, control], cutoff, draws["seeds"])
    t, c = available
    both = t & c
    score = np.where(t & ~c, 1, np.where(c & ~t, -1, np.where(both, np.sign(nv[1] - nv[0]), 0)))
    matched = both & (nv[0] == nv[1])
    raw_gap = np.where(matched, td[0] - td[1], 0)
    zero_control = matched & (td[1] == 0)
    pct_gap = np.divide(100 * raw_gap, td[1], out=np.zeros_like(raw_gap), where=matched & (td[1] > 0))
    counts, seed_counts = draw_weights(metadata, names, draws)
    point_counts = np.ones((1, len(names)), dtype=int)
    point_seeds = np.ones((1, len(draws["seeds"])), dtype=int)

    def estimate(ic, sc):
        scores = score @ sc.T / len(draws["seeds"])
        pct = _seed_mean(pct_gap, matched, sc)
        raw = _seed_mean(raw_gap, matched, sc)
        result = {
            "fleet_score": _stratify(scores, ic, metadata, names, weights),
            "td_pct": _stratify(pct, ic, metadata, names, weights),
            "td_raw": _stratify(raw, ic, metadata, names, weights),
            "matched_pairs": ((matched.astype(int) @ sc.T) * ic.T).sum(axis=0),
            "matched_instances": (np.isfinite(raw) * ic.T).sum(axis=0),
        }
        invalid = ((zero_control.astype(int) @ sc.T) * ic.T).sum(axis=0) > 0
        result["td_pct"][invalid] = np.nan
        return result, pct, raw

    point, pct, _ = estimate(point_counts, point_seeds)
    reps, _, _ = estimate(counts, seed_counts)
    complete = both.all(axis=1)
    sums_t, sums_c = np.nansum(nv[0], axis=1), np.nansum(nv[1], axis=1)
    matched_values = pct[:, 0][matched.any(axis=1)]
    descriptive = float(matched_values.mean()) if len(matched_values) and not zero_control.any() else None
    summary = {
        "fleet_score": float(point["fleet_score"][0]),
        "td_pct_stratified": nullable(point["td_pct"][0]),
        "td_raw_stratified": nullable(point["td_raw"][0]),
        "td_pct_unweighted": descriptive,
        "matched_pairs": int(matched.sum()),
        "matched_instances": int(matched.any(axis=1).sum()),
        "both_failed_pairs": int((~t & ~c).sum()),
        "fleet_tie_success_pairs": int((both & (nv[0] == nv[1])).sum()),
        "treatment_available": int(t.sum()),
        "control_available": int(c.sum()),
        "total_seed_pairs": int(t.size),
        "complete_seed_instances": int(complete.sum()),
        "excluded_complete_seed_instances": int((~complete).sum()),
        "mean_nv_wtl": {
            "win": int((complete & (sums_t < sums_c)).sum()),
            "tie": int((complete & (sums_t == sums_c)).sum()),
            "loss": int((complete & (sums_t > sums_c)).sum()),
        },
    }
    return {
        "point": summary,
        "replicates": reps,
        "intervals": {key: percentile_interval(reps[key], family_size) for key in ("fleet_score", "td_pct", "td_raw")},
    }


def analyze_interaction(rows, metadata, names, contrast, cutoff, draws, weights):
    require(len(contrast) == 4 and sorted(contrast.values()) == [-1, -1, 1, 1], "invalid bundle interaction")
    cases = list(contrast)
    nv, _, available = _cube(rows, metadata, names, cases, cutoff, draws["seeds"])
    valid = available.all(axis=0)
    values = sum(contrast[case] * np.nan_to_num(nv[i], nan=0) for i, case in enumerate(cases))
    counts, seeds = draw_weights(metadata, names, draws)
    point_values = _seed_mean(values, valid, np.ones((1, len(draws["seeds"])), dtype=int))
    observed = _stratify(point_values, np.ones((1, len(names)), dtype=int), metadata, names, weights)[0]
    reps = _stratify(_seed_mean(values, valid, seeds), counts, metadata, names, weights)
    return {
        "point": {
            "nv_interaction": nullable(observed),
            "eligible_seed_units": int(valid.sum()),
            "eligible_instances": int(valid.any(axis=1).sum()),
            "total_seed_units": int(valid.size),
        },
        "replicates": {
            "nv_interaction": reps,
            "eligible_seed_units": ((valid.astype(int) @ seeds.T) * counts.T).sum(axis=0),
        },
        "intervals": {"nv_interaction": percentile_interval(reps)},
    }


def seed_summary(rows):
    validate_records(rows)
    groups = defaultdict(list)
    for row in rows:
        groups[row["instance"], row["case_id"], row["cutoff_sec"]].append(row)
    summaries = []
    for (name, case, cutoff), records in sorted(groups.items()):
        valid = [r for r in records if r["available"]]

        def emit(metric, fleet, values, *, name=name, case=case, cutoff=cutoff, records=records):
            values = np.array(values, dtype=float)
            summaries.append(
                {
                    "instance": name,
                    "case_id": case,
                    "cutoff_sec": cutoff,
                    "metric": metric,
                    "fleet": fleet,
                    "valid_runs": len(values),
                    "declared_runs": len(records),
                    "mean": float(values.mean()) if len(values) else None,
                    "median": float(np.median(values)) if len(values) else None,
                    "sample_sd": float(values.std(ddof=1)) if len(values) > 1 else None,
                    "minimum": float(values.min()) if len(values) else None,
                    "maximum": float(values.max()) if len(values) else None,
                    "return_failures": sum(not r["return_ok"] for r in records),
                    "unverified_binding_runs": sum(not r["binding_ok"] for r in records),
                }
            )

        emit("nv", None, [r["nv"] for r in valid])
        for fleet in sorted({r["nv"] for r in valid}):
            emit("td_at_nv", fleet, [r["td"] for r in valid if r["nv"] == fleet])
    return summaries
