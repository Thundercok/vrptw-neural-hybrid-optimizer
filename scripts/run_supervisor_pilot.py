"""Declared fourteen-job native supervisor preflight; no adaptive retries or promotion."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import shutil
import signal
import subprocess
import sys
import time
import zipfile
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import benchmark_supervised as cli
import run_factor_contract_pilot as factor

from vrptw.gnn_training import sha256, snapshot, source_hash
from vrptw.native_certification import routes_sha256, validate_routes

native, require = factor.native, factor.native.require
PROTOCOL = ROOT / "docs/supervisor_long_pilot_20261020.md"
GATES = ("certification_ok", "clock_ok", "provenance_ok", "binding_ok", "cold_ok", "cleanup_ok", "budget_ok")


def jobs():
    blocks = [(inst, seed, 60) for inst in native.INSTANCES for seed in (42, 43)]
    blocks.append((native.INSTANCES[2], 43, 300))
    random.Random(20261020).shuffle(blocks)
    result = []
    for block, (instance, seed, budget) in enumerate(blocks):
        cases = ("alns", "F111111") if block % 2 == 0 else ("F111111", "alns")
        for position, case in enumerate(cases):
            result.append(
                {
                    "run": f"{Path(instance).stem}__{case}__seed{seed}__{budget}s__supervised",
                    "instance": instance,
                    "ablation": case,
                    "seed": seed,
                    "time_limit": budget,
                    "profiled": False,
                    "phase_traced": False,
                    "block": block,
                    "position": position,
                }
            )
    return result


def freeze(output):
    output.mkdir(exist_ok=False)
    shutil.copy2(__file__, output / "launcher.py")
    shutil.copy2(PROTOCOL, output / "protocol_before_execution.md")
    model = ROOT / "results/gnn_retraining_20261017/model_seed42/best.pt"
    training = json.loads((model.parent / "training.json").read_text())
    require(
        training["status"] == "completed"
        and not training["smoke_only"]
        and sha256(model) == training["checkpoint_sha256"] == factor.GNN_SHA256,
        "training/checkpoint drift",
    )
    shutil.copy2(model, output / "gnn_checkpoint.pt")
    shutil.copy2(model.parent / "training.json", output / "training_metadata.json")
    (output / "inputs").mkdir()
    inputs = {}
    for name in native.INSTANCES:
        path = output / "inputs" / Path(name).name
        shutil.copy2(ROOT / name, path)
        inputs[name] = {"snapshot": str(path.relative_to(output)), "sha256": sha256(path)}
    schedule, configs = jobs(), {}
    for job in schedule:
        _, cfg = cli.native_cli.get_solver_and_config(
            job["ablation"],
            job["time_limit"],
            seed=job["seed"],
            gnn_model=output / "gnn_checkpoint.pt"
            if job["ablation"].startswith("F") and job["ablation"][-1] == "1"
            else None,
        )
        inst = factor.load_job_instance(output, {"inputs": inputs}, job)
        configs[job["run"]] = (
            factor.declared_configs(cfg, inst)
            if job["ablation"].startswith("F")
            else {
                "requested_config": native.config_signature(asdict(cfg)),
                "effective_config": native.config_signature(asdict(cfg)),
                "module_configs": {},
            }
        )
    snapshot(output / "source_snapshot.zip")
    with zipfile.ZipFile(output / "source_snapshot.zip", "a", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.glob("tests/**/*.py")):
            archive.write(path, path.relative_to(ROOT))
    runtime, archived = native.archived_sources(output)
    plan = {
        "schema_version": 1,
        "scope": "Native supervisor engineering pilot; no quality, ranking, hard-real-time or causal before/after claim",
        "jobs": schedule,
        "search_budget_sec": sum(j["time_limit"] for j in schedule),
        "return_gate_sec": {"lower_slack": 0.05, "upper_slack": 0.5},
        "order_seed": 20261020,
        "cache_policy": "Fresh process, initially empty exclusive work/cache, JIT on, no warmup",
        "hash_seed": 42,
        "source_sha256": source_hash(),
        "source_files": runtime,
        "snapshot_files": archived,
        "inputs": inputs,
        "configs": configs,
        "source_snapshot_sha256": sha256(output / "source_snapshot.zip"),
        "checkpoint_sha256": sha256(output / "gnn_checkpoint.pt"),
        "training_metadata_sha256": sha256(output / "training_metadata.json"),
        "launcher_sha256": sha256(output / "launcher.py"),
        "protocol_sha256": sha256(output / "protocol_before_execution.md"),
        "failure_policy": "Retain certification/return failures; abort on protocol identity drift; no retry",
    }
    plan["commands"] = {job["run"]: command(output, plan, job) for job in schedule}
    native.write_json(output / "plan.json", plan, "x")
    return plan


def check(output, plan, digest):
    native.check_frozen(output, plan)
    require(
        sha256(output / "plan.json") == digest and json.loads((output / "plan.json").read_text()) == plan, "plan drift"
    )
    require(sha256(output / "launcher.py") == plan["launcher_sha256"] == sha256(Path(__file__)), "launcher drift")
    require(sha256(output / "protocol_before_execution.md") == plan["protocol_sha256"], "protocol drift")


def audit(output, job, plan, raw, *, execution_mode="native_supervisor_v1"):
    session = output / job["run"] / "session"
    inst = factor.load_job_instance(output, plan, job)
    request = json.loads((session / "request.json").read_text())
    ready = json.loads((session / "ready.json").read_text()) if (session / "ready.json").exists() else {}
    start = json.loads((session / "start.json").read_text()) if (session / "start.json").exists() else {}
    ack = json.loads((session / "ack.json").read_text()) if (session / "ack.json").exists() else {}
    actual, expected = request["identity"], plan["configs"][job["run"]]
    verdict, errors = {}, []

    def gate(key, function):
        try:
            function()
            verdict[key] = True
        except Exception as exc:
            verdict[key] = False
            errors.append(f"{key}: {type(exc).__name__}: {exc}")

    def provenance():
        require(
            raw["execution_mode"] == execution_mode and raw["metadata"]["hard_return_deadline"] is False,
            "execution scope drift",
        )
        require(
            actual == ready["identity"]
            and actual["source_sha256"]
            == raw["environment"]["source_sha256"]
            == ready["environment"]["source_sha256"]
            == plan["source_sha256"],
            "source identity drift",
        )
        require(actual["instance_sha256"] == plan["inputs"][job["instance"]]["sha256"], "input identity drift")
        require(all(raw["metadata"][key] == value for key, value in actual.items()), "metadata identity drift")
        require(
            actual["seed"] == job["seed"]
            and actual["case"] == raw["requested_ablation"] == job["ablation"]
            and request["time_limit"] == raw["metadata"]["time_limit"] == job["time_limit"]
            and raw["metadata"]["seed"] == job["seed"],
            "job drift",
        )
        require(
            actual["gnn_model_sha256"]
            == (plan["checkpoint_sha256"] if job["ablation"].startswith("F") and job["ablation"][-1] == "1" else None),
            "model identity drift",
        )

    def binding():
        require(
            native.config_signature(raw["requested_config"])
            == native.config_signature(actual["requested_config"])
            == expected["requested_config"],
            "requested config drift",
        )
        checkpoint = raw["worker_checkpoint"]
        require(checkpoint is not None, "no delivered checkpoint; effective binding evidence unavailable")
        require(
            native.config_signature(checkpoint["effective_config"]) == expected["effective_config"],
            "checkpoint effective config drift",
        )
        require(
            {k: native.config_signature(v) for k, v in checkpoint["instrumentation"]["module_configs"].items()}
            == expected["module_configs"],
            "checkpoint nested config drift",
        )
        if job["ablation"].startswith("F"):
            bits = factor.factor_levels(job["ablation"])
            components = checkpoint["instrumentation"]["resolved_components"]
            require(
                [components[k] for k in ("gec", "route_pool", "macro_ddqn", "micro_ddqn", "lac", "gnn_edge_guidance")]
                == list(bits),
                "factor binding drift",
            )
        if raw["worker_completion"] is None:
            require(
                raw["iterations"]
                is raw["instrumentation"]
                is raw["effective_config"]
                is raw["final_worker_counters"]
                is None,
                "fabricated final counters",
            )

    def cold():
        entry = ready["environment"]["process_entry"]
        require(
            entry
            == {
                "cwd": str(session / "work"),
                "cwd_entries": [],
                "cache_dir": str(session / "cache"),
                "cache_entries": [],
            },
            "worker entry drift",
        )
        require(ready["cold_start_evidence"] == cli.COLD, "loaded archive/controller state")
        require(
            ready["environment"]["numba"]["disable_jit"] is False
            and ready["environment"]["numba"]["cache_dir"] == str(session / "cache"),
            "effective JIT drift",
        )
        require(
            ready["environment"]["torch_threads"] == 1
            and all(v == "1" for v in ready["environment"]["thread_environment"].values()),
            "thread request drift",
        )
        require(
            ready["jit_environment"]
            == {"NUMBA_DISABLE_JIT": "0", "NUMBA_CACHE_DIR": str(session / "cache"), "PYTHONHASHSEED": "42"},
            "JIT/hash environment drift",
        )

    def clock():
        require(start == {k: ack[k] for k in start} and start["token"] == request["token"], "start/ack drift")
        require(
            start["start_perf"] == raw["solve_start_perf"]
            and start["deadline_perf"] == raw["solve_deadline_perf"]
            and abs(start["deadline_perf"] - start["start_perf"] - job["time_limit"]) < 1e-8,
            "cutoff clock drift",
        )
        require(
            start["start_perf"]
            <= ack["worker_received_perf"]
            <= raw["cleanup_start_perf"]
            <= raw["cleanup_end_perf"]
            <= start["start_perf"] + raw["runtime_sec"],
            "cleanup/ack clock drift",
        )

    def certification():
        require(raw["feasible"] and "error" not in raw, "no successful parent incumbent")
        cert = raw["native_certification"]["certificate"]
        require(
            raw["native_certification"]["clock"] == cert["clock"] == "perf_counter"
            and raw["native_certification"]["cutoff_sec"] == cert["cutoff_sec"] == job["time_limit"],
            "selected certificate clock drift",
        )
        independent_nv, independent_td = native.independent_routes(raw["routes"], inst)
        require(
            independent_nv == raw["nv"] and math.isclose(independent_td, raw["td"], rel_tol=1e-12, abs_tol=1e-6),
            "independent coordinate/objective failure",
        )
        require(
            validate_routes(raw["routes"], inst) == raw["td"] == cert["td"]
            and len(raw["routes"]) == raw["nv"] == cert["nv"]
            and routes_sha256(raw["routes"]) == cert["routes_sha256"],
            "returned original-space route/certificate failure",
        )
        require(
            0 <= cert["worker_captured_sec"] <= cert["receipt_sec"] <= cert["captured_sec"] < job["time_limit"],
            "late selected certificate",
        )
        receipts = {r["sequence"]: r for r in raw["receipts"]}
        previous_pair, last = None, None
        admitted, admitted_points = [], []
        for observed in raw["packet_observations"]:
            path = session / observed["file"]
            require(sha256(path) == observed["sha256"], "observed packet drift")
            if not observed["admitted"]:
                continue
            packet = json.loads(path.read_text())
            worker_cert = packet["certificate"]
            require(
                worker_cert["clock"] == "perf_counter" and worker_cert["cutoff_sec"] == job["time_limit"],
                "packet certificate clock drift",
            )
            receipt = receipts[packet["sequence"]]
            require(
                receipt["admitted"]
                and packet["token"] == start["token"]
                and packet["start_perf"] == start["start_perf"]
                and packet["deadline_perf"] == start["deadline_perf"],
                "admission identity drift",
            )
            cost = validate_routes(packet["routes"], inst)
            independent_nv, independent_td = native.independent_routes(packet["routes"], inst)
            require(
                cost == worker_cert["td"]
                and routes_sha256(packet["routes"]) == worker_cert["routes_sha256"]
                and len(packet["routes"]) == worker_cert["nv"] == independent_nv
                and math.isclose(independent_td, cost, rel_tol=1e-12, abs_tol=1e-6),
                "admitted packet route failure",
            )
            require(
                0
                <= worker_cert["captured_sec"]
                <= receipt["receipt_sec"]
                <= receipt["validated_sec"]
                < job["time_limit"]
                and start["start_perf"] + worker_cert["captured_sec"] >= ack["worker_received_perf"],
                "admission chronology drift",
            )
            pair = len(packet["routes"]), cost
            require(
                previous_pair is None
                or pair[0] < previous_pair[0]
                or (pair[0] == previous_pair[0] and pair[1] < previous_pair[1] - 1e-6),
                "nonlexicographic admission",
            )
            previous_pair, last = pair, (packet, receipt)
            admitted.append(receipt)
            admitted_points.append(
                {
                    "t_sec": receipt["validated_sec"],
                    "nv": worker_cert["nv"],
                    "td": worker_cert["td"],
                    "phase": worker_cert["phase"],
                    "iter": worker_cert["iter"],
                    "routes_sha256": worker_cert["routes_sha256"],
                }
            )
        require(
            last is not None
            and last[0]["routes"] == raw["routes"]
            and last[1]["validated_sec"] == cert["captured_sec"]
            and last[0]["certificate"]["captured_sec"] == cert["worker_captured_sec"]
            and last[1]["receipt_sec"] == cert["receipt_sec"],
            "selected incumbent was not delivered/admitted",
        )
        require(
            len(admitted) == len(raw["trajectory"])
            and all(a["validated_sec"] == t["t_sec"] for a, t in zip(admitted, raw["trajectory"], strict=True)),
            "trajectory admission drift",
        )
        require(admitted_points == raw["trajectory"], "trajectory objective/context drift")

    gate("provenance_ok", provenance)
    gate("binding_ok", binding)
    gate("cold_ok", cold)
    gate("clock_ok", clock)
    gate("certification_ok", certification)
    gate(
        "cleanup_ok", lambda: require(raw["worker_reaped"] and raw["worker_returncode"] is not None, "unreaped worker")
    )
    gate(
        "budget_ok",
        lambda: require(
            native.finite(raw["runtime_sec"])
            and job["time_limit"] - 0.05 <= raw["runtime_sec"] <= job["time_limit"] + 0.5,
            "return outside unchanged gate",
        ),
    )
    return verdict, errors


def command(output, plan, job):
    directory = output / job["run"]
    argv = [
        sys.executable,
        str(ROOT / "scripts/benchmark_supervised.py"),
        "--instance",
        str(output / plan["inputs"][job["instance"]]["snapshot"]),
        "--ablation",
        job["ablation"],
        "--seed",
        str(job["seed"]),
        "--time-limit",
        str(job["time_limit"]),
        "--session-dir",
        str(directory / "session"),
        "--output-json",
        str(directory / "result.json"),
    ]
    if job["ablation"].startswith("F") and job["ablation"][-1] == "1":
        argv.extend(["--gnn-model", str(output / "gnn_checkpoint.pt")])
    return argv


def activity(raw):
    """Label checkpoint observations separately from complete worker counters."""
    fields = (
        "macro_training_calls",
        "micro_training_calls",
        "macro_decisions",
        "micro_decisions",
        "lac_queries",
        "lac_acceptances",
        "highs_calls",
        "highs_timeouts",
    )
    row = {}
    for scope, key in (("checkpoint", "worker_checkpoint"), ("final", "final_worker_counters")):
        counters = raw.get(key) or {}
        row[f"{scope}_iterations"] = counters.get("iterations")
        instrumentation = counters.get("instrumentation") or {}
        for field in fields:
            row[f"{scope}_{field}"] = instrumentation.get(field)
    return row


def run_child(argv, *, directory, budget):
    """On watchdog expiry, let the owned supervisor execute its cleanup finally."""
    info = {"watchdog_fired": False, "watchdog_sec": budget + 180, "returncode": None}
    with (directory / "stdout.log").open("x") as stdout, (directory / "stderr.log").open("x") as stderr:
        process = subprocess.Popen(
            argv,
            cwd=ROOT,
            env={**os.environ, **dict.fromkeys(native.THREADS, "1")},
            stdout=stdout,
            stderr=stderr,
        )
        info["pid"] = process.pid
        native.write_json(directory / "cli_process.json", info, "x")
        try:
            info["returncode"] = process.wait(timeout=budget + 180)
        except subprocess.TimeoutExpired:
            info["watchdog_fired"] = True
            process.send_signal(signal.SIGINT)
            try:
                info["returncode"] = process.wait(timeout=10)
            finally:
                native.write_json(directory / "cli_process.json", info)
            raise
        except KeyboardInterrupt:
            process.send_signal(signal.SIGINT)
            try:
                info["returncode"] = process.wait(timeout=10)
            finally:
                native.write_json(directory / "cli_process.json", info)
            raise
    native.write_json(directory / "cli_process.json", info)
    return info["returncode"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    plan = freeze(output)
    digest = sha256(output / "plan.json")
    rows, verified = [], []
    state = {"status": "running", "completed_jobs": 0, "plan_sha256": digest}
    native.write_json(output / "status.json", state)
    try:
        for job in plan["jobs"]:
            check(output, plan, digest)
            directory = output / job["run"]
            directory.mkdir()
            argv = plan["commands"][job["run"]]
            native.write_json(directory / "command.json", argv, "x")
            beginning, cpu = time.perf_counter(), factor.child_cpu()
            returncode = run_child(argv, directory=directory, budget=job["time_limit"])
            wall, after_cpu = time.perf_counter() - beginning, factor.child_cpu()
            raw = json.loads((directory / "result.json").read_text())
            verdict, errors = audit(output, job, plan, raw)
            cert = (raw.get("native_certification") or {}).get("certificate") or {}
            row = {
                "run": job["run"],
                "instance": job["instance"],
                "ablation": job["ablation"],
                "seed": job["seed"],
                "time_limit": job["time_limit"],
                "returncode": returncode,
                "feasible": raw["feasible"],
                "nv": raw["nv"],
                "td": raw["td"],
                "runtime_sec": raw["runtime_sec"],
                "captured_sec": cert.get("captured_sec"),
                "worker_captured_sec": cert.get("worker_captured_sec"),
                "cleanup_sec": raw["cleanup_end_perf"] - raw["cleanup_start_perf"]
                if "cleanup_end_perf" in raw
                else None,
                "child_wall_sec": wall,
                "child_cpu_sec": after_cpu - cpu,
                "final_counters_available": raw["final_worker_counters"] is not None,
                **activity(raw),
                **verdict,
                "errors": json.dumps(errors),
            }
            rows.append(row)
            verified.append(
                {"run": job["run"], "result_sha256": sha256(directory / "result.json"), **verdict, "errors": errors}
            )
            with (output / "summary.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(row))
                writer.writeheader()
                writer.writerows(rows)
            state["completed_jobs"] = len(rows)
            native.write_json(output / "status.json", state)
            print(json.dumps(row), flush=True)
            check(output, plan, digest)
            require(
                all(verdict[k] for k in ("provenance_ok", "cold_ok", "clock_ok", "cleanup_ok"))
                and (verdict["binding_ok"] or raw.get("worker_checkpoint") is None)
                and not raw.get("error", "").startswith("SupervisorProtocolError:"),
                "protocol integrity gate failed",
            )
        state["status"] = "completed"
    except Exception as exc:
        state.update(status="aborted", reason=f"{type(exc).__name__}: {exc}")
    native.write_json(output / "status.json", state)
    check(output, plan, digest)
    reopened = []
    for job in plan["jobs"][: state["completed_jobs"]]:
        raw = json.loads((output / job["run"] / "result.json").read_text())
        verdict, errors = audit(output, job, plan, raw)
        reopened.append({"run": job["run"], **verdict, "errors": errors})
    require(
        all({k: a[k] for k in (*GATES, "run", "errors")} == b for a, b in zip(verified, reopened, strict=True)),
        "reopened audit drift",
    )
    require(
        (list(csv.DictReader((output / "summary.csv").open())) if rows else [])
        == [{k: "" if v is None else str(v) for k, v in row.items()} for row in rows],
        "CSV drift",
    )
    audit_result = {
        "status": "passed"
        if state["status"] == "completed" and all(row[k] for row in rows for k in GATES)
        else "failed",
        "complete": state["status"] == "completed",
        "source_sha256": plan["source_sha256"],
        "verified_runs": verified,
        "limits": plan["scope"],
    }
    native.write_json(output / "audit.json", audit_result, "x")
    native.write_json(
        output / "artifact_hashes.json",
        {str(p.relative_to(output)): sha256(p) for p in sorted(output.rglob("*")) if p.is_file()},
        "x",
    )
    print(
        json.dumps({"status": state["status"], "audit_status": audit_result["status"], "completed_jobs": len(rows)}),
        flush=True,
    )
    return 0 if audit_result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
