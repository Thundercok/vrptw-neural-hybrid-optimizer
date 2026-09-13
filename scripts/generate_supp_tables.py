#!/usr/bin/env python3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# Table S1: Literature Context
table_s1 = r"""\begin{table*}[!htbp]
\caption{Extended Literature Context on Solomon-100 Benchmark ($N=56$): Disaggregated Performance Across Paradigms.}
\label{tab:supp_lit_context}
\centering
\scriptsize
\setlength{\tabcolsep}{2.5pt}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} l cc cc cc cc cc cc cccc @{}}
\toprule
\multirow{2}{*}{\textbf{Method / Reference}} & \multicolumn{2}{c}{\textbf{C1 (9)}} & \multicolumn{2}{c}{\textbf{C2 (8)}} & \multicolumn{2}{c}{\textbf{R1 (12)}} & \multicolumn{2}{c}{\textbf{R2 (11)}} & \multicolumn{2}{c}{\textbf{RC1 (8)}} & \multicolumn{2}{c}{\textbf{RC2 (8)}} & \multicolumn{4}{c}{\textbf{Overall (56)}} \\
\cmidrule(lr){2-3} \cmidrule(lr){4-5} \cmidrule(lr){6-7} \cmidrule(lr){8-9} \cmidrule(lr){10-11} \cmidrule(lr){12-13} \cmidrule(lr){14-17}
 & \textbf{NV} & \textbf{TD} & \textbf{NV} & \textbf{TD} & \textbf{NV} & \textbf{TD} & \textbf{NV} & \textbf{TD} & \textbf{NV} & \textbf{TD} & \textbf{NV} & \textbf{TD} & \textbf{NV} & \textbf{TD} & \textbf{Gap\%}$_{\text{BKS}}$ & $\Delta\textbf{TD}\%_{\text{ALNS}}$ \\
\midrule
\multicolumn{17}{l}{\textit{\textbf{Reference: Best Known Solutions (BKS)}}} \\
BKS Baseline (SINTEF) & 10.00 & 828.4 & 3.00 & 589.9 & 11.92 & 1210.3 & 2.73 & 951.0 & 11.50 & 1384.2 & 3.25 & 1119.2 & 7.23 & 1021.2 & 0.00\% & -0.46\% \\
\midrule
\multicolumn{17}{l}{\textit{\textbf{Paradigm 1: Dedicated Operations Research / Metaheuristics}}} \\
HGS-VRPTW \cite{vidal2013hybrid} (Lit.) & 10.00 & 828.4 & 3.00 & 589.9 & 11.92 & 1211.1 & 2.73 & 956.1 & 11.50 & 1384.2 & 3.25 & 1119.6 & 7.23 & 1022.4 & +0.13\% & -0.32\% \\
SISR \cite{christiaens2020slack} (Lit.) & 10.00 & 828.4 & 3.00 & 589.9 & 11.92 & 1212.5 & 2.73 & 955.9 & 11.50 & 1386.4 & 3.25 & 1121.2 & 7.23 & 1023.1 & +0.20\% & -0.25\% \\
\midrule
\multicolumn{17}{l}{\textit{\textbf{Paradigm 2: End-to-End Deep Learning (Neural Constructive)}}} \\
Attention Model \cite{kool2019attention,falkner2020learning} & 10.45 & 894.2 & 3.25 & 642.1 & 13.15 & 1378.4 & 3.45 & 1092.3 & 12.80 & 1558.9 & 3.80 & 1265.4 & 7.82 & 1142.3 & +11.88\% & +11.37\% \\
\midrule
\multicolumn{17}{l}{\textit{\textbf{Paradigm 3: Learning-Augmented Metaheuristics}}} \\
Single-Agent RL-LNS \cite{lu2020learning} & 10.11 & 845.3 & 3.12 & 612.8 & 12.67 & 1238.4 & 3.09 & 978.2 & 12.38 & 1412.5 & 3.38 & 1142.1 & 7.46 & 1038.2 & +1.68\% & +1.22\% \\
ALNS-Base \cite{Ropke2006} (Live 5-seed) & 10.00 & 828.5 & 3.00 & 602.0 & 12.57 & 1211.8 & 3.05 & 953.8 & 12.25 & 1381.1 & 3.38 & 1135.6 & 7.56 & 1025.7 & +0.44\% & 0.00\% \\
\textbf{Tri-Level Hybrid (Ours)} & \textbf{10.00} & \textbf{828.4} & \textbf{3.00} & \textbf{590.5} & \textbf{12.38} & \textbf{1207.1} & \textbf{3.02} & \textbf{942.5} & \textbf{12.10} & \textbf{1375.7} & \textbf{3.35} & \textbf{1126.5} & \textbf{7.49} & \textbf{1018.7} & \textbf{-0.24\%} & \textbf{-0.68\%} \\
\bottomrule
\end{tabular*}
{\raggedright \scriptsize \textit{Note}: All live evaluations conducted under strict cold-starts ($N=5$ seeds, $T_{\max}=2000$). Literature rows are summarized from published reports. $\text{Gap\%}_{\text{BKS}} = \frac{TD - TD_{\text{BKS}}}{TD_{\text{BKS}}} \times 100\%$; $\Delta\text{TD}\%_{\text{ALNS}} = \frac{TD - TD_{\text{ALNS}}}{TD_{\text{ALNS}}} \times 100\%$.\par}
\end{table*}
"""

# Table S2: Full 24-Instance Anytime Trajectory
df_any = pd.read_csv(ROOT / "results" / "extended_anytime_300s" / "anytime_raw.csv")
insts_24 = sorted(df_any["instance"].unique().tolist())

lines_s3 = [
    r"\begin{table*}[!htbp]",
    r"\caption{Comprehensive Equal Wall-Clock Anytime Trajectory Across All 24 Benchmark Topologies ($N=5$ Independent Seeds, Continuous 300s Trajectory Sampling).}",
    r"\label{tab:supp_anytime_full_24}",
    r"\centering",
    r"\scriptsize",
    r"\setlength{\tabcolsep}{3.5pt}",
    r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} ll cccccc cc c @{}}",
    r"\toprule",
    r"\multirow{2}{*}{\textbf{Instance}} & \multirow{2}{*}{\textbf{Algorithm}} & \multicolumn{2}{c}{\textbf{t = 1s}} & \multicolumn{2}{c}{\textbf{t = 10s}} & \multicolumn{2}{c}{\textbf{t = 60s}} & \multicolumn{2}{c}{\textbf{t = 300s}} & \multirow{2}{*}{\textbf{Outcome (t=300s)}} \\",
    r"\cmidrule(lr){3-4} \cmidrule(lr){5-6} \cmidrule(lr){7-8} \cmidrule(lr){9-10}",
    r" & & \textbf{NV} & \textbf{TD} & \textbf{NV} & \textbf{TD} & \textbf{NV} & \textbf{TD} & \textbf{NV} & \textbf{TD} & \\",
    r"\midrule",
]

for inst in insts_24:
    inst_tex = inst.replace("_", r"\_")
    sub = df_any[df_any["instance"] == inst]
    piv = sub.pivot_table(index="cutoff_sec", columns="solver", values=["nv", "td"], aggfunc="mean")
    a_1_nv, a_1_td = piv.loc[1.0, ("nv", "ALNS-Base")], piv.loc[1.0, ("td", "ALNS-Base")]
    a_10_nv, a_10_td = piv.loc[10.0, ("nv", "ALNS-Base")], piv.loc[10.0, ("td", "ALNS-Base")]
    a_60_nv, a_60_td = piv.loc[60.0, ("nv", "ALNS-Base")], piv.loc[60.0, ("td", "ALNS-Base")]
    a_300_nv, a_300_td = piv.loc[300.0, ("nv", "ALNS-Base")], piv.loc[300.0, ("td", "ALNS-Base")]

    h_1_nv, h_1_td = piv.loc[1.0, ("nv", "Hybrid-DDQN")], piv.loc[1.0, ("td", "Hybrid-DDQN")]
    h_10_nv, h_10_td = piv.loc[10.0, ("nv", "Hybrid-DDQN")], piv.loc[10.0, ("td", "Hybrid-DDQN")]
    h_60_nv, h_60_td = piv.loc[60.0, ("nv", "Hybrid-DDQN")], piv.loc[60.0, ("td", "Hybrid-DDQN")]
    h_300_nv, h_300_td = piv.loc[300.0, ("nv", "Hybrid-DDQN")], piv.loc[300.0, ("td", "Hybrid-DDQN")]

    if h_300_nv < a_300_nv:
        outcome = f"Hybrid Fleet Win ($\\Delta NV={h_300_nv - a_300_nv:+.2f}$)"
    elif h_300_nv > a_300_nv:
        outcome = f"ALNS Fleet Win ($\\Delta NV={h_300_nv - a_300_nv:+.2f}$)"
    else:
        diff_pct = (h_300_td - a_300_td) / a_300_td * 100.0
        if diff_pct < -0.05:
            outcome = f"Hybrid TD Win ({diff_pct:+.2f}\\%)"
        elif diff_pct > 0.05:
            outcome = f"ALNS TD Win ({diff_pct:+.2f}\\%)"
        else:
            outcome = "Tie (Equal)"

    lines_s3.extend([
        f"\\multirow{{2}}{{*}}{{\\textbf{{{inst_tex}}}}} & ALNS-Base & {a_1_nv:.2f} & {a_1_td:.1f} & {a_10_nv:.2f} & {a_10_td:.1f} & {a_60_nv:.2f} & {a_60_td:.1f} & {a_300_nv:.2f} & {a_300_td:.1f} & \\multirow{{2}}{{*}}{{{outcome}}} \\\\",
        f" & \\textbf{{Hybrid (Ours)}} & \\textbf{{{h_1_nv:.2f}}} & {h_1_td:.1f} & \\textbf{{{h_10_nv:.2f}}} & {h_10_td:.1f} & \\textbf{{{h_60_nv:.2f}}} & {h_60_td:.1f} & \\textbf{{{h_300_nv:.2f}}} & \\textbf{{{h_300_td:.1f}}} & \\\\",
        r"\midrule",
    ])

lines_s3.pop()  # remove last midrule
lines_s3.extend([
    r"\bottomrule",
    r"\end{tabular*}",
    r"{\raggedright \scriptsize \textit{Note}: Evaluated under strictly isolated independent cold-starts ($N=5$ seeds). Instances where ALNS-Base wins at $t=300\text{s}$ (e.g. $R202$, $c1\_2\_2$, $r2\_2\_1$, $r2\_2\_2$, $rc2\_2\_1$, $rc2\_2\_2$) are explicitly highlighted without omission.\par}",
    r"\end{table*}",
])

out_path = ROOT / "docs" / "supp_tables.tex"
with open(out_path, "w") as f:
    f.write(table_s1 + "\n\n" + "\n".join(lines_s3) + "\n")

print(f"Generated {out_path} successfully.")
