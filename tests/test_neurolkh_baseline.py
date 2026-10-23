from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from vrptw import Config, Inst
from vrptw import neurolkh_baseline as baseline
from vrptw.core import Plan

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "results/external/NeuroLKH"
SPEC = importlib.util.spec_from_file_location("neurolkh_cli", ROOT / "scripts/benchmark.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def instance(n=25):
    data = np.zeros((n + 1, 7))
    data[:, 0] = np.arange(n + 1)
    data[:, 1] = np.arange(n + 1) / 10
    data[1:, 3] = 1
    data[:, 5] = 100
    return Inst({"name": "neurolkh_toy", "capacity": 10.0, "data": data})


def test_features_exclude_self_even_for_coincident_locations_and_preserve_reverse_indices():
    inst = instance()
    inst.coords[2] = inst.coords[1]
    x, distances, edges, inverse, scale = baseline.neural_features(inst)
    assert x.shape == (26, 6) and edges.shape == inverse.shape == (26, 20)
    assert np.isfinite(x).all() and np.isfinite(distances).all()
    assert np.all(edges != np.arange(26)[:, None])
    assert scale == 2.5
    assert np.array_equal(x[:, 2], inst.demands / 50)
    for i, neighbours in enumerate(edges):
        for j, neighbour in enumerate(neighbours):
            idx = inverse[i, j]
            if idx >= 0:
                assert idx // 20 == neighbour and edges.flat[idx] == i


@pytest.mark.parametrize("vehicles", [1, 2, 4, 20, 25])
def test_candidate_file_covers_transformed_graph_without_out_of_range_nodes(tmp_path, vehicles):
    n = 25
    candidates = np.array([[(i + j + 1) % (n + 1) for j in range(20)] for i in range(n + 1)])
    path = tmp_path / "candidate.txt"
    baseline.write_candidates(path, candidates, candidates, vehicles)
    lines = path.read_text().splitlines()
    dimension = 2 * (n + vehicles)
    assert int(lines[0]) == dimension and lines[-2:] == ["-1", "EOF"]
    assert len(lines[1:-2]) == dimension
    for i, line in enumerate(lines[1:-2], 1):
        fields = list(map(int, line.split()))
        assert fields[:3] == [i, 0, 5] and len(fields) == 13
        neighbours = fields[3::2]
        assert len(set(neighbours)) == 5
        assert all(1 <= node <= dimension and node != i for node in neighbours)


def test_tour_parser_handles_empty_routes_and_checks_complete_permutation():
    text = "DIMENSION : 7\nTOUR_SECTION\n1\n2\n3\n6\n7\n4\n5\n-1\nEOF\n"
    assert baseline.parse_tour(text, customers=4, vehicles=3) == [[1, 2], [3, 4]]
    with pytest.raises(ValueError):
        baseline.parse_tour(text.replace("EOF", ""), customers=4, vehicles=3)
    with pytest.raises(ValueError):
        baseline.parse_tour(text.replace("\n5\n", "\n4\n"), customers=4, vehicles=3)


def test_first_half_dummy_depots_keep_the_upstream_bridge_to_real_depot(tmp_path):
    n, vehicles = 25, 20
    candidates = np.array([[(i + j + 1) % (n + 1) for j in range(20)] for i in range(n + 1)])
    path = tmp_path / "candidates.txt"
    baseline.write_candidates(path, candidates, candidates, vehicles)
    lines = path.read_text().splitlines()
    for node in range(n + 2, n + vehicles + 1):
        assert n + vehicles + 1 in list(map(int, lines[node].split()))[3::2]


def test_inference_consuming_budget_cannot_start_backend(monkeypatch, tmp_path):
    solver = baseline.NeuroLKHSolver.__new__(baseline.NeuroLKHSolver)
    solver.inst, solver.assets = instance(), {}
    solver.cfg = Config(time_limit=1.0, output_dir=str(tmp_path))
    solver.torch = SimpleNamespace(manual_seed=lambda seed: None)
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(baseline, "time", SimpleNamespace(perf_counter=lambda: clock.now))

    def infer():
        clock.now = 2.0
        return np.zeros((26, 20)), np.zeros((26, 20))

    monkeypatch.setattr(solver, "_infer", infer)
    monkeypatch.setattr(baseline.subprocess, "Popen", lambda *a, **k: pytest.fail("late backend"))
    with pytest.raises(baseline.NeuroLKHNoSolutionError):
        solver.solve(seed=47)
    assert solver.time_limit_hit and solver.diagnostics["stages"] == []


def test_unresponsive_child_is_killed_and_reaped():
    events = []

    def wait(timeout=None):
        events.append(("wait", timeout))
        if timeout:
            raise baseline.subprocess.TimeoutExpired("fixture", timeout)

    process = SimpleNamespace(
        poll=lambda: None, terminate=lambda: events.append("terminate"), kill=lambda: events.append("kill"), wait=wait
    )
    baseline.NeuroLKHSolver._stop_process(process)
    assert events == ["terminate", ("wait", 0.2), "kill", ("wait", None)]


def test_problem_writer_preserves_service_depot_and_conservative_travel(tmp_path):
    inst = instance()
    inst.service_times[1] = 0.123456789
    path = tmp_path / "instance.vrp"
    data = baseline.write_problem(path, inst, vehicles=25)
    text = path.read_text()
    assert "EDGE_WEIGHT_TYPE : EXPLICIT" in text and "VEHICLES : 25" in text
    assert "SERVICE_TIME_SECTION\n1 0\n2 12346\n" in text
    assert np.all(data["distance"] / baseline.DISTANCE_SCALE >= inst.dist - 1e-12)
    assert data["ready"][0] == 0 and data["due"][0] == 10000000


@pytest.mark.parametrize("field", ["demand", "depot", "overflow", "small"])
def test_unsupported_inputs_fail_closed(tmp_path, field):
    inst = instance(5 if field == "small" else 25)
    if field == "demand":
        inst.demands[1] = 1.5
    elif field == "depot":
        inst.service_times[0] = 1
    elif field == "overflow":
        inst.dist *= 1e10
    with pytest.raises(ValueError):
        baseline.write_problem(tmp_path / "instance.vrp", inst, inst.n)


@pytest.mark.parametrize("expires_during_validation", [False, True])
def test_late_tour_cannot_replace_incumbent(monkeypatch, tmp_path, expires_during_validation):
    solver = baseline.NeuroLKHSolver.__new__(baseline.NeuroLKHSolver)
    solver.inst = instance()
    solver._deadline, solver._start = 1.0, 0.0
    solver._best_plan, solver._best_key = None, (np.inf, np.inf)
    solver.trajectory_log = []
    solver.diagnostics = {"invalid_original_tours": 0}
    clock = SimpleNamespace(now=0.0 if expires_during_validation else 2.0)
    monkeypatch.setattr(baseline, "time", SimpleNamespace(perf_counter=lambda: clock.now))
    tour = tmp_path / "tour.txt"
    tour.write_text("DIMENSION : 26\nTOUR_SECTION\n" + "\n".join(map(str, range(1, 27))) + "\n-1\nEOF\n")

    def plan(*args):
        clock.now = 2.0
        return SimpleNamespace(feasible=True, cost=1.0, nv=1)

    monkeypatch.setattr(baseline, "Plan", plan)
    solver._capture_tour(tour, vehicles=1)
    assert solver._best_plan is None


def test_parameters_forward_actual_seed_and_disable_iteration_cap(tmp_path):
    path = tmp_path / "solver.par"
    baseline.write_parameters(path, seed=47)
    text = path.read_text()
    assert "SEED = 47\n" in text
    assert "PRECISION = 1\n" in text and "MAX_TRIALS = 2147483647\n" in text
    assert "STOP_AT_OPTIMUM = NO\n" in text and "MTSP_MIN_SIZE = 0\n" in text
    assert "CANDIDATE_FILE = candidates.txt\n" in text
    assert "INITIAL_TOUR_FILE" not in text


@pytest.mark.skipif(not (ASSETS / "assets.json").exists(), reason="requires separately prepared NeuroLKH assets")
def test_real_cpu_inference_search_and_fleet_first_restart(tmp_path):
    import torch

    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        inst = instance()
        reference = Plan([list(range(1, 26))], inst)
        assert reference.cost > 0
        solver = baseline.NeuroLKHSolver(
            inst, Config(time_limit=1.0, neurolkh_root=str(ASSETS), output_dir=str(tmp_path))
        )
        plan, _ = solver.solve(seed=47)
        assert plan.feasible and sorted(node for route in plan.routes for node in route) == list(range(1, 26))
        assert solver.diagnostics["seed"] == 47 and solver.diagnostics["inference_sec"] > 0
        assert solver.diagnostics["incumbent_capture_sec"] < 1.0
        assert solver.diagnostics["assets"]["checkpoint_sha256"] == baseline.CHECKPOINT_SHA256
        assert all("SEED = 47\n" in p.read_text() for p in tmp_path.glob("neurolkh/stage_*/solver.par"))
        assert solver.time_limit_hit
    finally:
        torch.set_num_threads(previous)


def test_unified_cli_config_has_no_hybrid_components():
    cls, cfg = cli.get_solver_and_config("neurolkh", 1.5, seed=47)
    assert cls is baseline.NeuroLKHSolver and cfg.time_limit == 1.5


@pytest.mark.parametrize("extra", [[], ["--gnn-model", "unused.pt"], ["--budget-mode", "capped"]])
def test_cli_rejects_missing_assets_or_conflicting_modes(monkeypatch, tmp_path, extra):
    path, out = tmp_path / "instance.txt", tmp_path / "out.json"
    path.write_text("fixture")
    monkeypatch.setattr(
        sys,
        "argv",
        ["benchmark.py", "--instance", str(path), "--ablation", "neurolkh", *extra, "--output-json", str(out)],
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2 and not out.exists()


def test_cli_keeps_backend_artifacts_on_failure(monkeypatch, tmp_path):
    inst = instance()
    path, out = tmp_path / "instance.txt", tmp_path / "out.json"
    path.write_text("fixture")
    monkeypatch.setattr(cli, "load_solomon_instance", lambda path: inst)

    def init(solver, inst, cfg):
        solver.inst, solver.cfg, solver.diagnostics = inst, cfg, {"seed": 47}

    def solve(solver, seed=None):
        artifacts = Path(solver.cfg.output_dir) / "neurolkh"
        artifacts.mkdir()
        (artifacts / "backend.log").write_text("failure fixture")
        raise baseline.NeuroLKHNoSolutionError("no timely incumbent")

    monkeypatch.setattr(baseline.NeuroLKHSolver, "__init__", init)
    monkeypatch.setattr(baseline.NeuroLKHSolver, "solve", solve)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark.py",
            "--instance",
            str(path),
            "--ablation",
            "neurolkh",
            "--neurolkh-root",
            str(tmp_path),
            "--output-json",
            str(out),
        ],
    )
    assert cli.main() == 1
    payload = json.loads(out.read_text())
    assert payload["adapter"]["seed"] == 47
    assert (out.with_suffix(".backend") / "backend.log").read_text() == "failure fixture"
