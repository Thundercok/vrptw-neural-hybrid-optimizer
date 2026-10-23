"""Original-space incumbent snapshots captured inside the native solve budget.

This certifies route availability, not a hard return deadline: cooperative native
and backend calls can still return late. No Plan feasibility/objective cache is
trusted, and no work performed at return can create a pre-cutoff certificate.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Sequence
from copy import deepcopy
from numbers import Integral

from .core import Inst, Plan


class NativeNoSolutionError(RuntimeError):
    """No complete, original-feasible incumbent was certified within the budget."""


def routes_sha256(routes: Sequence[Sequence[int]]) -> str:
    """Hash ordered customer-only routes as UTF-8 compact JSON (no rounding)."""
    return hashlib.sha256(json.dumps(routes, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_routes(routes: Sequence[Sequence[int]], inst: Inst) -> float | None:
    """Recompute exact cover, original double-precision distance and feasibility.

    Native time semantics: depart depot at zero; wait for each customer ready
    time, start service by its due time, and return by the depot due time.
    """
    nodes = [node for route in routes for node in route]
    if any(not route for route in routes) or sorted(nodes) != list(range(1, inst.n + 1)):
        return None
    if not math.isfinite(inst.capacity) or inst.capacity <= 0 or not math.isfinite(inst.due_times[0]):
        return None
    route_costs = []
    for route in routes:
        load, elapsed, previous = 0.0, 0.0, 0
        legs = []
        for node in route:
            demand, ready, due, service, travel = map(
                float,
                (
                    inst.demands[node],
                    inst.ready_times[node],
                    inst.due_times[node],
                    inst.service_times[node],
                    inst.dist[previous, node],
                ),
            )
            if any(not math.isfinite(value) or value < 0 for value in (demand, ready, due, service, travel)):
                return None
            load += demand
            elapsed = max(elapsed + travel, ready)
            if load > inst.capacity or elapsed > due:
                return None
            elapsed += service
            legs.append(travel)
            previous = node
        home = float(inst.dist[previous, 0])
        if not math.isfinite(home) or home < 0 or elapsed + home > inst.due_times[0]:
            return None
        route_costs.append(math.fsum([*legs, home]))
    cost = math.fsum(route_costs)
    return cost if math.isfinite(cost) else None


class NativeIncumbent:
    """One solve's independent, fleet-first incumbent and serialisable evidence."""

    def __init__(
        self,
        inst: Inst,
        *,
        start: float,
        deadline: float | None,
        clock: Callable[[], float],
        on_capture: Callable[[dict], None] | None = None,
    ):
        self.inst, self.start, self.deadline, self.clock = inst, start, deadline, clock
        self.on_capture = on_capture
        self._plan: Plan | None = None
        self._routes: tuple[tuple[int, ...], ...] | None = None
        self.trajectory: list[dict] = []
        self.diagnostics = {
            "schema_version": 1,
            "status": "searching",
            "policy": "original-feasible exact cover; snapshot, validation and route hash completed strictly before cutoff",
            "clock": "perf_counter",
            "cutoff_sec": None if deadline is None else deadline - start,
            "hard_return_deadline": False,
            "certificate": None,
            "rejected_late": 0,
            "rejected_invalid": 0,
        }

    def expired(self) -> bool:
        return self.deadline is not None and self.clock() >= self.deadline

    def consider(self, candidate: Plan, *, phase: str, iteration: int = 0) -> bool:
        if self.expired():
            self.diagnostics["rejected_late"] += 1
            return False
        if candidate.inst is not self.inst or any(
            not isinstance(node, Integral) or isinstance(node, bool) for route in candidate.routes for node in route
        ):
            self.diagnostics["rejected_invalid"] += 1
            return False
        routes = tuple(tuple(int(node) for node in route) for route in candidate.routes)
        if routes == self._routes:
            return False
        cost = validate_routes(routes, self.inst)
        if cost is None:
            self.diagnostics["rejected_invalid"] += 1
            return False
        if self._plan is not None and not (
            len(routes) < self._plan.nv or (len(routes) == self._plan.nv and cost < self._plan.cost - 1e-6)
        ):
            return False
        # Complete *all* substantive work before sampling the certification time.
        snapshot = Plan([list(route) for route in routes], self.inst, candidate.algo)
        snapshot._cost, snapshot._ok = cost, True
        certificate = {
            "clock": "perf_counter",
            "cutoff_sec": self.diagnostics["cutoff_sec"],
            "routes_sha256": routes_sha256(routes),
            "nv": snapshot.nv,
            "td": cost,
            "phase": phase,
            "iter": int(iteration),
            "validation": {"exact_cover": True, "route_feasible": True, "objective_recomputed": True},
        }
        captured = self.clock()
        if self.deadline is not None and captured >= self.deadline:
            self.diagnostics["rejected_late"] += 1
            return False
        certificate["captured_sec"] = captured - self.start
        self._routes, self._plan = routes, snapshot
        self.diagnostics["certificate"] = certificate
        self.trajectory.append(
            {
                "t_sec": captured - self.start,
                "nv": snapshot.nv,
                "td": cost,
                "iter": int(iteration),
                "phase": phase,
                "routes_sha256": certificate["routes_sha256"],
            }
        )
        if self.on_capture is not None:
            self.on_capture({"routes": [list(route) for route in routes], "certificate": deepcopy(certificate)})
        return True

    def finish(self) -> Plan:
        self.diagnostics["elapsed_sec"] = self.clock() - self.start
        if self._plan is None:
            self.diagnostics["status"] = "no_certified_incumbent"
            raise NativeNoSolutionError(
                "Native solve has no certified feasible exact-cover incumbent within its budget"
            )
        self.diagnostics["status"] = "certified"
        return self._plan
