# OR-Tools Baseline Contract Audit

Status: adapter and three-scale operational pilot verified on 2026-10-18.
This is not a publication performance comparison or approval for the full sweep.
No historical result/model, training label, or manuscript was replaced.

## Findings and Repairs

The previous adapter rounded distances/service, truncated demand, used an
arbitrary fixed vehicle cost, dropped fractional seconds, and timed only the
backend search. The legacy `run_instance()` caller could give OR-Tools at least
30 seconds with a 5% discount relative to the other solver and did not forward
its per-run seed into the copied config.

The new `src/vrptw/ortools_baseline.py` owns the adapter. The existing
`solvers.run_ortools(inst, cfg)` tuple API is retained; its elapsed time now covers
model construction, search and validation, excluding dependency imports. Legacy
matched-time calls use the supplied budget exactly and forward the run seed.

`scripts/benchmark.py --ablation ortools` records the same input, source, routes,
component flags and timing schema as the native solvers, plus `adapter` diagnostics.
GNN checkpoints and capped iteration mode are rejected for this external baseline.
`--include-ortools` adds it to the existing pilot; defaults are unchanged.

## Fleet-First Objective

Let `n` be the customer count and `M` the largest integer arc cost. A complete
plan with at most `n` active routes has at most `2*n` travel arcs. Therefore its
travel objective is in `[0, D]`, where `D = 2*n*M`. Set each active vehicle's
fixed cost to `B = D + 1`.

For any `k`, `k*B + D < (k+1)*B`. Thus fewer vehicles always beats any possible
travel improvement in this encoded objective. Conversion and `n*B + D` are
checked against a safe integer range before calling the backend. This proves
objective ordering, not that a timed heuristic finds the minimum fleet.

## Precision and Feasibility

Scale is fixed at 100,000. Travel cost uses nearest-integer distances. Time
transit rounds travel and source-node service upward; ready times round upward
and due times downward. Capacity/demand must be exact nonnegative integers, never
silently truncated. The native depot convention requires ready/service/demand
zero, departure at zero and return no later than depot due time.

This time-grid model may exclude original-feasible routes. The plan travel-rounding
bound is `n/100000`: 0.001, 0.002 and 0.004 at the pilot sizes. Each window endpoint
changes by less than one grid unit. Transit inflation alone is bounded by
`(2*n+1)/100000` per route. Reported distances use the original matrix, not the
integer objective. Retained callback incumbents must pass original route
feasibility and exact customer coverage checks.

The [SINTEF convention](https://www.sintef.no/projectweb/top/vrptw/solomon-benchmark/)
uses fleet-first ordering and double-precision distance/travel time. This adapter
is not an exact double-precision solver. Precision acceptance and sensitivity
policy remain decisions for the full experiment protocol.

All 74 frozen evaluation inputs passed numeric preflight without model building,
solving, scoring routes or tuning settings. Evidence:
`results/ortools_contract_20261018/preflight.json` and `preflight.py`.

## Seed and Cutoff Semantics

Installed version: 9.15.6755. CP routing, local cheapest insertion and guided local
search are fixed; CP-SAT fallbacks are disabled. The run seed reaches
`routing.solver().ReSeed(seed)`, not just config or inactive SAT parameters.
A test intercepts the actual Python API call and verifies seed 47 reaches it
despite config seed 42.

The [official Solver API](https://or-tools.github.io/docs/python/classortools_1_1constraint__solver_1_1pywrapcp_1_1Solver.html)
defines `ReSeed` for the solver's random generator. This does not establish that
all routing components use it or different seeds yield distinct trajectories.
Requested seeds are not proven independent randomized routing replications.

The [version-pinned search schema](https://github.com/google/or-tools/blob/v9.15/ortools/constraint_solver/routing_parameters.proto)
uses a protobuf duration. The adapter passes remaining nanoseconds after
quantization/model-build/callback setup, instead of `int(seconds)`. Original-
feasibility validation inside callbacks consumes search time. Only complete
incumbents validated and captured before the adapter deadline can be selected.
The final backend assignment is not used because it could arrive after cutoff.

Return latency and incumbent capture time are separate facts. Backend calls may
still return late. No sleep, larger tolerance or hidden budget reserve forces a
pass. Dependency imports/constructor setup are outside `solve()` and included in
the separately recorded end-to-end task latency.

## Verification

- **165 tests passed in 93.53 seconds**; Ruff and `git diff --check` clean.
- Tests cover objective bounds, overflow, rounding, unsupported quantities,
  fractional cutoffs, real CP seed wiring, setup exhausting budget, late callbacks,
  original feasibility, CLI diagnostics/modes, and legacy budget/seed forwarding.
- The fractional-budget unit warms the route validator to isolate API forwarding
  from JIT startup. The actual pilot has no explicit warmup: fresh processes and
  isolated run state, with validation charged inside search.

## Recorded Pilot

Directory: `results/resubmission_pilot_20261018_ortools_contract_10s/`.
Four branches on three sizes: ALNS, no-GNN hybrid, frozen retrained-GNN hybrid
and OR-Tools; seed 42, one Torch thread, nominal ten-second solve budgets.
All 12 are feasible exact covers and pass the unchanged 9.95-10.5-second gate.
Runtimes span 10.000383-10.432464 seconds.

The independent `audit_pilot.py` verifies source/model/input hashes, coverage,
original and quantized feasibility, integer objective decomposition, original
distance recomputation, incumbent cutoff and timer allocation. No neural component
is executed by OR-Tools. Checks and artifact hashes are in `audit.json`.

| Instance | Native Fleet (ALNS / No GNN / GNN) | OR Fleet | OR Distance | Model Build | Engine Search | Return | Incumbent Capture |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C101 | 10 / 10 / 10 | 10 | 828.936867 | 0.017215 | 9.984432 | 10.002382 | 0.300373 |
| R1_2_1 | 20 / 20 / 20 | 22 | 4929.625350 | 0.015214 | 10.415777 | 10.432464 | 5.464727 |
| RC2_4_1 | 14 / 14 / 14 | 17 | 9049.176225 | 0.027277 | 10.020011 | 10.048077 | 9.966057 |

Timing columns are seconds. All selected incumbents were captured before ten
seconds; R1_2_1 nevertheless returned 0.432464 seconds late. A diagnostic pass is
not a strict return-deadline guarantee.

No distance-gap comparison is made for R1_2_1 or RC2_4_1 because fleets differ.
This fixed preset used more vehicles in those two observations and is not
established as the strongest classical comparator. No superiority claim,
statistical inference or retuning follows from this pilot. All raw native and
external outcomes, including worse GNN outcomes, are retained.

## Reproducibility and Gates

Recorded command, already completed; a repeat needs a new output directory:

```sh
env PYTHONPATH=src .venv/bin/python scripts/run_benchmark_pilot.py \
  --output-dir results/resubmission_pilot_20261018_ortools_contract_10s \
  --time-limit 10 --seed 42 \
  --gnn-model results/gnn_retraining_20261017/model_seed42/best.pt \
  --include-ortools
```

Source SHA-256: `6382d8eccc010d8e542efad5be539d6a5c26acf18c74913fbb4f22b8cb64ae8c`.
Checkpoint SHA-256: `365de53beba09097d1176a8b102ced8d6d97311f5a3ac82186b116d3290e1b97`.
Commands, stdout/stderr, route JSON, CSV and source/model snapshots are preserved.
Training source/manifest and historical weights remain unchanged.

Still required: accept/disclose precision/cutoff/seed semantics, broaden timing
and seed coverage, reproduce a stronger classical comparator and an independent
learning-augmented baseline, validate ablations and approve the publication
compute budget. Legacy batch aggregation/run-count conventions are not validated
by this wrapper repair. No full sweep or manuscript edits were performed.
