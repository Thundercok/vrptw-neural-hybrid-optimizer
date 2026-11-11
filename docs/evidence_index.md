# Evidence & Verification Index

This page is a guide to the evidence committed with the project. It adds no experiments and does not replace the protocols. Read the scope notes alongside every result.

## Start here

| What you want to inspect | Primary artifact | What it establishes |
| --- | --- | --- |
| Method and reported results | [Manuscript PDF](manuscript.pdf) · [LaTeX source](manuscript.tex) · [Supplement](supplementary_proofs.pdf) | The revised manuscript. Every result it reports comes from the two record folders below. |
| Wall-clock rerun (the paper's results) | [Rerun records](../results/rerun_records_20261102/) | Validated per-cell records of the November 2026 rerun at 10, 60 and 300 s, the analysis outputs behind every number in the paper, the analysis plan and all amendments, and the frozen solver snapshot. See its `PUBLISHED.md`. |
| Micro-DDQN test at 60 s | [Micro test records](../results/micro_replication_records_20261110/) · [Protocol](micro_replication_protocol.md) | The fresh-instance test of the Micro-DDQN controller, with its protocol frozen before any cell ran. |
| How results are worded | [Wording rules](rerun_wording_rules.md) | The wording fixed for each possible outcome before the rerun's results were read. |
| Response to the reviewers | [Response letter draft](response_to_reviewers_draft.md) | How each of the 23 reviewer concerns was addressed. |
| Solver implementation | [Core package](../src/vrptw/) | The current code. The rerun used the frozen snapshot in the rerun records, which `runtime_manifest.json` there identifies file by file. |
| Feasibility and regression tests | [Test suite](../tests/) | Automated checks for selected solver, feasibility, benchmark and regression behaviour. |
| Benchmark reference | [SINTEF BKS reference](../data/reference/sintef_official_bks.json) | Best-known values stored in the repository. The rerun does not read them during search. |

## Reproducing the paper's numbers

The rerun analysis is [`scripts/analyze_ges_rerun.py`](../scripts/analyze_ges_rerun.py). It reads the validator records and writes the results and tables that the manuscript uses. The Micro test has its own `analyze.py` in its record folder. The compact records are enough to recompute every reported number. The full per-cell outputs (routes, trajectories, supervisor receipts and logs, about 23 GB) are not in Git and are available from the authors on request.

A fresh benchmark run is a new experiment, not a reproduction of a recorded one. Keep the exact command, commit, input data, configuration, environment, seed and output files for any new run.

## Earlier material kept for the record

These artifacts predate the rerun. The revised manuscript does not use them for any claim.

- **Fixed-iteration benchmarks** ([combined CSV](../results/ultimate-publication-suite/combined_clean.csv), [ablations](../results/phase2_loco_ablations/ablation_raw.csv), [LOCO-200](../results/loco_200/loco_200_raw.csv), [GEC ablations](../results/task5_loco_gec/loco_gec_raw.csv)). Withdrawn, because a fixed iteration count does not give solvers equal computing time.
- **Anytime data** ([300 s CSV](../results/extended_anytime_300s/anytime_raw.csv)). Withdrawn with the fixed-iteration results.
- **First wall-clock sweep** ([records](../results/cutoff_clock_audit_20261029/run/records.csv), [analysis](../results/revision_analysis_20261101/results.json), via [`scripts/analyze_revision.py`](../scripts/analyze_revision.py)). The manuscript reports it only as a record (its Table 6): that sweep's hybrid read the best-known fleet size, and machine speed varied between its blocks.
- **[Resubmission protocol](resubmission_protocol.md)** and **[reviewer evidence matrix](resubmission_evidence_matrix_20261019.md)**. Planning documents from October 2026, superseded by the rerun's README and the response letter.

## What the integrity auditor checks

[`scripts/audit_paper_integrity.py`](../scripts/audit_paper_integrity.py) compares tables and selected text claims with stored data. Most of the tables it checks are the earlier fixed-iteration and anytime tables listed above, which the revised manuscript no longer contains, so its "zero discrepancies" result does not cover the rerun. The rerun's numbers are checked by recomputing them with `scripts/analyze_ges_rerun.py`.

Neither tool proves that every historical run was an independent cold start, that every method claim is correct, that the results have been reproduced by a third party, or that the solver is optimal or generally better than others.

## Reporting rule

When citing a result, name the artifact, benchmark scope, solver configuration, metric and aggregation. Keep fleet-size comparisons separate from distance comparisons; compare distance only where fleets matched. Report descriptive or non-significant outcomes as such.
