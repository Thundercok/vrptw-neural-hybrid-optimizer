"""Print the pgfplots body of the fleet-score-by-budget figure in docs/manuscript.tex.

Reads the rerun analysis (results/ges_sweep_20261102/analysis/results.json). At 300 s the intervals
are the confirmatory 98.33% intervals (filled markers); at 10 and 60 s they are descriptive 95%
intervals (open markers). The manuscript holds the printed coordinates inline; rerun this script
and compare to check them.

usage: python scripts/plot_fleet_score_by_budget.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/ges_sweep_20261102/analysis/results.json"
# Comparator, color name in the manuscript, pgfplots mark, horizontal offset factor on the log axis.
SERIES = (("ALNS-Base", "cSerA", "*", 0.88), ("PyVRP-ILS", "cSerB", "square*", 1.0),
          ("NeuroLKH-adapted", "cSerC", "triangle*", 1.13))
BUDGETS = (10, 60, 300)


def rows():
    out = {}
    for r in json.loads(RESULTS.read_text())["results"]:
        if r.get("scope") != "all" or r.get("gap_mode") != "drop_pair":
            continue
        if (r.get("analysis"), r["cutoff_sec"]) in (("primary", 300), ("budget", 10), ("budget", 60)):
            i = r["intervals"]["fleet_score"]
            out[(r["control"], r["cutoff_sec"])] = (r["fleet_score"], i["lower"], i["upper"], i["level"])
    assert len(out) == 9, sorted(out)
    assert all(abs(v[3] - (0.95 if b != 300 else 1 - 0.05 / 3)) < 1e-9 for (_, b), v in out.items())
    return out


def point(x, values):
    score, low, high, _ = values
    return f"({x:g},{score:.3f}) += (0,{high - score:.3f}) -= (0,{score - low:.3f})"


def main() -> None:
    data = rows()
    lines = []
    for name, color, mark, dodge in SERIES:
        xs = [b * dodge for b in BUDGETS]
        path = " ".join(f"({x:g},{data[(name, b)][0]:.3f})" for x, b in zip(xs, BUDGETS))
        lines.append(f"% {name}")
        lines.append(f"\\addplot[{color}, line width=0.8pt, opacity=0.55, forget plot] coordinates {{{path}}};")
        open_pts = " ".join(point(x, data[(name, b)]) for x, b in zip(xs, BUDGETS) if b != 300)
        lines.append(f"\\addplot[{color}, only marks, mark={mark}, mark options={{fill=white}}, forget plot, "
                     f"error bars/.cd, y dir=both, y explicit] coordinates {{{open_pts}}};")
        lines.append(f"\\addplot[{color}, only marks, mark={mark}, "
                     f"error bars/.cd, y dir=both, y explicit] coordinates {{{point(xs[-1], data[(name, 300)])}}};")
        lines.append(f"\\addlegendentry{{{name}}}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
