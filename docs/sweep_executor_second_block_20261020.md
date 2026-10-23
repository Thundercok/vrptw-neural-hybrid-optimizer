# Second frozen block — 2026-10-20

Completed C105, seed 46, at ten seconds for F111111, PyVRP-ILS, ALNS-Base and
NeuroLKH-adapted, in the exact frozen order. The manifest now has **8/8,620**
committed jobs. Four new jobs were dispatched; the first four were revalidated
and skipped. No source, setting, model, old result or manuscript changed.

The pre-execution
[stage_plan.json](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/results/sweep_executor_second_block_20261020/stage_plan.json)
limits this stage to four cold starts and 40 nominal solve seconds. There were
no retries, warmups, score-based exclusions or changes to the return gate.
Actual worker requests use search seed **46**, while Python hash seed remains
**42**, as registered. Every new job passes integrity, availability, effective
binding and the unchanged [9.95, 10.5]-second return gate.

Measured values come from
[block_records.csv](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/results/sweep_executor_second_block_20261020/block_records.csv)
and
[cleanup.csv](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/results/sweep_executor_second_block_20261020/cleanup.csv).

| Case | Return seconds | Selected capture seconds |
| --- | ---: | ---: |
| F111111 | 10.019266 | 2.715135 |
| PyVRP-ILS | 10.009497 | 0.388752 |
| ALNS-Base | 10.009285 | 2.302147 |
| NeuroLKH-adapted | 10.125442 | 0.602473 |

All four independently validated incumbents were captured before the cutoff.
All have NV=10 and original TD=828.936866942834 in this block. This is one
instance/seed/cutoff observation, not a ranking or significance result. The
incomplete 74-instance matrix was not used for aggregate statistical inference.

Complete child wall time totals 65.096158 seconds and reaped child CPU totals
65.868886 seconds, including setup and cleanup. These are distinct from the
nominal solve allocation and do not establish exact backend thread counts or
dedicated host isolation.

All four workers were reaped. NeuroLKH's worker required SIGKILL after its grace
period, after both owned LKH children were already terminated and reaped. Neither
LKH child required SIGKILL. Final worker counters exist for one run only; absent
counters remain unavailable. No hard real-time guarantee follows.

The absolute-path audit succeeded for **all eight commits**, including the
original-space packet/certificate, identity, cold-start and cleanup checks.
Use absolute audit paths because the frozen launcher's relative-path issue
remains as documented in the
[first-block report](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/docs/sweep_executor_first_block_20261020.md).
No repair was applied to frozen source or recorded hashes.

All **5,857 protected files** are unchanged, including the first block's 156
job files, historical results, prepared input/model/config/source/test snapshots,
prior validation evidence and both goldens. The old four-row CSV is an unchanged
byte prefix of the current eight-row CSV. The tracked diff is byte-identical.
No code changed, so the historical 777-test pass was not rerun or relabelled as
new validation.

```text
source_sha256   a55b90f6fff53d6708b9d8152b84a60d645033242a09b34ae50b21433ec4c70d
manifest_sha256 0803c6c7200af6dba84d96bdb0edd266636949db2552f1d8b69b2c907ec2011a
```

Stage evidence, numeric summary and preservation hashes:
[sweep_executor_second_block_20261020](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/results/sweep_executor_second_block_20261020).

The next frozen block is **R2_2_5, seed 43**, with PyVRP-ILS, ALNS-Base,
NeuroLKH-adapted and F111111 at **900 seconds each**: **3,600 nominal solve
seconds**, plus setup/audit/cleanup overhead. It was not started in this stage.
Baseline precision/adaptation/representativeness limits remain open; this
bounded execution does not settle the publication-comparison scope or start an
unattended full sweep.
