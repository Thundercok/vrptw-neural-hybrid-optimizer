"""Longer-cutoff harness contracts; fixtures never launch a native solve."""

from __future__ import annotations

import copy
import importlib.util
import json
import signal
import subprocess
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def pilot():
    spec = importlib.util.spec_from_file_location("supervisor_pilot", ROOT / "scripts/run_supervisor_pilot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_declared_schedule_and_order(pilot):
    jobs = pilot.jobs()
    assert jobs == pilot.jobs()
    assert len(jobs) == len({j["run"] for j in jobs}) == 14
    expected = Counter(
        (inst, case, seed, 60) for inst in pilot.native.INSTANCES for case in ("alns", "F111111") for seed in (42, 43)
    )
    expected.update((pilot.native.INSTANCES[2], case, 43, 300) for case in ("alns", "F111111"))
    assert Counter((j["instance"], j["ablation"], j["seed"], j["time_limit"]) for j in jobs) == expected
    assert sum(j["time_limit"] for j in jobs) == 1320
    assert all(not j["profiled"] and not j["phase_traced"] for j in jobs)
    for case in ("alns", "F111111"):
        assert sorted(Counter(j["position"] for j in jobs if j["ablation"] == case).values()) == [3, 4]


@pytest.fixture(params=[60, 300])
def record(pilot, tmp_path, request):
    """Rebind a preserved successful ALNS record; no score/timing evidence is made."""
    original = ROOT / "results/supervisor_pilot_20261020"
    old_plan = json.loads((original / "plan.json").read_text())
    old_job = next(j for j in old_plan["jobs"] if j["ablation"] == "alns")
    job = {**old_job, "run": "fixture", "seed": 43, "time_limit": request.param}
    session = tmp_path / "fixture/session"
    session.mkdir(parents=True)
    for path in (original / old_job["run"] / "session").glob("*.json"):
        (session / path.name).write_bytes(path.read_bytes())
    target = tmp_path / old_plan["inputs"][job["instance"]]["snapshot"]
    target.parent.mkdir(parents=True)
    target.write_bytes((ROOT / job["instance"]).read_bytes())
    plan = copy.deepcopy(old_plan)
    _, cfg = pilot.cli.native_cli.get_solver_and_config("alns", job["time_limit"], seed=43)
    cfg.output_dir = str(session / "work/archive")
    config = asdict(cfg)
    expected = {
        "requested_config": pilot.native.config_signature(config),
        "effective_config": pilot.native.config_signature(config),
        "module_configs": {},
    }
    plan["configs"][job["run"]] = expected
    raw = json.loads((original / old_job["run"] / "result.json").read_text())
    req = json.loads((session / "request.json").read_text())
    req.update(time_limit=job["time_limit"], session_dir=str(session))
    req["identity"].update(seed=43, requested_config=config)
    (session / "request.json").write_text(json.dumps(req))
    ready = json.loads((session / "ready.json").read_text())
    ready["identity"] = copy.deepcopy(req["identity"])
    ready["environment"]["process_entry"].update(cwd=str(session / "work"), cache_dir=str(session / "cache"))
    ready["environment"]["numba"]["cache_dir"] = str(session / "cache")
    ready["jit_environment"]["NUMBA_CACHE_DIR"] = str(session / "cache")
    (session / "ready.json").write_text(json.dumps(ready))
    deadline = raw["solve_start_perf"] + job["time_limit"]
    raw.update(solve_deadline_perf=deadline, runtime_sec=job["time_limit"] + 0.02, requested_config=config)
    raw["metadata"].update(seed=43, time_limit=job["time_limit"], session_dir=str(session), requested_config=config)
    raw["cleanup_start_perf"], raw["cleanup_end_perf"] = deadline, deadline + 0.01
    raw["native_certification"]["cutoff_sec"] = job["time_limit"]
    raw["native_certification"]["certificate"]["cutoff_sec"] = job["time_limit"]
    raw["worker_checkpoint"]["effective_config"] = config
    for name in ("start.json", "ack.json"):
        message = json.loads((session / name).read_text())
        message["deadline_perf"] = deadline
        (session / name).write_text(json.dumps(message))
    for observed in raw["packet_observations"]:
        path = session / observed["file"]
        packet = json.loads(path.read_text())
        packet["deadline_perf"] = deadline
        packet["certificate"]["cutoff_sec"] = job["time_limit"]
        packet["checkpoint"]["effective_config"] = config
        path.write_text(json.dumps(packet))
        observed["sha256"] = pilot.sha256(path)
    return tmp_path, job, plan, raw


def test_variable_seed_and_budget_are_audited(pilot, record):
    verdict, errors = pilot.audit(*record)
    assert errors == []
    assert all(verdict.values())


@pytest.mark.parametrize("slack,accepted", [(-0.051, False), (-0.049, True), (0.499, True), (0.501, False), (2, False)])
def test_return_slack_is_absolute_at_long_cutoffs(pilot, record, slack, accepted):
    output, job, plan, raw = record
    raw["runtime_sec"] = job["time_limit"] + slack
    verdict, _ = pilot.audit(output, job, plan, raw)
    assert verdict["budget_ok"] is accepted


@pytest.mark.parametrize("field,value", [("seed", 42), ("time_limit", 10)])
def test_job_identity_tampering_is_rejected(pilot, record, field, value):
    output, job, plan, raw = record
    path = output / job["run"] / "session/request.json"
    req = json.loads(path.read_text())
    if field == "seed":
        req["identity"][field] = value
    else:
        req[field] = value
    path.write_text(json.dumps(req))
    verdict, _ = pilot.audit(output, job, plan, raw)
    assert verdict["provenance_ok"] is False


def test_cutoff_capture_is_strict(pilot, record):
    output, job, plan, raw = record
    raw["native_certification"]["certificate"]["captured_sec"] = job["time_limit"]
    verdict, _ = pilot.audit(output, job, plan, raw)
    assert verdict["certification_ok"] is False


@pytest.mark.parametrize("field,value", [("clock", "calendar"), ("cutoff_sec", 10)])
def test_packet_certificate_clock_is_audited(pilot, record, field, value):
    output, job, plan, raw = record
    observed = next(p for p in raw["packet_observations"] if p["admitted"])
    path = output / job["run"] / "session" / observed["file"]
    packet = json.loads(path.read_text())
    packet["certificate"][field] = value
    path.write_text(json.dumps(packet))
    observed["sha256"] = pilot.sha256(path)
    verdict, _ = pilot.audit(output, job, plan, raw)
    assert verdict["certification_ok"] is False


def test_metadata_identity_is_bound(pilot, record):
    output, job, plan, raw = record
    raw["metadata"]["source_sha256"] = "foreign-source"
    verdict, _ = pilot.audit(output, job, plan, raw)
    assert verdict["provenance_ok"] is False


def test_trajectory_objective_is_audited(pilot, record):
    output, job, plan, raw = record
    raw["trajectory"][0]["nv"] += 1
    verdict, _ = pilot.audit(output, job, plan, raw)
    assert verdict["certification_ok"] is False


def test_freeze_persists_all_commands_before_children(pilot, tmp_path):
    output = tmp_path / "prepared"
    plan = pilot.freeze(output)
    assert plan["search_budget_sec"] == 1320
    assert len(plan["commands"]) == 14
    assert all(plan["commands"][j["run"]] == pilot.command(output, plan, j) for j in plan["jobs"])
    pilot.check(output, plan, pilot.sha256(output / "plan.json"))
    assert not any((output / j["run"]).exists() for j in plan["jobs"])


def test_partial_activity_never_becomes_a_final_count(pilot):
    raw = {
        "worker_checkpoint": {"iterations": 7, "instrumentation": {"lac_queries": 2}},
        "final_worker_counters": None,
    }
    activity = pilot.activity(raw)
    assert activity["checkpoint_iterations"] == 7
    assert activity["checkpoint_lac_queries"] == 2
    assert activity["final_iterations"] is None and activity["final_lac_queries"] is None
    assert activity["checkpoint_micro_training_calls"] is None


def test_seed_and_budget_reach_command(pilot, record):
    output, job, plan, _ = record
    command = pilot.command(output, plan, job)
    assert command[command.index("--seed") + 1] == "43"
    assert command[command.index("--time-limit") + 1] == str(job["time_limit"])
    assert "--gnn-model" not in command
    job["ablation"] = "F111111"
    command = pilot.command(output, plan, job)
    assert command[command.index("--gnn-model") + 1] == str(output / "gnn_checkpoint.pt")


def test_existing_output_is_refused_before_mutation(pilot, tmp_path):
    marker = tmp_path / "keep"
    marker.write_text("prior bytes")
    with pytest.raises(FileExistsError):
        pilot.freeze(tmp_path)
    assert marker.read_text() == "prior bytes"
    assert list(tmp_path.iterdir()) == [marker]


def test_watchdog_requests_cli_finally_cleanup_without_blind_kill(pilot, monkeypatch, tmp_path):
    calls = []

    class Process:
        pid = 123

        def wait(self, timeout):
            calls.append(("wait", timeout))
            if len(calls) == 1:
                raise subprocess.TimeoutExpired("fixture", timeout)
            return -signal.SIGINT

        def send_signal(self, sig):
            calls.append(("signal", sig))

    monkeypatch.setattr(pilot.subprocess, "Popen", lambda *a, **k: Process())
    with pytest.raises(subprocess.TimeoutExpired):
        pilot.run_child(["fixture"], directory=tmp_path, budget=300)
    assert calls == [("wait", 480), ("signal", signal.SIGINT), ("wait", 10)]
    info = json.loads((tmp_path / "cli_process.json").read_text())
    assert info["watchdog_fired"] and info["returncode"] == -signal.SIGINT


def test_normal_child_does_not_receive_a_signal(pilot, monkeypatch, tmp_path):
    monkeypatch.setattr(pilot.subprocess, "Popen", lambda *a, **k: SimpleNamespace(pid=123, wait=lambda timeout: 0))
    assert pilot.run_child(["fixture"], directory=tmp_path, budget=60) == 0
