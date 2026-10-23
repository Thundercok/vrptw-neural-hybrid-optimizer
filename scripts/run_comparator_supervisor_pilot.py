"""Prespecified common-supervisor preflight; sixteen jobs, no publication sweep."""

from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import sys
import time
import zipfile
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import benchmark_supervised as cli
import run_supervisor_pilot as shared

from vrptw.gnn_training import sha256, snapshot, source_hash
from vrptw.supervisor import check_descendant_cleanup

native, factor, require = shared.native, shared.factor, shared.require
GATES = shared.GATES
activity, run_child = shared.activity, shared.run_child
ASSETS = (ROOT / "results/external/NeuroLKH").resolve()
PROTOCOL = ROOT / "docs/comparator_supervisor_20261020.md"
CASES = ("alns", "F111111", "pyvrp", "neurolkh")


def jobs():
    blocks = [(i, 42, 10) for i in native.INSTANCES] + [(native.INSTANCES[2], 43, 60)]
    random.Random(20261020).shuffle(blocks)
    return [
        {
            "run": f"{Path(inst).stem}__{case}__seed{seed}__{budget}s__common",
            "instance": inst,
            "ablation": case,
            "seed": seed,
            "time_limit": budget,
            "profiled": False,
            "phase_traced": False,
            "block": block,
            "position": position,
        }
        for block, (inst, seed, budget) in enumerate(blocks)
        for position, case in enumerate(CASES[block:] + CASES[:block])
    ]


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
        dest = output / "inputs" / Path(name).name
        shutil.copy2(ROOT / name, dest)
        inputs[name] = {"snapshot": str(dest.relative_to(output)), "sha256": sha256(dest)}
    schedule, configs, backends = jobs(), {}, {}
    for job in schedule:
        _, cfg = cli.native_cli.get_solver_and_config(
            job["ablation"],
            job["time_limit"],
            seed=job["seed"],
            gnn_model=output / "gnn_checkpoint.pt" if job["ablation"] == "F111111" else None,
        )
        if job["ablation"] == "neurolkh":
            cfg.neurolkh_root = str(ASSETS)
        if job["ablation"] in ("pyvrp", "neurolkh"):
            current = cli.backend_identity(job["ablation"], cfg)
            require(backends.get(job["ablation"], current) == current, "backend changed during freeze")
            backends[job["ablation"]] = current
        instance = factor.load_job_instance(output, {"inputs": inputs}, job)
        config = native.config_signature(asdict(cfg))
        configs[job["run"]] = (
            factor.declared_configs(cfg, instance)
            if job["ablation"] == "F111111"
            else {"requested_config": config, "effective_config": config, "module_configs": {}}
        )
    snapshot(output / "source_snapshot.zip")
    with zipfile.ZipFile(output / "source_snapshot.zip", "a", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.glob("tests/**/*.py")):
            archive.write(path, path.relative_to(ROOT))
    runtime, archived = native.archived_sources(output)
    plan = {
        "schema_version": 1,
        "scope": "Common-supervisor engineering preflight; no ranking, significance or generalization claim",
        "jobs": schedule,
        "search_budget_sec": sum(j["time_limit"] for j in schedule),
        "order_seed": 20261020,
        "return_gate_sec": {"lower_slack": 0.05, "upper_slack": 0.5},
        "inputs": inputs,
        "configs": configs,
        "backends": backends,
        "source_sha256": source_hash(),
        "source_files": runtime,
        "snapshot_files": archived,
        "source_snapshot_sha256": sha256(output / "source_snapshot.zip"),
        "checkpoint_sha256": sha256(output / "gnn_checkpoint.pt"),
        "training_metadata_sha256": sha256(output / "training_metadata.json"),
        "launcher_sha256": sha256(output / "launcher.py"),
        "protocol_sha256": sha256(output / "protocol_before_execution.md"),
        "failure_policy": "Keep ordinary no-incumbent/return failures; abort identity/config/clock/cleanup drift; no retry",
        "cache_policy": "Fresh process and empty exclusive cwd/cache, JIT on, hash seed42, one-thread requests, no warmup",
    }
    plan["commands"] = {j["run"]: command(output, plan, j) for j in schedule}
    native.write_json(output / "plan.json", plan, "x")
    return plan


def command(output, plan, job):
    argv = shared.command(output, plan, job)
    if job["ablation"] == "neurolkh":
        argv.extend(["--neurolkh-root", str(ASSETS)])
    return argv


def check(output, plan, digest):
    native.check_frozen(output, plan)
    require(
        sha256(output / "plan.json") == digest and json.loads((output / "plan.json").read_text()) == plan, "plan drift"
    )
    require(sha256(output / "launcher.py") == plan["launcher_sha256"] == sha256(Path(__file__)), "launcher drift")
    require(sha256(output / "protocol_before_execution.md") == plan["protocol_sha256"], "protocol drift")
    for case in ("pyvrp", "neurolkh"):
        _, cfg = cli.native_cli.get_solver_and_config(case, 10)
        if case == "neurolkh":
            cfg.neurolkh_root = str(ASSETS)
        require(cli.backend_identity(case, cfg) == plan["backends"][case], "external assets drift")


def audit(output, job, plan, raw):
    external = job["ablation"] in ("pyvrp", "neurolkh")
    verdict, errors = shared.audit(
        output, job, plan, raw, execution_mode="external_supervisor_v1" if external else "native_supervisor_v1"
    )
    if not external:
        return verdict, errors
    case = job["ablation"]
    session = output / job["run"] / "session"
    request = json.loads((session / "request.json").read_text())
    try:
        require(
            request["identity"]["backend_identity"] == raw["metadata"]["backend_identity"] == plan["backends"][case],
            "backend binding drift",
        )
    except Exception as exc:
        verdict["provenance_ok"] = False
        errors.append(f"provenance_ok: {type(exc).__name__}: {exc}")
    try:
        checkpoint = raw["worker_checkpoint"]
        require(checkpoint is not None, "no external checkpoint")
        diag = checkpoint["adapter_diagnostics"]
        require(
            diag["seed"] == job["seed"] and diag["requested_budget_sec"] == job["time_limit"],
            "adapter budget/seed drift",
        )
        require(diag["distance_scale"] == 100000, "adapter precision drift")
        components = checkpoint["instrumentation"]["resolved_components"]
        require(
            all(not value for key, value in components.items() if key != "external_learned_candidates"),
            "external enabled native machinery",
        )
        require(components["external_learned_candidates"] == (case == "neurolkh"), "external learned binding drift")
        if case == "pyvrp":
            require(
                diag["pyvrp_version"] == plan["backends"][case]["version"]
                and diag["parameters"]["initial_solution"] is None,
                "PyVRP parameters/version drift",
            )
            require(checkpoint["iterations"] == diag.get("ils_iterations"), "invented PyVRP checkpoint iteration count")
        else:
            require(
                diag["model_device"] == "cpu" and diag["model_training"] is False and checkpoint["iterations"] is None,
                "NeuroLKH model/counter scope drift",
            )
    except Exception as exc:
        verdict["binding_ok"] = False
        errors.append(f"binding_ok: {type(exc).__name__}: {exc}")
    if case == "neurolkh":
        try:
            closure = check_descendant_cleanup(session, request, raw["worker_pid"])
            require(
                raw["descendants_reaped"] is True and closure == raw["descendant_cleanup"], "descendant cleanup drift"
            )
            require(closure["closed_perf"] <= raw["cleanup_end_perf"], "descendant cleanup chronology drift")
        except Exception as exc:
            verdict["cleanup_ok"] = False
            errors.append(f"cleanup_ok: {type(exc).__name__}: {exc}")
    return verdict, errors


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
