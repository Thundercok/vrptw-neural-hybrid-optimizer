# Continuation after the cleanup infrastructure failure, 2026-10-22

The user authorized continuation after the primary-first sweep stopped. Preserve
the frozen solver/executor source and every historical result, manifest, failed
attempt and control file. No manuscript edits or automatic retries.

The stopped cohort has 705 committed cells (40 earlier parallel imports plus
665 primary-first commits), and one incomplete attempt:
04057_RC206_F111111_s44_t300. Its outer CLI was reaped with exit code 1;
stderr records PermissionError from worker-group SIGKILL during cleanup. The
underlying OS reason is not established. A read-only process inventory found no
remaining benchmark workers. Do not signal any PID recovered from these files.

Seal the complete failed-attempt file inventory in a separate infrastructure
ledger. Do not manufacture result.json, reconstruct parent admission times from
saved incumbents, certify this attempt, call it a solver loss, or retry it.
The ledger is a missing measurement, not an algorithmic no-solution outcome.

Re-audit the 705 committed cells against their original physical manifests and
immutable evidence. Use commit verification without rewriting old derived CSVs
or statuses. Require that no old controller/runner lock is held. New manifests
contain only the 7,914 never-started cells, in their original logical slots and
within-slot order. Inputs/configs/backends/cutoffs/cold starts remain unchanged;
physical paths and the external execution epoch change explicitly.

First run the 809 unstarted primary-300s cells (202/204/202/201 by slot). At the
barrier, reap all four runners, independently re-audit all imports and new
commits, then export 1,479 primary records and a checkpoint explicitly labelled
with one infrastructure gap out of 1,480 declared cells. Do not label the
primary dataset complete or silently remove its missing paired observation.
Automatically continue every remaining cell with no overall time/job cap.

At closure export 8,619 committed records plus the separate one-cell gap ledger,
requiring their disjoint, exact union to equal all 8,620 registered cells. Label
the closure completed_with_infrastructure_gap, not a fully valid complete
dataset. Any inferential analysis must disclose this missingness and all earlier
availability, execution-order, concurrency and power-policy limitations.

Reuse frozen native execution and tested external ownership/waiting helpers.
Retain source/config/backend/certification/return gates and exclusive locks.
On any new runner/integrity/guard error, stop further dispatch cooperatively
after current jobs; do not auto-quarantine arbitrary future failures. A
STOP_REQUESTED file or SIGINT similarly stops after current transactions.
Own and reap runner/caffeinate subprocess objects; never act on recovered PIDs.

TDD covers exact coverage including a distinct gap, no retries, fixed slots and
order, rejection of non-prefix/tampered/ambiguous old attempts, rejection of
missing/duplicate/unregistered rows and fabricated gap scores, immutable import
checks, primary-only checkpoint membership, and errors preventing later phases.
All implementation and tests live under results/, outside frozen source/tests.
