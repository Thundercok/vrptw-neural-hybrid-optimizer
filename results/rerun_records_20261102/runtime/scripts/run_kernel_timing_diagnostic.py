#!/usr/bin/env python3
"""Five frozen confirmation failures with finer opt-in Python/compiler tracing."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

import run_factor_contract_pilot as factor
from run_return_timing_diagnostic import audit_phases

from vrptw.gnn_training import sha256

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = ROOT / "results/return_timing_confirmation_20261020"


def select_jobs(previous):
    require = factor.native.require
    plan = json.loads((previous / "plan.json").read_text())
    audit = json.loads((previous / "audit.json").read_text())
    require(audit["complete"] and audit["status"] == "failed", "unexpected prior stage")
    require(
        plan["source_sha256"] == "0f9595e2f4f58ba9f4b0a5b842dd345f90609843756ce32cc935546f72d5b9f0",
        "wrong prior source",
    )
    manifest = json.loads((previous / "artifact_hashes.json").read_text())
    require(all(name in manifest for name in ("plan.json", "audit.json", "summary.csv")), "missing selection seals")
    for hashes in (audit["artifact_hashes"], manifest):
        for name, digest in hashes.items():
            require(sha256(previous / name) == digest, f"prior artifact drift: {name}")
    with (previous / "summary.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    require(len(rows) == len(plan["jobs"]) == len(audit["verified_runs"]) == 9, "incomplete prior stage")
    selected = []
    for job, row, verdict in zip(plan["jobs"], rows, audit["verified_runs"], strict=True):
        require(job["run"] == row["run"] == verdict["run"], "prior order drift")
        require(not job["phase_traced"] and not job["profiled"], "prior instrumentation drift")
        require(
            all(row[key] == "True" and verdict[key] for key in factor.GATES if key != "budget_ok"),
            "prior integrity/certification failure",
        )
        require(row["budget_ok"] in ("True", "False"), "invalid timing gate")
        require((row["budget_ok"] == "True") == verdict["budget_ok"], "prior timing gate drift")
        if row["budget_ok"] == "False":
            selected.append(
                {
                    **job,
                    "run": job["run"].removesuffix("__confirmation") + "__kernel_trace",
                    "source_run": job["run"],
                    "phase_traced": True,
                }
            )
    require(len(selected) == 5, "selection is not the fixed five failures")
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    jobs = select_jobs(PREVIOUS)
    plan = factor.prepare(
        output,
        ROOT / "results/gnn_retraining_20261017/model_seed42/best.pt",
        20261019,
        jobs=jobs,
        protocol_path=ROOT / "docs/kernel_timing_20261020.md",
    )
    filenames = ("plan.json", "summary.csv", "audit.json", "artifact_hashes.json")
    for name in filenames:
        shutil.copy2(PREVIOUS / name, output / f"selection_{name}")
    previous = json.loads((PREVIOUS / "plan.json").read_text())
    for job in jobs:
        factor.native.require(
            plan["configs"][job["run"]] == previous["configs"][job["source_run"]], "selected config drift"
        )
    factor.native.write_json(
        output / "selection.json",
        {
            "jobs": jobs,
            "instrumented": True,
            "files": {f"selection_{name}": sha256(output / f"selection_{name}") for name in filenames},
        },
        "x",
    )
    state = factor.execute(output, plan)
    audit = factor.audit_directory(output, expected_jobs=jobs)
    if state["status"] == "completed":
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
                "audit_status": audit["status"],
                "instrumented": True,
            }
        ),
        flush=True,
    )
    return 0 if state["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
