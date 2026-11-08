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

All evaluations are executed under **strict independent cold-starts** starting from `build_greedy` in isolated temporary scopes, locking random seeds across $N_{\text{seeds}} = 10$. Significance is evaluated using two-sided non-parametric **Wilcoxon signed-rank tests** with rank-biserial correlation ($r_{\text{rb}}$) and Bonferroni correction:

| Benchmark Scale | Instance | BKS NV | ALNS-Base ($\mu \pm \sigma$) | Hybrid-DDQN ($\mu \pm \sigma$) | Wilcoxon $p$-value | Effect Size ($r_{\text{rb}}$) | Statistical Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Solomon ($N=100$)** | `RC101` | 14 | $15.00 \pm 0.00$ | $15.00 \pm 0.00$ | — | $0.00$ | Zero-gap fleet saturation |
| **Homberger ($N=200$)** | `c1_2_1` | 20 | $20.00 \pm 0.00$ | $20.00 \pm 0.00$ | — | $0.00$ | NV-Floor reached; **$-2.84\%$ TD** ($p < 0.05$) |
| **Homberger ($N=200$)** | `r1_2_1` | 20 | $20.00 \pm 0.00$ | $20.00 \pm 0.00$ | — | $0.00$ | NV-Floor reached; **$-3.15\%$ TD** ($p < 0.05$) |
| **Homberger ($N=400$)** | **`c2_4_1`** | 10 | $13.00 \pm 0.00$ | **$12.20 \pm 0.42$** | **$p = 0.0078^{**}$** | $+1.00$ | **Significant fleet reduction** ($-0.80$ veh) |
| **Homberger ($N=400$)** | **`r2_4_1`** | 4 | $8.80 \pm 0.42$ | **$8.10 \pm 0.32$** | **$p = 0.0156^{*}$** | $+0.87$ | **Significant fleet reduction** ($-0.70$ veh) |
| **Homberger ($N=400$)** | **`rc2_4_1`** | 10 | $12.80 \pm 0.42$ | $12.50 \pm 0.53$ | $p = 0.3750$ | $+0.33$ | Moderate gain, not significant |

*(Significance levels: $^{*}p < 0.05$, $^{**}p < 0.01$. All runs strictly isolated with identical iteration budgets).*

### Key Empirical Findings
1. **200-Customer Scale (NV-Flattening & TD Dominance)**: Both solvers hit the same vehicle count floor ($NV=20$). Hybrid-DDQN delivers consistency with a **$1.75\%$ to $4.07\%$ TD reduction** at matched NV ($0\%$ to $20\%$ degradation rate vs $30\%$ to $70\%$ for ALNS-Base).
2. **400-Customer Scale (Suboptimal Graceful Degradation)**: DRL operator selection avoids deep local minima, achieving statistically significant fleet reductions over ALNS-Base on clustered and random instances (`c2_4_1`, `r2_4_1`).
3. **Computational Trade-off**: Hybrid-DDQN is a quality-maximizing solver trading search budget for solution quality ($1.5\times$ to $4\times$ run-time on Solomon-100, $1.3\times$ to $4.6\times$ on Homberger-200).

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
│       ├── ortools_baseline.py       # Google OR-Tools constraint solver baseline
│       └── pyvrp_baseline.py         # PyVRP modern ILS comparative baseline
├── scripts/
│   ├── run_paper_benchmarks.py       # Multiprocessing benchmark suite for IEEE publication
│   ├── compute_paper_statistics.py   # Wilcoxon signed-rank + Binomial Sign + Bonferroni
│   ├── generate_latex_tables.py      # Automated Table III, IV, V export for LaTeX
│   ├── make_paper_tables.py          # Unified publication table formatter
│   └── audit_paper_integrity.py      # Artifact hash & reproducibility verification
├── data/
│   ├── reference/                    # Official SINTEF BKS reference files
│   ├── solomon/                      # 56 Solomon (N=100) benchmark instances
│   ├── homberger_200/                # Gehring & Homberger (N=200) instances
│   └── homberger_400/                # Gehring & Homberger (N=400) instances
├── docs/
│   ├── manuscript.tex                # IEEE Access paper manuscript
│   └── manuscript.pdf                # Compiled paper PDF
└── tests/                            # 40+ unit and regression tests
```

---

## 4. Reproducibility & Quickstart

### Prerequisites
Requires Python 3.11 or 3.12 and [`uv`](https://github.com/astral-sh/uv). PDF compilation requires `pdflatex`.

```bash
# 1. Install dependencies
uv sync --extra dev

# 2. Run test suite
make test

# 3. Fast smoke verification (5 representative instances, 3 seeds)
python scripts/run_paper_benchmarks.py --mode quick --workers 4

# 4. Full publication benchmark on Homberger-400
python scripts/run_paper_benchmarks.py \
    --mode homberger400 \
    --workers 4 \
    --iterations 2000 \
    --output-dir results/paper_run_400

# 5. Compute non-parametric statistics and generate LaTeX tables
python scripts/compute_paper_statistics.py \
    --csv results/paper_run_400/benchmark_homberger400_raw.csv \
    --out-md results/paper_run_400/stats_report.md

python scripts/generate_latex_tables.py \
    --csv results/paper_run_400/benchmark_homberger400_raw.csv
```
