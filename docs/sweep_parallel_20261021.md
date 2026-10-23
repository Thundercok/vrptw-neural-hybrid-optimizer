# Mac parallel sweep execution, 2026-10-21

User authorized stopping Homebrew MySQL and maximum practical throughput on the
existing Mac. Finish the current sequential transaction before starting any
parallel solver. Preserve that entire cohort, including incomplete-matrix audit
status; never rewrite its frozen sequential policy.

## Contract before implementation

Reuse the unchanged frozen `scripts/run_sweep.py` executor in independent,
disjoint shard directories. Each shard remains sequential and keeps its kernel
lock, launch intent, receipt, cold process/cache, packet certification, cleanup,
source/input/model/backend checks, evidence hashes, and once-only recovery.
Never remove a live lock or signal a PID obtained from a file. Keep every
algorithm setting, seed and per-job cutoff unchanged. A block (same instance,
seed and cutoff, all comparison cases) stays within one shard. Greedily assign
blocks in registered order to the least nominally loaded shard; preserve order
inside each shard. The union must equal the intended job set exactly once.

Only temporary output/input/checkpoint command paths are rebound. Recompute each
job declaration and shard manifest hash before dispatch. Bind the parent
manifest, shard assignment, external controller and this protocol. Copy all
prepared assets; preserve the original source archive and configuration
bindings. Do not change frozen runtime, tests, models, prior evidence or paper.

A stdlib controller owns up to four native runners and a caffeinate child.
All owned processes are reaped. Manual STOP_REQUESTED, controller interruption,
guard failure or any failed runner stops all remaining runners cooperatively
after their current jobs; no automatic retries or blind kills. No hour deadline,
AI polling or job cap. Audit every completed shard before declaring completion.
Combined CSV carries shard and execution-policy identity; it is a view of
audited commits, not a replacement for raw evidence.

## Capacity pilot and selection, fixed before outcomes

Run separate two-slot and four-slot engineering pilots, in that order. Each
uses the first two registered ten-second primary blocks at each size
(100/200/400), all four cases: 24 jobs per pilot, fresh independent directories.
Do not inspect objective values to choose concurrency. Select the highest slot
count for which all 24 integrity and return gates pass and observed swap usage
does not grow by more than 512 MiB from the pilot's pre-launch baseline. Log
swap samples every five seconds, plus startup and completion; missing samples
make the capacity decision unverified. Preserve failed pilots without retries.
This short pilot is not a memory upper bound for 900-second solves or every
ablation; record this limitation. If neither passes, resume the original
sequential experiment under an external unlimited controller.

On passing capacity validation, prepare a NEW complete 8,620-job cohort using
the selected maximum concurrency. Keeping the complete matrix under its own
policy avoids pooling the old sequential prefix with new parallel outcomes.
The earlier approximately 200 jobs remain independent historical evidence;
they are not erased, substituted, or relabelled. The extra complete cohort is
an execution-policy change, not selective retry based on solver scores.

The policy is maximum concurrency, not CPU affinity or isolated cores. This
Mac has heterogeneous Performance/Efficiency cores and other applications;
Torch/Numba/BLAS one-thread requests do not establish the HiGHS thread count.
Log actual runner lifetimes and swap, retain return-gate failures, and make no
claim of identical CPU service, measured fourfold speedup, isolated hardware,
or publication readiness. Statistical analysis needs the new execution-policy
identity and full audited matrix; no automatic manuscript/statistics update.

## Tests

Before implementation, fail tests for exact/disjoint coverage, atomic blocks,
stable order/load assignment, command path rebinding/declaration hashes,
duplicate/empty/collision refusal, owned-process cleanup, stop-on-error/manual
stop, status completion, and capacity selection independent of objective values.
After Green, run the existing executor regression tests and static checks.
Use stdlib process fixtures, never real solvers, in controller negative tests.
