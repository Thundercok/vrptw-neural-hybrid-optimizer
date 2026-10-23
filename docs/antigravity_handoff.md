# GNN Retraining Handoff

Working directory: `VRPTW-Research-Optimization` inside this repository.
Status: full teacher generation and seed-42 training completed on 2026-10-17;
artifact audit passes. New-checkpoint three-scale, ten-second integration pilot
and subsequent OR-Tools, PyVRP and six-solver adapted-NeuroLKH contract pilots pass; broader timing and
publication launch gates remain open.
The 2026-10-19 native diagnostic and guard-only retest exposed further timing and
clock defects; their failed cells remain preserved. Late-candidate guards and
monotonic native clocks now pass 267 tests. See the separate diagnostic report
for the post-clock-fix operational retest; do not assume the earlier pilot passes
establish a hard cutoff or stable GNN benefit.
Do not edit the manuscript or overwrite historical results/model files.

## Findings

- Recovered historical checkpoint: `data/checkpoints/gnn_edge_predictor.pt`.
  Its hash and provenance are in `docs/resubmission_protocol.md`.
- The exact blob first appears in the available Git history at
  `45365c89d21f87f2b47560995aea2ec5ca0bdb64` (2026-08-13). That commit's
  `src/vrptw/train_gnn.py` scans result/elite directories and records neither
  a held-out split nor a training seed. This does not prove which files were
  actually consumed, but it cannot substantiate the old checkpoint's split.
- A proposed split using unused GH200 indices was rejected: different files
  share customer/depot geometry with the evaluation instances. Name or raw-file
  disjointness is insufficient for an unseen-geometry claim.
- The new path uses the existing `SyntheticVRPTWGenerator`, fresh ALNS labels,
  and no historical elite cache or pretrained model. This is a new experiment,
  not retroactive verification of the old results.

## Prepared Dataset

Manifest: `results/gnn_retraining_20261017/manifest.json`.

- 48 synthetic training instances: C/R/RC, 100 and 200 customers, eight per cell.
- 12 synthetic validation instances: two per cell, separate seeds/geometries.
- All original 74 evaluation instances retained as test; no test labels generated.
- Records include requested generator seeds, file hashes, numeric hashes and
  order-invariant geometry hashes. Cross-split overlap is rejected on load.
- Teacher: independent cold-start ALNS, seed 42, nominal ten-second solve budget.
  Every saved label is checked for input/source hash, teacher identity, exact
  customer coverage, feasibility and independently recomputed objective.
- The default sample count and teacher budget are initial engineering settings,
  not evidence that a publication-quality predictor has converged. Tune using
  validation only; never select checkpoints/settings using the 74 test results.

## Verified Status (2026-10-18)

- Initial pipeline suite: 117 passed. Following the deadline repair, the current
  suite passed 145 tests; after three baseline integrations the current suite has 217
  passing tests. Ruff and `git diff --check` pass.
- Prepared manifest: 48 train, 12 validation and 74 test instances; zero geometry
  overlaps across all three split pairs. The test set has 12 geometry groups,
  so later statistical analysis should account for shared geometry.
- End-to-end smoke completed: two ALNS labels, one training epoch and a
  validation-selected checkpoint in `results/gnn_retraining_20261017/smoke_model/`.
  Its 53 tensors are finite and load strictly; checkpoint and manifest hashes
  match the saved metadata. `smoke_only=true`; zero test-label files exist.
- Full teacher generation completed: 60 verified cold-start labels. One nominal
  ten-second run returned in 10.576862 seconds; retained and disclosed, not rerun.
- Full training completed: 150 epochs, 292.25 seconds elapsed. The selected model
  is `results/gnn_retraining_20261017/model_seed42/best.pt`, epoch 71, validation
  loss 0.4555501366655032. Strict loading, target/model/source hashes and independent
  validation-loss recomputation pass; no test inference was performed.
- See [the execution report](gnn_retraining_20261017.md) for edge diagnostics and
  limitations. Historical checkpoints, result tables and manuscript files have
  not been replaced.
- Deadline repair and new-model integration: nine feasible pilot runs, nine timing
  passes under the unchanged tolerance. See [the diagnostic report](deadline_validation_20261017.md).
  This is one seed at ten seconds, not evidence of routing superiority.
- OR-Tools contract audit (2026-10-18): 74 inputs pass numeric preflight without
  solving; the 12-run four-solver pilot and independent audit pass. The integer
  approximation, CP seed scope and 10.432464-second late return remain disclosed.
  See [the baseline report](ortools_contract_20261018.md).
- PyVRP 0.14.1 ILS contract audit (2026-10-18): 74 model-building preflight inputs
  and all 15 five-solver pilot runs pass, including independent artifact audit.
  Absolute cutoff includes initialisation; only validated pre-cutoff incumbents
  are retained. PyVRP matches fleet 14 and has lower distance than all native
  branches on RC2_4_1 in this single pilot; no universal hybrid/GNN gain is shown.
  See [the PyVRP report](pyvrp_contract_20261018.md). Historical GNN and prior
  pilot snapshots are unchanged.
- Adapted NeuroLKH (2026-10-18): pinned source/model and unmodified LKH build work
  on Mac CPU. All 74 integer/feature preflights pass without solving; all 18
  six-solver ten-second pilot runs and independent stage/route/hash/cutoff audit
  pass. This uses a declared fleet-reduction wrapper, not author fixed-20 CUDA
  experiments. Checkpoint split metadata is absent, 400 is OOD, and no top-level
  upstream license was found. No stable GNN gain or strong-baseline
  representativeness is established. See [the complete report](neurolkh_contract_20261018.md).

## Commands

Recorded commands, run from the working directory above. Labels used 601.39
seconds of actual search plus process/setup overhead; training took 292.25 seconds
elapsed. Training is already complete: do not launch a duplicate or overwrite its
output. A deliberately planned independent repeat needs a new output directory.

```sh
env PYTHONPATH=src .venv/bin/python -m vrptw.gnn_training targets \
  --manifest results/gnn_retraining_20261017/manifest.json

env PYTHONPATH=src .venv/bin/python -m vrptw.gnn_training train \
  --manifest results/gnn_retraining_20261017/manifest.json \
  --output-dir results/gnn_retraining_20261017/model_seed42 \
  --seed 42 --epochs 150
```

Both commands validate the frozen inputs. Target generation skips only existing
labels that pass provenance checks. Training refuses an existing output directory.
It starts a fresh CPU model, records source/manifest/label hashes and environment,
writes `history.csv`, and selects `best.pt` by validation loss alone.
`training.json` links the checkpoint hash to the full training protocol.
Training has no optimizer-state resume; an interrupted run is not a completed run.

`--smoke` on both commands uses separate `smoke_targets/`, one train/validation
instance, a one-second teacher budget and one training epoch. Its metadata is
marked `smoke_only=true`. Never substitute a smoke checkpoint for the final model.

The manifest freezes the teacher's source hash. If Python source changes before
label generation, use its `source_snapshot.zip` in an isolated environment or
prepare a new versioned dataset manifest. Do not modify the recorded hash to
make mismatched labels pass. New preparation uses the `prepare` subcommand and
requires a new output directory; preserve the original benchmark test set.
The current solver has changed since training as part of the deadline repair.
Historical audit/label regeneration must therefore use the frozen training source,
not rewritten metadata. The integration pilot records its separate source hash.

## Remaining Gates

1. Broaden timing/cutoff validation beyond the passing new-checkpoint pilot at
   100/200/400 customers, seed 42, ten seconds. Do not retune model/settings using
   benchmark outcomes. One pilot does not validate generalization or superiority.
2. Preserve and disclose the old GNN-400 and ALNS teacher overruns. Profiling exposed
   operator-stage and neighborhood cancellation defects, now covered by tests,
   but did not reproduce the exact old delays. Define a strict publication cutoff
   policy; cooperative checks are not hard real-time interruption.
3. Validate representative classical comparison settings and reproduce an
   independent learning-augmented baseline with matching objective, precision
   and timing. PyVRP/OR-Tools adapters and pilots are audited, not full literature
   replications or approved publication comparisons. Adapted NeuroLKH now has a
   working CPU adapter/pilot, with OOD/training-provenance and redistribution
   limits; its suitability as the independent learning comparator remains a
   protocol decision, not a completed author-experiment replication.
   Precision/cutoff acceptance, broader seed coverage and GNN attribution remain
   pending; do not tune on the observed evaluation pilot scores.
4. Do not launch the 74-instance publication sweep or replace paper numbers
   until those gates are satisfied. No citation/convergence claims were repaired
   by this engineering work.

## Latest Timing Work (2026-10-19)

See [the native diagnostic report](native_diagnostic_20261019.md). The original
12 unprofiled/three profiled RC2_4_1 matrix preserves both no-GNN ten-second
overruns (13.630654s/11.014515s). Provenance/routes pass; timing does not. At
60 seconds full and no-GNN both reach NV13 for seeds 42/43, with lower TD for
no-GNN on both. Do not tune or select weights from these test outcomes.

Late non-`None` MILP, greedy and LS results could bypass deadline guards; fixed
after Red tests, including post-validation/cache checks. The six-run guard-only
retest then caught a calendar/elapsed clock mismatch: NV43/zero iterations after
2.731449s, with an internal timestamp of 31.207s. That cell remains a failed
timing/clock case, not an excluded outlier or a passing retest.

All native budget producers/consumers, sub-solve deadlines and trajectory clocks
now use `time.perf_counter()`. External adapters and CLI already use that domain.
Native helper `deadline` values must be absolute perf-counter times, not epoch
timestamps. Epoch IDs and unrelated legacy reporting scripts are not migrated.
The suite passes 267 tests (one expected PyVRP warning), Ruff and whitespace
checks. The hybrid cProfile trees have an unresolved root/caller attribution
anomaly; recorded hotspot entries are provisional, not an exact phase breakdown.
Hard return deadlines and native pre-cutoff route certification remain open.

The separately frozen post-clock-fix retest is complete:
`results/native_monotonic_20261019/`, source
`bf22c622561a9ce91606e0c16a627e9b6e7a0348df8a9f0c3d52aa06e301a88c`.
All six declared jobs are feasible exact covers and pass the unchanged timing
gate (10.002646--10.056941s); route/hash/config/trajectory-clock audit passes.
Full requested/effective configs match the prior retest except temporary paths.
Keep all three stages separate. Next work is cutoff/incumbent certification and
protocol acceptance, not automatic launch of the full publication sweep.

## Native Incumbent Certification (2026-10-19)

Native pre-cutoff snapshot certification is now implemented via TDD; see
[the certification contract and verification report](native_certification_20261019.md).
ALNS and hybrid variants return only independently validated exact-cover
incumbents captured strictly before their monotonic cutoff, or raise an explicit
no-certified-incumbent error. The CLI exports the certificate on success/failure;
split/reconcile preserves the parent clock and incumbent. Native trajectory
promotions carry full-precision capture times and route hashes.

The 55 new certification tests and all 322 tests pass (90.84s; one existing
expected PyVRP warning). Ruff, touched-file formatting and whitespace checks
pass. Prior changes/results are retained; no manuscript edit, model change,
operational retest or full sweep ran. Hard return deadlines, broader operational
certification validation and publication protocol acceptance remain open.

## Certification Operational Pilot (2026-10-19)

The separately frozen three-scale/two-seed certification pilot is complete:
`results/native_certification_pilot_20261019/`. All 18 declared ten-second jobs
ran once in fresh processes, without profiling, tuning or adaptive reruns.
Independent route/certificate/clock/provenance audits and all unchanged return
timing gates pass. Source SHA-256:
`b1a4202e997de622538cf3477373c7cb4245901d8394fe90f3ea67387d8520ab`.

Returns span 10.000041–10.262991s; every selected capture is strictly before ten
seconds (latest 9.973614s). The 18 requested/effective config pairs match the
previous six-solver pilot except seed and temporary paths. The immutable audit
hashes all 81 evidence files; 143 protected historical/runtime/model files are
unchanged. See [the pilot protocol and results](native_certification_pilot_20261019.md).

The 25 new harness tests and all 347 tests pass (90.78s; one expected PyVRP
warning), as do Ruff, formatting and whitespace checks. Native certification
runtime code was unchanged during this pilot. This validates final returned
route certificates on three inputs/two seeds/one cutoff; intermediate route
lists are not available for independent replay. Broader cutoffs/coverage, hard
return deadlines and publication protocol acceptance remain open. No full sweep,
model change or manuscript edit ran, and earlier failed stages remain separate.
