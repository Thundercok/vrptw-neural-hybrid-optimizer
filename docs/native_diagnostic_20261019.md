# Native 400-Customer Diagnostic

## Question and Scope

Why did the full GNN hybrid vary sharply across earlier ten-second operational
pilots? This diagnostic is not a publication comparison, a checkpoint/parameter
selection exercise, or a statistical claim about instance-level generalisation.
It preserves all previous outcomes and does not edit the manuscript.

Earlier six-solver RC2_4_1 outputs show initial trajectory points at 2.473s for
ALNS, 4.352s for no-GNN hybrid and 4.435s for full GNN hybrid. These are cumulative
initialisation timestamps, **not** isolated GNN inference times. All three
effective configs have split disabled; blaming recursive split passes for these
particular observations would be incorrect. No causal attribution follows from
these timestamps alone.

The code also shows that GNN changes greedy construction, destroy/repair guidance
and pruning, not just runtime. A paired full/no-GNN difference therefore cannot
be read as the isolated cost or benefit of neural forward inference. The frozen
GNN was trained/selected on synthetic 100/200-customer splits; RC2_4_1 at 400 is
an out-of-size diagnostic, not a previously verified training-domain estimate.

## Declared Protocol

The schedule is fixed before observing these new outcomes:

- One input: frozen `RC2_4_1.TXT`, 400 customers. No new geometry is introduced.
- Branches: ALNS, full hybrid without GNN, full hybrid with the existing frozen
  retrained GNN. No external comparator is retuned or rerun in this diagnostic.
- Unprofiled matrix: seeds 42/43, independent 10/60-second solves, all three
  branches in each seed/budget block: **12 jobs, 420 seconds of nominal search**.
- Block order is randomized with order seed 20261019. Branch positions follow a
  randomly selected cyclic Latin order; each branch occupies every position and
  position counts differ by at most one across four blocks.
- Three additional, separately marked ten-second profiles at seed 42 run last,
  one per branch. They are **instrumented**, have overhead, and are never pooled
  with the unprofiled observations. Total declared search budget: **450 seconds**.
- Every job runs once in a fresh process and isolated run directory. No results,
  routes, archives or controller weights transfer between jobs. No explicit JIT
  warmup, padding, adaptive rerun, parameter change or score-based exclusion.
- Model/source/input snapshots and exact commands are recorded in `plan.json`
  before any child starts. Identity drift aborts subsequent jobs and preserves
  the partial evidence; it does not quietly start a new experiment identity.

Only the CLI harness is instrumented. No solver, operator, model architecture,
training procedure or search allocation is changed. Default runs are unprofiled;
`--profile PATH` wraps only `solver.solve()`, excludes constructor/model loading,
retains stats even on solve exceptions and refuses existing/colliding profile
paths. Profile serialisation is outside the solve interval and inside total
task latency.

## Resource and Interpretation Rules

Torch/Numba/BLAS environment settings request one thread, as in the earlier
pilots. This alone does **not** establish a one-thread count for every backend;
in particular the current SciPy MILP options do not explicitly fix HiGHS threads.
This diagnostic records child user+system CPU and wall duration for the complete
child including setup/reaped descendants, not just the solve. Their ratio is
context, not proof that waiting, system load or a particular backend caused a
quality change. Values above one may reflect multithreading; values below one
do not by themselves identify a cause.

Host 1/5/15-minute load averages are also captured. They are not CPU percentages
and are not used for post-hoc exclusion. No isolated-machine, thermal or external
process control is claimed. A future primary experiment needs an accepted compute
policy and broader independent instance/geometry coverage.

Report only matched-fleet TD differences. Fleet changes take precedence; do not
compare distances across different fleet counts. Seeds within one geometry are
not independent test instances. With two seeds and one instance there is no
instance-level significance test or universal solver ranking.

The return gate stays `T-0.05 <= runtime <= T+max(0.5, 0.05*T)`, as before. It is
an operational tolerance, not a hard return deadline. Do not widen it to pass.
Cumulative profile times for nested functions overlap and must not be added
as if independent phases. Profiles are diagnostic samples, not uninstrumented
speed measurements or proof that a hotspot caused a particular quality outcome.

## Reproduction

Run from `VRPTW-Research-Optimization`, using a new output directory:

```sh
env PYTHONPATH=src .venv/bin/python scripts/run_native_diagnostic.py \
  --output-dir results/native_diagnostic_20261019 \
  --gnn-model results/gnn_retraining_20261017/model_seed42/best.pt \
  --order-seed 20261019
```

The final evidence includes plan/status JSON, raw outputs and routes, source/model
snapshots, commands, stderr/stdout, summary CSV, three profiles and independent
route/provenance/profile analysis. Completion and results are recorded below;
no prior pilot or training source hash is rewritten to match this new harness.

## Frozen Diagnostic Results

`results/native_diagnostic_20261019/` completed all 15 declared jobs exactly once.
Its independent audit passed source/model/input, exact-cover, original route
feasibility, distance, schedule and metadata checks **before subsequent source or
test changes**. The operational gate failed: 13/15 timing passes, including 10/12
unprofiled passes. The two no-GNN ten-second overruns remain failures.

Runtime source SHA-256:
`ea1b07d5bf53680aecf4631159139b7af802283004e8a8130d5c53f249833bd8`.
Checkpoint SHA-256 remains the training-selected
`365de53beba09097d1176a8b102ced8d6d97311f5a3ac82186b116d3290e1b97`.
Input SHA-256:
`d4afb6096d8a0f2069f0f3c863aba4cda99640498edfe5d4271b98f2a41ddfc6`.
The pre-fix suite had 225 passing tests. Raw artifacts, immutable audit hashes
and all profile outputs are retained, not replaced by later retests.

Unprofiled observations only; TD is shown as an individual objective, not a gap
across unequal fleets. Failed timing cells are not equal-budget comparisons.

| Seed | Budget | Branch | NV | TD | Return Seconds | Gate |
|---|---|---|---|---|---|---|
| 42 | 10 | ALNS | 14 | 6962.030 | 10.070521 | pass |
| 42 | 10 | no-GNN | 15 | 7357.954 | 13.630654 | fail |
| 42 | 10 | full | 14 | 7350.175 | 10.002916 | pass |
| 43 | 10 | ALNS | 13 | 7232.399 | 10.008433 | pass |
| 43 | 10 | no-GNN | 14 | 7018.092 | 11.014515 | fail |
| 43 | 10 | full | 13 | 7477.041 | 10.002430 | pass |
| 42 | 60 | ALNS | 13 | 6900.177 | 60.004293 | pass |
| 42 | 60 | no-GNN | 13 | 6665.132 | 60.006677 | pass |
| 42 | 60 | full | 13 | 6806.451 | 60.007904 | pass |
| 43 | 60 | ALNS | 13 | 6825.256 | 60.003252 | pass |
| 43 | 60 | no-GNN | 13 | 6676.116 | 60.010436 | pass |
| 43 | 60 | full | 13 | 6752.435 | 60.005530 | pass |

At 60 seconds all fleets match: full has lower TD than ALNS by 93.726/72.820,
but higher TD than no-GNN by 141.318/76.319 at seeds 42/43. At ten seconds full
matches ALNS fleet but has higher TD at both seeds. These are descriptive
observations on one geometry, not significance or generalisation evidence.
They do not establish a stable GNN benefit. Search iteration counts differ and
are not matched computational effort or independently comparable move counts.

The unprofiled initialisation timestamps span 2.321--4.549s for ALNS,
2.288--5.058s for no-GNN and 2.678--4.838s for full. Complete-child CPU/wall
ratios span about 0.777--0.964. Neither spread identifies a causal explanation;
host load, process startup and backend threading were not isolated controls.

## Profile Caveat

The three instrumented jobs are retained separately in `analysis.json` and raw
`.pstats`. Their reported entries suggest costly greedy construction (about
4.3--4.7s under instrumentation) and neural-Shaw work (six calls, 2.478s
cumulative in full), versus one GNN forward entry of 0.016154s and feature
construction of 0.005037s. These are provisional hotspot observations only.

**Attribution anomaly:** both hybrid profiles lack a `solve` root entry and
report about eight cumulative seconds on SciPy `check_option` with an empty
caller map; the ALNS profile retains its `solve` root. The cause has not been
isolated. Hash verification does not certify a correct profiler call tree.
Do not treat these profiles as an exact phase decomposition, a measurement of
unprofiled speed, or proof that GNN/HiGHS/system load caused a score change.
The existing raw profiles and analysis are preserved with this caveat rather
than silently relabelled. No new algorithm settings were selected from them.

## Deadline Acceptance Repair

Static inspection found a separate bug: a non-`None` MILP candidate could be
accepted after the shared deadline. The remaining-time option was forwarded,
but a cooperative backend limit is not a guarantee about when the call returns.
The same missing post-call checks affected greedy fallback, local search and
final candidate validation. Cached plans also needed a post-validation guard.

New fake-clock regression cases produced **20 failures and nine positive-control
passes before repair**. Post-call/post-validation checks now reject late results,
avoid caching late MILP solutions and return the previous incumbent. No search
parameters, model weights, kernels or tolerance were changed. The relevant
81-test suite and then all 254 tests passed; Ruff passed.

This does **not** prove that the exact old overruns were caused by late candidate
acceptance, nor does it preempt a running backend. Seed 42's failed run reports
one HiGHS timeout and the same final objective as its 5.380s improvement; seed
43 reports three HiGHS calls/two timeouts, and its return objective differs from
the last logged improvement. Those logs are not native pre-cutoff route
certificates. Neither failed run is retroactively reclassified.

## Guard-Only Retest and Clock Defect

`results/native_recombination_guard_20261019/` contains six separately declared
fresh unprofiled ten-second runs on the same geometry: three branches, seeds
42/43, original order restricted to these cells. The launcher is included in
the source archive. Source SHA-256:
`47b9a4c3a0e541b1d4fb37619aa823f52a3a903d5e442b6b4b71f8408c5fa46b`.

All six routes pass independent feasibility/objective/provenance checks, but
only five timing gates pass. No-GNN seed 43 returns after **2.731449s** with zero
search iterations and NV43, while its initial internal trajectory timestamp is
**31.207s** and `time_limit_hit=true`. The clock-consistency audit explicitly
fails; this is not a successful six-run validation or an eligible score cell.
The other return times are 10.002770--10.028364s. All raw scores remain in the CSV
and audit; none are substituted into the original diagnostic.

The native deadline producers/consumers used adjustable `time.time()`, whereas
the CLI measured elapsed time with `perf_counter()`. The observed discrepancy
does not distinguish clock adjustment, suspend or another host-clock effect.
It does expose incompatible timing contracts. Thirteen new regressions fail
before migration, covering forward/backward/frozen calendar clocks, both native
solvers, all repair operators, route pool and local search.

All native deadline creation, shared sub-solve deadlines, remaining budgets,
trajectory timestamps and local-search elapsed accounting now use the same
monotonic `time.perf_counter()` domain as the CLI. Numeric absolute `deadline`
arguments to these native helpers must therefore be `perf_counter()` values,
not Unix timestamps. Epoch timestamps used for run IDs are unchanged. Legacy
reporting scripts outside this native solve path have not been comprehensively
audited. The related 94-test suite passes after migration.

Both failed stages remain frozen. The separate post-clock-fix retest below is
not pooled with their cells. Hard interruption, complete native pre-cutoff route
certification, broader instance/seed/cutoff coverage and publication launch
approval remain open.

## Post-Clock-Fix Verification

`results/native_monotonic_20261019/` contains the six jobs declared before launch
by `results/monotonic_retest_20261019.py`, whose source is also archived. Each
branch/seed runs once in a fresh process at ten seconds, unprofiled, in the same
restricted order as the guard-only retest. Nominal search budget is 60 seconds.
No settings or outcomes are selected from the preceding failure. Source SHA-256:
`bf22c622561a9ce91606e0c16a627e9b6e7a0348df8a9f0c3d52aa06e301a88c`.
Input and model hashes remain unchanged.

| Seed | Branch | NV | TD | Return Seconds | Gate |
|---|---|---|---|---|---|
| 42 | no-GNN | 14 | 7472.436 | 10.056941 | pass |
| 42 | full | 14 | 7370.797 | 10.005793 | pass |
| 42 | ALNS | 14 | 6846.360 | 10.002646 | pass |
| 43 | ALNS | 13 | 7232.399 | 10.003178 | pass |
| 43 | no-GNN | 14 | 6879.232 | 10.003279 | pass |
| 43 | full | 13 | 7177.586 | 10.003263 | pass |

`results/audit_monotonic_20261019.py` independently verifies every route, original
distance, exact cover, input/model/runtime/test/launcher snapshot, seed, process
isolation, summary row and trajectory clock order. It also checks that requested
and effective configs exactly match the preceding retest except temporary
output/model path strings. **All six timing gates and clock-consistency checks
pass.** The immutable `audit.json` hashes all raw artifacts and links the prior
failed audit; neither earlier failure is rewritten.

Final verification: **267 tests pass in 88.89s**, with one expected PyVRP
infeasibility-test penalty warning. Ruff checks the entire repo successfully;
all nine touched diagnostic/runtime/test files pass format checks, and
`git diff --check` passes. The clock regressions show forward/backward calendar
jumps cannot alter these native elapsed deadlines. They do not identify the
precise host event responsible for the recorded clock discrepancy.

This is an operational repair validation on one geometry/two seeds/one cutoff,
not a matched before/after quality experiment or a proof of universal GNN gain.
The longest return still exceeds exactly ten seconds by 0.056941s: the unchanged
tolerance is not a hard deadline. HiGHS remains cooperative and final native
routes do not yet carry complete pre-cutoff incumbent certificates. No manuscript,
historical result or training checkpoint was replaced; no publication sweep ran.
