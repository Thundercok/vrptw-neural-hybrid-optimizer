# Adapted NeuroLKH Contract

This is an independently sourced learning-augmented **adaptation**, not a
replication of the authors' original CVRPTW experiment or literature scores.
No manuscript, historical result, training label or checkpoint was replaced.
The publication sweep remains gated by precision/cutoff acceptance, representative
settings, seed coverage, component attribution and an approved compute plan.

## Pinned Assets

Upstream: [NeuroLKH](https://github.com/liangxinedu/NeuroLKH).
Commit: `32ab884c2fe6548ca4011eeb181af70fbfedc72b`.

The local checkout is `results/external/NeuroLKH/`, ignored by Git. The setup
script refuses a modified/different existing checkout and never resets user
files. It records tracked source, checkpoint and binary hashes, build command,
compiler version, stdout/stderr and creation time in `assets.json`.
The adapter rechecks the identity before loading or executing those assets.
No upstream C/Python source or checkpoint is vendored into the project.

```sh
env PYTHONPATH=src .venv/bin/python scripts/setup_neurolkh.py \
  --root results/external/NeuroLKH
```

This command has already completed locally; a different build needs a new root.
The original Makefile needed `SRC/OBJ/` created. It then built with Apple Clang
without source patches, compatibility flags or a system installation. The setup
script performs a fresh rebuild and retains the logs. The upstream `FindTour.c`
has three format warnings printing 64-bit `GainType` with `%d`; the adapter does
not parse those trial-cost log lines. Tour files and original-space validation,
not the potentially truncated log fields, determine results.

- Upstream tracked-source SHA-256:
  `a52338d7ee7f6500cf53fdb0de111b5d36e0e61e7b9deb6494e370b0b5f5fcce`.
- CVRPTW checkpoint SHA-256:
  `58287b23eedf9eecab5aadcf8ba640b56c50b1b6cfa3259eb39cd443a6072394`.
- Local LKH binary SHA-256:
  `7b06251e0f73f9a81189fd206fbec8f5513753e656e91749196e0417eb6caa38`.

The checkpoint contains only a `model` state dictionary: 584 finite tensors.
It is loaded on CPU with `weights_only=True` and `strict=True`; no unsafe
pickle fallback or missing-weight fallback is allowed. The original 30-layer,
128-hidden-unit SparseGCN implementation is imported from the pinned checkout.
There is no retraining, test-instance fine-tuning, own-GNN checkpoint reuse or
fallback to a native solver. The constructor loads weights outside `solve()`,
consistently with the existing benchmark's model-load policy; total latency is
recorded separately.

No top-level license file was found at this upstream pin. The external checkout,
weights and build remain local ignored research artifacts; their availability
is not treated as a grant to redistribute them. Redistribution/use conditions
must be resolved before packaging or deployment beyond this local workflow.

## What Was Adapted

The pinned
[CVRPTW driver](https://github.com/liangxinedu/NeuroLKH/blob/32ab884c2fe6548ca4011eeb181af70fbfedc72b/CVRPTW_test.py)
uses CUDA, fixes 20 vehicles and depot horizon 10, scales/truncates its own
synthetic inputs, and records trial costs rather than deadline-validated native
route plans. Those conventions cannot silently stand in for this benchmark.

The new adapter runs CPU inference with batch size one. Node features are
translated/normalised Euclidean coordinates with a common bounding-box span,
author-style demand `/50`, ready/due divided by `10*span`, and a depot indicator.
Travel features use the same spatial normalisation. The common spatial/time
factor preserves their relative units; search constraints remain unnormalised.
There is no clipping of demands, windows or capacity to match the network's
training distribution. Actual capacity magnitude is not a separate learned
input in this architecture; variation in capacity/service is an OOD limitation.

The graph uses 20 nearest non-self neighbours, including correct handling of
coincident coordinates and reverse-edge indices. Both directed heads rank
candidates. The split-graph candidate writer generalises extra depots to the
requested fleet and preserves the authors' real-depot bridge. It includes the
fixed mate and four distinct opposite-half candidates for each split node.
Depot edges are deterministic structural edges; customer ranks come from the
checkpoint. `.eval()` is used; the upstream BatchNorm layers have
`track_running_stats=False` and there is no dropout.

The [README](https://github.com/liangxinedu/NeuroLKH/blob/32ab884c2fe6548ca4011eeb181af70fbfedc72b/README.md)
demonstrates CVRPTW at 40 customers and describes training sizes 40-200.
Solomon/Homberger structure and especially 400 customers are distribution/size
generalisation tests, not an already validated pretrained replication. The
checkpoint has no training manifest, seed/split metadata or consumed-data hashes.
The synthetic generator in source is not proof of the exact checkpoint's
consumed dataset; neither absence nor presence of test contamination is proven.

## Feasibility and Objective

All customers are mandatory. Demands/capacity must be integral and nonnegative;
depot demand, ready and service must be zero. The full original instance is
retained: capacity, service at each customer, ready/due and depot return horizon.

The backend receives an explicit full matrix at fixed scale 100,000, with
**upward-rounded travel for both distance cost and travel time**. Service/ready
are rounded upward and due downward. This differs from nearest-distance costs
in the other integer adapters. The total travel-cost rounding bound is
`2*n/100000`. This is a conservative time-grid inner approximation, not the exact
double-precision SINTEF convention. Every accepted plan is rechecked against the
original matrix and exact customer cover; reported distance is original TD.

`PRECISION=1` avoids LKH's default extra factor of 100 overflowing scaled 32-bit
arc costs. Data are guarded below the backend's `INT_MAX/2` forbidden-arc sentinel.
The existing shared integer checks also reject unsupported quantities and unsafe
objective ranges. Original customer IDs map to tour IDs 2 through `n+1`; ID 1
and IDs above `n+1` are depots. A tour must contain the entire transformed-node
permutation and `-1/EOF`; a partial/duplicate/missing tour is never accepted.

LKH's fixed-fleet inner search optimises its travel objective; it is **not**
claimed to minimise the benchmark's fleet-first objective itself. The wrapper
starts at `n` available vehicles and selects retained plans lexicographically by
`(original-feasible fleet, original TD)`. After a valid incumbent with fleet `k`,
it restarts at `max(capacity fleet lower bound, k-1)` if that target is smaller.
At the capacity lower bound it keeps searching distance. Each internal restart
is a fresh LKH process with the same run seed and neural candidate ranks, with
no transferred tour, archive or result from another solver.

This is a declared heuristic fleet-reduction procedure, not a proof of optimal
fleet or infeasibility at a failed lower target. It intentionally differs from
the authors' fixed-20-vehicle experiment and must retain the label
`NeuroLKH-adapted` in any eventual comparison. No large fixed vehicle cost is
inserted into LKH's travel matrix, where it would also corrupt travel time.

## Wall-Clock Contract

The upstream
[GetTime](https://github.com/liangxinedu/NeuroLKH/blob/32ab884c2fe6548ca4011eeb181af70fbfedc72b/SRC/GetTime.c)
uses process user CPU time on this platform. The adapter does not treat that as
wall-clock time or trust a final backend assignment at an earlier cutoff.

The parent absolute deadline starts at `solve()` entry and includes input
conversion, features, SGN inference, file writing, every backend initialisation/
restart, polling, original validation and child cleanup. Model/binary preparation
is excluded setup, never repeated for free inside the reported search interval.
The run seed reaches every actual parameter file; there is no controller
training or warm start. `MAX_TRIALS=2147483647`, `RUNS=1` and
`STOP_AT_OPTIMUM=NO` remove practical trial/optimum early stopping. Trial counts
are not reported as native search iterations.

The backend writes original tour snapshots via `OUTPUT_TOUR_FILE`. The parent
observes complete snapshots, validates/costs them and retains only those fully
processed before the deadline. Polling waits at most 10ms while a real child is
searching; this is not sleep padding after work completes. An unexpectedly early
backend exit is an explicit failure with logs, not a padded successful run.
At a fleet restart or cutoff the child is terminated, escalated to kill after
0.2s if needed, and reaped in `finally`. No required child is left running.

Python/C++ inference and OS scheduling/cleanup are not hard real-time. Return
latency may exceed the deadline; the selected incumbent's capture time is a
separate check. Inference consuming the entire budget prevents backend launch.
The unchanged ten-second diagnostic return gate is 9.95-10.5 seconds.

Every stage retains `instance.vrp`, `candidates.txt`, `solver.par`, stdout/stderr,
last backend tour and validated captured tour. Candidate arrays are stored in
NPZ. The CLI exports these files beside raw JSON even on failure before deleting
temporary run state. It refuses to overwrite an existing backend-artifact
directory and rejects capped mode, own-GNN checkpoints or implicit assets.

## Verification and Evidence

Tests were written before implementation. They cover source-compatible feature
normalisation, duplicate coordinates/reverse edges, variable fleet candidate
indices and depot bridges, tour completeness, original service/depot conversion,
numeric failures, late validation, inference consuming budget, actual CPU/LKH
execution and seeds, process cleanup, CLI failures/artifact retention and pilot
flag combinations.

An initial one-second collinear toy did not emit a timely incumbent. A missing
real-depot bridge in the first wrapper was reproduced with a failing structural
test, fixed by source comparison, and the real one-second toy then passed.
Demand normalisation was separately checked against the author's `/50` formula
with a failing test before repair. No checkpoint/settings were selected using
evaluation scores. The earlier C101 smoke in
`results/neurolkh_contract_20261018/initial_c101.json` is retained with its earlier
source identity, not silently substituted for final pilot evidence.

Final suite: **217 tests passed in 105.95 seconds**, including the actual
one-second CPU/LKH integration test and all 16 combinations of pilot optional
branches. One expected PyVRP penalty warning is from an intentionally infeasible
toy, not an evaluation run. Ruff and `git diff --check` pass.

All **74/74** frozen evaluation inputs passed integer/feature preflight, with
**zero inference runs and zero instances solved**. Manifest/raw/numeric/geometry
identity checks precede conversion. Evidence:
`results/neurolkh_contract_20261018/preflight.py` and `preflight.json`.

The completed final pilot is
`results/resubmission_pilot_20261018_neurolkh_contract_10s/`.
All **18/18** original-feasible exact covers pass the unchanged ten-second return
gate. Runtimes span 10.001161-10.315846 seconds, with 180.782269 seconds of
aggregate measured solve time. This is not a hard ten-second return guarantee:
OR-Tools C101 returns at 10.315846 and the no-GNN hybrid RC2_4_1 at 10.303817.

| Instance | Branch | Fleet | Original Distance | Return Seconds |
| --- | --- | --- | --- | --- |
| C101 | All six branches | 10 | 828.936867 | 10.001161-10.315846 |
| R1_2_1 | ALNS | 21 | 5334.695369 | 10.006203 |
| R1_2_1 | Hybrid without GNN | 21 | 5566.541900 | 10.047230 |
| R1_2_1 | Hybrid with GNN | 20 | 5721.662843 | 10.009137 |
| R1_2_1 | OR-Tools | 22 | 4929.625350 | 10.003512 |
| R1_2_1 | PyVRP | 21 | 4782.298324 | 10.005178 |
| R1_2_1 | NeuroLKH-adapted | 24 | 5243.007564 | 10.001973 |
| RC2_4_1 | ALNS | 14 | 7099.600863 | 10.003235 |
| RC2_4_1 | Hybrid without GNN | 15 | 7357.954273 | 10.303817 |
| RC2_4_1 | Hybrid with GNN | 17 | 7970.994682 | 10.004468 |
| RC2_4_1 | OR-Tools | 17 | 10007.933974 | 10.041528 |
| RC2_4_1 | PyVRP | 15 | 6267.397322 | 10.020032 |
| RC2_4_1 | NeuroLKH-adapted | 24 | 7405.578751 | 10.002685 |

| NeuroLKH Instance | Features/Inference | Preprocessing Total | Incumbent Capture | Fleet Targets |
| --- | --- | --- | --- | --- |
| C101 | 0.643822 | 0.659523 | 3.078858 | 100, 10 |
| R1_2_1 | 0.284744 | 0.288044 | 9.061205 | 200, 33, 29, 27, 26, 25, 24, 23 |
| RC2_4_1 | 1.747744 | 1.756968 | 7.121241 | 400, 23 |

Timing columns are seconds; capture/preprocessing totals are relative to solve
entry. Every LKH stage was terminated and reaped, with recorded return code -15.
No original-infeasible tour was accepted; the invalid-original-tour count is zero
at all three sizes. Raw data, including worse outcomes, are retained.

The independent `audit_pilot.py` / `audit.json` checks source/model/input hashes,
CPU/thread settings, exact cover, original route feasibility/distance and external
cutoff capture. For NeuroLKH it also verifies the external source/build identity,
strictly decreasing fleet targets, exact stage matrix/demand/service/windows,
actual seed/parameters, candidate dimensions and customer top-four arcs against
stored SGN ranks, selected tour/cost, conservative time-grid feasibility and all
backend artifact hashes. Integrity and operational gates pass.

NeuroLKH's fleet differs from the other nontrivial branches, so its distances
must not be compared directly. The full hybrid has fewer vehicles on R1_2_1 in
this observation, but more than ALNS on RC2_4_1. The pilot does not show a stable
GNN advantage or establish the adaptation as a representative strong baseline.
Earlier pilots have different outcomes even at the same requested seed under
wall-clock limits. No isolated/dedicated-machine, thermal or background-load
control has been established; do not attribute their variation to a particular
cause or pool/cherry-pick favorable pilot results. No settings were retuned from
these observations. A genuine comparison still needs a frozen, randomized/block
run order, broader cutoffs/seeds, compute control and the declared OOD limitations.

Source SHA-256: `529086dfecdf73fed1fd5ea8e1aac6c0a6ee4928d83cce5d54fb62f02e8f5056`.
Own GNN checkpoint SHA-256:
`365de53beba09097d1176a8b102ced8d6d97311f5a3ac82186b116d3290e1b97`.
Preflight SHA-256:
`dcb28e39741c28b153b314c6e2abd902e59cab57d5eaae37507931be995309ae`.
This evidence does not retroactively validate the authors' experiment, the
historical paper results or earlier source snapshots.

## Reproduction

Single run, with a new output path:

```sh
env PYTHONPATH=src NUMBA_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python scripts/benchmark.py \
  --instance data/Solomon/c101.txt --ablation neurolkh \
  --neurolkh-root results/external/NeuroLKH \
  --seed 42 --time-limit 10 --output-json results/new_neurolkh_run.json
```

Pilot: `--neurolkh-root PATH` adds three adapted-NeuroLKH runs to the runner.
With own GNN, OR-Tools and PyVRP enabled, that is 18 runs, six branches on
100/200/400 customers, with sequential one-thread cold starts.

Completed command, retained for provenance; repeat with a new output directory:

```sh
env PYTHONPATH=src .venv/bin/python scripts/run_benchmark_pilot.py \
  --output-dir results/resubmission_pilot_20261018_neurolkh_contract_10s \
  --time-limit 10 --seed 42 \
  --gnn-model results/gnn_retraining_20261017/model_seed42/best.pt \
  --include-ortools --include-pyvrp --neurolkh-root results/external/NeuroLKH
```
