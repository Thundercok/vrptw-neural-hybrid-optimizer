from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SEEDS = [42, 43, 44, 45, 46]
FIELDS = [
    "run", "stage", "instance", "case_id", "seed", "cutoff_sec", "available", "nv", "td", "captured_sec",
    "runtime_sec", "end_to_end_wall_sec", "power", "battery", "load1", "clock_gap_sec", "phases", "errors",
]


def api():
    spec = importlib.util.spec_from_file_location("ges_rerun", ROOT / "scripts/analyze_ges_rerun.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


METADATA = {
    name: {"customers": size, "geometry_sha256": geometry}
    for name, size, geometry in [
        ("C101", 100, "a"), ("R101", 100, "b"), ("C1_2_1", 200, "c"), ("R1_2_1", 200, "d"),
        ("C1_4_1", 400, "e"), ("R1_4_1", 400, "f"),
    ]
}
NAMES = sorted(METADATA)
WEIGHTS = {100: 1 / 3, 200: 1 / 3, 400: 1 / 3}


def cell(stage, instance, case, seed, cutoff=300, nv=10, td=1000.0, **over):
    return {
        "stage": stage, "instance": instance, "case_id": case, "seed": seed, "cutoff_sec": cutoff,
        **METADATA[instance], "available": True, "nv": nv, "td": td, "integrity_ok": True, "return_ok": True,
        "binding_ok": True, "load1": 5.0, "power": "AC", "phases": "search", "errors": [], **over,
    }


def t300_cells(m, ges_nv=10):
    return [
        cell("primary_t300", name, case, seed, nv=ges_nv if case == m.GES else 10)
        for name in NAMES for case in m.T300_ARMS for seed in SEEDS
    ]


def primary(m, cells, closed=("primary_t300",)):
    draws = m.stats.make_draws(METADATA, SEEDS, 200, 20261019)
    return m.analyze_primary(cells, METADATA, NAMES, SEEDS, draws, WEIGHTS, set(closed))


def write_records(path, rows):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows({**dict.fromkeys(FIELDS, ""), **r} for r in rows)


def record(**over):
    base = {
        "run": "C101_F111111_s42_t300", "stage": "primary_t300", "instance": "C101", "case_id": "F111111", "seed": 42,
        "cutoff_sec": 300, "available": "True", "nv": 10, "td": 828.9, "runtime_sec": 300.1, "power": "AC",
        "load1": 5.0, "clock_gap_sec": 0.1, "phases": "search", "errors": "[]",
    }
    return {**base, **over}


def test_a_stage_closes_only_when_a_later_one_starts(tmp_path):
    m = api()
    log = tmp_path / "sweep.log"
    log.write_text('{"stage_start": "primary_t300"}\n{"job": "x"}\n{"stage_start": "primary_t300"}\n')
    assert m.closed_stages(log, False) == set()
    log.write_text('{"stage_start": "primary_t300"}\n{"stage_start": "primary_t60"}\n')
    assert m.closed_stages(log, False) == {"primary_t300"}
    log.write_text('{"stage_start": "primary_t900"}\n')
    assert "primary_t900" not in m.closed_stages(log, False)
    assert "primary_t900" in m.closed_stages(log, True)


def test_no_result_is_computed_before_t300_closes():
    m = api()
    results, decision = primary(m, t300_cells(m, ges_nv=9), closed=())
    assert results == [] and decision is None
    assert "no result" in m.report(decision, results, {}, set())


def test_adoption_follows_the_lower_bound_and_sets_the_family():
    m = api()
    results, decision = primary(m, t300_cells(m, ges_nv=9))
    assert decision["ges_adopted"] and decision["proposed"] == m.GES
    assert results[0]["analysis"] == "adoption_rule"
    family = m.comparison_rows(results, "primary")
    assert {(r["treatment"], r["control"]) for r in family} == {
        (m.GES, m.ALNS_GES), (m.GES, m.PYVRP), (m.GES, m.NEUROLKH),
    }
    assert all(r["intervals"]["fleet_score"]["family_size"] == 3 for r in family)


def test_a_tie_keeps_the_blind_configuration():
    m = api()
    results, decision = primary(m, t300_cells(m, ges_nv=10))
    assert not decision["ges_adopted"] and decision["proposed"] == m.BLIND
    assert {(r["treatment"], r["control"]) for r in m.comparison_rows(results, "primary")} == {
        (m.BLIND, m.ALNS_NOGES), (m.BLIND, m.PYVRP), (m.BLIND, m.NEUROLKH),
    }


def test_adoption_uses_the_registered_98_75_percent_interval():
    m = api()
    results, _ = primary(m, t300_cells(m, ges_nv=9))
    assert results[0]["intervals"]["fleet_score"]["level"] == pytest.approx(0.9875)


def test_missing_cell_is_a_gap_not_a_loss():
    m = api()
    cells = [c for c in t300_cells(m, ges_nv=9) if not (c["instance"] == "C101" and c["case_id"] == m.PYVRP and c["seed"] == 42)]
    results, decision = primary(m, cells)
    assert decision["t300_gaps"] == 1
    row = next(r for r in m.comparison_rows(results, "primary") if r["control"] == m.PYVRP)
    assert row["seed_pairs_used"] == row["seed_pairs_total"] - 1


def test_no_solution_counts_against_its_case():
    m = api()
    cells = t300_cells(m)
    for c in cells:
        if c["instance"] == "R101" and c["case_id"] == m.PYVRP and c["seed"] == 43:
            c.update(available=False, nv=None, td=None, binding_ok=False)
    results, _ = primary(m, cells)
    row = next(r for r in m.comparison_rows(results, "primary") if r["control"] == m.PYVRP)
    assert row["control_no_solution"] == 1 and row["seed_wins"] == 1


def test_load_sensitivity_drops_whole_blocks():
    m = api()
    cells = t300_cells(m)
    for c in cells:
        if c["instance"] == "C101" and c["seed"] == 44 and c["case_id"] == m.PYVRP:
            c["load1"] = 9.0
    results, decision = primary(m, cells)
    assert decision["high_load_blocks"] == 1
    row = m.comparison_rows(results, "primary_load_sensitivity")[0]
    assert row["seed_pairs_used"] == row["seed_pairs_total"] - 1


def test_comparisons_stay_inside_the_rerun():
    m = api()
    results, _ = primary(m, t300_cells(m))
    assert all("closed" not in r["treatment"] and "closed" not in r["control"] for r in results)
    assert not hasattr(m, "SWEEP")


def test_load_cells_skips_anchors_and_rejects_bad_cells(tmp_path):
    m = api()
    path = tmp_path / "records.csv"
    write_records(path, [record(), record(run="C101_PyVRP-ILS_s42_t60_anchor_start", stage="anchor_start", cutoff_sec=60)])
    assert len(m.load_cells(path, METADATA)) == 1
    write_records(path, [record(errors=json.dumps(["certificate hash mismatch"]), available="False")])
    with pytest.raises(ValueError, match="integrity"):
        m.load_cells(path, METADATA)
    write_records(path, [record(clock_gap_sec=400.0)])
    with pytest.raises(ValueError, match="frozen"):
        m.load_cells(path, METADATA)


def test_load_cells_treats_an_invalid_cell_as_no_solution(tmp_path):
    m = api()
    path = tmp_path / "records.csv"
    errors = json.dumps(["certificate not captured before cutoff"])
    write_records(path, [record(errors=errors, available="False", nv=10, td=900.0)])
    row = m.load_cells(path, METADATA)[0]
    assert row["available"] is False and row["nv"] is None and row["td"] is None


def test_same_key_in_primary_and_ablation_stages_stays_separate():
    m = api()
    cells = t300_cells(m) + [cell("ablation_t300", name, m.GES, seed, nv=99) for name in NAMES for seed in SEEDS]
    rows, gaps = m.stage_rows(cells, "primary_t300", NAMES, m.T300_ARMS, SEEDS, METADATA)
    assert not gaps and all(r["nv"] == 10 for r in rows)


def test_family_of_handles_both_naming_schemes():
    m = api()
    assert [m.family_of(n) for n in ("C101", "R208", "RC105", "C1_2_1", "RC2_4_1", "R1_2_5")] == [
        "C1", "R2", "RC1", "C1", "RC2", "R1",
    ]


def test_family_table_counts_fleet_and_matched_gap():
    m = api()
    cells = [
        cell("primary_t300", "C101", m.GES, 42, nv=9), cell("primary_t300", "C101", m.PYVRP, 42, nv=10),
        cell("primary_t300", "R101", m.GES, 42, td=990.0), cell("primary_t300", "R101", m.PYVRP, 42, td=1000.0),
    ]
    rows = {r["family"]: r for r in m.family_table(cells, m.GES, (m.PYVRP,), 300, "primary_t300", {"primary_t300"})}
    assert rows["C1"]["fewer"] == 1 and rows["C1"]["matched_td_gap_pct"] is None
    assert rows["R1"]["same"] == 1 and rows["R1"]["matched_td_gap_pct"] == pytest.approx(-1.0)


def test_latex_reports_undefined_intervals_and_losses():
    m = api()
    results, _ = primary(m, t300_cells(m, ges_nv=10))
    row = m.comparison_rows(results, "primary")[0]
    row["td_pct"] = 0.5
    row["intervals"]["td_pct"] = {"lower": None, "upper": None, "suppressed": True}
    assert "(undefined)" in m.fmt_interval(row, "td_pct", 2)
    row["td_pct"] = None
    assert m.fmt_interval(row, "td_pct", 2) == "---"


def test_ablation_stage_uses_its_own_cells_and_the_primary_family():
    m = api()
    contrasts = [
        {"id": "Micro_full_context", "role": "primary_ablation_300s", "weights": {"F111111": 1, "F111011": -1}},
        {"id": "Micro_bare", "role": "exploratory", "weights": {"F000100": 1, "F000000": -1}},
        {
            "id": "bundle_interaction",
            "role": "exploratory_complete_NV_only",
            "weights": {"F111111": 1, "F110000": -1, "F001111": -1, "F000000": 1},
        },
    ]
    cases = {case for c in contrasts for case in c["weights"]}
    cells = [cell("primary_t300", name, "F111111", seed, nv=99) for name in NAMES for seed in SEEDS]
    cells += [
        cell("ablation_t300", name, case, seed, nv=9 if case == "F111111" else 10)
        for name in NAMES for case in cases for seed in SEEDS
    ]
    draws = m.stats.make_draws(METADATA, SEEDS, 200, 20261019)
    design = {"ablation_instances": NAMES}
    results = m.analyze_ablation(cells, METADATA, design, contrasts, SEEDS, draws, {"ablation_t300"})
    by_id = {r["analysis"]: r for r in results}
    primary_row = by_id["ablation:Micro_full_context"]
    assert primary_row["fleet_score"] == pytest.approx(1.0)
    assert primary_row["intervals"]["fleet_score"]["level"] == pytest.approx(1 - 0.05 / 8)
    assert by_id["ablation:Micro_bare"]["intervals"]["fleet_score"]["level"] == pytest.approx(0.95)
    assert "nv_interaction" in by_id["ablation:bundle_interaction"]["intervals"]
    assert m.latex_contrasts(results).count("\\\\") == 2


def test_other_budgets_are_flagged_when_ges_is_not_adopted():
    m = api()
    cells = t300_cells(m, ges_nv=10)
    cells += [
        cell("primary_t60", name, case, seed, cutoff=60)
        for name in NAMES for case in m.PRIMARY_ARMS for seed in SEEDS
    ]
    results, decision = primary(m, cells, closed=("primary_t300", "primary_t60"))
    budget = [r for r in results if r["analysis"] == "budget"]
    assert not decision["ges_adopted"] and budget
    assert all(r["treatment"] == m.GES and r["proposed_configuration"] is False for r in budget)
    assert {r["cutoff_sec"] for r in budget} == {60}


def test_report_lists_results_and_conditions():
    m = api()
    cells = t300_cells(m, ges_nv=9)
    results, decision = primary(m, cells)
    text = m.report(decision, results, m.run_conditions(cells, {"primary_t300"}), {"primary_t300"})
    assert "GES adopted: True" in text and "Primary family" in text and "power_at_start" in text
