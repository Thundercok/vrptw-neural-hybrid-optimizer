"""Revision analysis of the closed sweep with a disclosed missing-data treatment.

Inputs: the closed sweep records, its infrastructure-gap inventory, and the
ALNS-Base R1_2_5 rerun after the build_greedy depot-deadline fix.

Estimands follow vrptw.sweep_statistics (registered design): per-seed paired fleet
score sign(NV_control - NV_treatment), fleet-matched TD gap, fixed size-stratum
weights and a geometry/seed bootstrap with the registered draws (10000, seed
20261019). Amendment: the registered analysis requires every declared cell. The
21 infrastructure gaps are not algorithm outcomes, so the primary treatment drops
the affected seed pair from that comparison only. Two bounds are reported:
"gap_as_failure" (a gap counts as no solution for its own case) and "worst_case"
(treatment gaps count as treatment failures; control gaps are dropped).
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))
from vrptw import sweep_statistics as stats  # noqa: E402

SWEEP = ROOT / "results/cutoff_clock_audit_20261029/run"
RERUN = ROOT / "results/alns_greedy_fix_20261101/run/records.csv"
BLIND_RECORDS = ROOT / "results/reference_blind_t300_20261101/run/records.csv"
DESIGN = ROOT / "results/ablation_design_20261019"
BKS = ROOT / "data/reference/sintef_official_bks.json"
RETURN_UPPER_SLACK = 0.5
TREATMENT = "F111111"
BLIND = "F111111-blind"
GAP_MODES = ("drop_pair", "gap_as_failure", "worst_case")


def load_rows():
    rows = []
    with (SWEEP / "records.csv").open(newline="") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "instance": r["instance"],
                    "case_id": r["case_id"],
                    "seed": int(r["seed"]),
                    "cutoff_sec": int(r["cutoff_sec"]),
                    "customers": int(r["customers"]),
                    "geometry_sha256": r["geometry_sha256"],
                    "available": r["available"] == "True",
                    "nv": int(r["nv"]) if r["nv"] else None,
                    "td": float(r["td"]) if r["td"] else None,
                    "integrity_ok": r["integrity_ok"] == "True",
                    "return_ok": r["return_ok"] == "True",
                    "binding_ok": r["binding_ok"] == "True",
                }
            )
    geometry = {r["instance"]: (r["customers"], r["geometry_sha256"]) for r in rows}
    # Replace the 20 ALNS-Base R1_2_5 rows that failed on the infeasible greedy start.
    replaced = [r for r in rows if r["instance"] == "R1_2_5" and r["case_id"] == "ALNS-Base"]
    stats.require(len(replaced) == 20 and not any(r["available"] for r in replaced), "unexpected R1_2_5 rows")
    rows = [r for r in rows if r not in replaced]
    with RERUN.open(newline="") as f:
        rerun = list(csv.DictReader(f))
    stats.require(len(rerun) == 20 and all(r["available"] == "True" for r in rerun), "rerun incomplete")
    customers, geometry_sha = geometry["R1_2_5"]
    for r in rerun:
        cutoff = int(r["cutoff_sec"])
        rows.append(
            {
                "instance": "R1_2_5",
                "case_id": "ALNS-Base",
                "seed": int(r["seed"]),
                "cutoff_sec": cutoff,
                "customers": customers,
                "geometry_sha256": geometry_sha,
                "available": True,
                "nv": int(r["nv"]),
                "td": float(r["td"]),
                "integrity_ok": True,
                "return_ok": float(r["runtime_sec"]) <= cutoff + RETURN_UPPER_SLACK,
                "binding_ok": True,
            }
        )
    gaps = []
    for g in json.loads((SWEEP / "infrastructure_failures.json").read_text()):
        parts = g["run"].split("_")
        gaps.append(("_".join(parts[1:-3]), parts[-3], int(parts[-2][1:]), int(parts[-1][1:])))
    present = {(r["instance"], r["case_id"], r["seed"], r["cutoff_sec"]) for r in rows}
    stats.require(len(gaps) == 21 and not present & set(gaps), "gap inventory overlaps records")
    for name, case, seed, cutoff in gaps:
        customers, geometry_sha = geometry[name]
        rows.append(
            {
                "instance": name,
                "case_id": case,
                "seed": seed,
                "cutoff_sec": cutoff,
                "customers": customers,
                "geometry_sha256": geometry_sha,
                "available": False,
                "nv": None,
                "td": None,
                "integrity_ok": True,
                "return_ok": False,
                "binding_ok": False,
            }
        )
    metadata = {n: {"customers": c, "geometry_sha256": s} for n, (c, s) in geometry.items()}
    return rows, metadata, set(gaps)


def add_blind_rows(rows, metadata):
    """Append the reference-blind T300 cells; a cell that failed validation counts as no solution."""
    with BLIND_RECORDS.open(newline="") as f:
        blind = list(csv.DictReader(f))
    keys = {(r["instance"], int(r["seed"])) for r in blind}
    stats.require(
        len(blind) == 370 and len(keys) == 370 and {k[0] for k in keys} == set(metadata), "blind run incomplete"
    )
    for r in blind:
        ok = r["available"] == "True"
        rows.append(
            {
                "instance": r["instance"],
                "case_id": BLIND,
                "seed": int(r["seed"]),
                "cutoff_sec": 300,
                **metadata[r["instance"]],
                "available": ok,
                "nv": int(r["nv"]) if ok else None,
                "td": float(r["td"]) if ok else None,
                "integrity_ok": True,
                "return_ok": ok and float(r["runtime_sec"]) <= 300 + RETURN_UPPER_SLACK,
                "binding_ok": ok,
            }
        )


def analyze_pair(rows, metadata, names, treatment, control, cutoff, draws, weights, gaps, mode, family_size=1):
    """sweep_statistics.analyze_pair with an explicit observed mask for gap cells."""
    seeds = draws["seeds"]
    nv, td, available = stats._cube(rows, metadata, names, [treatment, control], cutoff, seeds)
    gap = np.array(
        [[[(n, case, s, cutoff) in gaps for s in seeds] for n in names] for case in (treatment, control)], dtype=bool
    )
    if mode == "drop_pair":
        observed = ~(gap[0] | gap[1])
    elif mode == "gap_as_failure":
        observed = np.ones_like(gap[0])
    else:
        observed = ~gap[1]
    t, c = available & observed
    both = t & c
    score = np.where(t & ~c, 1, np.where(c & ~t, -1, np.where(both, np.sign(nv[1] - nv[0]), 0)))
    matched = both & (nv[0] == nv[1])
    raw_gap = np.where(matched, td[0] - td[1], 0)
    pct_gap = np.divide(100 * raw_gap, td[1], out=np.zeros_like(raw_gap), where=matched & (td[1] > 0))
    counts, seed_counts = stats.draw_weights(metadata, names, draws)
    one_i = np.ones((1, len(names)), dtype=int)
    one_s = np.ones((1, len(seeds)), dtype=int)

    def estimate(ic, sc):
        return {
            "fleet_score": stats._stratify(stats._seed_mean(score, observed, sc), ic, metadata, names, weights),
            "td_pct": stats._stratify(stats._seed_mean(pct_gap, matched, sc), ic, metadata, names, weights),
            "td_raw": stats._stratify(stats._seed_mean(raw_gap, matched, sc), ic, metadata, names, weights),
        }

    point = estimate(one_i, one_s)
    reps = estimate(counts, seed_counts)
    mean_t = np.nanmean(np.where(t, nv[0], np.nan), axis=1)
    mean_c = np.nanmean(np.where(c, nv[1], np.nan), axis=1)
    usable = np.isfinite(mean_t) & np.isfinite(mean_c)
    return {
        "fleet_score": stats.nullable(point["fleet_score"][0]),
        "td_pct": stats.nullable(point["td_pct"][0]),
        "td_raw": stats.nullable(point["td_raw"][0]),
        "intervals": {k: stats.percentile_interval(reps[k], family_size) for k in reps},
        "seed_pairs_used": int(observed.sum()),
        "seed_pairs_total": int(observed.size),
        "seed_wins": int((observed & (score > 0)).sum()),
        "seed_ties": int((observed & (score == 0)).sum()),
        "seed_losses": int((observed & (score < 0)).sum()),
        "matched_pairs": int(matched.sum()),
        "matched_instances": int(matched.any(axis=1).sum()),
        "treatment_no_solution": int((observed & ~available[0]).sum()),
        "control_no_solution": int((observed & ~available[1]).sum()),
        "mean_nv_instance_wtl": {
            "win": int((usable & (mean_t < mean_c)).sum()),
            "tie": int((usable & (mean_t == mean_c)).sum()),
            "loss": int((usable & (mean_t > mean_c)).sum()),
        },
    }


def descriptive(rows, gaps):
    bks = json.loads(BKS.read_text())["instances"]
    groups = defaultdict(list)
    for r in rows:
        if (r["instance"], r["case_id"], r["seed"], r["cutoff_sec"]) in gaps:
            continue
        groups[r["case_id"], r["cutoff_sec"], r["customers"]].append(r)
    out = []
    for (case, cutoff, size), rs in sorted(groups.items()):
        ok = [r for r in rs if r["available"]]
        gaps_bks = []
        for r in ok:
            ref = bks.get(r["instance"]) or bks.get(r["instance"].lower())
            if isinstance(ref, dict) and ref.get("nv"):
                gaps_bks.append(r["nv"] - ref["nv"])
        out.append(
            {
                "case_id": case,
                "cutoff_sec": cutoff,
                "customers": size,
                "runs": len(rs),
                "available": len(ok),
                "mean_nv": float(np.mean([r["nv"] for r in ok])) if ok else None,
                "mean_td": float(np.mean([r["td"] for r in ok])) if ok else None,
                "mean_nv_minus_bks": float(np.mean(gaps_bks)) if gaps_bks else None,
                "return_late": sum(not r["return_ok"] for r in ok),
            }
        )
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/revision_analysis_20261101")
    parser.add_argument("--replicates", type=int, default=10000)
    parser.add_argument("--blind", action="store_true", help="add the reference-blind T300 comparisons")
    args = parser.parse_args(argv)
    rows, metadata, gaps = load_rows()
    design = json.loads((DESIGN / "design.json").read_text())
    contrasts = json.loads((DESIGN / "contrasts.json").read_text())
    names = sorted(metadata)
    stats.require(len(names) == 74, "instance universe differs")
    draws = stats.make_draws(metadata, design["seeds"], args.replicates, 20261019)
    main_weights = {s: sum(m["customers"] == s for m in metadata.values()) / len(names) for s in (100, 200, 400)}
    results = []
    for cutoff in design["primary_cutoffs_sec"]:
        for control in ("ALNS-Base", "PyVRP-ILS", "NeuroLKH-adapted"):
            for mode in GAP_MODES:
                results.append(
                    {
                        "analysis": "primary",
                        "cutoff_sec": cutoff,
                        "treatment": TREATMENT,
                        "control": control,
                        "scope": "all_74",
                        "gap_mode": mode,
                        **analyze_pair(
                            rows,
                            metadata,
                            names,
                            TREATMENT,
                            control,
                            cutoff,
                            draws,
                            main_weights,
                            gaps,
                            mode,
                            3 if cutoff == 300 else 1,
                        ),
                    }
                )
            for size in (100, 200, 400):
                subset = [n for n in names if metadata[n]["customers"] == size]
                results.append(
                    {
                        "analysis": "primary_by_size",
                        "cutoff_sec": cutoff,
                        "treatment": TREATMENT,
                        "control": control,
                        "scope": f"size_{size}",
                        "gap_mode": "drop_pair",
                        **analyze_pair(
                            rows, metadata, subset, TREATMENT, control, cutoff, draws, {size: 1.0}, gaps, "drop_pair"
                        ),
                    }
                )
    ablation_names = design["ablation_instances"]
    for cutoff in design["ablation_cutoffs_sec"]:
        for contrast in contrasts:
            if len(contrast["weights"]) != 2:
                continue
            treatment = next(k for k, v in contrast["weights"].items() if v == 1)
            control = next(k for k, v in contrast["weights"].items() if v == -1)
            primary = cutoff == 300 and contrast["role"] == "primary_ablation_300s"
            results.append(
                {
                    "analysis": f"ablation:{contrast['id']}",
                    "cutoff_sec": cutoff,
                    "treatment": treatment,
                    "control": control,
                    "scope": "ablation_18",
                    "gap_mode": "drop_pair",
                    "role": "primary_ablation_300s" if primary else "exploratory",
                    **analyze_pair(
                        rows,
                        metadata,
                        ablation_names,
                        treatment,
                        control,
                        cutoff,
                        draws,
                        {100: 1 / 3, 200: 1 / 3, 400: 1 / 3},
                        gaps,
                        "drop_pair",
                        8 if primary else 1,
                    ),
                }
            )
    if args.blind:
        add_blind_rows(rows, metadata)
        for control in (TREATMENT, "ALNS-Base", "PyVRP-ILS", "NeuroLKH-adapted"):
            scopes = [("all_74", names, main_weights)] + [
                (f"size_{size}", [n for n in names if metadata[n]["customers"] == size], {size: 1.0})
                for size in (100, 200, 400)
            ]
            for scope, subset, weights in scopes:
                results.append(
                    {
                        "analysis": "reference_blind",
                        "cutoff_sec": 300,
                        "treatment": BLIND,
                        "control": control,
                        "scope": scope,
                        "gap_mode": "drop_pair",
                        **analyze_pair(
                            rows,
                            metadata,
                            subset,
                            BLIND,
                            control,
                            300,
                            draws,
                            weights,
                            gaps,
                            "drop_pair",
                            4 if scope == "all_74" else 1,
                        ),
                    }
                )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "results.json").write_text(json.dumps(results, indent=1))
    desc = descriptive(rows, gaps)
    with (args.output_dir / "descriptive.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(desc[0]))
        writer.writeheader()
        writer.writerows(desc)
    print(f"{len(results)} analyses, {len(desc)} descriptive rows -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
