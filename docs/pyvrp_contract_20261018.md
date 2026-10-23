# PyVRP Baseline Contract

The adapter, three-scale operational pilot and independent artifact audit were
verified on 2026-10-18. This is not
approval for the publication sweep, a performance claim, or a replication of
historical PyVRP paper results. No manuscript, training label or checkpoint was
changed.

## Version and Algorithm

Optional extra: `baselines = ["pyvrp==0.14.1"]`; the lockfile adds only PyVRP,
tqdm and vrplib, without upgrading existing packages. Install with:

```sh
uv sync --locked --extra dev --extra baselines
```

The tested environment uses Python 3.12.6 on macOS ARM64 and the PyPI wheel.
The adapter refuses a different PyVRP version until its API and numerical/timing
contract are re-audited. This pin is independent of the historical GNN training
source snapshot and does not alter the training provenance.

PyVRP 0.14.1 uses **iterated local search (ILS)**, not the HGS implementation
associated with older releases. Its
[version-pinned solve implementation](https://github.com/PyVRP/PyVRP/blob/v0.14.1/pyvrp/solve.py)
constructs a seeded random solution and applies local search before the ILS loop.
The [ILS implementation](https://github.com/PyVRP/PyVRP/blob/v0.14.1/pyvrp/IteratedLocalSearch.py)
uses late acceptance and offers callbacks for the initial and improved solutions.
Do not label this comparator HGS or imply that it reproduces a particular
published configuration or literature number.

Search parameters remain release defaults, except observer callbacks and disabling
statistics/progress display. The recorded metadata includes all parameter values,
available/supported operators and the actual seed passed to `pyvrp.solve()`.
`initial_solution=None`: there is no route, pool, controller or GNN warm start
from another solver. Each pilot child is a fresh process with one-thread settings.
Seed 42 is one run, not evidence of independent multi-seed statistics.

## Objective and Conversion

`src/vrptw/integer_baseline.py` now owns the existing OR-Tools quantization
contract; the OR-Tools module retains its old helper/type names as aliases.
No OR-Tools dependency is required to construct the PyVRP model. Both adapters
use the same fixed 100,000-unit grid, nearest-integer distance cost,
upward-rounded travel/service/ready and downward-rounded due times.

For `n` mandatory customers, let `D = 2*n*max_integer_arc` and `B = D+1`.
There are at most `n` active routes and `2*n` travel arcs. Thus
`k*B + D < (k+1)*B`: the scalar objective orders feasible solutions fleet first.
PyVRP gets `n` identical vehicles, fixed cost `B`, unit distance cost one, no
duration cost, no optional clients, reloads or shipments. This bound proves
objective ordering, not that the heuristic finds a minimum fleet.

Demands/capacity must be exact nonnegative integers. Depot demand, ready and
service must be zero. Vehicle start-late is zero, and depot/vehicle closing times
enforce the native return horizon. Source service is a client attribute, not
double-counted in travel durations. PyVRP 0.14 client activities are zero-based;
the adapter explicitly maps them back to native customer IDs 1 through `n`.
Preflight checks the scalar objective and a conservative worst-case penalty
bound against safe integer range.

This is an inner time-grid approximation that may exclude original-feasible
routes, not the exact double-precision
[SINTEF convention](https://www.sintef.no/projectweb/top/vrptw/solomon-benchmark/).
Total distance rounding error is at most `n/100000`; each time-window endpoint
changes by less than one grid unit. Transit inflation alone is bounded by
`(2*n+1)/100000` per route. Every retained incumbent is also validated against
the original matrix, capacity, windows, depot return and exact customer coverage;
reported distance uses the original matrix.

Release-default penalties are not guaranteed to be scale-invariant or the best
settings for a large fixed fleet cost. No settings were changed in response to
evaluation pilot outcomes. A representative classical comparison still needs an
accepted precision/parameter protocol and broader seed/cutoff validation.

## Timing and Selection

An absolute `perf_counter()` deadline begins at adapter `solve()` entry.
Quantization, model building, neighbour computation, initial solution creation,
search and original-space callback validation all consume that budget.
Dependency imports/version checks are outside `solve()` and included in the
CLI's separate `total_runtime_sec`.

The stock
[MaxRuntime implementation](https://github.com/PyVRP/PyVRP/blob/v0.14.1/pyvrp/stop/MaxRuntime.py)
starts its clock on its first call, after initial solution construction.
The adapter instead passes a stopping criterion against the original absolute
deadline, so construction time cannot silently restart the budget. Expiry while
building the model prevents calling the backend.

Initial/best callbacks retain only original-feasible exact covers fully copied,
validated and costed before that deadline. The backend's final `result.best` is
never substituted, because it may include a late improvement. Incumbent capture,
model construction, initialisation, backend call, ILS runtime and outer return
latency are recorded separately. ILS iterations are not comparable to native
ALNS iterations or CP branches.

Stopping is checked between ILS iterations; C++ local-search/initialisation calls
cannot be preempted. Late return remains possible, even with a valid pre-cutoff
incumbent. The unchanged pilot timing gate is 9.95-10.5 seconds for a ten-second
request, not a strict real-time guarantee. No sleep padding or enlarged tolerance
is used. CLI rejects a GNN checkpoint or capped iteration mode for PyVRP.

## Verification

- Red phase: the new tests failed collection before the adapter existed.
- Final full suite: **185 passed in 86.42 seconds**, including the OR-Tools regression
  tests and all GNN/OR-Tools/PyVRP pilot-flag combinations. One penalty-bound
  warning comes from an intentionally infeasible service/depot toy fixture.
- Tests cover encoded constraints/mapping, fleet bound, seed forwarding,
  fractional time, construction expiry, late initialisation/final results,
  expiry during route copying/validation, invalid quantities/overflow, CLI
  metadata on success/failure, and incompatible modes.
- Ruff, `git diff --check` and `uv pip check` pass. The fractional-budget API unit explicitly warms the native route
  validator; the recorded cold-start pilot does not explicitly warm it.
- All **74/74** frozen test inputs pass model-building preflight with **zero
  instances solved**. Manifest/input/geometry hashes are checked first.
  Evidence: `results/pyvrp_contract_20261018/preflight.py` and `preflight.json`.

## Recorded Evidence

The early single C101 smoke is preserved at
`results/pyvrp_contract_20261018/initial_c101.json`; its earlier source identity
differs from the final, formatted pilot snapshot. It was not used to select
weights, parameters or a preferred result.

The five-solver pilot directory is
`results/resubmission_pilot_20261018_pyvrp_contract_10s/`.
The completed outcomes, audit status and hashes belong to this exact snapshot,
not the earlier OR-Tools-only pilot or GNN training snapshot.

All **15/15** runs are original-feasible exact covers and pass the unchanged
timing gate. Return times span 10.000316-10.399829 seconds, with 150.549183 seconds
of aggregate measured solve time. OR-Tools R1_2_1 returned 0.399829 seconds late,
although its chosen incumbent was captured at 5.481084 seconds. Its diagnostic
pass is not a strict ten-second return guarantee.

| Instance | Branch | Fleet | Original Distance | Return Seconds |
| --- | --- | --- | --- | --- |
| C101 | All five branches | 10 | 828.936867 | 10.000316-10.009038 |
| R1_2_1 | ALNS | 20 | 5383.628579 | 10.002973 |
| R1_2_1 | Hybrid without GNN | 20 | 4958.627540 | 10.000988 |
| R1_2_1 | Hybrid with GNN | 20 | 5721.662843 | 10.041455 |
| R1_2_1 | OR-Tools | 22 | 4929.625350 | 10.399829 |
| R1_2_1 | PyVRP | 21 | 4782.298324 | 10.004476 |
| RC2_4_1 | ALNS | 14 | 6846.359703 | 10.003132 |
| RC2_4_1 | Hybrid without GNN | 14 | 7472.436107 | 10.029870 |
| RC2_4_1 | Hybrid with GNN | 14 | 7247.371560 | 10.002335 |
| RC2_4_1 | OR-Tools | 17 | 9044.565363 | 10.036094 |
| RC2_4_1 | PyVRP | 14 | 6374.716737 | 10.009725 |

| PyVRP Instance | Model Build | Initialisation Complete | Incumbent Capture | ILS Iterations |
| --- | --- | --- | --- | --- |
| C101 | 0.001948 | 0.009765 | 0.203751 | 27241 |
| R1_2_1 | 0.002784 | 0.020026 | 9.099504 | 13916 |
| RC2_4_1 | 0.006488 | 0.052247 | 7.140469 | 14284 |

Timing columns are seconds since the relevant adapter solve entry, except
model-build duration. All chosen external incumbents were captured before ten
seconds. PyVRP's original-validation callback failure count is zero at all sizes.

The independent `audit_pilot.py` / `audit.json` verifies all 15 source/input/model
identities, CPU/thread settings, route coverage, original feasibility and distance,
and both external integer objectives/time-grid constraints. It checks deadline
captures, OR-Tools engine allocation, PyVRP's pinned parameters and absence of
neural components in both external branches. Integrity and operational gates pass.

On R1_2_1 the external fleets differ from the native fleet, so no distance-gap
comparison is valid. On RC2_4_1 PyVRP's matched-fleet distance is lower than all
three native branches in this observation. The full GNN branch is worse than the
no-GNN branch on R1_2_1, and worse than ALNS on both nontrivial pilot cases.
Do not claim hybrid superiority or stable GNN benefit from this pilot. These are
one-seed operational observations, not unbiased performance estimates or a
parameter-selection dataset. No retuning follows from them.

Source SHA-256: `f43792c9de151bea31abc7c61ecbdf7640691d0efdaad79911eef629206a5261`.
Checkpoint SHA-256: `365de53beba09097d1176a8b102ced8d6d97311f5a3ac82186b116d3290e1b97`.
Preflight SHA-256: `88a7cfb6af66dc204c61ca28edbd522940e6ebe900a29f3dd4c10204c357d4a5`.
Raw JSON/CSV, commands, logs and source/model snapshots are preserved. A
post-pilot test-only skip guard allows environments without the optional PyVRP
extra to collect the default suite; it changes no solver source or pilot result.

Recorded command:

```sh
env PYTHONPATH=src .venv/bin/python scripts/run_benchmark_pilot.py \
  --output-dir results/resubmission_pilot_20261018_pyvrp_contract_10s \
  --time-limit 10 --seed 42 \
  --gnn-model results/gnn_retraining_20261017/model_seed42/best.pt \
  --include-ortools --include-pyvrp
```

Repeats require a new output directory. `--include-pyvrp` alone adds three runs
to the existing six-run default; with GNN and OR-Tools the total is 15.

## Remaining Gates

Accept/disclose integer precision and cutoff semantics; validate representative
classical settings and multiple seeds/cutoffs without tuning on evaluation
outcomes; reproduce an independent learning-augmented baseline; validate matched-
time ablations and approve the full compute budget. No publication sweep or
manuscript edits were performed.
