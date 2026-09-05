#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manuscript_path = ROOT / "docs" / "manuscript.tex"
tables_path = ROOT / "docs" / "generated_tables.tex"

with open(tables_path) as f:
    tables_content = f.read()

with open(manuscript_path) as f:
    tex = f.read()

def extract_generated_table(label):
    lbl = r"\label{" + label + "}"
    pos = tables_content.find(lbl)
    assert pos != -1, f"Label {label} not found in generated_tables.tex"
    start = tables_content.rfind(r"\begin{table*}", 0, pos)
    end = tables_content.find(r"\end{table*}", pos) + len(r"\end{table*}")
    return tables_content[start:end]

def replace_table_in_tex(tex_content, label, new_table):
    lbl = r"\label{" + label + "}"
    pos = tex_content.find(lbl)
    assert pos != -1, f"Label {label} not found in manuscript.tex"
    start = tex_content.rfind(r"\begin{table*}", 0, pos)
    end = tex_content.find(r"\end{table*}", pos) + len(r"\end{table*}")
    old_table = tex_content[start:end]
    print(f"Replacing {label} (old length {len(old_table)} chars -> new length {len(new_table)} chars)")
    return tex_content[:start] + new_table + tex_content[end:]

t3_new = extract_generated_table("tab:solomon_tri_paradigm")
t4_new = extract_generated_table("tab:homberger_scale_benchmark")
t5_new = extract_generated_table("tab:anytime_wallclock")
t6_new = extract_generated_table("tab:loco_ablation_matrix")
t7_new = extract_generated_table("tab:constructive_ladder")

tex = replace_table_in_tex(tex, "tab:solomon_tri_paradigm", t3_new)
tex = replace_table_in_tex(tex, "tab:anytime_wallclock", t5_new)
tex = replace_table_in_tex(tex, "tab:homberger_scale_benchmark", t4_new)
tex = replace_table_in_tex(tex, "tab:loco_ablation_matrix", t6_new)

# Update Figure 4 caption
fig4_old = r"\caption{Equal wall-clock anytime convergence curves: Mean travel distance ($TD$) over wall-clock time $t \in [1, 300]\text{s}$ across C101, R101, and RC101 ($N=5$ seeds, log-scale).}"
fig4_new = r"\caption{Equal wall-clock anytime convergence curves: Mean travel distance ($TD$) over wall-clock time $t \in [1, 300]\text{s}$ across representative 100- and 200-customer topologies (C101, R101, RC101, c1\_2\_1, r1\_2\_1, rc1\_2\_1, $N=5$ seeds, log-scale).}"
if fig4_old in tex:
    tex = tex.replace(fig4_old, fig4_new)
    print("✓ Updated Figure 4 caption")

# Update GEC observation in Section V-C
gec_obs_old = r"""    \item \textbf{Generalized Ejection Chains (GEC)}: Falling back to single-level direct customer insertion degraded primary fleet size on tight-window instance $r1\_2\_1$ ($NV=20.40^\dagger$ vs $20.00$, with 2 of 5 seeds failing to collapse the 21st vehicle) and increased travel distance on $rc1\_2\_1$ ($+186.89\text{ km}$), consistent with findings suggesting that multi-level customer displacement assists route elimination in dense temporal topologies."""
gec_obs_new = r"""    \item \textbf{Generalized Ejection Chains (GEC) \& Fleet Elimination Dynamics}: Evaluating GEC deactivation under contemporaneous paired cold starts ($N=5$ seeds, Table~\ref{tab:loco_ablation_matrix}) reveals the precise mechanisms governing route collapse:
    \begin{itemize}
        \item On mixed instance \textbf{RC101}, \textsf{Full} and \textsf{w/o GEC} achieve the \textbf{identical mean fleet count} of $NV=14.60$ across the 5 independent random seeds (both configurations eliminate the 15th vehicle in exactly 2 out of 5 seeds: seeds 43 and 44 for Full vs seeds 42 and 44 for w/o GEC), with comparable travel distance ($1697.89\text{ km}$ vs $1678.55\text{ km}$). The apparent advantage reported in earlier uncorrected drafts stemmed from comparing w/o GEC ($14.60$) against an out-of-sync iteration-matched baseline row ($15.00$).
        \item On \textbf{rc1\_2\_1} ($N=200$), \textsf{Full} achieves $NV=18.80$ (4/5 seeds at 19, 1/5 at 18) whereas \textsf{w/o GEC} reaches $NV=18.60$ (3/5 seeds at 19, 2/5 at 18). However, when \textsf{w/o GEC} eliminates vehicle 19 without multi-level chained displacement, its travel distance severely degrades to $4625.65\text{ km}$ and $4033.37\text{ km}$, yielding a massive $+186.89\text{ km}$ ($+5.03\%$) travel distance penalty relative to Full ($3904.95\text{ km}$ vs $3718.06\text{ km}$).
        \item On tight-window instance \textbf{r1\_2\_1}, GEC strictly prevents fleet inflation: \textsf{Full} locks onto $NV=20.00$ across all 5 seeds ($TD=4843.60\text{ km}$), whereas \textsf{w/o GEC} degrades to $NV=20.40^\dagger$ ($TD=4866.11\text{ km}$), with 2 of 5 seeds permanently stuck at 21 vehicles.
    \end{itemize}"""
if gec_obs_old in tex:
    tex = tex.replace(gec_obs_old, gec_obs_new)
    print("✓ Updated GEC empirical observations in Section V-C")

# Replace Table VII if already present, or insert if not
if r"\label{tab:constructive_ladder}" in tex:
    tex = replace_table_in_tex(tex, "tab:constructive_ladder", t7_new)
    print("✓ Replaced Table VII (Constructive Ladder)")
else:
    ladder_section = r"""
\subsection{Constructive Contribution Ladder: Isolating Learning vs.\ Heuristic Components (RQ3)}
\label{sec:constructive_ladder}

To complement the top-down LOCO sensitivity analysis and directly establish whether the RL hierarchy outperforms a purely heuristic stack, Table~\ref{tab:constructive_ladder} details the bottom-up \textbf{Constructive Contribution Ladder} ($A_0 \to A_4$) across all 74 benchmark instances ($N=56$ Solomon-100, $N=12$ Homberger-200, and $N=6$ Homberger-400) evaluated across identical 5 independent random seeds under strictly isolated cold starts ($T_{\max}=2000$). Each progressive rung adds a single architectural layer within the identical metaheuristic solver infrastructure:
\begin{itemize}
    \item $\mathbf{A_0 \to A_1}$ \textbf{(Classical Metaheuristic $\to$ Pure Heuristic Stack)}: Adding Generalized Ejection Chains and Set Partitioning Route Pool recombination (with zero reinforcement learning, $use\_rl=False, use\_op\_rl=False$) reduces mean fleet size across the 74 instances from $9.83$ to $9.70$ (Wilcoxon $W=169.0, p=2.55 \times 10^{-4}$) and slashes travel distance from $2019.5\text{ km}$ to $1959.1\text{ km}$ ($-3.00\%$, Wilcoxon $W=489.0, p=3.46 \times 10^{-6}$). This confirms that column generation and multi-level ejections provide a powerful heuristic baseline.
    \item $\mathbf{A_1 \to A_2}$ \textbf{(Pure Heuristic Stack $\to$ Multi-Mode Rule Scheduling)}: Introducing deterministic, rule-based macro mode transitions (switching between diversification, intensification, and pool recombination based on static stagnation counters) marginally reduces travel distance to $1952.9\text{ km}$ ($-0.32\%$, Wilcoxon $W=967.0, p=0.2278$) while maintaining identical fleet size ($NV=9.71$).
    \item $\mathbf{A_2 \to A_3}$ \textbf{(Rule Scheduling $\to$ Tri-Level Learning Hierarchy)}: Replacing static handcrafted rule thresholds with the Tri-Level MARL hierarchy (Macro Dueling DDQN, Micro Operator DDQN with Softmax-Entropy policy gating, and Learned Acceptance Criterion) adaptively manages search diversification. On large-scale Homberger-400 instances, Tri-Level MARL achieves the lowest fleet size ($NV=25.13$), preventing premature stagnation where rule-based heuristics become trapped in local minima.
    \item $\mathbf{A_3 \to A_4}$ \textbf{(Tri-Level MARL $\to$ Contrastive GNN Guidance)}: Augmenting the MARL hierarchy with offline Contrastive GNN spatial edge heatmaps prunes $98.74\%$ of search candidate arcs, achieving the lowest overall fleet count floor across the entire benchmark suite ($NV=9.68$ overall, and $NV=7.49$ on Solomon-100).
\end{itemize}

""" + t7_new + "\n"
    loco_end_marker = r"\section{Discussion and Managerial Insights}"
    assert loco_end_marker in tex, "loco_end_marker not found"
    tex = tex.replace(loco_end_marker, ladder_section + "\n" + loco_end_marker)
    print("✓ Inserted Section V-D and Table VII (Constructive Ladder)")

with open(manuscript_path, "w") as f:
    f.write(tex)

print("Saved updated docs/manuscript.tex successfully.")
