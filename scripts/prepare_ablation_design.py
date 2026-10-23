#!/usr/bin/env python3
"""Prepare a blocked, read-only experiment design. This tool cannot run solvers."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import random
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict
from fractions import Fraction
from itertools import combinations, product
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FACTORS = ("GEC", "SP", "Macro", "Micro", "LAC", "GNN")
FAMILIES = ("C1", "C2", "R1", "R2", "RC1", "RC2")
SEEDS = (42, 43, 44, 45, 46)
CUTOFFS = (10, 60, 300, 900)
ABLATION_CUTOFFS = (60, 300)
PRIMARY_CASES = ("F111111", "ALNS-Base", "PyVRP-ILS", "NeuroLKH-adapted")
MODEL = "results/gnn_retraining_20261017/model_seed42/best.pt"
MODEL_SHA256 = "365de53beba09097d1176a8b102ced8d6d97311f5a3ac82186b116d3290e1b97"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_names():
    names = {f"{f}{i:02}" for f, n in zip(FAMILIES, (9, 8, 12, 11, 8, 8)) for i in range(1, n + 1)}
    return names | {f"{f}_2_{i}" for f in FAMILIES for i in (1, 5)} | {f"{f}_4_1" for f in FAMILIES}


def core_names():
    return {f"{f}01" for f in FAMILIES} | {f"{f}_2_1" for f in FAMILIES} | {f"{f}_4_1" for f in FAMILIES}


def load_inputs(manifest_path, root):
    records, seen = [], set()
    manifest_path, root = manifest_path.resolve(), root.resolve()
    for entry in json.loads(manifest_path.read_text())["splits"]["test"]:
        name = entry["name"].upper()
        path = (manifest_path.parent / entry["path"]).resolve()
        if name in seen or not path.is_relative_to(root):
            raise ValueError(f"Duplicate or out-of-root input: {name}")
        if not path.is_file() or digest(path) != entry["sha256"]:
            raise ValueError(f"Input hash mismatch or missing file: {name}")
        if not re.fullmatch(r"[0-9a-f]{64}", entry["geometry_sha256"]):
            raise ValueError(f"Invalid recorded geometry identity: {name}")
        seen.add(name)
        records.append(
            {
                "name": name,
                "path": str(path.relative_to(root)),
                "customers": entry["customers"],
                "sha256": entry["sha256"],
                "geometry_sha256": entry["geometry_sha256"],
            }
        )
    return sorted(records, key=lambda r: r["name"])


def build_cells():
    levels = {(0,) * 6, (1,) * 6, (1, 1, 0, 0, 0, 0), (0, 0, 1, 1, 1, 1)}
    for i in range(6):
        levels.add(tuple(int(i == j) for j in range(6)))
        levels.add(tuple(int(i != j) for j in range(6)))
    return {"F" + "".join(map(str, bits)): {"levels": list(bits), "execution_binding": None} for bits in sorted(levels)}


def build_contrasts(cells):
    contrasts = []
    for i, factor in enumerate(FACTORS):
        single = "F" + "".join(str(int(i == j)) for j in range(6))
        leave_out = "F" + "".join(str(int(i != j)) for j in range(6))
        for label, on, off, role in (
            ("bare", single, "F000000", "exploratory"),
            ("full_context", "F111111", leave_out, "primary_ablation_300s"),
        ):
            contrasts.append({"id": f"{factor}_{label}", "factor": factor, "weights": {on: 1, off: -1}, "role": role})
    for name, on, off, role in (
        ("heuristic_at_no_learning", "F110000", "F000000", "primary_ablation_300s"),
        ("learning_at_heuristic", "F111111", "F110000", "primary_ablation_300s"),
        ("learning_at_no_heuristic", "F001111", "F000000", "exploratory"),
        ("heuristic_at_learning", "F111111", "F001111", "exploratory"),
    ):
        contrasts.append({"id": name, "weights": {on: 1, off: -1}, "role": role})
    contrasts.append(
        {
            "id": "heuristic_learning_bundle_interaction",
            "role": "exploratory_complete_NV_only",
            "weights": {"F111111": 1, "F110000": -1, "F001111": -1, "F000000": 1},
        }
    )
    if any(not set(c["weights"]).issubset(cells) for c in contrasts):
        raise ValueError("Contrast references an unavailable cell")
    return contrasts


def matrix_rank(rows):
    matrix = [[Fraction(v) for v in row] for row in rows]
    rank = 0
    for column in range(len(matrix[0])):
        pivot = next((i for i in range(rank, len(matrix)) if matrix[i][column]), None)
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        divisor = matrix[rank][column]
        matrix[rank] = [v / divisor for v in matrix[rank]]
        for i in range(rank + 1, len(matrix)):
            multiple = matrix[i][column]
            if multiple:
                matrix[i] = [v - multiple * p for v, p in zip(matrix[i], matrix[rank])]
        rank += 1
        if rank == len(matrix):
            break
    return rank


def design_ranks(cells):
    terms = [()] + [(i,) for i in range(6)] + list(combinations(range(6), 2))
    all_levels = list(product((0, 1), repeat=6))
    half = [bits for bits in all_levels if sum(bits) % 2 == 0]
    loco = [tuple(int(i != j) for j in range(6)) for i in range(6)]
    result = {}
    for name, levels in (
        ("anchored16", [c["levels"] for c in cells.values()]),
        ("half32", half),
        ("half32_plus_loco", sorted(set(half + loco))),
        ("full64", all_levels),
    ):
        rows = []
        for bits in levels:
            row = []
            for term in terms:
                value = 1
                for i in term:
                    value *= 2 * bits[i] - 1
                row.append(value)
            rows.append(row)
        rank = matrix_rank(rows)
        seconds = (
            74 * 5 * 4 * sum(CUTOFFS) + 18 * 5 * len(levels) * sum(ABLATION_CUTOFFS) - 18 * 5 * sum(ABLATION_CUTOFFS)
        )
        result[name] = {
            "cells": len(levels),
            "rank": rank,
            "columns": len(terms),
            "all_pairwise_identified": rank == len(terms),
            "nominal_combined_solve_seconds": seconds,
            "nominal_combined_hours": seconds / 3600,
            "caveat": "Rank concerns the intercept/main/two-factor model only; it does not rule out higher-order interaction aliasing or prove a causal effect.",
        }
    return result


def make_jobs(inputs, cells, order_seed=20261019):
    indexed = {r["name"]: r for r in inputs}
    if len(inputs) != len(indexed) or set(indexed) != expected_names():
        raise ValueError("Expected the exact frozen 74-instance selection with unique IDs")
    for r in inputs:
        expected = 100 if "_" not in r["name"] else 200 if "_2_" in r["name"] else 400
        if r["customers"] != expected:
            raise ValueError(f"Wrong instance size: {r['name']}")
    blocks = [(name, seed, cutoff) for name in sorted(indexed) for seed in SEEDS for cutoff in CUTOFFS]
    rng = random.Random(order_seed)
    rng.shuffle(blocks)
    counters, permutations, jobs = Counter(), {}, []
    for number, (name, seed, cutoff) in enumerate(blocks):
        is_ablation = name in core_names() and cutoff in ABLATION_CUTOFFS
        cases = sorted(set(PRIMARY_CASES) | (set(cells) if is_ablation else set()))
        size = len(cases)
        if size not in permutations:
            permutations[size] = cases[:]
            rng.shuffle(permutations[size])
        order = permutations[size]
        offset = counters[size] % size
        counters[size] += 1
        for position, case in enumerate(order[offset:] + order[:offset]):
            uses = ["primary"] if case in PRIMARY_CASES else []
            if is_ablation and case in cells:
                uses.append("ablation")
            entry = indexed[name]
            jobs.append(
                {
                    "instance": name,
                    "seed": seed,
                    "cutoff_sec": cutoff,
                    "case_id": case,
                    "uses": uses,
                    "block": number,
                    "position": position,
                    "input_sha256": entry["sha256"],
                    "geometry_sha256": entry["geometry_sha256"],
                    "independent_cold_start": True,
                    "execution_binding": None,
                }
            )
    return jobs


def compute_budget(jobs):
    seconds = sum(j["cutoff_sec"] for j in jobs)
    return {
        "physical_jobs": len(jobs),
        "nominal_solve_seconds": seconds,
        "nominal_solve_hours": seconds / 3600,
        "excludes": "Imports, model loading, process start/cleanup, audits, failed pilots, host contention and overruns; not an elapsed-time forecast.",
    }


def call_sites(path):
    tree, found = ast.parse(path.read_text()), []
    targets = {
        "self._recombine_with_pool",
        "self._try_gec_route_reduction",
        "self.split_ctrl.try_split",
        "_ejection_chain_eliminate",
        "_buffered_route_elimination",
        "_iterative_route_elimination",
    }

    def visit(node, scope="", guards=()):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scope = node.name
        if isinstance(node, (ast.If, ast.IfExp)):
            test = ast.unparse(node.test)
            visit(node.test, scope, guards)
            body = node.body if isinstance(node, ast.If) else [node.body]
            other = node.orelse if isinstance(node, ast.If) else [node.orelse]
            for item in body:
                visit(item, scope, (*guards, test))
            for item in other:
                visit(item, scope, (*guards, f"not ({test})"))
            return
        if isinstance(node, ast.Call) and ast.unparse(node.func) in targets:
            found.append(
                {
                    "function": scope,
                    "line": node.lineno,
                    "callee": ast.unparse(node.func),
                    "guards": list(guards),
                    "keywords": {kw.arg: ast.unparse(kw.value) for kw in node.keywords if kw.arg is not None},
                }
            )
        for child in ast.iter_child_nodes(node):
            visit(child, scope, guards)

    visit(tree)
    return found


def audit_switches(root):
    # Constructors/config inspection and a stubbed helper dispatch, never solve().
    from vrptw import solvers
    from vrptw.ablation import AblationHybridSolver
    from vrptw.pool import RoutePool

    spec = importlib.util.spec_from_file_location("design_benchmark_cli", root / "scripts/benchmark.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    branches = (
        "alns",
        "gns",
        "gns_pool",
        "gns_pool_lac",
        "micro",
        "full",
        "full_no_macro",
        "full_no_micro",
        "full_no_lac",
        "full_no_pool",
        "full_no_gec",
        "full_no_gnn",
    )
    configs, classes, snapshots = {}, {}, {}
    for branch in branches:
        cls, cfg = cli.get_solver_and_config(branch, 60, seed=42)
        configs[branch], classes[branch] = cfg, cls
        snapshots[branch] = {"solver_class": cls.__name__, "requested_config": asdict(cfg)}
    calls = []
    wrapper = object.__new__(solvers.HybridDDQNSolver)
    wrapper.cfg = configs["full_no_pool"]
    wrapper.cfg.pool_recombine_enabled = False
    marker = object()

    def stub(incumbent, *a, **kw):
        calls.append(True)
        return incumbent

    with patch.object(solvers, "recombine_with_route_pool", stub):
        wrapper._recombine_with_pool(marker, object(), wrapper.cfg)
    pool_settings = []
    for n in (100, 200, 400):
        _, requested = cli.get_solver_and_config("full_no_pool", 60)
        pool = RoutePool(SimpleNamespace(n=n), requested)
        pool_settings.append(
            {
                "customers": n,
                "requested_limit": requested.route_pool_limit,
                "actual_pool_limit": pool.cfg.route_pool_limit,
                "actual_sp_time_limit": pool.cfg.sp_time_limit,
            }
        )
    sites = call_sites(root / "src/vrptw/solvers.py")
    factor_bindings = {}
    binding_classes = []
    for case_id, cell in build_cells().items():
        cls, cfg = cli.get_solver_and_config(
            case_id, 60, seed=42, gnn_model=root / MODEL if cell["levels"][-1] else None
        )
        binding_classes.append(cls)
        factor_bindings[case_id] = {
            "solver_class": cls.__name__,
            "requested_config": asdict(cfg),
            "macro_policy": "ddqn" if cell["levels"][2] else "rule",
            "micro_policy": "ddqn" if cell["levels"][3] else "rule",
        }
    findings = []

    def add(key, detail):
        findings.append({"id": key, "status": "open", "detail": detail})

    if classes["alns"] is classes["gns"] and asdict(configs["alns"]) == asdict(configs["gns"]):
        add(
            "alns_aliases",
            "alns/gns are identical. gns_pool/gns_pool_lac also select ALNSSolver, whose loop has no LAC/SP calls.",
        )
    if calls:
        add(
            "sp_off_leak",
            "Even pool_recombine_enabled=False dispatches the central wrapper to recombination. CLI full_no_pool also leaves periodic/plateau enabled; pool constructor replaces zero capacity.",
        )
    if not configs["full_no_macro"].macro_enabled:
        add(
            "macro_confound",
            "full_no_macro pins DEFAULT and suppresses macro-gated recombination/restarts; it is not a DDQN-versus-rule policy-only contrast.",
        )
    ejection_sites = [s for s in sites if s["callee"] in ("_ejection_chain_eliminate", "_buffered_route_elimination")]
    if (
        getattr(configs["full_no_gec"], "gec_enabled", True)
        or not ejection_sites
        or any(s["keywords"].get("gec_enabled") != "cfg.gec_enabled" for s in ejection_sites)
    ):
        add(
            "gec_scope",
            "Depth=1 only restricts one routine; other ejection-chain/GES paths remain. A global recursive-ejection scope needs tests.",
        )
    split_calls = [c for c in sites if c["callee"] == "self.split_ctrl.try_split"]
    split_source = (root / "src/vrptw/split_controller.py").read_text()
    if (
        any(not any("split_enabled" in guard for guard in c["guards"]) for c in split_calls)
        and "split_enabled" not in split_source
    ):
        add(
            "split_off_leak",
            "The main-loop learned split call and try_split implementation do not consult split_enabled; it can contaminate learning-off cells.",
        )
    if any(cls is not AblationHybridSolver for cls in binding_classes) or any(
        not b["requested_config"]["macro_enabled"] or b["requested_config"]["split_enabled"]
        for b in factor_bindings.values()
    ):
        add("controller_composition", "Factor cells do not use the common independent controller binding.")
    add(
        "explicit_gnn",
        "full alone does not load a GNN. Every GNN-on cell must require the pinned checkpoint; GNN-off must forbid inference and guidance.",
    )
    return {
        "launch_ready": False,
        "solver_calls": 0,
        "scope": "Config/constructor/static-call audit plus stubbed dispatch; not an exhaustive dynamic execution audit.",
        "findings": findings,
        "branches": snapshots,
        "factor_bindings": factor_bindings,
        "sp_disabled_stub_dispatches": len(calls),
        "pool_constructor_settings": pool_settings,
        "call_sites": sites,
    }


def prepare(output, root=ROOT):
    output, root = Path(output).resolve(), root.resolve()
    if output.exists():
        raise FileExistsError(f"Refuse existing design directory: {output}")
    manifest = root / "results/gnn_retraining_20261017/manifest.json"
    manifest_hash = digest(manifest)
    sources = sorted(
        [*root.glob("src/**/*.py"), *root.glob("scripts/**/*.py"), root / "pyproject.toml", root / "uv.lock"]
    )
    sources = [p for p in sources if p.is_file()]
    source_hashes = {str(p.relative_to(root)): digest(p) for p in sources}
    inputs = load_inputs(manifest, root)
    if digest(root / MODEL) != MODEL_SHA256:
        raise ValueError("Frozen GNN checkpoint identity changed")
    pinned = {manifest: manifest_hash, root / MODEL: MODEL_SHA256}
    pinned.update({root / name: value for name, value in source_hashes.items()})
    pinned.update({root / r["path"]: r["sha256"] for r in inputs})

    def assert_identity():
        if any(not path.is_file() or digest(path) != expected for path, expected in pinned.items()):
            raise RuntimeError("Input/model/source identity drift during preparation; preserve any partial artifacts")

    cells = build_cells()
    jobs = make_jobs(inputs, cells)
    audit = audit_switches(root)
    assert_identity()
    groups = defaultdict(set)
    for r in inputs:
        groups[r["customers"]].add(r["geometry_sha256"])
    gates = [f["id"] for f in audit["findings"]] + [
        "new_source_cutoff_validation",
        "baseline_precision_and_representativeness",
        "statistics_implementation_validation",
        "compute_plan_acceptance",
    ]
    plan = {
        "status": "design_frozen_not_executable",
        "launch_ready": False,
        "solver_calls": 0,
        "chosen_design": "anchored16_plus_bundle_2x2",
        "factors": list(FACTORS),
        "seeds": list(SEEDS),
        "primary_cutoffs_sec": list(CUTOFFS),
        "ablation_cutoffs_sec": list(ABLATION_CUTOFFS),
        "primary_cutoff_for_inference_sec": 300,
        "primary_cases": list(PRIMARY_CASES),
        "primary_comparisons": [{"treatment": "F111111", "comparator": c} for c in PRIMARY_CASES[1:]],
        "input_count": len(inputs),
        "ablation_instances": sorted(core_names()),
        "geometry_groups_by_size": {str(k): len(v) for k, v in groups.items()},
        "manifest_sha256": manifest_hash,
        "gnn_checkpoint": MODEL,
        "gnn_checkpoint_sha256": MODEL_SHA256,
        "lac_policy": "sa_or_predictive_v1",
        "order_seed": 20261019,
        "budget": compute_budget(jobs),
        "design_options": design_ranks(cells),
        "open_gates": gates,
        "parameter_selection": "No choices based on pilot objective values; proposed horizons/seeds are protocol settings, not an approved compute allocation.",
        "statistics": {
            "primary_endpoint": "Mean over instances of mean paired-seed feasibility-then-fleet win score (+1 treatment win, -1 loss, 0 tie; both failures separately counted).",
            "distance": "Secondary original-TD gaps only at valid paired-seed matched fleets; report exact denominator. Never compare TD across different fleets.",
            "resampling": "10000 approximate paired cluster-bootstrap replicates, RNG seed 20261019: resample geometry groups within each size, keep all members; resample five seed labels jointly across every algorithm/cutoff in each replicate; retain original size-stratum weights.",
            "multiplicity": "Primary 300s comparisons: 3 simultaneous Bonferroni percentile intervals; ablation 300s: separate family of 8. Other horizons/contrasts descriptive. No p-values computed here.",
            "limitations": "Only 4 geometry groups per size and 5 seed labels: approximate intervals, no power/coverage guarantee. Undefined matched-TD bootstrap draws are retained as undefined; suppress that interval if any draw lacks a denominator. All-failure ties are not quality ties.",
        },
        "failure_policy": "Retain every declared cell. No-solution/known algorithm failures count in availability and paired fleet score. Input/source/config/model integrity errors invalidate protocol inference, never become ordinary solver losses. Pre-cutoff certification and return latency are separate gates; no score-based reruns or cutoff-prefix reuse.",
        "execution_policy": "No executor/commands in this artifact. Fresh process and empty archive per independent cutoff; solve-scope construction/inference/online updates/certification charged; setup/model-load/end-to-end recorded separately; sequential one-thread-requested blocks, no sleep padding. Each future child requests its own initially empty NUMBA_CACHE_DIR; compilation after solve entry is charged; operational validation must include this policy.",
    }
    identity = {
        "source_files": source_hashes,
        "source_sha256": hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest(),
    }
    assert_identity()
    output.mkdir(parents=True, exist_ok=False)
    for name, value in (
        ("design.json", plan),
        ("contrasts.json", build_contrasts(cells)),
        ("input_identity.json", inputs),
        ("switch_audit.json", audit),
        ("source_identity.json", identity),
    ):
        with (output / name).open("x") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
    with (output / "cases.csv").open("x", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["case_id", *FACTORS, "execution_binding"])
        writer.writerows([key, *cell["levels"], "UNIMPLEMENTED"] for key, cell in cells.items())
    with (output / "jobs.jsonl").open("x") as stream:
        for job in jobs:
            stream.write(json.dumps(job) + "\n")
    with zipfile.ZipFile(output / "source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in [*sources, *sorted(root.glob("tests/**/*.py"))]:
            archive.write(path, path.relative_to(root))
    assert_identity()
    hashes = {str(p.relative_to(output)): digest(p) for p in sorted(output.rglob("*")) if p.is_file()}
    with (output / "artifact_hashes.json").open("x") as stream:
        json.dump(hashes, stream, indent=2)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    plan = prepare(args.output_dir)
    print(
        json.dumps(
            {
                "status": plan["status"],
                "launch_ready": plan["launch_ready"],
                "budget": plan["budget"],
                "open_gates": plan["open_gates"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
