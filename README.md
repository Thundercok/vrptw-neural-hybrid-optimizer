# VRPTW Neural Hybrid Solver

ALNS and DDQN-based solvers for the vehicle routing problem with time windows.

[Paper](docs/manuscript.pdf) | [LaTeX source](docs/manuscript.tex) |
[Overleaf sources](docs/overleaf_ieee_access.zip) |
[Poster](posters/Poster_VRPTW_NCKHSV_2026.pdf)

## Files

| Path | Contents |
| --- | --- |
| `src/vrptw/` | Solvers, configuration, and model training |
| `data/` | Benchmark instances and [reference values](data/reference/sintef_official_bks.json) |
| `scripts/` | Experiments, statistics, figures, tables, and audits |
| `results/` | Recorded publication CSVs; new runs are ignored by Git |
| `docs/`, `posters/` | Paper and poster sources and outputs |
| `tests/` | Solver tests and optional browser tests |
| `src/backend/`, `src/frontend/` | Dispatch demo |
| `archive/` | Historical file index and local experiment outputs |

## Research

Requires Python 3.11 or 3.12 and `uv`; PDF compilation requires `pdflatex`.

```sh
uv sync --all-extras --all-groups
make test
make research-quick      # Exploratory runs in results/research_pipeline/quick/
make research-tables    # Snippets from the recorded publication CSV
make research-figures
make research-audit
make research-paper     # PDF and Overleaf ZIP
```

Tables and figures use `results/ultimate-publication-suite/combined_clean.csv`.
To generate tables from another sweep:

```sh
uv run python scripts/research_pipeline.py --stage tables --sweep-csv path/to/combined.csv
```

Integrate generated table snippets into the manuscript before rebuilding it.
Use independent cold starts and equal budgets; compare distance at matched
fleet sizes. The last paper audit reported 39 table-format and text-claim
discrepancies. `research-all` stops at that failed audit.

## Demo

Requires Node.js 20+. `npm ci && make dev-all` starts the API on port 8000 and
the frontend at http://127.0.0.1:5050/app.html. Anonymous demo access is enabled
by default; set `DEMO_AUTH_BYPASS=false` and configure Firebase for authentication.

## Historical Files

Tag `research-history-before-cleanup` preserves old tracked outputs.
`archive/history-manifest.json` records their paths and SHA-256 checksums.
Export a folder with `git archive`; extract the local-only archive separately:

```sh
git archive --format=zip --output=/tmp/vrptw-history.zip research-history-before-cleanup results
python -m zipfile -e archive/local-experiments.zip /tmp/vrptw-local-history
```

GNN retraining may need historical elite plans. Keep restored caches out of
cold-start benchmarks.

[MIT license](LICENSE). Use the manuscript's author list and title for citations.
