#!/usr/bin/env python3
"""Standard Solver CLI Wrapper for Phase 2 Benchmarking.

Provides a unified contract for:
  --instance PATH
  --seed INT
  --time-limit FLOAT
  --ablation [ortools|pyvrp|neurolkh|alns|gns|gns_pool|gns_pool_lac|micro|full|full_no_macro|full_no_micro|full_no_lac|full_no_pool|full_no_gnn|full_no_gate]
  --output-json PATH
"""

from __future__ import annotations

import argparse
import cProfile
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

PROCESS_ENTRY_TIME = time.perf_counter()
# Capture before importing VRPTW/Numba. Later setup may legitimately compile.
_entry_cache = os.environ.get("NUMBA_CACHE_DIR")
PROCESS_ENTRY_STATE = {
    "cwd": str(Path.cwd()),
    "cwd_entries": sorted(path.name for path in Path.cwd().iterdir()),
    "cache_dir": _entry_cache,
    "cache_entries": sorted(str(path.relative_to(_entry_cache)) for path in Path(_entry_cache).rglob("*"))
    if _entry_cache and Path(_entry_cache).is_dir()
    else None,
}

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vrptw.ablation import bind_ablation
from vrptw.config import Config
from vrptw.core import load_solomon_instance
from vrptw.neurolkh_baseline import NeuroLKHSolver
from vrptw.ortools_baseline import ORToolsSolver
from vrptw.pyvrp_baseline import PyVRPSolver
from vrptw.solvers import ALNSSolver, HybridDDQNSolver, RuleMacroHybridSolver, RuleMicroHybridSolver


def get_env_info() -> dict[str, Any]:
    import numba
    import numpy as np
    import torch

    git_hash = None
    git_status = None
    diff_hash = None
    try:
        git_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        git_status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
        diff_hash = hashlib.sha256(subprocess.check_output(["git", "diff", "HEAD", "--binary"], cwd=ROOT)).hexdigest()
    except (OSError, subprocess.CalledProcessError):
        pass

    source_files = sorted(
        [*ROOT.glob("src/**/*.py"), *ROOT.glob("scripts/**/*.py"), ROOT / "pyproject.toml", ROOT / "uv.lock"]
    )
    source_hashes = {str(path.relative_to(ROOT)): sha256_file(path) for path in source_files if path.is_file()}
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "cuda_available": torch.cuda.is_available(),
        "solver_device": "cpu",
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "torch_threads": torch.get_num_threads(),
        "thread_environment": {
            key: os.environ.get(key)
            for key in ("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        },
        "process_entry": PROCESS_ENTRY_STATE,
        "numba": {
            "version": numba.__version__,
            "cache_dir": numba.config.CACHE_DIR,
            "disable_jit": bool(numba.config.DISABLE_JIT),
        },
        "jit_environment": {
            key: os.environ.get(key) for key in ("NUMBA_CACHE_DIR", "NUMBA_DISABLE_JIT", "PYTHONHASHSEED")
        },
        "git_commit": git_hash,
        "git_status": git_status,
        "git_diff_sha256": diff_hash,
        "source_sha256": hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest(),
        "source_files": source_hashes,
    }


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def has_exact_cover(plan: Any) -> bool:
    customers = [int(node) for route in plan.routes for node in route]
    return len(customers) == plan.inst.n and set(customers) == set(range(1, plan.inst.n + 1))


def cold_start_state(solver: Any) -> dict[str, Any]:
    """Observed state immediately after construction, before loading/solving."""
    return {
        "archive_plans": sum(len(plans) for plans in getattr(getattr(solver, "archive", None), "_plans", {}).values()),
        "pool_created": getattr(solver, "pool", None) is not None,
        "macro_replay_size": len(getattr(getattr(solver, "ctrl", None), "buf", [])),
        "micro_replay_size": len(getattr(getattr(solver, "op_ctrl", None), "buf", [])),
        "macro_training_calls": int(getattr(getattr(solver, "ctrl", None), "step", 0)),
        "micro_training_calls": int(getattr(getattr(solver, "op_ctrl", None), "step", 0)),
        "lac_queries": int(getattr(getattr(solver, "lac", None), "step", 0)),
    }


def get_solver_and_config(
    ablation: str, time_limit: float, *, seed: int = 42, wall_clock_only: bool = True, gnn_model: Path | None = None
) -> tuple[type, Config]:
    cfg = Config(
        # Explicit input is used below; keep this ancillary path identical when
        # the CLI is launched from an isolated, empty working directory.
        data_path=str(ROOT / "data" / "Solomon"),
        alns_iterations=10000,
        hybrid_iterations=10000,
        early_stop_patience=2500,
        polish_iterations=500,
        time_limit=float(time_limit),
        seed=seed,
        wall_clock_only=wall_clock_only,
    )

    if ablation.startswith("F"):
        return bind_ablation(ablation, cfg, gnn_model=gnn_model)

    # 1. Cumulative Ladder
    if ablation in ("ortools", "pyvrp", "neurolkh"):
        cfg.ortools_time_limit = float(time_limit)
        cfg.lac_enabled = False
        cfg.route_pool_limit = 0
        cfg.recombine_after_main_search = False
        cfg.recombine_after_polish = False
        return {"ortools": ORToolsSolver, "pyvrp": PyVRPSolver, "neurolkh": NeuroLKHSolver}[ablation], cfg
    elif ablation == "alns":
        cfg.lac_enabled = False
        cfg.route_pool_limit = 0
        cfg.recombine_after_main_search = False
        cfg.recombine_after_polish = False
        return ALNSSolver, cfg
    elif ablation == "gns":
        cfg.lac_enabled = False
        cfg.route_pool_limit = 0
        cfg.recombine_after_main_search = False
        cfg.recombine_after_polish = False
        return ALNSSolver, cfg
    elif ablation == "gns_pool":
        cfg.lac_enabled = False
        cfg.route_pool_limit = 480
        cfg.recombine_after_main_search = True
        cfg.recombine_after_polish = True
        return ALNSSolver, cfg
    elif ablation == "gns_pool_lac":
        cfg.lac_enabled = True
        cfg.route_pool_limit = 480
        cfg.recombine_after_main_search = True
        cfg.recombine_after_polish = True
        return ALNSSolver, cfg
    elif ablation == "micro":
        cfg.lac_enabled = True
        cfg.route_pool_limit = 480
        cfg.recombine_after_main_search = True
        cfg.recombine_after_polish = True
        cfg.macro_enabled = False
        return HybridDDQNSolver, cfg
    elif ablation == "full":
        cfg.lac_enabled = True
        cfg.route_pool_limit = 480
        cfg.recombine_after_main_search = True
        cfg.recombine_after_polish = True
        cfg.macro_enabled = True
        return HybridDDQNSolver, cfg

    # 2. Leave-One-Component-Out (LOCO) Ablations
    elif ablation == "full_no_macro":
        cfg.lac_enabled = True
        cfg.route_pool_limit = 480
        cfg.recombine_after_main_search = True
        cfg.recombine_after_polish = True
        cfg.macro_enabled = True
        return RuleMacroHybridSolver, cfg
    elif ablation == "full_no_micro":
        cfg.lac_enabled = True
        cfg.route_pool_limit = 480
        cfg.recombine_after_main_search = True
        cfg.recombine_after_polish = True
        cfg.macro_enabled = True
        cfg.use_op_rl = False
        return RuleMicroHybridSolver, cfg
    elif ablation == "full_no_lac":
        cfg.lac_enabled = False
        cfg.route_pool_limit = 480
        cfg.recombine_after_main_search = True
        cfg.recombine_after_polish = True
        cfg.macro_enabled = True
        return HybridDDQNSolver, cfg
    elif ablation == "full_no_pool":
        cfg.lac_enabled = True
        cfg.pool_recombine_enabled = False
        cfg.route_pool_limit = 0
        cfg.recombine_after_main_search = False
        cfg.recombine_after_polish = False
        cfg.macro_enabled = True
        return HybridDDQNSolver, cfg
    elif ablation in ("full_no_gns", "full_no_gnn"):
        cfg.lac_enabled = True
        cfg.route_pool_limit = 480
        cfg.recombine_after_main_search = True
        cfg.recombine_after_polish = True
        cfg.macro_enabled = True
        cfg.gnn_model_path = ""
        return HybridDDQNSolver, cfg
    elif ablation == "full_no_gate":
        cfg.lac_enabled = True
        cfg.route_pool_limit = 480
        cfg.recombine_after_main_search = True
        cfg.recombine_after_polish = True
        cfg.macro_enabled = True
        cfg.op_use_entropy_gate = False
        return HybridDDQNSolver, cfg
    elif ablation in ("full_no_gec", "no_gec"):
        cfg.lac_enabled = True
        cfg.route_pool_limit = 480
        cfg.recombine_after_main_search = True
        cfg.recombine_after_polish = True
        cfg.macro_enabled = True
        cfg.gec_enabled = False
        return HybridDDQNSolver, cfg
    else:
        raise ValueError(f"Unknown ablation configuration: {ablation}")


def extract_instrumentation(solver: Any, cfg: Config, ablation: str) -> dict[str, Any]:
    highs_calls = int(getattr(solver, "sp_stats", {}).get("calls", 0))
    highs_timeouts = int(getattr(solver, "sp_stats", {}).get("timeouts", 0))
    macro_decisions = sum(getattr(solver, "mode_trace", {}).values()) if hasattr(solver, "mode_trace") else 0
    lac_queries = int(getattr(getattr(solver, "lac", None), "step", 0))
    lac_acceptances = int(getattr(getattr(solver, "lac", None), "accept_count", 0))
    modules = {
        name: getattr(solver, attribute, None)
        for name, attribute in (("macro", "ctrl"), ("micro", "op_ctrl"), ("lac", "lac"), ("route_pool", "pool"))
    }
    module_configs = {
        name: asdict(module.cfg) for name, module in modules.items() if is_dataclass(getattr(module, "cfg", None))
    }

    hybrid = isinstance(solver, HybridDDQNSolver)
    micro_decisions = int(getattr(solver, "search_iterations", 0)) if hybrid else 0
    micro = hybrid and bool(getattr(solver, "use_op_rl", False)) and not getattr(solver, "use_op_rule", False)
    macro_policy = getattr(
        solver,
        "macro_policy",
        "rule"
        if isinstance(solver, RuleMacroHybridSolver)
        else "ddqn"
        if hybrid and solver.use_rl and cfg.macro_enabled
        else "none",
    )
    micro_policy = getattr(
        solver,
        "micro_policy",
        "ddqn"
        if micro and solver.use_rl
        else "rule"
        if getattr(solver, "use_op_rule", False)
        else "bandit"
        if hybrid
        else "none",
    )
    resolved_components = {
        "macro_ddqn": bool(hybrid and macro_policy == "ddqn" and solver.ctrl.use_rl and cfg.macro_enabled),
        "micro_ddqn": bool(micro and solver.use_rl),
        "policy_gate": bool(micro and cfg.op_use_entropy_gate),
        "lac": bool(hybrid and cfg.lac_enabled),
        "gnn_edge_guidance": getattr(solver, "gnn_model", None) is not None,
        "external_learned_candidates": isinstance(solver, NeuroLKHSolver),
        "gns": bool(hybrid and len(getattr(solver.inst, "neighbors_k", [])) > 0),
        "route_pool": bool(hybrid and cfg.pool_recombine_enabled),
        "learned_split": bool(hybrid and cfg.split_enabled),
        "gec": bool(hybrid and cfg.gec_enabled),
    }

    return {
        "ablation": ablation,
        "resolved_components": resolved_components,
        "macro_policy": macro_policy,
        "micro_policy": micro_policy,
        "controller_counts": dict(getattr(solver, "controller_counts", {})),
        "module_configs": module_configs,
        "macro_replay_size": len(solver.ctrl.buf) if hybrid and hasattr(solver.ctrl, "buf") else 0,
        "micro_replay_size": len(solver.op_ctrl.buf) if hybrid and hasattr(solver.op_ctrl, "buf") else 0,
        "macro_training_calls": int(getattr(getattr(solver, "ctrl", None), "step", 0)),
        "micro_training_calls": int(getattr(getattr(solver, "op_ctrl", None), "step", 0)),
        "highs_calls": highs_calls,
        "highs_timeouts": highs_timeouts,
        "macro_decisions": macro_decisions,
        "micro_decisions": micro_decisions,
        "lac_queries": lac_queries,
        "lac_acceptances": lac_acceptances,
        "lac_policy": getattr(getattr(solver, "lac", None), "policy", None) if hybrid and cfg.lac_enabled else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", required=True, help="Path to instance file")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--time-limit", type=float, default=60.0)
    parser.add_argument("--budget-mode", choices=["wall-clock", "capped"], default="wall-clock")
    parser.add_argument("--gnn-model", type=Path, help="Explicit pretrained GNN checkpoint; never loaded implicitly")
    parser.add_argument("--neurolkh-root", type=Path, help="Explicit prepared, pinned NeuroLKH checkout")
    parser.add_argument(
        "--phase-trace", type=Path, help="Diagnostic-only buffered phase CSV; instrumentation affects timing"
    )
    parser.add_argument(
        "--profile",
        type=Path,
        help="Diagnostic-only cProfile of solve; instrumented results are not benchmark evidence",
    )
    parser.add_argument(
        "--ablation",
        default="full",
        choices=["F" + format(i, "06b") for i in range(64)]
        + [
            "ortools",
            "pyvrp",
            "neurolkh",
            "alns",
            "gns",
            "gns_pool",
            "gns_pool_lac",
            "micro",
            "full",
            "full_no_macro",
            "full_no_micro",
            "full_no_lac",
            "full_no_pool",
            "full_no_gns",
            "full_no_gnn",
            "full_no_gate",
            "full_no_gec",
            "no_gec",
        ],
    )
    parser.add_argument("--output-json", required=True, help="Path to output JSON")
    args = parser.parse_args()
    if args.phase_trace is not None:
        if args.phase_trace.exists():
            parser.error("Phase trace already exists; use a new path")
        if args.phase_trace.resolve() == Path(args.output_json).resolve():
            parser.error("Phase trace and result need distinct paths")
        if args.profile is not None:
            parser.error("Phase tracing and cProfile cannot be combined")
        if args.ablation in ("ortools", "pyvrp", "neurolkh"):
            parser.error("Phase tracing supports native solvers only")
    if args.profile is not None and args.profile.exists():
        parser.error("Profile already exists; use a new output path")
    if args.profile is not None and args.profile.resolve() == Path(args.output_json).resolve():
        parser.error("Profile and JSON result need distinct paths")
    if args.ablation in ("ortools", "pyvrp", "neurolkh") and args.budget_mode != "wall-clock":
        parser.error("External baselines support only wall-clock budget mode")
    if args.ablation == "neurolkh":
        if args.neurolkh_root is None or not args.neurolkh_root.is_dir():
            parser.error("--ablation neurolkh requires an explicit prepared --neurolkh-root")
        if Path(args.output_json).with_suffix(".backend").exists():
            parser.error("NeuroLKH backend artifacts already exist; use a new output path")
    elif args.neurolkh_root is not None:
        parser.error("--neurolkh-root is only valid for the neurolkh baseline")

    inst_path = Path(args.instance)
    if not inst_path.exists():
        print(f"Error: instance {inst_path} does not exist", file=sys.stderr)
        sys.exit(1)

    try:
        solver_cls, cfg = get_solver_and_config(
            args.ablation,
            args.time_limit,
            seed=args.seed,
            wall_clock_only=args.budget_mode == "wall-clock",
            gnn_model=args.gnn_model,
        )
    except ValueError as exc:
        parser.error(str(exc))
    if args.neurolkh_root is not None:
        cfg.neurolkh_root = str(args.neurolkh_root.resolve())
    if args.gnn_model is not None:
        if args.ablation in ("ortools", "pyvrp", "neurolkh", "full_no_gnn", "full_no_gns"):
            parser.error("--gnn-model conflicts with a no-GNN solver/ablation")
        if not args.gnn_model.is_file():
            parser.error(f"GNN checkpoint does not exist: {args.gnn_model}")
        cfg.gnn_model_path = str(args.gnn_model.resolve())

    inst = load_solomon_instance(str(inst_path))
    metadata = {
        "instance": inst.name,
        "instance_path": str(inst_path.resolve()),
        "instance_sha256": sha256_file(inst_path),
        "customers": inst.n,
        "ablation": args.ablation,
        "seed": args.seed,
        "time_limit": args.time_limit,
        "budget_mode": args.budget_mode,
        "budget_scope": "solver.solve (includes construction, inference, search and tail; excludes imports/model load)",
        "cold_start": True,
        "pretrained_controller": False,
        "gnn_model_sha256": sha256_file(args.gnn_model) if args.gnn_model else None,
        "warmup": False,
        "profiling": {"enabled": args.profile is not None, "scope": "solver.solve only", "sha256": None},
        "phase_tracing": {
            "enabled": args.phase_trace is not None,
            "path": str(args.phase_trace.resolve()) if args.phase_trace else None,
            "scope": "solver.solve Python phases/properties and Numba compile events; diagnostic overhead; CSV serialization excluded",
            "sha256": None,
        },
    }
    result = {
        "schema_version": 2,
        "requested_ablation": args.ablation,
        "feasible": False,
        "nv": None,
        "td": None,
        "metadata": metadata,
        "environment": get_env_info(),
    }
    total_start = time.perf_counter()
    with TemporaryDirectory(prefix="vrptw_benchmark_") as run_dir:
        cfg.output_dir = run_dir
        result["requested_config"] = asdict(cfg)
        start_time = None
        solver = None
        profiler = cProfile.Profile() if args.profile is not None else None
        tracer = None
        try:
            setup_start = time.perf_counter()
            solver = solver_cls(inst, cfg)
            result["setup_timings"] = {"constructor_sec": time.perf_counter() - setup_start, "model_load_sec": 0.0}
            result["cold_start_evidence"] = cold_start_state(solver)
            if args.gnn_model is not None:
                model_start = time.perf_counter()
                solver.load_gnn_model(str(args.gnn_model))
                result["setup_timings"]["model_load_sec"] = time.perf_counter() - model_start
                if solver.gnn_model is None:
                    raise RuntimeError("Requested GNN checkpoint was not loaded")
            result["setup_timings"]["child_entry_to_solve_sec"] = time.perf_counter() - PROCESS_ENTRY_TIME
            if args.phase_trace is not None:
                from vrptw.phase_trace import PhaseTrace

                tracer = PhaseTrace(solver)
                tracer.install()
            start_time = time.perf_counter()
            if tracer is not None:
                plan, _ = tracer.call("solve", solver.solve, seed=args.seed)
            elif profiler is None:
                plan, _ = solver.solve(seed=args.seed)
            else:
                plan, _ = profiler.runcall(solver.solve, seed=args.seed)
            elapsed = time.perf_counter() - start_time
            instrumentation = extract_instrumentation(solver, solver.cfg, args.ablation)
            trajectory = list(getattr(solver, "trajectory_log", []))
            # Tail improvements must not be silently assigned to an earlier cutoff.
            trajectory.append({"t_sec": elapsed, "nv": int(plan.nv), "td": float(plan.cost), "phase": "return"})
            result.update(
                {
                    "requested_ablation": args.ablation,
                    "resolved_components": instrumentation.get("resolved_components", {}),
                    "feasible": bool(plan.feasible and has_exact_cover(plan)),
                    "validation": {"route_feasible": bool(plan.feasible), "exact_cover": has_exact_cover(plan)},
                    "routes": [[int(node) for node in route] for route in plan.routes],
                    "nv": int(plan.nv),
                    "td": float(plan.cost),
                    "runtime_sec": float(elapsed),
                    "iterations": solver.search_iterations,
                    "time_limit_hit": bool(solver.time_limit_hit),
                    "budget_overrun_sec": max(0.0, elapsed - args.time_limit),
                    "budget_underrun_sec": max(0.0, args.time_limit - elapsed),
                    "effective_config": asdict(solver.cfg),
                    "instrumentation": instrumentation,
                    "trajectory": trajectory,
                }
            )
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
            result["runtime_sec"] = time.perf_counter() - (start_time or total_start)
        finally:
            if tracer is not None:
                tracer.restore()
                if tracer.events and getattr(solver, "_deadline", None) is not None:
                    tracer.write(args.phase_trace)
                    metadata["phase_tracing"]["sha256"] = sha256_file(args.phase_trace)
                else:
                    metadata["phase_tracing"]["error"] = "No completed solve spans with a finite cutoff"
            if solver is not None and "instrumentation" not in result:
                result["effective_config"] = asdict(solver.cfg)
                result["instrumentation"] = extract_instrumentation(solver, solver.cfg, args.ablation)
                result["resolved_components"] = result["instrumentation"]["resolved_components"]
                result["iterations"] = int(getattr(solver, "search_iterations", 0))
            if hasattr(solver, "native_certification"):
                result["native_certification"] = solver.native_certification
            if profiler is not None and start_time is not None:
                args.profile.parent.mkdir(parents=True, exist_ok=True)
                profiler.dump_stats(str(args.profile))
                metadata["profiling"]["sha256"] = sha256_file(args.profile)
        if isinstance(solver, (ORToolsSolver, PyVRPSolver, NeuroLKHSolver)):
            result["adapter"] = solver.diagnostics
        if isinstance(solver, NeuroLKHSolver) and (Path(run_dir) / "neurolkh").is_dir():
            backend_dir = Path(args.output_json).resolve().with_suffix(".backend")
            backend_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(Path(run_dir) / "neurolkh", backend_dir)
            result["adapter"]["artifacts_path"] = str(backend_dir)
        result["total_runtime_sec"] = time.perf_counter() - total_start

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[{args.ablation}] {inst.name} -> NV={result['nv']}, TD={result['td']} in {result['runtime_sec']:.2f}s")
    return 1 if "error" in result or not result["feasible"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
