# Response to reviewers: working draft for Access-2026-45322

Working draft, not ready to send. Final text goes into the IEEE template
(concern / author response / author action).

Status tags:
- **DONE**: the manuscript edit exists in `docs/manuscript.tex`.
- **DATA OK, TEXT TODO**: evidence exists, the manuscript text is not rewritten yet.
- **OPEN**: evidence or decision still missing.

Numbers below come from the closed sweep plus the reference-blind T300 run. They change
if the GES variant replaces the current solver. A single GES rerun is in progress with its
analysis and adoption rule fixed in advance: see `results/ges_sweep_20261102/README.md`.

## Must fix before sending

Manuscript edits of 2 November are in `docs/manuscript.tex`, uncommitted, and still need copying to Overleaf.

1. **GNN training description.** DONE. Now 48 training and 12 validation synthetic instances at N = 100
   and 200, ALNS teacher at 10 s, no test instances.
2. **Recall figures 95.8%, 91.4%, 78.2%.** REMOVED, because they cannot be traced to the registered checkpoint.
   Replaced by validation-set figures, labelled as optimistic. Recall by test size is still open (R2.5).
3. **Firewall sentence.** DONE. States that test results motivated evaluating GES, and how the development
   set relates to the test set.
4. **Stale claims.** PARTLY DONE. Conclusion, limitations and platform are fixed. The Results sections still
   hold old tables and 23W/49T/2L, p=1.7e-5, T_max=2000. They wait for the T300 numbers. The Conclusion has a visible
   `[RESULTS PENDING]` marker that must not reach submission. Table A4 still says "Contrastive GNN".
5. **Instance-family heuristic.** DONE, disclosed. It stays in the solver because the rerun is running.
6. **Machine speed varied.** DONE, disclosed in the setup section. Rerun block counts and the load sensitivity
   result are still to add.
7. **Granular neighbourhood was misdescribed.** FIXED. The text said k = 25 spatiotemporal neighbours with an affinity
   equation. The code uses 15 nearest customers by distance. The equation is removed.
8. **Pruning claim (97.5-98.7%, 98.74%).** REMOVED. Those figures match k = 5, which is neither the text's k = 25 nor the
   code's k = 15, and `docs/gnn_retraining_20261017.md` says the registered model does not establish them.
9. **Hardware text was wrong.** FIXED. It said 32 GB, macOS 15 and pinned processes. The machine is an M1 with 16 GB
   on macOS 26.5.2, and processes are not pinned.
10. **Author to confirm.** (a) Data availability. The old link returned 404, so manuscript and supplement now cite `Thundercok/vrptw-neural-hybrid-optimizer`. "Archived on Zenodo" was removed: no such archive is known to the author. Say in the response that the statement was corrected. Before submission, push the code and publish the records, checkpoint and logs, because `results/` is gitignored and the repository was last pushed on 23 October. (b) That the "synthetic pilot"
    calibration in Supplementary Section 10 happened as described: I could not verify it from the code.

11. **ALNS-Base was misdescribed.** FIXED. The text called it a faithful Pisinger and Ropke reproduction with a roulette wheel, sigma3 = 13 and cooling 0.9995. The code uses Thompson sampling over 65 pairs, sigma3 = 3 and cooling 0.99975. Say so in the response (R3.3).
12. **Hyperparameter table and blending equation did not match the code.** FIXED from `config.py` and `rl.py`: macro state 12 (figure said 13), macro lr, buffer and batch, blend weights 0.55/0.20/0.35, no standardization before the gate, ungated UCB term, and the set-partitioning limit min(30, 4 + 0.05N) s instead of 4 s.
13. **"Synthetic pilot" calibration.** REWORDED in manuscript and supplement: no calibration log was retained. The author can restore the claim only with a record of it. This replaces item 10(b).
14. **Supplement rebuilt.** DONE except per-instance tables, which wait for the rerun. REMOVED because no source could be traced or the data were iteration-budget results: Section 5 sensitivity table (its nominal 0.35/0.65 was not the code), Section 6 PCA, Section 7 literature comparison (family-level rows could not be traced), Section 8 per-instance tables, Section 11 variability, Section 12 anytime table. Tell the reviewers these were withdrawn and why.
15. **Main-text methods audited against the frozen code.** FIXED in `docs/manuscript.tex`:
    - Macro: modes a4 and a5 were swapped; DIVERSIFY is 1.35 destroy and 1.08 temperature, not 1.5 and 1.5.
    - Search phases were undescribed: a penalized first phase without LAC (up to 3,000 nominal iterations) and tail phases taking 20% of the budget. The old penalty multipliers were wrong.
    - Reward and potential omitted the 0.30 scale and used wrong potential coefficients (15 and 0.18). Micro exploration and reward were missing.
    - LAC: the feature vector was wrong, the label follows best distance only and not lexicographic F, and the latency claim of under 0.05 ms was removed.
    - GEC: no beam (k = 25 and 15 were not implemented), no 0.5 s limit, and feasibility tests replay the route instead of using O(1) queries.
    - Set partitioning: per-query limits of 3, 4.7 and 8 s, at most 800 columns, a set-covering fallback, up to min(60, 28 + N/10) routes per customer (not 3).
    - Ablation: low levels of Macro and Micro are rule policies, not removals.
    Implication for R3.5 and R3.7: state that LAC does not act in the first phase, and that GEC does not use O(1) checks. Whether LAC fires enough at 300 s should be measured from the rerun's counters.
16. **Proofs corrected.** DONE. The two-stage set-partitioning theorem was removed because the solver does not use that formulation, and its conditioning claim had no basis. The GEC complexity proof now describes the code (no beam, O(m K^3 L^4)). The behavior policy in the Bellman section is corrected to epsilon-greedy. The forward-slack condition was wrong as an if-and-only-if: the exact condition is max(0, delta - W_{i+1}) <= F_{i+1}, fixed in manuscript and supplement. Algorithm S1 and the reward table, now with Micro coefficients, follow the code.

17. **Findings from the dry runs of 2 November, development instances only.** The sweep CLI uses a nominal 10,000 iterations and patience 2,500, not the Config defaults of 5,000 and 250. Corrected in the text. (a) LAC can be absent at 300 s: it is not consulted until the first phase ends, which needs 6,000 iterations or the fleet floor, and 10 of 18 dev100 runs did not reach 6,000. With GES and blind search the floor is the capacity bound, which is often unreachable, so the early exit may rarely fire. This can make the rerun's LAC contrast nearly empty. Measure it and say so in R3.5. The solver must not change. (b) At 10 s, GES and its JIT compilation take much of the budget: a 8 s dry run spent all of it there, and ALNS iterations at 10 s fell from 1,901 to 609 and from 7,567 to 1,021 on two instances. Report this with the 10 s results. (c) Set partitioning took 15.1 of 30 s in a dry run on a 100-customer instance.
18. **Checklist items still open.** A grammar pass was done on 3 November by reading the source, with no grammar tool; an author should still proofread it. References are in citation order; rerun the ordering if citations change. No video. Byline form only if the author list changes. Supplement must be uploaded with the final files. NV and TD were converted to upright notation on 3 November.
19. **Reference audit of 3 November.** Corrected against Crossref or the publisher: Lu et al. (wrong title and venue), Alvarenga et al. (wrong author, title, issue, pages), Subramanian et al. (wrong authors, title, issue, pages), Rochat and Taillard, Turkes et al., Chen and Tian (title, pages), Vidal et al. (author initials), Auer et al. (issue). Syberfeldt and Back could not be found in Crossref or a web search and was replaced with Kallestad et al. 2023. Vidal et al. no longer supports the set-partitioning claim, and the taxonomy rows for L2I and Neural LNS were corrected from the papers. A second check the same day confirmed the other entries against Crossref, arXiv, publisher pages or indexes, and added the pages of Li et al. and the volume of Nazari et al. Gehring and Homberger rests on reference lists of other papers. The ICLR venue of Kool et al. and Schaul et al. and the edition of Toth and Vigo were not seen in a record. Still to check by hand: the pages of Khalil et al. (and its author order, since arXiv lists Dai first), Nazari et al., NeuroLKH and van Hasselt et al., and the SINTEF link, which refuses scripts.
20. **Amendment 5 of 3 November.** Load is sampled once a minute during the rerun, and two repeats at 300 s are registered before any result is read: without blocks that have a cell run at mean load above 8, and on measured blocks only. Report both with their block counts. Load during a run is unknown for about 450 cells at 300 s that finished before sampling began.

Manuscript rewrite of 2 November (uncommitted, not yet compiled): old Results, LOCO, ladder and Wilcoxon text removed. New statistics subsection and first-sweep record are written. Rerun numbers are visible `\PENDING{}` markers, none of which may reach submission.

## Reviewer 1

**R1.1 Equal-compute evaluation as the primary basis.** DATA OK, TEXT TODO.
Response: All primary claims now rest on matched wall-clock budgets of 10, 60, 300 and
900 s across all 74 instances with five seeds, under a supervisor that certifies the
incumbent captured before the cutoff. Iteration-budget results are no longer used for claims.
Action: Replace the iteration-budget results section with the wall-clock tables.

**R1.2 Directly reproduced contemporary baselines.** DATA OK, TEXT TODO.
Response: PyVRP (0.14.1) and an adapted NeuroLKH run on the same hardware, cutoffs, seeds
and supervisor as the proposed solver. Published results are no longer used as comparators.
Results: at 300 s the hybrid is not significantly different from PyVRP overall, is behind on
100-customer instances, and is behind NeuroLKH on fleet size. State these directly.
Action: Add the baselines to the setup and results; restrict claims accordingly.

**R1.3 Separate learning from heuristic machinery.** DATA OK, TEXT TODO.
Response: A wall-clock factorial ablation (anchored 16 cases plus a 2x2 bundle on 18
instances at 60 and 300 s) separates the components. No single component is significant at
300 s after Bonferroni correction. Micro-DDQN is significant at 60 s in full context, and the
learning bundle matters at 60 s. We no longer attribute the total gain to the DDQN hierarchy.
Action: Replace LOCO and ladder interpretation with the factorial results.

**R1.4 LAC and SA convergence.** DONE.
Response: We removed the claim. The rule accepts every SA-approved move and adds rescue
transitions, so it changes the transition kernel and the classical theorem does not carry
over. We state only what the experiments support.
Action: LAC section and Design Principle 2 rewritten; supplement rescoped.

**R1.5 Statistical hierarchy and seed-level uncertainty.** DONE for method (Statistical Analysis subsection); numbers wait for the rerun.
Response: The fleet estimand is the per-seed paired score sign(NV_c - NV_t). Uncertainty
comes from a hierarchical geometry/seed bootstrap (10,000 replicates, fixed size-stratum
weights) with Bonferroni families. Distance gaps are explicitly conditional on matched
fleet size.
Action: Rewrite the statistics subsection; remove best-of-five and instance-mean tests.

**R1.6 Moderate GNN and lexicographic claims.** DONE, except the ablation numbers.
Response: The penalty guarantee is scoped to the route pool and the incumbent rule is stated
separately. We removed the earlier pruning and recall figures, which we could not trace to the
registered checkpoint. Recall is now reported only on validation data against heuristic teacher edges,
and described as such. The effect of the GNN on solutions rests on the factorial ablation.
Action: GNN paragraph, contributions list, architecture figure and Property 2 rewritten.

## Reviewer 2

**R2.1 What is the fundamental innovation?** DRAFTED in abstract and contributions; author to approve.
Response direction: Do not claim a fundamentally new algorithm. The honest contribution is
an online-learning, cold-start control layer over ALNS, evaluated under a certified
wall-clock protocol, with an explicit account of where it helps and where it does not.
Action: Rewrite the contributions list.

**R2.2 Markov property and convergence of the aggregated SMDP.** DONE.
Response: We make no convergence guarantee. The state aggregates search history, so the
Markov property is at best approximate; we state this and cite Li et al. (2006). The
Bellman contraction holds only for a finite MDP and is stated in that scope.
Action: Macro section and supplement rewritten.

**R2.3 Does LAC preserve SA convergence?** DONE. See R1.4.

**R2.4 Table 8: A1 beats A4 on distance.** DATA OK, TEXT TODO.
Response: That table used iteration budgets. In the wall-clock factorial study no learning
component is significant at 300 s after correction, so we do not claim that learning justifies
itself at every budget; we report the 60 s evidence and the 300 s null result.
Action: Table removed; new ablation reported.

**R2.5 GNN recall drop and its effect.** PARTLY DONE.
Response: The figures you questioned described an earlier model, so we withdrew them. For the registered
checkpoint, validation recall against heuristic teacher edges at threshold 0.01 is 100% at N = 100 and 99.85% at N = 200,
retaining about 29% of candidate arcs. These instances also selected the checkpoint, so the figures are optimistic.
N = 400 lies outside the training sizes and is an extrapolation.
Open: recall at N = 400 and on benchmark sizes (after T300, to avoid CPU contention), plus the ablation contrast.
Action: Paragraph rewritten.

## Reviewer 3

**R3.1 Novelty over learning-guided ALNS.** OPEN. See R2.1.

**R3.2 Comprehensive ablation.** DATA OK, TEXT TODO. See R1.3.

**R3.3 Fair comparison under consistent conditions.** DATA OK, TEXT TODO. See R1.2. Disclose
that the hybrid read the reference fleet inside search in the registered analysis, and report
the reference-blind arm of the contemporaneous rerun. Do NOT use the 1 November blind numbers
(+0.049 vs F111111, +0.119 vs ALNS-Base): that run was about 1.9 times faster than the closed
cells, so those comparisons are confounded in its favour. Also disclose that machine speed varied
between blocks in the closed sweep (see Must fix item 6).

**R3.4 Training and testing protocol.** DONE.
Response: The Macro DDQN, Micro DDQN and LAC have no offline phase. They start from random weights in every run and
learn online within the time budget, so they have no train/test split and we make no transfer claim. Only the GNN is
trained offline, on 48 synthetic instances with 12 for validation at N = 100 and 200, and then frozen. No test instance
was used for its training or selection. We also state that test results motivated evaluating GES, and that the development
instances used for its parameters share coordinates with test instances.
Action: "Training and testing protocol" paragraph added to the setup section.

**R3.5 LAC training with delayed outcomes.** DONE for mechanism; comparison DATA OK.
Response: LAC is consulted only for feasible, same-fleet, distance-worsening candidates,
after a 300-decision warmup, with an observational label over a horizon of 80 LAC decisions.
Comparison with SA alone comes from the factorial LAC contrast.

**R3.6 Effect of GNN pruning on quality.** PARTLY DONE. See R2.5. At threshold 0.01 on validation, 2 of 2,005 teacher
edges were lost. Teacher edges are heuristic, so this does not bound the loss of useful arcs. The solution-level effect waits for the
ablation numbers.

**R3.7 O(1) insertion checks.** DONE.
Response: Constant time applies to a query against cached forward-slack and latest-start
profiles. Each route change costs O(m) to refresh, and a full insertion scan is not O(1).

**R3.8 Total computational cost.** OPEN.
Response direction: Measure time per component (DDQN inference, GNN, GEC, set partitioning)
with `vrptw.phase_trace` on a representative subset. Use `scripts/measure_component_cost.py`, because search rates vary widely between instances.

**R3.9 Hierarchical objective enforcement.** DONE.
Response: The penalty lambda_cert applies only at the top penalty scale, the guarantee holds
within the pool, and the incumbent update rule separately enforces lexicographic order.

**R3.10 Variability and significance testing.** DONE for method. See R1.5.

**R3.11 Feasibility after complex modifications.** DATA OK, TEXT TODO.
Response: Every incumbent is validated in the original problem space by the supervisor
before it counts. Infrastructure gaps (21 cells) are disclosed with bounds. The greedy
depot-deadline bug found during this audit is disclosed and its affected cells rerun.

**R3.12 Learning vs established techniques.** DATA OK, TEXT TODO. See R1.3.
