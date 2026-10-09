# VRPTW Neural Hybrid Solver

ALNS and DDQN-based solvers for the vehicle routing problem with time windows.

[Paper](docs/manuscript.pdf) | [LaTeX source](docs/manuscript.tex) |
[Poster](posters/Poster_VRPTW_NCKHSV_2026.pdf)

## Files

| Path | Contents |
| --- | --- |
| `src/vrptw/` | Solvers, configuration, and model training |
| `data/` | Benchmark instances and [reference values](data/reference/sintef_official_bks.json) |
| `scripts/` | Experiments, statistics, figures, tables, and audits |
| `results/` | Recorded publication CSVs; new runs are ignored by Git |
| `docs/`, `posters/` | Paper and poster sources, required assets, and final PDFs |
| `tests/` | Solver and regression test suites |
| `archive/` | Historical file index; experiment archives stay outside Git |

Start with `src/vrptw/__main__.py` for the solver CLI and
`scripts/research_pipeline.py` for the supported research workflow.

## Research

Requires Python 3.11 or 3.12 and `uv`; PDF compilation requires `pdflatex`.

```sh
uv sync --extra dev
make test
make research-quick      # Exploratory runs in results/research_pipeline/quick/
make research-tables    # Snippets from the recorded publication CSV
make research-figures
make research-audit
make research-paper     # PDF and Overleaf ZIP
```

The pipeline uses `run_paper_benchmarks.py`, `make_paper_tables.py`,
`generate_paper_figures.py`, `audit_paper_integrity.py`, and `docs/build_paper.py`.
Other scripts provide specific ablations, extended benchmarks, or model publishing
tools; they are not additional required setup steps.

`make benchmark` uses the same paper runner. For a larger suite:

```sh
make benchmark BENCHMARK_MODE=all BENCHMARK_ARGS="--workers 4 --iterations 2000"
```

Use `grand_master_benchmarker.py --help` for the extended 600-1000-customer
catalog and checkpoint/resume support. Ablation and anytime experiments remain
separate because they measure different quantities.

`make research-paper` generates `docs/overleaf_ieee_access.zip` locally.
`make poster` regenerates the poster HTML, PNG, and PPTX exports and copies the
deliverables to `../workspace-artifacts/`. Generated ZIP/HTML/PNG/PPTX exports
are ignored; only the final paper and poster PDFs are versioned.
Poster rendering dependencies are isolated in the `poster` dependency group;
`make poster` enables it automatically. Browser tools are not needed for solver tests.

Tables and figures use `results/ultimate-publication-suite/combined_clean.csv`.
To generate tables from another sweep:

```sh
uv run python scripts/research_pipeline.py --stage tables --sweep-csv path/to/combined.csv
```

Integrate generated table snippets into the manuscript before rebuilding it.
Use independent cold starts and equal budgets; compare distance at matched
fleet sizes. The last paper audit reported 39 table-format and text-claim
discrepancies. `research-all` stops at that failed audit.

## Web Demo Archive

The retired frontend, backend, browser tests, and deployment sources are preserved
at Git tag `v1.0-with-web-demo`. Restore them without switching the research checkout:

```sh
git archive --format=zip --output=/tmp/vrptw-web-demo.zip v1.0-with-web-demo
```

## Historical Files

Tag `research-history-before-cleanup` preserves old tracked outputs.
`archive/history-manifest.json` records their paths and SHA-256 checksums.
Export a folder with `git archive`:

```sh
git archive --format=zip --output=/tmp/vrptw-history.zip research-history-before-cleanup results
```

Local material removed in the workspace cleanup is preserved under
`../workspace-artifacts/repo-cleanup/`, with original relative paths and a
SHA-256 inventory in `manifest.json`. It includes visual experiments, redundant
dataset/model copies, poster exports, one-off diagnostic/manuscript scripts,
and `archive/local-experiments.zip`. Restore a script to its original path
before running it, since these scripts resolve inputs relative to the repo.
`config-manifest.json` inventories the retired editor/MCP configuration,
Firebase Dockerfile, and duplicate development launcher in the same archive.
`deep-manifest.json` inventories the unused frontend stack, legacy benchmark
wrappers, alternative poster asset generators, and consolidated tool configs.
`research-only-manifest.json` inventories the remaining retired environment
template and deployment/emulator scripts.

The main model checkpoint is `rl_alns_dr_v15.safetensors` at the repository root.
Canonical benchmark instances live in `data/Solomon/` and
`data/Gehring_Homberger/`; do not maintain separate sweep copies.

GNN retraining may need historical elite plans. Keep restored caches out of
cold-start benchmarks.

[MIT license](LICENSE). Use the manuscript's author list and title for citations.
