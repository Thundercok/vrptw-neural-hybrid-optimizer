# Fresh-instance test of Micro-DDQN at 60 s

**Status: approved by the authors on 10 November 2026, before any cell of this test ran.** The file is frozen. Its hash
is in `results/micro_replication_20261110/launch_hashes.txt`. Any later change is added below with its date and reason.

## Why this test exists

In the ablation at 60 s, Micro-DDQN looked helpful against the rule-based Micro policy:

| Contrast | Fleet score, 18 test instances | 95% interval | 100 customers | 200 customers | 400 customers |
|---|---|---|---|---|---|
| Micro full context (F111111 vs F111011) | +0.244 | [0.053, 0.492] | +0.100 | +0.167 | +0.467 |
| Micro bare (F000100 vs F000000) | +0.344 | [0.198, 0.516] | +0.033 | +0.200 | +0.800 |

These results are descriptive. The hypothesis came from reading test results, and 47% of those cells ran at a mean
load above 8. This test asks whether the pattern holds on instances that played no part in forming it. The size
breakdown above was read before this test was designed and motivates using 200 and 400 customers only. The paper must
say both of these things.

## What is fixed

**Instances (24).** Homberger instances numbered 9 and 10 of each family (C1, C2, R1, R2, RC1, RC2) at 200 and 400
customers. These numbers were chosen because 9 and 10 are the only ones unused in every family at 200 customers, so
there was no choice among them. By file and folder name, none appears in the 74 test instances, the 30 development
instances or any earlier run. The GNN was trained on synthetic instances. The runtime holds best-known values for
these instances in `config.py`, and these runs set `VRPTW_REFERENCE_BLIND=1`, as the sweep did, so they are not read.

**Cases (4).** F111111, F111011, F000100, F000000. The GES phase is on in all four, as in the ablation.

**Run settings.** Seeds 42 to 46. Cutoff 60 s. 480 cells, four at a time, about 2 to 2.5 hours on a quiet machine.

**Solver.** The frozen `results/ges_sweep_20261102/runtime` and `gnn_checkpoint.pt`, unchanged and checked against
their hashes. The four cases of an instance and seed run together as one block. Load, battery and sleep guards are the
same as in the sweep. The test runs once.

## Analysis

- **Confirmatory (family of 2, 97.5% intervals):** the fleet score of Micro full context and of Micro bare, with
  200 and 400 customers weighted 1/2 each.
- **Method:** the same `analyze_pair` as the ablation, with geometry and seed bootstrap, 10,000 draws, draw seed
  20261110. Instances that share coordinates count as one geometry group.
- **Descriptive (95%):** each contrast by size, matched distance gaps, and both contrasts without blocks run at a mean
  load above 8. If leaving those blocks out changes the wording that applies, report it in the same paragraph.
- Failed or missing cells stay gaps, handled as in the sweep. They are not rerun.

## How the outcome is worded

The rules in `docs/rerun_wording_rules.md` apply, one contrast at a time.

| 97.5% interval of the fleet score | Wording |
|---|---|
| Lower bound above 0 | "Micro-DDQN used fewer vehicles than the rule-based policy at 60 s on these instances" |
| Upper bound below 0 | "used more vehicles than the rule-based policy" |
| Contains 0, or an endpoint is exactly 0 | "did not differ detectably from the rule-based policy on fleet size" |

The paper must also say:

- The hypothesis came from exploring results on the test set, and this test was designed afterwards.
- The test covers 200 and 400 customers at 60 s only. It says nothing about 100 customers or 300 s.
- The comparison is Micro-DDQN against a rule-based policy inside the same framework. It says nothing about ALNS-Base,
  PyVRP-ILS or NeuroLKH-adapted, and the 300 s results stand as they are.
- A null result is reported with the same prominence as a positive one, as "the pattern seen at 60 s did not replicate".

## Not allowed

- Changing the instances, cases, cutoff or analysis after any cell has been read.
- Running further seeds or instances if the result disappoints.
- Reporting only the contrast that comes out positive.
- Changing the solver.

## Settled at approval

1. Both contrasts are kept, as a family of 2 at 97.5%.
2. This test runs before the 900 s stage resumes. `results/micro_replication_20261110/chain.sh` waits for the
   component-cost measurement, runs this test, and resumes the 900 s stage only if this test finished.
3. Load is sampled every 10 s in this test. The sweep sampled once a minute, which leaves a 60 s cell with about one
   sample, so the 47% above rests on about one sample per cell.

## Corrections, 10 November 2026, before any cell ran

These follow a critical review of this protocol. They change no instance, case, seed, cutoff or analysis.

1. **The instances share customer layouts with the test instances.** In Homberger, every instance of a family and
   size has the same coordinates and demands, and instances differ only in their time windows. Instances 9 and 10
   therefore have the same layouts as the 18 ablation instances that produced the hypothesis. Their time windows are
   wider than those of instances 1 and 5. The sentence above saying these instances "played no part in forming" the
   pattern is true of the instances, not of their layouts. The paper must describe this test as new time-window
   variants of the same layouts, and must not call it a test on new instances.
2. **A null result is not a failed replication.** Run through this analysis, the discovery data at 200 and 400
   customers gives +0.317 [0.03, 0.63] for Micro full context and +0.500 [0.25, 0.80] for Micro bare at 97.5%. The
   bootstrap resamples layouts, and there are five per size, so this test may be too small to detect an effect of
   that size in the full-context contrast. Micro was also selected as one of the strongest 60 s contrasts, so its
   true effect is likely smaller. A null result is therefore worded as "this test did not detect a difference and is
   too small to rule one out", replacing "the pattern seen at 60 s did not replicate" above.
