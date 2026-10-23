# Deadline Repair and GNN Integration

Status: cooperative-deadline regressions fixed; new-checkpoint three-scale,
ten-second integration pilot passed on 2026-10-17. This does not establish a
hard real-time guarantee, comparative solver superiority, or readiness for the
74-instance publication sweep. Historical results and training labels are intact.

## Diagnosis Before Editing

All measurements are preserved in `results/deadline_profile_20261017/`.
The profiler wraps existing calls without modifying solver source. Inclusive
times overlap; instrumentation and wall-clock search can change the search path.
No timing or solution-quality claim is inferred from differences between runs.

The exact old 0.542809-second hybrid overrun and 0.576862-second ALNS label overrun
were not reproduced during diagnosis. The measurements did expose real defects:

- ALNS destroy started at 9.949779 seconds, finished at 10.001928, and was followed
  by a repair starting at 10.001945. There was no intervening deadline check.
- One hybrid local search in fixed-NV polish ran from 8.925604 to 10.081710 seconds.
  Its total duration is not proof that one atomic kernel took 1.16 seconds.
- Deeper profiling found individual Or-Opt scans up to 0.251700 seconds and
  repeated Neural Shaw destroy calls of 0.273114 to 0.485264 seconds.
- Deterministic fake-clock tests demonstrated acceptance of late candidates,
  eager merge seeding after expiry, and starting a neighborhood after cache
  construction had consumed the remaining time.

| Profile Artifact Stem | Source | Solve Time (Seconds) |
| --- | --- | --- |
| `alns_before` | Training snapshot | 10.005844 |
| `hybrid_before` | Training snapshot, recovered model | 10.084649 |
| `hybrid_neighborhoods_before` | Training snapshot, recovered model | 10.007757 |
| `hybrid_operators_before` | Training snapshot, recovered model | 10.015280 |
| `alns_after` | Patched source | 10.002885 |
| `hybrid_after` | Patched source, same recovered model | 10.003800 |

Every stem has raw `.json` and `_profile.json` records. Exact instrument versions
are preserved as `profile_solver_v1.py`, `profile_solver_v2.py` and
`profile_solver_v3.py`; their hashes match the profile metadata. The formatted
`profile_solver.py` is retained for future diagnostics.

## Scoped Changes

- ALNS now checks between destroy and repair and rejects a repair completed late.
- Hybrid main search, pool seeding, committed search and fixed-NV polish forward
  the deadline to repair and stop on cancellation. Fixed-NV polish does not start
  another local search after expiry or promote a late result.
- Shaw/Neural Shaw check the deadline between removal steps. Repair operators
  accept an optional deadline and return `None` on cancellation; partially repaired
  private candidates cannot escape as solutions. Default calls still return plans.
- Or-Opt checks between route-pair kernels. Intra-route polish checks between
  passes/routes; merge/compaction checks between insertions. Local and inter-route
  search reject neighborhood results completed late, including after cache setup.
- No artificial sleep, wider tolerance, changed GNN threshold, changed model
  weights, or replacement of old CSVs/labels was used to obtain a pass.

Tests were added before solver edits. Final verification: **145 tests passed in
88.15 seconds**, Ruff and `git diff --check` clean. Coverage includes mid-repair
cancellation, exact customer coverage, no-expiry behavior, operator-stage guards,
late move rejection, cache expiry and merge-helper expiry.

## New-Checkpoint Pilot

Artifacts: `results/resubmission_pilot_20261017_retrained_gnn_deadline_10s/`.
There are nine sequential, fresh-process cold starts: seed 42, one Torch thread,
nominal ten-second `solve()` budgets. Model loading/imports are excluded from
that timer and recorded separately by the existing runner.

All nine returned feasible exact covers and passed the **unchanged** diagnostic
range of 9.95 to 10.5 seconds. The independent `audit_pilot.py` validated source
snapshot contents, model/input hashes, component flags, full coverage, feasibility,
fleet counts and travel distances recomputed from saved routes. `audit.json`
records its checks and artifact hashes.

| Instance | Branch | Fleet | Distance | Solve Seconds |
| --- | --- | --- | --- | --- |
| C101 | ALNS | 10 | 828.936867 | 10.003585 |
| C101 | Hybrid without GNN | 10 | 828.936867 | 10.000746 |
| C101 | Hybrid with new GNN | 10 | 828.936867 | 10.000538 |
| R1_2_1 | ALNS | 20 | 5383.628579 | 10.003103 |
| R1_2_1 | Hybrid without GNN | 20 | 4937.020304 | 10.000837 |
| R1_2_1 | Hybrid with new GNN | 20 | 5721.662843 | 10.036825 |
| RC2_4_1 | ALNS | 14 | 6846.359703 | 10.002935 |
| RC2_4_1 | Hybrid without GNN | 14 | 7472.436107 | 10.009666 |
| RC2_4_1 | Hybrid with new GNN | 14 | 7247.371560 | 10.004636 |

These are operational observations, not a performance experiment. The new GNN
does not dominate these observations: its distance is worse than no-GNN hybrid
on R1_2_1 and worse than ALNS on RC2_4_1 at matched fleets. Weights, thresholds and
settings were not reselected based on these benchmark outcomes.

## Frozen Identities

- Teacher/trainer source: `948698b77671d6bbff31763f626f437e9594b64d948c545f14082d2974da437a`.
- Patched pilot source: `1ca71b1075777677240a533eed2207adda76c6ddf85f28bb40f43ee0bfbde956`.
- Validation-selected checkpoint: `365de53beba09097d1176a8b102ced8d6d97311f5a3ac82186b116d3290e1b97`.

The dataset/model training snapshots remain at their original source version.
The integration pilot has its own source snapshot and checkpoint copy. Training
audit/target generation deliberately reject a changed source: use the frozen
training snapshot for historical rechecking; never rewrite its hash to match the
patched solver. The old checkpoint and original dataset manifest hashes are unchanged.

## Remaining Gates

Non-preemptible kernels, initialization, external solver calls and OS scheduling
can still cross a deadline. Other tail heuristics and all instances/cutoffs/seeds
have not been exhaustively validated. Passing a 0.5-second diagnostic tolerance
does not mean every return meets a strict ten-second publication cutoff.

Before publication runs: freeze an explicit late-return/incumbent cutoff policy,
broaden timing coverage, reproduce independent classical and learning-augmented
baselines, validate ablations and approve the full compute budget. The original
timing failures remain failures in their original artifacts. No manuscript edits
or full publication sweep were performed.
