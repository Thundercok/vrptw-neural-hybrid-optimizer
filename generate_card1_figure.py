# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path

# High-resolution figure: 16 x 5.8 inches, 300 DPI
fig, ax = plt.subplots(figsize=(16, 5.8), dpi=300)
ax.set_xlim(0, 100)
ax.set_ylim(0, 36)
ax.axis('off')
fig.patch.set_facecolor('#ffffff')

# Outer container
bg = patches.FancyBboxPatch((0.5, 0.5), 99, 35, boxstyle="round,pad=0.2,rounding_size=1.2",
                             facecolor='#f8fafc', edgecolor='#cbd5e1', linewidth=2.0)
ax.add_patch(bg)

# ================= 1. LEFT PANEL: DEPOT LOGISTICS HUB =================
depot_box = patches.FancyBboxPatch((2, 2.5), 20, 31, boxstyle="round,pad=0.2,rounding_size=1.0",
                                   facecolor='#eff6ff', edgecolor='#3b82f6', linewidth=2.2)
ax.add_patch(depot_box)

# Header badge
dh_badge = patches.FancyBboxPatch((3.5, 29.0), 17, 3.4, boxstyle="round,pad=0.1,rounding_size=0.6",
                                  facecolor='#1d4ed8', edgecolor='none')
ax.add_patch(dh_badge)
ax.text(12.0, 30.7, "KHO TRUNG TÂM", fontsize=14.5, fontweight='bold', color='#ffffff', ha='center', va='center')

ax.text(12.0, 27.2, "DEPOT (X₀, Y₀) = (40, 50)", fontsize=12.5, fontweight='bold', color='#1e3a8a', ha='center')

# Modern Sleek Warehouse / Logistics Center Graphic
# Main building block
wh_main = patches.FancyBboxPatch((4.5, 14.2), 15.0, 10.5, boxstyle="round,pad=0.1,rounding_size=0.8",
                                facecolor='#ffffff', edgecolor='#2563eb', linewidth=2.2, zorder=5)
ax.add_patch(wh_main)

# Roof header
wh_roof = patches.FancyBboxPatch((4.0, 22.0), 16.0, 3.2, boxstyle="round,pad=0.1,rounding_size=0.6",
                                 facecolor='#1d4ed8', edgecolor='#1e40af', linewidth=1.5, zorder=6)
ax.add_patch(wh_roof)
ax.text(12.0, 23.6, "NAMI LOGISTICS HUB", fontsize=10.5, fontweight='bold', color='#ffffff', ha='center', va='center', zorder=7)

# 3 Loading bays (docks)
for bi in range(3):
    bx = 5.8 + bi * 4.6
    dock = patches.FancyBboxPatch((bx, 15.0), 3.4, 5.5, boxstyle="round,pad=0.1,rounding_size=0.4",
                                  facecolor='#e2e8f0', edgecolor='#64748b', linewidth=1.2, zorder=6)
    ax.add_patch(dock)
    # Shutter lines
    for si in range(3):
        ax.plot([bx+0.4, bx+3.0], [16.2 + si*1.3, 16.2 + si*1.3], color='#94a3b8', lw=1.2, zorder=7)
    # Dock label
    col_dock = ['#2563eb', '#16a34a', '#9333ea'][bi]
    ax.text(bx+1.7, 19.3, f"Cửa {bi+1}", fontsize=8.5, fontweight='bold', color=col_dock, ha='center', zorder=8)

# Star marker for Depot
ax.scatter([12.0], [12.2], s=200, c='#f59e0b', marker='*', edgecolors='#b45309', linewidth=1.2, zorder=8)

# Specs at bottom
ax.text(12.0, 9.2, "Tải trọng xe: Q = 200", fontsize=13, fontweight='bold', color='#047857', ha='center',
        bbox=dict(boxstyle="round,pad=0.3", fc="#ecfdf5", ec="#a7f3d0", lw=1.2))
ax.text(12.0, 6.2, "Khung giờ: [08:00 - 18:00]", fontsize=11.5, fontweight='bold', color='#334155', ha='center')
ax.text(12.0, 3.8, "3 Đội xe điều phối đồng thời", fontsize=12, fontweight='bold', color='#1d4ed8', ha='center')

# ================= 2. CENTER PANEL: 3 OPTIMAL ROUTES NETWORK =================
net_box = patches.FancyBboxPatch((23.5, 2.5), 48.5, 31, boxstyle="round,pad=0.2,rounding_size=1.0",
                                 facecolor='#ffffff', edgecolor='#94a3b8', linewidth=2.0)
ax.add_patch(net_box)

# Header banner
ax.text(47.75, 31.0, "MẠNG LƯỚI ĐIỀU PHỐI 3 LỘ TRÌNH TỐI ƯU (KHÔNG GIAO CẮT)", 
        fontsize=14.5, fontweight='bold', color='#0f172a', ha='center', va='center')

# Customer nodes definitions
# Route 1 (Blue)
r1_nodes = [(32.0, 24.5, "C₁", "q=35", "[08:30 - 09:30]"),
            (46.5, 25.5, "C₂", "q=45", "[09:45 - 11:00]"),
            (57.5, 23.5, "C₃", "q=40", "[11:15 - 12:30]")]

# Route 2 (Green)
r2_nodes = [(35.0, 16.5, "C₄", "q=60", "[08:45 - 10:15]"),
            (53.0, 16.0, "C₅", "q=70", "[10:30 - 12:00]")]

# Route 3 (Purple)
r3_nodes = [(33.0, 8.5, "C₆", "q=50", "[09:00 - 10:30]"),
            (50.5, 8.0, "C₇", "q=80", "[11:00 - 12:30]")]

# Draw Route 1 Arrows & Connections
ax.annotate('', xy=(30.2, 24.5), xytext=(20.0, 22.0),
            arrowprops=dict(arrowstyle="-|>", color='#2563eb', lw=3.2, mutation_scale=18))
ax.annotate('', xy=(44.7, 25.5), xytext=(33.8, 24.5),
            arrowprops=dict(arrowstyle="-|>", color='#2563eb', lw=3.2, mutation_scale=18))
ax.annotate('', xy=(55.7, 23.5), xytext=(48.3, 25.5),
            arrowprops=dict(arrowstyle="-|>", color='#2563eb', lw=3.2, mutation_scale=18))
# Return edge
ax.annotate('', xy=(20.0, 20.5), xytext=(59.0, 22.5),
            arrowprops=dict(arrowstyle="-|>", color='#2563eb', lw=2.4, linestyle='--',
                            connectionstyle="arc3,rad=-0.16", mutation_scale=15))

# Draw Route 2 Arrows & Connections
ax.annotate('', xy=(33.2, 16.5), xytext=(20.0, 18.0),
            arrowprops=dict(arrowstyle="-|>", color='#16a34a', lw=3.2, mutation_scale=18))
ax.annotate('', xy=(51.2, 16.0), xytext=(36.8, 16.5),
            arrowprops=dict(arrowstyle="-|>", color='#16a34a', lw=3.2, mutation_scale=18))
# Return edge
ax.annotate('', xy=(20.0, 16.5), xytext=(54.5, 14.5),
            arrowprops=dict(arrowstyle="-|>", color='#16a34a', lw=2.4, linestyle='--',
                            connectionstyle="arc3,rad=-0.11", mutation_scale=15))

# Draw Route 3 Arrows & Connections
ax.annotate('', xy=(31.2, 8.5), xytext=(20.0, 14.5),
            arrowprops=dict(arrowstyle="-|>", color='#9333ea', lw=3.2, mutation_scale=18))
ax.annotate('', xy=(48.7, 8.0), xytext=(34.8, 8.5),
            arrowprops=dict(arrowstyle="-|>", color='#9333ea', lw=3.2, mutation_scale=18))
# Return edge
ax.annotate('', xy=(20.0, 13.0), xytext=(52.0, 6.8),
            arrowprops=dict(arrowstyle="-|>", color='#9333ea', lw=2.4, linestyle='--',
                            connectionstyle="arc3,rad=-0.09", mutation_scale=15))

# Customer Node Drawer
def draw_customer_node(x, y, label, demand, tw, color):
    # Circle node
    circle = patches.Circle((x, y), 1.8, facecolor='#ffffff', edgecolor=color, linewidth=3.2, zorder=10)
    ax.add_patch(circle)
    ax.text(x, y-0.1, label, fontsize=13.5, fontweight='bold', color='#0f172a', ha='center', va='center', zorder=11)
    
    # Demand pill (Top)
    dpill = patches.FancyBboxPatch((x-2.4, y+2.1), 4.8, 1.8, boxstyle="round,pad=0.1,rounding_size=0.4",
                                   facecolor=color, edgecolor='none', zorder=12)
    ax.add_patch(dpill)
    ax.text(x, y+2.95, demand, fontsize=11, fontweight='bold', color='#ffffff', ha='center', va='center', zorder=13)
    
    # Time window badge (Bottom)
    ax.text(x, y-2.6, tw, fontsize=11, fontweight='bold', color='#1e293b', ha='center', va='center', zorder=11,
            bbox=dict(boxstyle="round,pad=0.2", fc="#ffffff", ec="#cbd5e1", lw=1.0))

for x, y, lbl, dem, tw in r1_nodes:
    draw_customer_node(x, y, lbl, dem, tw, '#2563eb')

for x, y, lbl, dem, tw in r2_nodes:
    draw_customer_node(x, y, lbl, dem, tw, '#16a34a')

for x, y, lbl, dem, tw in r3_nodes:
    draw_customer_node(x, y, lbl, dem, tw, '#9333ea')

# Route gauges on the right side of center box
r1_gauge = patches.FancyBboxPatch((63.5, 22.8), 7.6, 3.6, boxstyle="round,pad=0.1,rounding_size=0.5",
                                  facecolor='#eff6ff', edgecolor='#3b82f6', linewidth=1.8)
ax.add_patch(r1_gauge)
ax.text(67.3, 25.2, "Tuyến 1 (Xanh)", fontsize=11, fontweight='bold', color='#1e40af', ha='center')
ax.text(67.3, 23.6, "Tải: 120/200", fontsize=11.5, fontweight='bold', color='#2563eb', ha='center')

r2_gauge = patches.FancyBboxPatch((63.5, 14.8), 7.6, 3.6, boxstyle="round,pad=0.1,rounding_size=0.5",
                                  facecolor='#f0fdf4', edgecolor='#16a34a', linewidth=1.8)
ax.add_patch(r2_gauge)
ax.text(67.3, 17.2, "Tuyến 2 (Lục)", fontsize=11, fontweight='bold', color='#166534', ha='center')
ax.text(67.3, 15.6, "Tải: 130/200", fontsize=11.5, fontweight='bold', color='#16a34a', ha='center')

r3_gauge = patches.FancyBboxPatch((63.5, 6.8), 7.6, 3.6, boxstyle="round,pad=0.1,rounding_size=0.5",
                                  facecolor='#faf5ff', edgecolor='#9333ea', linewidth=1.8)
ax.add_patch(r3_gauge)
ax.text(67.3, 9.2, "Tuyến 3 (Tím)", fontsize=11, fontweight='bold', color='#6b21a8', ha='center')
ax.text(67.3, 7.6, "Tải: 130/200", fontsize=11.5, fontweight='bold', color='#9333ea', ha='center')

# ================= 3. RIGHT PANEL: 2 CORE HARD CONSTRAINTS =================
rule_box = patches.FancyBboxPatch((73.5, 2.5), 24.5, 31, boxstyle="round,pad=0.2,rounding_size=1.0",
                                  facecolor='#ffffff', edgecolor='#cbd5e1', linewidth=2.0)
ax.add_patch(rule_box)

rh_badge = patches.FancyBboxPatch((75.0, 29.0), 21.5, 3.4, boxstyle="round,pad=0.1,rounding_size=0.6",
                                  facecolor='#0a193b', edgecolor='none')
ax.add_patch(rh_badge)
ax.text(85.75, 30.7, "RÀNG BUỘC CỐT LÕI", fontsize=14.5, fontweight='bold', color='#ffffff', ha='center', va='center')

# Constraint 1: Capacity
c1_box = patches.FancyBboxPatch((75.0, 16.0), 21.5, 11.5, boxstyle="round,pad=0.2,rounding_size=0.8",
                                facecolor='#f0fdf4', edgecolor='#16a34a', linewidth=2.0)
ax.add_patch(c1_box)
ax.text(76.5, 24.8, "[RÀNG BUỘC TẢI TRỌNG]", fontsize=13, fontweight='bold', color='#166534')
ax.text(76.5, 21.6, "∑ qᵢ ≤ Q = 200 đơn vị", fontsize=15.5, fontweight='bold', color='#047857')
ax.text(76.5, 19.0, "• Tuyệt đối không chở quá tải", fontsize=12, fontweight='bold', color='#14532d')
ax.text(76.5, 17.2, "• 100% Khả thi trên mọi tuyến", fontsize=12, fontweight='bold', color='#15803d')

# Constraint 2: Time Window
c2_box = patches.FancyBboxPatch((75.0, 3.8), 21.5, 11.5, boxstyle="round,pad=0.2,rounding_size=0.8",
                                facecolor='#fef2f2', edgecolor='#dc2626', linewidth=2.0)
ax.add_patch(c2_box)
ax.text(76.5, 12.6, "[RÀNG BUỘC KHUNG GIỜ]", fontsize=13, fontweight='bold', color='#991b1b')
ax.text(76.5, 9.4, "Eᵢ ≤ tᵢ ≤ Lᵢ (tại mỗi khách)", fontsize=15.5, fontweight='bold', color='#b91c1c')
ax.text(76.5, 6.8, "• Đến sớm: Chờ • Trễ: Phạt nặng", fontsize=12, fontweight='bold', color='#7f1d1d')
ax.text(76.5, 5.0, "• 0 Vi phạm thời gian (Strict)", fontsize=12, fontweight='bold', color='#dc2626')

plt.tight_layout()
out_path = 'fig1_vrptw_network_hd.png'
plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='#ffffff')
plt.close()
print(f"Generated {out_path} with polished warehouse graphics successfully!")
