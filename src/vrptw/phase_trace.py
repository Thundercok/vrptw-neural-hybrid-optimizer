"""Opt-in Python phase spans; instrumentation is not benchmark evidence."""

from __future__ import annotations

import csv
import importlib
import math
import threading
import time
from functools import wraps
from inspect import getattr_static
from pathlib import Path


def _post(start, end, cutoff):
    return max(0.0, end - max(start, cutoff))


def _measure(events, cutoff):
    children_by_parent = {}
    for event in events:
        children_by_parent.setdefault(event["parent_id"], []).append(event)
    measured = []
    for event in events:
        children = children_by_parent.get(event["id"], [])
        inclusive = _post(event["start_perf"], event["end_perf"], cutoff)
        exclusive = inclusive - math.fsum(_post(e["start_perf"], e["end_perf"], cutoff) for e in children)
        measured.append(
            {**event, "post_cutoff_inclusive_sec": inclusive, "post_cutoff_exclusive_sec": max(0.0, exclusive)}
        )
    return measured


class PhaseTrace:
    def __init__(self, solver, *, clock=time.perf_counter):
        self.solver, self.clock = solver, clock
        self.events, self.stack, self._undo = [], [], []
        self._patched = set()
        self._solve_only = False

    def _begin(self, name, *, deadline=None, detail=""):
        event = {
            "id": len(self.events) + 1,
            "parent_id": self.stack[-1] if self.stack else 0,
            "name": name,
            "start_perf": self.clock(),
            "end_perf": None,
            "deadline_arg_perf": deadline,
            "detail": detail,
            "outcome": "return",
        }
        self.events.append(event)
        self.stack.append(event["id"])
        return event

    def _end(self, event):
        event["end_perf"] = self.clock()
        assert self.stack.pop() == event["id"]

    def call(self, name, function, *args, **kwargs):
        event = self._begin(name, deadline=kwargs.get("deadline", kwargs.get("_deadline")))
        try:
            return function(*args, **kwargs)
        except BaseException as exc:
            event["outcome"] = type(exc).__name__
            raise
        finally:
            self._end(event)

    def patch(self, owner, key, name):
        identity = (id(owner), key)
        if identity in self._patched or not hasattr(owner, key):
            return
        original = getattr_static(owner, key) if isinstance(owner, type) else getattr(owner, key)
        function = original.__func__ if isinstance(original, (classmethod, staticmethod)) else original
        if isinstance(original, property):
            function = original.fget
        if not callable(function):
            return
        own_attribute = key in vars(owner)

        @wraps(function)
        def traced(*args, **kwargs):
            if self._solve_only and (not self.stack or self.events[self.stack[0] - 1]["name"] != "solve"):
                return function(*args, **kwargs)
            return self.call(name, function, *args, **kwargs)

        replacement = traced
        if isinstance(original, (classmethod, staticmethod)):
            replacement = type(original)(traced)
        elif isinstance(original, property):
            replacement = original.getter(traced)
        setattr(owner, key, replacement)
        self._patched.add(identity)
        self._undo.append(lambda: setattr(owner, key, original) if own_attribute else delattr(owner, key))

    def install_numba_events(self):
        from numba.core import event as numba_event

        trace, owner_thread = self, threading.get_ident()

        class CompilerListener(numba_event.Listener):
            def __init__(self):
                self.frames = []

            def on_start(self, event):
                if threading.get_ident() != owner_thread or not trace.stack:
                    return
                if trace.events[trace.stack[0] - 1]["name"] != "solve":
                    return
                function = event.data["dispatcher"].py_func
                span = trace._begin(
                    f"numba.compile:{function.__module__}.{function.__qualname__}",
                    detail=str(event.data["args"]),
                )
                self.frames.append(span)

            def on_end(self, event):
                if threading.get_ident() == owner_thread and self.frames:
                    span = self.frames.pop()
                    # END records a boundary, not a successful compilation claim.
                    span["outcome"] = "compiler_event_end"
                    trace._end(span)

        listener = CompilerListener()
        numba_event.register("numba:compile", listener)
        self._undo.append(lambda: numba_event.unregister("numba:compile", listener))

    def install(self):
        self._solve_only = True
        self.install_numba_events()
        methods = (
            "_validate_search_setup",
            "_destroy",
            "_local_search",
            "_refine_candidate",
            "_try_gec_route_reduction",
            "_fixed_nv_polish",
            "_committed_nv_search",
            "_recombine_with_pool",
            "_generate_dense_pool_columns",
            "_seed_savings_routes",
            "_seed_nv_targeted_construction",
            "_seed_pool_large_destroy",
            "_capture_native",
            "_finish_native",
            "_select_action",
            "_op_state",
        )
        for key in methods:
            self.patch(self.solver, key, f"solver.{key}")
        for attr in ("ctrl", "op_ctrl", "lac", "archive"):
            owner = getattr(self.solver, attr, None)
            if owner is not None:
                for key in ("act", "train_step", "observe", "decide", "update"):
                    self.patch(owner, key, f"{attr}.{key}")
        targets = {
            "local_search": (
                "local_search",
                "_ejection_chain_eliminate",
                "_try_chain_elimination",
                "_iterative_route_elimination",
                "_buffered_route_elimination",
                "_guided_ejection_search",
                "_try_buffered_route_elimination",
                "_try_route_merge",
                "td_converge_polish",
                "td_inter_route_polish",
                "_intra_route_optimize",
                "_try_route_compact",
                "_cross_exchange",
                "_cross_tail",
                "_two_opt_best",
                "_best_relocate",
                "_best_swap",
                "_best_swap_21",
                "_best_or_opt",
                "_intra_route_or_opt",
                "_build_merged_route",
                "_insertion_options",
            ),
            "pool": ("recombine_with_route_pool", "_milp_recombine", "_greedy_recombine", "milp"),
            "gnn": ("get_gnn_features",),
            "solvers": ("build_greedy", "local_search", "recombine_with_route_pool"),
        }
        for module_name, names in targets.items():
            module = importlib.import_module(f"vrptw.{module_name}")
            for key in names:
                self.patch(module, key, f"{module_name}.{key}")
        pool = importlib.import_module("vrptw.pool")
        self.patch(pool.RoutePool, "add_plan", "pool.add_plan")
        local = importlib.import_module("vrptw.local_search")
        self.patch(local._PlanCache, "from_plan", "local_search._PlanCache.from_plan")
        core = importlib.import_module("vrptw.core")
        for key in ("route_arrays", "cost", "feasible"):
            self.patch(core.Plan, key, f"plan.{key}")
        solvers = importlib.import_module("vrptw.solvers")
        # Patch the Python list dispatch only; compiled Numba globals stay intact.
        for index, original in enumerate(list(solvers.REPAIR)):

            def repair(*args, _original=original, **kwargs):
                if self._solve_only and (not self.stack or self.events[self.stack[0] - 1]["name"] != "solve"):
                    return _original(*args, **kwargs)
                return self.call(f"repair.{_original.__name__}", _original, *args, **kwargs)

            solvers.REPAIR[index] = repair
            self._undo.append(lambda i=index, fn=original: solvers.REPAIR.__setitem__(i, fn))

    def restore(self):
        for undo in reversed(self._undo):
            undo()
        self._undo.clear()
        self._patched.clear()
        self._solve_only = False

    def write(self, path: Path):
        cutoff = self.solver._deadline
        if cutoff is None:
            raise ValueError("Phase diagnostics require an explicit finite cutoff")
        records = [
            {**e, "solve_start_perf": self.solver._t_start, "solve_deadline_perf": cutoff}
            for e in _measure(self.events, cutoff)
        ]
        if not records or self.stack:
            raise ValueError("Missing root span or unfinished trace")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)


def audit_trace(path: Path):
    """Recompute parent intervals and exclusive post-cutoff arithmetic from CSV."""
    with path.open() as stream:
        raw = list(csv.DictReader(stream))
    if not raw:
        raise ValueError("empty phase trace")
    events = []
    for row in raw:
        event = {**row, "id": int(row["id"]), "parent_id": int(row["parent_id"])}
        for key in (
            "start_perf",
            "end_perf",
            "solve_start_perf",
            "solve_deadline_perf",
            "post_cutoff_inclusive_sec",
            "post_cutoff_exclusive_sec",
        ):
            event[key] = float(row[key])
            if not math.isfinite(event[key]):
                raise ValueError("nonfinite phase timestamp")
        events.append(event)
    start, cutoff = events[0]["solve_start_perf"], events[0]["solve_deadline_perf"]
    if cutoff <= start or [e["id"] for e in events] != list(range(1, len(events) + 1)):
        raise ValueError("invalid cutoff/span IDs")
    by_id = {e["id"]: e for e in events}
    children_by_parent = {}
    for event in events:
        children_by_parent.setdefault(event["parent_id"], []).append(event)
    roots = [e for e in events if not e["parent_id"]]
    if len(roots) != 1 or roots[0] is not events[0]:
        raise ValueError("invalid root")
    for e in events:
        if e["end_perf"] < e["start_perf"] or (e["solve_start_perf"], e["solve_deadline_perf"]) != (start, cutoff):
            raise ValueError("clock reversal/domain mismatch")
        if e["parent_id"]:
            parent = by_id.get(e["parent_id"])
            if (
                parent is None
                or parent["id"] >= e["id"]
                or not (parent["start_perf"] <= e["start_perf"] <= e["end_perf"] <= parent["end_perf"])
            ):
                raise ValueError("invalid parent interval")
        children = children_by_parent.get(e["id"], [])
        for first, second in zip(children, children[1:]):
            if first["end_perf"] > second["start_perf"]:
                raise ValueError("overlapping siblings")
    calculated = _measure(events, cutoff)
    for original, expected in zip(events, calculated, strict=True):
        for key in ("post_cutoff_inclusive_sec", "post_cutoff_exclusive_sec"):
            if not math.isclose(original[key], expected[key], abs_tol=1e-8):
                raise ValueError("post-cutoff arithmetic mismatch")
    post = _post(events[0]["start_perf"], events[0]["end_perf"], cutoff)
    if not math.isclose(math.fsum(e["post_cutoff_exclusive_sec"] for e in events), post, abs_tol=1e-7):
        raise ValueError("exclusive intervals do not conserve root post-cutoff time")
    return {
        "spans": len(events),
        "solve_start_perf": start,
        "solve_deadline_perf": cutoff,
        "root_end_perf": events[0]["end_perf"],
        "post_cutoff_sec": post,
        "post_cutoff_spans": [
            {
                k: e[k]
                for k in (
                    "id",
                    "parent_id",
                    "name",
                    "start_perf",
                    "end_perf",
                    "deadline_arg_perf",
                    "post_cutoff_exclusive_sec",
                )
            }
            for e in events
            if e["post_cutoff_exclusive_sec"] > 0
        ],
    }
