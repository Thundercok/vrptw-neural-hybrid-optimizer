"""Auditable integer OR-Tools adapter; not an exact double-precision model."""

from __future__ import annotations

import math
import time

from .config import ALGO_ORTOOLS, Config
from .core import Inst, Plan
from .integer_baseline import DISTANCE_SCALE
from .integer_baseline import IntegerVRPTW as ORToolsData
from .integer_baseline import quantize_vrptw as prepare_ortools_data


class ORToolsNoSolutionError(RuntimeError):
    """No original-feasible complete incumbent was captured before the cutoff."""


class ORToolsSolver:
    def __init__(self, inst: Inst, cfg: Config):
        import ortools
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
        from ortools.util import optional_boolean_pb2

        self.inst, self.cfg = inst, cfg
        self.pywrapcp, self.enums, self.version = pywrapcp, routing_enums_pb2, ortools.__version__
        self.optional_boolean = optional_boolean_pb2
        self.diagnostics = {}
        self.trajectory_log = []
        self.search_iterations = 0
        self.time_limit_hit = False
        self.elapsed_sec = 0.0
        self._best_routes = self._best_plan = None
        self._best_objective = math.inf

    def _build_model(self, data: ORToolsData):
        manager = self.pywrapcp.RoutingIndexManager(self.inst.n + 1, self.inst.n, 0)
        routing = self.pywrapcp.RoutingModel(manager)
        routing.solver().ReSeed(self._seed)
        cost_index = routing.RegisterTransitMatrix(data.distance.tolist())
        routing.SetArcCostEvaluatorOfAllVehicles(cost_index)
        routing.SetFixedCostOfAllVehicles(data.fleet_cost)

        def demand(index):
            return int(data.demands[manager.IndexToNode(index)])

        demand_index = routing.RegisterUnaryTransitCallback(demand)
        routing.AddDimensionWithVehicleCapacity(demand_index, 0, [data.capacity] * self.inst.n, True, "Capacity")
        transit_index = routing.RegisterTransitMatrix(data.transit.tolist())
        horizon = int(data.due[0])
        routing.AddDimension(transit_index, horizon, horizon, True, "Time")
        dimension = routing.GetDimensionOrDie("Time")
        for node in range(1, self.inst.n + 1):
            dimension.CumulVar(manager.NodeToIndex(node)).SetRange(int(data.ready[node]), int(data.due[node]))
        for vehicle in range(self.inst.n):
            dimension.CumulVar(routing.Start(vehicle)).SetRange(0, 0)
            dimension.CumulVar(routing.End(vehicle)).SetRange(0, horizon)
        parameters = self.pywrapcp.DefaultRoutingSearchParameters()
        parameters.first_solution_strategy = self.enums.FirstSolutionStrategy.LOCAL_CHEAPEST_INSERTION
        parameters.local_search_metaheuristic = self.enums.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        # Freeze the CP backend; SAT seed settings would not seed this search.
        parameters.use_cp = self.optional_boolean.BOOL_TRUE
        parameters.use_cp_sat = self.optional_boolean.BOOL_FALSE
        parameters.use_generalized_cp_sat = self.optional_boolean.BOOL_FALSE
        parameters.log_search = False
        return manager, routing, parameters

    def _read_routes(self, manager, routing):
        routes = []
        for vehicle in range(self.inst.n):
            route = []
            index = routing.Start(vehicle)
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node:
                    route.append(node)
                index = routing.NextVar(index).Value()
            if route:
                routes.append(route)
        return routes

    def _capture_solution(self, manager, routing):
        if time.perf_counter() >= self._deadline:
            return
        objective = routing.CostVar().Value()
        if objective >= self._best_objective:
            return
        routes = self._read_routes(manager, routing)
        if time.perf_counter() >= self._deadline:
            return
        plan = Plan(routes, self.inst, ALGO_ORTOOLS)
        exact_cover = sorted(node for route in routes for node in route) == list(range(1, self.inst.n + 1))
        if not exact_cover or not plan.feasible:
            self.diagnostics["invalid_original_solution_callbacks"] += 1
            return
        cost = float(plan.cost)
        captured = time.perf_counter()
        if captured >= self._deadline:
            return
        self._best_objective, self._best_routes, self._best_plan = objective, routes, plan
        self.diagnostics["incumbent_capture_sec"] = captured - self._start
        self.trajectory_log.append({"t_sec": captured - self._start, "nv": plan.nv, "td": cost, "phase": "incumbent"})

    def solve(self, seed: int | None = None) -> tuple[Plan, list[float]]:
        budget = self.cfg.time_limit if self.cfg.time_limit is not None else self.cfg.ortools_time_limit
        if not math.isfinite(budget) or budget <= 0:
            raise ValueError("OR-Tools needs a finite positive solve budget")
        seed = self.cfg.seed if seed is None else seed
        if seed is None or int(seed) != seed or not 0 <= seed <= 2_147_483_647:
            raise ValueError("OR-Tools CP seed must be a nonnegative signed 32-bit integer")
        self._seed = int(seed)
        self._start = time.perf_counter()
        self._deadline = self._start + budget
        self._best_routes = self._best_plan = None
        self._best_objective = math.inf
        self.trajectory_log = []
        self.search_iterations = 0
        self.time_limit_hit = False
        self.diagnostics = {
            "status": "building",
            "ortools_version": self.version,
            "requested_budget_sec": budget,
            "cp_seed": self._seed,
            "seed_scope": "CP Solver.ReSeed only; distinct search trajectories are not guaranteed",
            "search_sec": 0.0,
            "postprocess_sec": 0.0,
            "invalid_original_solution_callbacks": 0,
            "backend": "CP routing with local cheapest insertion and guided local search",
            "timer_scope": "solve includes quantization/model-build/search/callback validation/return; excludes dependency imports",
            "incumbent_policy": "only original-feasible exact covers fully captured before the solve deadline",
            "distance_scale": DISTANCE_SCALE,
            "distance_rounding": "nearest",
            "time_rounding": "transit/ready ceil; due floor",
            "quantity_policy": "exact integral nonnegative demands/capacity; no truncation",
            "rounding_policy": "conservative time inner approximation; may exclude original-feasible routes",
            "window_endpoint_error_bound": 1 / DISTANCE_SCALE,
        }
        data = prepare_ortools_data(self.inst)
        self.diagnostics.update(
            fleet_cost=data.fleet_cost,
            travel_bound=data.travel_bound,
            distance_error_bound=self.inst.n / data.scale,
            transit_inflation_bound_per_route=(2 * self.inst.n + 1) / data.scale,
        )
        manager, routing, parameters = self._build_model(data)
        built = time.perf_counter()
        self.diagnostics["model_build_sec"] = built - self._start
        routing.AddAtSolutionCallback(lambda: self._capture_solution(manager, routing))
        search_start = time.perf_counter()
        remaining = self._deadline - search_start
        if remaining <= 0:
            self.elapsed_sec = search_start - self._start
            self.time_limit_hit = True
            self.diagnostics["elapsed_sec"] = self.elapsed_sec
            self.diagnostics["status"] = "budget_exhausted_before_search"
            raise ORToolsNoSolutionError("OR-Tools solve budget exhausted while building the model")
        search_ns = max(1, int(remaining * 1_000_000_000))
        parameters.time_limit.FromNanoseconds(search_ns)
        self.diagnostics["search_budget_ns"] = search_ns
        # The returned assignment can be later than the cutoff; use only our
        # validated, deadline-checked incumbent, never that late assignment.
        routing.SolveWithParameters(parameters)
        search_end = time.perf_counter()
        self.diagnostics.update(
            search_sec=search_end - search_start,
            search_parameters=str(parameters),
            routing_status=int(routing.status()),
            cp_branches=int(routing.solver().Branches()),
            cp_failures=int(routing.solver().Failures()),
        )
        plan = self._best_plan
        end = time.perf_counter()
        self.elapsed_sec = end - self._start
        self.time_limit_hit = end >= self._deadline
        self.diagnostics["postprocess_sec"] = end - search_end
        self.diagnostics["elapsed_sec"] = self.elapsed_sec
        if plan is None:
            self.diagnostics["status"] = "no_original_feasible_incumbent_before_cutoff"
            raise ORToolsNoSolutionError("OR-Tools found no original-feasible incumbent before the solve cutoff")
        self.diagnostics["status"] = "completed"
        self.diagnostics["selected_integer_objective"] = self._best_objective
        return plan, [row["td"] for row in self.trajectory_log]
