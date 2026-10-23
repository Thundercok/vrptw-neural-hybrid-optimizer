# Primary-300s-first continuation, 2026-10-21

The user explicitly selected: obtain primary results in approximately 36–48
hours, then continue the entire matrix. This amends execution order only. Keep
all 8,620 registered physical cells, five seeds, four primary cutoffs, anchored
ablation cells, algorithms, source, inputs, checkpoints and solver budgets.
The 203-job historical sequential cohort remains separate.

Finish current jobs in the four-worker parallel cohort and independently audit
its stopped prefix. Preserve its manifests, raw artifacts, availability failures
and commits without reruns or changed identities. Link those already completed
parallel cells into the continuation via sealed physical locations, manifest,
commit/evidence hashes and audited rows. Old sequential cells are not imported.
No incomplete intent may be retried or treated as a solver loss.

Prepare new immutable native-executor shard manifests for only unexecuted cells.
All members of a partially executed block stay in the same logical slot as its
earlier parallel members; physical directories differ across this explicit
execution-order amendment. Unstarted blocks are assigned deterministically to
balance the primary work first, then total nominal budgets. Inside each shard,
primary 300s cells precede all other cells; preserve registered relative order
within each of those two partitions. Shared Full cells execute exactly once.
Unlike the earlier contiguous-block order, ablation-only members may execute
later than the primary members of their block; this change is explicit.

Primary means the original 74 instances × four comparators × five seeds at
300 seconds: 1,480 cells, including unavailable outcomes. Do not promote other
ablation cases or other cutoffs into that endpoint. Each runner first executes
its exact primary prefix. After all four owned runners exit and are reaped,
independently audit the new prefixes and old parallel commits, export the full
primary_300s_records.csv and primary_300s_checkpoint.json, then automatically
resume all four unchanged shard manifests without any job or hour limit.
No solvers run during the milestone audit. This is a phase boundary, not a stop
requiring another user instruction. No automatic significance/manuscript edits.

Reuse the frozen native executor and the previously tested external ownership
helpers. Keep exclusive locks, isolated cold workers/caches, original-space
certification, source/config/backend checks, cooperative stop and no blind kill.
Own and reap runner/caffeinate children directly. On manual stop, interruption,
guard failure or a failed runner, finish current transactions and stop further
phases. Never signal a PID recovered from a file. The controller performs native
waiting without periodic model calls. Record phases, heartbeat and swap.

At final closure independently audit every new shard and the imported parallel
prefix, then require exact once-only coverage of all 8,620 parent cells. Export
rows with physical source manifest, execution epoch/control and logical slot.
Do not quietly pool the sequential cohort or claim isolated CPU service. This
is still max-four shared-Mac execution with heterogeneous cores, background load
and unverified backend-wide thread counts. The 36–48-hour target is a budget
estimate, not a deadline or guarantee; the full matrix still takes several days.

TDD covers deterministic primary-first allocation and anchored partial blocks,
exact union with imported commits, duplicate/missing/tampered prefix rejection,
primary-only membership, per-shard phase commands, audit barrier before resume,
stop/error preventing later phases, once-only resume, and final complete-matrix
validation. Negative tests use fixtures, never real benchmark solvers. All new
code/tests live under results/, outside the frozen runtime and test snapshot.
