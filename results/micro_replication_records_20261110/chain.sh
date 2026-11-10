#!/bin/sh
# Protocol order: wait for the component-cost measurement, run this test, then resume the 900 s stage.
cd "$(dirname "$0")" || exit 1
COST=../ges_sweep_20261102/analysis/component_cost/progress.log
until grep -q finished "$COST" 2>/dev/null; do
  pgrep -f 'run_component_cost\.sh' >/dev/null || break
  sleep 30
done
nohup python3 -I sample_load.py >/dev/null 2>&1 &
caffeinate -ims ../../.venv/bin/python run_replication.py >> sweep.log 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then echo "chain stopped: run_replication exit $rc" >> sweep.log; exit "$rc"; fi
exec ../ges_sweep_20261102/resume_t900.sh
