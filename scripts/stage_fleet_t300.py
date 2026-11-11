"""Fleet size by stage at 300 s for the proposed configuration and ALNS-Base.

usage: python3 scripts/stage_fleet_t300.py

Reads the trajectory of every certified `primary_t300` cell of F111111 and ALNS-Base in the full
run folder and writes one row per cell: the fleet of the initial solution, the fleet right after
the Guided Ejection Search phase, the final fleet, and when that phase recorded its last solution.
It then prints the counts quoted in the Discussion. Descriptive only: no interval, no test.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results/ges_sweep_20261102/run"
RECORDS = ROOT / "results/rerun_records_20261102/records.csv"
OUT = ROOT / "results/rerun_records_20261102/analysis/stage_fleet_t300.csv"
CASES = ("F111111", "ALNS-Base")


def stages(instance: str, case: str, seed: str) -> dict:
    result = json.loads((RUN / f"{instance}_{case}_s{seed}_t300/result.json").read_text())
    points = [p for p in result["trajectory"] if isinstance(p, dict) and p.get("nv") is not None]
    before_search = [p for p in points if p["phase"] in ("initial", "ges")]
    ges = [p for p in points if p["phase"] == "ges"]
    return {
        "instance": instance, "seed": int(seed), "case_id": case,
        "nv_initial": int(next(p["nv"] for p in points if p["phase"] == "initial")),
        "nv_after_ges": min(int(p["nv"]) for p in before_search),
        "nv_final": int(result["nv"]),
        "ges_last_solution_sec": round(max(p["t_sec"] for p in ges), 3) if ges else "",
    }


def main() -> int:
    cells = sorted({(r["instance"], r["seed"]) for r in csv.DictReader(RECORDS.open())
                    if r["stage"] == "primary_t300" and r["available"] == "True" and r["case_id"] in CASES})
    rows = [stages(inst, case, seed) for inst, seed in cells for case in CASES]
    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    by = {(r["instance"], r["seed"], r["case_id"]): r for r in rows}
    pairs = [(by[i, int(s), "F111111"], by[i, int(s), "ALNS-Base"]) for i, s in cells]
    sign = lambda d: "more" if d > 0 else "fewer" if d < 0 else "same"
    table = Counter((sign(h["nv_after_ges"] - a["nv_after_ges"]), sign(h["nv_final"] - a["nv_final"])) for h, a in pairs)
    print(f"{OUT.relative_to(ROOT)}: {len(rows)} rows, {len(pairs)} seed pairs")
    print("hybrid fleet vs ALNS-Base (after the phase, at the end):", dict(sorted(table.items())))
    print("same at both points:", table["same", "same"])
    print("after the phase: same", sum(v for (a, _), v in table.items() if a == "same"),
          "| hybrid more", sum(v for (a, _), v in table.items() if a == "more"),
          "| hybrid fewer", sum(v for (a, _), v in table.items() if a == "fewer"))
    print("runs that reduced the fleet after the phase: hybrid",
          sum(h["nv_final"] < h["nv_after_ges"] for h, _ in pairs), "| ALNS-Base",
          sum(a["nv_final"] < a["nv_after_ges"] for _, a in pairs))
    lost = [(h, a) for h, a in pairs if h["nv_final"] > a["nv_final"]]
    behind = [(h, a) for h, a in lost if h["nv_after_ges"] > a["nv_after_ges"]]
    later = [(h, a) for h, a in lost if h["nv_after_ges"] <= a["nv_after_ges"]]
    print("pairs lost:", len(lost), "| already behind after the phase:", len(behind),
          "| lost afterwards:", len(later), sorted({h["instance"] for h, _ in later}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
