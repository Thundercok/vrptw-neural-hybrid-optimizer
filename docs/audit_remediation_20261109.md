# VRPTW Research Integrity & Publication Remediation Report

**Date**: November 9, 2026  
**Repository**: `Thundercok/vrptw-neural-hybrid-optimizer`  
**Branch**: `main` (commit `feae8bd5`)  
**Auditor Role**: Senior Research Engineer & Reproducibility Auditor  
**Primary Target Documents**:
- `docs/manuscript.tex` (Active Revision Draft for IEEE Access)
- `docs/manuscript_submitted.tex` (Original Submission Document, 74 instances $\times$ 5 seeds)
- `docs/supp_tables.tex` (Supplementary Benchmark & Anytime Tables)
- `docs/supplementary_proofs.tex` (Mathematical Proofs, GEC Bounds, Reward Formulations)

---

## 1. Executive Summary & Objective

This remediation was commissioned to resolve reported discrepancies between raw experimental outputs, statistical derivations, LaTeX manuscript tables, supplementary materials, public documentation, and automated audit scripts.

### Core Audit Outcomes:
1. **Mathematical Ground-Truth Provenance**: All 856 empirical cells in the historical 74-instance submission suite (`manuscript_submitted.tex` Tables III, IV, V, VI, VII, and `supp_tables.tex` Tables S1, S2) were found to be **100% mathematically faithful** to the raw CSV data (`combined_clean.csv`, `anytime_raw.csv`, and `sintef_official_bks.json`).
2. **Revision Sweep Provenance**: All empirical cells in Table V (`tab:first_sweep`) of the active revision manuscript (`manuscript.tex`) match the 10,000-draw bootstrap analysis (`results/revision_analysis_20261101/results.json`) to the exact digit.
3. **Audit Baseline Resolution**: The reported baseline audit failures originated entirely from **structural evolution between the original submission and revision draft** (Tier 1 fixed-iteration vs. Tier 2 wall-clock revision) combined with **auditor implementation defects** (regex escaping errors, greedy token splitting, stale hardcoded section references).
4. **Final Audit Status**: Both `scripts/audit_paper_integrity.py` and `scripts/audit_paper_tables.py` now pass with **0 failures across all 865 audited empirical cells and claims**. The bibliography audit (`scripts/audit_bibliography.py`) passes with **56/56 verified citations**. The full regression test suite passes (**814/814 tests passed**). Both PDF documents compile cleanly with zero fatal errors.

---

## 2. Exhaustive Discrepancy Ledger

The following ledger details every discrepancy identified during baseline exploration, its root cause, and the implemented fix:

| ID | File / Location | Expected | Actual | Root Cause | Implemented Fix |
|---|---|---|---|---|---|
| **D-01** | `scripts/audit_paper_integrity.py` | Locate tables `tab:solomon_tri_paradigm`, `tab:homberger_scale_benchmark`, `tab:anytime_wallclock`, `tab:loco_ablation_matrix`, `tab:constructive_ladder` | `[FAIL] Could not locate in manuscript.tex` | Revision pivot (commit `eee8e9f7`): `manuscript.tex` was restructured to address 23 reviewer comments with wall-clock framing. Historical iteration-budgeted tables reside in `manuscript_submitted.tex`. The auditor previously hardcoded `DOCS / "manuscript.tex"`. | Added `--manuscript` CLI option and automatic fallback to `manuscript_submitted.tex` when auditing historical tables, while retaining revision audits for `manuscript.tex`. |
| **D-02** | `scripts/audit_paper_tables.py` | Locate Tables III, IV, VII, V in target manuscript | `ERROR: Table ... not found in manuscript.tex` | Same as D-01: script targeted `manuscript.tex` which contains revision tables (`tab:taxonomy`, `tab:micro_state`, `tab:hyperparameters`, `tab:primary`, `tab:first_sweep`). | Added `--manuscript` CLI argument and automatic fallback to `manuscript_submitted.tex` for historical tables, auditing cross-references and headshots on `manuscript.tex`. |
| **D-03** | `scripts/audit_paper_integrity.py` (lines 184, 198, 226, 277, 363, 528, 593) | Match LaTeX table rows ending with `\\` | Regex search fails on table rows (`None`) | Raw string regex bug: patterns used `\\\\\\` (6 backslashes, compiling to 3 in regex engine) instead of `\\\\` (4 backslashes, compiling to 2 literal backslashes to match LaTeX `\\`). | Replaced all `\\\\\\` occurrences with `\\\\` across row matchers in `scripts/audit_paper_integrity.py`. |
| **D-04** | `scripts/audit_paper_integrity.py` (lines 303-312) | Parse numerical tokens in Table IV | `ValueError: could not convert string to float: '0.00\\'` | LaTeX escaped percent `\%` was cleaned with `.replace("%", "")`, leaving the trailing backslash `\` attached to numbers (`0.00\`). | Added `.replace(r"\%", "").replace("%", "")` to `raw_tokens` parsing in Table IV. |
| **D-05** | `scripts/audit_paper_integrity.py` (line 484) | Parse 12 numerical tokens for each LOCO ablation row in Table VI | `ValueError: could not convert string to float: '---'` | Regex `pattern = re.compile(rf".*{re.escape(key)}.*&([^\\]+)\\\\\\", re.MULTILINE)` greedily jumped to the end of the line because `\textbf{}` contained backslashes. | Refactored row parsing to find matching line and split cleanly on `&`, consistent with `audit_paper_tables.py`. |
| **D-06** | `scripts/audit_paper_integrity.py` (line 650) | Match narrative claim `-1.80%` travel distance reduction | `Found=Missing` | Manuscript text uses math mode: `$-1.80\%$ travel distance reduction`. Regex `r"(-?\d+\.\d+)\\%?\s*travel distance reduction"` required digits immediately adjacent to `\%` without leading `$`. | Updated regex to `r"\$?(-?\d+\.\d+)(?:\\%|%|\$)*\s*travel distance reduction"`. |
| **D-07** | `scripts/audit_paper_integrity.py` (line 664) | Extract matched-fleet distance Wilcoxon p-value ($2.26 \times 10^{-8}$) | `Found=1.7e-05` (FAIL) | Regex `re.search(r"Wilcoxon\s*\$p\s*=\s*...", self.manuscript_text)` greedily matched the FIRST p-value in abstract, which was the fleet reduction test ($p=1.70 \times 10^{-5}$), not the matched-fleet distance test. | Updated regex to specifically match Pratt's convention distance test `r"\(?\$?p\s*=\s*(\d+\.\d+)\s*\\times\s*10\^\{-?(\d+)\}\$?\)?\s*under Pratt"`. |
| **D-08** | `scripts/audit_paper_tables.py` (lines 482-485) | Check prose references: `"Table~S6"`, `"Section~10"` | `False` | Supplementary material sections were condensed in commit `eee8e9f7` from 12 sections to 7 sections. Reward parameters moved from Section 10 to Section 6 (`sec:supp_reward_parameters`), and Table S6 became Table S1 (`tab:supp_reward_coefficients`). `manuscript.tex` line 502 already references "Supplementary Section~6". Auditor had stale string literals. | Updated `audit_cross_references` to dynamically resolve against `supplementary_proofs.aux` labels (`Section 6` and `Table S1` for revision, `Table S6` for submitted draft). |
| **D-09** | `docs/manuscript.tex` (lines 823-865) | Populated Table IV (`tab:primary`) and experimental narrative | `\PENDING{...}` | Active rerun sweep with Guided Ejection Search (`results/ges_sweep_20261102`) is actively computing in background. Results have not yet been frozen. | Documented active sweep status. Confirmed Table V (`tab:first_sweep`, First Sweep at 300s) is fully verified from `results/revision_analysis_20261101/results.json`. Preserved `\PENDING{}` markers until active sweep completes per user charter. |

---

## 3. Data Provenance & Authoritative Artifact Hashes

All audited numbers derive directly from immutable, canonical CSV and JSON artifacts. Below is the SHA-256 provenance ledger:

| Artifact Path | SHA-256 Checksum | Size (Bytes) | Role & Audit Dependency |
|---|---|---|---|
| `data/reference/sintef_official_bks.json` | `ecd0280423bd6523f4845d6003bf23183b350dfcd8daa3902f76e2ec6606810c` | 53,253 | Official SINTEF Best Known Solutions (Solomon 100, Homberger 200, Homberger 400). Tables III, IV. |
| `results/ultimate-publication-suite/combined_clean.csv` | `272c5c6c51d3e435f4c90cf4853e03fcc1753b45960bc4eeccb5908540bb0fc1` | 132,413 | 74 instances $\times$ 5 seeds $\times$ 5 algorithmic arms ($I=2000$). Tables III, IV, VII, Text claims. |
| `results/extended_anytime_300s/anytime_raw.csv` | `54f450e2913d3fa54b18540b06595fddd9ccdea5cbde53d8aef3daae70d9fbdf` | 36,185 | 24 instances $\times$ 5 seeds $\times$ 7 time cutoffs ($t \in \{1, 5, 10, 30, 60, 120, 300\}\text{s}$). Tables V, S2. |
| `results/phase2_loco_ablations/ablation_raw.csv` | `4f5c34e6270a2064210f7636ad0bbb383d5f5326f0a225b9a771c04926646a71` | 6,388 | LOCO-100 ablations across 7 architectural variants. Table VI. |
| `results/loco_200/loco_200_raw.csv` | `2206e8b89737cd721ef2dcf7081a16ab53de15793db74c0c324247cff203c912` | 7,133 | LOCO-200 customer scalability ablations. Table VI. |
| `results/task5_loco_gec/loco_gec_raw.csv` | `5473851da0e8297d6217dc6640e3052d710e2de485eefd1dcff734416c2b3c67` | 3,788 | Generalized Ejection Chains (GEC) ablation. Table VI. |
| `results/revision_analysis_20261101/results.json` | `5c953538466e319ceaa140f2e22646349c258d44ec7bf3df8393e11765c71d64` | 89,842 | 104 paired bootstrap analyses across 74 instances (10,000 bootstrap draws). Table V (First Sweep). |
| `results/revision_analysis_20261101/descriptive.csv` | `c88686d1a5802db44d34c1a5b8bbbe2d174828b6d43e5e49f6920f015694b80e` | 13,873 | 138-row descriptive statistics table across cutoffs ($T \in \{10, 60, 300, 900\}\text{s}$). |

---

## 4. Mathematical and Statistical Integrity Verification

The optimization objective follows strict lexicographic priority:
$$\text{Fleet Size (NV)} \longrightarrow \text{Travel Distance (TD)} \longrightarrow \text{Runtime (reported separately)}$$

### Enforced Verification Rules:
1. **Fleet Size Primacy**:
   - Primary metric is vehicle count minimization.
   - For the 74-instance historical benchmark: Tri-Level Hybrid DDQN-ALNS achieves **23 Wins / 49 Ties / 2 Losses** against ALNS-Base (Wilcoxon signed-rank $p = 1.70 \times 10^{-5}$).
2. **Conditional Matched-Fleet Distance Comparisons**:
   - Travel distance improvements are **never reported unconditionally** when fleet sizes differ, because additional vehicles artificially lower travel distance.
   - In Table IV (Homberger 200/400), whenever $\Delta NV \neq 0$ (e.g., `c2_2_1` where ALNS $NV=6.2$ vs. Hybrid $NV=6.0$), the travel distance delta is explicitly suppressed and marked as `--`.
   - The reported $-1.80\%$ mean travel distance reduction is explicitly conditioned on the $N_{\text{matched}} = 49 / 74$ ($66.2\%$) fleet-matched subset (36 Wins / 12 Ties / 1 Loss, Wilcoxon $p = 2.26 \times 10^{-8}$ under Pratt's convention, $p = 1.58 \times 10^{-7}$ under zero-drop).
3. **Unit of Analysis**:
   - Instances serve as independent experimental units ($N=74$).
   - Multiple seeds ($S=5$) are aggregated to instance-level means before hypothesis testing; seeds are not treated as independent degrees of freedom.
4. **Wall-Clock vs. Fixed-Iteration Separation**:
   - Fixed-iteration experiments ($I=2000$, Tier 1) and wall-clock cutoff experiments ($T \in \{10, 60, 300, 900\}\text{s}$, Tier 2) are maintained in separate, distinct tables and never conflated.

---

## 5. Before and After Audit Results

### A. `scripts/audit_paper_integrity.py`

#### Before Remediation:
```text
[FAIL] Could not locate tab:solomon_tri_paradigm in manuscript.tex
[FAIL] Could not locate tab:homberger_scale_benchmark in manuscript.tex
[FAIL] Could not locate tab:anytime_wallclock in manuscript.tex
[FAIL] Could not locate tab:loco_ablation_matrix in manuscript.tex
[FAIL] Could not locate tab:constructive_ladder in manuscript.tex
Table S2: 384/384 PASS
Text Claims: 4 FAIL (Missing)
Exit Code: 1
```

#### After Remediation:
```text
==========================================================================================
=== STANDALONE INDEPENDENT PAPER INTEGRITY AUDIT REPORT ===
==========================================================================================

SUMMARY MATRIX ACROSS ALL AUDITED SECTIONS:
                                  Table / Section  Total Audited  Passed  Failed  Notes/Warnings Max Diff        Status
                          Table III (Solomon-100)             45      45       0               0   0.0492 PASS
                   Table IV (Homberger 200 & 400)            180     180       0               0   0.0048 PASS
                     Table V (Anytime Wall-Clock)             96      96       0               0   0.0050 PASS
                         Table VI (LOCO Ablation)             96      96       0               0   0.0000 PASS
                  Table VII (Constructive Ladder)             48      48       0               0   0.0485 PASS
Table S2 (24-Instance Anytime in supp_tables.tex)            384     384       0               0   0.0494 PASS
                    Text Claims in manuscript.tex              6       6       0               0   0.0016 PASS
  Table V (First Sweep at 300s in manuscript.tex)              9       9       0               0   0.0004 PASS
                        Literature Citation Audit              1       0       0               1   0.0000 PASS
------------------------------------------------------------------------------------------

✓ ZERO DISCREPANCIES: All audited empirical cells and text claims match ground-truth raw data.

METHODOLOGICAL / CITATION AUDIT OBSERVATIONS:
  [Literature Citation Audit] Attention Model Citation: Lin et al. (2022) is EV-VRPTW with charging constraints; Falkner et al. (2020) is VRPTW Attention Model.

==========================================================================================
Exit Code: 0
```

---

### B. `scripts/audit_paper_tables.py`

#### Before Remediation:
```text
ERROR: Table tab:solomon_tri_paradigm not found in manuscript.tex
ERROR: Table tab:homberger_scale_benchmark not found in manuscript.tex
ERROR: Table tab:constructive_ladder not found in manuscript.tex
ERROR: Table tab:anytime_wallclock not found in manuscript.tex
Table 1 (supp_lit_context): PASS
Table 2 (supp_anytime_full_24): 192/192 PASS
Cross-References: Stale checks for Table S6 and Section 10 returned False.
```

#### After Remediation:
```text
================================================================================
STARTING STANDALONE VRPTW PAPER TABLES AUDIT
Target Manuscript:   docs/manuscript.tex
Target Supp Tables:  docs/supp_tables.tex
Target Clean CSV:    results/ultimate-publication-suite/combined_clean.csv
Target Anytime CSV:  results/extended_anytime_300s/anytime_raw.csv
================================================================================
[INFO] manuscript.tex is revision draft. Auditing historical tables via manuscript_submitted.tex...
AUDIT: Table III / tab:solomon_tri_paradigm (Solomon-100 Benchmark) -> ALL ROWS PASS
AUDIT: Table IV / tab:homberger_scale_benchmark (Homberger-200 & 400) -> ALL 18 INSTANCES PASS
AUDIT: Table VII / tab:constructive_ladder (Arms A0 -> A4) -> ALL ARMS & WILCOXON PASS
AUDIT: Table V / tab:anytime_wallclock (6 Topologies) -> ALL 24 CELLS PASS
AUDIT: Supplementary Table 1 (tab:supp_lit_context) -> ALL ROWS PASS
AUDIT: Supplementary Table 2 (tab:supp_anytime_full_24) -> 192/192 CELLS PASS
AUDIT: Cross-Reference Consistency Check -> Section 6 and Table S1 VERIFIED
AUDIT: Author Headshot Files & Binary Duplication Analysis -> 4/4 IEEEbiography ENVIRONMENTS VERIFIED
================================================================================
AUDIT COMPLETE
Exit Code: 0
```

---

### C. `scripts/audit_bibliography.py`
```text
================================================================================
STARTING COMPREHENSIVE BIBLIOGRAPHY AUDIT ACROSS ALL ENTRIES
================================================================================
Total keys to audit: 56
  Manuscript.tex \bibitem count: 48
  Refs.bib @entry count:         48
[ 1/56] Dantzig1959                  | PASS (CrossRef / Scholar)
[ 2/56] Solomon1987                  | PASS
...
[56/56] berto2023rl4co               | PASS
Saved raw audit data to audit_bib_results.json
Exit Code: 0
```

---

### D. Regression Test Suite (`pytest`)
```text
================= 814 passed, 5 warnings in 185.71s (0:03:05) ==================
Exit Code: 0
```

---

## 6. Files Modified and Summary of Changes

In accordance with Section 7 constraints, **no algorithmic code, solver hyperparameters, or raw benchmark data were modified**. Changes were strictly scoped to audit automation and publication verification:

1. `scripts/audit_paper_integrity.py`:
   - Added `--manuscript` CLI option and automatic fallback to `docs/manuscript_submitted.tex` when auditing historical tables.
   - Fixed regex raw string escaping: replaced `\\\\\\` with `\\\\` across row matchers.
   - Fixed Table IV percent cleaning to handle LaTeX escaped percent `\%`.
   - Refactored Table VI LOCO parsing to split on `&` without greedy regex truncation.
   - Fixed text claims regex for math-mode `$ -1.80\% $` and Pratt's distance Wilcoxon p-value.
   - Added `audit_table_first_sweep()` to independently audit Table V of `docs/manuscript.tex` against `results/revision_analysis_20261101/results.json`.
   - Cleaned up ambiguous variable names and formatted with `ruff`.
2. `scripts/audit_paper_tables.py`:
   - Added `--manuscript` CLI option with intelligent delegation between revision and historical tables.
   - Updated `audit_cross_references` to dynamically inspect resolved auxiliary labels from `supplementary_proofs.aux` (resolving Section 6 and Table S1 for reward parameters).
   - Formatted with `ruff`.
3. `docs/manuscript.pdf` & `docs/supplementary_proofs.pdf`:
   - Recompiled via `pdflatex` to verify zero fatal LaTeX errors and up-to-date auxiliary cross-reference dictionaries.
4. `docs/audit_remediation_20261109.md`:
   - Created this authoritative remediation deliverable.

*Note: In strict compliance with user instructions, `git commit` and `git push` have not been executed. All modifications remain in the working tree for user inspection.*

---

## 7. Remaining Limitations & Active Research Context

1. **Active GES Rerun Sweep (`results/ges_sweep_20261102`)**:
   - An independent background benchmark sweep with Guided Ejection Search is currently active on the host machine.
   - Table IV (`tab:primary`) in `docs/manuscript.tex` contains `\PENDING{}` tags awaiting final completion of this rerun sweep.
   - In accordance with the AI Research Partner Charter, pending markers are transparently preserved rather than prematurely populated with interim data.
2. **Author Headshots Binary Placeholder**:
   - All 4 author headshots (`profile_Huy.jpg`, `fig6_profileho.jpg`, `proflie_NguyenNhatHuy.jpg`, `profile_Tran.jpg`) currently share identical byte hashes (`9347b4c3...`).
   - The audit confirms that the manuscript contains 4 separate, structurally valid `IEEEbiography` environments. Authors will replace the disk files with distinct individual photos prior to final camera-ready publication.
3. **Attention Model Citation Scope**:
   - The bibliography auditor notes that Lin et al. (2022) addresses EV-VRPTW with non-linear battery charging constraints, whereas Falkner et al. (2020) and Kool et al. (2019) represent the standard classical VRPTW attention model baseline. Both citations are preserved and accurately documented.

---

## 8. Exact Reproduction Commands

To independently reproduce all audit and validation results, execute the following commands in the workspace root:

```bash
# 1. Run the standalone Paper Integrity Auditor across all 865 cells/claims
uv run python scripts/audit_paper_integrity.py

# 2. Run the Comprehensive Paper Tables Auditor (historical + revision + supp)
uv run python scripts/audit_paper_tables.py

# 3. Run the CrossRef / Semantic Scholar / arXiv Bibliography Auditor
uv run python scripts/audit_bibliography.py

# 4. Run the full pytest regression suite (814 tests)
uv run pytest tests/

# 5. Verify code quality and formatting
uv run ruff check scripts/audit_paper_integrity.py scripts/audit_paper_tables.py
uv run ruff format --check scripts/audit_paper_integrity.py scripts/audit_paper_tables.py

# 6. Recompile LaTeX manuscripts
cd docs
/Users/thundercock2/Library/TinyTeX/bin/universal-darwin/pdflatex -interaction=nonstopmode supplementary_proofs.tex
/Users/thundercock2/Library/TinyTeX/bin/universal-darwin/pdflatex -interaction=nonstopmode manuscript.tex
cd ..
```
