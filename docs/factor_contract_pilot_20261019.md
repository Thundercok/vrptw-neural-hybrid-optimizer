# Factor binding and cold-cache contract pilot (2026-10-19)

## Protocol fixed before execution

Engineering validation only. Preserve all historical results, models, source
snapshots, both goldens and the frozen publication design. No manuscript edit,
training, parameter selection, statistical performance claim or full sweep.

Run 24 independent jobs: c101 (100), R1_2_1 (200), RC2_4_1 (400), seed 42,
10 seconds each; eight factor cases per input. Bits are GEC, SP, macro DDQN,
micro DDQN, LAC, GNN. Cases are F111111, F000000, F110000, F001111, F011111,
F101111, F110111 and F111011. This covers all four routing-controller choices,
the heuristic/learning anchors and individual GEC/SP removals. It does not
estimate six independent effects or replace the 16-cell proposed study.

Order seed 20261019 shuffles the three input blocks and the initial case order;
successive blocks rotate that order by one. Each case has three distinct
positions; each position has three jobs overall. This is not complete position
balance for each case. Write exact jobs/configs and source/input/model snapshots
to an exclusive new directory before starting any child.

Every job gets a fresh process, initially empty working directory and initially
empty, exclusive NUMBA_CACHE_DIR. Record the child entry state before project
imports, effective Numba settings, initial controller/archive state, nested
module configs, counters and cache inventory. Request JIT enabled, hash seed 42
and one Torch/Numba/BLAS thread; actual HiGHS thread counts are not established.
No explicit compilation warmup, sleep padding or shared results/controller state.
Imports, input setup, constructor and model loading are outside solver.solve;
compilation after solve entry is charged. Record constructor/model setup and
whole-child wall/CPU separately. Cold caches can cause a failed 10-second job.

Keep independent gates for route/certificate, clocks, provenance, factor binding,
cache/cold state and return timing. Independently replay final routes in original
coordinates. Capture must be strictly before cutoff. Return gate is fixed at
[T-0.05, T+0.5] seconds, separately from certification. No hard deadline claim.
Intermediate trajectory hashes cannot be replayed without intermediate routes.

Each declared job runs once. Preserve all algorithm, availability and return
failures and continue the frozen schedule. Source/input/model/config/cache
integrity drift aborts subsequent jobs, retaining partial evidence. Missing or
unreadable child evidence is an integrity failure; timeout is retained and stops
the schedule. No extension, rerun, exclusion or tuning using observed scores.

TDD precedes CLI metadata and runner changes. Unit tests must force bad cache,
source, config, model and disabled-component activity; validate fresh-directory
execution and fail-closed integrity handling. Existing solver code is unchanged.

## Preflight verification before execution

The protocol above preceded implementation and jobs. Evidence is additional in
`results/factor_contract_validation_20261019/`. Initial Red: two failures and
29 missing-runner errors. A separate failure-metadata test failed before its CLI
repair. Initial Green: 32 passes, then 41 with all eight bindings and artifact
tampering checks. Two plan/protocol drift tests failed before adding checks
before and after every child. Final targeted group: 194 passes, including 43 new
pilot tests. The full suite passes 533 tests in 88.38 seconds, with the existing
PyVRP warning from the intentionally infeasible fixture. Ruff, touched-file
formatting and whitespace checks pass. No native solver logic was changed.

The execution directory uses the client date 2026-10-20:
`results/factor_contract_pilot_20261020/`. The earlier date in this protocol and
validation directory denotes preparation; those files are retained. The runner
will freeze this pre-execution document alongside its plan before any job.

```sh
.venv/bin/python scripts/run_factor_contract_pilot.py \
  --output-dir results/factor_contract_pilot_20261020 \
  --gnn-model results/gnn_retraining_20261017/model_seed42/best.pt \
  --order-seed 20261019
```

## Execution results

The first frozen stage, `results/factor_contract_pilot_20261020/`, stopped after
the first job on its config integrity gate. Its 41 files, including the failed
audit, are sealed by `aborted_pilot_hashes.json` in the validation directory.
The 400-customer F001111 route, clocks, cold/cache state, provenance and timing
pass; config binding does not. The remaining 23 jobs did not run and are not
passing cells. The audit status remains failed.

Diagnosis: `Config.default_data_path()` returns `./data/Solomon` when preparation
runs at the repo root, but returns the absolute repo data directory in the new
empty child cwd. This differs in the requested/effective and all four nested
module configs. Explicit `--instance` still loads the frozen intended input.
The gate correctly stopped rather than ignoring the field.

Four new tests failed before the repair, covering ALNS, legacy Full and both
GNN-on/off factor cases across repo and foreign cwd. The CLI now explicitly sets
its ancillary data path to the absolute repo Solomon directory, including when
the foreign cwd has a shadow data/Solomon directory. The core Config API and all
solver algorithms remain unchanged; the strict config comparison is retained.
The final targeted group has 198 passes (47 new pilot tests); Ruff passes.

### Version 2 protocol, declared before its first job

Run the same 24-job schedule, input/model hashes, seed, budgets, order and gates
in the new `results/factor_contract_pilot_20261020_v2/` directory after tests pass.
The only runtime change from the aborted source is the explicit CLI data path.
This is a separate rerun following a harness integrity repair, with an additional
240 nominal solve seconds; no score-based change, model selection, tolerance
change or pooling with the aborted stage. Preserve both stages. Source and
configs will be frozen anew, rather than rewriting the earlier plan.

```sh
.venv/bin/python scripts/run_factor_contract_pilot.py \
  --output-dir results/factor_contract_pilot_20261020_v2 \
  --gnn-model results/gnn_retraining_20261017/model_seed42/best.pt \
  --order-seed 20261019
```

Version 2 preflight: **537 tests pass in 97.03 seconds**, with the same existing
PyVRP fixture warning. The 198-test targeted group and Ruff/format/whitespace
checks pass. Before the first v2 child, the recorded Python orchestration
`results/factor_contract_validation_20261019/execute_v2.py` will assert that
jobs, inputs, model, training metadata, budget gates and environment are identical
to the aborted plan, and all 144 requested/effective/nested config differences
are solely the equivalent absolute representation of data_path. The only runtime
source difference must be scripts/benchmark.py. Record this check in
prelaunch_invariance.json before starting jobs. Then call the same prepare,
execute and independent audit APIs used by the CLI command above.

The frozen pre-execution copy retains this stage before jobs started. Results
from the completed v2 schedule follow below.

## Version 2 completed results (2026-10-20)

All 24 declared jobs completed once after the separate integrity repair, with
zero process errors/timeouts. The independently reopened artifact audit is
**failed**, with `complete=true`: all route/certification, clock, provenance,
binding and cold/cache gates pass, while only **15/24** return-timing gates pass.
All nine late returns remain in the CSV, raw results and failed audit.

| Input | Jobs | Certification / clock / integrity passes | Return-timing passes | Solve return range (s) |
|---|---:|---:|---:|---:|
| RC2_4_1 | 8 | 8 | 6 | 10.000626–11.653878 |
| R1_2_1 | 8 | 8 | 5 | 10.174127–10.785565 |
| c101 | 8 | 8 | 4 | 10.305139–11.713680 |

The latest selected incumbent capture is **9.615684s**,
strictly before the ten-second cutoff. Every final route is independently checked
for exact cover, capacity, customer/depot windows and full-precision distance in
original coordinates. Intermediate trajectory hashes are checked for monotonic
time and fleet-first improvement, but intermediate route lists are unavailable.

| Failed timing cell | Solve return (s) | Selected capture (s) |
|---|---:|---:|
| RC2_4_1__F111011__seed42__10s | 11.419354 | 8.981244 |
| RC2_4_1__F011111__seed42__10s | 11.653878 | 9.445659 |
| R1_2_1__F101111__seed42__10s | 10.688135 | 7.928812 |
| R1_2_1__F111111__seed42__10s | 10.785565 | 5.464421 |
| R1_2_1__F000000__seed42__10s | 10.527542 | 7.299332 |
| c101__F110111__seed42__10s | 11.011352 | 2.443892 |
| c101__F111111__seed42__10s | 10.803204 | 4.432152 |
| c101__F000000__seed42__10s | 10.610939 | 6.694894 |
| c101__F111011__seed42__10s | 11.713680 | 6.765277 |

Whole-child wall durations span 15.152647–20.137196s and total
402.151773s, versus 240 nominal solve seconds. These include
Python startup, imports/input setup, constructor and model loading. The CLI
records constructor/model times and child-entry-to-solve separately. Returned
solve times exclude that setup; no equal end-to-end compute claim follows.
CPU/load records are diagnostic context, not attribution or exclusion criteria.

### What the dispatch observations cover

The derived `activity_v2.csv` records each raw-result path/hash and source hash.
Seven jobs make eligible macro-DDQN selections and five make rule-macro
selections. All 24 dispatch the declared micro policy (15 DDQN / 9 rule).
Every SP-on job calls the backend (15/15); SP-off calls remain zero. These
are dispatch/call counts, not neural forward counts or optimizer-update counts.
The earlier forced unit tests establish disabled-module behavior and actual
weight changes where appropriate.

**LAC is enabled in 18 jobs but has zero acceptance queries in all 24.** This
short operational pilot therefore does not exercise LAC acceptance or its
80-decision delayed training path. Config acceptance must not be presented as
operational evidence for an LAC effect. GEC secondary-path disabling is covered
by the earlier forced tests; this pilot does not supply per-routine GEC counters.

### Evidence, preservation and remaining gates

Source SHA-256:
`86bf7c352c4b506057cf9501629735d2a49c2acb1670a3bcee0736f8e1bb30b1`.
The frozen checkpoint is unchanged:
`365de53beba09097d1176a8b102ced8d6d97311f5a3ac82186b116d3290e1b97`.

The final audit hashes 765 evidence files, including per-job
cache files, commands/environment, initial cwd/cache state, raw routes, nested
configs, source/tests, model/training/input snapshots and the pre-execution
protocol. All those hashes are independently rechecked after execution. The
aborted stage retains its failed audit and all 41 original files unchanged.

The report uses `summary.csv` for timing/gate counts and the derived activity
CSV for dispatch coverage. Analysis and preservation records are additional in
`results/factor_contract_validation_20261019/`. Of 2,581 files protected before
this work, 2,580 are byte-identical; the sole intended existing-file edit is
`scripts/benchmark.py`. Native algorithms, manuscript, models, older results,
both goldens and the frozen 16-cell publication design remain unchanged. New
runner, tests and this report are additional.

The pre-cutoff incumbent contract passes these three-input/one-seed/eight-case
checks under the new empty-Numba-cache policy. The overall timing contract
fails; no hard return guarantee, broad seed/geometry coverage, six-factor causal
attribution, stable GNN benefit, LAC operational effect or solver ranking is
established. The first priority is a separately frozen diagnosis of the nine
late returns without widening the gate; longer-horizon controller/LAC coverage
and compute/protocol acceptance remain open. The publication sweep stays
unlaunched. No retraining or manuscript edit ran.
