"""Estimated main-loop iteration rate at 300 s for the proposed configuration and ALNS-Base.

usage: python3 scripts/iteration_rate_t300.py

Sweep cells do not record a total iteration count, so the rate is estimated from each cell's
trajectory: the iterations between the first and the last improvement recorded in the main loop
(phase `search`), divided by the time between them. A cell is used when those two improvements are
at least 5 s apart. Writes one row per usable cell and prints medians by size and by family, and
the macro controller's decisions per run from the component-cost measurement. Descriptive only.
"""

from __future__ import annotations

import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results/ges_sweep_20261102/run"
RECORDS = ROOT / "results/rerun_records_20261102/records.csv"
COST = ROOT / "results/rerun_records_20261102/analysis/component_cost"
OUT = ROOT / "results/rerun_records_20261102/analysis/iteration_rate_t300.csv"
CASES = ("F111111", "ALNS-Base")
MIN_SPAN_SEC = 5.0


def size(instance: str) -> int:
    return 400 if "_4_" in instance else 200 if "_2_" in instance else 100


def family(instance: str) -> str:
    return re.match(r"(RC|R|C)[12]", instance).group(0)


def main() -> int:
    rows = []
    for r in csv.DictReader(RECORDS.open()):
        if r["stage"] != "primary_t300" or r["available"] != "True" or r["case_id"] not in CASES:
            continue
        result = json.loads((RUN / f"{r['instance']}_{r['case_id']}_s{r['seed']}_t300/result.json").read_text())
        search = [p for p in result["trajectory"] if isinstance(p, dict) and p.get("phase") == "search" and p.get("iter") is not None]
        if len(search) < 2:
            continue
        first, last = min(search, key=lambda p: p["t_sec"]), max(search, key=lambda p: p["t_sec"])
        span, iterations = last["t_sec"] - first["t_sec"], last["iter"] - first["iter"]
        if span < MIN_SPAN_SEC or iterations <= 0:
            continue
        rows.append({"instance": r["instance"], "seed": int(r["seed"]), "case_id": r["case_id"],
                     "customers": size(r["instance"]), "family": family(r["instance"]),
                     "iterations_between": iterations, "seconds_between": round(span, 3),
                     "iterations_per_sec": round(iterations / span, 3)})
    rows.sort(key=lambda x: (x["instance"], x["seed"], x["case_id"]))
    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{OUT.relative_to(ROOT)}: {len(rows)} usable cells of 740")

    def table(key, values):
        groups = defaultdict(lambda: defaultdict(list))
        for x in rows:
            groups[x[key]][x["case_id"]].append(x["iterations_per_sec"])
        for v in values:
            h, a = groups[v]["F111111"], groups[v]["ALNS-Base"]
            mh, ma = statistics.median(h), statistics.median(a)
            print(f"  {str(v):>5}: hybrid {mh:7.1f} ({len(h)} cells) | ALNS-Base {ma:7.1f} ({len(a)} cells) | ratio {ma / mh:5.1f}")

    print("median iterations per second by size:")
    table("customers", (100, 200, 400))
    print("by family:")
    table("family", ("C1", "C2", "R1", "R2", "RC1", "RC2"))

    macro = [json.loads(p.read_text())["component_calls"].get("macro_inference", 0) for p in sorted(COST.glob("*.json"))]
    print(f"macro decisions per run, {len(macro)} cost-measurement runs: median {statistics.median(macro)}, "
          f"range {min(macro)} to {max(macro)}, ten or fewer in {sum(m <= 10 for m in macro)}, none in {sum(m == 0 for m in macro)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
