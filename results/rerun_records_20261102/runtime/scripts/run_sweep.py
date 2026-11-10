"""Frozen sequential sweep execution; preparation never starts a solver."""

from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import os
import platform
import resource
import shutil
import signal
import subprocess
import sys
import time
import uuid
import zipfile
from contextlib import contextmanager
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import benchmark_supervised as cli
import run_comparator_supervisor_pilot as common

from vrptw.gnn_training import fingerprints, sha256, snapshot, source_hash
from vrptw.sweep_statistics import finite

DESIGN = ROOT / "results/ablation_design_20261019"
PROTOCOL = ROOT / "docs/sweep_execution_20261020.md"
ALIASES = {"ALNS-Base": "alns", "PyVRP-ILS": "pyvrp", "NeuroLKH-adapted": "neurolkh"}
ALGORITHM_ERRORS = {"NativeNoSolutionError", "PyVRPNoSolutionError", "NeuroLKHNoSolutionError"}
require = common.require


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def read(path):
    try:
        return json.loads(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise ValueError(f"incomplete or invalid evidence: {path}") from exc


def publish(path, value, *, replace=False):
    data = encode(value)
    if path.exists() and not replace:
        require(path.read_bytes() == data, f"immutable artifact differs: {path.name}")
        return
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".pending")
    with temp.open("xb") as stream:
        stream.write(data)
    os.replace(temp, path)


def hardware():
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        "executable": sys.executable,
        "packages": {p: version(p) for p in ("numpy", "scipy", "torch", "numba", "ortools", "pyvrp")},
    }


def prepare(output):
    output = output.resolve()
    output.mkdir(exist_ok=False)
    historical = read(DESIGN / "artifact_hashes.json")
    require(all(sha256(DESIGN / n) == h for n, h in historical.items()), "historical design drift")
    design = read(DESIGN / "design.json")
    old_jobs = [json.loads(line) for line in (DESIGN / "jobs.jsonl").read_text().splitlines()]
    inputs_list = read(DESIGN / "input_identity.json")
    require(len(old_jobs) == 8620 and len(inputs_list) == 74, "wrong registered design")
    require(sum(j["cutoff_sec"] for j in old_jobs) == 2365600, "registered compute drift")
    (output / "design").mkdir()
    for name in historical:
        shutil.copy2(DESIGN / name, output / "design" / name)
    shutil.copy2(DESIGN / "artifact_hashes.json", output / "design/artifact_hashes.json")
    shutil.copy2(PROTOCOL, output / "protocol_before_execution.md")
    shutil.copy2(__file__, output / "launcher.py")
    model = ROOT / "results/gnn_retraining_20261017/model_seed42/best.pt"
    training = read(model.parent / "training.json")
    require(
        training["status"] == "completed"
        and not training["smoke_only"]
        and sha256(model) == training["checkpoint_sha256"] == common.factor.GNN_SHA256,
        "frozen native model drift",
    )
    shutil.copy2(model, output / "gnn_checkpoint.pt")
    shutil.copy2(model.parent / "training.json", output / "training_metadata.json")
    (output / "inputs").mkdir()
    (output / "bindings").mkdir()
    inputs = {}
    instances = {}
    metadata = {}
    for entry in inputs_list:
        path = ROOT / entry["path"]
        require(sha256(path) == entry["sha256"], "input drift")
        instance = common.factor.native.load_solomon_instance(str(path))
        require(
            instance.n == entry["customers"] and fingerprints(instance)["geometry_sha256"] == entry["geometry_sha256"],
            "actual input geometry/size differs",
        )
        dest = output / "inputs" / path.name
        require(not dest.exists(), "input basename collision")
        shutil.copy2(path, dest)
        inputs[entry["path"]] = {"snapshot": str(dest.relative_to(output)), "sha256": entry["sha256"]}
        instances[entry["name"]] = (entry, instance)
        metadata[entry["name"]] = {"customers": entry["customers"], "geometry_sha256": entry["geometry_sha256"]}
    jobs = []
    bindings = {}
    backends = {}
    for i, original in enumerate(old_jobs):
        entry, instance = instances[original["instance"]]
        require(
            original["input_sha256"] == entry["sha256"] and original["geometry_sha256"] == entry["geometry_sha256"],
            "job input binding drift",
        )
        case = ALIASES.get(original["case_id"], original["case_id"])
        _, cfg = cli.native_cli.get_solver_and_config(
            case,
            original["cutoff_sec"],
            seed=original["seed"],
            gnn_model=output / "gnn_checkpoint.pt" if case.startswith("F") and case[-1] == "1" else None,
        )
        if case == "neurolkh":
            cfg.neurolkh_root = str(common.ASSETS)
        if case in ("pyvrp", "neurolkh") and case not in backends:
            backends[case] = cli.backend_identity(case, cfg)
        config = common.native.config_signature(asdict(cfg))
        binding = (
            common.factor.declared_configs(cfg, instance)
            if case.startswith("F")
            else {"requested_config": config, "effective_config": config, "module_configs": {}}
        )
        digest = hashlib.sha256(encode(binding)).hexdigest()
        if digest not in bindings:
            publish(output / "bindings" / f"{digest}.json", binding)
            bindings[digest] = f"bindings/{digest}.json"
        job = {
            **original,
            "run": f"{i:05d}_{original['instance']}_{original['case_id']}_s{original['seed']}_t{original['cutoff_sec']}",
            "ablation": case,
            "time_limit": original["cutoff_sec"],
            "input_key": entry["path"],
            "customers": entry["customers"],
            "binding_sha256": digest,
        }
        job.pop("execution_binding")
        job["command"] = common.shared.command(output, {"inputs": inputs}, {**job, "instance": entry["path"]})
        if case == "neurolkh":
            job["command"].extend(["--neurolkh-root", str(common.ASSETS)])
        job["declaration_sha256"] = hashlib.sha256(encode(job)).hexdigest()
        jobs.append(job)
    snapshot(output / "source_snapshot.zip")
    with zipfile.ZipFile(output / "source_snapshot.zip", "a", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.glob("tests/**/*.py")):
            archive.write(path, path.relative_to(ROOT))
    runtime, archived = common.native.archived_sources(output)
    plan = {
        "schema_version": 1,
        "jobs": jobs,
        "bindings": bindings,
        "inputs": inputs,
        "metadata": metadata,
        "backends": backends,
        "source_sha256": source_hash(),
        "source_files": runtime,
        "snapshot_files": archived,
        "source_snapshot_sha256": sha256(output / "source_snapshot.zip"),
        "checkpoint_sha256": sha256(output / "gnn_checkpoint.pt"),
        "training_metadata_sha256": sha256(output / "training_metadata.json"),
        "hardware": hardware(),
        "design_sha256": sha256(DESIGN / "design.json"),
        "search_budget_sec": 2365600,
        "design": design,
        "contrasts": read(DESIGN / "contrasts.json"),
        "policy": {
            "automatic_launch": False,
            "execution": "sequential",
            "return_gate": {"lower_slack": 0.05, "upper_slack": 0.5},
            "hash_seed": 42,
            "bootstrap_replicates": 10000,
            "bootstrap_seed": 20261019,
            "remaining_scope": [
                "baseline precision/representativeness is not established by engineering pilots",
                "compute allocation is not inferred from preparation",
            ],
            "fixtures_are_not_benchmark_data": True,
        },
    }
    publish(output / "plan.json", plan)
    hashes = {str(p.relative_to(output)): sha256(p) for p in sorted(output.rglob("*")) if p.is_file()}
    publish(output / "prepared_hashes.json", hashes)
    return load(output)


def load(output):
    plan = read(output / "plan.json")
    plan["manifest_sha256"] = sha256(output / "plan.json")
    return plan


def check(output, plan, job=None):
    hashes = read(output / "prepared_hashes.json")
    require(hashes.get("plan.json") == sha256(output / "plan.json") == plan["manifest_sha256"], "manifest drift")
    if job is None:
        require(
            encode({k: v for k, v in plan.items() if k != "manifest_sha256"}) == (output / "plan.json").read_bytes(),
            "in-memory manifest differs",
        )
    else:
        require(
            hashlib.sha256(encode({k: v for k, v in job.items() if k != "declaration_sha256"})).hexdigest()
            == job["declaration_sha256"],
            "in-memory job declaration drift",
        )
        frozen = read(output / "plan.json")
        declared = next((j for j in frozen["jobs"] if j["run"] == job["run"]), None)
        require(declared == job, "job differs from frozen manifest")
    names = (
        list(hashes)
        if job is None
        else ["plan.json", "protocol_before_execution.md", "bindings/" + job["binding_sha256"] + ".json"]
    )
    require(all(sha256(output / name) == hashes[name] for name in names), "prepared artifact drift")
    common.native.check_frozen(output, plan)
    require(hardware() == plan["hardware"], "hardware/package drift")
    for case in ("pyvrp", "neurolkh"):
        _, cfg = cli.native_cli.get_solver_and_config(case, 10)
        if case == "neurolkh":
            cfg.neurolkh_root = str(common.ASSETS)
        require(cli.backend_identity(case, cfg) == plan["backends"][case], "backend assets drift")


@contextmanager
def exclusive_lock(output):
    with (output / ".run.lock").open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("another runner holds the exclusive lock") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def execute_job(output, plan, job):
    directory = output / job["run"]
    budget = job["time_limit"]
    started = time.perf_counter()
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = usage.ru_utime + usage.ru_stime
    process_info = {"watchdog_fired": False, "returncode": None}
    with (directory / "stdout.log").open("x") as stdout, (directory / "stderr.log").open("x") as stderr:
        process = subprocess.Popen(
            job["command"],
            cwd=ROOT,
            env={**os.environ, **dict.fromkeys(common.native.THREADS, "1")},
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
        process_info["pid"] = process.pid
        publish(directory / "cli_process.json", process_info)
        try:
            process_info["returncode"] = process.wait(timeout=budget + 180)
        except subprocess.TimeoutExpired:
            process_info["watchdog_fired"] = True
            process.send_signal(signal.SIGINT)
            try:
                process_info["returncode"] = process.wait(timeout=10)
            finally:
                publish(directory / "cli_process.json", process_info, replace=True)
            raise
    publish(directory / "cli_process.json", process_info, replace=True)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {
        "returncode": process.returncode,
        "child_wall_sec": time.perf_counter() - started,
        "child_cpu_sec": after.ru_utime + after.ru_stime - cpu,
    }


def audit_job(output, plan, job, receipt):
    directory = output / job["run"]
    raw = read(directory / "result.json")
    binding = read(output / plan["bindings"][job["binding_sha256"]])
    require(hashlib.sha256(encode(binding)).hexdigest() == job["binding_sha256"], "binding content drift")
    view = {**plan, "configs": {job["run"]: binding}}
    actual = {**job, "instance": job["input_key"]}
    gates, errors = common.audit(output, actual, view, raw)
    error_kind = (raw.get("error") or "").partition(":")[0] or None
    known_failure = raw.get("feasible") is False and error_kind in ALGORITHM_ERRORS
    no_checkpoint = raw.get("worker_checkpoint") is None
    identity_ok = all(gates[k] for k in ("provenance_ok", "cold_ok", "clock_ok", "cleanup_ok"))
    requested = read(directory / "session/request.json")["identity"]["requested_config"]
    requested_ok = (
        common.native.config_signature(raw.get("requested_config", {}))
        == common.native.config_signature(requested)
        == binding["requested_config"]
    )
    binding_acceptable = requested_ok and (gates["binding_ok"] or (known_failure and no_checkpoint))
    quality_ok = gates["certification_ok"] and raw.get("feasible") is True and error_kind is None
    failure_ok = known_failure and all(raw.get(k) is None for k in ("routes", "nv", "td"))
    integrity = identity_ok and binding_acceptable and (quality_ok or failure_ok)
    integrity = integrity and type(receipt["returncode"]) is int and receipt["returncode"] == (0 if quality_ok else 1)
    cert = (raw.get("native_certification") or {}).get("certificate") or {}
    return {
        "run": job["run"],
        "instance": job["instance"],
        "case_id": job["case_id"],
        "seed": job["seed"],
        "cutoff_sec": job["time_limit"],
        "customers": job["customers"],
        "geometry_sha256": job["geometry_sha256"],
        "integrity_ok": bool(integrity),
        "available": bool(quality_ok),
        "return_ok": gates["budget_ok"],
        "binding_ok": gates["binding_ok"],
        "nv": raw["nv"] if quality_ok else None,
        "td": raw["td"] if quality_ok else None,
        "runtime_sec": raw.get("runtime_sec"),
        "captured_sec": cert.get("captured_sec"),
        "error_kind": error_kind,
        "child_wall_sec": receipt["child_wall_sec"],
        "child_cpu_sec": receipt["child_cpu_sec"],
        "result_sha256": sha256(directory / "result.json"),
        "audit_errors": json.dumps(errors),
    }


def intent(plan, job):
    return {
        "job": job["run"],
        "manifest_sha256": plan["manifest_sha256"],
        "command": job["command"],
        "binding_sha256": job["binding_sha256"],
    }


def commit(output, plan, job, *, auditor=None):
    auditor = auditor or audit_job
    directory = output / job["run"]
    started = read(directory / "started.json")
    require(all(started.get(k) == v for k, v in intent(plan, job).items()), "invalid launch intent")
    require(finite(started.get("intent_perf")), "invalid intent clock")
    require(not (directory / "integrity_error.json").exists(), "protocol drift recorded during execution")
    receipt = read(directory / "execution.json")
    require(
        receipt.get("job") == job["run"] and receipt.get("manifest_sha256") == plan["manifest_sha256"],
        "receipt identity drift",
    )
    metrics = receipt["metrics"]
    process = read(directory / "cli_process.json")
    require(
        type(metrics.get("returncode")) is int
        and metrics["returncode"] == process.get("returncode")
        and not process.get("watchdog_fired", False),
        "incomplete outer CLI reaping evidence",
    )
    require(
        all(finite(metrics[k]) and metrics[k] >= 0 for k in ("child_wall_sec", "child_cpu_sec")),
        "invalid resource receipt",
    )
    row = auditor(output, plan, job, metrics)
    files = {}
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        if path.parent == directory and (
            path.name in ("completed.json", "evidence.json")
            or any(
                path.name.startswith(prefix + ".") and path.name.endswith(".pending")
                for prefix in ("completed", "evidence", "execution", "started", "cli_process")
            )
        ):
            continue
        files[str(path.relative_to(directory))] = sha256(path)
    publish(directory / "evidence.json", files)
    record = {
        "job": job["run"],
        "manifest_sha256": plan["manifest_sha256"],
        "evidence_sha256": sha256(directory / "evidence.json"),
        "receipt_sha256": sha256(directory / "execution.json"),
        "record": row,
    }
    publish(directory / "completed.json", record)
    return row


def views(output, plan, rows, status):
    temporary = output / ("records." + uuid.uuid4().hex + ".pending")
    with temporary.open("x", newline="") as stream:
        if rows:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    os.replace(temporary, output / "records.csv")
    status_view(output, plan, rows, status)


def status_view(output, plan, rows, status):
    publish(
        output / "status.json",
        {
            "status": status,
            "completed_jobs": len(rows),
            "planned_jobs": len(plan["jobs"]),
            "manifest_sha256": plan["manifest_sha256"],
        },
        replace=True,
    )


def run(output, *, max_jobs=None, execute=None, auditor=None):
    output = output.resolve()
    execute = execute or execute_job
    auditor = auditor or audit_job
    require(max_jobs is None or (type(max_jobs) is int and max_jobs > 0), "max_jobs must be positive")
    rows = []
    dispatched = 0
    stop = False
    view_ready = False

    def request_stop(*_):
        nonlocal stop
        stop = True

    with exclusive_lock(output):
        plan = load(output)
        check(output, plan)
        missing = False
        for declared in plan["jobs"]:
            if not (output / declared["run"]).exists():
                missing = True
            else:
                require(not missing, "non-prefix job artifacts violate frozen order")
        previous = signal.signal(signal.SIGINT, request_stop)
        try:
            for job in plan["jobs"]:
                directory = output / job["run"]
                if directory.exists():
                    require(
                        (directory / "started.json").is_file()
                        and (directory / "execution.json").is_file()
                        and (directory / "result.json").is_file(),
                        "ambiguous incomplete launch intent; no automatic retry",
                    )
                    row = commit(output, plan, job, auditor=auditor)
                else:
                    if stop or (max_jobs is not None and dispatched >= max_jobs):
                        break
                    if not view_ready:
                        views(output, plan, rows, "running")
                        view_ready = True
                    check(output, plan, job)
                    directory.mkdir()
                    publish(directory / "started.json", {**intent(plan, job), "intent_perf": time.perf_counter()})
                    metrics = execute(output, plan, job)
                    publish(
                        directory / "execution.json",
                        {"job": job["run"], "manifest_sha256": plan["manifest_sha256"], "metrics": metrics},
                    )
                    try:
                        check(output, plan, job)
                    except Exception as exc:
                        publish(directory / "integrity_error.json", {"reason": f"{type(exc).__name__}: {exc}"})
                        raise
                    row = commit(output, plan, job, auditor=auditor)
                    dispatched += 1
                rows.append(row)
                require(row["integrity_ok"], "protocol integrity failure retained; subsequent dispatch stopped")
                if view_ready:
                    with (output / "records.csv").open("a", newline="") as stream:
                        writer = csv.DictWriter(stream, fieldnames=list(row))
                        if stream.tell() == 0:
                            writer.writeheader()
                        writer.writerow(row)
                status_view(output, plan, rows, "running")
            status = "completed" if len(rows) == len(plan["jobs"]) else "stopped_after_job"
            views(output, plan, rows, status)
            return {"status": status, "completed_jobs": len(rows), "dispatched_jobs": dispatched}
        except BaseException:
            views(output, plan, rows, "needs_attention")
            raise
        finally:
            signal.signal(signal.SIGINT, previous)


def audit(output, *, require_complete=False):
    with exclusive_lock(output):
        plan = load(output)
        check(output, plan)
        rows = []
        for job in plan["jobs"]:
            directory = output / job["run"]
            if not directory.exists():
                continue
            require((directory / "completed.json").is_file(), "incomplete transaction cannot enter analysis")
            row = commit(output, plan, job)
            require(row["integrity_ok"], "protocol-invalid completed record")
            rows.append(row)
        complete = len(rows) == len(plan["jobs"])
        require(complete or not require_complete, "full declared matrix is incomplete")
        views(output, plan, rows, "completed" if complete else "prepared_or_incomplete")
        return plan, rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--output-dir", type=Path, required=True)
    for name in ("run", "audit", "status"):
        p = sub.add_parser(name)
        p.add_argument("--run-dir", type=Path, required=True)
        if name == "run":
            p.add_argument("--max-jobs", type=int)
        if name == "audit":
            p.add_argument("--require-complete", action="store_true")
    args = parser.parse_args(argv)
    if args.action == "prepare":
        plan = prepare(args.output_dir)
        result = {
            "status": "prepared",
            "jobs": len(plan["jobs"]),
            "nominal_solve_sec": plan["search_budget_sec"],
            "solver_calls": 0,
        }
    elif args.action == "run":
        result = run(args.run_dir, max_jobs=args.max_jobs)
    elif args.action == "audit":
        plan, rows = audit(args.run_dir, require_complete=args.require_complete)
        result = {"status": "audited", "completed_jobs": len(rows), "planned_jobs": len(plan["jobs"])}
    else:
        path = args.run_dir / "status.json"
        plan = load(args.run_dir)
        result = (
            read(path)
            if path.exists()
            else {"status": "prepared", "completed_jobs": 0, "planned_jobs": len(plan["jobs"])}
        )
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
