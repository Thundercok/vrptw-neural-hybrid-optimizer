# How the rerun results will be worded

Written on 5 November 2026 while `primary_t300` was still running, with T300 at 1,745 of 2,220
cells and no rerun outcome read. It fixes the wording in advance, so that the text follows the
intervals and not the hopes of the authors. It adds no analysis: the estimands, families and
adoption rule stay as in `results/ges_sweep_20261102/README.md` (Amendments 1 to 5).

If a rule here turns out to be wrong after results are read, change it and say so in this file,
with the date and the reason. Do not edit it silently.

## Reading an interval

The fleet score is the mean of sign(NV_comparator - NV_proposed), so positive favors the proposed
configuration. Matched TD gaps are negative when they favor it.

| Fleet score interval | Allowed wording |
|---|---|
| Lower bound above 0 | "used fewer vehicles than X" |
| Upper bound below 0 | "used more vehicles than X" |
| Contains 0, or an endpoint is exactly 0 | "did not differ detectably from X on fleet size" |
| Undefined (a size stratum is empty) | Give the point estimate, say the interval is undefined, and state no direction |

- "Did not differ detectably" never becomes "matched", "equivalent", "as good as" or "competitive".
  These intervals are wide, with four geometry groups per size, so they cannot show equivalence.
- A matched TD gap is always introduced with "where fleets matched" and is never called an overall
  distance gain. If the fleet result is behind, the fleet result comes first.
- If a gap's interval is undefined, say "that interval is undefined". This is what Section
  `sec:first_sweep` already does.
- Words not to use for these results: significantly outperforms, superior, state-of-the-art,
  robust, scale-aware, breakthrough.

## What each level of evidence can support

- **Confirmatory:** the three primary comparisons at 300 s (98.33%), the adoption contrast
  (98.75%) and the eight primary ablation contrasts at 300 s (99.38%). Only these can carry a claim
  in the abstract or the conclusion.
- **Descriptive:** sizes, families, the 10, 60 and 900 s budgets, the 60 s and exploratory ablation
  contrasts, and the load repeats. Always name the interval ("on the unadjusted 95% interval"). They
  can describe a pattern, not establish one.
- A subgroup that looks good does not rescue a primary comparison that does not. Report losing sizes
  and families with the same prominence as winning ones.

## Adoption outcome

**GES adopted** (98.75% lower bound of F111111 against F111111-blind is above 0). F111111 is
proposed, compared with ALNS-Base, PyVRP-ILS and NeuroLKH-adapted. The text must also say:

- Test results motivated the GES phase, so this is not an independent test of that design choice.
- GES is classical. A gain from it is not evidence for learned control.
- The ablation holds GES fixed in all cases, so it cannot apportion the gain to GES.

**GES not adopted.** F111111-blind is proposed, compared with ALNS-Base-noges, PyVRP-ILS and
NeuroLKH-adapted. The text must also say:

- The GES phase was evaluated and did not meet the rule, with the estimate and interval. Do not
  drop it from the paper.
- The 10, 60 and 900 s stages and the ablation describe the configuration with GES, not the proposed
  one, so they say nothing direct about the proposed configuration at those budgets. Sections
  `sec:budget_results`, `sec:ablation_results` and the abstract must carry this, and no budget claim
  can be made for F111111-blind beyond 300 s.

Either way, the repeats in Amendments 4 and 5 cannot change adoption. If a repeat changes which
wording above applies to a comparison, report that in the same paragraph as the main result.

## Text by outcome

⟨…⟩ marks a value from the analysis output. Pick the row for each comparator independently.

**Abstract, first of the two pending sentences.**

- Ahead: "At 300 s, the proposed configuration used fewer vehicles than ⟨X⟩ (fleet score ⟨s⟩, 98.33%
  interval [⟨l⟩, ⟨u⟩])."
- No detectable difference: "At 300 s, it did not differ detectably from ⟨X⟩ on fleet size (⟨s⟩,
  [⟨l⟩, ⟨u⟩])."
- Behind: "At 300 s, it used more vehicles than ⟨X⟩ (⟨s⟩, [⟨l⟩, ⟨u⟩])."

**Abstract, second sentence.**

- No primary contrast excludes zero: "No primary factorial contrast excluded zero at 300 s, so the
  ablation does not establish a benefit of the learned components at that budget."
- Some do: "At 300 s, ⟨contrast⟩ excluded zero (⟨s⟩, 99.38% interval [⟨l⟩, ⟨u⟩]); the other ⟨k⟩
  primary contrasts did not."

**Contributions (R2.1, R3.1).** The claim stays what `docs/manuscript.tex` already says: a cold-start
online control layer over ALNS and a certified wall-clock evaluation, with an account of where it
helps. If the hybrid is ahead of no comparator, the contribution is the evaluation and the negative
finding, and the text says so plainly. It does not fall back on subgroups.

**Discussion (`sec:disc_scale_aware`).** Answer in this order: (1) gain or no gain against ALNS-Base,
which is the comparison that speaks to the learned layer; (2) position against PyVRP-ILS and
NeuroLKH-adapted; (3) how much is attributable to classical components; (4) what the ablation
supports. If the learning contrasts are empty because LAC rarely fires at 300 s (Must fix item 17 in
`docs/response_to_reviewers_draft.md`), say the contrast is uninformative. Do not call it a null effect
of LAC.

**Managerial implications (`sec:disc_managerial`).** Name the solver the results favor at 5 minutes.
Name one at 15 minutes only if T900 ran for all the solvers named. If nothing separates the solvers, say
that the choice cannot rest on these results and that the simplest or fastest solver is the
reasonable default.

**Conclusion.** Restate the three primary results and the ablation result in the abstract's wording,
losses included. The final sentence on future work must not imply that a result was shown.

**Response letter (R1.2, R1.3, R2.4, R3.12).** Use the same sentences. Keep a reviewer's doubt on the
record when the data support it, for example: "Your concern is supported: in the wall-clock factorial
study, no learning contrast excluded zero at 300 s."

## Comparison with the original submission

The original 23W/49T/2L, p = 1.7e-5 and -1.80% came from iteration budgets, and the text withdraws
them. They are not compared with the rerun as better or worse. If asked, say only that the protocol
changed and the old figures should not be used.
