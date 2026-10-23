# Sweep executor and statistical analysis validation — 2026-10-20

Implemented the sequential, resumable executor and the prespecified statistical
pipeline. Prepared the executable manifest; **no full-sweep job was launched**.
The manuscript, solver implementations, checkpoints, old results and goldens
were not changed.

The pre-implementation contract is
[sweep_execution_20261020.md](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/docs/sweep_execution_20261020.md).

## Prepared artifact

[plan.json](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/results/sweep_execution_20261020/plan.json)
binds 8,620 physical jobs, 74 inputs (56/12/6 at 100/200/400 customers), seeds
42–46, the four main cutoffs, and the registered 18-input ablation. The original
order and 180 shared main/ablation executions match the preserved design exactly.
The analysis matrix and execution matrix have identical keys.

There are 1,100 content-addressed requested/effective/nested configuration
bindings. The 1,189 prepared files are sealed by `prepared_hashes.json`; the
manifest also binds input copies, completed GNN training/checkpoint, source and
tests, protocol, hardware/packages, and external backend identities. Audit found
zero completed jobs and no job directories. Automatic launch remains disabled;
the historical design's `launch_ready=false` is preserved.

The nominal solve allocation is 2,365,600 seconds, or **657.111111 hours**.
Interpreter startup, audit, I/O and cleanup add overhead; this is not an ETA.
Engineering tests do not establish baseline precision/representativeness or
allocate this compute. Environment requests one thread; this does not establish
actual thread counts inside every backend.

```text
source_sha256   a55b90f6fff53d6708b9d8152b84a60d645033242a09b34ae50b21433ec4c70d
manifest_sha256 0803c6c7200af6dba84d96bdb0edd266636949db2552f1d8b69b2c907ec2011a
```

## Execution and recovery

[run_sweep.py](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/scripts/run_sweep.py)
uses an exclusive kernel lock and writes launch intent before starting an owned
CLI session. It records CLI reaping/resources, independently audits the common
supervisor evidence, seals job files, and publishes the immutable commit last.
CSV and status are derived views.

Resume revalidates and skips existing commits, including ordinary no-solution
and return-gate failures. A complete receipt left before a crash can be committed
without rerunning the solver. An ambiguous intent, altered evidence, protocol
drift, failed cleanup or out-of-order artifact stops subsequent dispatch. It does
not automatically retry or convert an executor exception into a solver loss.
Ctrl-C requests a stop after the current job commits. The owned CLI watchdog
requests its supervisor cleanup; resume never signals PIDs read from disk.

Known no-solution rows can enter the availability denominator only when request,
source, cold-start, clock and cleanup checks pass. Missing effective binding
evidence remains false/unverified. Requested config drift is rejected even when
no checkpoint exists. A certified pre-cutoff incumbent and its return-latency
gate remain separate endpoints; late-return counts remain visible.

## Statistical outputs

[analyze_sweep.py](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/scripts/analyze_sweep.py)
requires the complete, audited declared matrix before creating analysis output.
It rejects duplicate, missing, undeclared or protocol-invalid cells. It implements
paired feasibility/fleet scores, descriptive complete-five-seed mean-NV W/T/L,
seed-level variability, conditional same-seed/same-fleet TD gaps and the raw-NV
heuristic/learning bundle interaction.

All 46 analyses reuse the same 10,000 seed/geometry draws. Size weights remain
fixed; unequal geometry-group sizes and resampling multiplicity are retained.
TD intervals are suppressed if a required stratum or matched denominator is
undefined. The three main and eight ablation comparisons at 300 seconds use
separate Bonferroni percentile families **per metric**, not joint control across
all endpoints. Other cutoffs/contrasts are descriptive or exploratory. With only
four geometry groups per size and five seeds, these are approximate intervals;
no coverage/power, unconditional TD or global-optimality claim is made.

The analysis saves records, draws, seed summaries, point estimates, every
bootstrap replicate and interval CSVs. It reopens the replicate CSV to derive
intervals and reopens the numeric CSVs to construct the report, then seals the
output. The fixture flag is explicit; synthetic records are not solver results.

## Validation and preservation

- **777 passed in 110.34 seconds**, including 48 new tests. The single PyVRP
  penalty-bound warning comes from the existing infeasible fixture.
- Ruff check passed; all six new Python files pass format checking.
- TDD retained missing-module/script Red logs and regression Reds for a zero TD
  denominator, altered self-hashed job declaration, null success error and
  missing-checkpoint request drift. Executor tests cover resume, collision,
  evidence tamper, ordinary failures, protocol stops, source drift after dispatch,
  locking, Ctrl-C and the owned CLI watchdog. Preparation tests forbid real
  solver calls and bind the complete 8,620-job schedule.
- Reopened all **16 preserved comparator pilot results** using the new auditor;
  all retained availability, integrity, binding and return gates. This is an
  evidence replay under the original pilot source identity, not new runs.
- Explicit synthetic validation used **8,620 cells**, **46 analyses**, **10,000
  draws**, **460,000 replicate CSV rows**, and independently replayed all **134
  intervals** with NumPy quantiles/undefined-denominator checks. Scalar-loop
  unit references also verify fleet and conditional TD resampling.
- The real prepared artifact passed audit with **0/8,620** completed jobs.
  The analysis CLI refused it before creating output because the matrix is
  incomplete. No new operational benchmark solve was made in this stage.
- **4,418/4,418** protected pre-implementation files are byte-identical. All **20** prior artifact
  manifests validate, covering **3,620** sealed entries. The existing tracked
  diff is byte-identical; both golden hashes are unchanged.

Validation artifacts are in
[sweep_execution_validation_20261020](/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization/results/sweep_execution_validation_20261020).
Two validation-helper errors are retained in its first logs: the replay initially
looked for legacy `records.csv` instead of `summary.csv`, and its independent
NumPy assertion accidentally passed a diagnostic dict as `rtol`. The corrected
read-only `--verify-existing` check verified the already-recorded files without
regenerating or altering them. These errors did not change executor/statistics
code or old results.

## Commands for the next execution stage

Run from the project directory shown below. These commands are instructions;
the `run` commands have **not** been executed in this stage. Keep the frozen
source, tests, environment, inputs, models and prepared artifact unchanged.

```sh
cd /Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization

# Inspect/audit without solving.
.venv/bin/python scripts/run_sweep.py status --run-dir results/sweep_execution_20261020
.venv/bin/python scripts/run_sweep.py audit --run-dir results/sweep_execution_20261020

# Explicitly run or resume the same manifest; no automatic retries.
.venv/bin/python scripts/run_sweep.py run --run-dir results/sweep_execution_20261020

# Optional bounded execution: dispatch at most N new jobs in frozen order.
# Existing completed jobs do not count against --max-jobs.
.venv/bin/python scripts/run_sweep.py run --run-dir results/sweep_execution_20261020 --max-jobs 1

# After every declared job is complete, audit and analyze into a NEW directory.
.venv/bin/python scripts/run_sweep.py audit --run-dir results/sweep_execution_20261020 --require-complete
.venv/bin/python scripts/analyze_sweep.py --run-dir results/sweep_execution_20261020 --output-dir results/sweep_analysis_20261020
```

If recovery reports an ambiguous intent or protocol failure, preserve its files
and investigate; do not delete the intent, edit a commit, or create a replacement
job to improve the observed score. The next scientific execution stage still
needs an explicit choice of compute and baseline-comparison scope.
