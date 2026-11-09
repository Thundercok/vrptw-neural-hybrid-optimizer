# VRPTW — next chat handoff, 28 October 2026

## Current active continuation — 29 October 2026

This section supersedes the historical active-run snapshot below. The recovery is already running; do not launch duplicate workers.

- BASE: `ROOT/results/cutoff_clock_audit_20261029`; RUN: `BASE/run`; epoch: `cutoff_clock_audit_20261029`.
- Verified 2026-10-29T11:26:27.793475+07:00: `running`, phase `remaining`, fresh controller and all four runner processes confirmed; finished.json absent. PIDs in status are informational only.
- 6198 actual good observations / 8620, including 163 new good and 0 new bad commits; 21 preserved gaps; 2401 uncompleted cells. Count actual integrity_ok=true commits and add 6035 imported good.
- Source SHA: `6e8b786c5e7149bdd8caed3488c2edb6e291dec66ef11cc8d271030da7728f72`; control SHA: `a7de37bfeed76f0eacb514e58f6fdb4e6fbeca2bd1fc91c6576cab09b5e1ccfd`; primary CSV SHA remains `f57aa23709651e958b350fdfc853f2cdce79407108a0cf8c176c673461676896`.
- Nine historical runtime namespaces passed startup and primary audits in separate Python processes. All 6046 prior commit hashes unchanged. Read BASE/README.md, protocol.md, validation.json and resumption_verified.json.
- Interrupted epoch9 had four started/uncommitted attempts retained as gaps. The first `reboot_continuation_20261028` startup stopped before benchmark dispatch because a historical cleanup clock was compared with the new boot clock. The audit-only `historical_clock.py` replays the exact recorded, hash-bound cleanup_end_perf and retains all descendant chronology/event/hash checks.
- `reboot_clock_recovery_20261028` then closed [0,1,1,1] with 84 good and three bad certificate-clock commits: `05248_C2_2_5_NeuroLKH-adapted_s42_t900`, `05346_R1_2_1_F001111_s46_t300`, `05654_R107_PyVRP-ILS_s42_t60`. Preserve them as gaps; never reclassify, reconstruct scores or retry. Neuro also had an operational late return; all flags retained.
- Only scripts/run_supervisor_pilot.py changes from v9 in the new runtime. Certificates are compared exactly to recorded deadline minus start; deadline must exactly equal start plus registered budget. Strict original-budget capture/receipt limits, admission and return gates unchanged. No solver/search/model/learning settings changed; root source and deferred patch untouched.
- TDD: Red 3 failed/9 negative controls passed; Green 12 passed. Relevant regression 123 passed, two historical provenance-fixture failures reproduced unchanged on v9. Four native configuration checks passed.
- Dispatched only 2564 never-started cells in slots 638/682/580/664; primary prefixes zero; four workers, no overall cap. Expected final good coverage is 8599 if no further failures.
- Prior analysis impact counts/bundles below are historical and must not be presented as current 21-gap impact. No inference, manuscript edits, training, power retuning or AI automation. Existing recovery authorization persists across actual interruptions, subject to audit and never-started-only continuation.


Read this first. It supersedes old launch restrictions and old status counts in `docs/antigravity_handoff.md`; retain that document as historical evidence. The user subsequently authorized the complete overnight sweep with four workers and no overall time/job cap. Do not launch duplicate workers while a controller is alive. If the controller is confirmed gone after interruption, the existing authorization covers an audited continuation in a new isolated epoch, dispatching only never-started cells; no repeated confirmation is required merely because the previous run died.

## Authorization clarification — 2026-10-28T23:21:30.834851+07:00

The earlier sentence “Do not launch another sweep” was too absolute. It meant to prevent duplicate concurrent execution, not to prohibit recovery of the already-authorized matrix. The full-sweep authorization persists across chats and interruptions. Do not ask the user to reconfirm recovery solely because of that sentence. First verify no active controller/runner or other chat is already dispatching; preserve and audit all old evidence, classify interrupted attempts as gaps, and launch only never-started cells in a separate continuation epoch with the same frozen protocol and four workers. Never relaunch the old guarded launcher or retry failed/started cells.

At 23:20 on 28 October, this chat independently read the old status: heartbeat was stale at 19:24:35 local and finished.json was absent. The continuation chat reports a later Mac reboot and four incomplete attempts; verify those inventories before binding a new control. The 19:20 snapshot below is historical, not current liveness. This clarification only changes documentation; this chat has not dispatched any recovery workers. Keep recovery execution in one chat to avoid races.

## Location and permission trap

- Canonical repository (`ROOT`): `/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-optimizer`.
- Historical logical namespace (`OLD`): `/Users/thundercock2/Documents/Github/vrptw-neural-hybrid-solver/VRPTW-Research-Optimization`.
- Relocation is complete and user-confirmed. OLD source/docs/data aliases point into ROOT; historical result directories also contain fill-only hardlinks and migration shadows. Preserve all aliases, paths and files.
- Some chats still start in the old workspace. ROOT was outside this chat's writable sandbox: canonical writes required an escalated executor call. Do not bypass permissions by writing through OLD symlinks. Read-only inspection is sufficient for routine status checks.
- Parent instructions: `/Users/thundercock2/Documents/Github/AGENTS.md`; repository instructions: `ROOT/.agents/AGENTS.md`. Remote is `https://github.com/Thundercok/vrptw-neural-hybrid-optimizer.git`.

## Active run — first action is a fresh read-only check

`BASE = ROOT/results/backend_signal_cleanup_20261028`

`RUN = BASE/run`

Snapshot at **2026-10-28 19:20:43 +0700** (Vietnam time):

- Controller reports `running`, phase `remaining`, heartbeat `2026-10-28T12:20:38.707985+00:00`.
- **5,951 good observations / 8,620 (69.0%)**, including 590 new good commits and 0 new bad commits in epoch9.
- **14 preserved gaps; 2,655 cells remaining**. Four runner processes freshly confirmed live.
- Informational runner PIDs: 92016, 92017, 92018, 92019; these must not be used for signaling.
- Primary CSV SHA checked unchanged at this handoff. No running control or result was modified.


This is a dated snapshot, not a promise that the run remains healthy. Read `RUN/status.json`, each `RUN/shard_i/status.json`, and `RUN/finished.json` if present. Confirm heartbeat age and, when needed, fresh process existence. Stored PIDs are informational, never authority to signal. `ps` required escalation in this sandbox.

Count actual new commits by reading `RUN/shard_*/*/completed.json` and checking `document['record']['integrity_ok'] is True`. Add the 5,361 imported good observations. A stopped controller's completed count can include a bad commit; do not call it valid without checking. Availability, return timing and integrity are separate flags: an audited no-solution or late return can be a valid observation. Inspect bad commits, incomplete started directories and integrity errors if status stops.

Useful files: `RUN/controller.log`, `remaining_runner_i.log`, `control.json`, `control_identity.json`, `imported_references.json`, `infrastructure_failures.json`, `import_audit_startup_*.json`, `import_audit_primary_*.json`; `BASE/resumption_verified.json`, `artifact_hashes.json`, `old_commit_hashes.json`.

Active epoch: `backend_signal_v9_20261028` (eight distinct source versions; nine execution epochs).

- Source SHA: `8db0b64a9253911270432fe5a03d8e3557f863bc0eaff35326df560f3621f31a`.
- Control SHA: `7a7d24968772858985c92a19e778fc0d9f2bc713e04bcb77b9c7ebe8a186cc2e`.
- Primary CSV SHA: `f57aa23709651e958b350fdfc853f2cdce79407108a0cf8c176c673461676896`.
- Launch imported 5,361 good observations, preserved 5,369 historical commit hashes, and dispatched only 3,245 never-started cells across slots 782/833/717/913. Primary prefixes are zero; no primary redispatch.
- Total design: 8,620 cells. Fourteen infrastructure gaps remain unscored and unretried. Expected final good coverage is 8,606 if no further failures.

## User instructions that remain in force

- Keep the full sweep running on this Mac, four workers, no overall cap. Do not restart merely because the chat changes. An actual interruption is different: after confirming no live controller/runner and no competing recovery owner, audit and continue only never-started cells in a new epoch. Preserve interrupted attempts as gaps, without retries or invented exit codes.
- Preserve every historical result, failure, partial attempt, source/control snapshot and provenance hash. Never retry a failed/interrupted benchmark cell or reconstruct scores/receipts.
- No manuscript or Overleaf edits, training, new experimental settings, benchmark-blind rerun, Git commit or unregistered performance inference. The user will eventually paste explicitly supplied LaTeX themselves; they asked to defer that work.
- Keep Antigravity open; the user needs it. Prior control permission was denied. MySQL was stopped by the user; AC/Low Power Mode settings were already handled. Do not retune system settings or concurrency.
- No AI periodic polling/automation was created. The local controller continues without chat tokens. Give concise Vietnamese updates on request.
- Never remove locks or signal saved PIDs. If a stop is necessary and authorized, use `RUN/STOP_REQUESTED` so the owned controller stops cooperatively. Do not touch this file for a handoff.
## Latest repair and its evidence


Read `BASE/README.md` before debugging. The prior epoch `ROOT/results/worker_reap_tail_20261026/run` closed with codes `[0,1,0,0]` after 1,279 good and one bad new record. The failed cell `04387_RC2_4_1_NeuroLKH-adapted_s45_t10` had one child start but no stop/aggregate cleanup proof. Its worker was killed/reaped; no benchmark retry took place. Raw SHA: `48e18bc488c359d4a78d9dae812dd49f47b69c42490d21ad47fe237e7d3b3a1b`.

Only `BASE/runtime/src/vrptw/supervised_process.py` changes from v8. The TERM handler now closes the owned backend registry at safe boundaries; guarded spawn/stop/close operations defer signal cleanup until handle/start-proof registration completes and avoid reentrant waits/writes. A separate signal flag preserves ordinary nonfinal-stop retry behavior. The exact production scheduling point is not proven, and this does not guarantee interruption of all unresponsive native code.

TDD: Red 6 failed/1 control pass, Green 7 passed; two extra receipt-race tests. Relevant regression: 187 passed/one historical physical-provenance fixture deselected. Controller/primary guard: 10 passed; Ruff and all four native preparation checks passed. Tests asserted the actual runtime import path.

Four cold seed99/T60 engineering probes passed protocol/certification/reaping, with one operational late return retained. Separate Neuro RC2_4_1 seed99/T10 passed in 10.352945s with 6 child starts and 6 stop receipts. These are engineering evidence, never replacements for failed benchmark cells.

Parent TERM grace, child wait durations, post-kill worker reap, admission cutoff and return gate are unchanged. All cleanup tail latency is charged; no post-cutoff packet admission. All routing/search/learning/model/reference-fleet settings remain frozen. Across the original source to v9, only supervisor.py, native_supervisor_worker.py and supervised_process.py changed. `BASE/patch_after_sweep.diff` is deferred and has NOT been applied to root source.

## If another infrastructure failure occurs

Do not relax integrity/timing gates, silently rerun, overwrite frozen runtime, or restart an existing launcher. Preserve the failed raw/partial directory and exact hashes; let owned workers close cooperatively, inspect logs/receipts and establish the failure before fixing it by TDD in a new isolated epoch. Audit all prior commits and keep failures as gaps. Historical source namespaces must be audited in separate fresh Python processes to avoid import-cache mixing.

The controller depends on the sealed continuation helper at `OLD/results/cleanup_fix_20261022/continuation.py`. `previous_control` deliberately remains the original recovery control for original four-slot mapping. `BASE/namespace_runtime.py` handles exact registered historical logical/physical roots, executable aliases, hardware checks and backend asset bindings. Do not simplify or bypass those checks. `launch.json` prevents duplicate launch; a pre-dispatch first launch attempt only lacked a Ruff log and was safely corrected. There was no benchmark attempt in that failed launcher invocation.

## Research context and work after sweep closure

IEEE Access manuscript `Access-2026-45322`; 23 reviewer concerns (6+5+12) remain OPEN. Completion does not guarantee acceptance. Frozen matrix: 74 instances (56 Solomon100, 12 Homberger200, 6 Homberger400), seeds42–46, cutoffs10/60/300/900; four main cases plus anchored 16-case ablation on 18 instances, not a full 64-case factorial. Independent cold starts, algorithm-specific initialization. PyVRP0.14.1 is ILS; CPU-adapted NeuroLKH is not an author-experiment replication.

Primary T300: 1,476 recorded observations plus four gaps out of1,480; 1,471 available, five ALNS no-solutions. Six return failures, including one available late Neuro C208/s42 at300.6104s, remain explicit. Certified pre-cutoff quality and operational return flags are separate endpoints. Do not imply every recorded observation is available or on time.

Fourteen current gaps affect20/46 registered analysis scopes (`BASE/analysis_impact/`). Whole-matrix frozen inference rejects missing cells. Do not silently use complete cases, zero scores or imputation. Any missing-data amendment must acknowledge that descriptive outcomes were already inspected. Future final analysis requires closure/provenance audit and an explicit, disclosed missing-data treatment before CI/p-value claims; all travel-distance comparisons remain conditional on fleet matching.

Critical unresolved disclosure: the hybrid uses per-instance BKS/reference fleet INSIDE search (phase transitions, td_only SP and tail vehicle search); ALNS/PyVRP/Neuro do not use the native lookup in search. Equal compute alone does not remove this information asymmetry. Do not alter the frozen lookup or claim a benchmark-blind causal comparison. A separately declared evaluation would be needed.

Training audit: GNN48 synthetic train/12 validation,100/200 customers, seed42, epoch71 of150 selected by validation; geometry disjoint from74 benchmarks, but400 is a size shift. Macro/micro DDQN and LAC are fresh online per worker, not pretrained zero-shot controllers. LAC horizon80 means calls, not ALNS steps, and its future-distance label is observational. SA-approved moves preserved at the acceptance gate does not establish the classical SA convergence theorem. Macro state/Markov and convergence claims require qualification; O(1) applies to a cached feasibility query under assumptions; candidate/pool ordering is not global optimality.

Read supporting artifacts ONLY when needed (paths relative to ROOT):

- `results/training_protocol_audit_20261025/`: audit.md, reviewer_addendum.md, verification and sealed evidence.
- `results/reviewer_response_preparation_20261024/`: internal23-item drafts/worklist; historical gap counts, all concerns still open.
- `results/revision_readiness_20261026/`: static23-item preparation/limitations; pinned to epoch7, not current status.
- `results/analysis_readiness_20261024/readiness.py`: pure structural inventory utility, not inference.
- `results/missing_data_reporting_20261025/` and `gap_aware_bundle*/`: historical pinned bundles; do not apply stale five/seven-gap bindings to epoch9.
- `results/primary_descriptive_peek_20261024/`, `theory_claim_audit_20261024/`, `objective_feasibility_audit_20261024/`.

Next chat should first check the live run and report actual good/gap/remaining counts. Leave healthy workers alone. If the run is interrupted, carry out the audited continuation already authorized above. Manuscript work and experimental protocol changes remain deferred.
