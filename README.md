# vrptw-neural-hybrid-optimizer

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Numba JIT](https://img.shields.io/badge/accelerated-Numba%20JIT-orange.svg)](https://numba.pydata.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-research%20reproducible-purple.svg)](docs/manuscript.pdf)

A hybrid **Deep Reinforcement Learning (Dueling DDQN)** and **Adaptive Large Neighborhood Search (ALNS)** solver with time-limited **MILP set partitioning** (HiGHS) for the Vehicle Routing Problem with Time Windows ($\text{VRPTW}$). Constraint feasibility checks and route cost evaluations are compiled to native machine code via **Numba JIT** kernels.

[Paper Manuscript](docs/manuscript.pdf) | [LaTeX Source](docs/manuscript.tex) | [Poster](posters/Poster_VRPTW_NCKHSV_2026.pdf) | [Official BKS Reference](data/reference/sintef_official_bks.json) | [Evidence & Verification Index](docs/evidence_index.md)

---

## 1. Mathematical Formulation

Given a complete directed graph $\mathcal{G} = (\mathcal{V}, \mathcal{A})$ where $\mathcal{V} = \{0, 1, \dots, n\}$ denotes the depot ($0$) and customer set $\mathcal{V}_c = \mathcal{V} \setminus \{0\}$, each customer $i \in \mathcal{V}_c$ has demand $q_i$, service duration $s_i$, and hard time window $[e_i, l_i]$.

### Hierarchical Lexicographic Minimization
$$\min_{x \in \Omega} \mathcal{F}(x) = \alpha \cdot |\mathcal{K}(x)| + \sum_{k \in \mathcal{K}(x)} \sum_{(i,j) \in \mathcal{A}} d_{ij} x_{ijk}, \quad \text{where } \alpha \gg \max_{(i,j)} d_{ij}$$
The solver strictly prioritizes fleet size minimization ($|\mathcal{K}(x)|$) before optimizing total travel distance ($\text{TD}$).

### $\mathcal{O}(1)$ Time-Window Feasibility via Forward Time Slack
By maintaining precomputed earliest arrival $E_i$, latest arrival $L_i$, and cumulative load $Q_i$ along partial tour segments, insertion feasibility of customer $u$ between $(i, j)$ is evaluated in constant time $\mathcal{O}(1)$ inside `Numba @njit(nogil=True, fastmath=True)` kernels:
$$\tilde{E}_u = \max\left(e_u, E_i + s_i + t_{iu}\right) \le l_u \quad \wedge \quad \tilde{E}_u + s_u + t_{uj} \le L_j$$

### Dueling DDQN Operator Selection & Set-Partitioning
At iteration $t$, the agent observes search telemetry $s_t \in \mathbb{R}^d$ and selects a composite destroy-repair operator pair $a_t = (d_{\text{op}}, r_{\text{op}}) \in \mathcal{A}_{\text{ops}}$ using a Dueling Double Deep Q-Network:
$$Q(s_t, a_t; \theta, \alpha, \beta) = V(s_t; \theta, \beta) + \left( A(s_t, a_t; \theta, \alpha) - \frac{1}{|\mathcal{A}_{\text{ops}}|} \sum_{a' \in \mathcal{A}_{\text{ops}}} A(s_t, a'; \theta, \alpha) \right)$$
Unique feasible routes generated during the search are hashed into an elite pool $\mathcal{R}$, periodically recombined by a set-partitioning MILP, solved by HiGHS under a per-query time limit:
$$\min_{y_r \in \{0, 1\}} \sum_{r \in \mathcal{R}} c_r y_r \quad \text{s.t.} \quad \sum_{r \in \mathcal{R}} a_{ir} y_r = 1 \quad \forall i \in \mathcal{V}_c$$

---

## 2. Evaluation

### Current results: wall-clock rerun (November 2026)

The revised manuscript reports one rerun in which every solver had the same wall-clock cutoff (10, 60 and 300 s) on 74 instances (56 Solomon-100, 12 Homberger-200, 6 Homberger-400) with five seeds. All solvers ran on the same machine, and all cases of an instance, seed and cutoff ran together. A run counts only if its solution was certified feasible on the original instance before the cutoff. The learned controllers start from random weights in every run, with nothing carried over between runs; only the GNN edge model is a frozen pretrained checkpoint. The analysis plan, and the rule for adopting the Guided Ejection Search phase, were fixed before any result was read.

Primary comparisons at 300 s. The fleet score is the mean over seed pairs of sign(NV of the comparator − NV of the proposed configuration), so a positive score favors the proposed configuration. Intervals are 98.33% (three comparisons). Wins/ties/losses count seed pairs from the proposed configuration's side. The distance gap is computed only where fleets matched, and a negative gap favors the proposed configuration.

| Comparator | Fleet score [98.33% interval] | Wins/ties/losses | Distance gap where fleets matched (%) |
| :--- | :---: | :---: | :---: |
| ALNS-Base | −0.027 [−0.065, 0.011] | 4/352/14 | +0.04 [−0.61, 0.66] |
| PyVRP-ILS 0.14.1 | +0.008 [−0.098, 0.117] | 37/299/34 | +0.95 (interval undefined) |
| NeuroLKH, adapted | −0.068 [−0.142, 0.033] | 16/313/41 | −3.57 (interval undefined) |

- **At 300 s, the proposed configuration did not differ detectably from any of the three comparators on fleet size.** Every interval contains zero.
- **Guided Ejection Search.** This classical route-minimization phase was added after test results had been seen, so its inclusion was not an independent test. A rule fixed in advance kept it: its fleet score against the same configuration without it was +0.062 [0.001, 0.123] at 98.75%. Leaving out the blocks that ran under high machine load gives [−0.014, 0.123].
- **Ablation.** On 18 instances, none of the eight primary factorial contrasts at 300 s excluded zero (99.38% intervals), so the ablation does not establish a benefit of the learned components at that budget.
- **Short budgets (descriptive, unadjusted 95% intervals).** At 10 s the proposed configuration used more vehicles than PyVRP-ILS (−0.522 [−0.654, −0.354]) and NeuroLKH-adapted (−0.573 [−0.690, −0.372]). At 60 s it did not differ detectably from either.
- **Micro-DDQN at 60 s, tested on new time-window variants.** The 60 s ablation suggested a benefit of the Micro-DDQN controller, so it was tested once more on 24 unused Homberger instances (time-window variants of the same layouts) under a protocol frozen before any cell ran. Against the rule-based policy, Micro-DDQN used fewer vehicles in the bare configuration (+0.208 [0.025, 0.450], 97.5% interval); in the full context the test did not detect a difference (+0.150 [−0.012, 0.372]). Without the blocks run at high machine load, neither interval is defined.
- **900 s.** This stage was started and ended unfinished, and no 900 s result is reported (see the README of the rerun records, Amendment 8).

The analysis code is [`scripts/analyze_ges_rerun.py`](scripts/analyze_ges_rerun.py). The compact records of the rerun are in [`results/rerun_records_20261102/`](results/rerun_records_20261102/) and those of the Micro-DDQN test in [`results/micro_replication_records_20261110/`](results/micro_replication_records_20261110/); each folder has a `PUBLISHED.md` describing its files. The full per-cell outputs are available from the authors on request.

### Withdrawn results

Earlier versions of this README and of the manuscript reported comparisons at a fixed budget of 2000 iterations, with Wilcoxon tests, and claimed significant fleet reductions on some Homberger-400 instances. A fixed iteration count does not give solvers equal computing time, so the revised manuscript withdraws those results. They should not be cited or compared with the rerun. The raw files remain in `results/ultimate-publication-suite/` and `results/extended_anytime_300s/` for the record.

---

## 3. Repository Architecture

```text
vrptw-neural-hybrid-optimizer/
├── src/
│   └── vrptw/
│       ├── numba_kernels.py          # @njit O(1) TW forward slack & capacity feasibility
│       ├── operators.py              # Shaw, worst-cost, string removal & regret-k repair
│       ├── rl.py                     # Dueling DDQN network, replay buffer & state encoder
│       ├── pool.py                   # Elite route-pool hasher and route manager
│       ├── solvers.py                # ALNSSolver and HybridDDQNSolver implementations
│       ├── gnn.py & train_gnn.py     # Graph Attention Network (GAT) edge candidate filter
│       ├── benchmark_suite.py        # Independent cold-start task runner
│       ├── sweep_statistics.py       # Registered bootstrap & paired statistical estimands
│       ├── ortools_baseline.py       # Google OR-Tools constraint solver baseline
│       └── pyvrp_baseline.py         # PyVRP modern ILS comparative baseline
├── scripts/
│   ├── run_paper_benchmarks.py       # Multi-seed benchmark suite runner
│   ├── compute_paper_statistics.py   # Wilcoxon signed-rank + Binomial Sign + Bonferroni
│   ├── analyze_revision.py           # Revision sweep analysis with missing-data bounds
│   ├── generate_latex_tables.py      # Automated Table III, IV, V export for LaTeX
│   ├── make_paper_tables.py          # Unified publication table formatter
│   └── audit_paper_integrity.py      # Artifact hash & reproducibility verification
├── data/
│   ├── reference/                    # Official SINTEF BKS reference files (JSON)
│   ├── Solomon/                      # 56 Solomon (N=100) benchmark instances
│   └── Gehring_Homberger/            # Homberger 200- and 400-customer benchmark instances
├── results/
│   ├── ultimate-publication-suite/   # Recorded iteration-budgeted publication CSVs
│   ├── extended_anytime_300s/        # Archived anytime observations (through 300s)
│   ├── phase2_loco_ablations/        # Archived component ablations
│   ├── loco_200/                     # Archived 200-customer LOCO records
│   └── task5_loco_gec/               # Archived GEC ablation records
├── docs/
│   ├── manuscript.tex                # IEEE Access paper manuscript LaTeX source
│   ├── manuscript.pdf                # Compiled paper PDF
│   └── resubmission_protocol.md      # Protocol contract, baselines, and timing gates
└── tests/                            # Comprehensive unit, integration, and regression tests
```

---

## 4. Reproducibility & Quickstart

### Prerequisites
Requires Python 3.11 or 3.12 and [`uv`](https://github.com/astral-sh/uv). PDF compilation requires `pdflatex`.

```bash
# 1. Install pinned dependencies in isolated virtualenv
uv sync --extra dev

# 2. Run full test suite (117+ tests)
uv run pytest
```

### Reproducing & Verifying Benchmark Statistics

To verify reported statistics and tables directly from the recorded benchmark outputs without requiring multi-hour recomputations:

```bash
# 1. Integrity auditor: checks the earlier fixed-iteration tables, not the rerun (see docs/evidence_index.md)
uv run python scripts/audit_paper_integrity.py

# 2. Analysis of the November 2026 wall-clock rerun (needs the rerun records, not yet published)
uv run python scripts/analyze_ges_rerun.py
```

`scripts/analyze_revision.py` analyzes an earlier wall-clock sweep, whose cells ran at different machine speeds. The manuscript does not use it for any claim.

For the exact input files, scope distinctions, and audit limits, see the [Evidence & Verification Index](docs/evidence_index.md).

### Legacy fixed-iteration benchmarks

These commands reproduce the withdrawn fixed-iteration results. They are kept for the record and are not the paper's evaluation protocol.

```bash
# Fast smoke verification (representative instances, 3 seeds)
uv run python scripts/run_paper_benchmarks.py --mode quick --workers 4

# Full Homberger-400 evaluation (10 seeds, 2000 iterations per instance)
uv run python scripts/run_paper_benchmarks.py \
    --mode homberger400 \
    --solvers ALNS-Base Hybrid-DDQN \
    --seeds 42 43 44 45 46 47 48 49 50 51 \
    --iterations 2000 \
    --workers 4 \
    --out-dir results/paper_run_400

# Compute non-parametric statistics and generate LaTeX tables from the new run
uv run python scripts/compute_paper_statistics.py \
    --csv results/paper_run_400/benchmark_homberger400_raw.csv \
    --out-md results/paper_run_400/stats_report.md

uv run python scripts/generate_latex_tables.py \
    --csv results/paper_run_400/benchmark_homberger400_raw.csv
```
