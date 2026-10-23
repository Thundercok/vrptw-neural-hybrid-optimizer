# First frozen block: execution and resume — 2026-10-20

Completed the first four jobs of the frozen manifest, then audited them using
an absolute run-directory path. All four commits retain valid source/config,
independent cold-start, original-space certification, clock, return and cleanup
evidence. No solver source, setting, checkpoint, old result or manuscript changed.
The full sweep has **4/8,620** jobs committed; no further jobs were dispatched.

## Scope fixed before execution

The stage plan is
[stage_plan.json](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/results/sweep_executor_first_block_20261020/stage_plan.json).
It declares exactly the first frozen block: C202, seed 42, separate ten-second
cold starts for NeuroLKH-adapted, F111111, PyVRP-ILS and ALNS-Base, in that order.
The nominal solve budget is 40 seconds. This is a bounded executor validation;
baseline representativeness, integer precision/adaptation scope and the full
compute allocation are not settled by its outcomes.

The first invocation used `--max-jobs 1`. Before resuming, all 44 files of that
committed job were hashed. The second invocation used `--max-jobs 3`: it skipped
the first commit and dispatched exactly the next three jobs. The original 44
files remain byte-identical after resume and subsequent audits. No retry,
replacement, warming, parameter adjustment or score-based selection occurred.

## Recorded results

All measured values below come from
[records.csv](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/results/sweep_executor_first_block_20261020/records.csv)
and
[cleanup.csv](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/results/sweep_executor_first_block_20261020/cleanup.csv).

| Case | Return seconds | Selected capture seconds | Integrity / availability / binding / return |
| --- | ---: | ---: | --- |
| NeuroLKH-adapted | 10.127058 | 1.744935 | All pass |
| F111111 | 10.019132 | 3.118329 | All pass |
| PyVRP-ILS | 10.018816 | 0.590172 | All pass |
| ALNS-Base | 10.009177 | 2.390491 | All pass |

Every selected incumbent was independently validated before ten seconds; every
return lies in the unchanged [9.95, 10.5]-second gate. All four happen to have
NV=3 and original TD=591.5565566715014 in this block. This single instance/seed
does not establish superiority, generalization or significance. No aggregate
statistical inference was run on the incomplete matrix.

Complete CLI child wall time sums to 65.560125 seconds, with 64.079035 seconds
of reaped child CPU; setup and cleanup explain why this is distinct from the
40-second nominal solve budget. These measurements do not establish dedicated
host isolation or exact internal backend thread counts.

All four workers were reaped. NeuroLKH's worker required parent SIGKILL after
the grace period; its two owned LKH children had already been terminated and
reaped, neither requiring SIGKILL. The other three workers ended on SIGTERM.
Final worker counters are available for one run only; unavailable counters were
not invented. These outcomes do not establish hard real-time return guarantees.

## Auditor path issue and verified workaround

The first post-resume command used the documented relative `--run-dir`. It
failed with `immutable artifact differs: completed.json`. That failed audit is
preserved in
[audit.log](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/results/sweep_executor_first_block_20261020/audit.log).

The frozen `audit()` entry point does not normalize its path as `run()` does.
Consequently, cold-start validation compares a relative expected worker cwd
with the recorded absolute cwd and reports `worker entry drift`. Recomputing
the first record with a relative path changes only `integrity_ok` and this
diagnostic; using its absolute path exactly matches the immutable commit.
The evidence files themselves are unchanged. The diagnostic comparison is in
[audit_path_diagnostic.json](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/results/sweep_executor_first_block_20261020/audit_path_diagnostic.json).

Using an absolute `--run-dir` then successfully re-audited all four commits,
including route packets, file hashes and cleanup evidence. No benchmark was
rerun to obtain this pass. The failed invocation and successful absolute-path
invocation remain separate. The analysis CLI already normalizes its run path.
An actual call with the partial four-job matrix and a relative run path reached
the expected `full declared matrix is incomplete` guard, created no analysis
output and launched no solver. Its failed analysis log is preserved separately.

**Known launcher limitation:** use absolute run paths for audit. The source was
kept frozen to preserve this manifest's identity; a code repair should receive
its own Red/Green test and source version, rather than patching this experiment
in place or rewriting its hashes. Do not delete or alter the four commits.

## Preservation and continuation

All **5,675 protected files** are byte-identical, including the previous
validation's sealed evidence, the prepared artifact, source/tests, input/model
copies, historical results and goldens. The tracked diff is byte-identical.
All four new jobs have verified immutable file manifests and commit/receipt
hashes. Source is unchanged, so this stage did not repeat the previous 777-test
suite or relabel its historical test pass as a new run.

```text
source_sha256   a55b90f6fff53d6708b9d8152b84a60d645033242a09b34ae50b21433ec4c70d
manifest_sha256 0803c6c7200af6dba84d96bdb0edd266636949db2552f1d8b69b2c907ec2011a
```

Evidence, preservation hashes and the numeric summary are in
[sweep_executor_first_block_20261020](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/results/sweep_executor_first_block_20261020).

The following audit command is verified and launches no solver:

```sh
cd /Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization
.venv/bin/python scripts/run_sweep.py audit --run-dir /Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/results/sweep_execution_20261020
```

The next declared job is `00004_C105_F111111_s46_t10`. A subsequent execution
stage can resume from that job without replacing the existing four. Keep the
source/environment/assets fixed, preserve failures, use absolute audit paths,
and retain the unresolved publication-comparison limits. This stage did not
start an unattended full sweep or edit manuscript claims.
