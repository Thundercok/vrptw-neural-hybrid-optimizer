# GES rerun analysis

Closed stages: primary_t300, primary_t60, primary_t10, ablation_t60, ablation_t300

## Adoption rule

F111111 with GES vs F111111-blind: fleet score +0.062, 98.75% interval [0.001, 0.123].
GES adopted: True. Proposed configuration: F111111.
T300 infrastructure gaps: 0. Blocks with a cell started at load above 8: 0.
Blocks with a cell run at mean load above 8: 92. Blocks with a cell not measured during its run: 76.

## Primary family, 98.33% intervals

- 300 s all F111111 vs ALNS-Base: fleet -0.027 [-0.065, 0.011], W/T/L 4/352/14, matched TD +0.04%
- 300 s all F111111 vs PyVRP-ILS: fleet +0.008 [-0.098, 0.117], W/T/L 37/299/34, matched TD +0.95% (interval undefined)
- 300 s all F111111 vs NeuroLKH-adapted: fleet -0.068 [-0.142, 0.033], W/T/L 16/313/41, matched TD -3.57% (interval undefined)

## Primary family, treatment gaps as failures

- 300 s all F111111 vs ALNS-Base: fleet -0.027 [-0.065, 0.011], W/T/L 4/352/14, matched TD +0.04%
- 300 s all F111111 vs PyVRP-ILS: fleet +0.008 [-0.098, 0.117], W/T/L 37/299/34, matched TD +0.95% (interval undefined)
- 300 s all F111111 vs NeuroLKH-adapted: fleet -0.068 [-0.142, 0.033], W/T/L 16/313/41, matched TD -3.57% (interval undefined)

## Primary family without high-load blocks

- 300 s all F111111 vs ALNS-Base: fleet -0.027 [-0.065, 0.011], W/T/L 4/352/14, matched TD +0.04%
- 300 s all F111111 vs PyVRP-ILS: fleet +0.008 [-0.098, 0.117], W/T/L 37/299/34, matched TD +0.95% (interval undefined)
- 300 s all F111111 vs NeuroLKH-adapted: fleet -0.068 [-0.142, 0.033], W/T/L 16/313/41, matched TD -3.57% (interval undefined)

## Adoption contrast without blocks run at high load

- 300 s all F111111 vs F111111-blind: fleet +0.062 [-0.014, 0.123], W/T/L 17/258/3, matched TD -0.04% (interval undefined)

## Adoption contrast on measured blocks only

- 300 s all F111111 vs F111111-blind: fleet +0.054 undefined, W/T/L 11/190/2, matched TD -0.09% (interval undefined)

## Primary family without blocks run at high load

- 300 s all F111111 vs ALNS-Base: fleet -0.030 [-0.080, 0.015], W/T/L 3/265/10, matched TD +0.20% (interval undefined)
- 300 s all F111111 vs PyVRP-ILS: fleet +0.007 [-0.109, 0.122], W/T/L 25/230/23, matched TD +0.89% (interval undefined)
- 300 s all F111111 vs NeuroLKH-adapted: fleet -0.070 [-0.158, 0.044], W/T/L 10/240/28, matched TD -3.24% (interval undefined)

## Primary family on measured blocks only

- 300 s all F111111 vs ALNS-Base: fleet -0.039 undefined, W/T/L 2/194/7, matched TD +0.27% (interval undefined)
- 300 s all F111111 vs PyVRP-ILS: fleet -0.001 undefined, W/T/L 16/171/16, matched TD +0.83% (interval undefined)
- 300 s all F111111 vs NeuroLKH-adapted: fleet -0.095 undefined, W/T/L 7/176/20, matched TD -3.33% (interval undefined)

## By size, unadjusted

- 300 s size_100 F111111 vs ALNS-Base: fleet -0.011 [-0.038, 0.014], W/T/L 3/271/6, matched TD -0.20%
- 300 s size_200 F111111 vs ALNS-Base: fleet +0.000 [-0.067, 0.067], W/T/L 1/58/1, matched TD +1.16%
- 300 s size_400 F111111 vs ALNS-Base: fleet -0.233 [-0.486, 0.000], W/T/L 0/23/7, matched TD +0.05%
- 300 s size_100 F111111 vs PyVRP-ILS: fleet -0.071 [-0.164, 0.033], W/T/L 4/252/24, matched TD +1.09%
- 300 s size_200 F111111 vs PyVRP-ILS: fleet +0.233 [0.000, 0.386], W/T/L 19/36/5, matched TD +0.73%
- 300 s size_400 F111111 vs PyVRP-ILS: fleet +0.300 [0.000, 0.750], W/T/L 14/11/5, matched TD +0.11% (interval undefined)
- 300 s size_100 F111111 vs NeuroLKH-adapted: fleet -0.046 [-0.129, 0.057], W/T/L 9/249/22, matched TD -5.60%
- 300 s size_200 F111111 vs NeuroLKH-adapted: fleet -0.167 [-0.250, 0.000], W/T/L 0/50/10, matched TD +1.44%
- 300 s size_400 F111111 vs NeuroLKH-adapted: fleet -0.067 [-0.350, 0.200], W/T/L 7/14/9, matched TD +5.34% (interval undefined)

## Other configuration, unadjusted

- 300 s all F111111-blind vs ALNS-Base-noges: fleet +0.116 [0.002, 0.181], W/T/L 49/315/6, matched TD -0.20%
- 300 s all F111111-blind vs PyVRP-ILS: fleet -0.030 [-0.139, 0.089], W/T/L 34/291/45, matched TD +0.83% (interval undefined)
- 300 s all F111111-blind vs NeuroLKH-adapted: fleet -0.135 [-0.236, -0.012], W/T/L 12/296/62, matched TD -4.64% (interval undefined)

## Budgets, unadjusted

- 60 s all F111111 vs ALNS-Base: fleet -0.024 [-0.049, -0.000], W/T/L 5/351/14, matched TD +0.03%
- 60 s size_100 F111111 vs ALNS-Base: fleet -0.014 [-0.033, 0.000], W/T/L 2/272/6, matched TD +0.27%
- 60 s size_200 F111111 vs ALNS-Base: fleet -0.017 [-0.100, 0.043], W/T/L 2/55/3, matched TD +0.39%
- 60 s size_400 F111111 vs ALNS-Base: fleet -0.133 [-0.333, 0.067], W/T/L 1/24/5, matched TD -2.91%
- 60 s all F111111 vs PyVRP-ILS: fleet +0.032 [-0.060, 0.128], W/T/L 54/274/42, matched TD +1.28% (interval undefined)
- 60 s size_100 F111111 vs PyVRP-ILS: fleet -0.075 [-0.154, 0.000], W/T/L 10/239/31, matched TD +1.46%
- 60 s size_200 F111111 vs PyVRP-ILS: fleet +0.367 [0.000, 0.643], W/T/L 28/26/6, matched TD +0.59% (interval undefined)
- 60 s size_400 F111111 vs PyVRP-ILS: fleet +0.367 [0.000, 0.857], W/T/L 16/9/5, matched TD +1.00% (interval undefined)
- 60 s all F111111 vs NeuroLKH-adapted: fleet -0.032 [-0.095, 0.036], W/T/L 30/298/42, matched TD -3.74% (interval undefined)
- 60 s size_100 F111111 vs NeuroLKH-adapted: fleet -0.054 [-0.117, 0.015], W/T/L 14/237/29, matched TD -5.07%
- 60 s size_200 F111111 vs NeuroLKH-adapted: fleet -0.167 [-0.287, 0.000], W/T/L 1/48/11, matched TD +3.32%
- 60 s size_400 F111111 vs NeuroLKH-adapted: fleet +0.433 [0.000, 0.771], W/T/L 15/13/2, matched TD -5.36% (interval undefined)
- 10 s all F111111 vs ALNS-Base: fleet +0.073 [-0.040, 0.194], W/T/L 104/189/77, matched TD +3.87% (interval undefined)
- 10 s size_100 F111111 vs ALNS-Base: fleet +0.104 [-0.022, 0.230], W/T/L 74/161/45, matched TD +3.79%
- 10 s size_200 F111111 vs ALNS-Base: fleet +0.167 [-0.129, 0.460], W/T/L 22/26/12, matched TD +5.16% (interval undefined)
- 10 s size_400 F111111 vs ALNS-Base: fleet -0.400 [-0.900, 0.120], W/T/L 8/2/20, matched TD +2.07% (interval undefined)
- 10 s all F111111 vs PyVRP-ILS: fleet -0.522 [-0.654, -0.354], W/T/L 16/145/209, matched TD none (interval undefined)
- 10 s size_100 F111111 vs PyVRP-ILS: fleet -0.529 [-0.677, -0.306], W/T/L 1/130/149, matched TD +6.24%
- 10 s size_200 F111111 vs PyVRP-ILS: fleet -0.350 [-0.700, -0.057], W/T/L 12/15/33, matched TD +10.97% (interval undefined)
- 10 s size_400 F111111 vs PyVRP-ILS: fleet -0.800 [-1.000, -0.400], W/T/L 3/0/27, matched TD none (interval undefined)
- 10 s all F111111 vs NeuroLKH-adapted: fleet -0.573 [-0.690, -0.372], W/T/L 14/130/226, matched TD -0.00% (interval undefined)
- 10 s size_100 F111111 vs NeuroLKH-adapted: fleet -0.571 [-0.706, -0.306], W/T/L 2/116/162, matched TD -1.90%
- 10 s size_200 F111111 vs NeuroLKH-adapted: fleet -0.650 [-0.867, -0.433], W/T/L 4/13/43, matched TD +8.25% (interval undefined)
- 10 s size_400 F111111 vs NeuroLKH-adapted: fleet -0.433 [-1.000, 0.067], W/T/L 8/1/21, matched TD +1.24% (interval undefined)

## Run conditions

```json
{
 "cells": 8060,
 "power_at_start": {
  "AC": 8060
 },
 "started_above_load_limit": 0,
 "median_load1": 5.169921875,
 "late_returns": 350,
 "no_valid_solution": 5,
 "error_kinds": {
  "returncode 1": 5,
  "not feasible": 5
 },
 "ges_cells_with_ges_capture": 2218,
 "ges_cells": 2400
}
```
