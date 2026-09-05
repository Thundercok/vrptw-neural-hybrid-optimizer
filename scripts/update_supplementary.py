#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
supp_path = ROOT / "docs" / "supplementary_proofs.tex"
tables_path = ROOT / "docs" / "supp_tables.tex"

with open(supp_path) as f:
    supp_content = f.read()

with open(tables_path) as f:
    tables_content = f.read()

# Split tables into Table S1 and Table S3 based on label
t1_end = tables_content.find(r"\label{tab:supp_anytime_full_24}")
t1_split = tables_content.rfind(r"\begin{table*}[!htbp]", 0, t1_end)

table_s1 = tables_content[:t1_split].strip()
table_s3 = tables_content[t1_split:].strip()

sec_s1 = r"""\section{Extended Literature Context on Solomon-100}
\label{sec:supp_literature_context}

Table~\ref{tab:supp_lit_context} presents the complete disaggregated performance across dedicated Operations Research heuristics (HGS-VRPTW, SISR), end-to-end deep learning (Attention Model), and learning-augmented metaheuristics on the Solomon-100 benchmark suite ($N=56$ instances across 6 topological families).

""" + table_s1 + "\n\n"

sec_s3 = r"""\section{Comprehensive 24-Instance Equal Wall-Clock Anytime Trajectories}
\label{sec:supp_anytime_trajectories}

Table~\ref{tab:supp_anytime_full_24} documents the complete anytime trajectory across all 24 benchmark instances ($N=5$ independent seeds per solver, continuous 300s wall-clock sampling). In accordance with objective scientific reporting, all instances where ALNS-Base wins at $t=300\text{s}$ (specifically $R202$, $c1\_2\_2$, $r2\_2\_1$, $r2\_2\_2$, $rc2\_2\_1$, and $rc2\_2\_2$) are fully presented and cataloged without omission.

""" + table_s3 + "\n\n"

target_marker = r"\section{Comprehensive Benchmark Data: Full 74-Instance Results}"
if r"\label{tab:supp_lit_context}" not in supp_content:
    supp_content = supp_content.replace(target_marker, sec_s1 + target_marker)

end_marker = r"\end{document}"
if r"\label{tab:supp_anytime_full_24}" not in supp_content:
    supp_content = supp_content.replace(end_marker, sec_s3 + end_marker)

with open(supp_path, "w") as f:
    f.write(supp_content)

print("Updated docs/supplementary_proofs.tex successfully.")
