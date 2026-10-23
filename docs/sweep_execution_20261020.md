# Frozen sweep executor and registered statistics (2026-10-20)

## Specification before implementation

Implement executable binding, sequential/resumable execution and registered
statistics for the preserved anchored-16 design. Prepare a new artifact for all
8,620 physical jobs (2,365,600 nominal solve seconds); do not launch them in this
stage. Do not overwrite the old design, source/results/models/goldens, alter
solver behavior, retrain, tune from test scores or edit the manuscript.

Reuse the opt-in common supervisor and independent original-space packet audit.
Bind the original 74 input identities/geometries, five seeds, four main cutoffs,
18-input 60/300s ablation, original order and shared Full cells exactly. Resolve
legacy comparator labels to alns/pyvrp/neurolkh; every F case uses bind_ablation.
Freeze full requested/effective/nested configs in content-addressed bindings,
exact per-job commands, input/model/backend identities, source/tests, hardware/
package fingerprint and protocol before dispatch. No partial Config recreation.
Keep fresh processes/empty exclusive work/cache, no warmup, hash seed42,
one-thread requests, shared pre-cutoff validation and [T-.05,T+.5] return gate.

The prepared artifact is executable via an explicit run subcommand, not an
automatically activated sweep. Record the outstanding baseline-representativeness
and compute-policy scope; do not rewrite historical launch_ready=false or infer
policy approval from passing engineering tests. No extra approval flag is needed
inside the executor: invoking run is an explicit action on a concrete manifest.

## Transactions and recovery

Use a kernel advisory exclusive lock (POSIX local filesystem); never unlink a
live lock inode or signal a PID recovered from disk. Persist a launch intent
before spawning. A newly owned outer CLI runs in its own session, so the runner's
SIGINT handler can request a stop after the current job commits. Preserve the
existing T+180 watchdog; SIGINT the owned CLI and allow its supervisor cleanup,
never blindly SIGKILL it while its separate worker may still exist.

After CLI reaping, persist an immutable execution/resource receipt, audit result
and a manifest of every job artifact, then atomically publish the commit last.
Resume checks all prior commits/evidence and skips them, including known
algorithm/timing failures. If a crash leaves a complete execution receipt and
result, finalize/re-audit that transaction without spawning. A launch intent
without sufficient completion evidence blocks subsequent dispatch. No automatic
retry, replacement, success-only subset, or guessing that a missing result is a
solver loss. CSV/status are reproducible views of commits, not authoritative
editable state. Stop on protocol drift or failed cleanup.

No-solution errors explicitly identified by the three adapters are availability
failures when source/request/cold/clock/cleanup checks pass. Missing effective
binding evidence remains unverified/false when there is no checkpoint; it is
never relabelled a binding pass. Preserve its count separately. Observed binding
drift or unknown exceptions invalidate protocol inference. Certification and
return latency are separate: a certified pre-cutoff incumbent remains available
for the declared cutoff endpoint, while every return-gate failure is reported.
Do not call those rows compliant with an equal-return-latency policy.

## Statistical contract and pre-data clarifications

Use all declared completed cells, with exact paired seed labels and failure
availability; reject missing/duplicate/protocol-invalid cells. Primary is mean
paired feasibility-then-fleet score (+1 treatment win, -1 loss, 0 fleet tie or
both unavailable), averaged within instance then size strata with fixed original
weights. Both-failure counts are separate from quality ties. Mean-NV W/T/L is a
descriptive complete-five-seed analysis. Export seed mean, median, sample SD
(ddof=1), range, valid-run count and availability/return/binding denominators.

For valid seed pairs at matched fleet, TD percent gap is
100*(treatment-control)/control (negative means shorter). Average within each
instance first. Export the unweighted eligible-instance descriptive mean and,
separately, the fixed-size-weight stratified estimand used for intervals. This
distinguishes the two means when failures/matching change size composition.
A positive-weight stratum without matched instances makes the stratified TD
estimand undefined; retain that state, never fill it with zero or renormalize
away the stratum. Record exact matched seed/instance counts.

Generate 10,000 draws with NumPy default_rng seed20261019. Draw five seed labels
with replacement, shared globally across algorithms/cutoffs. Independently draw
four geometry groups with replacement within each size; keep every member and
duplicate-group multiplicity. Reuse the same geometry/seed draws for the primary
and ablation subsets; mean over sampled instances within stratum, not equal
weight over cluster means. Main weights are 56/74,12/74,6/74; ablation 1/3 each.
Persist draw indices and every replicate in CSV before deriving percentile CIs.

At 300s apply separate Bonferroni percentile families: three primary comparisons,
eight registered ablation contrasts. These comparison families apply separately
per metric; they do not provide simultaneous control across all endpoints.
Other cutoffs/contrasts are descriptive.
Suppress a matched-TD interval if any replicate lacks a required denominator;
keep undefined draws/counts. Four geometry groups per size and five seeds give
approximate intervals, no coverage/power guarantee. Do not compute unregistered
p-values. The 16-cell design does not identify all two-factor interactions.

The exploratory heuristic/learning interaction uses raw NV in seed units with
all four cells available: NV_full - NV_H - NV_L + NV_off. Average eligible seeds
within instance then fixed size strata; report selection/undefined denominators.
Do not add ordinal paired win scores as a factorial interaction.

## TDD validation plan

- Executor fixtures: exact 8,620-job binding/order/overlap/budget; no solve during
  prepare; collision refusal; source/input/model/config/backend/hardware drift;
  exclusive lock; once-only resume; interrupted receipts vs ambiguous intents;
  ordinary failures retained; protocol failure stops; graceful stop and watchdog.
- Statistics: hand-calculated paired fleet/failure/matched-TD cases, seed-order
  invariance, sample SD, unequal cluster sizes/multiplicity, globally paired
  draws, fixed weights, undefined TD suppression, CI levels and raw NV bundle
  interaction. Cross-check vectorized estimates with an independent scalar loop.
- Use synthetic/stdlib fixtures for execution/recovery tests; never launch the
  real benchmark in negative CLI tests or relabel fixtures as solver evidence.
  Preserve Red/Green, full regression/static checks, before/after hashes and
  reviewable prepared artifact. No operational solve is authorized by this stage.
