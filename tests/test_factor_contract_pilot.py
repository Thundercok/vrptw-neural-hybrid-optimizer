"""Frozen operational protocol, independent audits and fresh-cache execution."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from vrptw import Config, Inst
from vrptw.solvers import HybridDDQNSolver

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "results/gnn_retraining_20261017/model_seed42/best.pt"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def pilot():
    return load_script("run_factor_contract_pilot")


def test_schedule_covers_contracts_without_claiming_full_position_balance(pilot):
    jobs = pilot.build_schedule(20261019)
    assert jobs == pilot.build_schedule(20261019)
    assert len(jobs) == len({j["run"] for j in jobs}) == 24
    assert Counter((j["instance"], j["ablation"]) for j in jobs) == Counter(
        (i, c) for i in pilot.native.INSTANCES for c in pilot.CASES
    )
    assert sum(j["time_limit"] for j in jobs) == 240
    assert all(j["seed"] == 42 and j["time_limit"] == 10 and not j["profiled"] for j in jobs)
    assert Counter(j["position"] for j in jobs) == dict.fromkeys(range(8), 3)
    assert all(len({j["position"] for j in jobs if j["ablation"] == c}) == 3 for c in pilot.CASES)
    assert {(c[3], c[4]) for c in pilot.CASES} == {(a, b) for a in "01" for b in "01"}


def test_cli_captures_entry_before_project_imports(monkeypatch, tmp_path):
    work, cache = tmp_path / "work", tmp_path / "cache"
    work.mkdir()
    cache.mkdir()
    monkeypatch.chdir(work)
    monkeypatch.setenv("NUMBA_CACHE_DIR", str(cache))
    cli = load_script("benchmark")
    entry = cli.PROCESS_ENTRY_STATE
    assert entry == {"cwd": str(work), "cwd_entries": [], "cache_dir": str(cache), "cache_entries": []}
    (cache / "later.nbc").write_text("compiled")
    assert cli.PROCESS_ENTRY_STATE["cache_entries"] == []
    assert cli.get_env_info()["process_entry"] == entry


@pytest.mark.parametrize("case", ["alns", "full", "F000000", "F111111"])
def test_cli_data_path_identity_is_independent_of_working_directory(monkeypatch, tmp_path, case):
    cli = load_script("benchmark")
    model = MODEL if case == "F111111" else None
    monkeypatch.chdir(ROOT)
    first = asdict(cli.get_solver_and_config(case, 10, gnn_model=model)[1])
    (tmp_path / "data/Solomon").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    second = asdict(cli.get_solver_and_config(case, 10, gnn_model=model)[1])
    assert first["data_path"] == second["data_path"] == str(ROOT / "data/Solomon")
    assert {k: v for k, v in first.items() if k != "output_dir"} == {
        k: v for k, v in second.items() if k != "output_dir"
    }


def test_cli_records_actual_cold_state_and_detects_loaded_state():
    cli = load_script("benchmark")
    inst = make_instance()
    solver = HybridDDQNSolver(inst, Config())
    expected = {
        "archive_plans": 0,
        "pool_created": False,
        "macro_replay_size": 0,
        "micro_replay_size": 0,
        "macro_training_calls": 0,
        "micro_training_calls": 0,
        "lac_queries": 0,
    }
    assert cli.cold_start_state(solver) == expected
    solver.archive._plans[inst.name] = [object()]
    solver.ctrl.step = 7
    state = cli.cold_start_state(solver)
    assert state["archive_plans"] == 1 and state["macro_training_calls"] == 7


def test_cli_preserves_binding_evidence_on_solve_failure(monkeypatch, tmp_path):
    from vrptw.ablation import AblationHybridSolver

    cli = load_script("benchmark")
    path = tmp_path / "result.json"
    monkeypatch.setattr(cli, "load_solomon_instance", lambda *a: make_instance())
    monkeypatch.setattr(cli, "get_env_info", lambda: {})

    def fail(*args, **kwargs):
        raise RuntimeError("forced no incumbent")

    monkeypatch.setattr(AblationHybridSolver, "solve", fail)
    monkeypatch.setattr(
        cli.sys,
        "argv",
        [
            "benchmark",
            "--instance",
            str(MODEL),
            "--ablation",
            "F000000",
            "--time-limit",
            "10",
            "--output-json",
            str(path),
        ],
    )
    assert cli.main() == 1
    raw = json.loads(path.read_text())
    assert "forced no incumbent" in raw["error"] and raw["feasible"] is False
    assert raw["instrumentation"]["macro_policy"] == "rule"
    assert raw["effective_config"]["ablation_case"] == "F000000"
    assert raw["cold_start_evidence"]["archive_plans"] == 0
    assert raw["setup_timings"]["constructor_sec"] >= 0


def make_instance():
    data = np.zeros((4, 7))
    data[:, 0], data[:, 1], data[:, 5] = np.arange(4), np.arange(4), 100
    data[1:, 3] = 1
    return Inst({"name": "factor_fixture", "capacity": 10, "data": data})


@pytest.fixture
def record(pilot, tmp_path):
    inst = make_instance()
    job = {"run": "toy", "instance": "toy.txt", "seed": 42, "ablation": "F000000", "time_limit": 10}
    cfg = load_script("benchmark").get_solver_and_config("F000000", 10)[1]
    configs = pilot.declared_configs(cfg, inst)
    identity = {
        "source_sha256": "source",
        "source_files": {"src/a.py": "digest"},
        "checkpoint_sha256": "model",
        "input_sha256": "input",
        **configs,
    }
    work, cache = tmp_path / "toy/work", tmp_path / "toy/cache"
    identity.update(work_dir=str(work), cache_dir=str(cache))
    routes = [[1, 2, 3]]
    digest = hashlib.sha256(json.dumps(routes, separators=(",", ":")).encode()).hexdigest()
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
    components = {
        "macro_ddqn": False,
        "micro_ddqn": False,
        "lac": False,
        "gnn_edge_guidance": False,
        "external_learned_candidates": False,
        "route_pool": False,
        "gec": False,
        "learned_split": False,
    }
    result = {
        "feasible": True,
        "nv": 1,
        "td": 6.0,
        "routes": routes,
        "iterations": 3,
        "runtime_sec": 10.02,
        "validation": {"exact_cover": True, "route_feasible": True},
        "requested_ablation": job["ablation"],
        "requested_config": asdict(cfg),
        "effective_config": configs["effective_config"],
        "resolved_components": components,
        "instrumentation": {
            "resolved_components": components,
            "macro_policy": "rule",
            "micro_policy": "rule",
            "controller_counts": {"micro_rule": 3, "macro_rule": 1},
            "macro_replay_size": 0,
            "micro_replay_size": 0,
            "macro_training_calls": 0,
            "micro_training_calls": 0,
            "highs_calls": 0,
            "lac_queries": 0,
            "lac_acceptances": 0,
            "module_configs": configs["module_configs"],
        },
        "cold_start_evidence": {
            "archive_plans": 0,
            "pool_created": False,
            "macro_replay_size": 0,
            "micro_replay_size": 0,
            "macro_training_calls": 0,
            "micro_training_calls": 0,
            "lac_queries": 0,
        },
        "setup_timings": {"constructor_sec": 0.1, "model_load_sec": 0.0, "child_entry_to_solve_sec": 1.0},
        "metadata": {
            "instance_sha256": "input",
            "seed": 42,
            "time_limit": 10,
            "ablation": job["ablation"],
            "gnn_model_sha256": None,
            "cold_start": True,
            "pretrained_controller": False,
            "warmup": False,
            "budget_mode": "wall-clock",
            "profiling": {"enabled": False},
        },
        "environment": {
            "source_sha256": "source",
            "source_files": identity["source_files"],
            "torch_threads": 1,
            "thread_environment": dict.fromkeys(pilot.native.THREADS, "1"),
            "process_entry": {"cwd": str(work), "cwd_entries": [], "cache_dir": str(cache), "cache_entries": []},
            "numba": {"cache_dir": str(cache), "disable_jit": False, "version": "test"},
            "jit_environment": {"NUMBA_CACHE_DIR": str(cache), "NUMBA_DISABLE_JIT": "0", "PYTHONHASHSEED": "42"},
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


def test_valid_independent_factor_audit(pilot, record):
    audited = pilot.audit_result(*record)
    assert all(audited[k] for k in pilot.GATES) and audited["errors"] == []


def factor_record(pilot, original, job, identity):
    raw = copy.deepcopy(original)
    gec, sp, macro, micro, lac, gnn = map(bool, pilot.factor_levels(job["ablation"]))
    raw.update(
        requested_ablation=job["ablation"],
        requested_config=copy.deepcopy(identity["requested_config"]),
        effective_config=copy.deepcopy(identity["effective_config"]),
    )
    raw["requested_config"]["gnn_model_path"] = identity.get("model_path")
    raw["requested_config"]["output_dir"] = identity["work_dir"] + "/output"
    raw["metadata"].update(
        ablation=job["ablation"],
        instance_sha256=identity["input_sha256"],
        gnn_model_sha256=identity["checkpoint_sha256"] if gnn else None,
    )
    raw["environment"].update(source_sha256=identity["source_sha256"], source_files=identity["source_files"])
    raw["environment"]["process_entry"].update(cwd=identity["work_dir"], cache_dir=identity["cache_dir"])
    raw["environment"]["numba"]["cache_dir"] = identity["cache_dir"]
    raw["environment"]["jit_environment"]["NUMBA_CACHE_DIR"] = identity["cache_dir"]
    raw["resolved_components"].update(
        gec=gec, route_pool=sp, macro_ddqn=macro, micro_ddqn=micro, lac=lac, gnn_edge_guidance=gnn
    )
    ins = raw["instrumentation"]
    ins.update(
        module_configs=copy.deepcopy(identity["module_configs"]),
        macro_policy="ddqn" if macro else "rule",
        micro_policy="ddqn" if micro else "rule",
        controller_counts={"macro_ddqn" if macro else "macro_rule": 1, "micro_ddqn" if micro else "micro_rule": 3},
    )
    return raw


@pytest.mark.parametrize(
    "case", ["F111111", "F000000", "F110000", "F001111", "F011111", "F101111", "F110111", "F111011"]
)
def test_audit_handles_every_scheduled_binding(pilot, record, case):
    inst, job, identity, original = record
    job["ablation"] = case
    model = MODEL if pilot.factor_levels(case)[5] else None
    cfg = load_script("benchmark").get_solver_and_config(case, 10, gnn_model=model)[1]
    identity.update(pilot.declared_configs(cfg, inst), model_path=str(model) if model else None)
    raw = factor_record(pilot, original, job, identity)
    audited = pilot.audit_result(inst, job, identity, raw)
    assert all(audited[k] for k in pilot.GATES), audited["errors"]


def test_directory_audit_reopens_routes_configs_process_and_cache_artifacts(pilot, record, monkeypatch, tmp_path):
    inst, _, _, original = record
    output = tmp_path / "frozen_evidence"
    plan = pilot.prepare(output, MODEL, 20261019)
    monkeypatch.setattr(pilot, "load_job_instance", lambda *a: inst)

    def child(command, **kwargs):
        job = next(
            j
            for j in plan["jobs"]
            if j["ablation"] == command[command.index("--ablation") + 1]
            and Path(j["instance"]).name == Path(command[command.index("--instance") + 1]).name
        )
        identity = pilot.identity_for(output, plan, job)
        raw = factor_record(pilot, original, job, identity)
        Path(command[command.index("--output-json") + 1]).write_text(json.dumps(raw))
        (Path(kwargs["env"]["NUMBA_CACHE_DIR"]) / "new.nbc").write_text("compile fixture")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(pilot.subprocess, "run", child)
    state = pilot.execute(output, plan)
    assert state["status"] == "completed" and state["all_gates_passed"]
    job = plan["jobs"][0]
    for filename, mutate, message in (
        (
            f"{job['run']}.json",
            lambda r: r["native_certification"]["certificate"].update(captured_sec=10),
            "CSV gate drift",
        ),
        (f"{job['run']}.launch.json", lambda r: r.update(child_cpu_sec=999), "CSV process metric drift"),
        ("plan.json", lambda r: r.update(scope="rewritten"), "plan changed"),
    ):
        path = output / filename
        before = path.read_bytes()
        value = json.loads(before)
        mutate(value)
        path.write_text(json.dumps(value))
        with pytest.raises(ValueError, match=message):
            pilot.audit_directory(output)
        path.write_bytes(before)
    cache_file = pilot.job_dirs(output, job)[1] / "new.nbc"
    before = cache_file.read_bytes()
    cache_file.write_text("tampered")
    with pytest.raises(ValueError, match="cache artifact drift"):
        pilot.audit_directory(output)
    cache_file.write_bytes(before)
    audit = pilot.audit_directory(output)
    assert audit["status"] == "passed" and len(audit["verified_runs"]) == 24
    assert audit["artifact_hashes"]["plan.json"] == pilot.sha256(output / "plan.json")


@pytest.mark.parametrize(
    "defect,gate",
    [
        ("source", "provenance_ok"),
        ("input", "provenance_ok"),
        ("model", "provenance_ok"),
        ("config", "binding_ok"),
        ("module", "binding_ok"),
        ("policy", "binding_ok"),
        ("replay", "binding_ok"),
        ("training", "binding_ok"),
        ("highs", "binding_ok"),
        ("lac", "binding_ok"),
        ("counts", "binding_ok"),
        ("components", "binding_ok"),
        ("cache", "cold_ok"),
        ("cwd", "cold_ok"),
        ("cache_path", "cold_ok"),
        ("jit", "cold_ok"),
        ("archive", "cold_ok"),
        ("initial_training", "cold_ok"),
        ("hash_seed", "cold_ok"),
        ("late", "certification_ok"),
        ("routes", "certification_ok"),
        ("clock", "clock_ok"),
        ("return", "budget_ok"),
    ],
)
def test_tampering_fails_the_relevant_gate(pilot, record, defect, gate):
    inst, job, identity, original = record
    result = copy.deepcopy(original)
    env, ins = result["environment"], result["instrumentation"]
    if defect == "source":
        env["source_sha256"] = "drift"
    elif defect == "input":
        result["metadata"]["instance_sha256"] = "drift"
    elif defect == "model":
        result["metadata"]["gnn_model_sha256"] = "drift"
    elif defect == "config":
        result["requested_config"]["gec_enabled"] = True
    elif defect == "module":
        ins["module_configs"]["route_pool"]["sp_time_limit"] = 99
    elif defect == "policy":
        ins["macro_policy"] = "ddqn"
    elif defect == "replay":
        ins["micro_replay_size"] = 1
    elif defect == "training":
        ins["macro_training_calls"] = 1
    elif defect == "highs":
        ins["highs_calls"] = 1
    elif defect == "lac":
        ins["lac_queries"] = 1
    elif defect == "counts":
        ins["controller_counts"]["micro_ddqn"] = 1
    elif defect == "components":
        result["resolved_components"]["gec"] = True
    elif defect == "cache":
        env["process_entry"]["cache_entries"] = ["old.nbc"]
    elif defect == "cwd":
        env["process_entry"]["cwd_entries"] = ["archive.json"]
    elif defect == "cache_path":
        env["numba"]["cache_dir"] = "/shared"
    elif defect == "jit":
        env["numba"]["disable_jit"] = True
    elif defect == "archive":
        result["cold_start_evidence"]["archive_plans"] = 1
    elif defect == "initial_training":
        result["cold_start_evidence"]["macro_training_calls"] = 2
    elif defect == "hash_seed":
        env["jit_environment"]["PYTHONHASHSEED"] = "random"
    elif defect == "late":
        result["native_certification"]["certificate"]["captured_sec"] = 10
    elif defect == "routes":
        result["routes"] = [[1, 2]]
    elif defect == "clock":
        result["native_certification"]["elapsed_sec"] = 20
    elif defect == "return":
        result["runtime_sec"] = 10.501
    audited = pilot.audit_result(inst, job, identity, result)
    assert not audited[gate] and audited["errors"]


def test_algorithm_failure_keeps_identity_distinct_from_availability(pilot, record):
    inst, job, identity, result = record
    result.update(error="NoCertifiedIncumbent: cold compilation consumed budget", feasible=False, nv=None, td=None)
    result.pop("routes")
    result["native_certification"]["certificate"] = None
    audited = pilot.audit_result(inst, job, identity, result)
    assert not audited["certification_ok"] and not audited["clock_ok"]
    assert all(audited[k] for k in ("provenance_ok", "binding_ok", "cold_ok"))


def test_prepare_freezes_without_solving_and_refuses_overwrite(pilot, monkeypatch, tmp_path):
    monkeypatch.setattr(HybridDDQNSolver, "solve", lambda *a, **kw: pytest.fail("preparation must not solve"))
    output = tmp_path / "pilot"
    plan = pilot.prepare(output, MODEL, 20261019)
    assert len(plan["jobs"]) == 24 and plan["search_budget_sec"] == 240
    assert plan["checkpoint_sha256"] == pilot.GNN_SHA256
    assert (output / "plan.json").is_file()
    pilot.native.check_frozen(output, plan)
    with pytest.raises(FileExistsError):
        pilot.prepare(output, MODEL, 20261019)


@pytest.mark.parametrize("integrity_failure", [False, "source", "plan", "protocol"])
def test_executor_isolates_every_child_and_retains_failures(pilot, record, monkeypatch, tmp_path, integrity_failure):
    inst, original_job, identity, original = record
    jobs = [{**original_job, "run": f"job{i}"} for i in range(3)]
    output = tmp_path / "execution"
    output.mkdir()
    protocol = output / "protocol_before_execution.md"
    protocol.write_text("frozen protocol")
    plan = {"jobs": jobs, "protocol_sha256": pilot.sha256(protocol)}
    (output / "plan.json").write_text(json.dumps(plan))
    monkeypatch.setattr(pilot.native, "check_frozen", lambda *a: None)
    monkeypatch.setattr(pilot, "identity_for", lambda *a: identity)
    monkeypatch.setattr(pilot, "load_job_instance", lambda *a: inst)
    calls = []

    def child(command, *, cwd, env, **kwargs):
        assert list(Path(cwd).iterdir()) == []
        cache = Path(env["NUMBA_CACHE_DIR"])
        assert list(cache.iterdir()) == [] and cache not in calls
        assert all(env[k] == "1" for k in pilot.native.THREADS)
        assert env["NUMBA_DISABLE_JIT"] == "0" and env["PYTHONHASHSEED"] == "42"
        calls.append(cache)
        raw = copy.deepcopy(original)
        raw["environment"]["process_entry"].update(cwd=str(cwd), cache_dir=str(cache))
        raw["environment"]["numba"]["cache_dir"] = str(cache)
        raw["environment"]["jit_environment"]["NUMBA_CACHE_DIR"] = str(cache)
        identity.update(work_dir=str(cwd), cache_dir=str(cache))
        raw.update(error="NoCertifiedIncumbent: test", feasible=False)
        if integrity_failure == "source":
            raw["environment"]["source_sha256"] = "drift"
        elif integrity_failure == "plan":
            (output / "plan.json").write_text("{}")
        elif integrity_failure == "protocol":
            protocol.write_text("changed protocol")
        Path(command[command.index("--output-json") + 1]).write_text(json.dumps(raw))
        (cache / "new.nbc").write_text("compiled")
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(pilot.subprocess, "run", child)
    monkeypatch.setattr(
        pilot, "command_for", lambda out, plan, j: ["python", "--output-json", str(out / f"{j['run']}.json")]
    )
    state = pilot.execute(output, plan)
    assert len(calls) == (1 if integrity_failure else 3)
    assert state["status"] == ("aborted" if integrity_failure else "completed")
    assert state["all_gates_passed"] is False
    assert (output / "summary.csv").is_file()
