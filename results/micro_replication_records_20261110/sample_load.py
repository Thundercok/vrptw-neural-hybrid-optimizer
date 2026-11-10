"""Append the load averages to load_samples.jsonl every 10 s, so a 60 s cell gets about six samples until the sweep finishes (Amendment 5)."""

import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
while not (ROOT / "run/finished.json").exists():
    with (ROOT / "load_samples.jsonl").open("a") as f:
        f.write(json.dumps({"utc": time.time(), "load": os.getloadavg()}) + "\n")
    time.sleep(10)
