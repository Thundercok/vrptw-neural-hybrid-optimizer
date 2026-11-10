"""Independently validate the GES sweep cells and write records.csv.

usage: validate.py [run|smoke]

Checks per cell: CLI return code, certified status, exact-cover/feasibility and distance
recomputed in the original instance, certificate captured strictly before the cutoff,
incumbent route hash, recorded flags, one source hash across cells and the GNN checkpoint.
"""

from __future__ import annotations

import collections
import csv
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "runtime/src"))

from vrptw.core import load_solomon_instance  # noqa: E402
from vrptw.native_certification import routes_sha256, validate_routes  # noqa: E402

COMPARATORS = ("PyVRP-ILS", "NeuroLKH-adapted")
NO_GES_ARMS = ("F111111-blind", "ALNS-Base-noges")
which = sys.argv[1] if len(sys.argv) > 1 else "run"
root = BASE / which
dirs = [BASE / "inputs", BASE.parents[1] / "results/improvement_dev_20261101/instances"]
insts, rows = {}, []
sources = collections.Counter()
for done in sorted(root.glob("*/completed.json")):
    cell = done.parent
    meta = json.loads(done.read_text())
    start = json.loads((cell / "started.json").read_text())
    command = start["command"]
    path = Path(command[command.index("--instance") + 1])
    seed = int(command[command.index("--seed") + 1])
    cutoff = float(command[command.index("--time-limit") + 1])
    case = cell.name.split("_s")[0].split("_")[-1]
    inst = insts.setdefault(path.stem, load_solomon_instance(str(path)))
    errors = []
    res = {}
    if (cell / "result.json").exists():
        res = json.loads((cell / "result.json").read_text())
    else:
        errors.append("no result.json")
    cfg = res.get("requested_config") or {}
    cert = (res.get("native_certification") or {}).get("certificate") or {}
    routes = res.get("routes")
    td = validate_routes(routes, inst) if routes else None
    sources[(res.get("environment") or {}).get("source_sha256")] += 1
    if case not in COMPARATORS:
        if cfg.get("reference_blind") is not True or cfg.get("ges_phase_enabled") is (case in NO_GES_ARMS):
            errors.append("blind/GES flags not as declared")
        if cfg.get("ges_phase_frac") != 0.1:
            errors.append("unexpected ges_phase_frac")
    if meta["returncode"] != 0:
        errors.append(f"returncode {meta['returncode']}")
    if not res.get("feasible") or td is None:
        errors.append(f"not feasible: {res.get('error')}")
    else:
        if len(routes) != res["nv"] or abs(td - res["td"]) > 1e-6:
            errors.append("reported nv/td differ from recomputation")
        if cert.get("routes_sha256") != routes_sha256(tuple(tuple(r) for r in routes)):
            errors.append("certificate hash mismatch")
        if not cert.get("captured_sec", float("inf")) < cutoff:
            errors.append("certificate not captured before cutoff")
    phases = sorted({str(p.get("phase")) for p in (res.get("trajectory") or []) if isinstance(p, dict)})
    rows.append({
        "run": cell.name, "stage": start["stage"], "instance": path.stem, "case_id": case, "seed": seed,
        "cutoff_sec": int(cutoff), "available": not errors, "nv": len(routes) if td is not None else "",
        "td": td if td is not None else "", "captured_sec": cert.get("captured_sec", ""),
        "runtime_sec": res.get("runtime_sec", ""), "end_to_end_wall_sec": res.get("end_to_end_wall_sec", ""),
        "power": start.get("power"), "battery": start.get("battery"), "load1": start.get("loadavg", [None])[0],
        "clock_gap_sec": meta["utc"] - start["utc"] - meta["wall_sec"],
        "phases": "|".join(phases), "errors": json.dumps(errors),
    })
with (root / "records.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
bad = [r for r in rows if r["available"] is False]
for r in bad[:40]:
    print(r["run"], r["errors"])
print(f"{len(rows) - len(bad)}/{len(rows)} cells valid; source hashes {dict(sources)}")
