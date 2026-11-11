# Rerun records, published 10 November 2026

Compact records of the contemporaneous rerun reported in the revised manuscript. The full cell
outputs (about 22 GB: routes, trajectories, supervisor receipts and logs for every cell) are kept by
the authors and are available on request.

- `records.csv`: one row per cell from the validator (`validate.py`): stage, instance, case, seed,
  cutoff, whether a certified solution was found, fleet size, distance, capture and return times,
  power, battery and load at start, clock gap, and any validation errors. Calibration anchors are
  included. Rows of the 900 s stage are left out, because that stage has not finished and README
  Amendment 7 forbids reading or reporting any 900 s result before it has.
- `analysis/`: output of `scripts/analyze_ges_rerun.py` (results, report, per-instance and family
  tables, LaTeX rows), the GNN recall check, and both component-cost measurements, including the one
  whose LAC counters were not recorded (`component_cost_lac_uncounted_20261110`).
- `analysis/stage_fleet_t300.csv`: added on 12 November 2026. For every certified 300 s cell of
  F111111 and ALNS-Base, the fleet of the initial solution, the fleet right after the Guided
  Ejection Search phase and the final fleet, read from the cell trajectories by
  `scripts/stage_fleet_t300.py`. It backs the descriptive counts in the Discussion (338 of 370
  seed pairs with the same fleet at both points). It was computed after the results were read.
- `load_samples.jsonl`: load averages sampled during the run (README Amendment 5).
- `README.md`: the analysis plan, the adoption rule and all amendments, as written during the run.
- `run_sweep_ges.py`, `validate.py`, `sample_load.py`, `run_component_cost.sh`, `resume_t900.sh`,
  `launch_hashes.txt`, `runtime_manifest.json`: the runner, validator and launch records.
- `runtime/`: the frozen solver snapshot the runner used, without caches. `runtime_manifest.json`
  lists the hash of each of its files.

The GNN checkpoint used by the rerun (sha256 `365de53b...`) is tracked at
`results/gnn_retraining_20261017/model_seed42/best.pt`.
