#!/usr/bin/env python3
"""Bounded RC2_4_1 timing/seed diagnostic; never chooses parameters or ranks solvers."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import os
import random
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

try:
    import resource
except ImportError:
    resource = None

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vrptw.gnn_training import sha256, snapshot, source_hash

INSTANCE = "data/Gehring_Homberger/homberger_400_customer_instances/RC2_4_1.TXT"
BRANCHES = ("alns", "full_no_gnn", "full")


def build_schedule(order_seed: int) -> list[dict]:
    rng = random.Random(order_seed)
    blocks = list(itertools.product((42, 43), (10, 60)))
    rng.shuffle(blocks)
    branches = rng.sample(list(BRANCHES), len(BRANCHES))
    jobs = []
    for block, (seed, budget) in enumerate(blocks):
        shift = block % len(branches)
        for position, branch in enumerate(branches[shift:] + branches[:shift]):
            jobs.append(
                {
                    "run": f"plain__{branch}__seed{seed}__{budget}s",
                    "seed": seed,
                    "time_limit": budget,
                    "ablation": branch,
                    "profiled": False,
                    "block": block,
                    "position": position,
                }
            )
    for position, branch in enumerate(rng.sample(list(BRANCHES), len(BRANCHES))):
        jobs.append(
            {
                "run": f"profile__{branch}__seed42__10s",
                "seed": 42,
                "time_limit": 10,
                "ablation": branch,
                "profiled": True,
                "block": len(blocks),
                "position": position,
            }
        )
    return jobs


def child_cpu():
    if resource is None:
        return None
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def host_load():
    return os.getloadavg() if hasattr(os, "getloadavg") else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--gnn-model", type=Path, required=True)
    parser.add_argument("--order-seed", type=int, default=20261019)
    args = parser.parse_args()
    if not args.gnn_model.is_file():
        parser.error(f"missing checkpoint: {args.gnn_model}")
    instance = ROOT / INSTANCE
    if not instance.is_file():
        parser.error(f"missing diagnostic input: {instance}")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    model = output / "gnn_checkpoint.pt"
    shutil.copy2(args.gnn_model, model)
    snapshot(output / "source_snapshot.zip")
    with zipfile.ZipFile(output / "source_snapshot.zip", "a", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.glob("tests/**/*.py")):
            archive.write(path, path.relative_to(ROOT))
    jobs = build_schedule(args.order_seed)
    plan = {
        "scope": "Operational diagnostic only; two seeds and one geometry are not independent instance-level performance evidence",
        "instance": str(instance.resolve()),
        "input_sha256": sha256(instance),
        "source_sha256": source_hash(),
        "checkpoint_sha256": sha256(model),
        "order_seed": args.order_seed,
        "jobs": jobs,
        "selection_policy": "Execute every declared job once, regardless of scores; no retuning, post-hoc exclusion, adaptive reruns or profile/unprofiled pooling",
        "ordering": "Random block order; cyclic balanced branch positions within unprofiled blocks; instrumented jobs last",
        "search_budget_sec": sum(job["time_limit"] for job in jobs),
        "thread_policy": "Torch/Numba/BLAS environment one thread; HiGHS/backend thread counts are not proven by this setting",
        "cpu_policy": "CPU seconds cover complete child including setup and reaped descendants, not solve alone; CPU/wall is not a cause diagnosis",
        "load_policy": "1/5/15-minute load averages are context, not CPU percentages or post-hoc exclusion rules",
    }
    with (output / "plan.json").open("x") as stream:
        json.dump(plan, stream, indent=2)
    env = os.environ.copy()
    env.update(
        {key: "1" for key in ("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}
    )
    rows = []
    status = {"status": "running", "completed_jobs": 0, "all_gates_passed": False}
    (output / "status.json").write_text(json.dumps(status, indent=2))
    try:
        for job in jobs:
            if (
                source_hash() != plan["source_sha256"]
                or sha256(model) != plan["checkpoint_sha256"]
                or sha256(instance) != plan["input_sha256"]
            ):
                raise RuntimeError("Frozen source/model/input changed; aborting, not mixing experiment identities")
            run_id = job["run"]
            raw = output / f"{run_id}.json"
            command = [
                sys.executable,
                str(ROOT / "scripts/benchmark.py"),
                "--instance",
                str(instance.resolve()),
                "--seed",
                str(job["seed"]),
                "--time-limit",
                str(job["time_limit"]),
                "--budget-mode",
                "wall-clock",
                "--ablation",
                job["ablation"],
                "--output-json",
                str(raw),
            ]
            if job["ablation"] == "full":
                command.extend(["--gnn-model", str(model)])
            if job["profiled"]:
                command.extend(["--profile", str(output / f"{run_id}.pstats")])
            (output / f"{run_id}.command.json").write_text(json.dumps(command, indent=2))
            load_before, cpu_before = host_load(), child_cpu()
            start = time.perf_counter()
            timed_out = False
            with (
                (output / f"{run_id}.stdout.log").open("w") as stdout,
                (output / f"{run_id}.stderr.log").open("w") as stderr,
            ):
                try:
                    completed = subprocess.run(
                        command,
                        cwd=ROOT,
                        env=env,
                        stdout=stdout,
                        stderr=stderr,
                        timeout=job["time_limit"] + 120,
                        check=False,
                    )
                    returncode = completed.returncode
                except subprocess.TimeoutExpired:
                    timed_out, returncode = True, -1
            wall = time.perf_counter() - start
            cpu_after, load_after = child_cpu(), host_load()
            cpu = cpu_after - cpu_before if cpu_before is not None and cpu_after is not None else None
            result = json.loads(raw.read_text()) if raw.is_file() else {}
            runtime = result.get("runtime_sec")
            budget_ok = runtime is not None and job["time_limit"] - 0.05 <= runtime <= job["time_limit"] + max(
                0.5, job["time_limit"] * 0.05
            )
            row = {
                **job,
                "returncode": returncode,
                "timed_out": timed_out,
                "feasible": result.get("feasible", False),
                "nv": result.get("nv"),
                "td": result.get("td"),
                "runtime_sec": runtime,
                "budget_ok": budget_ok,
                "iterations": result.get("iterations"),
                "child_wall_sec_end_to_end": wall,
                "child_cpu_sec_end_to_end": cpu,
                "cpu_wall_ratio_end_to_end": cpu / wall if cpu is not None else None,
                "load_before": json.dumps(load_before),
                "load_after": json.dumps(load_after),
                "error": result.get("error", ""),
            }
            rows.append(row)
            with (output / "summary.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(row))
                writer.writeheader()
                writer.writerows(rows)
            print(json.dumps(row), flush=True)
            status["completed_jobs"] = len(rows)
            (output / "status.json").write_text(json.dumps(status, indent=2))
            if (
                source_hash() != plan["source_sha256"]
                or sha256(model) != plan["checkpoint_sha256"]
                or sha256(instance) != plan["input_sha256"]
                or (result and result["environment"]["source_sha256"] != plan["source_sha256"])
            ):
                raise RuntimeError(
                    "Frozen identity drift during child; preserving artifacts and aborting subsequent jobs"
                )
        status.update(
            status="completed",
            all_gates_passed=all(row["returncode"] == 0 and row["feasible"] and row["budget_ok"] for row in rows),
        )
    except Exception as exc:
        status.update(status="aborted", reason=f"{type(exc).__name__}: {exc}")
        print(json.dumps(status), file=sys.stderr)
    finally:
        (output / "status.json").write_text(json.dumps(status, indent=2))
    return 0 if status["status"] == "completed" and status["all_gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
