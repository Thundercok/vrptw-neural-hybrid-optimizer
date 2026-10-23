# Finer return-timing diagnostic (2026-10-20)

## Frozen specification before instrumentation or execution

The preceding uninstrumented nine-cell confirmation still fails the unchanged
return gate on five cells. Select exactly those five budget_ok=False rows from
results/return_timing_confirmation_20261020/summary.csv, in their recorded order.
Require its complete/failed audit, source
0f9595e2f4f58ba9f4b0a5b842dd345f90609843756ce32cc935546f72d5b9f0,
all five non-timing gates passing, matching plan/CSV/audit ordering and sealed
artifact hashes. Copy the prior plan, summary, audit and manifest as evidence.
Retain input, seed 42, factor case, 10s allocation and requested/effective/nested
configs. This diagnostic has five jobs and 50 nominal solve seconds, each once.

Keep independent fresh processes, empty exclusive work/cache directories,
NUMBA_DISABLE_JIT=0, PYTHONHASHSEED=42 and the prior single-thread environment
requests. Use the same frozen training-selected checkpoint. No warmup, padding,
arbitrary time reserve, tolerance widening, adaptive retries, tuning, retraining,
full sweep or manuscript changes. The return gate remains [9.95, 10.5]s and
incumbent validation/capture must independently finish strictly before 10s.

Extend only opt-in phase tracing with Python cache, two-opt and neighborhood
boundaries, Plan property getters, and a Numba compiler-event listener. Preserve
classmethod/subclass binding, property setters/deleters and original descriptors
on restoration, including exception paths. Do not wrap or replace compiled
dispatchers. The listener uses perf_counter and the active solve-thread stack;
ignore events outside solve or on other threads. Record nested compiler spans
and argument-type details. Remove the listener on restoration.

The documented [Numba Event API](https://numba.readthedocs.io/en/0.62.1/developer/event_api.html)
provides numba:compile notifications. The installed Numba 0.65.1 dispatcher
source places that event around compilation after a disk-cache miss; it excludes
cache loading, cache saving and execution. Archive hashes of the installed
event/dispatcher source in preflight. Compiler intervals include nested compiler
work; compute exclusive post-cutoff time with the same span arithmetic to avoid
double counting. Compiler END is an event boundary, not a success assertion.
Unwrapped work stays attributed to its nearest Python parent; absence of a
compile event does not identify the remaining work as pure kernel execution.

Write deterministic descriptor, event nesting/restoration, real tiny-JIT and
schedule-integrity tests first and retain Red/Green output. Validate opt-in
coverage without changing dispatcher identities. Freeze source/tests, protocol,
model, inputs, configs and exact jobs before launching any child. Audit trace
clock/interval/exclusive conservation and final route/certificate/identity/cold
state independently. Preserve timing failures; abort on identity drift.

Report numeric observations from recorded CSVs, with raw trace hashes. These
instrumented selected-failure runs are diagnostic evidence, not uninstrumented
timing confirmation, a causal before/after estimate or publication scores.
Only an evidenced, separately tested repair can justify a separately frozen
confirmation; an uncancellable compiler/kernel span alone has no cooperative
hard-deadline fix. Preserve all earlier stages byte-for-byte.

## Preflight completed before child launch

Initial Red: 12 failed, one positive-control pass. An additional conflicting-seal
regression failed before correcting the selector to verify both manifests
independently. All 14 new tests now pass; the relevant combined group passes
155 tests. Full suite: 590 passed in 79.73s with the existing PyVRP
infeasible-fixture warning. Both old golden files/fingerprints pass unchanged.
Ruff, four-file format check and whitespace checks pass. Changes to existing
runtime files are confined to opt-in phase_trace.py and its CLI scope metadata;
no native search algorithm, deadline, certification or parameter has changed.

The separately declared command is:

```sh
.venv/bin/python scripts/run_kernel_timing_diagnostic.py \
  --output-dir results/kernel_timing_diagnostic_20261020
```

Each of the fixed five jobs runs once; diagnostic outcomes remain separate from
the prior uninstrumented confirmation. No uninstrumented retest is authorized
by these measurements alone as a passing replacement observation.

## Trace-scope defect and recovery specification before repair

All five jobs completed once. The original strict phase audit failed with
ValueError: invalid root: after solve returned, CLI result assembly read cached
Plan cost/feasible properties four times while the tracer was still installed.
Those four getter spans form additional roots outside solve. This is an
instrumentation defect missed by the initial CLI failure-path test. Preserve the
entire stage, its failure record and all raw CSVs before repairing the tracer.
The stage is sealed with 208 evidence files, source
ac4f322f73eac2584012917c2d13e6b6a7c8cf596a8d2ed7ab76a2960f3abab7.
Do not repeat the five jobs or rewrite any original trace/audit.

Add success/exception regressions proving installed wrappers ignore calls
outside the solve root. Direct manual trace calls remain available for unit
tests. Repair only this opt-in scope, retaining descriptor/listener restoration.

A separately tested offline projection may recover the original solve tree:
require consecutive raw IDs; exactly one initial solve root; exactly four
trailing, childless roots named cost, feasible, feasible, cost; all with matching
clocks, finite ordered intervals wholly after solve ends, return outcomes and
independently correct inclusive/exclusive arithmetic. Reject any other roots,
overlap, clock/ID/arithmetic drift or edits to sealed files. Write a new CSV in
a separate analysis directory containing only the unchanged solve subtree.
Run the original strict audit on that projection. Hash/link raw and derived
files, disclose the excluded four spans and retain the original audit failure.
This projection cannot turn failed return gates into passes.

Derive compiler and exclusive post-cutoff attribution tables from the audited
projection CSVs; verify their sum equals the solve-root post-cutoff interval.
Recheck raw result gates against the frozen plan and prior audit. No further
benchmark solve or uninstrumented confirmation is part of this recovery.

## Recorded diagnostic and offline recovery

All five children returned feasible exact-cover plans without process errors or
timeouts. Certification, clock, provenance, config binding and cold/cache gates
pass 5/5. The operational return gate passes **2/5**, so timing remains failed.
The original strict phase audit also remains failed and preserved. The offline
solve-tree projection passes its own strict interval/hash/arithmetic audit for
all five traces, including independent rechecking of the raw result gates.
It retains 98,858 solve spans and excludes exactly 20 recorded post-solve getter
spans in separate derived CSVs. All 208 sealed raw evidence files remain intact.

| Input / case | Return (s) | Capture (s) | Return gate | Exclusive compiler time after cutoff (s) |
|---|---:|---:|---|---:|
| R1_2_1 / F101111 | 10.577297 | 6.588805 | fail | 0.568883 |
| R1_2_1 / F111111 | 10.146131 | 9.959543 | pass | 0.140206 |
| R1_2_1 / F000000 | 10.975401 | 4.927831 | fail | 0.963172 |
| c101 / F000000 | 10.000375 | 9.269292 | pass | 0.000000 |
| c101 / F111011 | 10.751686 | 4.889369 | fail | 0.741519 |

Across the recorded solve trees, exclusive compiler-event intervals account for
2.413780 of 2.450846 seconds after cutoff (**98.4876%**); other recorded/opaque
work accounts for 0.037066 seconds. Exclusive accounting removes nested compiler
overlap. The 274 compiler events include overload/internal helper compilation;
they are not 274 distinct VRPTW kernels. Every selected incumbent capture is
strictly before 10s, latest 9.959543s. Complete child wall time totals 73.896915s;
the solve allocation remains 50 nominal seconds.

The three failed return rows cross cutoff within compilation of:

- `_or_opt_intra_numba`, 9.924075–10.568883s, under `_intra_route_or_opt`;
- `_swap_21_evaluate_numba`, 9.033022–10.963172s, under `_best_swap_21`,
  including nested Numba overload compilation;
- `_cross_exchange_pair_pruned_numba`, 9.906601–10.741519s, under
  `_cross_exchange`.

The passing R1_2_1/F111111 row also crosses cutoff while compiling a pruned
insertion kernel, but returns within the existing tolerance. No cache-building
span is assigned exclusive post-cutoff time in this particular diagnostic.
This identifies measured occupancy in these instrumented runs. It does not
retroactively prove the cause of the five older uninstrumented failures or
establish improved timing/solution quality. Instrumentation changes execution
paths and available search time; old failed observations are never replaced.

Numeric sources are results/kernel_timing_diagnostic_20261020/summary.csv and
the separately derived results/kernel_timing_analysis_20261020/
diagnostic_summary.csv, compiler_spans.csv and attribution.csv. Projection
provenance and excluded rows are in projection_audit.json; raw CSV hashes are
carried into the derived tables. The offline command is:

```sh
.venv/bin/python scripts/audit_kernel_timing.py \
  --input-dir results/kernel_timing_diagnostic_20261020 \
  --output-dir results/kernel_timing_analysis_20261020
```

This command refuses an existing analysis directory, verifies the original seal,
and preserves the original failure record. Do not describe the raw strict phase
audit as passed merely because its solve-only derivative is valid.

## Engineering implication

No further native algorithm repair is justified by a Python boundary check:
the observed long compiler calls had already started before cutoff. An extra
post-call guard cannot preempt them. No JIT warmup outside the solve clock,
compile-cost subtraction, learned time reserve or warmed-cache confirmation was
introduced. The only post-diagnostic runtime repair confines opt-in tracing to
the active solve, with new success/exception regressions.

The next timing design should isolate search in a worker and deliver independently
certified incumbents to a supervisor before cutoff. It must specify one shared
solve clock, receipt/validation deadlines, original-space certificate checks,
fresh-cache setup, IPC and cleanup costs, whole-process CPU/wall accounting,
no-incumbent failure behavior and equivalent comparator budgets before execution.
Tests must cover a blocked compiler/backend worker and ensure a parent cannot
promote a late or undelivered candidate. Operating-system scheduling/termination
still cannot support an unconditional hard-real-time claim. That architecture
and its operational validation are not implemented by this diagnostic.

There was no new solver search change or uninstrumented confirmation, no full
sweep, retraining, manuscript edit or historical result replacement.

## Final verification

The final suite passes **602 tests in 79.46s**, with the same existing PyVRP
infeasible-fixture warning; the relevant final group passes 167 tests. There are
26 new tests across compiler/descriptor tracing, selection seals, scope and
offline projection. Both golden files and their exact fingerprints pass without
regeneration. Ruff, six-file formatting and whitespace checks pass.

Scope/projection Red initially had 11 failures. One CLI success fixture needed
the two counters normally set by solve; after correcting the fixture, replaying
the original unscoped wrapper reproduces the intended invalid-root error.
The direct success/exception property tests independently reproduced the defect
before repair. A final repair-dispatch regression also failed before extending
the same active-solve guard to the Python repair list wrappers. Red/Green,
intermediate checks and both fixture/recovery caveats remain recorded.

Against the pre-turn preservation inventory, only scripts/benchmark.py scope
metadata and src/vrptw/phase_trace.py changed among 2,947 protected files; the
other 2,945 are unchanged. New reviewable files are this report, the diagnostic
driver, offline auditor and two test modules. Historical results, native search
code, models, manuscript and old golden bytes are unchanged. Frozen raw and
derived seals, before/after source archives, the precise delta and final source
identity are recorded under results/kernel_timing_validation_20261020/.
No benchmark child was run again after the original five-cell diagnostic.
