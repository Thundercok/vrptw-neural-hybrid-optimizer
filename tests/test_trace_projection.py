from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from vrptw.phase_trace import PhaseTrace

ROOT = Path(__file__).resolve().parents[1]


def auditor():
    spec = importlib.util.spec_from_file_location("kernel_audit", ROOT / "scripts/audit_kernel_timing.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def raw_trace(path):
    clock = SimpleNamespace(now=109.0)
    t = PhaseTrace(SimpleNamespace(_t_start=100.0, _deadline=110.0), clock=lambda: clock.now)

    def solve():
        t.call("child", lambda: setattr(clock, "now", 111.0))

    t.call("solve", solve)
    for name in ("plan.cost", "plan.feasible", "plan.feasible", "plan.cost"):
        t.call(name, lambda: setattr(clock, "now", clock.now + 0.1))
    t.write(path)


def test_projection_preserves_raw_bytes_and_audits_original_solve_subtree(tmp_path):
    source, target = tmp_path / "raw.csv", tmp_path / "solve.csv"
    raw_trace(source)
    before = source.read_bytes()
    report = auditor().project_solve_trace(source, target)
    assert source.read_bytes() == before
    assert report["audit"]["spans"] == 2 and report["audit"]["post_cutoff_sec"] == 1
    assert [row["name"] for row in report["excluded_spans"]] == [
        "plan.cost",
        "plan.feasible",
        "plan.feasible",
        "plan.cost",
    ]
    assert list(csv.DictReader(target.open())) == list(csv.DictReader(source.open()))[:2]
    with pytest.raises(FileExistsError):
        auditor().project_solve_trace(source, target)


@pytest.mark.parametrize("tamper", ["overlap", "name", "clock", "arithmetic", "ids", "child", "outcome"])
def test_projection_rejects_unexplained_or_corrupt_extra_roots(tmp_path, tamper):
    source, target = tmp_path / "raw.csv", tmp_path / "solve.csv"
    raw_trace(source)
    rows = list(csv.DictReader(source.open()))
    if tamper == "overlap":
        rows[2]["start_perf"] = "109.5"
    elif tamper == "name":
        rows[2]["name"] = "hidden_search"
    elif tamper == "clock":
        rows[2]["solve_deadline_perf"] = "111"
    elif tamper == "arithmetic":
        rows[2]["post_cutoff_exclusive_sec"] = "99"
    elif tamper == "ids":
        rows[2]["id"] = "99"
    elif tamper == "child":
        rows[3]["parent_id"] = rows[2]["id"]
    else:
        rows[2]["outcome"] = "ValueError"
    with source.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError):
        auditor().project_solve_trace(source, target)
