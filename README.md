# vrptw-neural-hybrid-optimizer

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Numba JIT](https://img.shields.io/badge/accelerated-Numba%20JIT-orange.svg)](https://numba.pydata.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-research%20reproducible-purple.svg)](docs/manuscript.pdf)

A hybrid **Deep Reinforcement Learning (Dueling DDQN)** and **Adaptive Large Neighborhood Search (ALNS)** solver with exact **MILP Set-Partitioning** post-optimization for the Vehicle Routing Problem with Time Windows ($\text{VRPTW}$). Constraint feasibility checks and route cost evaluations are compiled to native machine code via **Numba JIT** kernels.

[Paper Manuscript](docs/manuscript.pdf) | [LaTeX Source](docs/manuscript.tex) | [Poster](posters/Poster_VRPTW_NCKHSV_2026.pdf) | [Official BKS Reference](data/reference/sintef_official_bks.json)

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
Unique feasible routes generated during the search are hashed into an elite pool $\mathcal{R}$, periodically refined via an exact MILP Set-Partitioning model:
$$\min_{y_r \in \{0, 1\}} \sum_{r \in \mathcal{R}} c_r y_r \quad \text{s.t.} \quad \sum_{r \in \mathcal{R}} a_{ir} y_r = 1 \quad \forall i \in \mathcal{V}_c$$

---

## 2. Empirical Verification under Strict Cold-Starts

All evaluations are executed under **strict independent cold-starts** starting from `build_greedy` in isolated temporary directory scopes. Standalone solver runs never share archives or warm-start states.

### Benchmark Protocols & Provenance

1. **Fixed-Iteration Comparative Benchmark** ($I = 2000$, $N_{\text{seeds}} = 10$, seeds 42–51):
   - Isolates search guidance and operator selection efficiency under matched iteration budgets.
   - Raw per-instance runs are archived in `results/ultimate-publication-suite/combined_clean.csv`.
   - Statistical significance is computed via two-sided non-parametric **Wilcoxon signed-rank tests** with rank-biserial correlation ($r_{\text{rb}}$) and Bonferroni multiple testing correction ($\alpha_{\text{adj}} = 0.0167$).

2. **Equal Wall-Clock Anytime Benchmark** ($T \in \{10, 60, 300, 900\}\text{s}$, $N_{\text{seeds}} = 5$, seeds 42–46):
   - Measures real-time optimization under strict elapsed-time deadlines, capturing runtime overheads (Numba JIT compilation, state encoding, MILP recombination).
   - Codified in [`docs/resubmission_protocol.md`](docs/resubmission_protocol.md), with full closed-sweep records archived in `results/cutoff_clock_audit_20261029/run/records.csv` and analyzed via `scripts/analyze_revision.py`.

### Representative Scale-Aware Comparison (Fixed-Iteration Benchmark)

| Benchmark Scale | Instance | BKS NV | ALNS-Base ($\mu \pm \sigma$) | Hybrid-DDQN ($\mu \pm \sigma$) | Wilcoxon $p$-value | Effect Size ($r_{\text{rb}}$) | Statistical Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Solomon ($N=100$)** | `RC101` | 14 | $15.00 \pm 0.00$ | $15.00 \pm 0.00$ | — | $0.00$ | Zero-gap fleet saturation |
| **Homberger ($N=200$)** | `c1_2_1` | 20 | $20.00 \pm 0.00$ | $20.00 \pm 0.00$ | — | $0.00$ | NV-Floor reached; **$-2.84\%$ TD** ($p < 0.05$) |
| **Homberger ($N=200$)** | `r1_2_1` | 20 | $20.00 \pm 0.00$ | $20.00 \pm 0.00$ | — | $0.00$ | NV-Floor reached; **$-3.15\%$ TD** ($p < 0.05$) |
| **Homberger ($N=400$)** | **`c2_4_1`** | 10 | $13.00 \pm 0.00$ | **$12.20 \pm 0.42$** | **$p = 0.0078^{**}$** | $+1.00$ | **Significant fleet reduction** ($-0.80$ veh) |
| **Homberger ($N=400$)** | **`r2_4_1`** | 4 | $8.80 \pm 0.42$ | **$8.10 \pm 0.32$** | **$p = 0.0156^{*}$** | $+0.87$ | **Significant fleet reduction** ($-0.70$ veh) |
| **Homberger ($N=400$)** | **`rc2_4_1`** | 10 | $12.80 \pm 0.42$ | $12.50 \pm 0.53$ | $p = 0.3750$ | $+0.33$ | Moderate gain, not significant |

*(Significance: $^{*}p < 0.05$, $^{**}p < 0.01$. Note on Travel Distance fairness: TD comparisons are reported only when vehicle counts match ($NV = NV_{\text{BKS}}$ or $NV_{\text{solver}} = NV_{\text{baseline}}$); extra vehicles provide artificial routing capacity that distorts distance comparisons).*

### Key Empirical Findings
1. **200-Customer Scale (NV-Flattening & TD Dominance)**: Both solvers converge to the same vehicle count floor ($NV=20$). Hybrid-DDQN advantage is characterized by consistency ($0\%$ to $20\%$ degradation rate vs $30\%$ to $70\%$ for ALNS-Base) and travel distance reduction of **$1.75\%$ to $4.07\%$** at matched NV.
2. **400-Customer Scale (Suboptimal Graceful Degradation)**: Deep reinforcement learning operator selection mitigates stagnation in severe local minima, achieving statistically significant fleet reductions over ALNS-Base on clustered (`c2_4_1`, $-0.80$ veh, $p=0.0078$) and random (`r2_4_1`, $-0.70$ veh, $p=0.0156$) instances.
3. **Computational Trade-off**: Hybrid-DDQN is a solution-quality-maximizing metaheuristic that trades computational budget for routing improvements ($1.5\times$ to $4\times$ runtime on Solomon-100, $1.3\times$ to $4.6\times$ on Homberger-200).

---

## 3. Repository Architecture

```text
vrptw-neural-hybrid-optimizer/
├── configs/                          # Experiment configs and parameter sweeps
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
│   ├── cutoff_clock_audit_20261029/  # Closed wall-clock sweep records and audits
│   └── revision_analysis_20261101/   # Processed revision statistics and bounds
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
# 1. Run revision analysis across the closed wall-clock sweep (74 instances, 4 cutoffs, 5 seeds)
uv run python scripts/analyze_revision.py

# 2. Inspect generated descriptive summaries and statistical bounds
head -n 20 results/revision_analysis_20261101/descriptive.csv
```

### Executing Independent Cold-Start Benchmarks from Scratch

To re-run the benchmark sweeps from scratch under strictly isolated environments:

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
