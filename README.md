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

### Wall-Clock Pilot

```sh
uv run python scripts/run_benchmark_pilot.py --output-dir results/resubmission_pilot --time-limit 10
```

This runs six fresh processes sequentially: ALNS and hybrid **without GNN**,
one seed on 100/200/400-customer instances. The output directory must be new.
Each run records its routes, exact-cover check, requested/effective configuration,
seed, source and input hashes, thread settings, timing, and raw logs. The pilot
also saves a source snapshot. It is a harness check, not publication evidence.

`scripts/benchmark.py` defaults to `--budget-mode wall-clock`: iteration and
stagnation caps do not stop the main search. Existing iteration parameters still
control search schedules and tail batch sizes; unused tail time goes to fixed-NV
polishing. `--budget-mode capped` retains the former stopping policy. Budgets
cover `solve()`, including construction and inference, but exclude imports,
solver construction and checkpoint loading. Operations can overrun a deadline;
the pilot flags deviations beyond 0.5 seconds or 5%, whichever is larger.
Late-returned solutions are not results at an earlier cutoff. No run is padded
with sleep. GNN loading requires an explicit `--gnn-model PATH`.
Other ablation labels and modern baselines still need protocol validation before
a resubmission suite is launched. Historical CSVs are not modified.

With an explicit checkpoint, `--gnn-model PATH` adds full-GNN runs and preserves
a model snapshot alongside the source snapshot. See
[the resubmission protocol](docs/resubmission_protocol.md) for the recovered
checkpoint's provenance, known limitations, candidate baselines and launch gates.

`--include-ortools` adds three external-baseline runs (12 total with a GNN
checkpoint). Single runs use `scripts/benchmark.py --ablation ortools` with
wall-clock mode only. The adapter charges model construction to the solve budget,
records CP seed/backend parameters and retains only original-feasible incumbents
captured before cutoff. Its integer grid is an approximation, not exact double
arithmetic. See [the OR-Tools contract audit](docs/ortools_contract_20261018.md).

Install the optional pinned comparator with `uv sync --locked --extra dev --extra baselines`.
`--include-pyvrp` adds three PyVRP 0.14.1 ILS runs (15 total with GNN and OR-Tools);
single runs use `scripts/benchmark.py --ablation pyvrp`. Model construction and
initialisation are charged to the absolute solve deadline. Only validated
pre-cutoff incumbents are selected, but non-preemptible calls may return late.
The [PyVRP contract report](docs/pyvrp_contract_20261018.md) records the 15-run
pilot, approximation limits and unfavorable as well as favorable observations.

The independent learning comparator is `neurolkh`, an explicitly labeled CPU
adaptation with pinned source/checkpoint, original-route validation and internal
cold fleet-reduction restarts. Prepare its separate local assets with
`python scripts/setup_neurolkh.py --root results/external/NeuroLKH`; no upstream
code or weights are vendored. Add `--neurolkh-root results/external/NeuroLKH`
to the pilot for 18 total runs with all branches, or use it with
`scripts/benchmark.py --ablation neurolkh`. Backend artifacts are exported beside
JSON, including on failure. See [the NeuroLKH contract report](docs/neurolkh_contract_20261018.md)
for the verified pilot, author-configuration differences, OOD/training-provenance
limits and unresolved redistribution conditions. This is not a literature-score
replication or evidence of stable hybrid/GNN superiority.

For clean GNN retraining, use `python -m vrptw.gnn_training` with an explicit
manifest. The legacy `train_gnn.py` discovery mode is not a held-out training
protocol. See [the training handoff](docs/antigravity_handoff.md) for the prepared
48/12/74 split, teacher-generation commands and validation-only checkpoint selection.

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
