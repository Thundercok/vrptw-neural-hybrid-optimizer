"""Analysis fixed by docs/micro_replication_protocol.md, written before any cell ran. Uses the sweep's functions.

usage: analyze.py    (refuses to run until run/finished.json exists and validate.py has written run/records.csv)
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_ges_rerun as rerun  # noqa: E402

from vrptw import sweep_statistics as stats  # noqa: E402

STAGE = "micro_replication_t60"
CASES = ("F111111", "F111011", "F000100", "F000000")
CONTRASTS = (("Micro full context", "F111111", "F111011"), ("Micro bare", "F000100", "F000000"))
SEEDS = [42, 43, 44, 45, 46]
CONFIRMATORY_FAMILY = 2
DRAW_SEED = 20261110


def metadata_from_inputs(folder: Path) -> dict:
    meta = {}
    for path in sorted(folder.glob("*.TXT")):
        rows = [ln.split() for ln in path.read_text().splitlines() if re.match(r"\s*\d+(\s+\d+){6}\s*$", ln)]
        coords = repr([(r[1], r[2]) for r in rows])
        meta[path.stem] = {"customers": len(rows) - 1, "geometry_sha256": hashlib.sha256(coords.encode()).hexdigest()}
    return meta


def analyze(cells, metadata, names, draws, weights, stage, cutoff, family):
    rows, gaps = rerun.stage_rows(cells, stage, names, CASES, SEEDS, metadata)
    exposed, unmeasured = rerun.run_load_blocks(rows)
    out = []
    for label, treatment, control in CONTRASTS:
        common = (rows, metadata)
        out.append(rerun.compare(*common, names, treatment, control, cutoff, draws, weights, gaps, "drop_pair", family,
                                 analysis="confirmatory", contrast=label, scope="all"))
        for scope, subset, subset_weights in rerun.size_scopes(names, metadata, weights)[1:]:
            out.append(rerun.compare(*common, subset, treatment, control, cutoff, draws, subset_weights, gaps,
                                     "drop_pair", 1, analysis="descriptive", contrast=label, scope=scope))
        out.append(rerun.compare(*common, names, treatment, control, cutoff, draws, weights,
                                 gaps | rerun.block_gaps(rows, exposed), "drop_pair", 1,
                                 analysis="without_high_load_blocks", contrast=label, scope="all"))
    return out, {"gaps": len(gaps), "exposed_blocks": len(exposed), "unmeasured_blocks": len(unmeasured)}


def main() -> int:
    stats.require((HERE / "run/finished.json").exists(), "the test has not finished")
    rerun.STAGES = (STAGE,)
    metadata = metadata_from_inputs(HERE / "inputs")
    names = sorted(metadata)
    stats.require(len(names) == 24, "instance universe differs")
    cells = rerun.load_cells(HERE / "run/records.csv", metadata)
    rerun.attach_run_load(cells, HERE / "run", HERE / "load_samples.jsonl")
    draws = stats.make_draws(metadata, SEEDS, 10000, DRAW_SEED)
    results, info = analyze(cells, metadata, names, draws, {200: 0.5, 400: 0.5}, STAGE, 60, CONFIRMATORY_FAMILY)
    (HERE / "analysis").mkdir(exist_ok=True)
    (HERE / "analysis/results.json").write_text(json.dumps({"info": info, "results": results}, indent=1))
    print(info)
    for r in results:
        print(r["analysis"], r["contrast"], r["scope"], r["fleet_score"], r["intervals"]["fleet_score"], r["td_pct"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
