"""Registered analysis from a complete, independently audited sweep."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import run_sweep as sweep

from vrptw import sweep_statistics as stats

FIELDS = (
    "instance",
    "case_id",
    "seed",
    "cutoff_sec",
    "customers",
    "geometry_sha256",
    "available",
    "nv",
    "td",
    "integrity_ok",
    "return_ok",
    "binding_ok",
)
REPLICATE_FIELDS = (
    "analysis_id",
    "replicate",
    "fleet_score",
    "td_pct",
    "td_raw",
    "nv_interaction",
    "matched_pairs",
    "matched_instances",
    "eligible_seed_units",
)


def expected_keys(plan):
    d = plan["design"]
    names = plan["metadata"]
    cells = set()
    for contrast in plan["contrasts"]:
        cells.update(contrast["weights"])
    keys = {
        (name, case, seed, t)
        for name in names
        for case in d["primary_cases"]
        for seed in d["seeds"]
        for t in d["primary_cutoffs_sec"]
    }
    keys.update(
        (name, case, seed, t)
        for name in d["ablation_instances"]
        for case in cells
        for seed in d["seeds"]
        for t in d["ablation_cutoffs_sec"]
    )
    return keys


def read_records(path):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        sweep.require(
            reader.fieldnames
            and len(set(reader.fieldnames)) == len(reader.fieldnames)
            and set(FIELDS) <= set(reader.fieldnames),
            "record CSV schema differs",
        )
        rows = []
        for original in reader:
            r = {k: original[k] for k in FIELDS}
            for k in ("seed", "cutoff_sec", "customers"):
                r[k] = int(r[k])
            r["nv"] = int(r["nv"]) if r["nv"] else None
            r["td"] = float(r["td"]) if r["td"] else None
            for k in ("available", "integrity_ok", "return_ok", "binding_ok"):
                sweep.require(r[k] in ("True", "False"), "invalid CSV boolean")
                r[k] = r[k] == "True"
            rows.append(r)
    return rows


def write_csv(path, rows, fields=None):
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def flat(value, prefix=""):
    for key, v in value.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(v, dict):
            yield from flat(v, name)
        else:
            yield name, v


def analyses(plan):
    d = plan["design"]
    names = sorted(plan["metadata"])
    items = []
    main_weights = {
        size: sum(r["customers"] == size for r in plan["metadata"].values()) / len(names)
        for size in sorted({r["customers"] for r in plan["metadata"].values()})
    }
    for t in d["primary_cutoffs_sec"]:
        for control in d["primary_cases"]:
            if control == "F111111":
                continue
            items.append(
                {
                    "analysis_id": f"primary:{t}:{control}",
                    "kind": "pair",
                    "treatment": "F111111",
                    "control": control,
                    "cutoff_sec": t,
                    "names": names,
                    "weights": main_weights,
                    "family_size": 3 if t == 300 else 1,
                    "role": "primary_300s" if t == 300 else "descriptive",
                }
            )
    for t in d["ablation_cutoffs_sec"]:
        for contrast in plan["contrasts"]:
            primary = t == 300 and contrast["role"] == "primary_ablation_300s"
            spec = {
                "analysis_id": f"ablation:{t}:{contrast['id']}",
                "cutoff_sec": t,
                "names": d["ablation_instances"],
                "weights": {100: 1 / 3, 200: 1 / 3, 400: 1 / 3},
                "family_size": 8 if primary else 1,
                "role": "primary_ablation_300s" if primary else "exploratory",
            }
            if len(contrast["weights"]) == 4:
                spec.update(kind="interaction", contrast=contrast["weights"], metrics=["nv_interaction"])
            else:
                spec.update(
                    kind="pair",
                    treatment=next(k for k, v in contrast["weights"].items() if v == 1),
                    control=next(k for k, v in contrast["weights"].items() if v == -1),
                )
            items.append(spec)
    for item in items:
        if item["kind"] == "pair":
            item["metrics"] = ["fleet_score", "td_pct", "td_raw"]
    return items


def write_analysis(output, source_csv, plan, provenance, *, replicates=10000):
    output = output.resolve()
    output.mkdir(exist_ok=False)
    fixture = provenance.get("fixture_only") is True
    if not fixture:
        sweep.require(
            replicates == 10000 and len(plan["metadata"]) == 74 and plan["design"]["seeds"] == [42, 43, 44, 45, 46],
            "registered analysis settings differ",
        )
    shutil.copy2(source_csv, output / "records.csv")
    if "expected_records_sha256" in provenance:
        sweep.require(
            sweep.sha256(output / "records.csv") == provenance["expected_records_sha256"], "audited record view drift"
        )
    rows = read_records(output / "records.csv")
    indexed = stats.validate_records(rows, plan["metadata"])
    sweep.require(set(indexed) == expected_keys(plan), "missing or undeclared statistical cells")
    draws = stats.make_draws(plan["metadata"], plan["design"]["seeds"], replicates, 20261019)
    draw_rows = [
        {
            "replicate": i,
            "seed_indices": json.dumps(draws["seed_indices"][i].tolist()),
            "geometry_group_indices": json.dumps(
                {str(k): v[i].tolist() for k, v in draws["group_indices"].items()}, sort_keys=True
            ),
        }
        for i in range(replicates)
    ]
    write_csv(output / "bootstrap_draws.csv", draw_rows)
    sweep.publish(
        output / "draw_metadata.json",
        {
            "seeds": draws["seeds"],
            "groups": draws["groups"],
            "rng_seed": 20261019,
            "scope": "same draws across every algorithm, cutoff and subset",
        },
    )
    index = analyses(plan)
    sweep.publish(output / "analysis_index.json", index)
    points = []
    with (output / "bootstrap.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REPLICATE_FIELDS)
        writer.writeheader()
        for item in index:
            args = (rows, plan["metadata"], item["names"])
            if item["kind"] == "pair":
                result = stats.analyze_pair(
                    *args,
                    item["treatment"],
                    item["control"],
                    item["cutoff_sec"],
                    draws,
                    item["weights"],
                    item["family_size"],
                )
            else:
                result = stats.analyze_interaction(*args, item["contrast"], item["cutoff_sec"], draws, item["weights"])
            for metric, value in flat(result["point"]):
                points.append(
                    {
                        "analysis_id": item["analysis_id"],
                        "cutoff_sec": item["cutoff_sec"],
                        "role": item["role"],
                        "metric": metric,
                        "value": value,
                        "value_type": "int" if type(value) is int else "float",
                    }
                )
            for i in range(replicates):
                row = {"analysis_id": item["analysis_id"], "replicate": i}
                for metric, values in result["replicates"].items():
                    value = values[i]
                    row[metric] = float(value) if math.isfinite(value) else None
                writer.writerow(row)
    write_csv(output / "point_estimates.csv", points)
    write_csv(output / "seed_summary.csv", stats.seed_summary(rows))
    # Derive the reported intervals only after reopening the recorded replicates.
    collected = {item["analysis_id"]: {metric: [] for metric in item["metrics"]} for item in index}
    seen = {item["analysis_id"]: set() for item in index}
    with (output / "bootstrap.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            key = row["analysis_id"]
            i = int(row["replicate"])
            sweep.require(i not in seen[key] and 0 <= i < replicates, "duplicate/out-of-range bootstrap row")
            seen[key].add(i)
            for metric in collected[key]:
                collected[key][metric].append(float(row[metric]) if row[metric] else float("nan"))
    intervals = []
    for item in index:
        key = item["analysis_id"]
        sweep.require(len(seen[key]) == replicates, "incomplete replicate CSV")
        for metric, values in collected[key].items():
            intervals.append(
                {"analysis_id": key, "metric": metric, **stats.percentile_interval(values, item["family_size"])}
            )
    write_csv(output / "intervals.csv", intervals)
    # JSON report values are read back from the public numeric CSV artifacts.
    point_report = []
    with (output / "point_estimates.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            row["value"] = (
                (int(row["value"]) if row["value_type"] == "int" else float(row["value"])) if row["value"] else None
            )
            row["cutoff_sec"] = int(row["cutoff_sec"])
            point_report.append(row)
    interval_report = []
    with (output / "intervals.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            for k in ("lower", "upper"):
                row[k] = float(row[k]) if row[k] else None
            row["level"] = float(row["level"])
            row["family_size"] = int(row["family_size"])
            row["undefined_replicates"] = int(row["undefined_replicates"])
            row["suppressed"] = row["suppressed"] == "True"
            interval_report.append(row)
    csv_names = (
        "records.csv",
        "bootstrap_draws.csv",
        "bootstrap.csv",
        "point_estimates.csv",
        "seed_summary.csv",
        "intervals.csv",
    )
    report = {
        "fixture_only": fixture,
        "analysis_count": len(index),
        "replicates": replicates,
        "provenance": provenance,
        "source_sha256": plan["source_sha256"],
        "sweep_manifest_sha256": plan["manifest_sha256"],
        "csv_hashes": {n: sweep.sha256(output / n) for n in csv_names},
        "point_estimates": point_report,
        "intervals": interval_report,
        "limits": [
            "Approximate geometry/seed intervals; no coverage or power guarantee.",
            "Bonferroni comparison families apply separately per metric, not jointly across endpoints.",
            "TD intervals target the fixed-stratum conditional matched-fleet estimand; raw eligible-instance means are descriptive.",
            "No p-values, unconditional distance effects or global optimality claims.",
            "Synthetic fixture output is not solver evidence." if fixture else "Complete declared sweep cells only.",
        ],
    }
    sweep.publish(output / "report.json", report)
    sweep.publish(
        output / "artifact_hashes.json",
        {str(p.relative_to(output)): sweep.sha256(p) for p in sorted(output.rglob("*")) if p.is_file()},
    )
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    plan, rows = sweep.audit(args.run_dir.resolve(), require_complete=True)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    expected = hashlib.sha256(stream.getvalue().encode()).hexdigest()
    report = write_analysis(
        args.output_dir,
        args.run_dir / "records.csv",
        plan,
        {"fixture_only": False, "expected_records_sha256": expected},
    )
    print(
        json.dumps(
            {"status": "analyzed", "analysis_count": report["analysis_count"], "replicates": report["replicates"]}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
