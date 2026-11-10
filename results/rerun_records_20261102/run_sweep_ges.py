"""Single contemporaneous rerun: all primary cases with comparators, plus the ablation cases.

Jobs come from the frozen design. All cases of one instance/seed/cutoff run together as a block,
because machine speed varied too much for cells from different days to be compared. Stage order puts
the primary T300 blocks first, and block order inside a stage is shuffled with the design's order seed.
Resumable: finished cells are skipped and a cell cut off by an interruption is moved to interrupted/
and run again. A block with a cell frozen by machine sleep is moved to slept_blocks/ and run again whole.
A file named STOP stops new cells from starting.

usage: run_sweep_ges.py [--smoke]
"""

from __future__ import annotations

import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PYTHON = ROOT / ".venv/bin/python"
CLI = BASE / "runtime/scripts/benchmark_supervised.py"
GNN = BASE / "gnn_checkpoint.pt"
NEUROLKH = ROOT / "results/external/NeuroLKH"
DESIGN = ROOT / "results/ablation_design_20261019/jobs.jsonl"
DEV = ROOT / "results/improvement_dev_20261101/instances"
ALIASES = {"ALNS-Base": "alns", "ALNS-Base-noges": "alns", "F111111-blind": "F111111", "PyVRP-ILS": "pyvrp",
           "NeuroLKH-adapted": "neurolkh"}
# Reported whichever way the adoption rule falls: the same family without GES, at T300 only.
NO_GES_ARMS = ("F111111-blind", "ALNS-Base-noges")
COMPARATORS = ("PyVRP-ILS", "NeuroLKH-adapted")
ORDER_SEED = 20261019
WORKERS = 4
# Low Power Sleep hit at 4% even on AC, so hold well above that.
BATTERY_HOLD, BATTERY_RESUME = 5, 8
LOAD_HOLD, LOAD_RESUME = 8.0, 7.0  # README Amendment 4
SLEEP_GAP_SEC = 5
MIN_FREE_GB = 5


def environment(case: str) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("VRPTW_")}
    env.update(NUMBA_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    if case not in COMPARATORS:
        env["VRPTW_REFERENCE_BLIND"] = "1"
    if case not in COMPARATORS and case not in NO_GES_ARMS:
        env["VRPTW_GES_PHASE"] = "1"
    return env


def battery() -> tuple[str, int | None]:
    text = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    level = re.search(r"(\d+)%", text)
    return ("AC" if "AC Power" in text else "BATT"), int(level.group(1)) if level else None


def wait_until_safe(out_root: Path, stop_file: Path) -> bool:
    """Hold new cells while unplugged or while the battery or disk is too low. False means stop."""
    held = False
    while not stop_file.exists():
        power, level = battery()
        free_gb = shutil.disk_usage(out_root).free / 2**30
        threshold = BATTERY_RESUME if held else BATTERY_HOLD
        load1 = os.getloadavg()[0]
        quiet = load1 <= (LOAD_RESUME if held else LOAD_HOLD)
        if power == "AC" and (level is None or level > threshold) and free_gb >= MIN_FREE_GB and quiet:
            if held:
                print(json.dumps({"hold_end": time.time(), "battery": level, "free_gb": free_gb}), flush=True)
            return True
        if not held:
            print(json.dumps({"hold_start": time.time(), "power": power, "battery": level, "free_gb": free_gb, "load1": load1}), flush=True)
            held = True
        time.sleep(60)
    return False


def cell_name(job: dict) -> str:
    case, inst, seed, cutoff = job["case_id"], job["instance"], job["seed"], job["cutoff_sec"]
    return f"{inst}_{case}_s{seed}_t{cutoff}" + (f"_{job['stage']}" if job["stage"].startswith("ablation") and case == "F111111" else "")


def slept(cell: Path) -> bool:
    """perf_counter stops during machine sleep and the wall clock does not, so a frozen cell shows a gap."""
    try:
        start = json.loads((cell / "started.json").read_text())["utc"]
        done = json.loads((cell / "completed.json").read_text())
    except FileNotFoundError:
        return False
    return done["utc"] - start - done["wall_sec"] > SLEEP_GAP_SEC


def requeue_slept_blocks(group: list[dict], out_root: Path) -> int:
    """Move every cell of a block touched by sleep aside, unread, so the whole block runs again together."""
    blocks: dict[tuple, list[Path]] = {}
    for job in group:
        blocks.setdefault((job["instance"], job["seed"]), []).append(out_root / cell_name(job))
    moved = 0
    for key, cells in blocks.items():
        if any(slept(c) for c in cells):
            target = out_root / "slept_blocks"
            target.mkdir(exist_ok=True)
            present = [c for c in cells if c.exists()]
            for c in present:
                c.rename(target / f"{c.name}__{int(time.time())}")
            moved += len(present)
            print(json.dumps({"requeued_block": key, "cells": len(present), "utc": time.time()}), flush=True)
    return moved


def run_cell(job: dict, out_root: Path, stop_file: Path) -> dict | None:
    case, inst, seed, cutoff = job["case_id"], job["instance"], job["seed"], job["cutoff_sec"]
    name = cell_name(job)
    out = out_root / name
    if (out / "completed.json").exists():
        return json.loads((out / "completed.json").read_text())
    if not wait_until_safe(out_root, stop_file):
        return None
    if out.exists():
        moved = out_root / "interrupted" / f"{name}__{int(time.time())}"
        moved.parent.mkdir(exist_ok=True)
        out.rename(moved)
    out.mkdir()
    command = [str(PYTHON), str(CLI), "--instance", job["path"], "--ablation", ALIASES.get(case, case), "--seed", str(seed),
               "--time-limit", str(cutoff), "--session-dir", str(out / "session"),
               "--output-json", str(out / "result.json")]
    if ALIASES.get(case, case).startswith("F") and ALIASES.get(case, case)[-1] == "1":
        command += ["--gnn-model", str(GNN)]
    if case == "NeuroLKH-adapted":
        command += ["--neurolkh-root", str(NEUROLKH)]
    power, level = battery()
    (out / "started.json").write_text(json.dumps({
        "job": name, "stage": job["stage"], "command": command, "utc": time.time(), "power": power, "battery": level,
        "loadavg": os.getloadavg(),
    }))
    with (out / "stdout.log").open("x") as so, (out / "stderr.log").open("x") as se:
        t = time.perf_counter()
        rc = subprocess.run(command, cwd=BASE / "runtime", env=environment(case), stdin=subprocess.DEVNULL, stdout=so,
                            stderr=se).returncode
    done = {"job": name, "returncode": rc, "wall_sec": time.perf_counter() - t, "utc": time.time()}
    (out / "completed.json").write_text(json.dumps(done))
    print(json.dumps(done), flush=True)
    return done


def sweep_jobs() -> list[list[dict]]:
    design = [json.loads(line) for line in DESIGN.read_text().splitlines()]
    assert len(design) == 8620

    def stage(name: str, uses: str, cutoff: int, extra_arms: tuple[str, ...] = ()) -> list[dict]:
        blocks: dict[tuple, list[dict]] = {}
        for j in design:
            if uses in j["uses"] and j["cutoff_sec"] == cutoff:
                blocks.setdefault((j["instance"], j["seed"]), []).append(j)
        rng = random.Random(f"{ORDER_SEED}/{name}")
        cells = []
        for key in rng.sample(sorted(blocks), len(blocks)):
            arms = sorted(blocks[key], key=lambda j: j["case_id"])
            arms += [{**arms[0], "case_id": c} for c in extra_arms]
            rng.shuffle(arms)
            cells += [{**j, "stage": name, "path": str(BASE / "inputs" / f"{j['instance']}.TXT")} for j in arms]
        return cells

    stages = [
        stage("primary_t300", "primary", 300, NO_GES_ARMS),
        stage("primary_t60", "primary", 60),
        stage("primary_t10", "primary", 10),
        stage("ablation_t60", "ablation", 60),
        stage("ablation_t300", "ablation", 300),
        stage("primary_t900", "primary", 900),
    ]
    assert [len(g) for g in stages] == [2220, 1480, 1480, 1440, 1440, 1480]
    return stages


def smoke_jobs() -> list[list[dict]]:
    design = [json.loads(line) for line in DESIGN.read_text().splitlines()]
    cases = sorted({j["case_id"] for j in design if j["case_id"] not in COMPARATORS} | set(NO_GES_ARMS))
    assert len(cases) == 19
    insts = ("dev100_C1_2_6", "dev100_RC2_2_8")
    group = [{"case_id": c, "instance": i, "seed": 1001, "cutoff_sec": 10, "stage": "smoke",
              "path": str(DEV / f"{i}.TXT")} for c in cases for i in insts]
    group += [{"case_id": c, "instance": "dev100_C2_2_6", "seed": 1001, "cutoff_sec": 10, "stage": "smoke",
               "path": str(DEV / "dev100_C2_2_6.TXT")} for c in COMPARATORS]
    return [group]


def main() -> int:
    smoke = "--smoke" in sys.argv
    out_root = BASE / ("smoke" if smoke else "run")
    out_root.mkdir(exist_ok=True)
    stop_file = BASE / "STOP"
    stages = smoke_jobs() if smoke else sweep_jobs()
    for group in stages:
        print(json.dumps({"stage_start": group[0]["stage"], "cells": len(group), "utc": time.time()}), flush=True)
        requeue_slept_blocks(group, out_root)
        while True:
            with ThreadPoolExecutor(WORKERS) as pool:
                results = list(pool.map(lambda job: run_cell(job, out_root, stop_file), group))
            if any(r is None for r in results):
                print(json.dumps({"stopped": time.time()}), flush=True)
                return 2
            if not requeue_slept_blocks(group, out_root):
                break
    (out_root / "finished.json").write_text(json.dumps({"utc": time.time()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
