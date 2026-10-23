# Native supervisor: longer-cutoff preflight (2026-10-20)

## Specification before implementation/execution

Test the existing opt-in native supervisor at longer cutoffs and a second search
seed. This is a bounded operational preflight toward an executable equal-compute
sweep, not the publication sweep or a parameter-selection experiment. No solver,
model, search allocation, acceptance rule or timing tolerance changes are planned.
Keep all earlier successful/failed results and the eight-job launcher's bytes.

Declare fourteen independent jobs before observing any new outcome:

- At 60 seconds: c101 (100), R1_2_1 (200), RC2_4_1 (400), each with ALNS and
  F111111 at search seeds 42 and 43 (twelve jobs).
- At 300 seconds: RC2_4_1 with ALNS and F111111 at seed 43 (two jobs).
- Total nominal solve budget: 1,320 seconds (22 minutes), plus setup and audits.
  The 300-second check covers one input/seed; 900 seconds remains untested.

Shuffle the seven input/seed/cutoff blocks using order seed 20261020, then use
alternating ALNS/Full order. Persist the exact schedule, commands and requested,
effective and nested configs before the first child. The two cases occupy each
position either three or four times. Seed 43 does not change PYTHONHASHSEED=42.
Use the same validation-selected GNN, SHA-256
365de53beba09097d1176a8b102ced8d6d97311f5a3ac82186b116d3290e1b97;
GNN-off ALNS receives no checkpoint. No score-based retries or exclusions.

Each worker starts in a fresh interpreter with initially empty exclusive cwd and
NUMBA_CACHE_DIR, JIT enabled, no warmup or shared archives, and the existing
one-thread requests. Setup/model loading remain separate; shared solve timing
includes dispatch, search, IPC, original-space validation and termination/reaping.
Record full CLI child wall/CPU and setup evidence. Preserve pending files.

Certification requires worker capture, parent receipt and complete parent
validation/hash strictly before T. Return timing remains [T-0.05,T+0.5], including
cleanup; no padding, reserve tuning, compile subtraction or hard-real-time claim.
Reopen every observed packet and independently check admitted original-space
routes, hashes, clock/session, fleet-first order, final selection and trajectory.
Check source/input/model identities, seed/budget, requested/effective/nested
configuration, cold entry and reaping separately. Missing final counters remain
null; packet counters are partial observations, never final totals or causal
learning-effect evidence. Export their scope explicitly for activity coverage.

Retain ordinary no-incumbent/return failures and continue. Abort further jobs on
source/input/model/config/cold/clock integrity drift, protocol errors or failed
cleanup. Do not silently change source mid-experiment. An outer watchdog allows
T+180 seconds for CLI setup/solve/export, then sends SIGINT to the owned CLI so
its supervisor finally block can reap its worker. Do not blindly SIGKILL the CLI
or signal a PID reconstructed from stale disk metadata. A stuck CLI after the
grace period is explicit failure requiring attention; it is not a successful row.

## Harness test plan

Before changing the reusable pilot harness, reproduce Red for variable seed/T
binding, fixed absolute return slack, strict certification cutoff and watchdog
timeout/cleanup. Use preserved result fixtures or mocks, never real native solves
inside negative CLI tests. Check exact schedule/cardinality, immutable outputs,
command/config propagation and audit rejection of tampered evidence. Preserve
Red/Green logs, before/after source, prior seals and all old golden hashes.

The new harness is derived from the sealed eight-job launcher; it must not edit
that launcher or import solver state from an earlier process. Runtime source
bytes under src/ and the existing worker/CLI stay unchanged. Source identity may
change because of the new harness; record that distinction explicitly.

External comparator clock/certification/cleanup equivalence and an executable
full-sweep/statistics pipeline remain separate work. Passing these fourteen jobs
does not alone establish readiness for a four-solver publication comparison.

## Implementation and completed preflight

The new launcher is `scripts/run_supervisor_pilot.py`, derived from the sealed
eight-job launcher without changing its bytes. The 34 new tests first produced
24 missing-module errors; after the initial implementation, ten additional Red
cases exposed missing packet-clock, metadata-identity, trajectory-objective,
predeclared-command and counter-scope checks. All 34 pass after repair.
The full suite passes **695 tests in 112.45s**, including both unchanged golden
fingerprints, with the existing PyVRP infeasible-fixture warning. Ruff, formatting
and whitespace checks pass. No existing runtime, worker, CLI or test file changed.

All fourteen jobs ran once under source SHA-256
`1c3f44b29a7d71fd494642dbe7df43159e8af4fb64cd41a8fedc0ecd366e66a2`.
This differs from the eight-job source because of the added launcher; all prior
source files are unchanged. The schedule, full configs and every command were
persisted before the first child. The frozen protocol and source/test snapshot
are retained alongside the results in `results/supervisor_long_pilot_20261020/`.

Certification, shared clock, provenance, config binding, cold/cache entry,
cleanup and the unchanged return gate each pass **14/14**. Reopening the evidence
reproduces all gates and CSV activity fields. The independent audit checks **544
admitted packets**, including original-coordinate feasibility/objective checks,
packet/route hashes, certificate flags, receipt/validation timing and fleet-first
trajectory/selection. No result was retried or replaced.

| Cutoff | Jobs | Solve return including cleanup | Latest parent admission |
| --- | ---: | ---: | ---: |
| 60s | 12 | 60.019513–60.078652s | 59.980266s |
| 300s | 2 | 300.040503–300.076937s | 267.179927s |

Numeric sources: `results/supervisor_long_pilot_20261020/summary.csv` and
`results/supervisor_long_validation_20261020/admissions.csv`. Every selected
worker snapshot and parent validation completes strictly before its own cutoff.
The two 300-second jobs use only RC2_4_1/seed43, so they do not establish broader
300-second seed/instance robustness. No 900-second job ran.

All workers were terminated and reaped at cutoff; none required SIGKILL.
Cleanup spans 0.019011–0.076268s. Full CLI child wall time sums to 1,445.899259s,
and recorded child CPU to 1,548.849283s, against 1,320 nominal solve seconds.
Setup/model loading remain separately reported. CPU and wall totals do not
establish isolated hardware or actual one-thread execution for every backend.
Resource source: `results/supervisor_long_validation_20261020/resource_audit.csv`.

Complete final worker counters are unavailable in all fourteen rows and remain
null. Last-admitted checkpoints from the seven Full jobs report positive micro
training counters in 7/7, macro training counters in 2/7, LAC query counters in
2/7 and HiGHS call counters in 5/7. These are partial observations; zero at a
checkpoint does not establish zero activity later. The counter names retain the
existing instrumentation's meaning, and these counts do not demonstrate learning
effectiveness, convergence or component causality. No objective ranking or
statistical significance is inferred from this operational pilot.

The sealed pilot manifest covers 1,121 files. Validation artifacts, Red/Green
logs, preservation inventory, exact source snapshots and the separate post-run
analysis are in `results/supervisor_long_validation_20261020/`.

## Concrete next step toward the sweep

The native 60/300-second preflight is complete. Next, bind PyVRP and adapted
NeuroLKH to the same parent start/cutoff and original-space incumbent publication,
validation and cleanup budget. Their existing adapters currently start private
solve clocks and do not publish through this supervisor. NeuroLKH also owns an
LKH subprocess: descendant termination/reaping and CPU evidence need explicit
tests before treating its execution as equivalent to native supervision.

Keep the selected model and solver settings fixed. After that integration, bind
the declared sweep jobs to executable configs, implement/test the prespecified
analysis, and freeze the launch manifest and compute policy. The old planning
artifact's `launch_ready=false` is not rewritten by this pilot. No full sweep,
manuscript edit, retraining or historical-result replacement ran.
