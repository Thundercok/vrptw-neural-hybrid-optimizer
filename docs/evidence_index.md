# Evidence & Verification Index

This page is a navigation guide to the evidence already committed with the project. It does not add experiments, certify every manuscript claim, or replace the experiment protocols. Read the scope and limitations alongside every result.

## Start here

| What you want to inspect | Primary artifact | What it establishes |
| --- | --- | --- |
| Method and reported results | [Manuscript PDF](manuscript.pdf) · [LaTeX source](manuscript.tex) | The submitted research narrative and the tables/claims being discussed. |
| Fixed-iteration benchmark data | [Combined benchmark CSV](../results/ultimate-publication-suite/combined_clean.csv) | Archived per-instance benchmark data used by the publication tables. |
| Anytime benchmark data | [Anytime raw CSV](../results/extended_anytime_300s/anytime_raw.csv) | The committed anytime observations. The checked-in artifact is the 300-second dataset; it is not evidence of a completed 900-second sweep. |
| Revision sweep records | [Sweep records CSV](../results/cutoff_clock_audit_20261029/run/records.csv) · [Revision analysis JSON](../results/revision_analysis_20261101/results.json) | The committed sweep records across cutoffs (10, 60, 300, 900s) and 10,000-draw bootstrap analysis for Table V. |
| Ablation data | [Phase-2 ablations](../results/phase2_loco_ablations/ablation_raw.csv) · [LOCO-200](../results/loco_200/loco_200_raw.csv) · [GEC ablations](../results/task5_loco_gec/loco_gec_raw.csv) · [Ablation design](../results/ablation_design_20261019/) | Archived component-level experiment records and factorial design specifications. |
| Statistical and table integrity checks | [Paper integrity auditor](../scripts/audit_paper_integrity.py) | Code intended to compare manuscript tables/text claims with the committed benchmark artifacts and reference BKS. |
| Solver implementation | [Core package](../src/vrptw/) · [Benchmark runner](../scripts/run_paper_benchmarks.py) | Implementation and the fixed-iteration runner used to launch benchmark jobs. |
| Feasibility and regression tests | [Test suite](../tests/) | Automated checks for selected solver, feasibility, benchmark, and regression behaviours. |
| Benchmark reference | [SINTEF BKS reference](../data/reference/sintef_official_bks.json) | The reference best-known-solution values stored in this repository. |

## What can be checked from a clean checkout

1. Install the pinned environment with `uv sync --extra dev`.
2. Run the test suite with `uv run pytest`.
3. Run the artifact-to-manuscript integrity audit with `uv run python scripts/audit_paper_integrity.py`.
4. Inspect the raw CSVs linked above directly. The fixed-iteration runner can be invoked in a small smoke mode with `uv run python scripts/run_paper_benchmarks.py --mode quick --workers 4`.

A fresh benchmark run is a new experiment, not an automatic reproduction of a historical result. Preserve the exact command, commit, input data, configuration, environment, seed, and output files for any new run.

## Important scope distinctions

### Archived results versus proposed resubmission work

[The resubmission protocol](resubmission_protocol.md) explicitly labels itself a preparation draft, not a completed replication or permission to launch the full suite. Its proposed evaluation contract, pilot reports, and baseline requirements must not be described as a completed publication-scale rerun.

The repository currently contains an anytime artifact at `results/extended_anytime_300s/anytime_raw.csv`. The README previously pointed to `results/cutoff_clock_audit_20261029/run/records.csv` and a 900-second cutoff, but that path is not present in the current checked-in `results/` directory. Treat the committed 300-second artifact as the available evidence unless the missing records are added with their provenance.

### Revision sweep analysis and lightweight inputs

`scripts/analyze_revision.py` processes the closed wall-clock sweep records and factorial ablation. The required lightweight inputs (`results/cutoff_clock_audit_20261029/run/records.csv`, `results/alns_greedy_fix_20261101/run/records.csv`, `results/reference_blind_t300_20261101/run/records.csv`, and `results/ablation_design_20261019/`) as well as the processed outputs (`results/revision_analysis_20261101/`) are committed directly to the repository (~10 MB total). Any fresh clone can execute:

```bash
uv run python scripts/analyze_revision.py
```

to reproduce the 104 paired comparisons and 138 descriptive rows. The underlying multi-gigabyte raw worker traces and shard logs (5.6 GB) remain archived outside Git due to repository size limits.

### What the integrity auditor does not prove

The integrity auditor is a useful consistency check between selected manuscript claims/tables and stored data. It is not a proof that:
- every historical run was a true independent cold start;
- every historical checkpoint has complete training provenance;
- every method claim or theoretical guarantee is correct;
- the benchmark suite has been independently reproduced by a third party;
- the solver is globally optimal or universally superior.

Those questions require their own evidence and should be stated with the relevant scope and limitations.

## Detailed research audit trail

- [Resubmission protocol](resubmission_protocol.md): proposed evaluation contract, pilot status, timing/baseline requirements, and known limitations.
- [Reviewer evidence matrix](resubmission_evidence_matrix_20261019.md): a detailed internal ledger mapping 23 reviewer concerns to evidence and remaining actions. Its own status statement says the concerns were not all closed; it is an audit/planning document, not proof that every requested revision was completed.
- [Paper integrity auditor](../scripts/audit_paper_integrity.py): executable consistency checks for selected tables, claims, references, and stored benchmark inputs.

## Reporting rule

When citing a result, identify the exact artifact, benchmark scope, solver/configuration, metric, and aggregation. Separate fleet-count comparisons from travel-distance comparisons; distance should only be compared under the stated matched-fleet rule. Report exploratory or non-significant outcomes as such, and do not convert a pilot or a protocol proposal into a completed performance result.
