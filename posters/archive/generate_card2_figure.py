# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

np.random.seed(42)

fig, axes = plt.subplots(1, 3, figsize=(16, 5.8), dpi=300)
fig.patch.set_facecolor('#ffffff')

# Common depot
depot = (50, 50)

# ================= 1. DOMAIN C (CLUSTERED) =================
ax1 = axes[0]
ax1.set_facecolor('#f8fafc')
ax1.set_xlim(0, 100)
ax1.set_ylim(0, 100)
ax1.set_xticks([])
ax1.set_yticks([])

# 3 Cluster centers
c_centers = [(26, 75), (74, 72), (50, 22)]
c_labels = ["Cụm 1 (Tây Bắc)", "Cụm 2 (Đông Bắc)", "Cụm 3 (Nam)"]
c_label_y = [56, 53, 9] # Explicit clean Y positions avoiding depot

for i, (cx, cy) in enumerate(c_centers):
    # Cluster halo
    halo = patches.Circle((cx, cy), 16, facecolor='#dbeafe', edgecolor='#3b82f6', alpha=0.55, linewidth=2.0, linestyle='--', zorder=2)
    ax1.add_patch(halo)
    # Cluster Label
    ax1.text(cx, c_label_y[i], c_labels[i], fontsize=12, fontweight='bold', color='#1d4ed8', ha='center', zorder=5,
             bbox=dict(boxstyle="round,pad=0.25", fc="#ffffff", ec="#bfdbfe", lw=1.2))
    # Dots
    pts_x = np.random.normal(cx, 4.8, 25)
    pts_y = np.random.normal(cy, 4.8, 25)
    ax1.scatter(pts_x, pts_y, c='#1d4ed8', s=65, edgecolors='#ffffff', linewidth=1.2, zorder=4)

# Depot
ax1.scatter([depot[0]], [depot[1]], c='#f59e0b', s=360, marker='*', edgecolors='#b45309', linewidth=2.0, zorder=6)
ax1.text(depot[0], depot[1]-6.5, "KHO (DEPOT)", fontsize=13, fontweight='bold', color='#78350f', ha='center', zorder=7,
         bbox=dict(boxstyle="round,pad=0.25", fc="#fffbeb", ec="#fcd34d", lw=1.2))

# Title & Footer
ax1.set_title("MIỀN C (CLUSTERED)\nCỤM KHÁCH HÀNG TẬP TRUNG", fontsize=15, fontweight='bold', color='#1e3a8a', pad=12)
ax1.text(50, 4.5, "Đặc trưng: Mật độ nội cụm cao • Di chuyển liên cụm lớn", 
         fontsize=11.5, fontweight='bold', color='#1e40af', ha='center', 
         bbox=dict(boxstyle="round,pad=0.4", fc="#eff6ff", ec="#93c5fd", lw=1.5))
for spine in ax1.spines.values():
    spine.set_color('#3b82f6')
    spine.set_linewidth(2.2)

# ================= 2. DOMAIN R (UNIFORM / RANDOM) =================
ax2 = axes[1]
ax2.set_facecolor('#f8fafc')
ax2.set_xlim(0, 100)
ax2.set_ylim(0, 100)
ax2.set_xticks([])
ax2.set_yticks([])

# Uniform random points
rx = np.random.uniform(8, 92, 75)
ry = np.random.uniform(8, 92, 75)
ax2.scatter(rx, ry, c='#16a34a', s=65, edgecolors='#ffffff', linewidth=1.2, zorder=4)

# Depot
ax2.scatter([depot[0]], [depot[1]], c='#f59e0b', s=360, marker='*', edgecolors='#b45309', linewidth=2.0, zorder=6)
ax2.text(depot[0], depot[1]-6.5, "KHO (DEPOT)", fontsize=13, fontweight='bold', color='#78350f', ha='center', zorder=7,
         bbox=dict(boxstyle="round,pad=0.25", fc="#fffbeb", ec="#fcd34d", lw=1.2))

# Title & Footer
ax2.set_title("MIỀN R (UNIFORM / RANDOM)\nPHÂN BỐ ĐỒNG ĐỀU NGẪU NHIÊN", fontsize=15, fontweight='bold', color='#166534', pad=12)
ax2.text(50, 4.5, "Đặc trưng: Toạ độ đồng xác suất • Cấu trúc hình học mở", 
         fontsize=11.5, fontweight='bold', color='#15803d', ha='center', 
         bbox=dict(boxstyle="round,pad=0.4", fc="#f0fdf4", ec="#86efac", lw=1.5))
for spine in ax2.spines.values():
    spine.set_color('#16a34a')
    spine.set_linewidth(2.2)

# ================= 3. DOMAIN RC (RANDOM-CLUSTERED) =================
ax3 = axes[2]
ax3.set_facecolor('#f8fafc')
ax3.set_xlim(0, 100)
ax3.set_ylim(0, 100)
ax3.set_xticks([])
ax3.set_yticks([])

# 2 Dense clusters
rc_centers = [(28, 72), (76, 25)]
rc_labels = ["Cụm Đô Thị A", "Cụm Đô Thị B"]
rc_label_pos = [(28, 53), (76, 9)] # Clean placement below halos

for i, (cx, cy) in enumerate(rc_centers):
    halo = patches.Circle((cx, cy), 15, facecolor='#fed7aa', edgecolor='#f97316', alpha=0.6, linewidth=2.0, linestyle='--', zorder=2)
    ax3.add_patch(halo)
    ax3.text(rc_label_pos[i][0], rc_label_pos[i][1], rc_labels[i], fontsize=12, fontweight='bold', color='#c2410c', ha='center', zorder=5,
             bbox=dict(boxstyle="round,pad=0.25", fc="#ffffff", ec="#fed7aa", lw=1.2))
    pts_x = np.random.normal(cx, 4.5, 22)
    pts_y = np.random.normal(cy, 4.5, 22)
    ax3.scatter(pts_x, pts_y, c='#ea580c', s=65, edgecolors='#ffffff', linewidth=1.2, zorder=4)

# Scattered points
sx = np.random.uniform(8, 92, 30)
sy = np.random.uniform(8, 92, 30)
ax3.scatter(sx, sy, c='#9a3412', s=50, edgecolors='#ffffff', linewidth=1.0, alpha=0.9, zorder=4)
ax3.text(50, 93, "Khách Vệ Tinh Phân Tán", fontsize=12, fontweight='bold', color='#9a3412', ha='center',
         bbox=dict(boxstyle="round,pad=0.25", fc="#fff7ed", ec="#fdba74", lw=1.2))

# Depot
ax3.scatter([depot[0]], [depot[1]], c='#f59e0b', s=360, marker='*', edgecolors='#b45309', linewidth=2.0, zorder=6)
ax3.text(depot[0], depot[1]-6.5, "KHO (DEPOT)", fontsize=13, fontweight='bold', color='#78350f', ha='center', zorder=7,
         bbox=dict(boxstyle="round,pad=0.25", fc="#fffbeb", ec="#fcd34d", lw=1.2))

# Title & Footer
ax3.set_title("MIỀN RC (RANDOM-CLUSTERED)\nCẤU TRÚC HỖN HỢP PHỨC TẠP", fontsize=15, fontweight='bold', color='#9a3412', pad=12)
ax3.text(50, 4.5, "Đặc trưng: Kết hợp cụm đô thị + Điểm giao hàng vệ tinh", 
         fontsize=11.5, fontweight='bold', color='#c2410c', ha='center', 
         bbox=dict(boxstyle="round,pad=0.4", fc="#fff7ed", ec="#fed7aa", lw=1.5))
for spine in ax3.spines.values():
    spine.set_color('#ea580c')
    spine.set_linewidth(2.2)

plt.tight_layout()
out_path = 'fig2_benchmark_domains_hd.png'
plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='#ffffff')
plt.close()
print(f"Generated {out_path} with perfectly positioned labels successfully!")
