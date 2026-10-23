from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from vrptw.core import Inst

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def pilot():
    spec = importlib.util.spec_from_file_location(
        "certification_pilot", ROOT / "scripts/run_native_certification_pilot.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_schedule_is_prespecified_complete_balanced_and_reproducible(pilot):
    jobs = pilot.build_schedule(20261019)
    assert jobs == pilot.build_schedule(20261019)
    assert len(jobs) == len({j["run"] for j in jobs}) == 18
    assert Counter((j["instance"], j["seed"], j["ablation"]) for j in jobs) == Counter(
        (instance, seed, branch)
        for instance in pilot.INSTANCES
        for seed in (42, 43)
        for branch in ("alns", "full_no_gnn", "full")
    )
    assert sum(j["time_limit"] for j in jobs) == 180
    assert all(j["time_limit"] == 10 and not j["profiled"] for j in jobs)
    for branch in ("alns", "full_no_gnn", "full"):
        assert Counter(j["position"] for j in jobs if j["ablation"] == branch) == {0: 2, 1: 2, 2: 2}


@pytest.fixture
def record():
    data = np.zeros((4, 7))
    data[:, 0], data[:, 1], data[:, 5] = np.arange(4), np.arange(4), 100
    data[1:, 3] = 1
    inst = Inst({"name": "audit_fixture", "capacity": 10, "data": data})
    routes = [[1, 2, 3]]
    digest = hashlib.sha256(json.dumps(routes, separators=(",", ":")).encode()).hexdigest()
    cfg = {"time_limit": 10, "wall_clock_only": True, "seed": 42, "split_enabled": False}
    job = {"run": "toy", "instance": "toy.txt", "seed": 42, "ablation": "full", "time_limit": 10}
    identity = {
        "source_sha256": "source",
        "source_files": {"src/runtime.py": "digest"},
        "checkpoint_sha256": "model",
        "input_sha256": "input",
        "requested_config": cfg,
        "effective_config": cfg,
    }
    point = {"t_sec": 9.75, "nv": 1, "td": 6.0, "iter": 1, "phase": "search", "routes_sha256": digest}
    cert = {
        "captured_sec": 9.75,
        "cutoff_sec": 10,
        "nv": 1,
        "td": 6.0,
        "clock": "perf_counter",
        "iter": 1,
        "phase": "search",
        "routes_sha256": digest,
        "validation": {"exact_cover": True, "route_feasible": True, "objective_recomputed": True},
    }
    result = {
        "routes": routes,
        "feasible": True,
        "validation": {"route_feasible": True, "exact_cover": True},
        "nv": 1,
        "td": 6.0,
        "runtime_sec": 10.02,
        "iterations": 3,
        "requested_ablation": "full",
        "requested_config": cfg,
        "effective_config": cfg,
        "resolved_components": {"gnn_edge_guidance": True, "external_learned_candidates": False},
        "environment": {
            "source_sha256": "source",
            "source_files": identity["source_files"],
            "torch_threads": 1,
            "thread_environment": {
                key: "1" for key in ("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
            },
        },
        "metadata": {
            "instance_sha256": "input",
            "seed": 42,
            "time_limit": 10,
            "ablation": "full",
            "gnn_model_sha256": "model",
            "cold_start": True,
            "warmup": False,
            "budget_mode": "wall-clock",
            "profiling": {"enabled": False, "sha256": None},
        },
        "trajectory": [point, {"phase": "return", "t_sec": 10.02, "nv": 1, "td": 6.0}],
        "native_certification": {
            "schema_version": 1,
            "status": "certified",
            "clock": "perf_counter",
            "cutoff_sec": 10,
            "hard_return_deadline": False,
            "elapsed_sec": 10.01,
            "certificate": cert,
            "rejected_late": 0,
            "rejected_invalid": 0,
        },
    }
    return inst, job, identity, result


def test_independent_audit_accepts_valid_certificate(pilot, record):
    inst, job, identity, result = record
    audited = pilot.audit_result(result, inst, job, identity)
    assert audited["certification_ok"] and audited["clock_ok"] and audited["provenance_ok"] and audited["budget_ok"]
    assert audited["errors"] == []


@pytest.mark.parametrize(
    "defect",
    [
        "missing_certificate",
        "equal_cutoff",
        "late",
        "negative",
        "nan",
        "hash",
        "td",
        "nv",
        "validation",
        "missing_customer",
        "capacity",
        "window",
        "depot",
        "trace_time",
        "trace_hash",
        "source",
        "model",
        "config",
    ],
)
def test_audit_rejects_tampered_or_invalid_certificate_without_trusting_flags(pilot, record, defect):
    inst, job, identity, original = record
    result = copy.deepcopy(original)
    cert = result["native_certification"]["certificate"]
    if defect == "missing_certificate":
        result.pop("native_certification")
    elif defect in ("equal_cutoff", "late", "negative", "nan"):
        cert["captured_sec"] = {"equal_cutoff": 10, "late": 11, "negative": -1, "nan": float("nan")}[defect]
    elif defect in ("hash", "td", "nv"):
        key, value = {"hash": ("routes_sha256", "wrong"), "td": ("td", 0), "nv": ("nv", 2)}[defect]
        cert[key] = value
    elif defect == "validation":
        cert["validation"]["exact_cover"] = False
    elif defect == "missing_customer":
        result["routes"] = [[1, 2]]
    elif defect == "capacity":
        inst.capacity = 2
    elif defect == "window":
        inst.due_times[2] = 1
    elif defect == "depot":
        inst.due_times[0] = 5
    elif defect == "trace_time":
        result["trajectory"][0]["t_sec"] = 10
    elif defect == "trace_hash":
        result["trajectory"][0]["routes_sha256"] = "wrong"
    elif defect == "source":
        result["environment"]["source_sha256"] = "drift"
    elif defect == "model":
        result["metadata"]["gnn_model_sha256"] = "drift"
    else:
        result["effective_config"]["time_limit"] = 11
    audited = pilot.audit_result(result, inst, job, identity)
    assert audited["errors"]
    assert not all(audited[k] for k in ("certification_ok", "clock_ok", "provenance_ok"))


def test_late_return_and_precutoff_certificate_have_separate_gates(pilot, record):
    inst, job, identity, result = record
    result["runtime_sec"] = result["trajectory"][-1]["t_sec"] = 11.0
    result["native_certification"]["elapsed_sec"] = 10.99
    audited = pilot.audit_result(result, inst, job, identity)
    assert audited["certification_ok"] and audited["clock_ok"] and audited["provenance_ok"]
    assert not audited["budget_ok"]


def test_failed_job_is_preserved_as_failure_not_an_exception(pilot, record):
    inst, job, identity, _ = record
    audited = pilot.audit_result(
        {"feasible": False, "error": "NativeNoSolutionError: no incumbent"}, inst, job, identity
    )
    assert not audited["certification_ok"] and not audited["budget_ok"]
    assert audited["errors"]


@pytest.mark.parametrize("drift", [False, True])
def test_execution_preserves_failed_cells_and_only_identity_drift_aborts(pilot, record, monkeypatch, tmp_path, drift):
    inst, job, identity, result = record
    jobs = [dict(job, run=f"run{idx}") for idx in range(2)]
    plan = {
        "jobs": jobs,
        "inputs": {job["instance"]: {"snapshot": "toy.txt", "sha256": "input"}},
        **{key: identity[key] for key in ("source_sha256", "source_files", "checkpoint_sha256")},
        "configs": {j["run"]: {key: identity[key] for key in ("requested_config", "effective_config")} for j in jobs},
    }
    pilot.write_json(tmp_path / "plan.json", plan)
    calls = []

    def frozen(output, declared):
        assert json.loads((output / "plan.json").read_text()) == declared
        if drift and calls:
            raise ValueError("frozen identity drift")

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs["env"]["NUMBA_NUM_THREADS"] == "1"
        payload = {"feasible": False, "error": "NativeNoSolutionError: fixture"} if len(calls) == 1 else result
        target = Path(command[command.index("--output-json") + 1])
        target.write_text(json.dumps(payload))
        return SimpleNamespace(returncode=int(len(calls) == 1))

    monkeypatch.setattr(pilot, "check_frozen", frozen)
    monkeypatch.setattr(pilot, "load_solomon_instance", lambda _: inst)
    monkeypatch.setattr(pilot.subprocess, "run", run)
    status = pilot.execute(tmp_path, plan)
    assert len(calls) == (1 if drift else 2)
    assert status["status"] == ("aborted" if drift else "completed")
    assert not status["all_gates_passed"]
    assert status["completed_jobs"] == len(calls)
    assert json.loads((tmp_path / "run0.json").read_text())["error"].startswith("NativeNoSolutionError")


def test_preparation_refuses_existing_output_without_overwriting_it(pilot, tmp_path, monkeypatch):
    model = tmp_path / "best.pt"
    model.write_bytes(b"model")
    (tmp_path / "training.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "smoke_only": False,
                "checkpoint_sha256": hashlib.sha256(b"model").hexdigest(),
            }
        )
    )
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "preserved.txt"
    sentinel.write_bytes(b"preserve")
    monkeypatch.setattr(pilot, "INSTANCES", ())
    with pytest.raises(FileExistsError):
        pilot.prepare(output, model, 20261019)
    assert list(output.iterdir()) == [sentinel] and sentinel.read_bytes() == b"preserve"
