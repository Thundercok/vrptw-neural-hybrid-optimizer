from __future__ import annotations

import importlib.util
import json
import pstats
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from vrptw import Config, Inst
from vrptw.core import Plan

ROOT = Path(__file__).resolve().parents[1]


def load_script(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


diagnostic = load_script("native_diagnostic", ROOT / "scripts/run_native_diagnostic.py")
cli = load_script("profile_cli", ROOT / "scripts/benchmark.py")


def test_schedule_is_complete_balanced_reproducible_and_profiles_are_separate():
    jobs = diagnostic.build_schedule(20261019)
    assert jobs == diagnostic.build_schedule(20261019)
    plain = [j for j in jobs if not j["profiled"]]
    profiles = [j for j in jobs if j["profiled"]]
    assert len(plain) == 12 and len(profiles) == 3
    assert jobs[-3:] == profiles
    assert Counter((j["seed"], j["time_limit"], j["ablation"]) for j in plain) == Counter(
        {
            (seed, budget, branch): 1
            for seed in (42, 43)
            for budget in (10, 60)
            for branch in ("alns", "full_no_gnn", "full")
        }
    )
    for branch in ("alns", "full_no_gnn", "full"):
        counts = Counter(j["position"] for j in plain if j["ablation"] == branch)
        assert set(counts) == {0, 1, 2} and max(counts.values()) - min(counts.values()) <= 1
    assert all(j["seed"] == 42 and j["time_limit"] == 10 for j in profiles)
    assert sum(j["time_limit"] for j in jobs) == 450
    assert len({j["run"] for j in jobs}) == 15


@pytest.mark.parametrize("failure", [False, True])
def test_cli_profiles_only_solve_and_saves_stats_on_exception(monkeypatch, tmp_path, failure):
    data = np.zeros((3, 7))
    data[:, 0], data[:, 1], data[:, 5] = np.arange(3), np.arange(3), 100
    data[1:, 3] = 1
    inst = Inst({"name": "profile_toy", "capacity": 10, "data": data})
    input_path, output, profile = tmp_path / "in.txt", tmp_path / "out.json", tmp_path / "solve.pstats"
    input_path.write_text("fixture")
    calls = []

    class Solver:
        def __init__(self, inst, cfg):
            self.inst, self.cfg = inst, cfg
            self.search_iterations, self.time_limit_hit = 1, False
            calls.append("constructor")

        def solve(self, seed=None):
            calls.append("solve")
            if failure:
                raise RuntimeError("profile fixture")
            return Plan([[1, 2]], self.inst), []

    monkeypatch.setattr(cli, "load_solomon_instance", lambda path: inst)
    monkeypatch.setattr(cli, "get_env_info", lambda: {})
    monkeypatch.setattr(cli, "get_solver_and_config", lambda *a, **k: (Solver, Config(time_limit=1)))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark",
            "--instance",
            str(input_path),
            "--ablation",
            "alns",
            "--profile",
            str(profile),
            "--output-json",
            str(output),
        ],
    )
    assert cli.main() == int(failure)
    payload = json.loads(output.read_text())
    assert payload["metadata"]["profiling"]["enabled"] is True
    assert payload["metadata"]["profiling"]["sha256"] == cli.sha256_file(profile)
    functions = [key[2] for key in pstats.Stats(str(profile)).stats]
    assert "solve" in functions and "__init__" not in [
        key[2] for key in pstats.Stats(str(profile)).stats if key[0] == __file__
    ]
    assert calls == ["constructor", "solve"]
    assert ("error" in payload) is failure


def test_cli_refuses_to_overwrite_existing_profile(monkeypatch, tmp_path):
    profile = tmp_path / "solve.pstats"
    profile.write_bytes(b"preserve")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark",
            "--instance",
            "unused.txt",
            "--profile",
            str(profile),
            "--output-json",
            str(tmp_path / "out.json"),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2 and profile.read_bytes() == b"preserve"


def test_profile_and_result_cannot_share_a_path(monkeypatch, tmp_path):
    path = tmp_path / "collision"
    monkeypatch.setattr(
        sys, "argv", ["benchmark", "--instance", "unused.txt", "--profile", str(path), "--output-json", str(path)]
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2 and not path.exists()


@pytest.mark.parametrize("changed_source", [False, True])
def test_runner_freezes_plan_before_children_and_isolates_profile_and_checkpoint(monkeypatch, tmp_path, changed_source):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "instance.txt").write_text("fixture")
    model = tmp_path / "model.pt"
    model.write_bytes(b"frozen model")
    monkeypatch.setattr(diagnostic, "ROOT", root)
    monkeypatch.setattr(diagnostic, "INSTANCE", "instance.txt")
    monkeypatch.setattr(diagnostic, "snapshot", lambda path: path.write_bytes(b"fixture snapshot"))
    monkeypatch.setattr(diagnostic, "source_hash", lambda: "changed" if changed_source and calls else "frozen")
    monkeypatch.setattr(
        diagnostic,
        "build_schedule",
        lambda _: [
            {
                "run": "plain",
                "seed": 42,
                "time_limit": 10,
                "ablation": "alns",
                "profiled": False,
                "block": 0,
                "position": 0,
            },
            {
                "run": "profile",
                "seed": 42,
                "time_limit": 10,
                "ablation": "full",
                "profiled": True,
                "block": 1,
                "position": 0,
            },
        ],
    )
    output = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["diagnostic", "--output-dir", str(output), "--gnn-model", str(model)])
    calls = []

    def run(command, **kwargs):
        assert (output / "plan.json").is_file()
        plan = json.loads((output / "plan.json").read_text())
        assert len(plan["jobs"]) == 2 and plan["source_sha256"] == "frozen"
        calls.append(command)
        branch = command[command.index("--ablation") + 1]
        assert ("--gnn-model" in command) is (branch == "full")
        assert ("--profile" in command) is (branch == "full")
        target = Path(command[command.index("--output-json") + 1])
        target.write_text(
            json.dumps(
                {
                    "feasible": True,
                    "nv": 1,
                    "td": 1,
                    "runtime_sec": 10,
                    "iterations": 1,
                    "environment": {"source_sha256": "frozen"},
                }
            )
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(diagnostic.subprocess, "run", run)
    assert diagnostic.main() == int(changed_source)
    assert len(calls) == (1 if changed_source else 2)
    assert (output / "gnn_checkpoint.pt").read_bytes() == model.read_bytes()
    status = json.loads((output / "status.json").read_text())
    assert status["status"] == ("aborted" if changed_source else "completed")


def test_missing_checkpoint_fails_before_creating_diagnostic_output(monkeypatch, tmp_path):
    output = tmp_path / "out"
    monkeypatch.setattr(
        sys, "argv", ["diagnostic", "--output-dir", str(output), "--gnn-model", str(tmp_path / "missing")]
    )
    with pytest.raises(SystemExit):
        diagnostic.main()
    assert not output.exists()
