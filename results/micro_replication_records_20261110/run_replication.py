"""Fresh-instance test of Micro-DDQN at 60 s, fixed by docs/micro_replication_protocol.md.

Reuses the sweep's run_cell, guards and sleep requeue from run_sweep_ges.py without changing them, so the runtime,
flags, GNN checkpoint and block discipline are those of the sweep. Resumable. A file named STOP here stops new cells.
"""

from __future__ import annotations

import importlib.util
import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("run_sweep_ges", HERE.parent / "ges_sweep_20261102/run_sweep_ges.py")
sweep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sweep)

STAGE = "micro_replication_t60"
CASES = ("F111111", "F111011", "F000100", "F000000")
SEEDS = (42, 43, 44, 45, 46)
INSTANCES = tuple(f"{f}_{s}_{k}" for s in (2, 4) for f in ("C1", "C2", "R1", "R2", "RC1", "RC2") for k in (9, 10))


def jobs() -> list[dict]:
    rng = random.Random(f"20261110/{STAGE}")
    cells = []
    for inst, seed in rng.sample(sorted((i, s) for i in INSTANCES for s in SEEDS), len(INSTANCES) * len(SEEDS)):
        arms = list(CASES)
        rng.shuffle(arms)
        cells += [{"case_id": c, "instance": inst, "seed": seed, "cutoff_sec": 60, "stage": STAGE,
                   "path": str(HERE / "inputs" / f"{inst}.TXT")} for c in arms]
    assert len(cells) == 480 and all(Path(j["path"]).exists() for j in cells)
    return cells


def main() -> int:
    group = jobs()
    if "--dry-run" in sys.argv:
        print(len(group), group[0], sweep.cell_name(group[0]), sweep.environment(group[0]["case_id"]).get("VRPTW_GES_PHASE"))
        return 0
    out_root, stop_file = HERE / "run", HERE / "STOP"
    out_root.mkdir(exist_ok=True)
    print(json.dumps({"stage_start": STAGE, "cells": len(group), "utc": time.time()}), flush=True)
    sweep.requeue_slept_blocks(group, out_root)
    while True:
        with ThreadPoolExecutor(sweep.WORKERS) as pool:
            results = list(pool.map(lambda job: sweep.run_cell(job, out_root, stop_file), group))
        if any(r is None for r in results):
            print(json.dumps({"stopped": time.time()}), flush=True)
            return 2
        if not sweep.requeue_slept_blocks(group, out_root):
            break
    (out_root / "finished.json").write_text(json.dumps({"utc": time.time()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
