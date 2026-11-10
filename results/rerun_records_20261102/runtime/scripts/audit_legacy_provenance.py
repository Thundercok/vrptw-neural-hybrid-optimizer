#!/usr/bin/env python3
"""Read-only audit of legacy publication data; writes only to a new audit folder.

Recomputable CSV arithmetic and Git artifact identity do not certify how the
historical solver executions actually ran. No solver or historical script is
imported/executed, and no manuscript/result file is replaced.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
import math
import re
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = Path("results/ultimate-publication-suite")
ARCHIVE = "research-history-before-cleanup"
STORAGE = "e47b4b77f871a2b6994bd30133400b68bf4c0a53"
COLD_FIX = "08479fbfb607b0cab888920ccf395b858d881b22"
COMBINED_STORAGE = "39a8cfe534d5a7a161df8d035ef33f49faef3024"
FULL = "GNN-Hybrid-DDQN"
BASE = "ALNS-Base"
ROUNDING_TOLERANCE = 0.005051  # 2-decimal summaries, 4-decimal raw costs.


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save_json(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def read_csv(raw):
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))


def write_csv(path, rows):
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def selection(rows):
    solomon = {r["Instance"].upper() for r in rows if re.fullmatch(r"(?:C|R|RC)\d{3}", r["Instance"].upper())}
    families = ("C1", "C2", "R1", "R2", "RC1", "RC2")
    target = solomon | {f"{f}_2_{i}" for f in families for i in (1, 5)} | {f"{f}_4_1" for f in families}
    assert len(solomon) == 56 and len(target) == 74
    return sorted(target)


def objective_summary(records):
    counts = {"wins": 0, "ties": 0, "losses": 0}
    gaps = []
    for base_nv, full_nv, base_td, full_td in records:
        delta = full_nv - base_nv
        key = "wins" if delta < -1e-6 else "losses" if delta > 1e-6 else "ties"
        counts[key] += 1
        if key == "ties":
            gaps.append(100 * (full_td - base_td) / base_td)
    return {
        "instances": sum(counts.values()),
        "fleet": counts,
        "matched": len(gaps),
        "mean_matched_td_gap_pct": statistics.fmean(gaps),
    }


def audit_arithmetic(rows, target):
    bykey = {(row["Instance"].upper(), row["Algorithm"]): row for row in rows}
    assert len(bykey) == len(rows) == 1056, "duplicate or incomplete master rows"
    algorithms = {}
    for algorithm in sorted({row["Algorithm"] for row in rows}):
        subset = [row for row in rows if row["Algorithm"] == algorithm]
        missing = [row for row in subset if not row["NV_mean"] or not row["TD_mean"]]
        errors = {key: [] for key in ("NV_mean", "TD_mean", "NV_std", "TD_std")}
        violations = []
        vector_lengths = collections.Counter()
        for row in subset:
            nv = [float(value) for value in row["raw_nv"].split(";")] if row["raw_nv"] else []
            td = [float(value) for value in row["raw_costs"].split(";")] if row["raw_costs"] else []
            vector_lengths[f"{len(nv)}/{len(td)}"] += 1
            if not nv or not td:
                continue
            assert len(nv) == len(td) == 5
            assert all(math.isfinite(value) for value in nv + td)
            for key, value in (
                ("NV_mean", statistics.fmean(nv)),
                ("TD_mean", statistics.fmean(td)),
                ("NV_std", statistics.pstdev(nv)),
                ("TD_std", statistics.pstdev(td)),
            ):
                error = abs(float(row[key]) - value)
                errors[key].append(error)
                if error > ROUNDING_TOLERANCE:
                    violations.append(
                        {"instance": row["Instance"], "metric": key, "saved": row[key], "recomputed": value}
                    )
        algorithms[algorithm] = {
            "rows": len(subset),
            "missing_objective_rows": len(missing),
            "vector_lengths_nv_td": dict(vector_lengths),
            "zero_reported_time_rows": sum(float(row["Time_s"]) == 0 for row in subset),
            "on_time_field_values": dict(collections.Counter(row["OnTime"] for row in subset)),
            "max_summary_errors": {key: max(values) if values else None for key, values in errors.items()},
            "rounding_violations": violations,
        }
    records, raw_records = [], []
    for name in target:
        base, full = bykey[(name, BASE)], bykey[(name, FULL)]
        records.append(
            tuple(
                float(row[key])
                for row, key in ((base, "NV_mean"), (full, "NV_mean"), (base, "TD_mean"), (full, "TD_mean"))
            )
        )
        raw_records.append(
            tuple(
                statistics.fmean(map(float, row[key].split(";")))
                for row, key in ((base, "raw_nv"), (full, "raw_nv"), (base, "raw_costs"), (full, "raw_costs"))
            )
        )
    summary = objective_summary(records)
    assert summary["fleet"] == {"wins": 23, "ties": 49, "losses": 2} and summary["matched"] == 49
    assert all(not info["rounding_violations"] for info in algorithms.values())
    return {
        "headline_from_printed_summary": summary,
        "headline_from_stored_raw_vectors": objective_summary(raw_records),
        "algorithm_completeness": algorithms,
    }, bykey


def audit_appendix(bykey, target):
    found = {}
    path = ROOT / "docs/supplementary_proofs.tex"
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        cells = [cell.strip() for cell in line.split("&")]
        name = cells[0].replace("\\_", "_").upper()
        if len(cells) != 10 or name not in target:
            continue
        try:
            values = list(map(float, cells[1:7]))
        except ValueError:
            continue
        assert name not in found, f"duplicate appendix benchmark row: {name}"
        found[name] = {
            "line": line_number,
            "base_nv": values[2],
            "base_td": values[3],
            "full_nv": values[4],
            "full_td": values[5],
        }
    assert set(found) == set(target)
    differences = []
    for name in target:
        printed = found[name]
        base, full = bykey[(name, BASE)], bykey[(name, FULL)]
        differences.append(
            {
                "instance": name,
                "appendix_line": printed["line"],
                "csv_base_nv": base["NV_mean"],
                "csv_base_td": base["TD_mean"],
                "appendix_base_nv": printed["base_nv"],
                "appendix_base_td": printed["base_td"],
                "csv_full_nv": full["NV_mean"],
                "csv_full_td": full["TD_mean"],
                "appendix_full_nv": printed["full_nv"],
                "appendix_full_td": printed["full_td"],
                "base_mismatch": abs(printed["base_nv"] - float(base["NV_mean"])) > 1e-6
                or abs(printed["base_td"] - float(base["TD_mean"])) > 0.0051,
                "full_mismatch": abs(printed["full_nv"] - float(full["NV_mean"])) > 1e-6
                or abs(printed["full_td"] - float(full["TD_mean"])) > 0.0051,
            }
        )
    records = [(row["base_nv"], row["full_nv"], row["base_td"], row["full_td"]) for row in found.values()]
    return (
        {
            "printed_appendix_summary": objective_summary(records),
            "full_rows_differing_from_master": sum(row["full_mismatch"] for row in differences),
            "base_rows_differing_from_master": sum(row["base_mismatch"] for row in differences),
        },
        differences,
        found,
    )


def recover(output, ref, path):
    raw = git("show", f"{ref}:{path}")
    dest = output / "recovered" / ref / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    return {
        "ref": ref,
        "path": path,
        "saved_as": str(dest.relative_to(output)),
        "sha256": digest(raw),
        "git_blob": git("rev-parse", f"{ref}:{path}").decode().strip(),
    }


def git_lineage(output, bykey):
    shards, combined = [], []
    for path in sorted((ROOT / SUITE).glob("*/benchmark_checkpoint.csv")):
        name = path.relative_to(ROOT).as_posix()
        raw = path.read_bytes()
        assert raw == git("show", f"{ARCHIVE}:{name}") == git("show", f"{STORAGE}:{name}")
        rows = read_csv(raw)
        assert all(row == bykey[(row["Instance"].upper(), row["Algorithm"])] for row in rows)
        clean_raw = path.with_name("benchmark_clean.csv").read_bytes()
        clean_rows = read_csv(clean_raw)

        def row_key(row):
            return row["Instance"].upper(), row["Algorithm"]

        clean_bykey = {row_key(row): row for row in clean_rows}
        checkpoint_bykey = {row_key(row): row for row in rows}
        assert len(clean_rows) == len(clean_bykey) == len(rows) == len(checkpoint_bykey)
        assert clean_bykey == checkpoint_bykey
        combined.extend(rows)
        blob = git("rev-parse", f"{ARCHIVE}:{name}").decode().strip()
        history = git(
            "log",
            "--all",
            "--full-history",
            "--no-renames",
            "--root",
            "-m",
            f"--find-object={blob}",
            "--format=%H %aI %s",
            "--raw",
            "--no-abbrev",
        ).decode()
        shards.append(
            {
                "path": name,
                "rows": len(rows),
                "sha256": digest(raw),
                "git_blob": blob,
                "clean_sha256": digest(clean_raw),
                "clean_bytes_identical": clean_raw == raw,
                "clean_parsed_rows_identical": True,
                "object_history": history,
            }
        )
    assert len(combined) == len(bykey) == len({(r["Instance"].upper(), r["Algorithm"]) for r in combined})
    objects = []
    for ref, paths in (
        (
            STORAGE,
            (
                "src/vrptw/benchmark.py",
                "src/vrptw/config.py",
                "src/vrptw/gnn.py",
                "src/vrptw/solvers.py",
                "docs/run_benchmark.py",
                "run_all_benchmarks.sh",
            ),
        ),
        (COLD_FIX, ("src/vrptw/benchmark.py",)),
        (
            ARCHIVE,
            (
                "src/vrptw/benchmark.py",
                "docs/legacy_archive/run_benchmark.py",
                "docs/legacy_archive/HANDOFF_PAPER1_CLAUDE.md",
                "docs/legacy_archive/RERUN_CHECKLIST.md",
                "scripts/benchmarks/run_all_benchmarks.sh",
            ),
        ),
    ):
        objects.extend(recover(output, ref, path) for path in paths)
    before = git("show", f"{STORAGE}:src/vrptw/benchmark.py").decode()
    after = git("show", f"{COLD_FIX}:src/vrptw/benchmark.py").decode()
    warm = "init = best_overall.copy() if best_overall is not None else _diversified_init(i, inst, archive, cfg)"
    assert warm in before and warm not in after and "init = None" in after
    tree = git("ls-tree", "-r", "--name-only", ARCHIVE).decode().splitlines()
    suite_paths = [path for path in tree if path.startswith(str(SUITE) + "/")]
    assert len(suite_paths) == 5 and all(path.endswith("benchmark_checkpoint.csv") for path in suite_paths)
    combined_blob = git("rev-parse", f"HEAD:{SUITE}/combined_clean.csv").decode().strip()
    return {
        "shards": shards,
        "combined_rows_match_all_17_fields": len(combined),
        "combined_git_blob": combined_blob,
        "combined_object_history": git(
            "log",
            "--all",
            "--full-history",
            "--no-renames",
            "--root",
            "-m",
            f"--find-object={combined_blob}",
            "--format=%H %aI %s",
            "--raw",
            "--no-abbrev",
        ).decode(),
        "archive_suite_paths": suite_paths,
        "recovered_objects": objects,
        "anchors": {
            key: git("show", "--no-patch", "--format=%H %aI %s", ref).decode().strip()
            for key, ref in (
                ("checkpoint_storage", STORAGE),
                ("cold_start_code_fix", COLD_FIX),
                ("combined_storage", COMBINED_STORAGE),
                ("archive_tag", ARCHIVE),
            )
        },
        "conclusion": "Git artifact identity is verified. Executed source/config/seed/model identities remain unverified; source at checkpoint storage contains cross-seed initialization.",
    }


def search_appendix_archive(found):
    paths = git("ls-tree", "-r", "--name-only", ARCHIVE).decode().splitlines()
    matches, eligible = [], 0
    for name in paths:
        if not name.endswith(".csv"):
            continue
        try:
            rows = read_csv(git("show", f"{ARCHIVE}:{name}"))
        except (UnicodeDecodeError, csv.Error):
            continue
        if not rows or not {"Instance", "Algorithm", "NV_mean", "TD_mean"}.issubset(rows[0]):
            continue
        eligible += 1
        hits = []
        for row in rows:
            name_key, algorithm = row["Instance"].upper(), row["Algorithm"]
            if name_key not in found or algorithm not in (BASE, FULL, "Hybrid-DDQN", "Hybrid-Rule", "Hybrid-Fixed"):
                continue
            try:
                nv, td = float(row["NV_mean"]), float(row["TD_mean"])
            except (ValueError, TypeError):
                continue
            prefix = "base" if algorithm == BASE else "full"
            if (
                abs(nv - found[name_key][f"{prefix}_nv"]) <= 1e-6
                and abs(td - found[name_key][f"{prefix}_td"]) <= 0.0051
            ):
                hits.append({"instance": name_key, "algorithm": algorithm, "nv": nv, "td": td})
        if hits:
            matches.append({"path": name, "matches": hits})
    return {
        "archive_ref": ARCHIVE,
        "csv_files_scanned": sum(name.endswith(".csv") for name in paths),
        "aggregate_format_files": eligible,
        "files_with_matches": matches,
        "caveat": "Printed-value matches do not identify a run; nonmatches do not prove the original data never existed. Search is limited to this tag and aggregate-format CSVs.",
    }


def current_input_identity(target):
    entries = []
    for name in target:
        if "_" not in name:
            path = Path("data/Solomon") / f"{name.lower()}.txt"
        else:
            scale = 200 if "_2_" in name else 400
            path = Path(f"data/Gehring_Homberger/homberger_{scale}_customer_instances") / f"{name}.TXT"
        raw = (ROOT / path).read_bytes()
        try:
            old = git("show", f"{STORAGE}:{path}")
            same = old == raw
            old_digest = digest(old)
        except subprocess.CalledProcessError:
            same, old_digest = None, None
        entries.append(
            {
                "instance": name,
                "path": str(path),
                "current_sha256": digest(raw),
                "storage_commit_sha256": old_digest,
                "same_bytes": same,
            }
        )
    return {
        "files": entries,
        "caveat": "Matching stored input files does not prove which inputs a historical process consumed.",
    }


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    source_paths = [
        ROOT / SUITE / "combined_clean.csv",
        ROOT / "docs/manuscript.tex",
        ROOT / "docs/supplementary_proofs.tex",
        ROOT / "archive/history-manifest.json",
    ]
    source_paths.extend(sorted((ROOT / SUITE).glob("*/*.csv")))
    inputs = {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in source_paths}
    rows = read_csv((ROOT / SUITE / "combined_clean.csv").read_bytes())
    target = selection(rows)
    arithmetic, bykey = audit_arithmetic(rows, target)
    appendix, differences, printed = audit_appendix(bykey, target)
    lineage = git_lineage(output, bykey)
    appendix_archive = search_appendix_archive(printed)
    input_identity = current_input_identity(target)
    save_json(output / "selection.json", target)
    save_json(output / "git_lineage.json", lineage)
    save_json(output / "appendix_archive_search.json", appendix_archive)
    save_json(output / "current_input_identity.json", input_identity)
    write_csv(output / "appendix_differences.csv", differences)
    summary = {
        "status": "audit_completed_execution_provenance_unverified",
        "assessment": "Headline arithmetic can be shared with caveats; strict-cold-start/equal-budget publication claims need additional evidence or new declared experiments.",
        "head_commit": git("rev-parse", "HEAD").decode().strip(),
        "initial_tracked_diff_sha256": digest(git("diff")),
        "input_hashes": inputs,
        "arithmetic": arithmetic,
        "appendix": appendix,
        "lineage": {
            "matched_rows": lineage["combined_rows_match_all_17_fields"],
            "archive_ref": ARCHIVE,
            "archive_suite_files": len(lineage["archive_suite_paths"]),
        },
        "historical_execution": {
            "source_and_effective_config": "unverified",
            "seed_ids_and_order": "unverified",
            "independent_cold_start": "unverified; contrary source-level evidence at storage commit",
            "matched_wall_clock_budget": "unverified",
            "loaded_gnn_checkpoint_hash": "unverified",
            "per_seed_original_route_feasibility": "unverified",
        },
        "program_sha256": digest(Path(__file__).read_bytes()),
    }
    assert all(digest((ROOT / path).read_bytes()) == expected for path, expected in inputs.items()), (
        "input changed during audit"
    )
    (output / "audit_program.py").write_bytes(Path(__file__).read_bytes())
    save_json(output / "summary.json", summary)
    save_json(
        output / "artifact_hashes.json",
        {
            str(path.relative_to(output)): digest(path.read_bytes())
            for path in sorted(output.rglob("*"))
            if path.is_file()
        },
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "status": summary["status"],
                "headline": arithmetic["headline_from_printed_summary"],
                "appendix": appendix,
                "archive_csvs_scanned": appendix_archive["csv_files_scanned"],
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.output_dir.resolve())


if __name__ == "__main__":
    main()
