#!/usr/bin/env python3
"""Limited factor-binding/cold-cache operational pilot; never a quality sweep."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import random
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

import run_native_certification_pilot as native
from run_native_diagnostic import child_cpu, host_load

from vrptw.ablation import GNN_SHA256, AblationHybridSolver, factor_levels
from vrptw.core import load_solomon_instance
from vrptw.gnn_training import sha256, snapshot, source_hash
from vrptw.pool import RoutePool

CASES = ("F111111", "F000000", "F110000", "F001111", "F011111", "F101111", "F110111", "F111011")
GATES = ("certification_ok", "clock_ok", "provenance_ok", "binding_ok", "cold_ok", "budget_ok")
INTEGRITY_GATES = ("provenance_ok", "binding_ok", "cold_ok")
COLD_STATE = {
    "archive_plans": 0,
    "pool_created": False,
    "macro_replay_size": 0,
    "micro_replay_size": 0,
    "macro_training_calls": 0,
    "micro_training_calls": 0,
    "lac_queries": 0,
}


def build_schedule(order_seed):
    rng = random.Random(order_seed)
    blocks = rng.sample(list(native.INSTANCES), len(native.INSTANCES))
    cases = rng.sample(list(CASES), len(CASES))
    return [
        {
            "run": f"{Path(instance).stem}__{case}__seed42__10s",
            "instance": instance,
            "seed": 42,
            "ablation": case,
            "time_limit": 10,
            "profiled": False,
            "block": block,
            "position": position,
        }
        for block, instance in enumerate(blocks)
        for position, case in enumerate(cases[block:] + cases[:block])
    ]


def load_cli():
    spec = importlib.util.spec_from_file_location("factor_benchmark_cli", ROOT / "scripts/benchmark.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def declared_configs(cfg, inst):
    effective = AblationHybridSolver._adapt_params_to_instance(SimpleNamespace(), cfg, inst)
    signature = native.config_signature
    return {
        "requested_config": signature(asdict(cfg)),
        "effective_config": signature(asdict(effective)),
        # Controllers are constructed before solve-time adaptation; LAC/pool after.
        "module_configs": {
            "macro": signature(asdict(cfg)),
            "micro": signature(asdict(cfg)),
            "lac": signature(asdict(effective)),
            "route_pool": signature(asdict(RoutePool(inst, effective).cfg)),
        },
    }


def prepare(output, model_path, order_seed, *, jobs=None, protocol_path=None):
    custom_schedule = jobs is not None
    training_path = model_path.parent / "training.json"
    training = json.loads(training_path.read_text())
    native.require(training["status"] == "completed" and not training["smoke_only"], "incomplete/smoke training")
    native.require(sha256(model_path) == training["checkpoint_sha256"] == GNN_SHA256, "wrong frozen checkpoint")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(model_path, output / "gnn_checkpoint.pt")
    shutil.copy2(training_path, output / "training_metadata.json")
    (output / "inputs").mkdir()
    inputs = {}
    for relative in native.INSTANCES:
        dest = output / "inputs" / Path(relative).name
        shutil.copy2(ROOT / relative, dest)
        inputs[relative] = {"snapshot": str(dest.relative_to(output)), "sha256": sha256(dest)}
    jobs, cli, configs = build_schedule(order_seed) if jobs is None else jobs, load_cli(), {}
    for job in jobs:
        _, cfg = cli.get_solver_and_config(
            job["ablation"],
            job["time_limit"],
            seed=job["seed"],
            gnn_model=output / "gnn_checkpoint.pt" if factor_levels(job["ablation"])[5] else None,
        )
        configs[job["run"]] = declared_configs(cfg, load_job_instance(output, {"inputs": inputs}, job))
    snapshot(output / "source_snapshot.zip")
    with zipfile.ZipFile(output / "source_snapshot.zip", "a", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.glob("tests/**/*.py")):
            archive.write(path, path.relative_to(ROOT))
    shutil.copy2(
        protocol_path or ROOT / "docs/factor_contract_pilot_20261019.md", output / "protocol_before_execution.md"
    )
    runtime, archived = native.archived_sources(output)
    digest = hashlib.sha256(json.dumps(runtime, sort_keys=True).encode()).hexdigest()
    native.require(digest == source_hash(), "source drift during preparation")
    plan = {
        "schema_version": 1,
        "scope": "Engineering factor/cache contract only; no quality or generalization claim",
        "order_seed": order_seed,
        "jobs": jobs,
        "search_budget_sec": sum(job["time_limit"] for job in jobs),
        "cache_policy": "Fresh process, initially empty exclusive cwd and NUMBA_CACHE_DIR per job; no warmup/padding",
        "budget_scope": "solver.solve; imports/input setup/constructor/model load excluded; whole child recorded separately",
        "return_gate_sec": {"lower_slack": 0.05, "upper_slack": 0.5},
        "ordering": "Explicit caller-provided schedule; selection frozen separately"
        if custom_schedule
        else "Three shuffled input blocks, cyclic eight-case order; three distinct positions per case, not full balance",
        "failure_policy": "Preserve algorithm/return failures and continue; abort on identity/config/cache drift or timeout",
        "thread_policy": "Request one Torch/Numba/BLAS thread; actual HiGHS/backend thread count not established",
        "environment_overrides": {
            **dict.fromkeys(native.THREADS, "1"),
            "NUMBA_DISABLE_JIT": "0",
            "PYTHONHASHSEED": "42",
        },
        "source_sha256": digest,
        "source_files": runtime,
        "snapshot_files": archived,
        "checkpoint_sha256": sha256(output / "gnn_checkpoint.pt"),
        "training_metadata_sha256": sha256(output / "training_metadata.json"),
        "source_snapshot_sha256": sha256(output / "source_snapshot.zip"),
        "protocol_sha256": sha256(output / "protocol_before_execution.md"),
        "inputs": inputs,
        "configs": configs,
    }
    native.write_json(output / "plan.json", plan, "x")
    return plan


def job_dirs(output, job):
    base = output / "jobs" / job["run"]
    return base / "work", base / "cache"


def load_job_instance(output, plan, job):
    return load_solomon_instance(str(output / plan["inputs"][job["instance"]]["snapshot"]))


def identity_for(output, plan, job):
    work, cache = job_dirs(output, job)
    return native.identity_for(plan, job) | {
        "work_dir": str(work),
        "cache_dir": str(cache),
        "model_path": str(output / "gnn_checkpoint.pt") if factor_levels(job["ablation"])[5] else None,
    }


def command_for(output, plan, job):
    command = native.command_for(output, plan, job)
    if factor_levels(job["ablation"])[5]:
        command.extend(["--gnn-model", str(output / "gnn_checkpoint.pt")])
    if job.get("phase_traced", False):
        command.extend(["--phase-trace", str(output / f"{job['run']}.phases.csv")])
    return command


def audit_result(inst, job, identity, result):
    # Reuse the route/clock checks unchanged. Legacy branch provenance is ignored;
    # factor IDs have their own explicit audit below, with no label remapping.
    old = native.audit_result(result, inst, job, identity)
    verdict = {key: old[key] for key in ("certification_ok", "clock_ok")}
    errors = [e for e in old["errors"] if e.startswith(("certification_ok:", "clock_ok:"))]
    require, finite = native.require, native.finite
    gec, sp, macro, micro, lac, gnn = map(bool, factor_levels(job["ablation"]))

    def check(key, fn):
        try:
            fn()
            verdict[key] = True
        except (KeyError, ValueError, TypeError, IndexError, OverflowError) as exc:
            verdict[key] = False
            errors.append(f"{key}: {type(exc).__name__}: {exc}")

    def provenance():
        meta, env = result["metadata"], result["environment"]
        require(
            env["source_sha256"] == identity["source_sha256"] and env["source_files"] == identity["source_files"],
            "source drift",
        )
        require(meta["instance_sha256"] == identity["input_sha256"], "input drift")
        require(meta["ablation"] == result["requested_ablation"] == job["ablation"], "case drift")
        require(meta["seed"] == job["seed"] and meta["time_limit"] == job["time_limit"], "seed/budget drift")
        require(meta["gnn_model_sha256"] == (identity["checkpoint_sha256"] if gnn else None), "model drift")
        require(result["requested_config"].get("gnn_model_path") == identity.get("model_path"), "model path drift")
        require(
            env["torch_threads"] == 1 and env["thread_environment"] == dict.fromkeys(native.THREADS, "1"),
            "thread policy drift",
        )
        require(
            meta["cold_start"] is True and meta["pretrained_controller"] is False and meta["warmup"] is False,
            "warm run",
        )
        require(meta["budget_mode"] == "wall-clock" and meta["profiling"]["enabled"] is False, "budget/profiling drift")
        require(
            meta.get("phase_tracing", {}).get("enabled", False) is job.get("phase_traced", False),
            "phase instrumentation mismatch",
        )

    def binding():
        for key in ("requested_config", "effective_config"):
            require(native.config_signature(result[key]) == identity[key], f"{key} drift")
        ins, resolved = result["instrumentation"], result["resolved_components"]
        require(ins["resolved_components"] == resolved, "inconsistent component metadata")
        expected = {
            "gec": gec,
            "route_pool": sp,
            "macro_ddqn": macro,
            "micro_ddqn": micro,
            "lac": lac,
            "gnn_edge_guidance": gnn,
            "external_learned_candidates": False,
            "learned_split": False,
        }
        require(all(resolved[k] is v for k, v in expected.items()), "component mismatch")
        require(
            ins["macro_policy"] == ("ddqn" if macro else "rule")
            and ins["micro_policy"] == ("ddqn" if micro else "rule"),
            "controller policy mismatch",
        )
        actual = {name: native.config_signature(cfg) for name, cfg in ins["module_configs"].items()}
        require(actual == identity["module_configs"], "nested module config drift")
        counts = ins["controller_counts"]
        require(all(type(v) is int and v >= 0 for v in counts.values()), "invalid selection counter")
        for name, enabled in (("macro", macro), ("micro", micro)):
            forbidden = "rule" if enabled else "ddqn"
            require(counts.get(f"{name}_{forbidden}", 0) == counts.get(f"{name}_bandit", 0) == 0, "disabled policy ran")
            if not enabled:
                require(ins[f"{name}_replay_size"] == ins[f"{name}_training_calls"] == 0, "disabled controller learned")
        require(
            not set(counts) - {"macro_ddqn", "macro_rule", "micro_ddqn", "micro_rule"}, "unknown controller counter"
        )
        selections = counts.get("micro_ddqn", 0) + counts.get("micro_rule", 0)
        require(result["iterations"] <= selections <= result["iterations"] + 1, "micro selection/iteration mismatch")
        require(sp or ins["highs_calls"] == 0, "SP-off called MILP")
        require(lac or ins["lac_queries"] == ins["lac_acceptances"] == 0, "LAC-off accepted/queried")

    def cold():
        env = result["environment"]
        require(
            env["process_entry"]
            == {
                "cwd": identity["work_dir"],
                "cwd_entries": [],
                "cache_dir": identity["cache_dir"],
                "cache_entries": [],
            },
            "nonempty/shared entry cwd/cache",
        )
        require(
            env["numba"]["cache_dir"] == identity["cache_dir"] and env["numba"]["disable_jit"] is False,
            "effective Numba settings drift",
        )
        require(
            env["jit_environment"]
            == {"NUMBA_CACHE_DIR": identity["cache_dir"], "NUMBA_DISABLE_JIT": "0", "PYTHONHASHSEED": "42"},
            "JIT/hash environment drift",
        )
        require(result["cold_start_evidence"] == COLD_STATE, "nonempty initial controller/archive/pool")
        times = result["setup_timings"]
        require(
            all(
                finite(times[k]) and times[k] >= 0
                for k in ("constructor_sec", "model_load_sec", "child_entry_to_solve_sec")
            ),
            "missing setup times",
        )
        require(
            times["child_entry_to_solve_sec"] >= times["constructor_sec"] + times["model_load_sec"],
            "inconsistent setup clocks",
        )

    def budget():
        runtime = result["runtime_sec"]
        require(
            finite(runtime) and job["time_limit"] - 0.05 <= runtime <= job["time_limit"] + 0.5,
            "return outside fixed tolerance",
        )

    for key, fn in (("provenance_ok", provenance), ("binding_ok", binding), ("cold_ok", cold), ("budget_ok", budget)):
        check(key, fn)
    return {**verdict, "errors": errors}


def cache_inventory(cache):
    return {str(p.relative_to(cache)): sha256(p) for p in sorted(cache.rglob("*")) if p.is_file()}


def check_execution_identity(output, plan, plan_digest):
    native.check_frozen(output, plan)
    native.require(sha256(output / "plan.json") == plan_digest, "plan changed during execution")
    native.require(json.loads((output / "plan.json").read_text()) == plan, "in-memory plan drift")
    native.require(sha256(output / "protocol_before_execution.md") == plan["protocol_sha256"], "protocol drift")


def execute(output, plan):
    rows = []
    state = {
        "status": "running",
        "completed_jobs": 0,
        "all_gates_passed": False,
        "plan_sha256": sha256(output / "plan.json"),
    }
    native.write_json(output / "status.json", state)
    try:
        for job in plan["jobs"]:
            check_execution_identity(output, plan, state["plan_sha256"])
            work, cache = job_dirs(output, job)
            work.mkdir(parents=True, exist_ok=False)
            cache.mkdir(exist_ok=False)
            env = os.environ.copy()
            overrides = {
                **dict.fromkeys(native.THREADS, "1"),
                "NUMBA_CACHE_DIR": str(cache),
                "NUMBA_DISABLE_JIT": "0",
                "PYTHONHASHSEED": "42",
            }
            env.update(overrides)
            command = command_for(output, plan, job)
            launch = {
                "command": command,
                "cwd": str(work),
                "environment": overrides,
                "work_entries_before": list(work.iterdir()),
                "cache_entries_before": list(cache.iterdir()),
                "host_load_before": host_load(),
            }
            native.require(
                launch["work_entries_before"] == launch["cache_entries_before"] == [], "nonempty launch dirs"
            )
            native.write_json(output / f"{job['run']}.launch.json", launch, "x")
            start, cpu_start = time.perf_counter(), child_cpu()
            timed_out, returncode = False, -1
            with (
                (output / f"{job['run']}.stdout.log").open("x") as stdout,
                (output / f"{job['run']}.stderr.log").open("x") as stderr,
            ):
                try:
                    completed = subprocess.run(
                        command,
                        cwd=work,
                        env=env,
                        stdout=stdout,
                        stderr=stderr,
                        timeout=job["time_limit"] + 120,
                        check=False,
                    )
                    returncode = completed.returncode
                except subprocess.TimeoutExpired:
                    timed_out = True
            wall, cpu_end = time.perf_counter() - start, child_cpu()
            launch.update(
                returncode=returncode,
                timed_out=timed_out,
                child_wall_sec_end_to_end=wall,
                child_cpu_sec=None if cpu_start is None else cpu_end - cpu_start,
                host_load_after=host_load(),
                cache_files_after=cache_inventory(cache),
            )
            native.write_json(output / f"{job['run']}.launch.json", launch)
            try:
                raw = json.loads((output / f"{job['run']}.json").read_text())
            except (OSError, ValueError) as exc:
                raw = {"error": f"unreadable child result: {exc}"}
            audited = audit_result(load_job_instance(output, plan, job), job, identity_for(output, plan, job), raw)
            cert = (raw.get("native_certification") or {}).get("certificate") or {}
            row = {
                **job,
                "returncode": returncode,
                "timed_out": timed_out,
                **{k: raw.get(k) for k in ("feasible", "nv", "td", "runtime_sec", "iterations")},
                "captured_sec": cert.get("captured_sec"),
                "child_wall_sec_end_to_end": wall,
                "child_cpu_sec": launch["child_cpu_sec"],
                **{k: audited[k] for k in GATES},
                "error": raw.get("error", ""),
                "audit_errors": json.dumps(audited["errors"]),
            }
            rows.append(row)
            with (output / "summary.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(row))
                writer.writeheader()
                writer.writerows(rows)
            state["completed_jobs"] = len(rows)
            native.write_json(output / "status.json", state)
            print(json.dumps(row, allow_nan=False), flush=True)
            check_execution_identity(output, plan, state["plan_sha256"])
            native.require(
                not timed_out and all(audited[k] for k in INTEGRITY_GATES), "timeout or protocol integrity gate failed"
            )
        state.update(
            status="completed",
            all_gates_passed=all(
                row["returncode"] == 0 and not row["timed_out"] and all(row[k] for k in GATES) for row in rows
            ),
        )
    except Exception as exc:
        state.update(status="aborted", reason=f"{type(exc).__name__}: {exc}")
    finally:
        native.write_json(output / "status.json", state)
    return state


def audit_directory(output, *, expected_jobs=None):
    """Reopen raw evidence and independently reproduce every CSV gate and value."""
    plan = json.loads((output / "plan.json").read_text())
    state = json.loads((output / "status.json").read_text())
    native.check_frozen(output, plan)
    runtime, archived = native.archived_sources(output)
    native.require(
        runtime == plan["source_files"] and archived == plan["snapshot_files"], "source archive manifest mismatch"
    )
    native.require(sha256(output / "plan.json") == state["plan_sha256"], "plan changed after execution start")
    native.require(sha256(output / "protocol_before_execution.md") == plan["protocol_sha256"], "protocol drift")
    expected_jobs = build_schedule(plan["order_seed"]) if expected_jobs is None else expected_jobs
    native.require(
        plan["jobs"] == expected_jobs and plan["search_budget_sec"] == sum(j["time_limit"] for j in expected_jobs),
        "schedule drift",
    )
    native.require(plan["checkpoint_sha256"] == GNN_SHA256, "wrong checkpoint")
    with (output / "summary.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    native.require([r["run"] for r in rows] == [j["run"] for j in plan["jobs"][: len(rows)]], "CSV schedule drift")
    verified, directories = [], []
    for job, row in zip(plan["jobs"], rows, strict=False):
        launch = json.loads((output / f"{job['run']}.launch.json").read_text())
        work, cache = job_dirs(output, job)
        native.require(
            launch["command"] == command_for(output, plan, job) and launch["cwd"] == str(work), "command/cwd drift"
        )
        native.require(
            launch["environment"] == {**plan["environment_overrides"], "NUMBA_CACHE_DIR": str(cache)},
            "launch environment drift",
        )
        native.require(launch["work_entries_before"] == launch["cache_entries_before"] == [], "nonempty launch dirs")
        native.require(cache_inventory(cache) == launch["cache_files_after"], "cache artifact drift")
        try:
            raw = json.loads((output / f"{job['run']}.json").read_text())
        except (OSError, ValueError) as exc:
            raw = {"error": f"unreadable child result: {exc}"}
        audited = audit_result(load_job_instance(output, plan, job), job, identity_for(output, plan, job), raw)
        for key in GATES:
            native.require(row[key] == str(audited[key]), f"CSV gate drift: {job['run']}/{key}")
        for key in ("feasible", "nv", "td", "runtime_sec", "iterations"):
            native.require(row[key] == (str(raw[key]) if raw.get(key) is not None else ""), f"CSV value drift: {key}")
        cert = (raw.get("native_certification") or {}).get("certificate") or {}
        native.require(
            row["captured_sec"] == (str(cert["captured_sec"]) if cert.get("captured_sec") is not None else ""),
            "CSV capture drift",
        )
        for key in ("returncode", "timed_out", "child_wall_sec_end_to_end", "child_cpu_sec"):
            native.require(
                row[key] == (str(launch[key]) if launch[key] is not None else ""), f"CSV process metric drift: {key}"
            )
        native.require(
            json.loads(row["audit_errors"]) == audited["errors"] and row["error"] == raw.get("error", ""),
            "CSV error drift",
        )
        for key in ("child_wall_sec_end_to_end", "child_cpu_sec"):
            native.require(native.finite(launch[key]) and launch[key] >= 0, "invalid process duration")
        if raw.get("requested_config"):
            directories.append(raw["requested_config"]["output_dir"])
        verified.append(
            {"run": job["run"], "process_ok": launch["returncode"] == 0 and not launch["timed_out"], **audited}
        )
    native.require(len(directories) == len(set(directories)), "reused solver output directory")
    complete = state["status"] == "completed" and state["completed_jobs"] == len(rows) == len(plan["jobs"])
    passed = complete and all(v["process_ok"] and all(v[k] for k in GATES) for v in verified)
    native.require(state["all_gates_passed"] == passed, "status gate drift")
    audit = {
        "status": "passed" if passed else "failed",
        "complete": complete,
        "source_sha256": plan["source_sha256"],
        "checkpoint_sha256": plan["checkpoint_sha256"],
        "verified_runs": verified,
        "audit_program_sha256": sha256(Path(__file__)),
        "artifact_hashes": {
            str(p.relative_to(output)): sha256(p)
            for p in sorted(output.rglob("*"))
            if p.is_file() and p.name != "audit.json"
        },
        "limits": "Declared engineering schedule only; no hard deadline, ranking, causal attribution or generalization claim",
    }
    native.write_json(output / "audit.json", audit, "x")
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--gnn-model", type=Path)
    parser.add_argument("--order-seed", type=int, default=20261019)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    native.require(not (output / "audit.json").exists(), "audit exists; preserve prior record")
    if not args.audit_only:
        if args.gnn_model is None:
            parser.error("--gnn-model required for a new pilot")
        plan = prepare(output, args.gnn_model.resolve(), args.order_seed)
        execute(output, plan)
    audit = audit_directory(output)
    print(
        json.dumps(
            {"status": audit["status"], "complete": audit["complete"], "verified_jobs": len(audit["verified_runs"])}
        ),
        flush=True,
    )
    return 0 if audit["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
