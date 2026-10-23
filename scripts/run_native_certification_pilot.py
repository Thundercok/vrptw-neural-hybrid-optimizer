#!/usr/bin/env python3
"""Prespecified 18-run certification pilot and independent artifact audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import itertools
import json
import math
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
sys.path.insert(0, str(ROOT / "src"))

from vrptw.core import load_solomon_instance
from vrptw.gnn_training import sha256, snapshot, source_hash

INSTANCES = (
    "data/Solomon/c101.txt",
    "data/Gehring_Homberger/homberger_200_customer_instances/R1_2_1.TXT",
    "data/Gehring_Homberger/homberger_400_customer_instances/RC2_4_1.TXT",
)
BRANCHES = ("alns", "full_no_gnn", "full")
THREADS = ("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")


def build_schedule(order_seed):
    rng = random.Random(order_seed)
    blocks = list(itertools.product(INSTANCES, (42, 43)))
    rng.shuffle(blocks)
    branches = rng.sample(list(BRANCHES), len(BRANCHES))
    jobs = []
    for block, (instance, seed) in enumerate(blocks):
        shift = block % len(branches)
        for position, branch in enumerate(branches[shift:] + branches[:shift]):
            jobs.append(
                {
                    "run": f"{Path(instance).stem}__{branch}__seed{seed}__10s",
                    "instance": instance,
                    "seed": seed,
                    "ablation": branch,
                    "time_limit": 10,
                    "profiled": False,
                    "block": block,
                    "position": position,
                }
            )
    return jobs


def config_signature(config):
    return {key: value for key, value in config.items() if key not in ("output_dir", "gnn_model_path")}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def independent_routes(routes, inst):
    """Audit from coordinates and raw windows; never use Plan/certifier caches."""
    require(
        isinstance(routes, list) and all(isinstance(route, list) and route for route in routes),
        "empty/malformed routes",
    )
    nodes = [node for route in routes for node in route]
    require(all(type(node) is int for node in nodes), "noninteger customer ID")
    require(sorted(nodes) == list(range(1, inst.n + 1)), "not an exact customer cover")
    distances = []
    for route in routes:
        require(sum(float(inst.demands[node]) for node in route) <= inst.capacity, "capacity violation")
        elapsed = 0.0
        previous = 0
        for node in route:
            travel = math.dist(inst.coords[previous], inst.coords[node])
            distances.append(travel)
            elapsed = max(elapsed + travel, float(inst.ready_times[node]))
            require(elapsed <= inst.due_times[node], "customer time-window violation")
            elapsed += float(inst.service_times[node])
            previous = node
        home = math.dist(inst.coords[previous], inst.coords[0])
        distances.append(home)
        require(elapsed + home <= inst.due_times[0], "depot return violation")
    return len(routes), math.fsum(distances)


def audit_result(result, inst, job, identity):
    """Keep provenance, route certification, clock and return gates separate."""
    verdict = {key: False for key in ("certification_ok", "clock_ok", "provenance_ok", "budget_ok")}
    errors = []
    budget = job["time_limit"]

    def check(key, function):
        try:
            function()
            verdict[key] = True
        except (KeyError, ValueError, TypeError, IndexError, OverflowError) as exc:
            errors.append(f"{key}: {type(exc).__name__}: {exc}")

    def certification():
        require("error" not in result and result["feasible"] is True, "solve failed")
        nv, distance = independent_routes(result["routes"], inst)
        native, cert = result["native_certification"], result["native_certification"]["certificate"]
        require(native["schema_version"] == 1 and native["status"] == "certified", "missing successful certificate")
        require(native["clock"] == cert["clock"] == "perf_counter", "wrong clock domain")
        require(native["hard_return_deadline"] is False, "unsupported hard-deadline claim")
        require(native["cutoff_sec"] == cert["cutoff_sec"] == budget, "wrong certification budget")
        require(finite(cert["captured_sec"]) and 0 <= cert["captured_sec"] < budget, "capture not strictly pre-cutoff")
        require(result["nv"] == cert["nv"] == nv, "fleet mismatch")
        for value in (result["td"], cert["td"]):
            require(finite(value) and math.isclose(value, distance, abs_tol=1e-6, rel_tol=1e-9), "distance mismatch")
        digest = hashlib.sha256(json.dumps(result["routes"], separators=(",", ":")).encode("utf-8")).hexdigest()
        require(cert["routes_sha256"] == digest, "route hash mismatch")
        require(
            cert["validation"] == {"exact_cover": True, "route_feasible": True, "objective_recomputed": True},
            "missing validation flags",
        )
        require(result["validation"] == {"exact_cover": True, "route_feasible": True}, "missing result validation")
        require(
            all(type(native[key]) is int and native[key] >= 0 for key in ("rejected_late", "rejected_invalid")),
            "invalid rejection counters",
        )

    def clocks():
        native, points = result["native_certification"], result["trajectory"]
        cert, runtime = native["certificate"], result["runtime_sec"]
        require(finite(runtime) and finite(native["elapsed_sec"]), "nonfinite elapsed time")
        require(0 <= cert["captured_sec"] <= native["elapsed_sec"] <= runtime, "inconsistent elapsed clocks")
        require(len(points) >= 2 and points[-1]["phase"] == "return", "missing separate return observation")
        require(
            points[-1]["t_sec"] == runtime and points[-1]["nv"] == result["nv"] and points[-1]["td"] == result["td"],
            "return observation mismatch",
        )
        previous = None
        for point in points[:-1]:
            require(finite(point["t_sec"]) and 0 <= point["t_sec"] < budget, "trajectory capture at/after cutoff")
            require(
                type(point["nv"]) is int and point["nv"] > 0 and finite(point["td"]), "invalid trajectory objective"
            )
            require(
                isinstance(point["routes_sha256"], str) and len(point["routes_sha256"]) == 64, "missing trajectory hash"
            )
            if previous is not None:
                require(point["t_sec"] >= previous["t_sec"], "trajectory clock reversal")
                require(
                    point["nv"] < previous["nv"]
                    or (point["nv"] == previous["nv"] and point["td"] < previous["td"] - 1e-6),
                    "trajectory is not fleet-first improvements",
                )
            previous = point
        for field, cert_field in (
            ("t_sec", "captured_sec"),
            ("nv", "nv"),
            ("td", "td"),
            ("routes_sha256", "routes_sha256"),
            ("phase", "phase"),
            ("iter", "iter"),
        ):
            require(previous[field] == cert[cert_field], f"final trajectory/certificate mismatch: {field}")

    def provenance():
        meta, env = result["metadata"], result["environment"]
        require(
            env["source_sha256"] == identity["source_sha256"] and env["source_files"] == identity["source_files"],
            "source drift",
        )
        require(
            env["torch_threads"] == 1 and env["thread_environment"] == dict.fromkeys(THREADS, "1"),
            "unexpected thread settings",
        )
        require(meta["instance_sha256"] == identity["input_sha256"], "input drift")
        require(meta["seed"] == job["seed"] and meta["time_limit"] == budget, "seed/budget mismatch")
        require(meta["ablation"] == result["requested_ablation"] == job["ablation"], "branch mismatch")
        require(
            meta["cold_start"] is True and meta["warmup"] is False and meta["budget_mode"] == "wall-clock",
            "unexpected run protocol",
        )
        require(
            meta["profiling"] == {"enabled": False, "scope": "solver.solve only", "sha256": None}
            or meta["profiling"] == {"enabled": False, "sha256": None},
            "instrumented run",
        )
        full = job["ablation"] == "full"
        require(meta["gnn_model_sha256"] == (identity["checkpoint_sha256"] if full else None), "model drift")
        require(
            result["resolved_components"]["gnn_edge_guidance"] is full
            and result["resolved_components"]["external_learned_candidates"] is False,
            "component mismatch",
        )
        for key in ("requested_config", "effective_config"):
            require(config_signature(result[key]) == identity[key], f"{key} differs from declared config")

    def return_budget():
        runtime = result["runtime_sec"]
        require(
            finite(runtime) and budget - 0.05 <= runtime <= budget + max(0.5, 0.05 * budget),
            "return outside unchanged operational tolerance",
        )

    check("certification_ok", certification)
    check("clock_ok", clocks)
    check("provenance_ok", provenance)
    check("budget_ok", return_budget)
    return {**verdict, "errors": errors}


def write_json(path, value, mode="w"):
    with path.open(mode) as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def archived_sources(output):
    with zipfile.ZipFile(output / "source_snapshot.zip") as archive:
        all_hashes = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
    runtime = {name: digest for name, digest in all_hashes.items() if not name.startswith("tests/")}
    return runtime, all_hashes


def prepare(output, model_path, order_seed):
    require(model_path.is_file(), f"missing checkpoint: {model_path}")
    training_path = model_path.parent / "training.json"
    training = json.loads(training_path.read_text())
    require(
        training["status"] == "completed" and not training["smoke_only"], "checkpoint is not completed training output"
    )
    require(sha256(model_path) == training["checkpoint_sha256"], "checkpoint/training metadata mismatch")
    require(all((ROOT / relative).is_file() for relative in INSTANCES), "missing pilot input")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(model_path, output / "gnn_checkpoint.pt")
    shutil.copy2(training_path, output / "training_metadata.json")
    (output / "inputs").mkdir()
    inputs = {}
    for relative in INSTANCES:
        dest = output / "inputs" / Path(relative).name
        shutil.copy2(ROOT / relative, dest)
        inputs[relative] = {"snapshot": str(dest.relative_to(output)), "sha256": sha256(dest)}
    spec = importlib.util.spec_from_file_location("certification_benchmark_cli", ROOT / "scripts/benchmark.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    jobs = build_schedule(order_seed)
    configs = {}
    for job in jobs:
        solver_cls, cfg = cli.get_solver_and_config(job["ablation"], job["time_limit"], seed=job["seed"])
        effective = cfg
        if job["ablation"] != "alns":
            inst = load_solomon_instance(str(ROOT / job["instance"]))
            effective = solver_cls._adapt_params_to_instance(SimpleNamespace(), cfg, inst)
        configs[job["run"]] = {
            "requested_config": config_signature(asdict(cfg)),
            "effective_config": config_signature(asdict(effective)),
        }
    snapshot(output / "source_snapshot.zip")
    with zipfile.ZipFile(output / "source_snapshot.zip", "a", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.glob("tests/**/*.py")):
            archive.write(path, path.relative_to(ROOT))
    runtime_files, all_files = archived_sources(output)
    digest = hashlib.sha256(json.dumps(runtime_files, sort_keys=True).encode()).hexdigest()
    require(digest == source_hash(), "source drift during preparation")
    plan = {
        "schema_version": 1,
        "scope": "Operational certification pilot only; no ranking, parameter selection or publication sweep",
        "order_seed": order_seed,
        "jobs": jobs,
        "search_budget_sec": sum(j["time_limit"] for j in jobs),
        "selection_policy": "Every declared job once; preserve failures; no score-based exclusions, adaptive reruns or tuning",
        "ordering": "Shuffled instance/seed blocks; cyclic branch order balanced over six blocks",
        "timing_policy": "Independent cold solve budgets; operational return gate T-0.05 to T+max(0.5,0.05*T); no hard deadline claim",
        "thread_policy": "Torch/Numba/BLAS environment requests one thread; actual HiGHS/backend thread counts are not established",
        "source_sha256": digest,
        "source_files": runtime_files,
        "snapshot_files": all_files,
        "checkpoint_sha256": sha256(output / "gnn_checkpoint.pt"),
        "training_metadata_sha256": sha256(output / "training_metadata.json"),
        "source_snapshot_sha256": sha256(output / "source_snapshot.zip"),
        "inputs": inputs,
        "configs": configs,
    }
    write_json(output / "plan.json", plan, "x")
    return plan


def identity_for(plan, job):
    return {key: plan[key] for key in ("source_sha256", "source_files", "checkpoint_sha256")} | {
        "input_sha256": plan["inputs"][job["instance"]]["sha256"],
        **plan["configs"][job["run"]],
    }


def command_for(output, plan, job):
    command = [
        sys.executable,
        str(ROOT / "scripts/benchmark.py"),
        "--instance",
        str(output / plan["inputs"][job["instance"]]["snapshot"]),
        "--seed",
        str(job["seed"]),
        "--time-limit",
        str(job["time_limit"]),
        "--budget-mode",
        "wall-clock",
        "--ablation",
        job["ablation"],
        "--output-json",
        str(output / f"{job['run']}.json"),
    ]
    if job["ablation"] == "full":
        command.extend(["--gnn-model", str(output / "gnn_checkpoint.pt")])
    return command


def check_frozen(output, plan):
    require(source_hash() == plan["source_sha256"], "runtime source drift")
    for filename, key in (
        ("source_snapshot.zip", "source_snapshot_sha256"),
        ("gnn_checkpoint.pt", "checkpoint_sha256"),
        ("training_metadata.json", "training_metadata_sha256"),
    ):
        require(sha256(output / filename) == plan[key], f"frozen artifact drift: {filename}")
    for relative, entry in plan["inputs"].items():
        require(sha256(output / entry["snapshot"]) == entry["sha256"] == sha256(ROOT / relative), "input drift")
    for name, digest in plan["snapshot_files"].items():
        require(sha256(ROOT / name) == digest, f"snapshot source/test drift: {name}")


def execute(output, plan):
    rows = []
    status = {"status": "running", "completed_jobs": 0, "all_gates_passed": False}
    write_json(output / "status.json", status)
    env = os.environ.copy()
    env.update(dict.fromkeys(THREADS, "1"))
    try:
        for job in plan["jobs"]:
            check_frozen(output, plan)
            command = command_for(output, plan, job)
            write_json(output / f"{job['run']}.command.json", command, "x")
            start = time.perf_counter()
            timed_out, returncode = False, -1
            with (
                (output / f"{job['run']}.stdout.log").open("x") as stdout,
                (output / f"{job['run']}.stderr.log").open("x") as stderr,
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
                    timed_out = True
            wall = time.perf_counter() - start
            raw = output / f"{job['run']}.json"
            try:
                result = json.loads(raw.read_text())
            except (OSError, ValueError) as exc:
                result = {"error": f"unreadable child result: {exc}"}
            inst = load_solomon_instance(str(output / plan["inputs"][job["instance"]]["snapshot"]))
            audit = audit_result(result, inst, job, identity_for(plan, job))
            cert = (result.get("native_certification") or {}).get("certificate") or {}
            row = {
                **job,
                "returncode": returncode,
                "timed_out": timed_out,
                "feasible": result.get("feasible", False),
                "nv": result.get("nv"),
                "td": result.get("td"),
                "runtime_sec": result.get("runtime_sec"),
                "iterations": result.get("iterations"),
                "captured_sec": cert.get("captured_sec"),
                "routes_sha256": cert.get("routes_sha256"),
                "child_wall_sec_end_to_end": wall,
                **{key: value for key, value in audit.items() if key != "errors"},
                "error": result.get("error", ""),
                "audit_errors": json.dumps(audit["errors"]),
            }
            rows.append(row)
            with (output / "summary.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(row))
                writer.writeheader()
                writer.writerows(rows)
            status["completed_jobs"] = len(rows)
            write_json(output / "status.json", status)
            print(json.dumps(row, allow_nan=False), flush=True)
            check_frozen(output, plan)
        status.update(
            status="completed",
            all_gates_passed=all(
                row["returncode"] == 0
                and not row["timed_out"]
                and all(row[key] for key in ("certification_ok", "clock_ok", "provenance_ok", "budget_ok"))
                for row in rows
            ),
        )
    except Exception as exc:
        status.update(status="aborted", reason=f"{type(exc).__name__}: {exc}")
    finally:
        write_json(output / "status.json", status)
    return status


def audit_directory(output):
    """Reopen frozen evidence; never reclassify a failed return as a timing pass."""
    plan = json.loads((output / "plan.json").read_text())
    status = json.loads((output / "status.json").read_text())
    runtime, archived = archived_sources(output)
    integrity_errors = []
    require(runtime == plan["source_files"] and archived == plan["snapshot_files"], "snapshot file manifest mismatch")
    require(
        hashlib.sha256(json.dumps(runtime, sort_keys=True).encode()).hexdigest() == plan["source_sha256"],
        "archived source hash mismatch",
    )
    require(
        plan["jobs"] == build_schedule(plan["order_seed"]) and plan["search_budget_sec"] == 180,
        "declared schedule mismatch",
    )
    for filename, key in (
        ("source_snapshot.zip", "source_snapshot_sha256"),
        ("gnn_checkpoint.pt", "checkpoint_sha256"),
        ("training_metadata.json", "training_metadata_sha256"),
    ):
        require(sha256(output / filename) == plan[key], f"artifact hash mismatch: {filename}")
    training = json.loads((output / "training_metadata.json").read_text())
    require(
        training["checkpoint_sha256"] == plan["checkpoint_sha256"]
        and training["status"] == "completed"
        and training["smoke_only"] is False,
        "training provenance mismatch",
    )
    with (output / "summary.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    require(
        [row["run"] for row in rows] == [job["run"] for job in plan["jobs"][: len(rows)]], "summary schedule mismatch"
    )
    verified, directories = [], []
    for job, row in zip(plan["jobs"], rows, strict=False):
        path = output / plan["inputs"][job["instance"]]["snapshot"]
        require(sha256(path) == plan["inputs"][job["instance"]]["sha256"], "input snapshot hash mismatch")
        try:
            result = json.loads((output / f"{job['run']}.json").read_text())
        except (OSError, ValueError) as exc:
            result = {"error": str(exc)}
        audited = audit_result(result, load_solomon_instance(str(path)), job, identity_for(plan, job))
        for key in ("certification_ok", "clock_ok", "provenance_ok", "budget_ok"):
            require((row[key] == "True") == audited[key], f"summary gate mismatch: {job['run']}/{key}")
        for key in ("runtime_sec", "nv", "td", "iterations"):
            require(
                row[key] == (str(result[key]) if result.get(key) is not None else ""), f"summary value mismatch: {key}"
            )
        command = json.loads((output / f"{job['run']}.command.json").read_text())
        require(command == command_for(output, plan, job), "recorded command mismatch")
        if result.get("requested_config"):
            directories.append(result["requested_config"]["output_dir"])
        completed = row["returncode"] == "0" and row["timed_out"] == "False"
        verified.append(
            {
                "run": job["run"],
                "instance": job["instance"],
                "seed": job["seed"],
                "ablation": job["ablation"],
                "runtime_sec": result.get("runtime_sec"),
                "captured_sec": ((result.get("native_certification") or {}).get("certificate") or {}).get(
                    "captured_sec"
                ),
                "process_ok": completed,
                **audited,
            }
        )
    require(len(directories) == len(set(directories)), "reused cold-start output directory")
    if status["status"] != "completed" or status["completed_jobs"] != len(rows) or len(rows) != len(plan["jobs"]):
        integrity_errors.append("pilot incomplete/aborted; unexecuted cells are not passing")
    passed = not integrity_errors and all(
        run["process_ok"] and all(run[key] for key in ("certification_ok", "clock_ok", "provenance_ok", "budget_ok"))
        for run in verified
    )
    require(status["all_gates_passed"] == passed, "status gate mismatch")
    audit = {
        "status": "passed" if passed else "failed",
        "source_sha256": plan["source_sha256"],
        "checkpoint_sha256": plan["checkpoint_sha256"],
        "verified_runs": verified,
        "integrity_errors": integrity_errors,
        "artifact_hashes": {
            str(path.relative_to(output)): sha256(path)
            for path in sorted(output.rglob("*"))
            if path.is_file() and path.name != "audit.json"
        },
        "audit_program_sha256": sha256(Path(__file__)),
        "limits": "Three inputs, two seeds, one cutoff; intermediate route hashes are not independently replayable routes; no hard deadline, before/after causal score comparison, tuning or generalization claim",
    }
    write_json(output / "audit.json", audit, "x")
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--gnn-model", type=Path)
    parser.add_argument("--order-seed", type=int, default=20261019)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if args.audit_only:
        require(not (output / "audit.json").exists(), "audit already exists; preserve the frozen record")
    else:
        if args.gnn_model is None:
            parser.error("--gnn-model is required for a new pilot")
        plan = prepare(output, args.gnn_model.resolve(), args.order_seed)
        execute(output, plan)
    audit = audit_directory(output)
    print(json.dumps({key: value for key, value in audit.items() if key != "artifact_hashes"}, indent=2), flush=True)
    return 0 if audit["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
