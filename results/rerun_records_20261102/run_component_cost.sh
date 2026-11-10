#!/bin/sh
# Component cost on the 18 ablation instances for the adopted F111111, seed 42, 300 s, one run at a time.
# Each run waits for AC power and load1 <= 3 (at most 30 min for load, then it runs and records its load).
# Rerunning skips instances that already have an output.
cd "$(dirname "$0")/../.." || exit 1
out=results/ges_sweep_20261102/analysis/component_cost
mkdir -p "$out"
for i in C101 C1_2_1 C1_4_1 C201 C2_2_1 C2_4_1 R101 R1_2_1 R1_4_1 R201 R2_2_1 R2_4_1 RC101 RC1_2_1 RC1_4_1 RC201 RC2_2_1 RC2_4_1; do
  [ -s "$out/$i.json" ] && continue
  until pmset -g batt | grep -q "AC Power"; do sleep 60; done
  n=0
  while [ "$n" -lt 30 ] && [ "$(sysctl -n vm.loadavg | awk '{print ($2 <= 3)}')" != 1 ]; do sleep 60; n=$((n + 1)); done
  echo "{\"start\": \"$i\", \"at\": \"$(date '+%d %H:%M:%S')\", \"waited_min\": $n, \"load\": \"$(sysctl -n vm.loadavg)\"}" >> "$out/progress.log"
  .venv/bin/python scripts/measure_component_cost.py --instance "results/ges_sweep_20261102/inputs/$i.TXT" --config ges --time-limit 300 --seed 42 --output "$out/$i.json" >> "$out/progress.log" 2>&1
done
echo "{\"finished\": \"$(date '+%d %H:%M:%S')\"}" >> "$out/progress.log"
