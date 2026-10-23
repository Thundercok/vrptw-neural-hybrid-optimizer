# Native Pre-Cutoff Incumbent Certification

## Scope

This extends the monotonic-clock repair described in
`native_diagnostic_20261019.md`. ALNS and the native hybrid family now return an
independently validated incumbent snapshot captured inside their solve budget.
Historical diagnostic/pilot results, training artifacts and manuscript files
are unchanged. No new operational pilot or publication sweep was launched.

This is in-process route certification. It does not preempt HiGHS, Numba, Torch
or Python calls, establish a hard return deadline, approve a publication protocol,
or demonstrate any routing-quality/GNN improvement.

## Contract

- The budget starts inside `solve()` before RNG setup, GNN inference and greedy
  construction. Constructor/checkpoint loading remains outside the benchmark's
  existing solve scope. Explicit and per-customer budgets use absolute
  `perf_counter()` deadlines.
- A candidate must belong to the original `Inst`. Customer IDs must be integers
  in `1..n`, with every customer appearing exactly once. Booleans and fractional
  IDs are rejected without truncation.
- The certifier copies customer-only routes and recomputes capacity, waiting,
  service-start windows, depot return and double-precision travel distance from
  the instance. It does not trust `Plan._ok`, `_cost` or cached route arrays.
  The instance is assumed immutable during a solve, as elsewhere in the native
  search. Distance uses `math.fsum`; final insignificant digits may differ from
  the search's cached summation order.
- Snapshot construction, independent validation and route hashing must all
  finish **strictly before** the absolute cutoff. Finishing exactly at cutoff
  is late. Validation/hash time consumes the same budget as search.
- Captured incumbents use the native fleet-first comparison: fewer vehicles,
  then a TD improvement greater than `1e-6` at equal fleet. A later invalid,
  worse or post-cutoff result cannot replace the saved snapshot, even if a helper
  mutates its input plan.
- Initial construction is subject to the same checks. If no incumbent is
  certified, `NativeNoSolutionError` is raised; a late feasible construction is
  not silently returned as a valid score.
- Without a finite budget, validation still applies and `cutoff_sec` is `null`.
  Such a certificate makes no finite-cutoff claim.

Capture sites cover initialization, main-search promotions, periodic and plateau
recombination, split results, fixed-NV/committed-search internal bests, route
elimination, TD polishing and the remaining-budget loop. A helper's intermediate
neighborhood moves are not automatically certificates: they become eligible at
the instrumented incumbent boundaries after complete validation.

Split children retain their own local-instance budgets. Child certification
failure falls back to that partition's original routes. A merged solution must
be certified again using original customer IDs under the parent cutoff. The
recursive reconcile pass shares the parent's certifier and original clock origin;
it cannot erase an earlier certificate or restart elapsed time. If the parent
cutoff has passed, its saved full-instance snapshot is returned.

## Evidence and Consumers

`solver.native_certification` and the benchmark JSON's `native_certification`
contain schema version 1, policy, clock, cutoff, rejection counters and status.
The CLI exports this block on success and on exceptions after certification
initialization. Successful status is `certified`; absence of an eligible snapshot
is `no_certified_incumbent`, with `certificate: null` and no feasible result.

The selected certificate contains:

- `captured_sec` and `cutoff_sec`, relative to the original native solve start;
- full-precision `nv`/`td`, phase/iteration and independent validation flags;
- `routes_sha256`, hashing ordered customer-only routes as compact UTF-8 JSON:
  `sha256(json.dumps(routes, separators=(",", ":")).encode("utf-8"))`.

The existing CLI input/source/model hashes bind the result to its provenance.
The route hash binds the certificate to the exact serialized return routes;
neither the route order nor customer order is canonicalized.

Native `trajectory_log` now contains only certified promotions, at unrounded
capture times with route hashes. The CLI still appends its separate `phase:
"return"` observation using actual solve latency. A return observation after
cutoff is not a new pre-cutoff incumbent. Numeric `history` and `solver_history`
retain their search-diagnostic role for API compatibility; they can describe
attempted candidates and are not route certificates.

`native_certification.elapsed_sec` is sampled at final snapshot selection;
subsequent logging/return bookkeeping can add latency. The CLI's `runtime_sec`
remains the return-latency measurement. The existing operational timing gate is
unchanged, and `hard_return_deadline` remains explicitly false.

## TDD and Validation

The first behavioral Red run produced 13 failures against the prior runtime:
late/equal-cutoff construction was returned, route-feasible inexact initial plans
were accepted, and late mutating tail helpers could replace the incumbent. These
tests were written and run before implementing the certifier.

The new test plan uses deterministic fake clocks for cutoff boundaries and
separate integration checks for solver/CLI wiring:

| Area | Test type | Required invariant |
| --- | --- | --- |
| Initial plans | Solver integration | Late construction and missing/duplicate customers fail explicitly |
| Original validation | Unit | Stale caches, capacity/TW/depot/service defects, nonfinite data, invalid IDs and foreign instances cannot certify |
| Cutoff boundaries | Unit + solver integration | Validation/hash completion before cutoff succeeds; equality/late completion retains the prior snapshot |
| Incumbent ownership | Unit + solver integration | Mutating helpers, worse candidates and later overruns cannot corrupt a saved route snapshot |
| Helper improvements | Solver integration | Fixed-NV and committed-search internal incumbents survive a later caller overrun |
| Clock/budget scope | Solver integration | GNN inference and derived budgets count; split/reconcile keeps the parent origin and fallback |
| Lifecycle/API | Solver + CLI integration | Independent solves reset certification; unbounded mode works; success/failure JSON includes certification |

Commands from the project directory:

```sh
env PYTHONPATH=src .venv/bin/pytest -q tests/test_native_certification.py
env PYTHONPATH=src .venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check src/vrptw/native_certification.py \
  src/vrptw/solvers.py scripts/benchmark.py tests/test_native_certification.py
git diff --check
```

The focused certification suite passes **55 tests**. The full suite passes
**322 tests in 90.84 seconds**, with the existing expected PyVRP penalty warning
from the infeasibility test. Repo-wide Ruff, format checks on all four changed
runtime/test files, and `git diff --check` pass. Existing solver fingerprints
also pass without regenerating their baselines.

These tests do not replace broader instance, seed and cutoff operational
validation. All three earlier diagnostic stages keep their original evidence
and interpretation; no old trajectory is retroactively promoted to a certificate.
