# Return timing diagnosis and repair (2026-10-20)

## Protocol before changes or execution

Preserve the complete 24-cell v2 pilot and its nine failed return gates. No
manuscript edit, training, full sweep, parameter tuning, tolerance widening or
replacement of historical rows. Expected return gate remains [9.95, 10.5]s;
incumbent certification must finish strictly before 10s, independently.

The diagnostic selects exactly the nine budget_ok=False rows in
results/factor_contract_pilot_20261020_v2/summary.csv, in their original order.
Verify that prior audit is complete/failed with only those return gates failing,
and verify its frozen artifacts before selection. Copy the previous plan/CSV/audit
as selection evidence. Retain input, seed 42, case, 10s budget, explicit frozen
GNN identity and requested/effective/nested configs. Diagnostic nominal solve
allocation is 90s. Each job has a fresh process, empty work directory and empty
exclusive NUMBA_CACHE_DIR, JIT enabled, hash seed 42, one thread requested for
Torch/Numba/BLAS. No warmup, padding, adaptive retry or score-based exclusion.

Use opt-in buffered perf_counter spans around Python phase entry points and
backend wrappers. Do not patch compiled Numba dispatchers or change solver
algorithms during diagnosis. Record the original solve clock/cutoff, absolute
entry/exit times, parent IDs, exception paths and explicit deadline arguments.
Derive inclusive and exclusive post-cutoff time, subtracting direct-child
intervals to avoid double counting. Unwrapped work remains attributed to its
nearest recorded parent; a span is not proof that a particular inner kernel or
JIT compilation caused its duration. The previous cProfile attribution anomaly
is not used as causal evidence. Never pool traced timings with uninstrumented
performance observations. Trace overhead may change paths/availability.

TDD must precede trace APIs and any deadline repair. Validate nesting, clock
arithmetic, exception restoration, exclusive-time conservation and opt-in CLI
marking/collisions. Reopen phase CSVs and audit interval/parent/clock/hash
consistency, routes, certificate, source/input/model/config and cold state.
Source/protocol/config/cache drift aborts; algorithm/return failures are retained.
Freeze source, inputs, model, exact jobs/configs and this protocol before launch.

After diagnosis, write deterministic fake-clock regressions for evidenced
deadline gaps, repair only those gaps and run relevant tests plus the full suite
and unchanged goldens. Preserve diagnostic source/results before this repair.
Then freeze a separate, uninstrumented confirmation on the same nine cells:
another 90 nominal solve seconds, same gates and cache policy. Execute each once,
preserve remaining failures, and report residual limits instead of chasing a
passing rerun. This selected failure subset is not a population performance or
six-factor causal estimate. LAC/longer-horizon validation remains separate.

## Results

Preflight: initial Red had six failures and three collision tests which only
checked exit code; after strengthening their error-message assertions all nine
failed before implementation. Green: 56 trace/factor tests, then 112 including
native certificates and exception-output coverage. Full suite: **547 passed in
141.85s**, with the existing expected PyVRP infeasible-fixture warning. Ruff,
touched-file format and whitespace checks pass. Native algorithms are unchanged.

Exact command from the project root, before any diagnostic child:

```sh
.venv/bin/python scripts/run_return_timing_diagnostic.py \
  --output-dir results/return_timing_diagnostic_20261020
```

The confirmation will use a separate output and `--confirmation`, after a
separately tested and frozen repair. Diagnostic results are pending.

## Diagnostic completed; repair specification before implementation

The nine traced jobs completed: certification/clock/provenance/binding/cold gates
9/9; return gate 4/9. Phase CSV audit passes, with 291 files sealed before repair.
Source: de633e0ce87de78a5b56a8f456efdd052db3044a5bfc3a2fc38c6673cf8f936d.
The recorded post_cutoff.csv assigns 5.869656s exclusive post-cutoff time to
solvers.local_search, 0.227801s to repair.op_tw_greedy, and much smaller remaining
spans. This identifies phase occupancy, not the precise opaque kernel/JIT cause.
Five traced returns still fail. Never treat the four instrumented passes as
replacement observations for the earlier uninstrumented failures.

Static follow-up finds that local_search and td_inter_route_polish check the
clock between neighborhoods but do not forward a cutoff into relocate, swap,
swap(2,1), cross-exchange or cross-tail. Their Python loops can start further
route-pair kernels after an earlier call crosses the cutoff. Two-opt similarly
lacks its own entry/exit guard. Tests will force exactly that structural gap;
they do not retroactively prove which inner operation caused each old delay.

Add optional absolute perf-counter deadlines to those private helpers, forward
the caller's deadline from both search paths, stop before starting more work,
and discard late proposals/cache inserts. Check before initial feasibility/cache
work and after uncancellable kernel returns. Preserve their unbudgeted defaults,
search order, moves and exact fingerprints. No GEC/SP/controller parameter,
initialization, acceptance or certification change is part of this repair.
Native/JIT calls already in flight remain uncancellable; remaining return-gate
failures must be disclosed, not hidden by warmup or a new time reserve.

## Repair preflight, recorded before confirmation

Twenty deterministic regressions failed before implementation and passed after
the change. Nine additional boundary cases cover expiry during cache creation
and between a route-cost kernel and the pair-search kernel. The 29 tests exercise
both ordinary and GNN-pruned dispatch, late memo suppression, two-opt and both
search entry paths. Six old fixture failures were two-opt stubs rejecting the
new keyword; only four stub signatures were updated to accept it, with their
original assertions retained. The final relevant group passes **239 tests**.

The repair changes only src/vrptw/local_search.py in runtime code relative to
the frozen diagnostic. Five neighborhood helpers plus two-opt take optional
absolute deadlines; the two search paths forward them at 12 call sites.
Checks stop further Python scans, cache setup and kernel dispatch after expiry,
and reject late results before memoization/proposal return. Default deadlines
remain None, with original traversal/order/thresholds and move formulas.
Source/model/input/config/cold-policy invariance and both old goldens are kept.
The full repair suite passes **576 tests in 170.54s**, with the same expected
PyVRP infeasible-fixture warning. Both existing golden files and all unbudgeted
fingerprints pass without regeneration or tolerance changes. Ruff, format and
whitespace checks pass. All 291 diagnostic evidence files remain byte-identical.

The separately declared confirmation command is:

```sh
.venv/bin/python scripts/run_return_timing_diagnostic.py \
  --output-dir results/return_timing_confirmation_20261020 --confirmation
```

It uses the same nine original failed cells once, with phase tracing disabled,
and is not pooled with the diagnostic or the earlier 24-cell source. Its
90-second nominal allocation and the original [9.95, 10.5]s gate are unchanged.

## Uninstrumented confirmation completed

All nine selected jobs ran once, without phase tracing or cProfile. The
**overall audit remains failed**: certification, clock, provenance, binding
and cold/cache gates pass 9/9; return timing passes only **4/9**. All nine
processes returned a feasible exact-cover result and zero process errors.
The five failed return cells remain retained:

| Input / case | Solve return (s) | Selected capture (s) |
|---|---:|---:|
| R1_2_1 / F101111 | 12.849514 | 7.237668 |
| R1_2_1 / F111111 | 15.589045 | 9.384854 |
| R1_2_1 / F000000 | 12.108082 | 9.752703 |
| c101 / F000000 | 12.213536 | 7.931336 |
| c101 / F111011 | 12.015440 | 5.213114 |

Across all nine returns, solve latency ranges 10.055548–15.589045s.
The latest selected capture is 9.920802s, strictly before ten
seconds. Every certificate/route is independently reopened and checked in the
original coordinate/constraint space. None of the late return observations is
silently used as a new pre-cutoff incumbent.

| Input | Selected jobs | Return passes | Certification / clock / integrity passes |
|---|---:|---:|---:|
| RC2_4_1 | 2 | 2 | 2 |
| R1_2_1 | 3 | 0 | 3 |
| c101 | 4 | 2 | 4 |

Confirmation source SHA-256:
`0f9595e2f4f58ba9f4b0a5b842dd345f90609843756ce32cc935546f72d5b9f0`.
Its artifact manifest verifies 289 files (the manifest itself excluded).
The diagnostic remains separately sealed, with 291 original evidence files
unchanged. Both stages retain source/tests, input/model/training metadata,
exact commands/configs, empty-cwd/cache entry evidence and stdout/stderr.

Numeric summaries come from each stage's recorded summary.csv and the
diagnostic post_cutoff.csv. Validation/analysis logs and a stage_inventory.csv
with source IDs and raw-result hashes are additional under
results/return_timing_validation_20261020/. Its diagnostic column is explicitly
instrumented. These are separate source/measurement stages on a selected
failure subset, not pooled measurements or a causal before/after estimate.
Some confirmation returns are larger than earlier observations; no wall-clock
improvement or fixed-overrun claim is supported by this confirmation.

## What is resolved and what remains

The deterministic tests establish entry/loop/post-kernel deadline propagation
and suppression of late proposals/memo writes in the audited neighborhoods.
The unbudgeted exact fingerprints remain unchanged. This is a structural
cancellation repair; it does not establish the precise inner cause of the old
local-search spans or of the five new late returns. Those confirmation runs
were deliberately uninstrumented, so their remaining latency is not assigned
to a particular kernel, compiler, GEC routine, backend or host-load cause.

Cooperative checks cannot interrupt an already running native/JIT/backend call.
Other previously identified helpers also retain coarse cancellation boundaries.
Consequently, the implementation does not establish a hard return deadline, and
the unchanged operational timing gate still fails. Further work needs a new,
separately declared diagnostic with finer opaque-call/cache coverage and/or an
explicit decision about supervisor-level interruption and incumbent delivery.
Do not add an arbitrary reserve, warm caches, widen tolerance, or rerun until
passing. No further solve was launched after this confirmation.

Publication launch and longer-horizon/controller/LAC coverage stay open. No
full sweep, checkpoint change, retraining, manuscript edit, author response
update, solver ranking or significance claim is included.
