"""One declared eight-job supervisor pilot; no adaptive retries or promotion."""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import benchmark_supervised as cli
import run_factor_contract_pilot as factor
import run_kernel_timing_diagnostic as previous

from vrptw.gnn_training import sha256, snapshot, source_hash
from vrptw.native_certification import routes_sha256, validate_routes

native, require = factor.native, factor.native.require
OUTPUT = ROOT / "results/supervisor_pilot_20261020"
PROTOCOL = ROOT / "docs/supervisor_contract_20261020.md"
GATES = ("certification_ok", "clock_ok", "provenance_ok", "binding_ok", "cold_ok", "cleanup_ok", "budget_ok")


def jobs():
    selected = previous.select_jobs(previous.PREVIOUS)
    result = [
        {**j, "run": j["run"].removesuffix("__kernel_trace") + "__supervised", "phase_traced": False} for j in selected
    ]
    for inst, case in ((native.INSTANCES[0], "alns"), (native.INSTANCES[2], "F111111"), (native.INSTANCES[2], "alns")):
        result.append(
            {
                "run": f"{Path(inst).stem}__{case}__seed42__10s__supervised",
                "instance": inst,
                "ablation": case,
                "seed": 42,
                "time_limit": 10,
                "profiled": False,
                "phase_traced": False,
            }
        )
    require([Path(j["instance"]).stem for j in result[-3:]] == ["c101", "RC2_4_1", "RC2_4_1"], "instance order drift")
    return result


def freeze():
    output = OUTPUT
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
            10,
            seed=42,
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
    old = json.loads((previous.PREVIOUS / "plan.json").read_text())
    for job in schedule[:5]:
        require(configs[job["run"]] == old["configs"][job["source_run"]], "prior failed-cell config drift")
    snapshot(output / "source_snapshot.zip")
    with zipfile.ZipFile(output / "source_snapshot.zip", "a", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.glob("tests/**/*.py")):
            archive.write(path, path.relative_to(ROOT))
    runtime, archived = native.archived_sources(output)
    plan = {
        "schema_version": 1,
        "scope": "Native supervisor engineering pilot; no quality, ranking, hard-real-time or causal before/after claim",
        "jobs": schedule,
        "search_budget_sec": 80,
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
    native.write_json(output / "plan.json", plan, "x")
    return plan


def check(plan, digest):
    native.check_frozen(OUTPUT, plan)
    require(
        sha256(OUTPUT / "plan.json") == digest and json.loads((OUTPUT / "plan.json").read_text()) == plan, "plan drift"
    )
    require(sha256(OUTPUT / "launcher.py") == plan["launcher_sha256"] == sha256(Path(__file__)), "launcher drift")
    require(sha256(OUTPUT / "protocol_before_execution.md") == plan["protocol_sha256"], "protocol drift")


def audit(job, plan, raw):
    session = OUTPUT / job["run"] / "session"
    inst = factor.load_job_instance(OUTPUT, plan, job)
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
            raw["execution_mode"] == "native_supervisor_v1" and raw["metadata"]["hard_return_deadline"] is False,
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
        require(actual["seed"] == 42 and actual["case"] == job["ablation"] and request["time_limit"] == 10, "job drift")
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
            and abs(start["deadline_perf"] - start["start_perf"] - 10) < 1e-8,
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
            validate_routes(raw["routes"], inst) == raw["td"] == cert["td"]
            and len(raw["routes"]) == raw["nv"] == cert["nv"]
            and routes_sha256(raw["routes"]) == cert["routes_sha256"],
            "returned original-space route/certificate failure",
        )
        require(
            0 <= cert["worker_captured_sec"] <= cert["receipt_sec"] <= cert["captured_sec"] < 10,
            "late selected certificate",
        )
        receipts = {r["sequence"]: r for r in raw["receipts"]}
        previous_pair, last = None, None
        admitted = []
        for observed in raw["packet_observations"]:
            path = session / observed["file"]
            require(sha256(path) == observed["sha256"], "observed packet drift")
            if not observed["admitted"]:
                continue
            packet = json.loads(path.read_text())
            worker_cert = packet["certificate"]
            receipt = receipts[packet["sequence"]]
            require(
                receipt["admitted"]
                and packet["token"] == start["token"]
                and packet["start_perf"] == start["start_perf"]
                and packet["deadline_perf"] == start["deadline_perf"],
                "admission identity drift",
            )
            cost = validate_routes(packet["routes"], inst)
            require(
                cost == worker_cert["td"]
                and routes_sha256(packet["routes"]) == worker_cert["routes_sha256"]
                and len(packet["routes"]) == worker_cert["nv"],
                "admitted packet route failure",
            )
            require(
                0 <= worker_cert["captured_sec"] <= receipt["receipt_sec"] <= receipt["validated_sec"] < 10
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

    gate("provenance_ok", provenance)
    gate("binding_ok", binding)
    gate("cold_ok", cold)
    gate("clock_ok", clock)
    gate("certification_ok", certification)
    gate(
        "cleanup_ok", lambda: require(raw["worker_reaped"] and raw["worker_returncode"] is not None, "unreaped worker")
    )
    gate("budget_ok", lambda: require(9.95 <= raw["runtime_sec"] <= 10.5, "return outside unchanged gate"))
    return verdict, errors


def main():
    plan = freeze()
    digest = sha256(OUTPUT / "plan.json")
    rows, verified = [], []
    state = {"status": "running", "completed_jobs": 0, "plan_sha256": digest}
    native.write_json(OUTPUT / "status.json", state)
    try:
        for job in plan["jobs"]:
            check(plan, digest)
            directory = OUTPUT / job["run"]
            directory.mkdir()
            command = [
                sys.executable,
                str(ROOT / "scripts/benchmark_supervised.py"),
                "--instance",
                str(OUTPUT / plan["inputs"][job["instance"]]["snapshot"]),
                "--ablation",
                job["ablation"],
                "--seed",
                "42",
                "--time-limit",
                "10",
                "--session-dir",
                str(directory / "session"),
                "--output-json",
                str(directory / "result.json"),
            ]
            if job["ablation"].startswith("F") and job["ablation"][-1] == "1":
                command.extend(["--gnn-model", str(OUTPUT / "gnn_checkpoint.pt")])
            native.write_json(directory / "command.json", command, "x")
            beginning, cpu = time.perf_counter(), factor.child_cpu()
            with (directory / "stdout.log").open("x") as stdout, (directory / "stderr.log").open("x") as stderr:
                completed = subprocess.run(
                    command,
                    cwd=ROOT,
                    env={**os.environ, **dict.fromkeys(native.THREADS, "1")},
                    stdout=stdout,
                    stderr=stderr,
                    timeout=190,
                    check=False,
                )
            wall, after_cpu = time.perf_counter() - beginning, factor.child_cpu()
            raw = json.loads((directory / "result.json").read_text())
            verdict, errors = audit(job, plan, raw)
            cert = (raw.get("native_certification") or {}).get("certificate") or {}
            row = {
                "run": job["run"],
                "instance": job["instance"],
                "ablation": job["ablation"],
                "seed": 42,
                "time_limit": 10,
                "returncode": completed.returncode,
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
                **verdict,
                "errors": json.dumps(errors),
            }
            rows.append(row)
            verified.append(
                {"run": job["run"], "result_sha256": sha256(directory / "result.json"), **verdict, "errors": errors}
            )
            with (OUTPUT / "summary.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(row))
                writer.writeheader()
                writer.writerows(rows)
            state["completed_jobs"] = len(rows)
            native.write_json(OUTPUT / "status.json", state)
            print(json.dumps(row), flush=True)
            check(plan, digest)
            require(
                all(verdict[k] for k in ("provenance_ok", "cold_ok", "clock_ok", "cleanup_ok"))
                and (verdict["binding_ok"] or raw.get("worker_checkpoint") is None)
                and not raw.get("error", "").startswith("SupervisorProtocolError:"),
                "protocol integrity gate failed",
            )
        state["status"] = "completed"
    except Exception as exc:
        state.update(status="aborted", reason=f"{type(exc).__name__}: {exc}")
    native.write_json(OUTPUT / "status.json", state)
    check(plan, digest)
    reopened = []
    for job in plan["jobs"][: state["completed_jobs"]]:
        raw = json.loads((OUTPUT / job["run"] / "result.json").read_text())
        verdict, errors = audit(job, plan, raw)
        reopened.append({"run": job["run"], **verdict, "errors": errors})
    require(
        all({k: a[k] for k in (*GATES, "run", "errors")} == b for a, b in zip(verified, reopened, strict=True)),
        "reopened audit drift",
    )
    require(
        (list(csv.DictReader((OUTPUT / "summary.csv").open())) if rows else [])
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
    native.write_json(OUTPUT / "audit.json", audit_result, "x")
    native.write_json(
        OUTPUT / "artifact_hashes.json",
        {str(p.relative_to(OUTPUT)): sha256(p) for p in sorted(OUTPUT.rglob("*")) if p.is_file()},
        "x",
    )
    print(
        json.dumps({"status": state["status"], "audit_status": audit_result["status"], "completed_jobs": len(rows)}),
        flush=True,
    )
    return 0 if audit_result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
