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

Version 2 has not started at this protocol stage. Its results are pending.
