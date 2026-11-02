"""Full-budget Guided Ejection Search for fleet minimisation (Nagata & Bräysy 2009).

The small GES in ``local_search`` runs as a late fallback with at most 1500 steps
and ejects consecutive customers only. This module is the standalone form: it spends
a wall-clock budget, ejects any subset of up to ``k_max`` customers from one route,
and perturbs after every ejection. It reads no reference fleet: the only stopping
floor is the capacity bound ceil(total demand / capacity).
"""

from __future__ import annotations

import math
import time

import numpy as np
from numba import njit

from .core import Inst, Plan
from .local_search import _covers_all_customers

STEPS_PER_CHUNK = 200


@njit(cache=True)
def _route_ok_arr(route, m, dem, cap, ready, due, svc, dist) -> bool:
    t, prev, load = 0.0, 0, 0.0
    for i in range(m):
        node = route[i]
        load += dem[node]
        if load > cap:
            return False
        t += dist[prev, node]
        if t > due[node]:
            return False
        t = max(t, ready[node]) + svc[node]
        prev = node
    return t + dist[prev, 0] <= due[0]


@njit(cache=True)
def _profile(route, m, ready, due, svc, dist, dep, latest):
    # dep[i]: departure from position i - 1 (dep[0] leaves the depot at time 0).
    # latest[i]: latest arrival at position i keeping the suffix feasible.
    t, prev = 0.0, 0
    dep[0] = 0.0
    for i in range(m):
        node = route[i]
        t = max(t + dist[prev, node], ready[node]) + svc[node]
        dep[i + 1] = t
        prev = node
    latest[m] = due[0]
    nxt = 0
    for i in range(m - 1, -1, -1):
        node = route[i]
        latest[i] = min(due[node], latest[i + 1] - dist[node, nxt] - svc[node])
        nxt = node


@njit(cache=True)
def _try_insert(v, routes, lens, cheapest, dem, cap, ready, due, svc, dist, dep, latest):
    """Feasible insertion, cheapest or uniform random; returns False when none exists."""
    seen, pick_r, pick_p = 0, -1, -1
    best_delta = np.inf
    for r in range(routes.shape[0]):
        m = lens[r]
        if m == 0:
            continue
        load = 0.0
        for i in range(m):
            load += dem[routes[r, i]]
        if load + dem[v] > cap:
            continue
        _profile(routes[r], m, ready, due, svc, dist, dep, latest)
        prev = 0
        for p in range(m + 1):
            a = dep[p] + dist[prev, v]
            if a <= due[v]:
                nxt = routes[r, p] if p < m else 0
                if max(a, ready[v]) + svc[v] + dist[v, nxt] <= latest[p]:
                    if cheapest:
                        delta = dist[prev, v] + dist[v, nxt] - dist[prev, nxt]
                        if delta < best_delta:
                            best_delta, pick_r, pick_p = delta, r, p
                    else:
                        seen += 1
                        if np.random.randint(seen) == 0:
                            pick_r, pick_p = r, p
            if p < m:
                prev = routes[r, p]
    if pick_r < 0:
        return False
    m = lens[pick_r]
    routes[pick_r, pick_p + 1 : m + 1] = routes[pick_r, pick_p : m].copy()
    routes[pick_r, pick_p] = v
    lens[pick_r] = m + 1
    return True


@njit(cache=True)
def _best_ejection(v, routes, lens, penalty, k_max, dem, cap, ready, due, svc, dist, dep, latest, node_budget):
    """Minimum-penalty ejection of at most k_max customers from one route for v.

    Depth-first over keep/eject at each position with pruning on time and on the
    best penalty sum so far. Returns (route, insert position, ejected-mask length),
    with the chosen mask stored in the returned array.
    """
    best_sum = np.iinfo(np.int64).max
    best_r, best_ins = -1, -1
    best_mask = np.zeros(routes.shape[1], dtype=np.bool_)
    max_m = routes.shape[1]
    st_t = np.zeros(max_m + 2)
    st_prev = np.zeros(max_m + 2, dtype=np.int64)
    st_k = np.zeros(max_m + 2, dtype=np.int64)
    st_sum = np.zeros(max_m + 2, dtype=np.int64)
    st_rem = np.zeros(max_m + 2)
    choice = np.zeros(max_m + 2, dtype=np.int8)
    budget = node_budget
    start_r = np.random.randint(routes.shape[0])
    for rr in range(routes.shape[0]):
        r = (start_r + rr) % routes.shape[0]
        m = lens[r]
        if m == 0:
            continue
        route = routes[r]
        load = 0.0
        for i in range(m):
            load += dem[route[i]]
        _profile(route, m, ready, due, svc, dist, dep, latest)
        for ins in range(m + 1):
            if budget <= 0:
                return best_sum, best_r, best_ins, best_mask
            # Time at v: walk with v placed before position ins.
            idx = 0
            st_t[0], st_prev[0], st_k[0], st_sum[0], st_rem[0] = 0.0, 0, 0, 0, 0.0
            choice[0] = 0
            while idx >= 0:
                budget -= 1
                if choice[idx] == 0:
                    # First visit to this depth: place v and test completion.
                    t, prev = st_t[idx], st_prev[idx]
                    if idx == ins:
                        a = t + dist[prev, v]
                        if a > due[v]:
                            idx -= 1
                            continue
                        t = max(a, ready[v]) + svc[v]
                        prev = v
                        st_t[idx], st_prev[idx] = t, prev
                    if idx >= ins and load - st_rem[idx] + dem[v] <= cap:
                        nxt = route[idx] if idx < m else 0
                        if t + dist[prev, nxt] <= latest[idx]:
                            if st_sum[idx] < best_sum:
                                best_sum, best_r, best_ins = st_sum[idx], r, ins
                                best_mask[:] = False
                                for j in range(idx):
                                    best_mask[j] = choice[j] == 2
                            idx -= 1
                            continue
                    if idx == m:
                        idx -= 1
                        continue
                    choice[idx] = 1
                    node = route[idx]
                    a = t + dist[prev, node]
                    if a <= due[node]:
                        st_t[idx + 1] = max(a, ready[node]) + svc[node]
                        st_prev[idx + 1] = node
                        st_k[idx + 1], st_sum[idx + 1], st_rem[idx + 1] = st_k[idx], st_sum[idx], st_rem[idx]
                        choice[idx + 1] = 0
                        idx += 1
                    continue
                if choice[idx] == 1:
                    # Second visit: eject this position.
                    choice[idx] = 2
                    node = route[idx]
                    s = st_sum[idx] + penalty[node]
                    if st_k[idx] < k_max and s < best_sum:
                        st_t[idx + 1], st_prev[idx + 1] = st_t[idx], st_prev[idx]
                        st_k[idx + 1], st_sum[idx + 1] = st_k[idx] + 1, s
                        st_rem[idx + 1] = st_rem[idx] + dem[node]
                        choice[idx + 1] = 0
                        idx += 1
                    continue
                idx -= 1
    return best_sum, best_r, best_ins, best_mask


@njit(cache=True)
def _route_len(route, m, dist):
    total, prev = 0.0, 0
    for i in range(m):
        total += dist[prev, route[i]]
        prev = route[i]
    return total + dist[prev, 0]


@njit(cache=True)
def _perturb(routes, lens, n_moves, temp, dem, cap, ready, due, svc, dist, scratch_a, scratch_b):
    """Random feasible relocate, exchange and 2-opt* moves; temp <= 0 applies them regardless of cost,
    otherwise a worsening move of delta is applied with probability exp(-delta / temp)."""
    live = np.flatnonzero(lens > 0)
    if len(live) < 2:
        return
    for _ in range(n_moves):
        a = live[np.random.randint(len(live))]
        b = live[np.random.randint(len(live))]
        if a == b:
            continue
        la, lb = lens[a], lens[b]
        kind = np.random.randint(3)
        if kind == 0:  # relocate a[i] into b at j
            if la < 2:
                continue
            i, j = np.random.randint(la), np.random.randint(lb + 1)
            scratch_a[:i] = routes[a, :i]
            scratch_a[i : la - 1] = routes[a, i + 1 : la]
            scratch_b[:j] = routes[b, :j]
            scratch_b[j] = routes[a, i]
            scratch_b[j + 1 : lb + 1] = routes[b, j : lb]
            na, nb = la - 1, lb + 1
        elif kind == 1:  # exchange a[i] and b[j]
            i, j = np.random.randint(la), np.random.randint(lb)
            scratch_a[:la] = routes[a, :la]
            scratch_b[:lb] = routes[b, :lb]
            scratch_a[i], scratch_b[j] = routes[b, j], routes[a, i]
            na, nb = la, lb
        else:  # 2-opt*: exchange tails; both routes must stay non-empty
            i, j = np.random.randint(1, la + 1), np.random.randint(1, lb + 1)
            na, nb = i + lb - j, j + la - i
            if na > routes.shape[1] or nb > routes.shape[1]:
                continue
            scratch_a[:i] = routes[a, :i]
            scratch_a[i : na] = routes[b, j : lb]
            scratch_b[:j] = routes[b, :j]
            scratch_b[j : nb] = routes[a, i : la]
        if _route_ok_arr(scratch_a, na, dem, cap, ready, due, svc, dist) and _route_ok_arr(
            scratch_b, nb, dem, cap, ready, due, svc, dist
        ):
            if temp > 0.0:
                delta = (
                    _route_len(scratch_a, na, dist)
                    + _route_len(scratch_b, nb, dist)
                    - _route_len(routes[a], la, dist)
                    - _route_len(routes[b], lb, dist)
                )
                if delta > 0.0 and np.random.random() >= np.exp(-delta / temp):
                    continue
            routes[a, :na] = scratch_a[:na]
            routes[b, :nb] = scratch_b[:nb]
            lens[a], lens[b] = na, nb


@njit(cache=True)
def _ges_chunk(
    routes, lens, pool, pool_size, penalty, n_steps, k_max, n_perturb, temp, cheapest, seed,
    dem, cap, ready, due, svc, dist, node_budget,
):
    """Runs up to n_steps ejection-pool steps in place; returns the new pool size."""
    np.random.seed(seed)
    size = routes.shape[1] + 2
    dep, latest = np.zeros(size), np.zeros(size)
    scratch_a, scratch_b = np.zeros(size, dtype=np.int64), np.zeros(size, dtype=np.int64)
    for _ in range(n_steps):
        if pool_size == 0:
            break
        pool_size -= 1
        v = pool[pool_size]
        if _try_insert(v, routes, lens, cheapest, dem, cap, ready, due, svc, dist, dep, latest):
            continue
        penalty[v] += 1
        _, r, ins, mask = _best_ejection(
            v, routes, lens, penalty, k_max, dem, cap, ready, due, svc, dist, dep, latest, node_budget
        )
        if r < 0:
            pool[pool_size] = v
            pool_size += 1
            _perturb(routes, lens, n_perturb, temp, dem, cap, ready, due, svc, dist, scratch_a, scratch_b)
            continue
        m, new_m = lens[r], 0
        for i in range(m + 1):
            if i == ins:
                scratch_a[new_m] = v
                new_m += 1
            if i < m:
                if mask[i]:
                    pool[pool_size] = routes[r, i]
                    pool_size += 1
                else:
                    scratch_a[new_m] = routes[r, i]
                    new_m += 1
        routes[r, :new_m] = scratch_a[:new_m]
        lens[r] = new_m
        _perturb(routes, lens, n_perturb, temp, dem, cap, ready, due, svc, dist, scratch_a, scratch_b)
    return pool_size


def fleet_lower_bound(inst: Inst) -> int:
    return max(1, math.ceil(float(inst.demands.sum()) / float(inst.capacity) - 1e-9))


def ges_minimize(
    plan: Plan,
    deadline: float,
    seed: int,
    *,
    k_max: int = 5,
    n_perturb: int = 100,
    temp_frac: float = 0.02,
    cheapest: bool = True,
    restart_steps: int = 20000,
    node_budget: int = 200000,
    on_improve=None,
) -> Plan:
    """Removes routes until the deadline or the capacity bound; returns the fleet-best plan."""
    if not plan.feasible:
        return plan
    inst = plan.inst
    rng = np.random.default_rng(seed)
    best = plan
    floor = fleet_lower_bound(inst)
    kernels = (inst.demands, float(inst.capacity), inst.ready_times, inst.due_times, inst.service_times, inst.dist)
    n_nodes = inst.dist.shape[0]
    # temp_frac is relative to the mean edge length of the starting plan.
    temp = temp_frac * float(plan.cost) / (inst.n + plan.nv) if temp_frac > 0.0 else 0.0
    penalty = np.ones(n_nodes, dtype=np.int64)
    while best.nv > floor and time.perf_counter() < deadline:
        width = n_nodes + 1
        source = [r for r in best.routes if r]
        target = int(rng.integers(len(source)))
        routes = np.zeros((len(source) - 1, width), dtype=np.int64)
        lens = np.zeros(len(source) - 1, dtype=np.int64)
        kept = [r for i, r in enumerate(source) if i != target]
        for i, r in enumerate(kept):
            routes[i, : len(r)] = r
            lens[i] = len(r)
        pool = np.zeros(n_nodes + 1, dtype=np.int64)
        pool[: len(source[target])] = source[target]
        pool_size = len(source[target])
        steps = 0
        while pool_size and steps < restart_steps and time.perf_counter() < deadline:
            pool_size = int(
                _ges_chunk(
                    routes, lens, pool, pool_size, penalty, STEPS_PER_CHUNK, k_max, n_perturb, temp, cheapest,
                    int(rng.integers(2**31)), *kernels, node_budget,
                )
            )
            steps += STEPS_PER_CHUNK
        if pool_size:
            continue
        cand = Plan([[int(x) for x in routes[i, : lens[i]]] for i in range(len(lens)) if lens[i]], inst, plan.algo)
        if cand.feasible and cand.nv < best.nv and _covers_all_customers(cand.routes, inst):
            best = cand
            if on_improve is not None:
                on_improve(best)
    return best
