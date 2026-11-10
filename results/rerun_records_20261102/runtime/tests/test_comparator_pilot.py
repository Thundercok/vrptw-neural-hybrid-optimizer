from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location("common_pilot", ROOT / "scripts/run_comparator_supervisor_pilot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_common_schedule_has_balanced_four_case_blocks():
    pilot = load()
    jobs = pilot.jobs()
    assert jobs == pilot.jobs()
    assert len(jobs) == len({j["run"] for j in jobs}) == 16
    assert sum(j["time_limit"] for j in jobs) == 360
    assert Counter((j["instance"], j["ablation"]) for j in jobs if j["time_limit"] == 10) == Counter(
        (inst, case) for inst in pilot.native.INSTANCES for case in pilot.CASES
    )
    assert all(j["seed"] == 42 for j in jobs if j["time_limit"] == 10)
    assert all(j["instance"] == pilot.native.INSTANCES[2] and j["seed"] == 43 for j in jobs if j["time_limit"] == 60)
    assert all(
        Counter(j["position"] for j in jobs if j["ablation"] == case) == dict.fromkeys(range(4), 1)
        for case in pilot.CASES
    )


def test_freeze_binds_backends_and_every_command_without_solving(tmp_path):
    pilot = load()
    out = tmp_path / "frozen"
    plan = pilot.freeze(out)
    assert plan["backends"]["pyvrp"]["version"] == "0.14.1"
    assert (
        plan["backends"]["neurolkh"]["assets"]["checkpoint_sha256"]
        == "58287b23eedf9eecab5aadcf8ba640b56c50b1b6cfa3259eb39cd443a6072394"
    )
    for job in plan["jobs"]:
        argv = plan["commands"][job["run"]]
        assert argv[argv.index("--seed") + 1] == str(job["seed"])
        assert argv[argv.index("--time-limit") + 1] == str(job["time_limit"])
        assert ("--gnn-model" in argv) is (job["ablation"] == "F111111")
        assert ("--neurolkh-root" in argv) is (job["ablation"] == "neurolkh")
        if job["ablation"] == "neurolkh":
            assert plan["configs"][job["run"]]["requested_config"]["neurolkh_root"] == str(pilot.ASSETS)
        assert not (out / job["run"]).exists()
    pilot.check(out, plan, pilot.sha256(out / "plan.json"))
