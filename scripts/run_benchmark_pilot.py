#!/usr/bin/env python3
"""Sequential cold-start smoke test, not a publication performance experiment."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTANCES = (
    "data/Solomon/c101.txt",
    "data/Gehring_Homberger/homberger_200_customer_instances/R1_2_1.TXT",
    "data/Gehring_Homberger/homberger_400_customer_instances/RC2_4_1.TXT",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gnn-model", type=Path, help="Add full hybrid runs using a snapshot of this checkpoint")
    parser.add_argument("--include-ortools", action="store_true", help="Add the audited external OR-Tools baseline")
    parser.add_argument("--include-pyvrp", action="store_true", help="Add the pinned external PyVRP ILS baseline")
    parser.add_argument("--neurolkh-root", type=Path, help="Add adapted NeuroLKH using these prepared pinned assets")
    args = parser.parse_args()
    if not (0 < args.time_limit <= 300):
        parser.error("pilot time limit must be in (0, 300]")
    if args.gnn_model is not None and not args.gnn_model.is_file():
        parser.error(f"missing GNN checkpoint: {args.gnn_model}")
    if args.neurolkh_root is not None and not (args.neurolkh_root / "assets.json").is_file():
        parser.error(f"missing NeuroLKH build manifest: {args.neurolkh_root}")
    for relative in INSTANCES:
        if not (ROOT / relative).is_file():
            parser.error(f"missing pilot instance: {relative}")
    args.output_dir = args.output_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    model_snapshot = None
    if args.gnn_model is not None:
        model_snapshot = args.output_dir / f"gnn_checkpoint{args.gnn_model.suffix}"
        shutil.copy2(args.gnn_model, model_snapshot)
    with zipfile.ZipFile(args.output_dir / "source_snapshot.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(
            [
                *ROOT.glob("src/**/*.py"),
                *ROOT.glob("scripts/**/*.py"),
                *ROOT.glob("tests/**/*.py"),
                ROOT / "pyproject.toml",
                ROOT / "uv.lock",
            ]
        ):
            if path.is_file():
                archive.write(path, path.relative_to(ROOT))
    env = os.environ.copy()
    env.update(
        {key: "1" for key in ("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}
    )
    rows = []
    ablations = ["alns", "full_no_gnn"]
    if model_snapshot:
        ablations.append("full")
    if args.include_ortools:
        ablations.append("ortools")
    if args.include_pyvrp:
        ablations.append("pyvrp")
    if args.neurolkh_root is not None:
        ablations.append("neurolkh")
        shutil.copy2(args.neurolkh_root / "assets.json", args.output_dir / "neurolkh_assets.json")
    for relative in INSTANCES:
        for ablation in ablations:
            run_id = f"{Path(relative).stem}__{ablation}__seed{args.seed}"
            output = args.output_dir / f"{run_id}.json"
            command = [
                sys.executable,
                str(ROOT / "scripts/benchmark.py"),
                "--instance",
                str(ROOT / relative),
                "--seed",
                str(args.seed),
                "--time-limit",
                str(args.time_limit),
                "--budget-mode",
                "wall-clock",
                "--ablation",
                ablation,
                "--output-json",
                str(output),
            ]
            if ablation == "full":
                command.extend(["--gnn-model", str(model_snapshot)])
            if ablation == "neurolkh":
                command.extend(["--neurolkh-root", str(args.neurolkh_root.resolve())])
            (args.output_dir / f"{run_id}.command.json").write_text(json.dumps(command, indent=2))
            timed_out = False
            with (
                (args.output_dir / f"{run_id}.stdout.log").open("w") as stdout,
                (args.output_dir / f"{run_id}.stderr.log").open("w") as stderr,
            ):
                try:
                    completed = subprocess.run(
                        command,
                        cwd=ROOT,
                        env=env,
                        stdout=stdout,
                        stderr=stderr,
                        timeout=args.time_limit + 120,
                        check=False,
                    )
                    returncode = completed.returncode
                except subprocess.TimeoutExpired:
                    timed_out = True
                    returncode = -1
            result = json.loads(output.read_text()) if output.is_file() else {}
            runtime = result.get("runtime_sec")
            budget_ok = runtime is not None and args.time_limit - 0.05 <= runtime <= args.time_limit + max(
                0.5, args.time_limit * 0.05
            )
            row = {
                "run": run_id,
                "returncode": returncode,
                "timed_out": timed_out,
                "feasible": result.get("feasible", False),
                "nv": result.get("nv"),
                "td": result.get("td"),
                "runtime_sec": runtime,
                "budget_ok": budget_ok,
                "iterations": result.get("iterations"),
                "error": result.get("error", ""),
            }
            rows.append(row)
            with (args.output_dir / "summary.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(row))
                writer.writeheader()
                writer.writerows(rows)
            print(json.dumps(row), flush=True)
    return 0 if all(r["returncode"] == 0 and r["feasible"] and r["budget_ok"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
