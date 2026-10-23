# Common native/PyVRP/NeuroLKH supervision (2026-10-20)

## Specification before implementation

Extend only the opt-in supervised CLI/worker and the two external adapters to
accept the existing parent-origin certifier. Default adapter calls, native
search, parameters, integer precision, pretrained assets and historical evidence
stay unchanged. Preserve the previous launchers/results and both golden files.
Use TDD, retain Red/Green and source snapshots, then run the full regression suite.
No full sweep, manuscript edit, retraining, backend retuning or asset rebuild.

All four cases (ALNS, F111111, PyVRP-ILS 0.14.1, adapted NeuroLKH) use one parent
perf_counter start/cutoff. After setup, model building/quantization, inference,
search, original-space certification, IPC, parent validation/hash and cleanup
are charged to that solve/return interval. Imports/constructor/frozen model load
stay in separately reported setup. Keep the fixed [T-0.05,T+0.5] return gate,
fresh process/empty exclusive work/cache, JIT on, hash seed 42 and one-thread
requests. No warmup, padding, reserve or compile-cost subtraction.

PyVRP callbacks and NeuroLKH tour polling publish through the injected
NativeIncumbent observer after their existing original-feasibility/backend
selection checks. The observer adds owned original-space certification and
serialization cost inside T. Only parent receipts fully validated/hashed before
T can become returned plans. No promotion from completion records or late disk
replay. The existing integer-model candidate stream remains unchanged; its
precision/representativeness limitations remain explicit. Use a distinct external
execution-mode label while preserving the native label and default behavior.

Bind PyVRP's exact version and NeuroLKH source/checkpoint/binary/build-manifest
identity in request and ready, in addition to source/input/seed/full config.
Require an explicit existing NeuroLKH root; canonicalize it before worker launch.
Frozen native GNN is accepted only by the existing native factor cases.
Preserve external backend diagnostics/parameters in labelled partial checkpoints
and complete counters only if completion exists. PyVRP backend iteration totals
are unavailable before its result; NeuroLKH trial counts are unavailable. Do not
export either as invented zero iterations.

## NeuroLKH process ownership and failure behavior

An opt-in worker-owned process registry starts LKH in the worker's process group,
registers the actual Popen handle, and reaps it on every stage exit. Its SIGTERM
handler only records a stop request; it cannot throw between spawn and handle
registration. The main poll loop observes the request. At shutdown it allows
0.03s for termination, then kills and allows another 0.03s to reap. Preserve the
legacy adapter's default cleanup path when no owner is supplied.

Keep the parent's existing 0.1s termination/0.1s kill grace for every case. Owned
start/stop events and a final atomic descendant-cleanup record bind token,
identity, worker PID, actual return codes, reaping times and reaped-descendant
CPU. Parent cleanup includes reading/checking that record. Missing, malformed,
foreign or unreaped descendant evidence fails closed, even if earlier routes
were admitted. No stale-PID signalling or unconditional hard-real-time claim.
The process group still provides fallback termination; it does not prove reaping
or authorize fabricated descendant CPU/cleanup success.

## Tests before changes

- Fake-clock adapter tests: inherited origin/deadline, no fresh T, no late
  model/inference/backend start, original certified snapshots/observer delivery,
  no post-cutoff promotion, unchanged unsupervised behavior.
- CLI/worker tests: supported cases and explicit asset roots; pin drift rejected
  before solve; external diagnostics/counter scopes; negative tests stub all
  supervision and never launch native solves accidentally.
- Owned stdlib process tests: normal, SIGTERM-resistant and already-exited child;
  reaping and CPU/event evidence; stop requested during spawn; no later spawn;
  parent rejection of absent/corrupt/foreign cleanup records. A real supervisor
  fixture with a grandchild checks termination/reaping at cutoff. Synthetic
  fixtures are protocol tests, not solver-quality evidence.

Freeze a separate small four-case operational schedule only after tests pass.
Declare its input/seed/cutoff/order and exact configs before launch; retain every
failure, abort integrity drift and independently reopen original-space packets.
This integration alone does not approve baseline representativeness, statistics,
the full sweep's compute allocation or publication claims.

## Operational preflight declared before execution

After tests/static checks pass, run sixteen jobs once: all four cases on c101,
R1_2_1 and RC2_4_1 at 10 seconds/seed42, plus all four on RC2_4_1 at 60 seconds/
seed43. Total nominal solve budget: 360 seconds. Shuffle the four blocks using
order seed 20261020, then rotate the fixed ALNS/Full/PyVRP/NeuroLKH order; every
case occupies each position once. This is a small engineering coverage check,
not a four-solver quality comparison, 300/900-second validation or full sweep.

Use the same frozen native GNN SHA-256
365de53beba09097d1176a8b102ced8d6d97311f5a3ac82186b116d3290e1b97 and the existing
pinned NeuroLKH checkout. Save both backend identities and all requested,
effective/nested configs, exact commands, protocol and source/test snapshot
before the first child. Freeze under a new directory; refuse reuse. Check live
source/input/model/backend identities before/after every job. No profiling,
retuning, retry or score-based exclusion.

Independently reopen/hash all observed packets, validate admitted original-space
routes and complete trajectories, match the returned selection to a timely parent
admission, verify config and external diagnostics/precision, cold state, shared
clock, parent/descendant cleanup and the same return gate. Preserve no-incumbent
and timing failures; stop on integrity/cleanup errors. The launcher's watchdog
uses the existing T+180 allowance and SIGINT cleanup path. Null iteration/final
counter scopes must remain explicit. Seal all evidence after reopening the CSV
and packet audit. No automatic full-sweep launch follows.

## Implementation and verification

The external adapters now accept an optional parent certifier; default calls keep
their existing private clock and candidate/precision/cleanup behavior. PyVRP's
callbacks and NeuroLKH's tour capture publish certified owned snapshots through
the same worker IPC and parent validation path. The opt-in CLI adds explicit
backend identities and NeuroLKH root, with `external_supervisor_v1` for external
results and the unchanged native execution-mode label for native results.

`BackendProcesses` owns actual Popen handles and immutable start/stop events.
NeuroLKH's worker records a final closure and reaped-child CPU; the parent checks
its token/identity/PID, clocks, event hashes, return codes and reaping before
returning any plan. Missing/corrupt closure fails closed even with an admitted
incumbent. The parent keeps its existing termination/kill grace. No PID read
from an old record is used for signalling.

There are **34 new tests**. Initial Red had 17 failures/three passes; additional
Red cases exposed future cleanup timestamps, escaping process groups and the
missing reusable audit/launcher interfaces. Real stdlib fixtures cover a
SIGTERM-resistant grandchild and a removed closure record without leaking that
child. Worker tests check backend drift and null iteration scope. The full suite
passes **729 tests in 181.10s**, including the old golden fingerprints, with the
existing PyVRP infeasible-fixture warning. Ruff, eleven-file formatting and
whitespace checks pass.

The existing native pilot auditor gains an optional expected execution-mode
argument with the same native default; its shared route/clock/config/cold checks
are reused. The previous sealed launchers/protocols/results remain unchanged.
The old unsupported-CLI test now uses OR-Tools, which remains outside this CLI.
PyVRP iteration totals are null until its completed backend result; NeuroLKH
trial totals stay null. External certificate `iter=0` is the certifier's
unspecified-iteration context, not a measured backend iteration total.

## Completed common-supervisor preflight

All sixteen declared jobs ran once, under source SHA-256
`60a9b173dbf5aa844e1c8ff4a5022a62c74a41345f5157521e976a9f91062ba1`.
Certification, shared clock, provenance, requested/effective config binding,
cold/cache entry, cleanup and the unchanged return gate each pass **16/16**.
The independent reopened audit reproduces all gates and counter CSV fields and
checks **348 admitted original-space packets**, route/packet hashes, complete
admitted trajectories and the selected timely parent incumbent.

| Cutoff | Jobs | Solve return including cleanup | Latest parent admission |
| --- | ---: | ---: | ---: |
| 10s | 12 | 10.009060–10.151004s | 9.957000s |
| 60s | 4 | 60.018582–60.126111s | 58.026424s |

Numeric sources: `results/comparator_supervisor_pilot_20261020/summary.csv` and
`results/comparator_supervisor_validation_20261020/admissions.csv`. The 60-second
block covers only RC2_4_1/seed43. This stage does not test external supervision at
300/900 seconds or establish instance/seed generalization.

All four NeuroLKH rows have valid closure records for **20 owned LKH children**,
all reaped. No LKH child required kill escalation in these operational jobs.
The parent did SIGKILL each of the four NeuroLKH workers after its termination
grace; their LKH children had already been reaped and closure records persisted.
Worker shutdown therefore is not described as graceful. Returns remain within
the declared gate, with actual cleanup included. Cleanup across all cases spans
0.008614–0.149960s. Event/CPU evidence is in
`results/comparator_supervisor_validation_20261020/descendant_audit.csv` and
`resource_audit.csv`; synthetic resistant-child tests separately cover escalation.

Full CLI child wall time sums to 530.670626s and recorded CPU to 507.086585s,
against 360 nominal solve seconds. Setup and frozen-model loading are separately
recorded. These values do not establish isolated hardware or an actual one-thread
count for every backend. Four NeuroLKH completions provide complete available
adapter counters; the other twelve final counter records remain null. Even a
complete NeuroLKH record has no measured LKH trial count. Checkpoints in every
case remain partial; no quality ranking or learning-effect inference is made.

The pilot seals 933 files, including source/tests, protocol, exact commands,
backend/model/input identities, raw results, packets, resource evidence and
pending files. Red/Green/full-suite logs, before/after source, exact delta,
reopened CSV audits and preservation checks are retained separately under
`results/comparator_supervisor_validation_20261020/`.

For one independent external job, use new session/result paths:

```sh
.venv/bin/python scripts/benchmark_supervised.py \
  --instance data/Solomon/c101.txt --ablation neurolkh --seed 42 \
  --time-limit 60 --neurolkh-root results/external/NeuroLKH \
  --session-dir /absolute/new/session --output-json /absolute/new/result.json
```

PyVRP uses `--ablation pyvrp` without `--neurolkh-root` or the native GNN argument.
Existing output/session paths are refused; no old result is replaced.

## Remaining work before a full-sweep launch

The common-supervisor implementation and its declared preflight are complete.
Next bind the prespecified sweep jobs to frozen executable configs, add resumable
block execution/integrity checks, and implement/test the registered geometry/seed
analysis. Baseline precision/representativeness and the full compute policy still
need explicit treatment in that launch artifact. The earlier frozen design and
its `launch_ready=false` remain historical evidence, not an activated executor.
No full sweep, manuscript edit, backend rebuild or checkpoint change ran.
