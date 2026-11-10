from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "benchmark_pilot", Path(__file__).resolve().parents[1] / "scripts" / "run_benchmark_pilot.py"
)
pilot = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pilot)


@pytest.mark.parametrize("include_gnn", [False, True])
@pytest.mark.parametrize("include_ortools", [False, True])
@pytest.mark.parametrize("include_pyvrp", [False, True])
@pytest.mark.parametrize("include_neurolkh", [False, True])
def test_pilot_isolates_checkpoint_to_full_runs_and_snapshots_it(
    tmp_path, monkeypatch, include_gnn, include_ortools, include_pyvrp, include_neurolkh
):
    root = tmp_path / "repo"
    root.mkdir()
    instances = ("a.txt", "b.txt", "c.txt")
    for name in instances:
        (root / name).touch()
    monkeypatch.setattr(pilot, "ROOT", root)
    monkeypatch.setattr(pilot, "INSTANCES", instances)
    monkeypatch.chdir(tmp_path)
    checkpoint = tmp_path / "weights.pt"
    checkpoint.write_bytes(b"frozen-checkpoint")
    arguments = ["pilot", "--output-dir", "out"]
    if include_gnn:
        arguments += ["--gnn-model", str(checkpoint)]
    if include_ortools:
        arguments += ["--include-ortools"]
    if include_pyvrp:
        arguments += ["--include-pyvrp"]
    if include_neurolkh:
        assets = tmp_path / "assets"
        assets.mkdir()
        (assets / "assets.json").write_text("{}")
        arguments += ["--neurolkh-root", str(assets)]
    monkeypatch.setattr(pilot.sys, "argv", arguments)
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        output = Path(command[command.index("--output-json") + 1])
        assert output.is_absolute()
        output.write_text(json.dumps({"feasible": True, "nv": 1, "td": 10, "runtime_sec": 10, "iterations": 4}))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(pilot.subprocess, "run", run)
    assert pilot.main() == 0
    counts = Counter(command[command.index("--ablation") + 1] for command in calls)
    expected = {"alns": 3, "full_no_gnn": 3}
    if include_gnn:
        expected["full"] = 3
    if include_ortools:
        expected["ortools"] = 3
    if include_pyvrp:
        expected["pyvrp"] = 3
    if include_neurolkh:
        expected["neurolkh"] = 3
    assert counts == expected
    for command in calls:
        if command[command.index("--ablation") + 1] == "full":
            model = Path(command[command.index("--gnn-model") + 1])
            assert model == tmp_path / "out" / "gnn_checkpoint.pt"
            assert model.read_bytes() == checkpoint.read_bytes()
        else:
            assert "--gnn-model" not in command
        assert ("--neurolkh-root" in command) == (command[command.index("--ablation") + 1] == "neurolkh")
    assert (tmp_path / "out" / "source_snapshot.zip").is_file()


def test_missing_checkpoint_fails_before_creating_output(tmp_path, monkeypatch):
    output = tmp_path / "out"
    monkeypatch.setattr(
        pilot.sys, "argv", ["pilot", "--output-dir", str(output), "--gnn-model", str(tmp_path / "absent.pt")]
    )
    with pytest.raises(SystemExit) as exc:
        pilot.main()
    assert exc.value.code == 2
    assert not output.exists()
