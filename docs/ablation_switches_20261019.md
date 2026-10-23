# SP and learned-split switch contract (2026-10-19)

## Specification written before implementation

`pool_recombine_enabled=False` disables every route-pool recombination query,
including standard, NV-targeted and TD-only queries in main search, committed
search and all tail phases. Both the hybrid dispatcher and public recombination
entry point must stop before consulting or mutating the pool, dispatching MILP,
greedy fallback or local search, or updating SP counters/cache.

The four SP-specific column/diversity seeding helpers must also return without
work when this flag is false. Ordinary route collection remains available for
existing search features and non-SP heuristics. The capacity-scaling policy of
`RoutePool` is outside this repair; zero requested pool capacity alone is not a
reliable off switch. CLI `full_no_pool` must explicitly set the global flag.

`split_enabled=False` disables recursive split sub-solves (already guarded),
main-loop learned split and final learned split. Direct `try_split` calls must
return before episode execution, inference, replay insertion or training.
Frozen solves continue to suppress learned split even when enabled. Controller
construction remains unchanged to preserve the existing setup/RNG order; this
contract does not claim zero allocation or zero setup cost for disabled split.

ON controls must still execute the same helpers and retain the existing search,
acceptance, budget and native certification contracts. CLI component metadata
must reflect the global SP flag and learned-split flag. The read-only design
audit must stop reporting these two repaired leaks but keep unrelated gates open.

Verification uses small synthetic plans, forced execution paths and spies,
followed by existing regression tests. It does not estimate routing performance.
No full sweep, training run, historical result rewrite or manuscript change is
part of this repair. The initial expectation was to leave golden selection
unchanged. The regression evidence below required a separate fixture version;
the original golden file remains unchanged.

## Regression contract migration

The first full suite produced 423 passes and three failures, all Hybrid exact
fingerprints: R101 seed 1, RC207 seeds 1/7. Both requested flags in the original
golden configuration were already false, but the earlier code still executed
SP and final learned split. This is an intended behavior correction, so the
old claim that the fingerprints excluded those components was inaccurate.

Before changing fixture selection, frozen pre-repair source reproduced all
three old fingerprints. Instrumentation recorded 2/2/3 SP queries respectively
and one learned-split episode in each, despite both flags being false. This
reproduction uses three existing 200-iteration regression cases; it is not a
solver-quality experiment. See `legacy_reproduction.json` and its source script
in `results/ablation_switches_tdd_20261019/`.

The new `tests/golden/baseline_sp_split_off_v2.json` records the same 16
case/solver/seed combinations under genuinely disabled SP and learned split.
Creation and regression tests forbid SP dispatch and split episodes. The
original `tests/golden/baseline.json` is retained byte-for-byte and linked by
SHA-256. Exact tolerances remain unchanged; ALNS objective records must continue
to match the original. Fixture solve times are incidental test timings and
cannot be used as equal-compute performance evidence.

## Implementation and scope

- The hybrid SP dispatcher and public pool recombination entry point now return
  the existing incumbent immediately when disabled. The four dedicated SP
  seeders return before producing columns, destroy/repair calls or RNG draws.
- Both main-loop and final learned-split callers now check `split_enabled`;
  `SplitController.try_split` independently checks it before doing any work.
- CLI `full_no_pool` explicitly disables `pool_recombine_enabled`. Component
  metadata uses this global flag for `route_pool` and adds `learned_split`.
  These fields describe enabled components, not observed call counts; a frozen
  solve still suppresses learned split when its configured flag is true.
- Ordinary pool collection and capacity scaling are retained. No GEC depth,
  macro/micro policy, LAC rule, GNN weight, search budget or certification logic
  is modified by this repair.

The read-only audit in `switch_audit_after.json` reports zero disabled SP
dispatches and no `sp_off_leak` or `split_off_leak`. Its remaining code findings
are `alns_aliases`, `macro_confound`, `gec_scope`, `controller_composition` and
`explicit_gnn`. It records zero solver executions and keeps `launch_ready=false`.
The frozen design and all its original gates/results remain unchanged. This
repair does not establish a complete factorial execution binding or close the
statistical, baseline, precision and compute-protocol gates.

## TDD evidence

The evidence directory is `results/ablation_switches_tdd_20261019/`.

- `red.log`: 21 failures, 35 passes. The first split-caller fixture also allowed
  unrelated SP work, which changed its synthetic plan and obscured that check.
- `red_isolated.log`: after isolating that backend, **19 failures, 37 passes**
  before any solver implementation change. This is the relevant Red stage.
- `red_tests_spec.zip`: the specification and test sources from that Red stage.
- `green.log`: **56 passes** after the scoped switch guards, including ON controls.
- `full_suite.log`: the preserved first full-suite result, **3 failed / 423 passed**;
  all three failures were the legacy Hybrid fingerprints discussed above.
- `fixture_red.log`: missing-v2 collection failure before fixture creation.
- `legacy_reproduction.json` and `legacy_reproduction.log`: all three old
  fingerprints reproduced using frozen pre-repair entry points.
- `fixture_capture.log`: same 16 existing regression cases captured once with
  disabled-component calls forbidden. `fixture_comparison.json` records exactly
  the same three Hybrid objective changes; all fleets and ALNS objectives match.

No tolerance is widened and no failing log is overwritten. The new fixture is
separate from the old file; the old SHA-256 is
`92af6dc05839f900d1f7a83d6657ab02570b97914d3d6a3ba586941d399a1483`.

No new operational pilot was run after this runtime change. Earlier pilots
remain evidence only for their frozen source versions. A new limited contract
pilot remains necessary before any publication sweep; these tests establish
switch behavior and regression consistency, not routing superiority, timing
compliance or an SA/learning convergence theorem.

## Final validation and preservation

`final_suite.log`: **427 passed in 98.81 seconds**, including all 16 version-2
fingerprints with strict OFF call guards. The one PyVRP `PenaltyBoundWarning`
comes from the existing intentionally infeasible final-service/depot-return
fixture. Ruff check, formatting checks on all nine changed Python files, and
`git diff --check` pass (`lint.log`).

Runtime/source SHA-256, using the existing `gnn_training.source_hash` convention:
`1a1971fb8002596390b54ac19ce826166c1c74f222feeabbdc33787dc4a1f6cb`.
This matches the version-2 fixture's capture provenance.

The preservation audit compares 2,518 pre-existing files: 2,510 remain identical;
the eight intentional edits are five implementation/configuration/CLI files and
three existing test files. No missing or unexpected changed files are allowed.
Historical results, model/checkpoint bytes, manuscript files, the original golden
and the frozen equal-compute design remain unchanged. The new tests, report and
versioned fixture are additional files.

`verification.json`, `before_hashes.json`, the original tracked diff, before/after
source snapshots and `final_delta.patch` record the audit. `artifact_hashes.json`
covers the evidence files and deliberately excludes itself.

The next correctness work is an explicit GEC scope and independent controller
composition/binding for the planned cells. Those need their own tests before a
limited execution-contract pilot. No full benchmark launch follows automatically.
