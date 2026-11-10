# Records of the Micro-DDQN test at 60 s, run on 10 November 2026

Compact records of the test fixed by `docs/micro_replication_protocol.md` and reported in the
ablation section of the revised manuscript. The full cell outputs (about 1.4 GB: routes,
trajectories, supervisor receipts and logs for every cell) are kept by the authors and are available
on request.

## What the test was

24 Homberger instances (numbers 9 and 10 of each family at 200 and 400 customers), four cases
(F111111, F111011, F000100, F000000), seeds 42 to 46, cutoff 60 s: 480 cells in 120 blocks. These
instances are new time-window variants of the layouts of the ablation instances, not new layouts.
The test ran once, from 05:38 to 20:21 (+07) on 10 November 2026, with the solver snapshot and GNN
checkpoint of the rerun. It took far longer than the 2 to 2.5 hours planned for a quiet machine,
because the load guard held new cells 368 times. One block (C1_4_9, seed 44) was frozen by sleep and
was rerun whole under the sweep's rule (README Amendment 2 of the rerun); no other cell was rerun.

## Files

- `records.csv`: one row per cell from the rerun's validator (`validate.py` in
  `results/rerun_records_20261102`, unchanged, given this test's run folder as its argument): stage,
  instance, case, seed, cutoff, whether a certified solution was found, fleet size, distance,
  capture and return times, power, battery and load at start, clock gap, and any validation errors.
  All 480 cells are valid and report one solver source hash, the same as the rerun's.
- `analysis/results.json`: output of `analyze.py`, run once after the test had finished.
- `load_samples.jsonl`: load averages sampled about every 10 s during the test (4,202 samples).
- `sweep.log`: the runner's log, with every hold and every cell's return code.
- `launch_hashes.txt`: hashes recorded before the first cell ran. The protocol appears twice: the
  second entry, of 04:32, is the protocol after the corrections at the end of that file, and is the
  one that matches the committed protocol.
- `run_replication.py`, `analyze.py`, `sample_load.py`, `chain.sh`: the runner, the analysis, the
  load sampler and the script that ordered this test before the 900 s stage. They are byte-identical
  to the files that ran and match `launch_hashes.txt`. Their paths assume the layout at run time
  (`run/records.csv`, `inputs/`, `../ges_sweep_20261102/`), so they document the run and do not
  execute from this folder as it stands.

Not copied here because they are already in the repository:

- The 24 instance files, under `data/Gehring_Homberger/`. They are byte-identical to the inputs
  hashed in `launch_hashes.txt`.
- The solver snapshot, in `results/rerun_records_20261102/runtime/`.
- The GNN checkpoint (sha256 `365de53b...`), at `results/gnn_retraining_20261017/model_seed42/best.pt`.

## Result

Fleet score, positive in favor of Micro-DDQN over the rule-based policy, 200 and 400 customers
weighted 1/2 each. The two contrasts form the confirmatory family, at 97.5%.

| Contrast | Fleet score | 97.5% interval | Seed pairs: wins / ties / losses |
|---|---|---|---|
| Micro bare (F000100 vs F000000) | +0.208 | [0.025, 0.450] | 29 / 87 / 4 |
| Micro full context (F111111 vs F111011) | +0.150 | [-0.012, 0.372] | 25 / 88 / 7 |

By the wording fixed in the protocol: in the bare configuration, Micro-DDQN used fewer vehicles than
the rule-based policy at 60 s on these instances; in the full context, the test did not detect a
difference and is too small to rule one out.

71 of the 120 blocks ran at a mean load above 8. Without them the fleet scores are +0.114 (bare) and
+0.157 (full context), and both intervals are undefined, so no direction is stated for the remaining
blocks alone.

The test covers 200 and 400 customers at 60 s and compares Micro-DDQN with a rule-based policy
inside the same framework. It says nothing about 100 customers, about 300 s, or about ALNS-Base,
PyVRP-ILS and NeuroLKH-adapted. The hypothesis came from exploring results on the test set, and this
test was designed afterwards.
