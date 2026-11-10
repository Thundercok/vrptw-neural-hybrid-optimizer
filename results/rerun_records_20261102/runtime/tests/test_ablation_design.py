"""Planning invariants; no benchmark solver is run by the preparation tool."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ablation_design", ROOT / "scripts/prepare_ablation_design.py")
design = importlib.util.module_from_spec(spec)
spec.loader.exec_module(design)


def inputs():
    records = []
    ranges = [("C1", 9), ("C2", 8), ("R1", 12), ("R2", 11), ("RC1", 8), ("RC2", 8)]
    for family, count in ranges:
        for i in range(1, count + 1):
            records.append({"name": f"{family}{i:02}", "customers": 100})
    for family, _ in ranges:
        records.extend({"name": f"{family}_2_{i}", "customers": 200} for i in (1, 5))
        records.append({"name": f"{family}_4_1", "customers": 400})
    for r in records:
        r.update(path=f"data/{r['name']}.txt", sha256="0" * 64, geometry_sha256="1" * 64)
    return records


def test_cases_cover_six_individual_effects_at_both_anchors_and_the_bundle_factorial():
    cells = design.build_cells()
    assert len(cells) == 16 and len({tuple(c["levels"]) for c in cells.values()}) == 16
    for levels in [(0,) * 6, (1,) * 6, (1, 1, 0, 0, 0, 0), (0, 0, 1, 1, 1, 1)]:
        assert "F" + "".join(map(str, levels)) in cells
    contrasts = design.build_contrasts(cells)
    assert len(contrasts) == 17
    assert sum(c["role"] == "primary_ablation_300s" for c in contrasts) == 8
    for c in contrasts:
        assert set(c["weights"]) <= cells.keys() and sum(c["weights"].values()) == 0
        if c.get("factor"):
            left, right = [cells[key]["levels"] for key in c["weights"]]
            differences = [i for i, (a, b) in enumerate(zip(left, right)) if a != b]
            assert differences == [design.FACTORS.index(c["factor"])]


def test_rank_guard_prevents_claiming_all_pairwise_interactions_are_identified():
    cells = design.build_cells()
    terms = [()] + [(i,) for i in range(6)] + list(combinations(range(6), 2))
    matrix = np.array([[np.prod([2 * c["levels"][j] - 1 for j in term]) for term in terms] for c in cells.values()])
    ranks = design.design_ranks(cells)
    assert ranks["anchored16"]["rank"] == np.linalg.matrix_rank(matrix) == 14
    assert ranks["anchored16"]["columns"] == 22
    assert ranks["anchored16"]["all_pairwise_identified"] is False
    assert ranks["half32"]["rank"] == ranks["full64"]["rank"] == 22


def test_jobs_are_independent_by_cutoff_unique_and_shared_full_cells_are_not_rerun():
    jobs = design.make_jobs(inputs(), design.build_cells())
    keys = [(j["instance"], j["seed"], j["cutoff_sec"], j["case_id"]) for j in jobs]
    assert len(keys) == len(set(keys)) == 8620
    assert {j["cutoff_sec"] for j in jobs} == {10, 60, 300, 900}
    shared = [j for j in jobs if set(j["uses"]) == {"primary", "ablation"}]
    assert len(shared) == 180 and {j["case_id"] for j in shared} == {"F111111"}
    assert all(j["independent_cold_start"] for j in jobs)
    assert all(j["execution_binding"] is None for j in jobs)
    ablation = [j for j in jobs if "ablation" in j["uses"]]
    assert len({j["instance"] for j in ablation}) == 18
    assert {j["cutoff_sec"] for j in ablation} == {60, 300}
    assert design.compute_budget(jobs)["nominal_solve_seconds"] == 2365600


def test_job_order_is_repeatable_and_balanced_within_each_block_size():
    cells = design.build_cells()
    jobs = design.make_jobs(inputs(), cells, order_seed=20261019)
    assert jobs == design.make_jobs(inputs(), cells, order_seed=20261019)
    assert jobs != design.make_jobs(inputs(), cells, order_seed=20261020)
    blocks = defaultdict(list)
    for job in jobs:
        blocks[job["block"]].append(job)
    counts = defaultdict(Counter)
    for block in blocks.values():
        assert len(block) in (4, 19)
        assert [j["position"] for j in block] == list(range(len(block)))
        for j in block:
            counts[len(block), j["case_id"]][j["position"]] += 1
    for (size, _), positions in counts.items():
        values = [positions[i] for i in range(size)]
        assert max(values) - min(values) <= 1


@pytest.mark.parametrize("defect", ["duplicate", "missing", "wrong_scale"])
def test_incomplete_or_ambiguous_test_selection_is_rejected(defect):
    records = inputs()
    if defect == "duplicate":
        records[-1] = records[0]
    elif defect == "missing":
        records.pop()
    else:
        records[0]["customers"] = 400
    with pytest.raises(ValueError):
        design.make_jobs(records, design.build_cells())


@pytest.mark.parametrize("defect", ["hash", "outside", "duplicate"])
def test_manifest_loader_checks_actual_input_identity_before_planning(tmp_path, defect):
    data = tmp_path / "data.txt"
    data.write_bytes(b"fixture")
    record = {
        "name": "C101",
        "customers": 100,
        "path": "data.txt",
        "sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
        "geometry_sha256": "1" * 64,
    }
    if defect == "hash":
        record["sha256"] = "0" * 64
    elif defect == "outside":
        record["path"] = "../outside.txt"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"splits": {"test": [record] * (2 if defect == "duplicate" else 1)}}))
    with pytest.raises(ValueError):
        design.load_inputs(manifest, tmp_path)


def test_switch_audit_is_read_only_and_never_runs_a_solver(monkeypatch):
    from vrptw.solvers import ALNSSolver, HybridDDQNSolver

    def forbidden(*a, **kw):
        pytest.fail("planning must not call a solver")

    monkeypatch.setattr(ALNSSolver, "solve", forbidden)
    monkeypatch.setattr(HybridDDQNSolver, "solve", forbidden)
    audit = design.audit_switches(ROOT)
    assert audit["solver_calls"] == 0
    assert audit["launch_ready"] is False
    ids = {f["id"] for f in audit["findings"]}
    assert {"alns_aliases", "explicit_gnn"} <= ids
    assert ids.isdisjoint({"sp_off_leak", "split_off_leak", "macro_confound", "gec_scope", "controller_composition"})
    assert len(audit["factor_bindings"]) == 16
    assert all(b["solver_class"] == "AblationHybridSolver" for b in audit["factor_bindings"].values())
    assert audit["sp_disabled_stub_dispatches"] == 0
    assert any(c["callee"] == "self.split_ctrl.try_split" for c in audit["call_sites"])


def test_existing_output_is_refused_before_loading_or_mutating_anything(monkeypatch, tmp_path):
    sentinel = tmp_path / "preserve.txt"
    sentinel.write_bytes(b"preserve")
    monkeypatch.setattr(design, "load_inputs", lambda *a: pytest.fail("output check must happen first"))
    with pytest.raises(FileExistsError):
        design.prepare(tmp_path)
    assert sentinel.read_bytes() == b"preserve"


def test_tool_has_no_execution_mode(monkeypatch):
    monkeypatch.setattr("sys.argv", ["prepare", "--output-dir", "unused", "--launch"])
    with pytest.raises(SystemExit) as error:
        design.main()
    assert error.value.code == 2


def fixture_repository(tmp_path, monkeypatch):
    manifest = tmp_path / "results/gnn_retraining_20261017/manifest.json"
    manifest.parent.mkdir(parents=True)
    records = inputs()
    for r in records:
        path = tmp_path / r["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(r["name"])
        r["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        r["path"] = "../../" + r["path"]
    manifest.write_text(json.dumps({"splits": {"test": records}}))
    model = tmp_path / "model.pt"
    model.write_bytes(b"fixture weights, not loaded")
    monkeypatch.setattr(design, "MODEL", "model.pt")
    monkeypatch.setattr(design, "MODEL_SHA256", hashlib.sha256(model.read_bytes()).hexdigest())
    source = tmp_path / "src/vrptw/example.py"
    source.parent.mkdir(parents=True)
    source.write_text("# initial source\n")
    return manifest, model, source


@pytest.mark.parametrize("changed", ["input", "manifest", "model", "source"])
def test_identity_drift_during_audit_prevents_a_frozen_design(monkeypatch, tmp_path, changed):
    manifest, model, source = fixture_repository(tmp_path, monkeypatch)
    paths = {"input": tmp_path / "data/C101.txt", "manifest": manifest, "model": model, "source": source}

    def audit(root):
        paths[changed].write_bytes(paths[changed].read_bytes() + b"\n")
        return {"findings": [], "launch_ready": False, "solver_calls": 0}

    monkeypatch.setattr(design, "audit_switches", audit)
    with pytest.raises(RuntimeError, match="identity drift"):
        design.prepare(tmp_path / "out", root=tmp_path)
    assert not (tmp_path / "out").exists()


def test_preparation_writes_a_sealed_blocked_plan_without_self_hashing(monkeypatch, tmp_path):
    fixture_repository(tmp_path, monkeypatch)
    monkeypatch.setattr(
        design, "audit_switches", lambda root: {"findings": [], "launch_ready": False, "solver_calls": 0}
    )
    out = tmp_path / "out"
    plan = design.prepare(out, root=tmp_path)
    assert plan["launch_ready"] is False and plan["solver_calls"] == 0
    assert len((out / "jobs.jsonl").read_text().splitlines()) == 8620
    hashes = json.loads((out / "artifact_hashes.json").read_text())
    assert "artifact_hashes.json" not in hashes
    assert all(hashlib.sha256((out / p).read_bytes()).hexdigest() == h for p, h in hashes.items())
