"""Shared conservative integer model for external VRPTW comparators."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .core import Inst

DISTANCE_SCALE = 100_000
SAFE_INT = np.iinfo(np.int64).max // 8


@dataclass(frozen=True)
class IntegerVRPTW:
    distance: np.ndarray
    transit: np.ndarray
    ready: np.ndarray
    due: np.ndarray
    demands: np.ndarray
    capacity: int
    fleet_cost: int
    travel_bound: int
    scale: int = DISTANCE_SCALE


def quantize_vrptw(inst: Inst) -> IntegerVRPTW:
    if inst.n < 1 or not math.isfinite(inst.capacity) or inst.capacity <= 0:
        raise ValueError("Integer baselines require customers and finite positive capacity")
    arrays = (inst.dist, inst.demands, inst.ready_times, inst.due_times, inst.service_times)
    if any(not np.isfinite(array).all() or (array < 0).any() for array in arrays):
        raise ValueError("Integer baseline inputs must be finite and nonnegative")
    if inst.ready_times[0] != 0 or inst.service_times[0] != 0 or inst.demands[0] != 0:
        raise ValueError("The native evaluation contract requires zero depot ready/service/demand")
    if inst.capacity != round(inst.capacity) or not np.equal(inst.demands, np.rint(inst.demands)).all():
        raise ValueError("Fractional demand/capacity is unsupported; refusing silent truncation")
    if max(float(inst.demands.max()), inst.capacity) > SAFE_INT:
        raise ValueError("Capacity outside safe integer range")

    def scaled(values, rounding):
        result = rounding(values * DISTANCE_SCALE)
        if (result > SAFE_INT).any():
            raise ValueError("Scaled baseline integer range overflow")
        return result.astype(np.int64)

    distance = scaled(inst.dist, np.rint)
    # An inner approximation: never make travel/service shorter or a window wider.
    transit = scaled(inst.dist, np.ceil) + scaled(inst.service_times, np.ceil)[:, None]
    ready, due = scaled(inst.ready_times, np.ceil), scaled(inst.due_times, np.floor)
    if (ready > due).any():
        raise ValueError("A time window is empty after conservative quantization")
    travel_bound = 2 * inst.n * int(distance.max())
    fleet_cost = travel_bound + 1
    if inst.n * fleet_cost + travel_bound > SAFE_INT:
        raise ValueError("Fleet-first objective would overflow safe integer range")
    return IntegerVRPTW(
        distance, transit, ready, due, inst.demands.astype(np.int64), int(inst.capacity), fleet_cost, travel_bound
    )
