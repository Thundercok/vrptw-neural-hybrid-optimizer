from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def api():
    spec = importlib.util.spec_from_file_location("sweep_analysis", ROOT / "scripts/analyze_sweep.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_plan():
    design = json.loads((ROOT / "results/ablation_design_20261019/design.json").read_text())
    design.update(input_count=3, ablation_instances=["a", "b", "c"])
    return {
        "design": design,
        "contrasts": json.loads((ROOT / "results/ablation_design_20261019/contrasts.json").read_text()),
        "metadata": {
            name: {"customers": size, "geometry_sha256": "g" + str(size)}
            for name, size in zip("abc", (100, 200, 400), strict=True)
        },
        "source_sha256": "synthetic",
        "manifest_sha256": "synthetic",
    }


def write_fixture(m, path, plan):
    rows = []
    for name, case, seed, cutoff in sorted(m.expected_keys(plan)):
        meta = plan["metadata"][name]
        available = not (case == "NeuroLKH-adapted" and seed == 44)
        rows.append(
            {
                "instance": name,
                "case_id": case,
                "seed": seed,
                "cutoff_sec": cutoff,
                **meta,
                "available": available,
                "nv": 1 if available else None,
                "td": 90.0 if case == "F111111" else 100.0 if available else None,
                "integrity_ok": True,
                "binding_ok": available,
                "return_ok": True,
            }
        )
        if not available:
            rows[-1]["td"] = None
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_csv_replay_uses_registered_families_and_all_shared_draws(tmp_path):
    m = api()
    plan = fixture_plan()
    source = tmp_path / "input.csv"
    write_fixture(m, source, plan)
    out = tmp_path / "analysis"
    report = m.write_analysis(out, source, plan, {"fixture_only": True}, replicates=32)
    assert report["fixture_only"] is True and report["analysis_count"] == 46
    assert len(list(csv.DictReader((out / "bootstrap_draws.csv").open()))) == 32
    index = json.loads((out / "analysis_index.json").read_text())
    assert sum(r["family_size"] == 3 for r in index) == 3
    assert sum(r["family_size"] == 8 for r in index) == 8
    intervals = list(csv.DictReader((out / "intervals.csv").open()))
    chosen = next(r for r in intervals if r["metric"] == "fleet_score" and r["family_size"] == "3")
    samples = [
        float(r["fleet_score"])
        for r in csv.DictReader((out / "bootstrap.csv").open())
        if r["analysis_id"] == chosen["analysis_id"]
    ]
    expected = np.quantile(samples, [0.025 / 3, 1 - 0.025 / 3])
    assert [float(chosen["lower"]), float(chosen["upper"])] == pytest.approx(expected)
    assert report["csv_hashes"]["bootstrap.csv"] == m.sweep.sha256(out / "bootstrap.csv")


@pytest.mark.parametrize("defect", ["missing", "duplicate", "protocol"])
def test_analysis_refuses_incomplete_or_invalid_matrix(tmp_path, defect):
    m = api()
    plan = fixture_plan()
    source = tmp_path / "input.csv"
    write_fixture(m, source, plan)
    rows = list(csv.DictReader(source.open()))
    fields = list(rows[0])
    if defect == "missing":
        rows.pop()
    elif defect == "duplicate":
        rows.append(rows[0])
    else:
        rows[0]["integrity_ok"] = "False"
    with source.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError):
        m.write_analysis(tmp_path / "out", source, plan, {"fixture_only": True}, replicates=5)


def test_analysis_collision_never_overwrites_prior_files(tmp_path):
    m = api()
    (tmp_path / "keep").write_text("old")
    with pytest.raises(FileExistsError):
        m.write_analysis(tmp_path, tmp_path / "missing", fixture_plan(), {"fixture_only": True})
    assert (tmp_path / "keep").read_text() == "old"


def test_main_requires_completed_audited_transactions_before_analysis(tmp_path, monkeypatch):
    m = api()

    def reject(*args, **kwargs):
        assert kwargs["require_complete"]
        raise ValueError("incomplete")

    monkeypatch.setattr(m.sweep, "audit", reject)
    monkeypatch.setattr(m, "write_analysis", lambda *a, **kw: pytest.fail("analysis ran before full audit"))
    with pytest.raises(ValueError):
        m.main(["--run-dir", str(tmp_path), "--output-dir", str(tmp_path / "new")])
