# Native Certification Operational Pilot

## Declared Before Execution

This follows `native_certification_20261019.md`. It checks actual saved native
route certificates and return latency after the TDD implementation. It is not a
publication comparison, parameter/model selection exercise or permission to run
the 74-instance sweep. Prior results, checkpoints and manuscript files stay
unchanged.

- Inputs are the existing three pilot files: Solomon `c101.txt` (100 customers),
  Homberger `R1_2_1.TXT` (200), and `RC2_4_1.TXT` (400). These are existing
  evaluation geometries; no new generalization evidence is claimed.
- Branches are ALNS, hybrid without GNN, and full hybrid with the existing
  validation-selected seed-42 checkpoint. No external comparator is rerun.
- Seeds 42/43 and independent ten-second budgets give **18 jobs and 180 seconds
  of nominal solve time**. All jobs are unprofiled. No explicit JIT warmup,
  score-based exclusion, adaptive rerun, tuning or checkpoint selection is used.
- Order seed 20261019 shuffles the six input/seed blocks. A cyclic branch order
  gives each branch each position exactly twice. The complete schedule and
  requested/effective configs are frozen in `plan.json` before the first child.
- Each child is a fresh process with an isolated output/archive directory.
  Source/tests, original inputs, copied inputs, checkpoint and training metadata
  are hashed/snapshotted. Identity drift aborts subsequent jobs and preserves
  partial evidence. Solve failures are retained and do not cancel later cells.
- Torch/Numba/BLAS environment requests one thread. This is not a measured
  one-thread count for every backend. No host-load/thermal isolation or causal
  explanation for timing/quality differences is claimed.
- The solve interval includes seed setup, inference, construction, search and
  certification. Imports, solver construction and checkpoint loading remain
  outside that interval; complete-child wall duration is also saved.

## Separate Acceptance Gates

The independent audit recomputes route distance from coordinates using
`math.dist`, checks exact customer coverage, capacity, service-start windows and
depot return, and compares fleet/distance to the returned result and certificate.
It does not call the native certifier, `Plan.feasible` or cached objectives.
The exact serialized route hash must match the certificate.

Capture must satisfy `0 <= captured_sec < 10`, with the native monotonic clock,
declared cutoff and validation flags. Native selection elapsed time, certified
trajectory order/objectives/hashes and the separate CLI return observation must
agree. Final capture must match the final native trajectory promotion. Saved
intermediate hashes are checked for consistency, but intermediate route lists
are not stored and cannot be independently replayed by this audit.

The **unchanged** operational return gate is `9.95 <= runtime_sec <= 10.5`.
A valid pre-cutoff certificate with a later return can pass certification while
failing this timing gate. No tolerance is widened. No hard return deadline is
claimed. Source/input/model/config, cold-start, component and thread-setting
provenance are checked separately. Overall pass requires all gates and a
successful child process for every scheduled cell.

Report all cells and failures. Do not pool them with earlier diagnostic stages
or treat a prior trajectory as retroactively certified. Routing distance is
compared only at matched fleet sizes, if any descriptive comparison is made;
there is no significance test or universal GNN/solver ranking from three inputs
and two seeds at one cutoff.

## Reproduction

Run from the project directory, choosing a new output directory for a deliberate
independent repeat:

```sh
env PYTHONPATH=src .venv/bin/python scripts/run_native_certification_pilot.py \
  --output-dir results/native_certification_pilot_20261019 \
  --gnn-model results/gnn_retraining_20261017/model_seed42/best.pt \
  --order-seed 20261019
```

The runner refuses existing output directories and immutable audit files. It
writes plan/status, checkpoint/training/input/source snapshots, exact commands,
raw result JSON and stdout/stderr, summary CSV and an independent `audit.json`.
The audit hashes all evidence artifacts. Runtime source changes are not needed
for this pilot; the certification implementation remains unchanged.

## Verification Before Launch

The new harness tests cover the complete balanced schedule, valid certificates,
18 distinct tampering/feasibility/provenance defects, separate late-return and
certificate gates, failed-cell retention, identity-drift aborts and refusal to
overwrite an existing output directory. The combined targeted suite is run
before freezing the experiment source.

## Recorded Results

`results/native_certification_pilot_20261019/` completed every declared job
exactly once. All **18/18 certificates, clock checks, provenance checks and
unchanged operational return gates pass**. Independent audit status is `passed`,
with zero integrity errors. No run was excluded, repeated or used for tuning.

The following values are generated from the recorded `summary.csv`; ranges
pool only timing/capture observations, not routing objectives.

| Input | Jobs | Certificates / timing passes | Return seconds | Selected capture seconds |
| --- | --- | --- | --- | --- |
| C101 (100) | 6 | 6 / 6 | 10.000041–10.000807 | 0.243437–0.332970 |
| R1_2_1 (200) | 6 | 6 / 6 | 10.000360–10.111871 | 2.814134–9.921085 |
| RC2_4_1 (400) | 6 | 6 / 6 | 10.000164–10.262991 | 6.897211–9.973614 |

The latest selected capture is 9.973614 seconds. The longest return is
10.262991 seconds (no-GNN/400/seed43); its incumbent was captured at 8.663980
seconds. This passes the existing operational tolerance, and remains a late
return relative to exactly ten seconds. A certificate is evidence of the saved
incumbent at cutoff, not backend preemption.

Frozen identities:

- Runtime source SHA-256: `b1a4202e997de622538cf3477373c7cb4245901d8394fe90f3ea67387d8520ab`.
- Frozen training-selected checkpoint SHA-256: `365de53beba09097d1176a8b102ced8d6d97311f5a3ac82186b116d3290e1b97`.
- Independent audit SHA-256: `864e79f5238eaaf45f931bf7f084eb8df1bcdb474aeacbf40c63df699ba11f05`.
- The audit hashes all 81 evidence files, including source/tests, input/model/training snapshots, plan/status, commands, routes, logs and summary.

All 18 declared requested/effective config pairs were also compared with the
previous six-solver contract pilot. They match after removing the requested
seed and temporary output/checkpoint paths; no search parameter was changed.
All 143 separately hashed protected files (earlier diagnostic stages, seed-42
model artifacts and existing certification/runtime files) remain unchanged.

The frozen GNN was trained/selected on synthetic 100/200-customer inputs;
400 remains an out-of-size operational check. These observations do not establish
a stable GNN benefit, instance-level significance or a matched before/after
quality effect. Intermediate route lists remain unavailable for independent
replay despite their saved hashes. Hard return deadlines, broader cutoffs and
seed/instance coverage, and publication protocol acceptance remain open. No full
sweep or manuscript edit was performed.

## Final Verification

The 25 new harness tests pass, and the combined certification/diagnostic target
passes 88 tests before launch. The complete repository suite then passes
**347 tests in 90.78 seconds**, with the existing expected PyVRP warning from
the infeasibility test. Repo-wide Ruff, formatting of the two new Python files
and `git diff --check` pass. Existing solver fingerprints were not regenerated.

A final read-only check recomputes all 81 frozen artifact hashes and verifies
the schedule, capture-time/hash, feasibility, error and complete-child wall-time
columns for all 18 CSV rows against the saved raw results. All pass. The original
13 tracked working-tree diffs remain unchanged; only the new harness/tests/report
and this appended handoff update were added in this continuation.
