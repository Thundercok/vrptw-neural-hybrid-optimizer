# GEC and independent controller binding (2026-10-19)

## Specification before implementation

Keep all earlier results, source snapshots, model bytes, manuscript files and
both golden fixtures. No sweep, model training or operational pilot is part of
this change. Defaults for existing solvers must preserve version-2 fingerprints.

`gec_enabled=False` means no displacement of an already routed customer to make
space for an unplaced customer. Direct insertion of the removed target route's
customers remains available. This applies to:

1. Hybrid GEC levels 2/3 in main search, committed search and final purge.
2. Deep-chain elimination in committed search and both tail calls: depth 1 only.
3. Buffered beam elimination in committed search and tail: zero ejections even
   in hard mode, with no Guided Ejection Search fallback or perturbation.

`_iterative_route_elimination`, ordinary relocate/swap/CROSS/compaction and
SP recombination do not recursively displace customers; they remain independent.
Existing standalone private helpers default to their prior behavior. Explicit
GEC-off parameters on the chain/buffered entry points enforce the same scope.
GEC-on keeps all existing per-routine depth/beam/branch limits without retuning.

All `Fabcdef` cells share one hybrid solver infrastructure; bits are GEC, SP,
macro DDQN, micro DDQN, LAC and GNN. Macro/micro 0 selects the existing rule
policy; 1 selects DDQN. The four combinations compose without setting the shared
`use_rl=False`. Macro policies use the same eligibility gate and mode list, and
`macro_enabled=True` in every cell keeps heuristic opportunities available.
Policies can choose different actions; a common action set does not require
identical action frequencies. LAC can run when both routing controllers are rule
based. Learned split is disabled in every bound cell.

Bindings must reject conflicting flags, controller transfer weights, neural
scale bypass, and GNN identity drift. GNN-on requires the explicit, frozen
validation-selected checkpoint; GNN-off forbids loading/inference/guidance.
The CLI must accept factor case IDs and preserve ordinary legacy entry points.
Legacy `full_no_macro` must use the rule macro rather than pinning DEFAULT;
`full_no_gec` must use the global GEC flag rather than depth alone.

Counters/metadata must distinguish actual macro/micro rule and DDQN selections,
replay sizes and training-call counts. Rule-selected components must not infer,
enqueue replay or update networks. Frozen solves suppress controller updates.
Initialization of unused network objects remains common setup; zero allocation
or zero setup cost is not claimed.

Tests precede implementation: forced ejection/direct-insertion cases, hard-mode
buffered fallback, real main/committed/tail forwarding, all four controller
combinations and all 16 planned cell bindings, LAC independence, GNN contract,
then the existing full suite. The frozen design/jobs remain unchanged and
`launch_ready` remains false.

## Implemented binding

`vrptw.ablation.bind_ablation(case_id, cfg, gnn_model=...)` returns
`AblationHybridSolver` and a new configuration without mutating `cfg`. The CLI
accepts six-bit factor IDs, including all 16 planned cells. It creates neither
an experiment executor nor a revised job schedule. `F000000` remains the common
hybrid infrastructure with rule controllers, distinct from ALNS-Base.

The common class keeps `use_rl=True` for compatibility and independently sets
`ctrl.use_rl`, `op_ctrl.use_rl` and the micro dispatch flags. Existing rule trees
are reused. Both macro policies enter at
`no_imp >= max(ctrl_start_floor, ctrl_start // 2)` and share the same mode list.
`macro_enabled=True` retains the macro-gated SP/restart machinery in both levels.
Micro-on includes the existing policy gate; its separate effect is not identified.
The standard CLI parameters are common across cells except declared factor
flags, SP phase switches, model path and case identity.

All controller objects are initialized in the common order, including unused
networks. Rule components do not infer, insert replay or update their networks.
LAC is independent of both routing policy choices. Transfer via either the
configuration or direct `load_weights` is rejected. Setup is not claimed to have
zero cost for disabled components.

GNN-on requires the explicit checkpoint with SHA-256
`365de53beba09097d1176a8b102ced8d6d97311f5a3ac82186b116d3290e1b97`.
Loading, missing-model, conflicting-path/hash, off-guidance and live controller
selection drift checks fail closed. Search-time revalidation runs after native
timer/deadline initialization, so its cost is charged. A fake-clock regression
consumes more than the cutoff in validation and verifies that no incumbent can
be certified afterward. This does not provide a hard return deadline.

The inventory has nine hybrid call sites: three calls to the hybrid GEC helper,
three deep-chain calls, two buffered calls, and one direct-only iterative
elimination call. The latter is intentionally retained. Own GEC-off uses depth 1;
deep-chain off clamps even an explicitly large requested depth to 1; buffered
off passes zero ejections to the beam and skips GES even in hard mode. ON uses
the previous routine-specific limits, including the scaled deep-chain limits;
`gec_max_depth` does not describe every routine's ON depth.

Future legacy `full_no_macro` runs now select `RuleMacroHybridSolver` with the
macro machinery enabled; `full_no_gec` uses the global flag and keeps depth 3.
Old rows under these labels retain their old source/config meaning and are not
retroactively certified as valid controls. The common factor class adds shared
macro eligibility; it does not silently rewrite legacy rule-policy behavior.

## Instrumentation and evidence

CLI output records policy names, actual selection-call counters, replay sizes,
training-call counts and actual nested configurations for macro, micro, LAC and
route pool. `controller_counts` counts policy selection calls, not individual
neural forwards. Ineligible DEFAULT macro choices remain in `mode_trace` but
do not count as a learned/rule controller call in factor bindings. Training-call
counts are controller `step` counters: attempts with insufficient replay do not
imply an optimizer update. Unit tests separately spy on forwards and verify
actual weight changes with small valid batches. Pool/controller configuration
snapshots are taken from their module objects, not inferred from the outer config.

All evidence is additional under `results/gec_controller_tdd_20261019/`:

- `red.log`: 46 failures / 2 passes; `red_extended.log`: 54 failures / 4 passes,
  before implementation. Missing binding APIs and leaking/missing GEC controls
  account for these Red cases.
- `green_initial.log` preserved eight fixture errors: controller tests requested
  an invalid zero eligibility floor. Fixtures were corrected to floor 1 and four
  short segments, forcing three eligible macro decisions. `green_corrected.log`
  then has 58 passes.
- `audit_red.log`, `transfer_red.log` and `live_drift_red.log` preserve separate
  failures before their repairs. `metadata_red.log` includes the missing nested
  configuration field and a clock-fixture mistake, corrected to use the native
  certifier's existing injected solver clock.
- `targeted.log` preserves four old SP-fixture stub signature failures after the
  new keyword was forwarded. The stub now accepts the keyword; assertions remain.
- `final_targeted.log`: **142 passes**, including 63 new contract tests.
- `full_suite.log`: 486 passes before the final metadata/drift checks;
  `final_suite.log`: **490 passes in 101.13 seconds**. The single warning is the
  existing PyVRP penalty-bound warning from its intentionally infeasible fixture.
- Ruff check, formatting on all nine changed Python files and whitespace checks
  pass (`lint.log`). Both existing golden files are unchanged; all version-2
  regression fingerprints pass without regeneration or tolerance changes.

`switch_audit_after.json` records 16 concrete factory/config bindings, zero solver
executions and `launch_ready=false`. Its remaining findings concern the legacy
`alns`/`gns` aliases and optional GNN loading on legacy `full`. The factor entry
point enforces its own model contract. This static/config audit is supplemented
by the forced dynamic unit tests; it is not a broad operational validation.
`gec_inventory.json` records call sites and `factor_config_invariance.json` checks
that non-factor CLI parameters are identical across the 16 bindings.

## Preservation and remaining work

Source SHA-256 using the existing `gnn_training.source_hash` convention:
`3479f1bc0eb552e148d659611d8fdf5377668a724b5f1ed3f04bb2653fc72c15`.

Of 2,546 pre-existing protected files, 2,539 remain byte-identical. Seven intended
edits comprise five implementation/configuration/CLI/audit files and two existing
test files. The new module, tests and this report are additional files. Historical
results, all model bytes, manuscript, both goldens, frozen design/jobs and earlier
evidence remain unchanged. Before/after snapshots, the initial tracked diff,
`final_delta.patch`, `verification.json` and artifact hashes preserve this audit.

The API is a treatment binding, not an experiment scheduler or a complete
execution protocol: callers still need fresh processes/controllers/archives and
recorded input/source/config identities. The old job manifest is not rebound or
launched. No new operational pilot, publication sweep, model retraining,
manuscript edit, statistics engine or equal-compute performance claim is included.
Next is a separately frozen, limited execution-contract pilot with the new
bindings and cache policy. Baseline/precision, statistics, compute acceptance and
the additional LAC acceptance-volume control still need resolution.
