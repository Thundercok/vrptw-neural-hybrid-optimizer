# LAC with SA-preserving predictive rescue

## Declared scope

This follows the [legacy audit](legacy_provenance_20261019.md) and addresses the
implementation mismatch underlying R1.4/R2.3 and part of R3.5. The intended
rule for new runs is the disjunction already described in the manuscript:

`accept = (prediction >= threshold) OR (uniform < SA_probability)`.

This deliberately changes post-warmup search behavior from the audited
threshold-or-fixed-0.05 implementation. It is not a behavior-preserving speed
optimization or a reconstruction of historical executions. The decision was
made to match the declared method, without selecting thresholds, checkpoints or
search parameters from benchmark scores. Old results/model files and manuscript
sources remain unchanged. No publication sweep or new operational pilot is part
of this change.

## Decision contract

- Existing solver eligibility gates remain: the LAC branch is reached only for
  feasible, equal-fleet, worsening candidates outside penalized acceptance,
  with LAC enabled, eligible micro control and `frozen=False`. LAC cannot bypass
  feasibility or fleet guards. Disabled and frozen branches keep their SA path.
- Preserve the existing warmup boundary: `step` increments for each `decide()`
  query; steps strictly below `lac_warmup` use SA only. With default 300,
  predictive rescue begins at decision 300, not ALNS iteration 300.
- After warmup, a prediction at or above the threshold accepts. Otherwise take
  one uniform draw and compare it strictly with SA probability; no extra fixed
  5% rescue is allowed. A predictive acceptance needs no random draw. The
  default threshold and adaptive threshold schedule stay unchanged.
- The solver supplies its original double-precision SA probability rather than
  recovering it from the float32 neural feature. At an identical candidate,
  temperature and uniform draw, a low prediction cannot veto SA acceptance.
  Float32 rounding must neither remove nor add an SA acceptance at the boundary.
- Keep existing positional calls and `(accepted, score)` results compatible.
  A new optional keyword-only `sa_probability` carries original precision;
  callers omitting it use the probability available in their feature vector.
  Warmup returns SA probability as the score; learned mode returns prediction.
- Queue every eligible query once, including rejected queries, and count actual
  acceptances once. Preserve delayed labels, feature snapshots, network shapes,
  weight format, optimizer, horizon and training frequency. The existing label
  is a best-distance improvement after 80 LAC decision calls; it is not a
  causal label for a move or a delayed fleet-first reward.
- New CLI instrumentation identifies the selected rule as
  `lac_policy=sa_or_predictive_v1`; it is null for disabled LAC or non-hybrid
  solvers. Policy identity describes configured semantics; query count still
  determines whether that branch was actually used.

The preservation property is about the same candidate/probability/uniform draw.
Search trajectories and future RNG states can change once additional moves are
accepted. No classical SA asymptotic-convergence theorem, neural convergence,
routing-quality improvement or positive learning attribution follows from this
change. The manuscript's unsupported convergence claim remains unresolved until
it is explicitly revised or rigorously proven in separate work.

## TDD verification plan

Write tests before runtime edits, record the failing baseline, then implement the
smallest change and run the relevant suites. Tests cover SA acceptance despite a
low prediction, predictive rescue, joint rejection and strict/equality bounds;
warmup and RNG consumption; original versus float32 probability; delayed queues
and counters; the real solver call path and disabled/frozen controls; and CLI
policy identity. Use deterministic toy fixtures, not benchmark score selection.

The first test run exposed a fixture error: a rule-micro method was patched on
the full solver instead of its actual `RuleMicroHybridSolver` subclass. Preserve
that log, correct the fixture before runtime edits, and use the corrected Red
run as behavioral evidence. Existing fingerprint baselines must not be rewritten.
Run the complete test suite after the targeted tests pass, retaining any failure.

## Recorded implementation and checks

The change is implemented in three runtime files:

- `src/vrptw/rl.py`: replace the fixed 0.05 rescue with the supplied SA
  probability, preserve the old call signature, and identify the policy.
- `src/vrptw/solvers.py`: pass the same original-precision exponential used by
  the SA-only branch. Eligibility and adaptive threshold logic are unchanged.
- `scripts/benchmark.py`: include the selected `lac_policy` in instrumentation.

All evidence is in [the new artifact directory](../results/lac_sa_tdd_20261019/).
It contains source snapshots before/after, source-file hashes, the delta from the
pre-existing working tree, the corrected Red tests, test logs and integrity
[verification](../results/lac_sa_tdd_20261019/verification.json). It refuses to
replace the preserved earlier artifacts.

The initial packaging manifest inadvertently hashed its own still-empty file.
That original is retained; `before_hashes_corrected.json` records the completed
manifest's actual hash. Every other initial entry matched. This packaging repair
does not change source snapshots, test results or historical files.

| Stage | Recorded result |
| --- | --- |
| Initial Red, including the fixture error | 14 failed / 9 passed, 11.40s |
| Corrected Red, before runtime edits | 12 failed / 11 passed, 4.48s |
| Initial Green, identical corrected Red tests | 23 passed, 4.35s |
| Final tests | 26 LAC cases, adding probability 1 and two infeasibility/fleet guard cases |
| LAC + native certification + benchmark-budget target | 144 passed, 4.89s |
| Complete repository suite | **373 passed**, 94.39s |
| Static checks | Repository-wide Ruff, formatting of all four changed/new Python files, `git diff --check`: pass |

The full suite has one existing expected PyVRP `PenaltyBoundWarning` from the
intentionally infeasible service/depot fixture. Existing solver fingerprints pass
without regeneration; their short budgets do not exercise post-warmup predictive
rescue, which the new deterministic tests cover directly. Automated tests include
toy solves and the existing fingerprint/backend checks; they are not a new
publication or operational comparison.

The preservation check confirms that **2,008 pre-existing files** under
docs/results/checkpoints/golden fixtures remain byte-identical. Eleven untouched
tracked diff blocks match the initial snapshot; the two already-dirty runtime
files retain their prior edits with only the declared LAC additions. `rl.py` is
the newly modified tracked file. The saved delta records all three runtime edits.
No fingerprint, checkpoint, historical result, manuscript or earlier audit was
rewritten.

Runtime identity uses the same source-file hash convention as the benchmark CLI:

- Before: `d30f8ad14ff41be6ed276918e72b56da78a3b7cca6b8839bd50c57aa3f5a94a9`.
- After: `5767a17e684550c97d319d03363b7846038d85afb3a97c22e9e442d97a23f5b4`.
- Policy: `sa_or_predictive_v1`.

The after snapshot includes the final 26-case tests. The before snapshot pairs
the pre-edit source with the corrected 23-case Red tests; replay it in an isolated
copy if reproducing the failure. Do not rerun the old semantic probe against new
source and label it a reproduction of its frozen historical observation.

The earlier [23-comment matrix](resubmission_evidence_matrix_20261019.md) and
legacy audit remain frozen at their own source identity. This report supersedes
their description of current LAC acceptance only for the new source above. The
original execution-provenance uncertainty, unsupported theory statements,
learning-attribution gaps and manuscript revisions remain open.

## Remaining gates

1. Validate operational cutoff/return behavior for the new source before a larger
   evaluation. Prior timing passes belong to the prior source identity; passing
   automated tests does not transfer those measurements to this policy.
2. Predeclare the equal-wall-clock ablation contrasts and component dependencies.
   Separate SA-only, predictive rescue and suitable acceptance-volume controls
   when evaluating LAC; a larger acceptance volume alone is not predictive credit.
3. Evaluate quality/uncertainty without retuning on test outcomes. This engineering
   change supplies no positive performance result and does not close R1.4/R2.3:
   the unsupported convergence language still needs removal or a valid proof in
   separately authorised manuscript work.

To run the relevant automated checks from the project directory:

```sh
.venv/bin/python -m pytest tests/test_lac_acceptance.py tests/test_native_certification.py tests/test_benchmark_budget.py -q
.venv/bin/python -m pytest -q
```

No full sweep, operational pilot, training campaign, publication table update or
manuscript edit was performed in this continuation.
