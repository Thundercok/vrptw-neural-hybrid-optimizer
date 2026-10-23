from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from vrptw import Config
from vrptw import benchmark_suite as suite


@pytest.mark.parametrize("has_solution", [False, True])
def test_ortools_task_uses_config_and_unpacks_solver_result(monkeypatch, has_solution):
    inst = SimpleNamespace(name="C101", n=100)
    plan = SimpleNamespace(feasible=True, nv=10, cost=828.94) if has_solution else None
    cfg = Config(ortools_time_limit=0.1, seed=42)
    monkeypatch.setattr(suite, "load_solomon_instance", lambda path: inst)

    def solve(actual_inst, actual_cfg):
        assert actual_inst is inst
        assert isinstance(actual_cfg, Config)
        assert actual_cfg.ortools_time_limit == 0.1
        assert actual_cfg.seed == 47
        assert Path(actual_cfg.output_dir).is_dir()
        assert actual_cfg.output_dir != cfg.output_dir
        return plan, 0.1

    monkeypatch.setattr(suite, "run_ortools", solve)
    task = suite.BenchmarkTask("C101", "unused.txt", "OR-Tools", 47, cfg)
    result = suite.execute_benchmark_task(task)
    assert result.feasible is has_solution
    assert result.nv == (10 if has_solution else 999)
    assert cfg.seed == 42
