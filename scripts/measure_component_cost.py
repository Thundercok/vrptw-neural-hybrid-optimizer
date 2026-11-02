"""Time per solver component and LAC activity for one in-process run (R3.5, R3.8).

Runs the frozen runtime with the sweep's flags, wrapping selected calls with timers. Times are exclusive:
a nested timed call is charged to itself and not to its parent. The wrappers add a small overhead and
these runs are not sweep cells, so they measure shares of a budget, not solution quality. Run them
while the sweep is stopped or finished, one at a time, or the timing will perturb the sweep.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from functools import wraps
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results/ges_sweep_20261102"


class Timers:
    """Exclusive wall time per name; nested timed calls subtract from their parent."""

    def __init__(self):
        self.seconds = defaultdict(float)
        self.calls = Counter()
        self._children = []

    def wrap(self, function, name):
        @wraps(function)
        def timed(*args, **kwargs):
            self._children.append(0.0)
            start = time.perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                nested = self._children.pop()
                self.seconds[name] += elapsed - nested
                self.calls[name] += 1
                if self._children:
                    self._children[-1] += elapsed

        return timed

    def patch(self, owner, key, name):
        setattr(owner, key, self.wrap(getattr(owner, key), name))


class LacActivity:
    """Counts consulted decisions, warmup decisions and classifier approvals around LearnedAcceptanceCriterion.decide."""

    def __init__(self):
        self.counts = Counter()

    def wrap(self, lac):
        original = lac.decide

        @wraps(original)
        def decide(feats, cur_best_cost, tau=None, *, sa_probability=None):
            accepted, p = original(feats, cur_best_cost, tau=tau, sa_probability=sa_probability)
            self.counts["consulted"] += 1
            if lac.step < lac.cfg.lac_warmup:
                self.counts["warmup"] += 1
            elif tau is not None and p >= tau:
                self.counts["classifier_approved"] += 1
            self.counts["accepted"] += bool(accepted)
            return accepted, p

        lac.decide = decide


def instrument(solver, repair_list, timers: Timers, activity: LacActivity):
    for owner, key, name in (
        (solver.ctrl, "act", "macro_inference"),
        (solver.ctrl, "train_step", "macro_training"),
        (solver.op_ctrl, "act", "micro_inference"),
        (solver.op_ctrl, "train_step", "micro_training"),
        (solver.lac, "decide", "lac_inference"),
        (solver.lac, "_train", "lac_training"),
        (solver, "_destroy", "destroy"),
        (solver, "_local_search", "local_search"),
        (solver, "_try_gec_route_reduction", "gec"),
        (solver, "_recombine_with_pool", "set_partitioning"),
        (solver, "_ges_phase", "ges_phase"),
        (solver, "_capture_native", "capture"),
        (solver, "_fixed_nv_polish", "fixed_fleet_polish"),
    ):
        if hasattr(owner, key):
            timers.patch(owner, key, name)
    activity.wrap(solver.lac)
    for i, operator in enumerate(repair_list):
        repair_list[i] = timers.wrap(operator, "repair")


def summarize(solver, timers, activity, seconds):
    timed = sum(timers.seconds.values())
    return {
        "wall_sec": seconds,
        "component_sec": dict(sorted(timers.seconds.items())),
        "component_calls": dict(sorted(timers.calls.items())),
        "other_sec": seconds - timed,
        "iterations": getattr(solver, "search_iterations", None),
        "first_phase_ended": getattr(solver, "phase1_done", None),
        "first_phase_end_iteration": getattr(solver, "early_stop_triggered_iter", None),
        "lac": dict(activity.counts),
        "modes": {str(k): v for k, v in sorted(getattr(solver, "mode_trace", {}).items())},
        "controllers": dict(getattr(solver, "controller_counts", {})),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--config", choices=("ges", "blind"), required=True, help="F111111 with or without the GES phase")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--time-limit", type=float, default=300.0)
    parser.add_argument("--runtime", type=Path, default=RUN / "runtime")
    parser.add_argument("--checkpoint", type=Path, default=RUN / "gnn_checkpoint.pt")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    os.environ.update(NUMBA_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", VRPTW_REFERENCE_BLIND="1")
    if args.config == "ges":
        os.environ["VRPTW_GES_PHASE"] = "1"
    else:
        os.environ.pop("VRPTW_GES_PHASE", None)
    sys.path.insert(0, str(args.runtime / "src"))
    sys.path.insert(0, str(args.runtime / "scripts"))
    import torch

    torch.set_num_threads(1)
    from benchmark import get_solver_and_config

    from vrptw import operators
    from vrptw.core import load_solomon_instance

    cls, cfg = get_solver_and_config("F111111", args.time_limit, seed=args.seed, gnn_model=args.checkpoint)
    inst = load_solomon_instance(str(args.instance))
    timers, activity = Timers(), LacActivity()
    solver = cls(inst, cfg, seed=args.seed)
    solver.load_gnn_model(str(args.checkpoint))
    instrument(solver, operators.REPAIR, timers, activity)
    if solver.gnn_model is not None:
        solver.gnn_model.forward = timers.wrap(solver.gnn_model.forward, "gnn_inference")
    start = time.perf_counter()
    plan, _ = solver.solve(seed=args.seed)
    seconds = time.perf_counter() - start
    summary = summarize(solver, timers, activity, seconds)
    summary.update(
        instance=args.instance.stem, config=args.config, seed=args.seed, time_limit=args.time_limit, customers=inst.n,
        loadavg=os.getloadavg(), nv=plan.nv, td=plan.cost,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: summary[k] for k in ("instance", "wall_sec", "iterations", "first_phase_ended", "lac")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
