from __future__ import annotations

import inspect
import re
from pathlib import Path

from vrptw import Config, solvers
from vrptw.core import load_solomon_instance

ROOT = Path(__file__).resolve().parents[1]


def _solver(cfg):
    inst = load_solomon_instance(str(ROOT / "data/Solomon/c101.txt"))
    return solvers.HybridDDQNSolver(inst, cfg)


def test_hybrid_reads_bks_only_through_reference_entry():
    source = inspect.getsource(solvers.HybridDDQNSolver)
    assert len(re.findall(r"\bBKS\s*[.\[]", source)) == 1
    assert "BKS.get(self.inst.name)" in inspect.getsource(solvers.HybridDDQNSolver._reference_entry)


def test_reference_blind_hides_the_reference_fleet():
    assert _solver(Config())._reference_entry()["nv"] == 10
    assert _solver(Config(reference_blind=True))._reference_entry() is None


def test_reference_blind_follows_environment(monkeypatch):
    monkeypatch.setenv("VRPTW_REFERENCE_BLIND", "1")
    assert Config().reference_blind is True
    monkeypatch.delenv("VRPTW_REFERENCE_BLIND")
    assert Config().reference_blind is False
