# GES sweep rerun: analysis plan fixed before launch, 2 November 2026

Written before any cell of this rerun ran on the 74 test instances. The only runs so far used
the development instances in `results/improvement_dev_20261101`, which do not overlap the test set.

## Why this exists

The closed sweep and the reference-blind T300 run showed the hybrid losing to PyVRP on
100-customer instances and to NeuroLKH on fleet size. Those per-family test results set the
direction of this change: a full-budget Guided Ejection Search phase before search
(`src/vrptw/ges.py`, `VRPTW_GES_PHASE=1`, 10% of the remaining budget). Parameters were chosen only on the
development instances, but the choice of direction was not blind to the test set. The manuscript
must say so. GES is a classical method, so any gain from it is not a gain from learning.

## Development gate

Stated to the author before the T300 development run finished, read on seed 1001, 30 instances.

| Condition | Result | Reading |
|:---|:---|:---|
| No more vehicles than the current blind hybrid | fewer 2, same 28, more 0 | met |
| Distance not materially worse at matched fleet | -0.25% / -0.54% / -1.71% for 100 / 200 / 400 | met |
| Fleet gap to PyVRP and NeuroLKH clearly narrower at 100 customers | PyVRP net +1 (was -1), NeuroLKH net +1 (was -1), of 16 and 18 instances | met, thin |

Limits of this evidence:

- It rests on one seed.
- The 100-customer change comes from two instances (`dev100_C1_2_6`, `dev100_RC2_2_8`).
- Those instances are C1 and RC2. The test-set losses that motivated the work were mostly on
  R instances (R104, R109, R110, R112, R207, R211), and the development R instances tied before
  and after. The rerun may therefore not fix those losses.
- The development results are not evidence for the paper.

## What runs

- Design: `results/ablation_design_20261019/jobs.jsonl`, minus PyVRP-ILS and NeuroLKH-adapted.
  5,660 cells: F111111 and ALNS-Base at 10, 60, 300 and 900 s on 74 instances with seeds 42-46, plus the
  15 other ablation cases at 60 and 300 s on 18 instances.
- Every non-comparator cell has `VRPTW_REFERENCE_BLIND=1` and `VRPTW_GES_PHASE=1`. ALNS-Base gets
  GES too, so the comparison with it stays fair. GES is therefore a fixed layer in the factorial,
  and the factor effects are measured on top of it.
- Same CLI, inputs (hashes checked against the design), GNN checkpoint (sha256 `365de53b...`), four
  workers and one-thread environment as the closed sweep.
- `runtime/` is a copy of `results/improvement_dev_20261101/runtime_ges2`, hashed in
  `runtime_manifest.json`. It must not change during the run.
- This is the only rerun on the test set. Results are not used to change the solver. A defect
  that invalidates cells may be fixed only with its affected cells rerun and the fact disclosed.

## Analysis fixed in advance

Registered statistics from `vrptw.sweep_statistics` and `scripts/analyze_revision.py`: per-seed paired
fleet score, matched-fleet distance gap, geometry/seed bootstrap (10,000 draws, seed 20261019), fixed
size-stratum weights, Bonferroni within each family. Primary inference at 300 s.

- Primary family (3 comparisons): F111111+GES vs ALNS-Base+GES, vs PyVRP-ILS, vs NeuroLKH-adapted.
- Secondary (reported whatever the outcome): F111111+GES vs F111111-blind and vs the closed F111111.
- The closed-sweep and blind results stay in the paper's record whichever variant is adopted.

**Adoption rule.** GES becomes the proposed method only if, at 300 s on all 74 instances, its fleet score
against F111111-blind has a 98.75% interval with a lower bound above zero. Otherwise F111111-blind stays the
proposed method and GES is reported as an inconclusive or negative result. Departing from this rule
requires saying so in the paper.

## Known deviations from the closed sweep

1. **Comparators are not rerun.** PyVRP and NeuroLKH code is unchanged, so their closed-sweep cells are
   reused, but they ran about a week earlier. To check that the machine is comparable, 36 anchor cells
   (18 ablation instances, seed 42, 60 s, both comparators) run first and last. They are calibration only and
   do not replace any sweep cell.
2. **Order.** The design's randomized blocks are replaced by stages, with order shuffled inside each stage:
   primary T300, T60, T10, ablation T60, ablation T300, primary T900. This gets the primary endpoint first if the
   run has to stop early. Later stages may run under different machine conditions.
3. **Power.** The machine is on a 20 W adapter and the battery sags under load (3-8% was also seen during
   the closed sweep). A short four-process CPU probe at 9% battery showed no clear throttling
   (0.30 s vs 0.28 s alone), but that does not rule out sustained throttling. Each cell records power
   source, battery level and load average. New cells hold at 3% battery or below and resume above 6%,
   so concurrency can only go down.

## Operation

- Run: `run_sweep_ges.py` (resumable); log in `sweep.log`.
- Stop safely: `touch STOP`. Running cells finish and no new ones start. Delete `STOP` and rerun to continue.
- Interrupted cells move to `run/interrupted/` and run again with the same seed. Any such rerun is disclosed.
- Validate: `validate.py run` writes `run/records.csv`.
- Smoke check on development instances only: 36/36 cells valid (`smoke/`).

## Amendment 1, 2 November 2026, 02:50 (+07): comparators are rerun together with the solvers

Made before any result from the 74-instance solver cells was read. It replaces "What runs" and deviations 1 and 2
above where they conflict. The text above is kept as written at launch.

**What the anchors showed.** PyVRP and NeuroLKH with the same seed retrace the same search, so the time to reach
the same (fleet, distance) step measures machine speed. Across the 18 anchor instances, the closed cell took a
median of 2.35 times as long as tonight for PyVRP (532 steps) and 2.34 times for NeuroLKH (66 steps). Per instance
the ratio ranged from about 0.65 to 9.6. As a result NeuroLKH at 60 s now uses fewer vehicles on 5 of 18 anchors and
more on none. The cause of the slowness in October is not established.

**Consequences.**

1. Reusing closed comparator cells would favour the new solver, so that plan is dropped.
2. The closed sweep is still internally valid: cells of one block finished close together (median gap to F111111
   about 0.1-0.17 h, under 1% of them more than 1 h apart). Its effective compute, however, varied between
   blocks, and the paper must disclose that.
3. The reference-blind T300 run of 1 November is not comparable with closed cells. Its first capture was a median
   of 1.9 times faster than in the matching closed F111111 cell (10th-90th percentile 1.05-3.28). Its comparisons
   with closed cells (+0.049 vs F111111, +0.119 vs ALNS-Base, -0.024 vs PyVRP, -0.127 vs NeuroLKH) are confounded
   in the blind variant's favour and must not be reported as measured effects.

**What runs now.** All cases of one instance, seed and cutoff run as a block, in the design's spirit, with
block order shuffled.

| Stage | Cases per block | Cells | Hours at 4 workers |
|:---|:---|:---:|:---:|
| primary_t300 | F111111+GES, ALNS-Base+GES, PyVRP-ILS, NeuroLKH-adapted, F111111-blind, ALNS-Base-noges | 2,220 | 46.2 |
| primary_t60 | first four | 1,480 | 6.2 |
| primary_t10 | first four | 1,480 | 1.0 |
| ablation_t60 | 16 cases, with their own F111111 cell | 1,440 | 6.0 |
| ablation_t300 | 16 cases, with their own F111111 cell | 1,440 | 30.0 |
| primary_t900 | first four | 1,480 | 92.5 |

Total: 9,540 cells, about 182 machine hours. The two no-GES arms at T300 make the full comparison family valid
whichever way the adoption rule falls. The comparators' closed cells are kept for the record.

**Analysis changes.** The adoption rule now compares with the F111111-blind arm of this run, not the 1 November
run. If GES is adopted, the primary family is F111111+GES vs ALNS-Base+GES, PyVRP-ILS and NeuroLKH-adapted. If not, it is
F111111-blind vs ALNS-Base-noges, PyVRP-ILS and NeuroLKH-adapted. The effect of reading the reference fleet is not
re-estimated under matched conditions, so the paper reports only that the closed F111111 read it.

**Cells set aside.** Four solver cells that had finished under the first plan are in `superseded/`. They were not
read and are not used. The 36 `*_anchor_start` cells in `run/` are calibration only. Runner and validator changed
after launch; `runtime/` did not (`runtime_manifest.json` still applies).

## Amendment 2, 2 November 2026, about 09:50 (+07): machine sleep and power guards

Made after reading only start times, cell durations, power state, load and the machine's sleep log. No solver outcome
from the 74-instance cells has been read. It adds to Amendment 1 and replaces the battery thresholds in deviation 3.

**What happened.** The lid was closed and the machine unplugged at 06:32, and it slept on and off until 08:30. A Low Power
Sleep followed at 08:43, on AC at 4% battery, until 09:36. Sixteen cells in five T300 blocks were frozen mid-run (R1_2_1 s45,
RC205 s43, C2_2_5 s46, R111 s45, R1_2_5 s46). `wall_sec` does not show this, because `perf_counter` stops during sleep. The
wall-clock span of those cells exceeded their measured duration by 374 to 4,232 s; no other cell exceeded 5 s. The author
reports that the machine is regularly unplugged to go to class and that Codex also runs on it.

**Rules, none of which depend on outcomes.**

1. A cell is frozen if its wall-clock span exceeds its measured duration by more than 5 s (`clock_gap_sec` in `records.csv`).
2. Every cell of a block with a frozen cell moves unread to `run/slept_blocks/`, and the whole block runs again with the same
   seeds. The runner checks at launch and after each pass of a stage. All such reruns are disclosed.
3. No new cell starts on battery. New cells hold at 10% battery or below and resume above 15%.
4. Sensitivity analysis: the primary family is repeated without blocks that have a cell started at load1 above 8. Cells
   started before 07:00 had load near 5; later cells had 7 to 63. Both analyses are reported.

Rule 3 changed the same morning, before any cell ran under it: new cells hold at 5% battery or below and resume above 8%, because
the machine ran overnight at 6-9% on AC and the Low Power Sleep happened at 4%.

**The closed sweep.** Result-file times show 65 pauses over 5 minutes in its 52 run folders, about 53 hours in total counting
gaps over 30 s. The sleep log only goes back to 26 October, so these pauses cannot all be attributed to sleep. Frozen time is not
counted by `perf_counter`, so pauses alone do not explain the 2.3 times slower step times in Amendment 1. Background load (Codex)
and throttled running during dark wake are hypotheses, not established causes. The paper reports the variation and says its
cause is not established.

## Amendment 3, 2 November 2026: the development instances are not independent of the test set

Made before any solver outcome from the 74-instance cells was read. "Do not overlap" in the opening section holds only for
instance identity. All 30 development instances share customer coordinates with a Gehring-Homberger test instance of the same
family, and a median of 50% (up to 81%) of a development instance's customer records are identical to those of a test instance.
Solomon test instances are not involved. The paper must say this. The analysis plan and adoption rule do not change.

## Amendment 4, 3 November 2026, about 02:00 (+07): load guard and rerun of high-load blocks

Made before any solver outcome from the 74-instance cells was read, using only start times, load, power state and the sleep log. `validate.py` had not been run on `run/`. The author chose this after seeing the load counts below.

**What happened.** Other work on the machine, including test and evaluation jobs of another project, pushed the one-minute load as high as 233 when cells started. Normal load for this sweep is about 5. Of 663 started T300 cells, 265 started above load 8, and 58 of 111 blocks had at least one such cell. The machine entered a Low Power Sleep at 01:03 on AC at 6% battery and rebooted at 01:06, killing the runner and four running cells. The cause of the reboot is not established.

**Rules, none of which depend on outcomes.**

1. Every cell of a `primary_t300` block (instance, seed) with a cell started at load1 above 8 moves unread to `run/high_load_blocks/`, once, and the whole block runs again with the same seeds. Those cells are not used for any estimate.
2. From now on no new cell starts while load1 is above 8. A held worker resumes at load1 of 7 or below. Load is read just before `started.json` records it, so a cell can still record slightly above 8. Such a cell stays in place, and the sensitivity analysis in Amendment 2 still applies to it.
3. The sensitivity analysis stays as registered. The paper reports the number of blocks rerun under this amendment.

Nothing else in the analysis plan or adoption rule changes.

## Amendment 5, 3 November 2026, about 13:00 (+07): load during a cell's run

Made before any solver outcome from the 74-instance cells was read, using only start times, cell durations, load, power state and the sleep log. `validate.py` has not been run on `run/`. The author chose this after being told of the gap below.

**What happened.** The guard in Amendment 4 reads load only when a cell starts. On 3 November at about 12:50 the one-minute load rose to between 50 and 86, with almost no idle CPU, while cells that had started below the limit were running. Neither the guard nor the sensitivity analysis in Amendment 2 sees this. About 450 T300 cells had finished before load was sampled during runs.

**Rules, none of which depend on outcomes.**

1. `sample_load.py` appends the load averages to `load_samples.jsonl` about once a minute, starting at 12:51:20 (+07). It does not touch the runner or any cell. It stops when the sweep finishes and must be restarted after a reboot.
2. A `primary_t300` cell is measured if at least 3 samples fall between the `utc` of its `started.json` and of its `completed.json`. Its run load is the mean load1 of those samples. A measured cell is exposed if its run load is above 8, the limit of Amendment 4. No other limit will be tried.
3. No cell moves and no block runs again because of this amendment. The adoption rule, the primary family and their estimates use the same cells as before.
4. Two sensitivity analyses are added, each repeating the adoption contrast at 98.75% and the primary family at 98.33%. Analysis A drops every block with an exposed cell and keeps blocks with an unmeasured cell. Analysis B also drops every block with an unmeasured cell. Neither can change the adoption decision. Both are reported, along with the number of exposed and unmeasured blocks, next to the analysis in Amendment 2.
5. Load cannot be reconstructed for cells that finished before sampling began, so Analysis A does not clear them. The paper says so.
6. An instance with no block left leaves its size stratum's mean without counting as ties. If a size has no block left, or a bootstrap draw leaves one empty, the result is reported as undefined, not reweighted.

Nothing else in the analysis plan or adoption rule changes.


## Amendment 6, 9 November 2026, about 23:15 (+07): the 900 s stage is stopped

The `primary_t900` stage is stopped by the authors' decision, with 64 of its 1,480 cells finished and none of them read or analyzed. The analysis counts a stage only once a later stage has started or the run has finished, so `primary_t900` stays unanalyzed and no T900 estimate is reported.

**Why.** Finished cells ran under a median load of about 25, at the observed rate the stage needed about 8 more days, two NeuroLKH-adapted cells failed with a missing `descendant_cleanup.json`, and the component-cost and GNN recall measurements requested by the reviewers had to wait for the machine. The decision was made after reading the results at 10, 60 and 300 s and the ablation, and before reading any 900 s result. The paper states that the 900 s stage was not completed.

Nothing else in the analysis plan or adoption rule changes.

## Amendment 7, 10 November 2026, about 03:00 (+07): the 900 s stage is resumed

The authors decided to complete `primary_t900`, which Amendment 6 had stopped. This replaces the statements in Amendment 6 that no T900 estimate is reported and that the paper states the stage was not completed. The decision was made after reading the results at 10, 60 and 300 s and the ablation, and before reading any 900 s result. The paper must say this.

**What changes.** Only that the stage runs to the end. `resume_t900.sh` waits for the component-cost measurement to end, so the two do not overlap, then removes `STOP` and relaunches the runner and the load sampler. The runner, validator, runtime and GNN checkpoint are unchanged: their hashes were checked against `launch_hashes.txt` and `runtime_manifest.json` before this restart, and the load, battery and sleep guards stay as they were.

**The 64 cells finished before the stop** are kept and remain unread. They ran under a median load of about 25, and the sensitivity analyses of Amendment 5 apply to them as written. Two of them, `R205_NeuroLKH-adapted_s42_t900` and `RC107_NeuroLKH-adapted_s46_t900`, returned code 1 after about 925 s with no `descendant_cleanup.json`. Their cause is not established. Both started soon after load spikes (5-minute load about 17 and 40). They are not rerun and stay as gaps under the existing rules. Any further cell that fails this way is added here.

**Status of the results.** The 900 s comparisons stay descriptive, with unadjusted 95% intervals, as `docs/rerun_wording_rules.md` already fixes. They cannot carry a claim in the abstract or conclusion, and they cannot change the adoption rule or any 300 s primary result.

**Stopping rule, added to Amendment 7 on 10 November 2026 (authors' decision, before any 900 s result was read).** When the authors declare the text of the manuscript and response letter final, the stage ends if it has not finished. No 900 s cell is read or analyzed before the stage has finished, so this rule cannot depend on 900 s outcomes. The trigger is the state of the writing only, and the writing does not wait for the stage. If the stage is ended this way, `STOP` is restored, no 900 s estimate is reported in any form, including from the cells already completed, and the paper states that the 900 s stage was started and not completed.

**Component cost repeated, added to Amendment 7 on 10 November 2026.** The first component-cost measurement did not count LAC, because `scripts/measure_component_cost.py` attached its counters to an object that `solve()` replaces. Its output is kept in `analysis/component_cost_lac_uncounted_20261110`. Before any new 900 s cell had started, `STOP` was restored and the runner exited. The script and its test were corrected, the 18 measurements were started again, and `resume_t900.sh` was relaunched to resume the stage after they end.

**Order changed, added to Amendment 7 on 10 November 2026.** Before any new 900 s cell had started, the authors approved a separate test on fresh instances (`docs/micro_replication_protocol.md`, folder `results/micro_replication_20261110`). The waiting `resume_t900.sh` was stopped, and `chain.sh` in that folder now runs the component-cost measurement's remainder, then that test, then `resume_t900.sh`. The 900 s stage, its analysis and its stopping rule are otherwise unchanged.

## Amendment 8, 12 November 2026, about 02:30 (+07): the 900 s stage is ended

`STOP` was restored by the authors' decision, and the stage ends here unfinished. No 900 s result has been read or analyzed, and none will be reported.

**Why.** Every NeuroLKH-adapted cell of the stage since its restart on 10 November (first at about 20:21) returned code 2 within seconds, 69 of 69, with the error "NeuroLKH assets differ from prepared build manifest". The NeuroLKH build in `results/external/NeuroLKH` (the `LKH` binary and its object files) had been recompiled on 10 November, apparently while preparing NeuroLKH for continuous integration, so it no longer matched the build the sweep was prepared with, and the runner refused to use it. Each affected block therefore lacks a valid NeuroLKH-adapted cell, and any 900 s comparison against NeuroLKH-adapted would be biased. The failure was found from return codes and error logs alone. The 10, 60 and 300 s stages and the ablation finished on 9 November, before the rebuild, and the Micro-DDQN test does not use NeuroLKH, so neither is affected.

This also satisfies the stopping rule of Amendment 7: the paper states that the 900 s stage was started and not completed.
