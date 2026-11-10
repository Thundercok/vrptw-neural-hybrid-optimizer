#!/usr/bin/env python3
"""Frozen nine-cell trace or uninstrumented confirmation; no parameter selection."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

import run_factor_contract_pilot as factor

from vrptw.gnn_training import sha256
from vrptw.phase_trace import audit_trace

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = ROOT / "results/factor_contract_pilot_20261020_v2"


def select_jobs(previous, *, traced):
    plan = json.loads((previous / "plan.json").read_text())
    audit = json.loads((previous / "audit.json").read_text())
    factor.native.require(audit["complete"] and audit["status"] == "failed", "unexpected prior stage")
    factor.native.require(
        plan["source_sha256"] == "86bf7c352c4b506057cf9501629735d2a49c2acb1670a3bcee0736f8e1bb30b1",
        "wrong prior source",
    )
    for name, digest in audit["artifact_hashes"].items():
        factor.native.require(sha256(previous / name) == digest, f"prior artifact drift: {name}")
    with (previous / "summary.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    factor.native.require(len(rows) == len(plan["jobs"]) == 24, "incomplete prior CSV")
    selected = []
    for job, row, verdict in zip(plan["jobs"], rows, audit["verified_runs"], strict=True):
        factor.native.require(job["run"] == row["run"] == verdict["run"], "prior order drift")
        factor.native.require(
            all(row[k] == "True" and verdict[k] for k in factor.GATES if k != "budget_ok"),
            "prior integrity/certification failure",
        )
        factor.native.require((row["budget_ok"] == "True") == verdict["budget_ok"], "prior timing gate drift")
        if row["budget_ok"] == "False":
            selected.append(
                {
                    **job,
                    "run": job["run"] + ("__trace" if traced else "__confirmation"),
                    "source_run": job["run"],
                    "phase_traced": traced,
                }
            )
    factor.native.require(len(selected) == 9, "selection is not the fixed nine failures")
    return selected


def audit_phases(output, jobs):
    reports, rows = [], []
    for job in jobs:
        raw = json.loads((output / f"{job['run']}.json").read_text())
        path = output / f"{job['run']}.phases.csv"
        meta = raw["metadata"]["phase_tracing"]
        factor.native.require(
            meta["enabled"] and meta["path"] == str(path) and meta["sha256"] == sha256(path),
            "phase file identity drift",
        )
        report = audit_trace(path)
        factor.native.require(
            abs(report["solve_deadline_perf"] - report["solve_start_perf"] - job["time_limit"]) < 1e-8,
            "phase cutoff mismatch",
        )
        factor.native.require(
            report["root_end_perf"] - report["solve_start_perf"] <= raw["runtime_sec"], "phase/result clocks mismatch"
        )
        reports.append({"run": job["run"], **report})
        for span in report["post_cutoff_spans"]:
            rows.append(
                {"run": job["run"], "trace_path": str(path.relative_to(output)), "trace_sha256": sha256(path), **span}
            )
    with (output / "post_cutoff.csv").open("x", newline="") as stream:
        if rows:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    result = {
        "status": "passed",
        "runs": reports,
        "limits": "Instrumented Python phase coverage; no causal inner-kernel attribution or uninstrumented timing certification",
    }
    factor.native.write_json(output / "phase_audit.json", result, "x")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--confirmation", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    jobs = select_jobs(PREVIOUS, traced=not args.confirmation)
    # Training provenance stays with the original immutable completed training.
    plan = factor.prepare(
        output,
        ROOT / "results/gnn_retraining_20261017/model_seed42/best.pt",
        20261019,
        jobs=jobs,
        protocol_path=ROOT / "docs/return_timing_20261020.md",
    )
    for filename in ("plan.json", "summary.csv", "audit.json"):
        shutil.copy2(PREVIOUS / filename, output / f"selection_{filename}")
    previous = json.loads((PREVIOUS / "plan.json").read_text())
    for job in jobs:
        factor.native.require(
            plan["configs"][job["run"]] == previous["configs"][job["source_run"]], "selected config drift"
        )
    factor.native.write_json(
        output / "selection.json",
        {
            "jobs": jobs,
            "files": {
                f"selection_{n}": sha256(output / f"selection_{n}") for n in ("plan.json", "summary.csv", "audit.json")
            },
            "instrumented": not args.confirmation,
        },
        "x",
    )
    state = factor.execute(output, plan)
    audit = factor.audit_directory(output, expected_jobs=jobs)
    if not args.confirmation and state["status"] == "completed":
        audit_phases(output, jobs)
    factor.native.write_json(
        output / "artifact_hashes.json",
        {
            str(p.relative_to(output)): sha256(p)
            for p in sorted(output.rglob("*"))
            if p.is_file() and p.name != "artifact_hashes.json"
        },
        "x",
    )
    print(
        json.dumps(
            {
                "status": state["status"],
                "jobs": state["completed_jobs"],
                "return_gate_status": audit["status"],
                "instrumented": not args.confirmation,
            }
        ),
        flush=True,
    )
    return 0 if state["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
