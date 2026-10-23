# Native supervisor contract (2026-10-20)

## Specification before code changes

Provide a separate opt-in native supervisor CLI for ALNS and the factor-bound
hybrid cases. Keep the existing benchmark CLI, default native search, parameters,
frozen model and all historical results unchanged. No full sweep, manuscript
edit, retraining, warmup, padding, compile-cost subtraction or time-reserve tuning.
This is a different execution protocol and cannot replace prior observations.

Use a fresh subprocess/interpreter (no forked solver state), initially empty
exclusive work and NUMBA_CACHE_DIR directories, JIT enabled, hash seed 42 and
one-thread environment requests. Keep stdout/stderr, request, ready/start/ack,
immutable incumbent packets, completion if available and resource evidence.
Do not delete a killed worker's incomplete temporary files or claim that a
partially written packet was delivered. Preserve artifacts in the requested
new session directory, refusing an existing directory/output.

Imports, input loading, constructor and explicit frozen-model loading occur in
setup, as in the prior CLI. They and whole-process CPU/wall time are reported
separately. There is no JIT warmup. Ready must bind source, input, model, seed,
case, full requested config and observed cold state. Identity drift fails closed.

After validating ready, the supervisor samples one system-wide perf_counter
start and cutoff=start+T. Writing/reading the start message, worker dispatch,
native construction/inference/search/tail, IPC, supervisor validation and worker
termination/reaping all count in the reported solve return interval. Inject the
same NativeIncumbent clock/start/deadline into ALNS/hybrid; do not give the child
a fresh T seconds when it reads start. The worker acknowledges its observed
clock, bracketed by the parent's start/receipt. Reject nonfinite, reversed,
foreign-session or incompatible clock metadata. No hard-real-time claim.

Add an optional NativeIncumbent observer, invoked only after a complete valid
fleet-first promotion. Send owned copies of routes/certificate; observer changes
cannot mutate native evidence. Default None preserves existing behavior. The
observer's serialization and publication costs remain in the solve budget;
capture-before-cutoff does not imply delivery-before-cutoff.

Publish JSON via a closed temporary file and atomic rename on the same local
filesystem, using monotonic sequence numbers in a fresh session. Supervisor
polling is only protocol waiting, not artificial padding. Ignore pending files.
Parent receipt, copying, exact cover, capacity/service/time windows/depot return,
original double-precision distance and route-hash checks must all finish strictly
before cutoff. Match the worker certificate to recomputed routes/objective,
shared clock and session. Reject malformed/inconsistent evidence explicitly.
Discard late delivery/validation and retain the last previously admitted
incumbent; never promote from completion metadata or post-cutoff disk replay.

Admit improvements lexicographically by fleet then distance, with the same
native 1e-6 distance improvement threshold. Final certificate captured_sec is
parent validation completion; retain worker_captured_sec and receipt_sec as
separate fields. Record each admission/rejection and packet hash. If no parent-
certified incumbent exists, return an explicit no-solution error. A worker exit,
protocol error or cleanup failure must remain visible; no fabricated success.

At cutoff, terminate the owned worker process group, escalating to kill after
0.1s and waiting at most another 0.1s. Include actual cleanup duration in return
timing; report any unreaped worker as failure. Native scope has no spawned
solver subprocesses; backend thread counts are not established by environment
requests. Record parent CPU, reaped worker CPU and end-to-end wall time. OS
scheduling may still violate the unchanged [T-0.05,T+0.5] operational gate.

Report complete worker counters only when a valid completion record exists.
Otherwise final counters are null/unknown; a packet checkpoint is explicitly
partial. Keep requested/effective/nested configs and observed counters at the
checkpoint. Do not infer final training, LAC, SP or iteration activity from it.
External comparator adapters and publication launch are outside this stage;
equivalent supervisor/validation/cleanup budgets must be specified before any
cross-solver publication comparison.

## TDD and validation plan

- Fake-clock unit tests: observer ownership/default behavior; shared ALNS/hybrid
  origin; exact boundary/future/wrong-clock/identity/hash/objective/feasibility
  rejection; validation/hash crossing cutoff; immutable fleet-first fallback.
- Real process tests with a stdlib fixture: certified packet then blocked worker,
  SIGTERM-resistant worker requiring kill, no incumbent, malformed/incomplete
  message, early exit and setup failure. Assert worker reaping, timing/resource
  recording and fresh entry work/cache. These fixtures are protocol tests,
  not solver-quality or actual JIT timing evidence.
- CLI/worker contract tests for explicit opt-in, supported native cases,
  collision refusal and full config/identity/metadata binding. Preserve Red and
  Green logs, before/after snapshots, old golden hashes, Ruff/format/whitespace
  checks and the full regression suite.

Freeze a separate operational pilot specification only after implementation
and tests pass. Do not silently repeat previous diagnostic cells or claim a
passing operational gate from synthetic fixtures.

Python's documented [system-wide perf_counter](https://docs.python.org/3.12/library/time.html#time.perf_counter),
[atomic rename](https://docs.python.org/3.12/library/os.html#os.replace) and
[subprocess termination](https://docs.python.org/3.12/library/subprocess.html#subprocess.Popen.terminate)
are the underlying facilities; none supplies unconditional scheduling bounds.

## Declared operational pilot before execution

After the full suite and old golden fingerprints pass, freeze eight independent
seed-42, ten-second jobs in this exact order (80 nominal solve seconds):

1. R1_2_1 / F101111
2. R1_2_1 / F111111
3. R1_2_1 / F000000
4. c101 / F000000
5. c101 / F111011
6. c101 / ALNS
7. RC2_4_1 / F111111
8. RC2_4_1 / ALNS

The first five retain the preceding confirmation's failed cells/configs; the
three additions exercise the ALNS path and 400-customer coverage under the new
protocol. This is not a paired speed/quality comparison with the old solver.solve
measurement scope. Source/tests/launcher/protocol, three inputs and the unchanged
validation-selected GNN checkpoint are sealed before launch. Checkpoint SHA-256:
365de53beba09097d1176a8b102ced8d6d97311f5a3ac82186b116d3290e1b97.
GNN-off cases receive no checkpoint. Every worker has a fresh process, empty
work/cache directories and the same thread/JIT/hash-seed policy. No phase trace,
cProfile, warmup, adaptive retry, tuning or score-based exclusion.

Persist each CLI command/output, worker protocol and immutable packet files,
checkpoint counters, final counters if available, CPU/wall measurements, routes,
certificates and gates to CSV. Independently reopen all admitted packets and
selected routes in original space, match their observed receipt/validation times
and hashes, check fleet-first ordering and requested/effective/nested configs.
Preserve missing-incumbent and timing failures and continue; source/model/input,
config, cold/clock identity drift aborts. Keep the unchanged [9.95,10.5] return
gate, with worker reaping and actual cleanup included. Reopen and seal all
evidence after the last job. No automatic publication/sweep launch follows.

## Pre-pilot development caveat

One ancestor-path negative CLI test initially lacked a supervisor stub. Before
the missing path guard was repaired, it started a real ALNS worker and then
failed writing its result because the requested result path had become the
session's parent directory. The test/session is preserved separately under
results/supervisor_validation_20261020/unplanned_cli_path_fixture/ with a source
snapshot and incident record. No completed result/return timing/independent
cleanup record was exported, so this is an unplanned failed integration fixture,
not one of the eight declared jobs or eligible operational evidence. It is not
rerun or used to choose parameters. Negative CLI tests now stub supervision;
the isolated regression fails before the path-guard repair and passes after it.

## Preflight completed before declared pilot

The full suite passes **661 tests in 118.19s**, including both unchanged golden
files/fingerprints; one existing PyVRP infeasible-fixture warning remains. There
are 59 new tests. The final targeted group passes 195 tests. Initial Red had
36 failures; two clock-test fixtures first needed per_beta_auto_scale=False
with zero iterations. Replaying the corrected fixtures against the archived
ALNS API and existing hybrid deadline resolution reproduced both real failures.
Additional Red cases cover cold-entry validation, exit/ACK publication races,
ancestor output paths and recorded cleanup boundaries. The race test first
needed its Path import restored after linting; all fixture corrections/logs are
retained. Runtime fixes are limited to opt-in supervision/observer publication
and inherited certifier origin/deadline handling; default search fingerprints
remain unchanged. Ruff, seven-file formatting and whitespace checks pass.

The one-shot launcher is preserved under
results/supervisor_validation_20261020/run_pilot.py, copied and hash-bound into
the new pilot before execution. If no checkpoint is delivered, effective binding
is explicitly unverified/failed and the missing-incumbent row is retained;
it is not treated as a fully verified binding pass. Protocol identity drift
still aborts. No score-based retry or replacement is permitted.

## Operational pilot completed

All eight declared jobs ran once and passed certification, shared-clock,
provenance, config binding, cold/cache, cleanup and the unchanged return gate.
The reopened audit is passed/complete. The source/tests, protocol, launcher,
input/model, packet, result, logs and cache evidence are sealed in
results/supervisor_pilot_20261020/artifact_hashes.json (453 files, manifest itself
excluded). Source SHA-256:
386195f8b5896380aee3670a5eb72e0fda7d72a15dcb4e22082558bb47e551b2.

| Input / case | Parent-validated capture (s) | Solve return including cleanup (s) | Gates |
|---|---:|---:|---|
| R1_2_1 / F101111 | 7.699915 | 10.019174 | all pass |
| R1_2_1 / F111111 | 4.093394 | 10.020397 | all pass |
| R1_2_1 / F000000 | 8.266399 | 10.019754 | all pass |
| c101 / F000000 | 4.417815 | 10.019633 | all pass |
| c101 / F111011 | 5.520788 | 10.019204 | all pass |
| c101 / ALNS | 3.151533 | 10.008810 | all pass |
| RC2_4_1 / F111111 | 9.705832 | 10.018972 | all pass |
| RC2_4_1 / ALNS | 8.609394 | 10.019388 | all pass |

Numeric source: results/supervisor_pilot_20261020/summary.csv. Returns range
10.008810–10.020397s on the shared solve clock; cleanup is included and ranges
0.008640–0.019709s. Worker imports/input/constructor/model setup are excluded
from this solve clock and reported separately. Full CLI child wall time totals
139.144720s across the eight jobs; reaped child CPU totals 138.570471s, versus
80 nominal solve seconds. These totals do not establish isolated-machine or
single-thread backend execution.

Every selected original-space plan was available, received and independently
revalidated/hashed by the supervisor before ten seconds. The latest parent
validation completed at 9.705832s; its worker capture was 9.698059s. The offline
audit reopened all admitted packets, recomputed their route constraints and
objectives, checked packet hashes/shared clock/ACK/admission order, matched the
selected packet to returned routes and confirmed the admitted trajectory.

All eight workers were terminated at cutoff and reaped. Complete final worker
counters are unavailable in 8/8 rows and are exported as null, including final
iterations/effective_config/instrumentation. Their separately labelled delivered
checkpoints retain requested/effective/nested config evidence and partial
counters. A missing final LAC/DDQN/SP count is not evidence of zero activity.
Neither the returned objectives nor checkpoint counts support a learning-effect
or quality-ranking claim from this pilot.

Reproduction uses the preserved, fixed launcher with a new output location
declared before another experiment; the existing directories refuse reuse.
For a separate individual supervised run, the opt-in CLI is:

```sh
.venv/bin/python scripts/benchmark_supervised.py \
  --instance data/Solomon/c101.txt --ablation F000000 \
  --seed 42 --time-limit 10 \
  --session-dir /absolute/new/session --output-json /absolute/new/result.json
```

GNN-on factor cases also require the explicit frozen --gnn-model path. The
default scripts/benchmark.py behavior is retained. Existing successful and
failed stages, including the trace-scope failure/projection and the separate
unplanned CLI test incident, are never replaced by these eight rows.

## Limits and next gate

This establishes the implemented supervisor contract and its operational gate
on three inputs, one seed and one cutoff. It does not provide an unconditional
hard return guarantee, prove a paired wall-clock or quality improvement over
the previous solver.solve protocol, or establish generalization. More seeds
and longer cutoffs, sustained controller/LAC coverage and equivalent external
comparator budget/validation/cleanup policies remain required before publication
launch. No full sweep, manuscript edit, checkpoint change or retraining ran.

All 661 regression tests and the old goldens passed before the declared pilot;
no runtime/test source changed during or after its eight jobs. The final
preservation inventory, exact delta, before/after snapshots, separate incident
record, Red/Green logs and raw/derived evidence hashes are under
results/supervisor_validation_20261020/.
