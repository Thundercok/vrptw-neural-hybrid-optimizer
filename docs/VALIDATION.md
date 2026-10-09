# Validation Notes

The consolidation retains the research solver implementation from the starting
`main` and merges the demonstration app from `demo-release`.

- Manuscript PDF compilation and Overleaf packaging completed successfully.
- Frontend production build completed successfully.
- Solver regression suite: 74 tests passed with the updated fingerprint harness.
- The exact-cost golden test previously varied when wall-clock-limited MILP
  recombination was enabled. The fingerprint configuration now excludes MILP
  recombination, and its 16 baseline records were regenerated. This changes
  the test harness, not the production solver configuration or paper evidence.
- The publication audit loader now reads the nested `instances` BKS schema.
  The audit still exits nonzero: 39 reported discrepancies include missing
  rows/blocks under legacy table formats and text-claim mismatches. These
  findings need parser/manuscript reconciliation before publication claims
  can be certified. A successful paper build does not certify those claims.

Run `make research-audit` to see the current findings. `research-all` stops at
an unsuccessful audit; use `make research-paper` to build the existing paper
independently. The published input CSVs are committed alongside the manuscript.
