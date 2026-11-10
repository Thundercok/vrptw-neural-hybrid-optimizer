# Response to reviewers: draft for Access-2026-45322

Draft of 10 November 2026, written to match `docs/manuscript.tex` at commit 2fb925fe. The authors
rewrite it in their own words before sending. The final text goes into the IEEE template
(concern / author response / author action). Section numbers refer to the compiled manuscript.

Updated on the evening of 10 November 2026 for the Micro test result, the GNN recall sentence now in
Section IV-E3, and the removal of the Discussion subsection on analytical properties. These updates
match `docs/manuscript.tex` as committed together with this file on 11 November 2026.

Open before sending:
- **[HGS]** The answer under R1.2 is checked against the installed PyVRP 0.14.1, the frozen
  adapter, the rerun cells and the PyVRP 0.13.0 release notes
  (https://github.com/PyVRP/PyVRP/releases/tag/v0.13.0). It gives no reason for not running another
  HGS implementation; the authors add one if they want to.
- **[AI]** A disclosure for this letter is drafted in its last section. The authors check that it
  describes what they actually did, and keep it consistent with the manuscript's Acknowledgment.

## Opening statement (draft)

We thank the editor and the reviewers. The reviews identified a central problem: our claims
rested on equal iteration budgets, and the proposed method costs more per iteration. We have
rebuilt the evaluation and withdrawn every iteration-budget result. All results now come from a
single rerun in which every solver received the same wall-clock budget on the same machine, with
all solvers of an instance, seed and budget run together, and with only incumbents certified in
the original problem space counted. The analysis plan was fixed before results were read.

The rerun changes the paper's conclusion, and we report it as it is. At 300 s the proposed
configuration did not differ detectably on fleet size from ALNS-Base, PyVRP-ILS or
NeuroLKH-adapted, and no primary factorial contrast excluded zero, so the study does not
establish a benefit of the learned components at that budget. One learned component, Micro-DDQN,
was then tested once more at 60 s under a protocol fixed in advance: one of its two contrasts
excluded zero and the other did not, and we report both (R1.3). Several of your concerns are
therefore supported by the new evidence, and we say so where they are. We also disclose that
results on the test instances motivated adding a classical Guided Ejection Search phase, which
was kept under a rule fixed before the rerun.

Other corrections found during the revision are listed at the end of this letter.

## Reviewer 1

**R1.1 Equal-compute evaluation as the primary basis.**
Response: We agree, and the iteration-budget results are withdrawn. All claims now rest on equal
wall-clock budgets of 10, 60 and 300 s on all 74 instances (56 Solomon-100, 12 Homberger-200,
6 Homberger-400) with five seeds, so the full suite rather than a subset. Construction, model
inference, compilation and certification are charged to each solver's budget. A 900 s stage was
started but not completed, and no 900 s result is reported, so the longer operational horizon you
asked for is not covered. We state this as a limitation.
Action: Sections V-A to V-D rewritten; Fig. 2 shows the comparisons by budget.

**R1.2 Directly reproduced contemporary baselines.**
Response: Two external solvers now run under the same hardware, budgets, seeds and supervisor as
the proposed method: PyVRP 0.14.1 with its iterated local search (PyVRP-ILS) and an adaptation of
NeuroLKH with its pretrained checkpoint (NeuroLKH-adapted). You named HGS, and we did not run it:
PyVRP 0.14.1, the release we pinned, solves with an iterated local search. PyVRP dropped its
hybrid genetic search in release 0.13.0, whose release notes give better solution quality at
limited runtimes as the reason, and we did not add an older release or another HGS
implementation. The manuscript says that PyVRP's HGS is not the method used, and we do not present
PyVRP-ILS as a reproduction of HGS or of any published configuration. At 300 s the proposed configuration did not differ detectably on fleet size from either
(fleet scores +0.008 [-0.098, 0.117] and -0.068 [-0.142, 0.033], 98.33% intervals). On
descriptive intervals it used more vehicles than both at 10 s, and on the wide-time-window
families R2 and RC2 it never used fewer vehicles than NeuroLKH-adapted. Published results are no
longer used as comparators.
Action: Section V-A (baselines), V-C, V-D and V-F.

**R1.3 Separate learning from heuristic machinery.**
Response: Your concern is supported. A wall-clock factorial ablation over GEC, set partitioning,
Macro, Micro, LAC and GNN on 18 instances at 60 and 300 s replaces the earlier ladder. No primary
contrast excluded zero at 300 s (99.38% intervals), so we do not attribute any gain to the DDQN
hierarchy. At 60 s, Micro-DDQN excluded zero on descriptive intervals (+0.244 [0.053, 0.492] in the
full context). That pattern came from exploring the test set, so we tested it once more on 24 new
time-window variants of the same customer layouts at 200 and 400 customers, under a protocol fixed
before any cell ran. On the two confirmatory contrasts (97.5% intervals), Micro-DDQN used fewer
vehicles than the rule-based policy at 60 s on these instances in the bare configuration (+0.208
[0.025, 0.450]), and in the full context the test did not detect a difference and is too small to
rule one out (+0.150 [-0.012, 0.372]). 71 of the 120 blocks ran at a mean load above 8, and without
them both intervals are undefined. The test compares Micro-DDQN with a rule-based policy inside the
same framework; it says nothing about 300 s or about the other solvers. We also show that much of
what ALNS-Base achieves comes from the classical Guided Ejection Search phase.
Action: Sections V-E and VI-A; Table 5; all 32 contrasts in the supplement.

**R1.4 LAC and SA convergence.**
Response: We removed the claim. The rule accepts every move SA accepts and adds others, so it
changes the transition kernel, and the classical convergence results do not carry over. We make no
convergence claim.
Action: Section IV-D rewritten; the design-principle statement about LAC removed from the
Discussion; supplement rescoped.

**R1.5 Statistical hierarchy and seed-level uncertainty.**
Response: The unit is a seed pair within an instance, never a best run or an instance mean. The
fleet score is +1, -1 or 0 per seed pair, averaged over seeds and instances within each size with
fixed weights. Intervals come from a bootstrap that resamples seeds and, within each size, groups
of instances sharing customer coordinates (10,000 replicates), with Bonferroni families of 3 for
the primary comparisons and 8 for the primary ablation contrasts. Distance gaps are computed only
where fleets matched and are described as conditional. Wilcoxon tests are no longer used.
Action: Section V-B.

**R1.6 Moderate GNN and lexicographic claims.**
Response: Both claims are now scoped. The set-partitioning penalty guarantee holds only within the
route pool at the top penalty scale, and the incumbent update rule separately enforces the
lexicographic order; no global optimality is claimed. The recall figures you questioned could not
be traced to the registered checkpoint and are withdrawn. Measured on the benchmark instances
against the 300 s routes of PyVRP-ILS and NeuroLKH-adapted, the heatmap kept between 98.0% and
100.0% of their route edges at threshold 0.01 across the three sizes, and 96.6% at the lowest point
over all thresholds (details under R2.5). The GNN full-context ablation contrast did not exclude
zero at 300 s (-0.044 [-0.167, 0.067]).
Action: Sections III-A, IV-E3 and IV-F.

## Reviewer 2

**R2.1 What is the fundamental innovation?**
Response: We no longer claim a new search principle. The contribution is a cold-start control
layer over ALNS, two controllers at different timescales and an acceptance model that learn
online from random weights in every run, together with a certified wall-clock evaluation of
whether that control pays for its compute. The evaluation finds that at 300 s it does not
detectably do so, and we report this as a negative result. The one positive signal, for Micro-DDQN
at 60 s, is described under R1.3.
Action: Abstract, introduction and contribution list rewritten.

**R2.2 Markov property and convergence of the aggregated SMDP.**
Response: The aggregated state is a lossy summary of the search, so the Markov property need not
hold, and we give no convergence guarantee or error bound. We describe the controller as a learned
policy over a partially observed, state-aggregated process (Li et al., 2006).
Action: Section IV-B and the supplement rewritten.

**R2.3 Does LAC preserve SA convergence?**
Response: No. See R1.4.

**R2.4 Ablation: heuristic-only A1 beats full A4 on distance.**
Response: Your concern is supported. That table used iteration budgets and is withdrawn. In the
wall-clock factorial study no learning contrast excluded zero at 300 s, so we do not claim that the
learning components justify themselves at that budget. At 60 s, a separate test fixed in advance
found that Micro-DDQN used fewer vehicles than a rule-based policy in the bare configuration and
did not detect a difference in the full context (R1.3).
Action: Section V-E.

**R2.5 GNN recall drop and its effect.**
Response: The figures 95.8% to 78.2% described an earlier model and could not be traced to the
registered checkpoint, so we withdrew them. We measured recall again with the registered
checkpoint on the 74 benchmark instances, against the 300 s routes of the two solvers that use no
GNN. At threshold 0.01 the heatmap kept 99.1%, 99.8% and 100.0% of the route edges of PyVRP-ILS
solutions at 100, 200 and 400 customers, and 98.0%, 99.2% and 99.8% of NeuroLKH-adapted's, while
retaining 34.0%, 23.3% and 23.6% of candidate arcs. The lowest figure over the three thresholds was
96.6%, for NeuroLKH-adapted at 100 customers and threshold 0.05. So we did not observe the drop
with size that the withdrawn figures showed. These are agreement with other solvers' routes, which
are themselves heuristic, not a solution-quality effect. The effect on solutions is estimated by
the ablation, where the GNN contrast did not exclude zero. Use at 400 customers remains an
extrapolation from training at 100 and 200.
Action: Section IV-E3.

## Reviewer 3

**R3.1 Novelty over learning-guided ALNS methods.**
Response: Section II-C now compares the design with the closest work, Johnn et al. (operator
choice in ALNS by deep RL with graph networks) and DR-ALNS (a policy over operators, parameters and
acceptance). The differences are two controllers at different timescales in place of one policy,
an acceptance model added to SA by a disjunctive rule, and online learning from random weights in
every run. We did not run those methods, and we state that these differences are not evidence of
better performance. See also R2.1.
Action: Sections II-C, II-D and the contribution list.

**R3.2 Comprehensive ablation.**
Response: See R1.3. The factorial design covers all six components you listed, each in a bare and
a full context, plus a 2x2 contrast of the learning and heuristic bundles.

**R3.3 Fair comparison under consistent conditions.**
Response: All solvers ran on one machine, under one supervisor, with the same budgets and seeds,
and all cases of an instance, seed and budget ran together as a block, because machine speed
varied by up to several times between nights in our earlier sweep. Blocks frozen by machine sleep
or run under load spikes were moved aside unread and rerun, and repeats without high-load blocks
are reported. We also disclose that the earlier version of the hybrid read the best-known fleet
size during search, which no baseline did; the rerun disables this. The baselines were not tuned
for these budgets, which we list as a limitation.
Action: Section V-A.

**R3.4 Training and testing protocol.**
Response: The Macro DDQN, Micro DDQN and LAC have no offline training: they start from random
weights in every run and learn within it, so there is no train/test split and we make no transfer
claim. Only the GNN is trained offline, on synthetic instances, and frozen; no benchmark instance
was used for its training or selection. Test results did motivate adding the Guided Ejection
Search phase, and its development instances share coordinates with test instances; both are
disclosed. The separate Micro-DDQN test (R1.3) used time-window variants that played no part in
development, but they share customer layouts with the ablation instances, so we describe it as a
test on new time-window variants and not on new layouts.
Action: Section V-A ("Training and testing protocol" and "Experimental firewall").

**R3.5 LAC training with delayed outcomes, and comparison with SA.**
Response: LAC is consulted only for feasible candidates that keep the fleet size and increase
distance, after 300 warmup decisions of pure SA. Each consulted decision is labelled by whether the
best distance improved within the next 80 LAC decisions. Your question about its performance
exposed a problem: in a separate measurement on the 18 ablation instances at 300 s, LAC was
consulted in 6 instances, passed its warmup in 3, and its classifier never changed an acceptance
decision. The LAC contrast (-0.022 [-0.098, 0.000]) is therefore uninformative rather than evidence
that LAC has no effect, and we say so.
Action: Sections IV-D, V-E, V-H and limitation (vi).

**R3.6 Effect of GNN pruning on solution quality.**
Response: See R2.5. The GNN ablation contrast did not exclude zero, and the recall check on the
benchmark sizes measures how often edges used by other solvers survive the pruning: at least 96.6%
in every combination of size, threshold and solver that we measured.

**R3.7 O(1) insertion checks.**
Response: Constant time applies to one insertion query against a cached route profile (arrival
times, load and latest feasible start). Refreshing the profile costs O(m) after each change to the
route, scanning all positions is O(m), and moves that reverse or relocate segments are not O(1). We
claim no O(1) bound for moves or iterations.
Action: Section IV-E1 rewritten, with the exact feasibility condition.

**R3.8 Total computational cost.**
Response: We timed the main components on the 18 ablation instances at 300 s. Set partitioning
took the largest share (median 53%, 28% and 22% of the budget at 100, 200 and 400 customers),
destroy, repair and local search 18%, 48% and 50%, and the Guided Ejection Search phase 10%. The
learned controllers took a median of 2.6%, 1.9% and 0.8% (at most 23% on one instance), GNN
inference 0.01% and certification under 0.05%. The main loop ran at a median of 17.8, 14.5 and 6.5
iterations per second. The learned layer is cheap, so its compute is unlikely to explain the null
results. At 10 s, compilation and the Guided Ejection Search phase take most of the first half of
the budget.
Action: Sections V-D and V-H.

**R3.9 Hierarchical objective enforcement.**
Response: The best solution changes only for a candidate with fewer vehicles, or the same number
and strictly lower distance, after validation in the original instance, so the reported solution
never trades a vehicle for distance. Intermediate moves may, for example in the diversification
mode, and we say so. The set-partitioning guarantee holds within the route pool at the top penalty
scale.
Action: Sections III-A and IV-F.

**R3.10 Variability and significance testing.**
Response: See R1.5. Per-instance means over five seeds for all solvers at 10, 60 and 300 s, all 32
ablation contrasts and per-family counts are in the supplement, and the record of every cell in
the reported stages is published in the repository.
Action: Section V-B and the supplement.

**R3.11 Feasibility after complex modifications.**
Response: Every incumbent counts only after the supervisor has validated coverage, capacity and
time windows in the original instance and hashed it before the cutoff. In the rerun, every cell of
the proposed configuration found a certified solution; five comparator cells at 10 and 60 s found
none and count as failures. No cell was lost to infrastructure failure. A defect in the greedy
construction found during this revision is disclosed, and the affected runs were rerun.
Action: Sections IV-E5 and V-G.

**R3.12 Learning versus established techniques.**
Response: Your concern is supported. With the Guided Ejection Search phase on, the difference
between the hybrid and ALNS-Base was no longer detectable, the phase gave ALNS-Base a fleet score
of +0.208 against ALNS-Base without it, and no primary learning contrast excluded zero at 300 s.
The one detectable gain for a learned component is at 60 s: in a separate test fixed in advance,
Micro-DDQN used fewer vehicles than a rule-based policy in the bare configuration, and the test did
not detect a difference in the full context. See also R1.3.
Action: Sections V-E and VI-A.

## Other corrections (draft list for the letter)

- Methods text audited against the frozen code: hardware (16 GB M1, macOS 26.5.2, unpinned),
  ALNS-Base (Thompson sampling over 65 pairs), the granular neighbourhood (15 nearest customers),
  the macro modes, search phases, reward, LAC features and label, GEC, set-partitioning limits and
  the hyperparameter table.
- Withdrawn because they could not be traced or rested on iteration budgets: earlier pruning and
  recall figures, the supplement's sensitivity, PCA, literature-comparison, variability and anytime
  sections.
- Removed because they argued for a benefit the results do not show, or restated the method: the
  introduction's list of problems of end-to-end neural solvers (we do not evaluate such solvers),
  the Discussion subsection on analytical properties and design principles, and the future-work
  sentence on electric vehicles and real-time dispatch. The penalty value $10^5$ is now stated in
  Section III-A, where the earlier condition on it was also corrected.
- Proofs corrected: the two-stage set-partitioning theorem removed, the GEC complexity bound and
  the forward-slack condition corrected.
- References corrected against Crossref or the publishers; one reference that could not be found
  was replaced.
- The data-availability statement now names the public repository and the published rerun
  records. "Archived on Zenodo" was removed, because no such archive exists.
- Disclosed: a solver rule reads the instance family from its name, the earlier hybrid read the
  best-known fleet, and machine speed varied in the earlier sweep.

## Use of AI tools (draft)

The authors used Claude (Anthropic) to draft this response and to check the figures in it against
the experimental records. The authors reviewed and revised the text, and take full responsibility
for it. The same tool was used in preparing the revised manuscript, as disclosed in its
Acknowledgment.
