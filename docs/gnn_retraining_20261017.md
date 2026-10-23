# GNN Retraining Execution Report

Status: full seed-42 training and artifact audit completed on 2026-10-17.
This is a new experiment, not a reconstruction of historical model training or
evidence that the new model improves routing. No benchmark test instance was
scored, and no manuscript or historical checkpoint/result was replaced.

Subsequent work is recorded in [the deadline and integration report](deadline_validation_20261017.md).
It uses a newer solver source and performs a small integration pilot; the training
run and validation-only diagnostics described here remain frozen at their original
source version. Historical training audit must use that source snapshot.

## Frozen Inputs and Execution

- Dataset: `results/gnn_retraining_20261017/manifest.json`.
- 48 synthetic train and 12 synthetic validation instances: C/R/RC distributions,
  100/200 customers. All 74 benchmark test identities retained for later evaluation.
- Zero cross-split numeric or geometry collisions. The 74 test cases have 12
  geometry groups; they are not 74 independent spatial samples.
- Teacher: 60 independent cold-start ALNS runs, seed 42, nominal 10-second solve
  budgets. All saved routes passed feasibility, exact-cover, objective and
  input/source provenance checks. No pretrained GNN was used by the teacher.
- Actual teacher solve times: 9.951572 to 10.576862 seconds, mean 10.023144;
  601.388664 seconds total search. Setup/import overhead is additional.
- One teacher run exceeded the unchanged 0.5-second diagnostic tolerance:
  `SYN_VALIDATION_RC_200_001`, 10.576862 seconds. Its original label/log is retained;
  labels were not rerun or filtered to obtain a timing pass. These labels are not
  a completed equal-cutoff solver comparison, and the deadline gate stays open.
- Fresh GNN, CPU, one Torch thread, deterministic algorithms, seed 42, Adam,
  learning rate 0.001, 150 epochs. Python 3.12.6, Torch 2.11.0, NumPy 2.2.6.
- Measured training command elapsed time: 292.25 seconds, including startup.

## Checkpoint and Learning Curve

Artifact directory: `results/gnn_retraining_20261017/model_seed42/`.

| Item | Recorded Result |
| --- | --- |
| Training status | `completed`, `smoke_only=false` |
| Checkpoint | `best.pt`, selected only by minimum validation loss |
| Best epoch | 71 of 150 |
| Epoch-1 train / validation loss | 1.38571610 / 0.94109371 |
| Best validation loss | 0.4555501366655032 |
| Independently recomputed best validation loss | 0.4555501366655032 |
| Epoch-150 train / validation loss | 0.34945716 / 0.49520541 |
| Strict checkpoint load | 53 tensors; all finite |
| Test labels or test inference | None |

Validation did not improve after epoch 71, despite further training-loss
reduction. The selected checkpoint is not the final epoch. This is not a proof
of convergence. Training samples contrastive negatives, whereas validation uses
all negatives; the absolute train/validation loss gap is not a like-for-like
generalization estimate.

## Validation Edge Diagnostics

The model was scored only on the 12 validation instances already used for
checkpoint selection. These are selection-set diagnostics, not an unbiased test
estimate. Directed teacher-route edges include depot arcs. Self-loops are
excluded from candidate edges. Micro-aggregation pools integer counts across
instances: 2,005 positive edges and 301,800 candidate edges.

The thresholds below are existing solver settings, not tuned in this run.

| Threshold | Teacher Edges Retained | Edge Recall | Candidate Edges Retained | Edge Precision |
| --- | --- | --- | --- | --- |
| 0.003 | 2003 / 2005 | 99.9002% | 34.0848% | 1.9472% |
| 0.01 | 2003 / 2005 | 99.9002% | 29.5997% | 2.2422% |
| 0.05 | 1994 / 2005 | 99.4514% | 23.2707% | 2.8392% |

Recall refers to the frozen ALNS teacher edges, not optimal edges. At threshold
0.01, the two missed arcs occur in `SYN_VALIDATION_C_200_001` and
`SYN_VALIDATION_R_200_001`. All per-instance counts are in `audit.json`.
Edge retention is not the fraction of local-search moves actually explored.
These results do not reproduce or establish the historical 98.74% pruning claim.
Weighted-BCE scores are not established calibrated probabilities.

## Provenance and Rechecking

| File / Source | SHA-256 |
| --- | --- |
| Manifest | `8eb73a263102615f2ea3cab0dc9b76f0f5e6e90e475e5c8aa7fbb1a03f25b7d9` |
| Frozen teacher and trainer source | `948698b77671d6bbff31763f626f437e9594b64d948c545f14082d2974da437a` |
| New selected checkpoint | `365de53beba09097d1176a8b102ced8d6d97311f5a3ac82186b116d3290e1b97` |

`training.json` records all 60 target hashes, train/validation names, model hash
and environment. `history.csv` records every epoch. Source snapshots are stored
beside the dataset and model. The artifact script `audit_training.py` revalidates
these inputs, selects the CSV minimum independently, reloads the checkpoint,
recomputes validation loss and saves `model_seed42/audit.json` exclusively.

Run from the repository directory with `PYTHONPATH=src`. The exact training
commands are in [the handoff](antigravity_handoff.md). The existing output
directory must not be overwritten. The audit output also refuses overwrite;
preserve the original evidence if doing an independent repeat elsewhere.

## Remaining Work

1. Broaden timing validation after the cooperative-deadline repair and passing
   three-scale integration pilot. Historical overruns remain disclosed; their
   exact old delays were not reproduced during profiling.
2. Evaluate routing quality under the frozen protocol without selecting weights
   or settings by benchmark outcomes. Training/validation cover 100/200 customers;
   the later 400-customer integration smoke is not a generalization-quality study.
3. Reproduce independent classical and learning-augmented baselines under a
   shared objective/precision/timing contract before the main publication sweep.

Only one training seed was run. Synthetic teacher labels are not optimal labels,
and wall-clock-limited label regeneration is not guaranteed bit-identical.
No model promotion, routing-quality gain, historical provenance repair, or
publication-sweep readiness is claimed by this execution report.
