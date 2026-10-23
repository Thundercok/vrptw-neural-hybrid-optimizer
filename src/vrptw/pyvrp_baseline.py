"""Pinned PyVRP ILS comparator with deadline-checked original-space incumbents."""

from __future__ import annotations

import math
import time
from dataclasses import asdict
from importlib.metadata import version

import numpy as np

from .config import Config
from .core import Inst, Plan
from .integer_baseline import DISTANCE_SCALE, SAFE_INT, quantize_vrptw

PYVRP_VERSION = "0.14.1"


class PyVRPNoSolutionError(RuntimeError):
    """No original-feasible exact cover was fully captured before the deadline."""


class PyVRPSolver:
    def __init__(self, inst: Inst, cfg: Config):
        import pyvrp

        self.version = version("pyvrp")
        if self.version != PYVRP_VERSION:
            raise RuntimeError(f"Expected PyVRP {PYVRP_VERSION}, got {self.version}; re-audit before changing versions")
        self.pyvrp, self.inst, self.cfg = pyvrp, inst, cfg
        self.diagnostics = {}
        self.trajectory_log = []
        self.search_iterations = 0
        self.time_limit_hit = False
        self.elapsed_sec = 0.0
        self._best_plan = None
        self._best_objective = math.inf
        self._certifier = None
        self.native_certification = None

    def _build_model(self):
        q = quantize_vrptw(self.inst)
        if not np.isfinite(self.inst.coords).all():
            raise ValueError("PyVRP coordinates must be finite")
        # Guard worst-case penalties as well as the feasible scalar objective.
        max_time_warp = 2 * self.inst.n * int(q.transit.max()) + sum(map(int, q.ready))
        max_penalty = self.pyvrp.SolveParams().penalty.max_penalty
        bound = self.inst.n * q.fleet_cost + q.travel_bound
        if bound + max_penalty * (max_time_warp + sum(map(int, q.demands))) > SAFE_INT:
            raise ValueError("PyVRP penalised cost outside safe integer range")
        service = np.ceil(self.inst.service_times * q.scale).astype(np.int64)
        travel_duration = q.transit - service[:, None]
        p = self.pyvrp
        data = p.ProblemData(
            locations=[p.Location(float(x), float(y)) for x, y in self.inst.coords],
            clients=[
                p.Client(
                    location=i,
                    delivery=[int(q.demands[i])],
                    service_duration=int(service[i]),
                    tw_early=int(q.ready[i]),
                    tw_late=int(q.due[i]),
                    required=True,
                )
                for i in range(1, self.inst.n + 1)
            ],
            depots=[p.Depot(location=0, tw_early=0, tw_late=int(q.due[0]))],
            vehicle_types=[
                p.VehicleType(
                    num_available=self.inst.n,
                    capacity=[q.capacity],
                    fixed_cost=q.fleet_cost,
                    tw_early=0,
                    tw_late=int(q.due[0]),
                    start_late=0,
                    unit_distance_cost=1,
                    unit_duration_cost=0,
                )
            ],
            distance_matrices=[q.distance],
            duration_matrices=[travel_duration],
        )
        return data, q

    def _read_routes(self, solution):
        # PyVRP 0.14 uses zero-based client activities, separate from locations.
        return [[int(activity.idx) + 1 for activity in route if activity.is_client()] for route in solution.routes()]

    def _capture_solution(self, solution):
        if time.perf_counter() >= self._deadline or solution is None or not solution.is_feasible():
            return
        distance = int(solution.distance())
        objective = distance + int(solution.fixed_vehicle_cost())
        if objective >= self._best_objective:
            return
        routes = self._read_routes(solution)
        if time.perf_counter() >= self._deadline:
            return
        plan = Plan(routes, self.inst, "PyVRP")
        exact_cover = sorted(node for route in routes for node in route) == list(range(1, self.inst.n + 1))
        if not exact_cover or not plan.feasible:
            self.diagnostics["invalid_original_solution_callbacks"] += 1
            return
        cost = float(plan.cost)
        captured = time.perf_counter()
        if captured >= self._deadline:
            return
        self._best_objective, self._best_plan = objective, plan
        self.diagnostics.update(
            incumbent_capture_sec=captured - self._start,
            selected_integer_objective=objective,
            selected_integer_distance=distance,
        )
        self.trajectory_log.append({"t_sec": captured - self._start, "nv": plan.nv, "td": cost, "phase": "incumbent"})
        if self._certifier is not None:
            self._certifier.consider(plan, phase="pyvrp_callback")

    def solve(self, seed: int | None = None, *, _certifier=None) -> tuple[Plan, list[float]]:
        budget = self.cfg.time_limit
        if budget is None or not math.isfinite(budget) or budget <= 0:
            raise ValueError("PyVRP needs a finite positive solve budget")
        seed = self.cfg.seed if seed is None else seed
        if seed is None or int(seed) != seed or not 0 <= seed <= 4_294_967_295:
            raise ValueError("PyVRP seed must be a nonnegative unsigned 32-bit integer")
        self._certifier = _certifier
        self.native_certification = _certifier.diagnostics if _certifier is not None else None
        self._start = _certifier.start if _certifier is not None else time.perf_counter()
        self._deadline = _certifier.deadline if _certifier is not None else self._start + budget
        self._best_plan, self._best_objective = None, math.inf
        self.trajectory_log = []
        self.search_iterations = 0
        self.time_limit_hit = False
        self.diagnostics = {
            "status": "building",
            "pyvrp_version": self.version,
            "seed": int(seed),
            "backend": "PyVRP iterated local search (ILS), not historical HGS",
            "requested_budget_sec": budget,
            "search_sec": 0.0,
            "invalid_original_solution_callbacks": 0,
            "timer_scope": "solve includes quantization/model/build/initialisation/search/callback validation; excludes imports",
            "incumbent_policy": "only original-feasible exact covers fully captured before absolute solve deadline",
            "stop_policy": "absolute deadline checked between ILS iterations; C++ calls are not preemptible",
            "distance_scale": DISTANCE_SCALE,
            "distance_rounding": "nearest",
            "time_rounding": "travel/service/ready ceil; due floor",
            "rounding_policy": "conservative time inner approximation; may exclude original-feasible routes",
            "quantity_policy": "exact integral nonnegative demands/capacity; no truncation",
            "window_endpoint_error_bound": 1 / DISTANCE_SCALE,
        }
        if _certifier is not None and time.perf_counter() >= self._deadline:
            raise PyVRPNoSolutionError("PyVRP parent budget exhausted before model building")
        data, q = self._build_model()
        self.diagnostics.update(
            fleet_cost=q.fleet_cost,
            travel_bound=q.travel_bound,
            distance_error_bound=self.inst.n / q.scale,
            transit_inflation_bound_per_route=(2 * self.inst.n + 1) / q.scale,
        )
        owner = self

        class Callbacks(self.pyvrp.IteratedLocalSearchCallbacks):
            def on_start(self, ils):
                owner.diagnostics["initialisation_complete_sec"] = time.perf_counter() - owner._start
                owner._capture_solution(ils.initial_solution)

            def on_best(self, best):
                owner._capture_solution(best)

        params = self.pyvrp.SolveParams(ils=self.pyvrp.IteratedLocalSearchParams(callbacks=Callbacks()))
        self.diagnostics["parameters"] = {
            "ils": {k: v for k, v in asdict(params.ils).items() if k != "callbacks"},
            **{
                name: {k: getattr(obj, k) for k in dir(obj) if not k.startswith("_") and not callable(getattr(obj, k))}
                for name, obj in (
                    ("penalty", params.penalty),
                    ("neighbourhood", params.neighbourhood),
                    ("perturbation", params.perturbation),
                )
            },
            "operators": [op.__name__ for op in params.operators],
            "supported_operators": [op.__name__ for op in params.operators if op.supports(data)],
            "collect_stats": False,
            "display": False,
            "initial_solution": None,
        }
        search_start = time.perf_counter()
        self.diagnostics["model_build_sec"] = search_start - self._start
        if search_start >= self._deadline:
            self.elapsed_sec, self.time_limit_hit = search_start - self._start, True
            self.diagnostics.update(status="budget_exhausted_before_search", elapsed_sec=self.elapsed_sec)
            raise PyVRPNoSolutionError("PyVRP solve budget exhausted while building model")
        result = self.pyvrp.solve(
            data,
            stop=lambda _: time.perf_counter() >= self._deadline,
            seed=int(seed),
            collect_stats=False,
            display=False,
            params=params,
            initial_solution=None,
        )
        search_end = time.perf_counter()
        self.search_iterations = int(result.num_iterations)
        self.elapsed_sec = search_end - self._start
        self.time_limit_hit = search_end >= self._deadline
        self.diagnostics.update(
            search_sec=search_end - search_start,
            elapsed_sec=self.elapsed_sec,
            ils_runtime_sec=float(result.runtime),
            ils_iterations=self.search_iterations,
        )
        # Never substitute result.best: its final improvement may be post-cutoff.
        if self._best_plan is None:
            self.diagnostics["status"] = "no_original_feasible_incumbent_before_cutoff"
            raise PyVRPNoSolutionError("PyVRP found no original-feasible incumbent before solve cutoff")
        self.diagnostics["status"] = "completed"
        plan = _certifier.finish() if _certifier is not None else self._best_plan
        return plan, [row["td"] for row in self.trajectory_log]
