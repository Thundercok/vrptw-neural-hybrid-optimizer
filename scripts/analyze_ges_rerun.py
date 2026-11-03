"""Analysis of the GES rerun, fixed by results/ges_sweep_20261102/README.md before results were read.

Inputs: records.csv from the rerun's validate.py and the runner's sweep.log. A stage enters the
analysis only after it has closed, so running this early never exposes a stage in progress.
Estimands and intervals are those of analyze_revision.analyze_pair (vrptw.sweep_statistics).

Adoption rule: GES is adopted only if, at 300 s on all 74 instances, the fleet score of F111111 (with
GES) against F111111-blind has a 98.75% interval with a lower bound above zero. The primary family of
three comparisons then follows that outcome. Amendment 1 dropped comparisons with closed-sweep cells
because machine speed differed, so none is made here.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_revision as revision  # noqa: E402
from vrptw import sweep_statistics as stats  # noqa: E402

RUN = ROOT / "results/ges_sweep_20261102"
DESIGN = ROOT / "results/ablation_design_20261019"
GEOMETRY_RECORDS = ROOT / "results/cutoff_clock_audit_20261029/run/records.csv"
BKS = ROOT / "data/reference/sintef_official_bks.json"

GES = "F111111"
BLIND = "F111111-blind"
ALNS_GES = "ALNS-Base"
ALNS_NOGES = "ALNS-Base-noges"
PYVRP = "PyVRP-ILS"
NEUROLKH = "NeuroLKH-adapted"
ADOPTION_FAMILY = 4  # percentile_interval's level is 1 - 0.05 / family, so 4 gives the rule's 98.75%
PRIMARY_FAMILY = 3
ABLATION_FAMILY = 8
SLEEP_GAP_SEC = 5.0
LOAD_LIMIT = 8.0
MIN_LOAD_SAMPLES = 3  # Amendment 5: a cell needs this many load samples during its run to count as measured
RETURN_UPPER_SLACK = 0.5
STAGES = ("primary_t300", "primary_t60", "primary_t10", "ablation_t60", "ablation_t300", "primary_t900")
# Validator messages that mean the cell cannot be trusted at all, as opposed to finding no solution.
INTEGRITY_ERRORS = ("blind/GES flags", "unexpected ges_phase_frac", "reported nv/td differ", "certificate hash mismatch")
PRIMARY_ARMS = (GES, ALNS_GES, PYVRP, NEUROLKH)
T300_ARMS = (*PRIMARY_ARMS, BLIND, ALNS_NOGES)


def closed_stages(log_path: Path, finished: bool) -> set[str]:
    """A stage is closed once a later one has started; the last closes with finished.json."""
    started = set()
    for line in log_path.read_text().splitlines():
        if line.startswith("{"):
            entry = json.loads(line)
            if "stage_start" in entry:
                started.add(entry["stage_start"])
    latest = max((STAGES.index(s) for s in started), default=-1)
    closed = set(STAGES[:latest])
    if finished and latest == len(STAGES) - 1:
        closed.add(STAGES[-1])
    return closed


def load_cells(records_path: Path, metadata: dict) -> list[dict]:
    """Parse validator rows; calibration anchors are not sweep cells. Fails on untrustworthy or frozen cells."""
    cells = []
    with records_path.open(newline="") as f:
        for r in csv.DictReader(f):
            if r["stage"] not in STAGES:
                continue
            errors = json.loads(r["errors"])
            bad = [e for e in errors if e.startswith(INTEGRITY_ERRORS)]
            stats.require(not bad, f"{r['run']}: integrity error {bad}")
            gap = float(r["clock_gap_sec"])
            stats.require(gap <= SLEEP_GAP_SEC, f"{r['run']}: frozen by sleep ({gap:.0f} s) but not requeued")
            ok = r["available"] == "True"
            cutoff = int(r["cutoff_sec"])
            runtime = float(r["runtime_sec"]) if r["runtime_sec"] else None
            cells.append(
                {
                    "run": r["run"],
                    "stage": r["stage"],
                    "instance": r["instance"],
                    "case_id": r["case_id"],
                    "seed": int(r["seed"]),
                    "cutoff_sec": cutoff,
                    **metadata[r["instance"]],
                    "available": ok,
                    "nv": int(r["nv"]) if ok else None,
                    "td": float(r["td"]) if ok else None,
                    "integrity_ok": True,
                    "return_ok": runtime is not None and runtime <= cutoff + RETURN_UPPER_SLACK,
                    "binding_ok": ok,
                    "load1": float(r["load1"]) if r["load1"] else None,
                    "power": r["power"],
                    "phases": r["phases"],
                    "errors": errors,
                }
            )
    return cells


def stage_rows(cells, stage, names, cases, seeds, metadata):
    """One stage's rows, with a missing cell added as an unavailable row and listed as an infrastructure gap."""
    rows = [c for c in cells if c["stage"] == stage and c["case_id"] in cases]
    cutoff = int(stage.rsplit("t", 1)[1])
    present = {(r["instance"], r["case_id"], r["seed"]) for r in rows}
    gaps = set()
    for name in names:
        for case in cases:
            for seed in seeds:
                if (name, case, seed) not in present:
                    gaps.add((name, case, seed, cutoff))
                    rows.append(
                        {
                            "stage": stage,
                            "instance": name,
                            "case_id": case,
                            "seed": seed,
                            "cutoff_sec": cutoff,
                            **metadata[name],
                            "available": False,
                            "nv": None,
                            "td": None,
                            "integrity_ok": True,
                            "return_ok": False,
                            "binding_ok": False,
                            "load1": None,
                            "power": "",
                            "phases": "",
                            "errors": ["missing cell"],
                        }
                    )
    return rows, gaps


def block_gaps(rows, blocks):
    return {
        (r["instance"], r["case_id"], r["seed"], r["cutoff_sec"]) for r in rows if (r["instance"], r["seed"]) in blocks
    }


def high_load_blocks(rows):
    """Cells of every (instance, seed) block with a cell started at load1 above the limit, as gap keys."""
    blocks = {(r["instance"], r["seed"]) for r in rows if r["load1"] is not None and r["load1"] > LOAD_LIMIT}
    return blocks, block_gaps(rows, blocks)


def attach_run_load(cells, run_root: Path, samples_path: Path):
    """Set run_load1 to the mean load1 sampled during a cell's run, or None with too few samples (Amendment 5)."""
    samples = []
    if samples_path.exists():
        for line in samples_path.read_text().splitlines():
            entry = json.loads(line)
            samples.append((entry["utc"], entry["load"][0]))
    times = np.array([s[0] for s in samples], dtype=float)
    loads = np.array([s[1] for s in samples], dtype=float)
    for c in cells:
        cell = run_root / c["run"]
        start = json.loads((cell / "started.json").read_text())["utc"]
        end = json.loads((cell / "completed.json").read_text())["utc"]
        during = loads[(times >= start) & (times <= end)]
        c["run_load1"] = float(during.mean()) if len(during) >= MIN_LOAD_SAMPLES else None


def run_load_blocks(rows):
    """Blocks with an exposed cell and blocks with an unmeasured cell. A missing cell has no run_load1 key."""
    exposed = {(r["instance"], r["seed"]) for r in rows if (r.get("run_load1") or 0.0) > LOAD_LIMIT}
    unmeasured = {(r["instance"], r["seed"]) for r in rows if "run_load1" in r and r["run_load1"] is None}
    return exposed, unmeasured


def adopted(result: dict) -> bool:
    lower = result["intervals"]["fleet_score"]["lower"]
    return lower is not None and lower > 0


def compare(rows, metadata, names, treatment, control, cutoff, draws, weights, gaps, mode, family, **labels):
    return {
        "cutoff_sec": cutoff,
        "treatment": treatment,
        "control": control,
        "gap_mode": mode,
        **labels,
        **revision.analyze_pair(
            rows, metadata, names, treatment, control, cutoff, draws, weights, gaps, mode, family
        ),
    }


def size_scopes(names, metadata, weights):
    return [("all", names, weights)] + [
        (f"size_{size}", [n for n in names if metadata[n]["customers"] == size], {size: 1.0})
        for size in sorted({metadata[n]["customers"] for n in names})
    ]


def analyze_primary(cells, metadata, names, seeds, draws, weights, closed):
    results, decision = [], None
    if "primary_t300" not in closed:
        return results, decision
    rows, gaps = stage_rows(cells, "primary_t300", names, T300_ARMS, seeds, metadata)
    rule = compare(
        rows, metadata, names, GES, BLIND, 300, draws, weights, gaps, "drop_pair", ADOPTION_FAMILY,
        analysis="adoption_rule", scope="all",
    )
    results.append(rule)
    is_adopted = adopted(rule)
    proposed, base = (GES, ALNS_GES) if is_adopted else (BLIND, ALNS_NOGES)
    other, other_base = (BLIND, ALNS_NOGES) if is_adopted else (GES, ALNS_GES)
    decision = {
        "ges_adopted": is_adopted,
        "proposed": proposed,
        "alns_comparator": base,
        "fleet_score": rule["fleet_score"],
        "interval": rule["intervals"]["fleet_score"],
    }
    blocks, load_gaps = high_load_blocks(rows)
    decision["high_load_blocks"] = len(blocks)
    decision["t300_gaps"] = len(gaps)
    exposed, unmeasured = run_load_blocks(rows)
    decision["run_load_exposed_blocks"] = len(exposed)
    decision["run_load_unmeasured_blocks"] = len(unmeasured)
    run_load_analyses = (
        ("run_load_a", gaps | block_gaps(rows, exposed)),
        ("run_load_b", gaps | block_gaps(rows, exposed | unmeasured)),
    )
    for label, dropped in run_load_analyses:
        results.append(
            compare(
                rows, metadata, names, GES, BLIND, 300, draws, weights, dropped, "drop_pair", ADOPTION_FAMILY,
                analysis=f"adoption_{label}", scope="all",
            )
        )
    for control in (base, PYVRP, NEUROLKH):
        for mode in revision.GAP_MODES:
            results.append(
                compare(
                    rows, metadata, names, proposed, control, 300, draws, weights, gaps, mode, PRIMARY_FAMILY,
                    analysis="primary", scope="all",
                )
            )
        results.append(
            compare(
                rows, metadata, names, proposed, control, 300, draws, weights, gaps | load_gaps, "drop_pair",
                PRIMARY_FAMILY, analysis="primary_load_sensitivity", scope="all",
            )
        )
        for label, dropped in run_load_analyses:
            results.append(
                compare(
                    rows, metadata, names, proposed, control, 300, draws, weights, dropped, "drop_pair",
                    PRIMARY_FAMILY, analysis=f"primary_{label}", scope="all",
                )
            )
        for scope, subset, scoped in size_scopes(names, metadata, weights)[1:]:
            results.append(
                compare(
                    rows, metadata, subset, proposed, control, 300, draws, scoped, gaps, "drop_pair", 1,
                    analysis="primary_by_size", scope=scope,
                )
            )
    for control in (other_base, PYVRP, NEUROLKH):
        results.append(
            compare(
                rows, metadata, names, other, control, 300, draws, weights, gaps, "drop_pair", 1,
                analysis="other_configuration", scope="all",
            )
        )
    results.append(
        compare(
            rows, metadata, names, ALNS_GES, ALNS_NOGES, 300, draws, weights, gaps, "drop_pair", 1,
            analysis="ges_effect_on_alns", scope="all",
        )
    )
    # Other budgets run the GES arms only, so they describe the proposed method only if GES was adopted.
    for stage in ("primary_t60", "primary_t10", "primary_t900"):
        if stage not in closed:
            continue
        cutoff = int(stage.rsplit("t", 1)[1])
        rows, gaps = stage_rows(cells, stage, names, PRIMARY_ARMS, seeds, metadata)
        for control in (ALNS_GES, PYVRP, NEUROLKH):
            for scope, subset, scoped in size_scopes(names, metadata, weights):
                results.append(
                    compare(
                        rows, metadata, subset, GES, control, cutoff, draws, scoped, gaps, "drop_pair", 1,
                        analysis="budget", scope=scope, proposed_configuration=is_adopted,
                    )
                )
    return results, decision


def analyze_ablation(cells, metadata, design, contrasts, seeds, draws, closed):
    names = sorted(design["ablation_instances"])
    weights = {100: 1 / 3, 200: 1 / 3, 400: 1 / 3}
    results = []
    cases = sorted({case for c in contrasts for case in c["weights"]})
    for stage in ("ablation_t60", "ablation_t300"):
        if stage not in closed:
            continue
        cutoff = int(stage.rsplit("t", 1)[1])
        rows, gaps = stage_rows(cells, stage, names, cases, seeds, metadata)
        for contrast in contrasts:
            if len(contrast["weights"]) == 2:
                treatment = next(k for k, v in contrast["weights"].items() if v == 1)
                control = next(k for k, v in contrast["weights"].items() if v == -1)
                primary = cutoff == 300 and contrast["role"] == "primary_ablation_300s"
                results.append(
                    compare(
                        rows, metadata, names, treatment, control, cutoff, draws, weights, gaps, "drop_pair",
                        ABLATION_FAMILY if primary else 1,
                        analysis=f"ablation:{contrast['id']}", scope="ablation_18",
                        role="primary_ablation_300s" if primary else "exploratory",
                    )
                )
            else:
                interaction = stats.analyze_interaction(
                    [{k: r[k] for k in stats_fields(r)} for r in rows], metadata, names, contrast["weights"],
                    cutoff, draws, weights,
                )
                results.append(
                    {
                        "analysis": f"ablation:{contrast['id']}",
                        "cutoff_sec": cutoff,
                        "scope": "ablation_18",
                        "role": "exploratory",
                        "point": interaction["point"],
                        "intervals": interaction["intervals"],
                    }
                )
    return results


def stats_fields(row):
    return (
        "instance", "case_id", "seed", "cutoff_sec", "customers", "geometry_sha256", "available", "nv", "td",
        "integrity_ok", "return_ok", "binding_ok",
    )


def family_of(name: str) -> str:
    """Solomon names carry the family in the first digits (R101 -> R1), Homberger names before the size."""
    head = name.split("_")[0]
    letters = "".join(ch for ch in head if ch.isalpha())
    digits = "".join(ch for ch in head if ch.isdigit())
    return letters + digits[0]


def describe(cells, closed):
    """Per-instance and per-family rows for the stages that have closed."""
    groups = defaultdict(list)
    for c in cells:
        if c["stage"].startswith("primary") and c["stage"] in closed:
            groups[c["instance"], c["case_id"], c["cutoff_sec"]].append(c)
    per_instance = []
    for (instance, case, cutoff), rs in sorted(groups.items()):
        ok = [r for r in rs if r["available"]]
        per_instance.append(
            {
                "instance": instance,
                "family": family_of(instance),
                "customers": rs[0]["customers"],
                "case_id": case,
                "cutoff_sec": cutoff,
                "runs": len(rs),
                "available": len(ok),
                "mean_nv": float(np.mean([r["nv"] for r in ok])) if ok else None,
                "mean_td": float(np.mean([r["td"] for r in ok])) if ok else None,
                "late_returns": sum(not r["return_ok"] for r in rs),
            }
        )
    return per_instance


def family_table(cells, proposed, comparators, cutoff, stage, closed):
    """Descriptive per-family seed-pair counts; a pair lacking either solution is counted separately."""
    if stage not in closed:
        return []
    index = {(c["instance"], c["case_id"], c["seed"]): c for c in cells if c["stage"] == stage}
    out = []
    for control in comparators:
        tally = defaultdict(Counter)
        gaps = defaultdict(list)
        for (name, case, seed), t in index.items():
            if case != proposed:
                continue
            c = index.get((name, control, seed))
            if c is None:
                continue
            family = family_of(name)
            if not (t["available"] and c["available"]):
                tally[family]["no_solution_pairs"] += 1
            elif t["nv"] < c["nv"]:
                tally[family]["fewer"] += 1
            elif t["nv"] > c["nv"]:
                tally[family]["more"] += 1
            else:
                tally[family]["same"] += 1
                gaps[family].append(100 * (t["td"] - c["td"]) / c["td"])
        for family in sorted(tally):
            out.append(
                {
                    "cutoff_sec": cutoff,
                    "family": family,
                    "proposed": proposed,
                    "control": control,
                    "fewer": tally[family]["fewer"],
                    "same": tally[family]["same"],
                    "more": tally[family]["more"],
                    "no_solution_pairs": tally[family]["no_solution_pairs"],
                    "matched_td_gap_pct": float(np.mean(gaps[family])) if gaps[family] else None,
                }
            )
    return out


def run_conditions(cells, closed):
    """How cells ran: power at start, load, return latency, failures and how often GES improved a plan."""
    rows = [c for c in cells if c["stage"] in closed]
    errors = Counter(e.split(":")[0] for c in rows for e in c["errors"])
    loads = [c["load1"] for c in rows if c["load1"] is not None]
    ges_cases = (GES, ALNS_GES)
    ges_rows = [c for c in rows if c["case_id"] in ges_cases]
    return {
        "cells": len(rows),
        "power_at_start": dict(Counter(c["power"] for c in rows)),
        "started_above_load_limit": sum(v > LOAD_LIMIT for v in loads),
        "median_load1": float(np.median(loads)) if loads else None,
        "late_returns": sum(not c["return_ok"] for c in rows),
        "no_valid_solution": sum(not c["available"] for c in rows),
        "error_kinds": dict(errors),
        "ges_cells_with_ges_capture": sum("ges" in c["phases"].split("|") for c in ges_rows),
        "ges_cells": len(ges_rows),
    }


def fmt(value, digits, signed=True):
    if value is None:
        return "---"
    return f"${value:+.{digits}f}$" if signed else f"${value:.{digits}f}$"


def fmt_interval(result, key, digits):
    point = result[key]
    iv = result["intervals"][key]
    if point is None:
        return "---"
    if iv["suppressed"] or iv["lower"] is None:
        return f"${point:+.{digits}f}$ (undefined)"
    return f"${point:+.{digits}f}$ [${iv['lower']:.{digits}f}$, ${iv['upper']:.{digits}f}$]"


def comparison_rows(results, analysis, mode="drop_pair"):
    return [r for r in results if r["analysis"] == analysis and r["gap_mode"] == mode]


def latex_primary(results):
    lines = []
    for r in comparison_rows(results, "primary"):
        wtl = f"{r['seed_wins']}/{r['seed_ties']}/{r['seed_losses']}"
        lines.append(f"{r['control']} & {fmt_interval(r, 'fleet_score', 3)} & {wtl} & {fmt_interval(r, 'td_pct', 2)} \\\\")
    return "\n".join(lines) + "\n"


def latex_contrasts(results):
    lines = []
    for r in results:
        if not r["analysis"].startswith("ablation:") or "fleet_score" not in r:
            continue
        label = r["analysis"].split(":", 1)[1].replace("_", " ")
        lines.append(
            f"{label} & {r['cutoff_sec']} & {fmt_interval(r, 'fleet_score', 3)} & {fmt_interval(r, 'td_pct', 2)} & "
            f"{'primary' if r['role'] == 'primary_ablation_300s' else 'descriptive'} \\\\"
        )
    return "\n".join(lines) + "\n"


def latex_per_instance(per_instance, cases, cutoff):
    """One row per instance with mean fleet and distance per case, for a longtable in the supplement."""
    index = {(r["instance"], r["case_id"]): r for r in per_instance if r["cutoff_sec"] == cutoff}
    names = sorted({r["instance"] for r in per_instance if r["cutoff_sec"] == cutoff})
    lines = []
    for name in names:
        cols = [name.replace("_", r"\_")]
        for case in cases:
            r = index.get((name, case))
            if r is None or r["mean_nv"] is None:
                cols += ["---", "---"]
            else:
                cols += [f"{r['mean_nv']:.2f}", f"{r['mean_td']:.1f}"]
        lines.append(" & ".join(cols) + " \\\\")
    return "\n".join(lines) + "\n"


def report(decision, results, conditions, closed):
    lines = ["# GES rerun analysis", "", f"Closed stages: {', '.join(s for s in STAGES if s in closed) or 'none'}", ""]
    if decision is None:
        lines.append("primary_t300 has not closed, so no result is reported.")
        return "\n".join(lines) + "\n"
    iv = decision["interval"]
    stats.require(iv["lower"] is not None, "adoption interval undefined")
    lines += [
        "## Adoption rule",
        "",
        f"F111111 with GES vs F111111-blind: fleet score {decision['fleet_score']:+.3f}, "
        f"98.75% interval [{iv['lower']:.3f}, {iv['upper']:.3f}].",
        f"GES adopted: {decision['ges_adopted']}. Proposed configuration: {decision['proposed']}.",
        f"T300 infrastructure gaps: {decision['t300_gaps']}. Blocks with a cell started at load above "
        f"{LOAD_LIMIT:g}: {decision['high_load_blocks']}.",
        f"Blocks with a cell run at mean load above {LOAD_LIMIT:g}: {decision['run_load_exposed_blocks']}. "
        f"Blocks with a cell not measured during its run: {decision['run_load_unmeasured_blocks']}.",
        "",
    ]
    for title, analysis, mode in (
        ("Primary family, 98.33% intervals", "primary", "drop_pair"),
        ("Primary family, treatment gaps as failures", "primary", "worst_case"),
        ("Primary family without high-load blocks", "primary_load_sensitivity", "drop_pair"),
        ("Adoption contrast without blocks run at high load", "adoption_run_load_a", "drop_pair"),
        ("Adoption contrast on measured blocks only", "adoption_run_load_b", "drop_pair"),
        ("Primary family without blocks run at high load", "primary_run_load_a", "drop_pair"),
        ("Primary family on measured blocks only", "primary_run_load_b", "drop_pair"),
        ("By size, unadjusted", "primary_by_size", "drop_pair"),
        ("Other configuration, unadjusted", "other_configuration", "drop_pair"),
        ("Budgets, unadjusted", "budget", "drop_pair"),
    ):
        chosen = comparison_rows(results, analysis, mode)
        if not chosen:
            continue
        lines += [f"## {title}", ""]
        for r in chosen:
            iv = r["intervals"]["fleet_score"]
            td = r["td_pct"]
            bounds = "undefined" if iv["lower"] is None else f"[{iv['lower']:.3f}, {iv['upper']:.3f}]"
            lines.append(
                f"- {r['cutoff_sec']} s {r['scope']} {r['treatment']} vs {r['control']}: "
                f"fleet {'undefined' if r['fleet_score'] is None else format(r['fleet_score'], '+.3f')} {bounds}, "
                f"W/T/L {r['seed_wins']}/{r['seed_ties']}/{r['seed_losses']}, matched TD "
                + (f"{td:+.2f}%" if td is not None else "none")
                + (" (interval undefined)" if r["intervals"]["td_pct"]["suppressed"] else "")
            )
        lines.append("")
    lines += ["## Run conditions", "", "```json", json.dumps(conditions, indent=1), "```", ""]
    return "\n".join(lines)


def write_csv(path, rows):
    if rows:
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=RUN)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--replicates", type=int, default=10000)
    args = parser.parse_args(argv)
    output = args.output_dir or args.run_dir / "analysis"

    with GEOMETRY_RECORDS.open(newline="") as f:
        metadata = {
            r["instance"]: {"customers": int(r["customers"]), "geometry_sha256": r["geometry_sha256"]}
            for r in csv.DictReader(f)
        }
    names = sorted(metadata)
    stats.require(len(names) == 74, "instance universe differs")
    design = json.loads((DESIGN / "design.json").read_text())
    contrasts = json.loads((DESIGN / "contrasts.json").read_text())
    seeds = design["seeds"]
    weights = {s: sum(m["customers"] == s for m in metadata.values()) / len(names) for s in (100, 200, 400)}

    closed = closed_stages(args.run_dir / "sweep.log", (args.run_dir / "run/finished.json").exists())
    cells = load_cells(args.run_dir / "run/records.csv", metadata)
    attach_run_load(cells, args.run_dir / "run", args.run_dir / "load_samples.jsonl")
    draws = stats.make_draws(metadata, seeds, args.replicates, 20261019)

    results, decision = analyze_primary(cells, metadata, names, seeds, draws, weights, closed)
    results += analyze_ablation(cells, metadata, design, contrasts, seeds, draws, closed)
    per_instance = describe(cells, closed)
    conditions = run_conditions(cells, closed)

    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps({"decision": decision, "results": results}, indent=1))
    (output / "report.md").write_text(report(decision, results, conditions, closed))
    write_csv(output / "per_instance.csv", per_instance)
    if decision is not None:
        comparators = (decision["alns_comparator"], PYVRP, NEUROLKH)
        write_csv(
            output / "family.csv", family_table(cells, decision["proposed"], comparators, 300, "primary_t300", closed)
        )
        tables = output / "tables"
        tables.mkdir(exist_ok=True)
        (tables / "primary_rows.tex").write_text(latex_primary(results))
        (tables / "ablation_rows.tex").write_text(latex_contrasts(results))
        (tables / "per_instance_t300_rows.tex").write_text(
            latex_per_instance(per_instance, (decision["proposed"], decision["alns_comparator"], PYVRP, NEUROLKH), 300)
        )
    print(f"closed {sorted(closed)}; {len(results)} comparisons -> {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
