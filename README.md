# VRPTW Neural Hybrid Solver

Research repository for a VRPTW NCKH report, reproducible experiments, and an
optional dispatch demo. All development is consolidated on `main`.

**Start here:** [Paper (PDF)](docs/manuscript.pdf) |
[Paper source](docs/manuscript.tex) |
[Overleaf bundle](docs/overleaf_ieee_access.zip) |
[Research workflow](docs/RESEARCH_PIPELINE.md) |
[Poster](posters/Poster_VRPTW_NCKHSV_2026.pdf)

## Project Map

| Location | Contents |
| --- | --- |
| `src/vrptw/` | Solver, configuration, training, and feasibility checks |
| `data/` | Solomon/Homberger instances and reference BKS data |
| `scripts/` | Experiment runners, statistics, figure/table generation, and audits |
| `results/` | Publication evidence and new, ignored experiment outputs |
| `docs/` | Manuscript, bibliography, figures, and paper build tools |
| `posters/` | Current poster and its generators |
| `tests/` | Solver regression tests and optional browser tests |
| `src/backend/`, `src/frontend/` | FastAPI/Vite demonstration app |
| `archive/` | History index, restoration instructions, and local experiment archive |

## Research

Requires Python 3.11 or 3.12 and `uv`. Paper compilation also requires
`pdflatex` on PATH; the supplied PDF and Overleaf ZIP can be read without it.

```sh
uv sync --all-extras --all-groups
make research-plan       # List available stages
make research-smoke      # Regression tests and a small synthetic solve
make research-quick      # New exploratory experiment; not publication evidence
make research-tables     # Tables from the recorded publication CSV
make research-audit      # Check manuscript claims against recorded data
make research-paper      # Compile PDF and package Overleaf sources
```

Use independent cold starts, equal experiment budgets, and matched fleet sizes
for distance comparisons. See [the workflow](docs/RESEARCH_PIPELINE.md) for inputs
and output locations. Benchmark caches are archived so they cannot silently
warm-start new runs.

## Optional Demo

Requires Node.js 20+. Run the API and frontend in separate terminals:

```sh
make dev                 # API: http://127.0.0.1:8000
npm ci
npm run dev -- --port 5050 --host 127.0.0.1
```

Open http://127.0.0.1:5050/app.html. The merged demo supports anonymous local
use; set `DEMO_AUTH_BYPASS=false` and configure Firebase for authenticated use.
Deployment configuration remains at the root for Docker/Vercel compatibility.

## History

Old experiments and duplicate publication bundles are preserved at Git tag
`research-history-before-cleanup`, indexed by original path and SHA-256 checksum
in `archive/history-manifest.json`. Previously local-only outputs are preserved
in `archive/local-experiments.zip`. [Archive instructions](archive/README.md) explain restoration.
The solver's GNN training tools may need the archived elite plans restored.

CI on `main` runs solver regression tests and builds the demo. Large benchmark
sweeps, browser/emulator tests, and deployment remain explicit commands.
See [validation notes](docs/VALIDATION.md) for the outstanding publication-audit
discrepancies; the manuscript has not been certified by that audit.

License: [MIT](LICENSE). Cite the authors and title from the manuscript when
using this research.
