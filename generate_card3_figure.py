# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import matplotlib.patches as patches

fig, ax = plt.subplots(figsize=(16, 6.2), dpi=300)
ax.set_xlim(0, 100)
ax.set_ylim(0, 48)
ax.axis('off')
fig.patch.set_facecolor('#ffffff')

# Background container
bg = patches.FancyBboxPatch((0.5, 0.5), 99, 47, boxstyle="round,pad=0.2,rounding_size=1.5",
                             facecolor='#f8fafc', edgecolor='#cbd5e1', linewidth=1.5)
ax.add_patch(bg)

# Title bar
tbar = patches.FancyBboxPatch((2, 41.5), 96, 5, boxstyle="round,pad=0.1,rounding_size=0.8",
                               facecolor='#0a193b', edgecolor='none')
ax.add_patch(tbar)
ax.text(50, 44.0, "KIẾN TRÚC PHÂN CẤP 4 TẦNG: HYBRID DDQN - ALNS & SET PARTITIONING", 
        fontsize=14, fontweight='bold', color='#ffffff', ha='center', va='center')

# ================= TIER 1: MACRO DDQN =================
t1_box = patches.FancyBboxPatch((2, 31), 96, 8.5, boxstyle="round,pad=0.2,rounding_size=1.0",
                                facecolor='#eff6ff', edgecolor='#3b82f6', linewidth=2.0)
ax.add_patch(t1_box)

# Badge
b1 = patches.FancyBboxPatch((3.5, 35.5), 18, 3.2, boxstyle="round,pad=0.1,rounding_size=0.6",
                             facecolor='#2563eb', edgecolor='none')
ax.add_patch(b1)
ax.text(12.5, 37.1, "TẦNG 1: MACRO DDQN", fontsize=11, fontweight='bold', color='#ffffff', ha='center', va='center')

# Content
ax.text(3.5, 33.2, "Vector trạng thái 13D s_k^macro (Độ bế tắc, Entropy, Đa dạng quần thể, Nhiệt độ SA, Tiến độ thời gian)", 
        fontsize=10.5, color='#1e3a8a', fontweight='600')

# Action pills (7 modes)
modes = ["Default", "Intensify", "Diversify", "TW-Rescue", "Pool-Recombine", "Route-Reduce", "Infeasible-Descent"]
ax.text(23, 37.1, "7 Chế độ thích ứng:", fontsize=10.5, fontweight='bold', color='#1e40af', va='center')
for i, m in enumerate(modes):
    mpill = patches.FancyBboxPatch((36 + i*9.0, 35.7), 8.5, 2.8, boxstyle="round,pad=0.1,rounding_size=0.5",
                                   facecolor='#ffffff', edgecolor='#60a5fa', linewidth=1.2)
    ax.add_patch(mpill)
    ax.text(36 + i*9.0 + 4.25, 37.1, m, fontsize=8.5, fontweight='bold', color='#1d4ed8', ha='center', va='center')

# Down arrow 1
ax.annotate('', xy=(50, 30.2), xytext=(50, 31.8),
            arrowprops=dict(arrowstyle="-|>", color='#2563eb', lw=2.5, mutation_scale=15))

# ================= TIER 2: MICRO DDQN =================
t2_box = patches.FancyBboxPatch((2, 21), 96, 8.5, boxstyle="round,pad=0.2,rounding_size=1.0",
                                facecolor='#faf5ff', edgecolor='#9333ea', linewidth=2.0)
ax.add_patch(t2_box)

# Badge
b2 = patches.FancyBboxPatch((3.5, 25.5), 18, 3.2, boxstyle="round,pad=0.1,rounding_size=0.6",
                             facecolor='#9333ea', edgecolor='none')
ax.add_patch(b2)
ax.text(12.5, 27.1, "TẦNG 2: MICRO DDQN", fontsize=11, fontweight='bold', color='#ffffff', ha='center', va='center')

# Content
ax.text(3.5, 23.2, "Vector trạng thái 20D s_k^micro (Đặc trưng giải pháp cục bộ, Tải trọng, Ràng buộc thời gian) + Chế độ Macro", 
        fontsize=10.5, color='#581c87', fontweight='600')

# Operators
ax.text(23, 27.1, "Không gian 65 Cặp toán tử thích ứng:", fontsize=10.5, fontweight='bold', color='#6b21a8', va='center')

op1 = patches.FancyBboxPatch((48, 25.7), 23, 2.8, boxstyle="round,pad=0.1,rounding_size=0.5",
                             facecolor='#ffffff', edgecolor='#c084fc', linewidth=1.2)
ax.add_patch(op1)
ax.text(59.5, 27.1, "13 Toán tử Phá huỷ (Destroy)", fontsize=9.5, fontweight='bold', color='#7e22ce', ha='center', va='center')

ax.text(72.5, 27.1, "×", fontsize=14, fontweight='bold', color='#9333ea', ha='center', va='center')

op2 = patches.FancyBboxPatch((74.5, 25.7), 22, 2.8, boxstyle="round,pad=0.1,rounding_size=0.5",
                             facecolor='#ffffff', edgecolor='#c084fc', linewidth=1.2)
ax.add_patch(op2)
ax.text(85.5, 27.1, "5 Toán tử Sửa chữa (Repair)", fontsize=9.5, fontweight='bold', color='#7e22ce', ha='center', va='center')

# Down arrow 2
ax.annotate('', xy=(50, 20.2), xytext=(50, 21.8),
            arrowprops=dict(arrowstyle="-|>", color='#9333ea', lw=2.5, mutation_scale=15))

# ================= TIER 3: GNN & LAC =================
t3_box = patches.FancyBboxPatch((2, 11), 96, 8.5, boxstyle="round,pad=0.2,rounding_size=1.0",
                                facecolor='#f0fdf4', edgecolor='#16a34a', linewidth=2.0)
ax.add_patch(t3_box)

# Badge
b3 = patches.FancyBboxPatch((3.5, 15.5), 18, 3.2, boxstyle="round,pad=0.1,rounding_size=0.6",
                             facecolor='#16a34a', edgecolor='none')
ax.add_patch(b3)
ax.text(12.5, 17.1, "TẦNG 3: GNN & LAC", fontsize=11, fontweight='bold', color='#ffffff', ha='center', va='center')

# Content
ax.text(3.5, 13.2, "Contrastive GNN 3-Layer (InfoNCE + BCE Loss) • Learned Acceptance Criterion MLP (9→64→48→32→1, H=80)", 
        fontsize=10.5, color='#14532d', fontweight='600')

# GNN and LAC pills
gnn_pill = patches.FancyBboxPatch((23, 15.7), 35, 2.8, boxstyle="round,pad=0.1,rounding_size=0.5",
                                   facecolor='#ffffff', edgecolor='#86efac', linewidth=1.2)
ax.add_patch(gnn_pill)
ax.text(40.5, 17.1, "Lọc sạch 98.74% cạnh tìm kiếm kém hứa hẹn", fontsize=9.5, fontweight='bold', color='#15803d', ha='center', va='center')

lac_pill = patches.FancyBboxPatch((60, 15.7), 36.5, 2.8, boxstyle="round,pad=0.1,rounding_size=0.5",
                                   facecolor='#ffffff', edgecolor='#86efac', linewidth=1.2)
ax.add_patch(lac_pill)
ax.text(78.25, 17.1, "Thẩm định nghiệm tương lai thay thế hoàn toàn SA", fontsize=9.5, fontweight='bold', color='#15803d', ha='center', va='center')

# Down arrow 3
ax.annotate('', xy=(50, 10.2), xytext=(50, 11.8),
            arrowprops=dict(arrowstyle="-|>", color='#16a34a', lw=2.5, mutation_scale=15))

# ================= TIER 4: SET PARTITIONING =================
t4_box = patches.FancyBboxPatch((2, 1), 96, 8.5, boxstyle="round,pad=0.2,rounding_size=1.0",
                                facecolor='#fffbeb', edgecolor='#d97706', linewidth=2.0)
ax.add_patch(t4_box)

# Badge
b4 = patches.FancyBboxPatch((3.5, 5.5), 18, 3.2, boxstyle="round,pad=0.1,rounding_size=0.6",
                             facecolor='#d97706', edgecolor='none')
ax.add_patch(b4)
ax.text(12.5, 7.1, "TẦNG 4: SET PARTITION", fontsize=11, fontweight='bold', color='#ffffff', ha='center', va='center')

# Content
ax.text(3.5, 3.2, "Dual-Slot Elite Route Archive (75% Lộ trình tối ưu + 25% Lộ trình đa dạng) • Bộ giải toán rời rạc HiGHS MILP", 
        fontsize=10.5, color='#78350f', fontweight='600')

# SP pill
sp_pill = patches.FancyBboxPatch((23, 5.7), 73.5, 2.8, boxstyle="round,pad=0.1,rounding_size=0.5",
                                 facecolor='#ffffff', edgecolor='#fcd34d', linewidth=1.2)
ax.add_patch(sp_pill)
ax.text(59.75, 7.1, "Tái tổ hợp tập lộ trình độc lập tối ưu toàn cục: min f(s) = M · N_V + D_T", 
        fontsize=10, fontweight='bold', color='#b45309', ha='center', va='center')

plt.tight_layout()
out_path = 'fig3_architecture_hd.png'
plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='#ffffff')
plt.close()
print(f"Generated {out_path} successfully!")
