#!/usr/bin/env python3
"""Offline, explicit solve-tree projection of the sealed five-cell trace defect."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

from vrptw.gnn_training import sha256
from vrptw.phase_trace import audit_trace

FROZEN_SOURCE = "ac4f322f73eac2584012917c2d13e6b6a7c8cf596a8d2ed7ab76a2960f3abab7"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    require(bool(rows), "missing analysis rows")
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def project_solve_trace(source, target):
    """Copy the unchanged solve subtree; accept only the four known CLI reads."""
    digest = sha256(source)
    rows = read_csv(source)
    require(bool(rows), "empty raw trace")
    require([int(row["id"]) for row in rows] == list(range(1, len(rows) + 1)), "raw ID drift")
    roots = [i for i, row in enumerate(rows) if int(row["parent_id"]) == 0]
    require(roots == [0, *range(len(rows) - 4, len(rows))], "unexpected raw root/child structure")
    require(rows[0]["name"] == "solve", "missing solve root")
    solve, tail = rows[:-4], rows[-4:]
    require(
        [r["name"] for r in tail] == ["plan.cost", "plan.feasible", "plan.feasible", "plan.cost"], "unexplained root"
    )
    start, cutoff = float(rows[0]["solve_start_perf"]), float(rows[0]["solve_deadline_perf"])
    previous_end = float(rows[0]["end_perf"])
    for row in tail:
        first, last = float(row["start_perf"]), float(row["end_perf"])
        require(all(math.isfinite(v) for v in (first, last, start, cutoff)), "nonfinite outside timestamp")
        require(previous_end <= first <= last, "outside span overlaps solve/another root")
        require(
            (float(row["solve_start_perf"]), float(row["solve_deadline_perf"])) == (start, cutoff),
            "outside clock drift",
        )
        require(row["outcome"] == "return" and not row.get("detail"), "outside getter outcome/detail drift")
        expected = max(0.0, last - max(first, cutoff))
        for key in ("post_cutoff_inclusive_sec", "post_cutoff_exclusive_sec"):
            require(math.isclose(float(row[key]), expected, abs_tol=1e-9), "outside arithmetic drift")
        previous_end = last
    target.parent.mkdir(parents=True, exist_ok=True)
    write_csv(target, solve)
    audit = audit_trace(target)
    require(sha256(source) == digest, "raw trace changed during projection")
    return {
        "source": str(source.resolve()),
        "source_sha256": digest,
        "projection": str(target.resolve()),
        "projection_sha256": sha256(target),
        "excluded_spans": tail,
        "audit": audit,
    }


def verify_seal(source):
    manifest = json.loads((source / "artifact_hashes.json").read_text())
    for name, digest in manifest.items():
        require(sha256(source / name) == digest, f"sealed evidence drift: {name}")
    return len(manifest)


def main():
    import run_factor_contract_pilot as factor

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source, output = args.input_dir.resolve(), args.output_dir.resolve()
    sealed_count = verify_seal(source)
    plan = json.loads((source / "plan.json").read_text())
    audit = json.loads((source / "audit.json").read_text())
    require(plan["source_sha256"] == FROZEN_SOURCE, "not the specified frozen instrumentation stage")
    require(audit["complete"] and len(plan["jobs"]) == 5, "incomplete frozen schedule")
    rows = read_csv(source / "summary.csv")
    require(len(rows) == len(audit["verified_runs"]) == 5, "incomplete raw result evidence")
    output.mkdir(parents=True, exist_ok=False)
    projections, compiler, post_rows, summaries, attributions = [], [], [], [], []
    for job, row, prior in zip(plan["jobs"], rows, audit["verified_runs"], strict=True):
        require(job["run"] == row["run"] == prior["run"], "raw result order drift")
        raw = json.loads((source / f"{job['run']}.json").read_text())
        current = factor.audit_result(
            factor.load_job_instance(source, plan, job), job, factor.identity_for(source, plan, job), raw
        )
        for gate in factor.GATES:
            require(current[gate] == prior[gate] == (row[gate] == "True"), f"result gate drift: {gate}")
        path = source / f"{job['run']}.phases.csv"
        meta = raw["metadata"]["phase_tracing"]
        require(
            meta["enabled"] and meta["path"] == str(path) and meta["sha256"] == sha256(path), "raw trace identity drift"
        )
        report = project_solve_trace(path, output / f"{job['run']}.solve.csv")
        checked = report["audit"]
        require(
            abs(checked["solve_deadline_perf"] - checked["solve_start_perf"] - job["time_limit"]) < 1e-8, "cutoff drift"
        )
        require(
            checked["root_end_perf"] - checked["solve_start_perf"] <= raw["runtime_sec"], "root/runtime clock drift"
        )
        projections.append({"run": job["run"], **report})
        spans = read_csv(Path(report["projection"]))
        by_id = {int(span["id"]): span for span in spans}
        grouped = defaultdict(float)
        for span in spans:
            post = float(span["post_cutoff_exclusive_sec"])
            is_compile = span["name"].startswith("numba.compile:")
            if post > 0:
                grouped["numba.compile" if is_compile else span["name"]] += post
                post_rows.append({"run": job["run"], "raw_trace_sha256": report["source_sha256"], **span})
            if is_compile:
                start = checked["solve_start_perf"]
                compiler.append(
                    {
                        "run": job["run"],
                        "raw_trace_sha256": report["source_sha256"],
                        "id": span["id"],
                        "parent_id": span["parent_id"],
                        "parent_name": by_id[int(span["parent_id"])]["name"],
                        "name": span["name"],
                        "argument_types": span["detail"],
                        "start_sec": float(span["start_perf"]) - start,
                        "end_sec": float(span["end_perf"]) - start,
                        "duration_sec": float(span["end_perf"]) - float(span["start_perf"]),
                        "post_cutoff_inclusive_sec": span["post_cutoff_inclusive_sec"],
                        "post_cutoff_exclusive_sec": post,
                    }
                )
        total = checked["post_cutoff_sec"]
        require(math.isclose(math.fsum(grouped.values()), total, abs_tol=1e-7), "attribution conservation failure")
        compile_post = grouped.get("numba.compile", 0.0)
        summaries.append(
            {
                **{
                    key: row[key]
                    for key in ("run", "instance", "ablation", "runtime_sec", "captured_sec", *factor.GATES)
                },
                "solve_spans": len(spans),
                "excluded_cli_spans": len(report["excluded_spans"]),
                "root_post_cutoff_sec": total,
                "compiler_post_cutoff_sec": compile_post,
                "other_post_cutoff_sec": total - compile_post,
            }
        )
        attributions.extend(
            {"run": job["run"], "phase": name, "post_cutoff_exclusive_sec": value}
            for name, value in sorted(grouped.items())
        )
    require(verify_seal(source) == sealed_count, "raw evidence changed")
    for name, data in (
        ("diagnostic_summary.csv", summaries),
        ("compiler_spans.csv", compiler),
        ("post_cutoff.csv", post_rows),
        ("attribution.csv", attributions),
    ):
        write_csv(output / name, data)
    result = {
        "status": "passed_solve_projection_only",
        "source_sha256": FROZEN_SOURCE,
        "original_strict_phase_audit": "failed; preserved in phase_audit_failure.json",
        "original_manifest_sha256": sha256(source / "artifact_hashes.json"),
        "sealed_raw_files_verified": sealed_count,
        "projections": projections,
        "limits": "Instrumented selected failures; no benchmark rerun, hard-deadline certification, causal before/after or uninstrumented replacement",
    }
    factor.native.write_json(output / "projection_audit.json", result, "x")
    shutil_source = output / "audit_program.py"
    shutil_source.write_bytes(Path(__file__).read_bytes())
    factor.native.write_json(
        output / "artifact_hashes.json",
        {str(p.relative_to(output)): sha256(p) for p in sorted(output.rglob("*")) if p.is_file()},
        "x",
    )
    print(json.dumps({"status": result["status"], "jobs": len(summaries), "raw_files_verified": sealed_count}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
