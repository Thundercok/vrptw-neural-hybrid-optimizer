# Research Pipeline

This repository is operated as a research project first, a reproducible
experimental pipeline second, and a web application third.

`main` is the single development branch. The short project map lives in the
root README; historical experiments and cached plans are preserved at the Git
tag `research-history-before-cleanup` (see `archive/README.md` for restoration).

## Outcome Priority

1. **NCKH report / paper**
   - Maintain `docs/manuscript.tex`, `docs/manuscript.pdf`, `docs/supp_tables.tex`,
     poster artifacts, and the Overleaf bundle as the main deliverables.
   - Every headline claim in the report should trace back to a raw CSV,
     generated table, benchmark script, or audit script.

2. **Reproducible research pipeline**
   - Keep benchmark execution, statistical testing, table generation, figure
     generation, and manuscript build steps runnable from stable commands.
   - Prefer small verified quick runs before expensive sweeps.
   - Treat app changes as downstream consumers of the solver, not as the source
     of research truth.

3. **Application demo**
   - The FastAPI/Vite dispatch portal demonstrates the solver.
   - The app is useful for presentation and inspection, but it should not block
     paper work unless an API regression breaks solver reproducibility.

## Daily Loop

Use this loop while developing algorithmic or paper changes:

```bash
make research-plan
make research-smoke
make research-quick
make research-tables
make research-paper
```

The first command prints the full intended pipeline without running it. The
smoke step is the cheapest correctness check. The quick benchmark step produces
fresh raw output under `results/research_pipeline/quick/`. By default, table
generation uses the aggregate publication sweep at
`results/ultimate-publication-suite/combined_clean.csv`; pass `--sweep-csv` to
`research_pipeline.py` when a new aggregate sweep is ready.

`make research-all` checks the recorded publication evidence and rebuilds the
paper. It deliberately excludes new exploratory benchmarks: `research-quick`
produces a separate screening dataset, not a replacement for the publication
sweep. Tables are generated snippets; check and integrate them into the
manuscript before presenting new numbers.

## Pipeline Stages

| Stage | Command | Purpose | Main outputs |
|---|---|---|---|
| Plan | `make research-plan` | Print all research commands in order | Terminal checklist |
| Smoke | `make research-smoke` | Verify solver import and baseline tests | Pytest result |
| Quick benchmark | `make research-quick` | Run representative paired experiments | `results/research_pipeline/quick/` |
| Tables | `make research-tables` | Regenerate LaTeX snippets from CSVs | `docs/tables/` or generated table files |
| Figures | `make research-figures` | Regenerate publication figures | `docs/figures/` |
| Paper | `make research-paper` | Compile and package manuscript | `docs/manuscript.pdf`, `docs/overleaf_ieee_access.zip` |
| Audit | `make research-audit` | Check manuscript claims against raw data | Audit terminal report |
| App | `make dev-all` | Run the demo portal | Local FastAPI/Vite services |

## Research Gates

Before treating a result as report-ready:

1. **Correctness gate**
   - Run `make research-smoke`.
   - Run focused tests for the touched solver module when applicable.

2. **Benchmark gate**
   - Use `scripts/run_paper_benchmarks.py --mode quick` for cheap screening.
   - Use the full Solomon/Homberger modes only after quick results justify the
     cost.
   - Compare travel distance only on matched fleet-size subsets.

3. **Reporting gate**
   - Regenerate tables from CSVs rather than editing numeric tables by hand.
   - Rebuild `docs/manuscript.pdf`.
   - Run `scripts/audit_paper_integrity.py` before presenting final numbers.

## Stable Entry Point

The `scripts/research_pipeline.py` driver is intentionally thin. It does not
replace existing benchmark, table, figure, or manuscript scripts. It only gives
the project one reliable top-level workflow:

```bash
python scripts/research_pipeline.py --stage plan
python scripts/research_pipeline.py --stage smoke
python scripts/research_pipeline.py --stage quick --iterations 200 --workers 1
python scripts/research_pipeline.py --stage paper
```

Use higher iteration counts and more workers only when moving from exploratory
work to final NCKH/report runs.
