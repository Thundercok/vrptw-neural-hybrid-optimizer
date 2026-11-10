#!/bin/sh
# Amendment 7: wait for the component-cost measurement to end, then resume the sweep at the 900 s stage.
cd "$(dirname "$0")" || exit 1
until grep -q finished analysis/component_cost/progress.log 2>/dev/null; do
  pgrep -f 'run_component_cost\.sh' >/dev/null || break
  sleep 30
done
rm -f STOP
nohup python3 -I sample_load.py >/dev/null 2>&1 &
exec caffeinate -ims ../../.venv/bin/python run_sweep_ges.py >> sweep.log 2>&1
