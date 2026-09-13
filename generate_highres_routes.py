# -*- coding: utf-8 -*-
import json
import os
import matplotlib.pyplot as plt
import numpy as np

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))

def parse_solomon(file_path):
    with open(file_path, 'r') as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    data_start = -1
    for i, line in enumerate(lines):
        parts = line.split()
        if len(parts) >= 7 and parts[0].isdigit():
            data_start = i
            break
    coords = {}
    demands = {}
    for line in lines[data_start:]:
        parts = line.split()
        if len(parts) >= 7 and parts[0].isdigit():
            cid = int(parts[0])
            coords[cid] = (float(parts[1]), float(parts[2]))
            demands[cid] = float(parts[3])
    return coords, demands

def plot_solution(instance_name, coords, routes, out_path, title_text):
    plt.figure(figsize=(7.5, 6.0), dpi=300)
    ax = plt.gca()
    ax.set_facecolor('#ffffff')

    # Color palette for routes
    palette = [
        '#2563eb', '#dc2626', '#16a34a', '#d97706', '#9333ea', 
        '#0891b2', '#ea580c', '#4f46e5', '#059669', '#b91c1c',
        '#0284c7', '#7c3aed', '#c026d3', '#ca8a04', '#15803d',
        '#e11d48', '#0d9488', '#4338ca', '#b45309'
    ]

    # Plot customer nodes
    cust_x = [coords[i][0] for i in coords if i != 0]
    cust_y = [coords[i][1] for i in coords if i != 0]
    ax.scatter(cust_x, cust_y, c='#475569', s=35, zorder=3, edgecolors='#1e293b', linewidth=0.8, alpha=0.85)

    # Plot routes
    depot_x, depot_y = coords[0]
    for r_idx, route in enumerate(routes):
        col = palette[r_idx % len(palette)]
        full_route = [0] + route + [0]
        rx = [coords[n][0] for n in full_route]
        ry = [coords[n][1] for n in full_route]
        ax.plot(rx, ry, color=col, linewidth=2.0, alpha=0.85, zorder=2)
        
        # Add subtle directional arrow in the middle of first leg
        if len(full_route) >= 3:
            mid = len(full_route) // 2
            x1, y1 = coords[full_route[mid-1]]
            x2, y2 = coords[full_route[mid]]
            dx, dy = (x2 - x1) * 0.25, (y2 - y1) * 0.25
            ax.annotate('', xy=(x1 + dx + dx*0.1, y1 + dy + dy*0.1), xytext=(x1 + dx, y1 + dy),
                        arrowprops=dict(arrowstyle="-|>", color=col, lw=1.5, mutation_scale=10),
                        zorder=4)

    # Plot depot
    ax.scatter([depot_x], [depot_y], c='#f59e0b', s=200, marker='*', zorder=5, edgecolors='#b45309', linewidth=1.5)
    ax.annotate(' DEPOT', (depot_x, depot_y), textcoords="offset points", xytext=(6,-4),
                fontsize=11, fontweight='bold', color='#78350f', zorder=6)

    # Styling
    ax.grid(True, linestyle='--', alpha=0.35, color='#cbd5e1')
    ax.set_title(title_text, fontsize=13, fontweight='bold', color='#0f172a', pad=10)
    ax.tick_params(colors='#64748b', labelsize=9)
    for spine in ax.spines.values():
        spine.set_color('#cbd5e1')
        spine.set_linewidth(1.2)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='#ffffff')
    plt.close()
    print(f"Exported {out_path}")

# Load R101
r101_coords, _ = parse_solomon(os.path.join(WORKSPACE_DIR, 'data/Solomon/r101.txt'))
with open(os.path.join(WORKSPACE_DIR, 'results/ultimate-publication-suite/solomon_short_horizon/Hybrid-DDQN/elite_plans/R101.json')) as f:
    r101_sol = json.load(f)

plot_solution('R101', r101_coords, r101_sol['routes'], 
              os.path.join(WORKSPACE_DIR, 'route_r101_hd.png'),
              f"Lộ trình R101 (Hybrid-DDQN: NV={r101_sol['nv']}, TD={r101_sol['cost']:.1f})")

# Load RC101
rc101_coords, _ = parse_solomon(os.path.join(WORKSPACE_DIR, 'data/Solomon/rc101.txt'))
with open(os.path.join(WORKSPACE_DIR, 'results/ultimate-publication-suite/solomon_short_horizon/Hybrid-DDQN/elite_plans/RC101.json')) as f:
    rc101_sol = json.load(f)

plot_solution('RC101', rc101_coords, rc101_sol['routes'], 
              os.path.join(WORKSPACE_DIR, 'route_rc101_hd.png'),
              f"Lộ trình RC101 (Hybrid-DDQN: NV={rc101_sol['nv']}, TD={rc101_sol['cost']:.1f})")

