#!/usr/bin/env python3
"""Opt-in native supervisor; separate execution protocol from benchmark.py."""

from __future__ import annotations

import argparse
import json
import math
import resource
import subprocess
import time
from dataclasses import asdict
from pathlib import Path

CLI_ENTRY_TIME = time.perf_counter()

import benchmark as native_cli

from vrptw.supervisor import supervise

ROOT = Path(__file__).resolve().parents[1]
COLD = {
    "archive_plans": 0,
    "pool_created": False,
    "macro_replay_size": 0,
    "micro_replay_size": 0,
    "macro_training_calls": 0,
    "micro_training_calls": 0,
    "lac_queries": 0,
}


def backend_identity(case, cfg):
    """Exact adapter assets, read in both parent and worker before starting T."""
    if case == "pyvrp":
        from importlib.metadata import PackageNotFoundError, version

        from vrptw.pyvrp_baseline import PYVRP_VERSION

        try:
            observed = version("pyvrp")
        except PackageNotFoundError as exc:
            raise ValueError("the pinned PyVRP baselines extra is not installed") from exc
        if observed != PYVRP_VERSION:
            raise ValueError(f"Expected PyVRP {PYVRP_VERSION}, got {observed}")
        return {"adapter": "pyvrp-ils", "version": observed}
    if case == "neurolkh":
        from vrptw.neurolkh_baseline import asset_identity

        root = Path(cfg.neurolkh_root)
        try:
            manifest = json.loads((root / "assets.json").read_text())
            assets = asset_identity(root)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ValueError(f"NeuroLKH assets could not be verified: {exc}") from exc
        if assets != manifest.get("identity") or "build" not in manifest:
            raise ValueError("NeuroLKH assets differ from prepared build manifest")
        return {
            "adapter": "neurolkh-adapted",
            "assets": assets,
            "manifest_sha256": native_cli.sha256_file(root / "assets.json"),
        }
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument(
        "--ablation", choices=["alns", "pyvrp", "neurolkh", *["F" + format(i, "06b") for i in range(64)]], required=True
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--time-limit", type=float, required=True)
    parser.add_argument("--gnn-model", type=Path)
    parser.add_argument("--neurolkh-root", type=Path)
    parser.add_argument("--session-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    session, output = args.session_dir.resolve(), args.output_json.resolve()
    if not math.isfinite(args.time_limit) or args.time_limit <= 0:
        parser.error("time limit must be positive and finite")
    if session.exists() or output.exists():
        parser.error("session/output already exists; preserve prior evidence")
    if session == output or session in output.parents or output in session.parents:
        parser.error("result must be separate from worker session messages")
    if not args.instance.is_file() or (args.gnn_model and not args.gnn_model.is_file()):
        parser.error("input/model file is missing")
    if not args.ablation.startswith("F") and args.gnn_model:
        parser.error("this supervised case does not accept the native GNN")
    if (args.ablation == "neurolkh") != (args.neurolkh_root is not None):
        parser.error("--neurolkh-root is required only for neurolkh")
    if args.neurolkh_root and not args.neurolkh_root.is_dir():
        parser.error("NeuroLKH root is missing")
    model = args.gnn_model.resolve() if args.gnn_model else None
    try:
        _, cfg = native_cli.get_solver_and_config(args.ablation, args.time_limit, seed=args.seed, gnn_model=model)
        if args.neurolkh_root:
            cfg.neurolkh_root = str(args.neurolkh_root.resolve())
        backend = backend_identity(args.ablation, cfg)
    except ValueError as exc:
        parser.error(str(exc))
    cfg.output_dir = str(session / "work/archive")
    environment = native_cli.get_env_info()
    identity = {
        "case": args.ablation,
        "seed": args.seed,
        "source_sha256": environment["source_sha256"],
        "instance_sha256": native_cli.sha256_file(args.instance),
        "gnn_model_sha256": native_cli.sha256_file(model) if model else None,
        "requested_config": asdict(cfg),
    }
    if backend is not None:
        identity["backend_identity"] = backend
    request = {
        "identity": identity,
        "expected_cold": COLD,
        "time_limit": args.time_limit,
        "instance": str(args.instance.resolve()),
        "gnn_model": str(model) if model else None,
    }
    if args.ablation == "neurolkh":
        request["descendant_cleanup_required"] = True
        request["neurolkh_root"] = cfg.neurolkh_root
    inst = native_cli.load_solomon_instance(str(args.instance))
    plan, supervised = supervise(inst, ROOT / "scripts/native_supervisor_worker.py", request, session)
    counters = supervised.get("final_worker_counters")
    result = {
        **supervised,
        "schema_version": 3,
        "execution_mode": "external_supervisor_v1" if backend is not None else "native_supervisor_v1",
        "requested_ablation": args.ablation,
        "feasible": plan is not None,
        "routes": plan.routes if plan else None,
        "nv": plan.nv if plan else None,
        "td": plan.cost if plan else None,
        "requested_config": asdict(cfg),
        "iterations": counters.get("iterations") if counters else None,
        "effective_config": counters.get("effective_config") if counters else None,
        "instrumentation": counters.get("instrumentation") if counters else None,
        "environment": environment,
        "metadata": {
            **identity,
            "instance_path": str(args.instance.resolve()),
            "customers": inst.n,
            "time_limit": args.time_limit,
            "budget_scope": "parent start through IPC, independent validation and worker cleanup; worker setup excluded and separately recorded",
            "hard_return_deadline": False,
            "warmup": False,
            "cold_start": True,
            "session_dir": str(session),
            "counter_scope": "complete worker counters or null; worker_checkpoint is partial",
        },
    }
    self_usage, child_usage = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
    result["whole_cli_cpu_sec_before_output"] = (
        self_usage.ru_utime + self_usage.ru_stime + child_usage.ru_utime + child_usage.ru_stime
    )
    result["whole_cli_wall_sec_before_output"] = time.perf_counter() - CLI_ENTRY_TIME
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(
        json.dumps(
            {"feasible": result["feasible"], "runtime_sec": result.get("runtime_sec"), "error": result.get("error")}
        ),
        flush=True,
    )
    return 0 if plan is not None and "error" not in result else 1


if __name__ == "__main__":
    raise SystemExit(main())
