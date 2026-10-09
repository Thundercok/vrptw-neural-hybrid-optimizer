# Research Rules

- Evaluate standalone solvers with independent cold starts. Label shared-archive
  refinement as a separate experiment.
- Compare travel distance only at matched fleet sizes.
- Pass equal iteration or wall-clock budgets to benchmark workers.
- Generate reported numbers from recorded CSVs; preserve their provenance.
- Use existing solver APIs and keep changes scoped to the requested behavior.
- Run relevant tests when changing solver behavior. Exact-cost fingerprints
  exclude wall-clock-limited MILP recombination.
