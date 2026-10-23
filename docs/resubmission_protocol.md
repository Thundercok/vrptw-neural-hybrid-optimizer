# Resubmission Experiment Protocol

Status: preparation draft, updated 2026-10-19. This is not a completed replication or
permission to launch the full suite. Historical CSVs and manuscript sources stay
unchanged. Pilot results are operational checks, not performance evidence.

## Recovered GNN

| Item | Verified Value |
| --- | --- |
| Local checkpoint | `data/checkpoints/gnn_edge_predictor.pt` |
| Archive tag | `research-history-before-cleanup` |
| Tag commit | `d1a48ecc312f1d6c2a2438dc4ea7b68992b46d99` |
| Original path | `docs/legacy_archive/model/gnn_edge_predictor.pt` |
| Git blob | `e4435a74393fb4a166d15ba45d38b15371abfa79` |
| SHA-256 | `1f196f4e7678841a2f9c701f3bf5bf7155735ccc7502e8e1aaa64b4199591429` |
| File size | 429773 bytes |
| Architecture check | All 53 keys and tensor shapes match; strict loading passes |
| Inference check | Finite dense heatmaps at 100, 200 and 400 customers |

The same blob exists at commit
`ca8a84b5cdc4f9498b75c980fbdc205e05c83ee6`. This does not prove that it was the
file used by historical runs: their recorded path was `docs/model/...`, and they
did not record a model hash or a complete working-tree snapshot.

No checkpoint-specific training seed, training-instance list, validation split,
or selection log has been recovered. The current `train_gnn.py` discovers elite
plans from result directories and saves a bare state dictionary, without a
held-out split manifest. That describes the available training code, not proof
of the recovered checkpoint's actual training history. Do not claim unseen-
instance generalization or reproduce the paper's recall numbers from this file
alone. Do not retrain on evaluation elite plans to fill this gap.

Further audit (2026-10-17) located the exact blob's first available addition at
`45365c89d21f87f2b47560995aea2ec5ca0bdb64`; its historical trainer also lacks
seed/split provenance. Unused GH200 instance names are not a safe geometry-held-
out training pool: several variants share the same coordinates. A new synthetic,
geometry-disjoint manifest and manifest-only trainer are prepared instead. See
[the retraining handoff](antigravity_handoff.md). This does not establish the
old model's training history or reproduce its claimed performance.

The new seed-42 retraining completed on 2026-10-17 with 48 synthetic training
and 12 validation instances. Its validation-selected checkpoint (epoch 71 of
150) has recorded source/input/label/model hashes and independently recomputed
validation loss. See [the execution report](gnn_retraining_20261017.md). No test
inference or solver-quality evaluation was performed. One nominal ten-second
ALNS label run returned in 10.576862 seconds; this is disclosed, not treated as
passing deadline validation. The new model is not automatically substituted for
the recovered model in historical tables or pilots.

## Evaluation Contract

- Freeze the same 74 instances as the existing paper selection: all 56 Solomon
  instances; `C1,C2,R1,R2,RC1,RC2` with suffix `_2_1` and `_2_5` (12 GH200);
  the same six families with suffix `_4_1` (6 GH400). Record input hashes.
- Proposed replication seeds: 42, 43, 44, 45, 46. No best-seed selection.
- Proposed primary cutoffs: 10, 60 and 300 seconds, with independent cold starts
  for each cutoff. Do not silently reuse a 300-second prefix: the hybrid reserves
  a fraction of its declared budget for tail phases, so this is a different
  experiment. A continuous anytime trace can be reported separately once every
  incumbent update, including tail phases, is timestamped.
- Use fresh processes, empty per-run archives/pools, frozen pretrained weights,
  and a documented CPU/thread policy. Never reuse evaluation solutions between
  solvers or seeds. Online learning must restart from the declared initial state.
- Record setup, model loading, construction, inference, search and return times.
  The current pilot budget covers `solve()` but excludes solver construction and
  checkpoint loading. External adapters must adopt one explicit timing contract;
  publish setup and end-to-end latency as well, rather than equating unlike timers.
- Validate complete customer coverage, capacity, time windows, depot return,
  fleet count and independently recomputed travel distance from saved routes.
- Compare lexicographically by fleet count first, distance second. Report fleet
  wins/ties/losses separately; report distance only for matched fleets, with the
  matching rule and denominator stated. Use raw values, not rounded table cells.
- Keep the instance as the unit for across-instance inference. Report seed
  variability separately; do not treat all instance-seed rows as independent
  experimental replicates. Prespecify confidence intervals and multiple-comparison
  handling before inspecting the full results.
- Several benchmark variants share geometry. Report that dependence and include
  geometry-clustered sensitivity analysis rather than treating the test cases as
  independent spatial samples just because their filenames differ.
- Report failures, timeouts and overruns. Never carry a stopped run's final result
  forward and describe it as continued search. A late return is not automatically
  a valid solution at an earlier cutoff. The pilot tolerance is diagnostic, not
  a substitute for a publication cutoff policy.

The original SINTEF convention uses hierarchical fleet/distance optimization and
double-precision distances and travel times. Integer or DIMACS-style inputs must
not be silently mixed with that convention. See the
[SINTEF benchmark definition](https://www.sintef.no/projectweb/top/vrptw/solomon-benchmark/).

## External Baselines

| Baseline | Current State | Required Before Inclusion |
| --- | --- | --- |
| ALNS-Base | Native pilot verified | Same frozen protocol as full hybrid |
| Hybrid without GNN | Native pilot verified | Component attribution only, not an external learning baseline |
| Full hybrid with recovered GNN | Strict loading/inference and feasible three-scale pilot verified; one timing gate still fails | Resolve remaining overrun and disclose training provenance |
| Full hybrid with new held-out GNN | Seed-42, ten-second integration pilot passes all three scales after deadline repair | Broader cutoff/seed validation and fair performance evaluation; no superiority established |
| OR-Tools 9.15.6755 | Audited CP-routing adapter; 74-input numeric preflight and three-scale ten-second pilot pass | Accept/disclose integer approximation, CP-seed and cutoff limits; broader validation and stronger comparators needed |
| PyVRP 0.14.1 ILS | Pinned independent adapter; 74 model-building preflight inputs and five-solver ten-second pilot/audit pass | Accept/disclose integer approximation and cutoff limits; validate representative settings and multiple seeds/cutoffs; not a historical HGS replication |
| NeuroLKH-adapted CVRPTW | Pinned source/checkpoint, unmodified LKH build and CPU fleet-reduction wrapper; 74 preflights and six-solver pilot/audit pass | Accept adaptation/OOD/training-provenance limits and precision/cutoff policy; establish representative settings and resolve redistribution conditions; not an author-experiment replication |

The [version-pinned PyVRP source](https://github.com/PyVRP/PyVRP/tree/v0.14.1/pyvrp) exposes fleet minimization and
vehicle fixed costs, but those facilities do not establish that a particular
adapter matches this paper's objective or precision. Its default benchmark
settings must be audited, not copied without verification. Solver names must also
match the pinned version's actual algorithm.

The [official NeuroLKH repository](https://github.com/liangxinedu/NeuroLKH)
provides a CVRPTW implementation and pretrained example at 40 customers, with
training instructions covering 40-200. This is not evidence of a ready-made
400-customer Solomon/Homberger replication. A CPU adaptation now passes the
operational contract pilot; suitability as a representative publication baseline
is not established. The project's own GNN toggle cannot substitute for
an independent learning-augmented comparator.

No literature number will be inserted into a reproduced-baseline table. If an
adapter cannot meet the evaluation contract, report the limitation and narrow
the comparison claims rather than silently substitute another problem variant.

The earlier OR-Tools task passed a float where `run_ortools()` requires `Config`
and did not unpack its `(plan, elapsed)` return. The current adapter also replaces
the arbitrary fleet penalty with a proven bound, rejects quantity truncation,
charges model-build time, preserves fractional cutoffs and applies the requested
seed to the actual CP solver. Legacy minimum-30-second/5%-discount behavior is
removed. See [the contract audit](ortools_contract_20261018.md).

These repairs do not turn an integer model into exact double arithmetic or prove
independent randomized routing trajectories. One seed, three instances and one
cutoff validate operation, not comparative performance or a strict return deadline.
Legacy result tables and batch aggregation are not retroactively validated.

## Launch Gates

1. Freeze the evaluation files, solver/model versions, objective and timing
   contracts, configuration hashes, seeds, precision and analysis rules.
2. Resolve or explicitly disclose the recovered GNN's unknown training split.
   An inductive generalization experiment needs a new, verified held-out protocol.
3. External OR-Tools/PyVRP/adapted-NeuroLKH adapters now pass operational pilots
   on 100/200/400 customers. Accept/disclose their approximations and adaptation
   limits, establish representative comparison settings, and broaden
   timing/seed coverage beyond these pilots, without
   widening the pilot tolerance or relabeling historical violations as passes.
4. Validate every claimed ablation against actual executed components. In
   particular, legacy `gns` labels and the `full_no_gns` alias are not yet validated
   granular-search ablations and must not be interpreted as such.
5. Review the compute budget before launch. At 74 instances, five seeds and
   independent 10/60/300-second runs, the search budget alone is 38.03 hours per
   solver. Four primary comparators need about 152.11 hours sequentially; all six
   current pilot branches would need about 228.17 hours of search alone, before
   setup, failures, repeats, longer horizons or ablations. This is an arithmetic
   budget, not a wall-clock completion estimate.

## Small Pilot

```sh
uv run python scripts/run_benchmark_pilot.py \
  --output-dir results/resubmission_pilot_with_gnn \
  --time-limit 10 --seed 42 \
  --gnn-model data/checkpoints/gnn_edge_predictor.pt
```

This creates nine isolated runs: ALNS, no-GNN hybrid and GNN hybrid on the three
pilot sizes. It snapshots both source and model, and refuses to overwrite an
existing output directory. It does not execute the 74-instance protocol.

### Recorded Pilot Status

The first recovered-model pilot is preserved in
`results/resubmission_pilot_20261016_recovered_gnn_10s/`: nine feasible runs,
but two failed timing gates. This exposed a missing deadline in local search
following MILP recombination. The repair passes a shared deadline into local
search and checks it between passes, routes and neighborhoods.

The follow-up is preserved in
`results/resubmission_pilot_20261016_recovered_gnn_deadline_fix_10s/`:
nine feasible runs, eight passing timing gates. GNN-200 now returns in
10.005600 seconds, but GNN-400 returns in 10.542809 seconds and remains marked
`budget_ok=False` under the unchanged 0.5-second/5% diagnostic tolerance.
This is not a fully passing deadline validation. Cooperative checks between
operations do not guarantee interruption inside a long repair or neighborhood
kernel. No performance conclusion is drawn from this one-seed smoke test.

### New-Checkpoint Integration (2026-10-17)

The cooperative deadline repair adds operator-stage guards, cancellable repairs,
Shaw/Or-Opt/merge checks and rejection of late candidate moves. All 145 tests pass.
The exact historical delays were not reproduced during profiling; measured
structural defects and every instrumented run are disclosed in
[the deadline report](deadline_validation_20261017.md).

`results/resubmission_pilot_20261017_retrained_gnn_deadline_10s/` contains nine
fresh-process runs using the new validation-selected GNN checkpoint: all feasible,
all passing the unchanged timing gate, with runtimes 10.000538 to 10.036825 seconds.
Independent route/provenance audit passes. The old failed artifacts remain intact.
This validates integration only at the tested seed/scales/cutoff. No weights or
settings were selected using these pilot outcomes, and no solver superiority or
strict hard-deadline guarantee follows. The full publication sweep remains gated.

### External Baseline Contract (2026-10-18)

`results/resubmission_pilot_20261018_ortools_contract_10s/` contains 12 cold-start
runs on one source snapshot, adding OR-Tools to the three native/GNN branches.
All are feasible and pass the unchanged timing gate; independent route, objective,
provenance and OR-Tools incumbent-cutoff audit passes. All 165 tests pass.
OR-Tools R1_2_1 returned in 10.432464 seconds, while its selected incumbent was
captured at 5.464727 seconds. Its fleet differs from the native branches on the
200/400-customer cases, so no distance-gap comparison is reported for those pairs.
Precision/cutoff acceptance and strong independent comparators remain open gates.

### PyVRP Contract Pilot (2026-10-18)

`results/resubmission_pilot_20261018_pyvrp_contract_10s/` preserves 15 cold-start
runs on one source snapshot: ALNS, hybrid without GNN, hybrid with the frozen
retrained GNN, OR-Tools and PyVRP 0.14.1 ILS. All are original-feasible exact
covers and pass the unchanged timing tolerance; independent source/model/input,
route/objective and external incumbent-cutoff audit passes. All 185 tests pass.
PyVRP's model construction and initialisation consume the original absolute
deadline rather than restarting the stock runtime clock after construction.

At RC2_4_1, PyVRP has fleet 14 and distance 6374.716737 versus fleet 14 and
7247.371560 for the full GNN hybrid. At R1_2_1, PyVRP has fleet 21 versus the
native fleet 20, so those distances must not be compared. These single-seed
observations do not establish a solver ranking or stable learning benefit; no
weights/settings were selected from them. OR-Tools again returns late on R1_2_1
(10.399829 seconds), with its selected incumbent captured before ten seconds.

See [the PyVRP contract report](pyvrp_contract_20261018.md) for the full table,
source hashes and limitations. Representative classical settings, integer
precision acceptance, broader seed/cutoff validation, learning attribution and
an independent learning-augmented baseline remain publication launch gates.

### Adapted NeuroLKH Contract (2026-10-18)

`results/resubmission_pilot_20261018_neurolkh_contract_10s/` contains 18 cold-start
runs, adding independently sourced SGN candidates and an unmodified LKH backend
on Mac CPU. All 18 original-feasible exact covers pass the unchanged timing gate;
the independent route/source/model/binary/stage/candidate/cutoff audit passes.
All 217 tests pass. Every internal fleet-reduction process is terminated/reaped;
only complete tours validated before the parent wall-clock cutoff are selected.

This is explicitly **NeuroLKH-adapted**, not a reproduction of the author's
fixed-20-vehicle CUDA experiment. The checkpoint has no consumed-data/split
manifest, 400-customer evaluation is OOD, and redistribution conditions are not
cleared. Its operational pass does not prove representativeness or generalisation.

At RC2_4_1 the recorded fleets are ALNS 14, no-GNN hybrid 15, full GNN hybrid 17,
OR-Tools 17, PyVRP 15 and adapted NeuroLKH 24. At R1_2_1 they are 21, 21, 20,
22, 21 and 24 respectively. Do not compare distances across different fleets or
pool/cherry-pick earlier pilot outcomes. Stable hybrid/GNN benefit is not shown;
dedicated compute, randomized/block run ordering and multi-seed/cutoff validation
remain necessary. No weights or settings were retuned from these scores.

See [the full adapted-NeuroLKH report](neurolkh_contract_20261018.md) for raw
tables, pinned identities, conversion/fleet policy, warnings and reproducibility.
The manuscript, historical artifacts and training protocol remain unchanged.

### Native Timing Diagnostic (2026-10-19)

The fixed RC2_4_1 diagnostic completed 12 unprofiled runs (three native branches,
seeds 42/43, independent 10/60-second budgets) and three separately instrumented
profiles. Source/model/input and original route/objective audits pass, but the
operational gate fails on both no-GNN ten-second runs: 13.630654s and 11.014515s.
All cells and profiles remain preserved. No-GNN has lower matched-fleet TD than
full at both 60-second seeds; a stable GNN benefit is still not established.
The hybrid profiles also have a call-tree attribution anomaly and cannot be used
as an exact runtime decomposition.

Regression tests exposed a separate late-MILP/candidate acceptance defect,
repaired with post-call/post-validation guards. A new six-run guard-only retest
then exposed incompatible clocks: no-GNN seed 43 returned after 2.731449s while
its internal initialisation timestamp was 31.207s. Its timing and clock-consistency
gates fail; it is not a valid equal-budget comparison. The other five timing
gates pass. Both failed stages retain their original source snapshots and scores.

The native solver, operators, route pool and local search now share monotonic
`perf_counter()` deadlines and elapsed logs, matching the CLI measurement.
Absolute native-helper deadlines are no longer Unix timestamps. Thirteen new
clock regressions fail before migration and pass afterward; all **267 tests**
pass, with the expected PyVRP infeasibility warning. Ruff passes. These repairs
do not guarantee backend preemption or certify all native incumbents before a
strict cutoff. No weights, search settings, historical tables or manuscript
claims were changed. See [the diagnostic and repair report](native_diagnostic_20261019.md)
for frozen identities, all observations and the separate post-clock-fix retest.

The post-clock-fix retest in `results/native_monotonic_20261019/` completes all
six declared jobs once: 6/6 feasible exact covers, 6/6 timing passes, return times
10.002646--10.056941s. Independent route/provenance/config/clock-consistency audit
passes. It is a new source identity, not a replacement for either failed stage,
and still does not establish a strict cutoff, solver ranking or universal GNN gain.
