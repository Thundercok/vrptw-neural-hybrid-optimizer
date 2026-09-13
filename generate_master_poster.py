#!/usr/bin/env python3
"""
Master Scientific Research Poster Generator for TDTU NCKHSV 2026
Format: ISO A1 Portrait (594mm x 841mm)
Author: Huynh Nhat Huy (MSSV: 523C0012)
Advisor: TS. Ho Thi Linh
Institution: Ton Duc Thang University (TDTU) - Faculty of Information Technology
"""

import base64
import os
import subprocess
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def get_base64_from_file(path):
    with open(path, "rb") as f:
        data = f.read()
    ext = os.path.splitext(path)[1].lower().replace(".", "")
    if ext == "jpg": ext = "jpeg"
    return f"data:image/{ext};base64," + base64.b64encode(data).decode("utf-8")

def main():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    figs_dir = os.path.join(base_dir, "docs", "figures")

    # 1. Architecture diagram: 3000x1612 high-res poster_architecture.png
    arch_b64 = get_base64_from_file(os.path.join(figs_dir, "poster_architecture.png"))

    # 2. Convergence curves: 4-panel convergence_curves.png (RC101, R101, C101, r1_2_1)
    conv_path = os.path.join(figs_dir, "convergence_curves.png")
    if os.path.exists(conv_path):
        conv_b64 = get_base64_from_file(conv_path)
    else:
        conv_b64 = get_base64_from_file(os.path.join(figs_dir, "anytime_convergence.png"))

    # 3. High-res Route maps & Boxplot from authentic assets
    res = subprocess.run(["git", "show", "07281e74:poster_v5.html"], cwd=base_dir, stdout=subprocess.PIPE, text=True)
    soup = BeautifulSoup(res.stdout, "html.parser")
    git_imgs = soup.find_all("img")
    
    r101_b64 = git_imgs[2]["src"]
    rc101_b64 = git_imgs[3]["src"]
    box_b64 = git_imgs[4]["src"]

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Poster NCKHSV 2026 - TDTU - Huỳnh Nhật Huy</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700;800;900&family=Inter:wght@400;500;600;700&family=Fira+Code:wght@400;500;600&display=swap" rel="stylesheet">
<style>
@page {{
  size: 594mm 841mm;
  margin: 0;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
  width: 594mm;
  height: 841mm;
  margin: 0;
  overflow: hidden;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
  background: #060919;
}}

.poster {{
  width: 594mm;
  height: 841mm;
  background: linear-gradient(155deg, #07091e 0%, #0c1236 20%, #0e1838 50%, #081226 80%, #050b1a 100%);
  position: relative;
  padding: 8.5mm 12.5mm 7.0mm 12.5mm;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 3.2mm;
  color: #dde4f0;
}}

/* Subtle ambient background glow */
.poster::before {{
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 20% 10%, rgba(99,102,241,0.08) 0%, transparent 60%),
    radial-gradient(ellipse 60% 40% at 80% 85%, rgba(59,130,246,0.06) 0%, transparent 50%),
    radial-gradient(ellipse 50% 30% at 50% 50%, rgba(139,92,246,0.04) 0%, transparent 40%);
  pointer-events: none;
  z-index: 0;
}}

.poster > * {{ position: relative; z-index: 1; }}

/* ═════════════════════════════════════════════════════════════════════
   HEADER BANNER
   ═════════════════════════════════════════════════════════════════════ */
.header {{
  text-align: center;
  padding: 4.8mm 8mm 4.2mm 8mm;
  background: linear-gradient(135deg, rgba(16,26,65,0.92), rgba(22,38,82,0.88));
  border: 1.2px solid rgba(99,130,255,0.35);
  border-radius: 10px;
  flex-shrink: 0;
  box-shadow: 0 6px 24px rgba(0,0,0,0.45);
}}

.header .category {{
  font-family: 'Montserrat', sans-serif;
  font-size: 8.8pt;
  font-weight: 800;
  letter-spacing: 2.8px;
  text-transform: uppercase;
  color: #60a5fa;
  margin-bottom: 1.8mm;
}}

.header .title {{
  font-family: 'Montserrat', sans-serif;
  font-size: 24pt;
  font-weight: 900;
  color: #ffffff;
  line-height: 1.15;
  margin-bottom: 1.4mm;
  text-shadow: 0 2px 10px rgba(0,0,0,0.6);
  letter-spacing: -0.3px;
}}

.header .title-accent {{
  font-family: 'Montserrat', sans-serif;
  font-size: 20pt;
  font-weight: 850;
  color: #fbbf24;
  line-height: 1.18;
  display: block;
  margin-bottom: 1.8mm;
  letter-spacing: -0.2px;
}}

.header .tags {{
  font-size: 8.2pt;
  font-weight: 700;
  color: #34d399;
  letter-spacing: 1.5px;
  margin-bottom: 2.0mm;
}}

.header .authors {{
  font-size: 9.0pt;
  color: #94a3b8;
  line-height: 1.45;
}}
.header .authors strong {{ color: #f1f5f9; font-weight: 700; }}

/* ═════════════════════════════════════════════════════════════════════
   KPI STRIP (5 KEY METRICS)
   ═════════════════════════════════════════════════════════════════════ */
.kpi-strip {{
  display: flex;
  gap: 3.0mm;
  flex-shrink: 0;
}}

.kpi-card {{
  flex: 1;
  padding: 3.2mm 4.2mm;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(20,40,82,0.92), rgba(15,30,62,0.85));
  border: 1.2px solid;
  display: flex;
  align-items: center;
  gap: 2.8mm;
  box-shadow: 0 4px 14px rgba(0,0,0,0.3);
}}
.kpi-card.emerald {{ border-color: rgba(16,185,129,0.55); }}
.kpi-card.blue {{ border-color: rgba(59,130,246,0.55); }}
.kpi-card.amber {{ border-color: rgba(245,158,11,0.55); }}
.kpi-card.purple {{ border-color: rgba(168,85,247,0.55); }}

.kpi-icon {{
  font-size: 18pt;
  line-height: 1;
  flex-shrink: 0;
}}

.kpi-body {{ flex: 1; }}

.kpi-value {{
  font-family: 'Montserrat', sans-serif;
  font-size: 17pt;
  font-weight: 900;
  line-height: 1.1;
}}
.kpi-card.emerald .kpi-value {{ color: #34d399; }}
.kpi-card.blue .kpi-value {{ color: #60a5fa; }}
.kpi-card.amber .kpi-value {{ color: #fbbf24; }}
.kpi-card.purple .kpi-value {{ color: #c084fc; }}

.kpi-label {{
  font-size: 7.6pt;
  font-weight: 800;
  color: #f1f5f9;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}}

.kpi-sub {{
  font-size: 6.6pt;
  color: #94a3b8;
  margin-top: 0.2mm;
  font-weight: 500;
}}

/* ═════════════════════════════════════════════════════════════════════
   MAIN 2-COLUMN GRID
   ═════════════════════════════════════════════════════════════════════ */
.body-grid {{
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: 3.5mm;
  flex: 1;
  min-height: 0;
}}

.col {{
  display: flex;
  flex-direction: column;
  gap: 3.2mm;
  min-height: 0;
}}

/* ═════════════════════════════════════════════════════════════════════
   CARDS
   ═════════════════════════════════════════════════════════════════════ */
.card {{
  border-radius: 9px;
  background: linear-gradient(140deg, rgba(18,30,60,0.95) 0%, rgba(12,21,44,0.92) 100%);
  border: 1px solid rgba(59,130,246,0.22);
  box-shadow: 0 4px 18px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}}

.card-header {{
  padding: 2.4mm 4.2mm;
  background: linear-gradient(135deg, rgba(30,58,100,0.85), rgba(24,44,82,0.7));
  border-bottom: 1px solid rgba(59,130,246,0.2);
  font-family: 'Montserrat', sans-serif;
  font-size: 10.5pt;
  font-weight: 850;
  color: #fbbf24;
  display: flex;
  align-items: center;
  gap: 2mm;
  flex-shrink: 0;
  letter-spacing: 0.2px;
}}
.card-header .icon {{ font-size: 11pt; }}

.card-body {{
  padding: 3.0mm 4.2mm;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1.8mm;
  overflow: hidden;
}}

/* Specific column flex allocation */
.card-arch {{ flex: 1.25; }}
.card-viz {{ flex: 1.0; }}
.card-results {{ flex: 1.30; }}
.card-contribs {{ flex: 0.95; }}

/* ═════════════════════════════════════════════════════════════════════
   MOTIVATION & PROBLEM CALLOUT
   ═════════════════════════════════════════════════════════════════════ */
.problem-box {{
  background: rgba(59,130,246,0.06);
  border: 1px solid rgba(59,130,246,0.22);
  border-radius: 5px;
  padding: 1.6mm 2.8mm;
  font-size: 7.8pt;
  line-height: 1.35;
  color: #cbd5e1;
}}
.problem-box strong {{ color: #fbbf24; }}
.problem-box .hl {{ color: #34d399; font-weight: 700; }}

/* ═════════════════════════════════════════════════════════════════════
   ARCHITECTURE TIERS
   ═════════════════════════════════════════════════════════════════════ */
.tier-list {{
  display: flex;
  flex-direction: column;
  gap: 1.1mm;
}}
.tier {{
  line-height: 1.32;
}}
.tier-name {{
  font-size: 8.6pt;
  font-weight: 800;
  color: #fbbf24;
}}
.tier-meta {{
  font-size: 7.4pt;
  color: #94a3b8;
}}
.tier-detail {{
  font-size: 7.8pt;
  color: #cbd5e1;
  padding-left: 3.2mm;
  line-height: 1.32;
}}
.tier-detail .hl {{ color: #34d399; font-weight: 700; }}
.tier-detail .code {{ color: #60a5fa; font-family: 'Fira Code', monospace; font-size: 7.5pt; }}

/* Figure containers */
.fig-box {{
  background: #ffffff;
  border-radius: 5px;
  padding: 1.2mm;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}}
.fig-box img {{
  width: 100%;
  height: auto;
  display: block;
  border-radius: 3px;
}}
.fig-arch img {{
  width: 100%;
  object-fit: contain;
}}
.fig-caption {{
  font-size: 7.0pt;
  color: #94a3b8;
  text-align: center;
  font-style: italic;
  margin-top: 0.6mm;
}}

/* ═════════════════════════════════════════════════════════════════════
   TABLES
   ═════════════════════════════════════════════════════════════════════ */
table {{
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  border-radius: 6px;
  overflow: hidden;
  font-size: 7.6pt;
  flex-shrink: 0;
}}
table caption {{
  font-size: 8.0pt;
  font-weight: 800;
  color: #e2e8f0;
  text-align: left;
  margin-bottom: 0.8mm;
}}
th {{
  background: linear-gradient(135deg, #1e40af, #1e3a8a);
  color: #ffffff;
  font-weight: 800;
  padding: 1.4mm 2.0mm;
  text-align: center;
  font-size: 7.2pt;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}}
td {{
  padding: 1.2mm 2.0mm;
  text-align: center;
  color: #cbd5e1;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}}
tr:nth-child(even) td {{ background: rgba(255,255,255,0.03); }}
tr:nth-child(odd) td {{ background: rgba(255,255,255,0.01); }}
td.best {{ color: #34d399; font-weight: 800; }}
td.delta {{ color: #34d399; font-weight: 800; }}
td.pval {{ color: #f59e0b; font-weight: 700; font-size: 7.0pt; }}

/* ═════════════════════════════════════════════════════════════════════
   FINDINGS CALLOUTS
   ═════════════════════════════════════════════════════════════════════ */
.finding-list {{
  display: flex;
  flex-direction: column;
  gap: 0.9mm;
}}
.finding {{
  font-size: 7.8pt;
  line-height: 1.32;
  padding: 1.3mm 2.5mm;
  border-radius: 5px;
  background: rgba(255,255,255,0.025);
  border-left: 2.6px solid;
}}
.finding.ok {{ border-color: #34d399; }}
.finding.stat {{ border-color: #60a5fa; }}
.finding.win {{ border-color: #f59e0b; }}
.finding.warn {{ border-color: #ef4444; }}
.finding.scale {{ border-color: #c084fc; }}
.finding .tag {{ font-weight: 800; }}
.finding.ok .tag {{ color: #34d399; }}
.finding.stat .tag {{ color: #60a5fa; }}
.finding.win .tag {{ color: #fbbf24; }}
.finding.warn .tag {{ color: #f87171; }}
.finding.scale .tag {{ color: #c084fc; }}

/* ═════════════════════════════════════════════════════════════════════
   CONTRIBUTIONS & FOOTER
   ═════════════════════════════════════════════════════════════════════ */
.sec-lbl {{
  font-size: 8.5pt;
  font-weight: 850;
  text-transform: uppercase;
  letter-spacing: 0.7px;
  margin-bottom: 0.5mm;
}}
.sec-lbl.green {{ color: #34d399; }}
.sec-lbl.blue {{ color: #60a5fa; }}
.sec-lbl.amber {{ color: #fbbf24; }}
.sec-lbl.gray {{ color: #94a3b8; }}

.contrib-item {{
  font-size: 7.8pt;
  line-height: 1.32;
  margin-bottom: 0.8mm;
  color: #cbd5e1;
}}
.contrib-item strong {{ color: #f1f5f9; }}
.contrib-item .num {{ color: #fbbf24; font-weight: 800; }}

.ref-item {{
  font-size: 6.8pt;
  color: #94a3b8;
  line-height: 1.28;
  margin-bottom: 0.6mm;
}}
.ref-item em {{ color: #cbd5e1; }}

.portal-box {{
  font-size: 7.8pt;
  color: #60a5fa;
  background: rgba(59,130,246,0.08);
  border: 1px solid rgba(59,130,246,0.25);
  border-radius: 5px;
  padding: 1.2mm 2.6mm;
  display: flex;
  align-items: center;
  justify-content: space-between;
}}
.portal-box strong {{ color: #93c5fd; }}
.portal-box code {{ color: #34d399; font-family: 'Fira Code', monospace; font-size: 7.4pt; }}

.poster-footer {{
  padding: 2.6mm 7mm;
  background: linear-gradient(135deg, rgba(16,26,65,0.92), rgba(22,38,82,0.88));
  border: 1.2px solid rgba(99,130,255,0.32);
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 8.0pt;
  color: #94a3b8;
  flex-shrink: 0;
}}
.poster-footer strong {{ color: #e2e8f0; }}
.poster-footer code {{ color: #60a5fa; font-family: 'Fira Code', monospace; font-size: 7.6pt; }}
</style>
</head>
<body>
<div class="poster">

  <!-- ══════════════ HEADER ══════════════ -->
  <div class="header">
    <div class="category">NGHIÊN CỨU KHOA HỌC SINH VIÊN 2026 • TRƯỜNG ĐẠI HỌC TÔN ĐỨC THẮNG</div>
    <div class="title">TỐI ƯU HÓA BÀI TOÁN ĐỊNH TUYẾN PHƯƠNG TIỆN CÓ KHUNG THỜI GIAN</div>
    <div class="title-accent">BẰNG THUẬT TOÁN TÌM KIẾM LÂN CẬN LỚN THÍCH ỨNG LAI HỌC TĂNG CƯỜNG SÂU</div>
    <div class="tags">▸ TRI-LEVEL COORDINATED DDQN-ALNS • CONTRASTIVE GNN • SET PARTITIONING MILP ◂</div>
    <div class="authors">
      <strong>SVTH:</strong> Huỳnh Nhật Huy (MSSV: 523C0012) – Ngành Khoa học Máy tính, Khoa Công nghệ Thông tin<br>
      <strong>GVHD:</strong> TS. Hồ Thị Linh – Nhóm nghiên cứu NLP-KD, Khoa CNTT, Trường Đại học Tôn Đức Thắng
    </div>
  </div>

  <!-- ══════════════ KPI STRIP ══════════════ -->
  <div class="kpi-strip">
    <div class="kpi-card emerald">
      <div class="kpi-icon">🛡️</div>
      <div class="kpi-body">
        <div class="kpi-value">100%</div>
        <div class="kpi-label">Khả thi tuyệt đối</div>
        <div class="kpi-sub">0 vi phạm / 580 thực nghiệm</div>
      </div>
    </div>
    <div class="kpi-card blue">
      <div class="kpi-icon">⚡</div>
      <div class="kpi-body">
        <div class="kpi-value">−165.2 km</div>
        <div class="kpi-label">Tiết kiệm quãng đường</div>
        <div class="kpi-sub">Homberger-200 (p &lt; 10⁻⁶)</div>
      </div>
    </div>
    <div class="kpi-card amber">
      <div class="kpi-icon">🚚</div>
      <div class="kpi-body">
        <div class="kpi-value">−0.29 xe</div>
        <div class="kpi-label">Cắt giảm đội xe</div>
        <div class="kpi-sub">Homberger-200 (Mean NV 11.58)</div>
      </div>
    </div>
    <div class="kpi-card purple">
      <div class="kpi-icon">🎯</div>
      <div class="kpi-body">
        <div class="kpi-value">0.70–0.80 xe</div>
        <div class="kpi-label">Lợi thế quy mô 400C</div>
        <div class="kpi-sub">Vượt ALNS-Base (c2_4_1, r2_4_1)</div>
      </div>
    </div>
    <div class="kpi-card emerald">
      <div class="kpi-icon">🌐</div>
      <div class="kpi-body">
        <div class="kpi-value">1.62%</div>
        <div class="kpi-label">Zero-Shot Gap</div>
        <div class="kpi-sub">Domain Randomization</div>
      </div>
    </div>
  </div>

  <!-- ══════════════ MAIN BODY GRID ══════════════ -->
  <div class="body-grid">

    <!-- ──── LEFT COLUMN ──── -->
    <div class="col">

      <!-- CARD 1: ARCHITECTURE -->
      <div class="card card-arch">
        <div class="card-header"><span class="icon">🧠</span> KIẾN TRÚC PHÂN CẤP TRI-LEVEL HYBRID DDQN-ALNS</div>
        <div class="card-body">
          <div class="problem-box">
            <strong>Động lực nghiên cứu:</strong> VRPTW là bài toán tối ưu tổ hợp NP-hard theo mục tiêu từ điển (Lexicographic): <span class="hl">ưu tiên giảm số xe N_V, sau đó tối thiểu hóa tổng quãng đường D_T</span> dưới ràng buộc tải trọng Q và khung thời gian [Eᵢ, Lᵢ]. ALNS cổ điển chọn toán tử ngẫu nhiên dễ mắc kẹt tại cực tiểu địa phương (plateau). DRL thuần túy vi phạm ràng buộc khả thi và rào cản OOD. Đề tài đề xuất khung kiến trúc phân cấp phối hợp 3 tầng khắc phục triệt để các hạn chế trên.
          </div>

          <div class="tier-list">
            <div class="tier">
              <span class="tier-name">TẦNG 1 — Macro Plateau Controller</span> <span class="tier-meta">(Semi-MDP, 128-D hidden Dueling DDQN, Replay Buffer)</span>
              <div class="tier-detail">Giám sát điểm dừng qua chu kỳ Δ_seg = 100 bước (s_k^macro ∈ ℝ¹³) → điều khiển <span class="hl">7 chế độ chiến lược</span> (<span class="code">Default • Intensify • Diversify • TW-Rescue • Pool-Recombine • Route-Reduce • Infeasible-Descent</span>).</div>
            </div>
            <div class="tier">
              <span class="tier-name">TẦNG 2 — Micro Operator Controller &amp; Learned Acceptance (LAC)</span> <span class="tier-meta">(20-D state, 65 action pairs)</span>
              <div class="tier-detail">Điều phối <span class="hl">13 Destroy × 5 Repair</span> qua hàm chọn Softmax-Entropy concentration gate w_conf(s), kết hợp Q-values và Thompson Bandit. LAC lookahead (H_lac = 80) thay thế SA sau warmup.</div>
            </div>
            <div class="tier">
              <span class="tier-name">TẦNG 3 — Heuristic Execution Engine (ALNS) &amp; Set Partitioning (HiGHS MILP)</span>
              <div class="tier-detail">Kiểm tra khả thi O(1) slack, cắt tỉa cạnh tìm kiếm bằng <span class="hl">Contrastive GNN</span> (98.74% pruning). Tái tổ hợp nghiệm tối ưu toàn cục qua HiGHS MIP trên Dual-Slot Route Pool 𝒫 (|𝒫|_max ≤ 2000).</div>
            </div>
          </div>

          <div class="fig-box fig-arch">
            <img src="{arch_b64}" alt="Tri-Level Coordinated Architecture">
          </div>
          <div class="fig-caption">Hình 1. Sơ đồ kiến trúc phân cấp Tri-Level Coordinated Hybrid DDQN-ALNS (Macro DDQN • Micro DDQN &amp; LAC • ALNS Core • Dual-Slot Route Pool • HiGHS MILP)</div>
        </div>
      </div>

      <!-- CARD 2: VISUALIZATION & REAL-TIME DISPATCH -->
      <div class="card card-viz">
        <div class="card-header"><span class="icon">📊</span> TRỰC QUAN HÓA KẾT QUẢ HỘI TỤ &amp; TUYẾN ĐƯỜNG</div>
        <div class="card-body">
          <!-- 4-panel convergence -->
          <div class="fig-box">
            <img src="{conv_b64}" alt="Convergence Curves">
          </div>
          <div class="fig-caption">Hình 2. Đường cong hội tụ Anytime trên RC101, R101, C101, r1_2_1 (Hybrid-DDQN vượt plateau nhanh hơn ALNS-Base)</div>

          <!-- 2 Route Maps -->
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2.2mm;">
            <div class="fig-box">
              <img src="{r101_b64}" alt="Route Map R101">
            </div>
            <div class="fig-box">
              <img src="{rc101_b64}" alt="Route Map RC101">
            </div>
          </div>
          <div class="fig-caption">Hình 3. Bản đồ phân bổ tuyến đường tối ưu trên bài toán R101 (Khớp BKS NV = 19, TD = 1650.80) và RC101 (NV = 15, TD = 1644.80)</div>

          <!-- NAMI Portal Box -->
          <div class="portal-box">
            <div>🚀 <strong>NAMI Dispatch Portal:</strong> Nền tảng điều phối lộ trình vận tải thời gian thực</div>
            <div><code>FastAPI • Leaflet.js • SSE Live Tracking • Docker Swarm</code></div>
          </div>
        </div>
      </div>

    </div>

    <!-- ──── RIGHT COLUMN ──── -->
    <div class="col">

      <!-- CARD 3: EXPERIMENTAL RESULTS -->
      <div class="card card-results">
        <div class="card-header"><span class="icon">📈</span> KẾT QUẢ THỰC NGHIỆM &amp; ĐÁNH GIÁ ĐỐI CHUẨN</div>
        <div class="card-body">
          <!-- Table 1 -->
          <table>
            <caption>Bảng 1. Tổng hợp đối chuẩn trên Solomon-100 (N=56) &amp; Homberger-200 (N=60)</caption>
            <tr><th>Benchmark</th><th>Thuật Toán</th><th>Số Xe (N_V) ↓</th><th>Quãng Đường (D_T, km) ↓</th><th>Thời Gian</th><th>Kiểm Định Wilcoxon</th></tr>
            <tr><td></td><td>BKS (SINTEF)</td><td class="best">7.07</td><td>1013.36</td><td>—</td><td>Chuẩn đối sánh quốc tế</td></tr>
            <tr><td>Solomon-100</td><td>ALNS-Base</td><td>7.54</td><td>1017.31</td><td>10.1s</td><td>baseline</td></tr>
            <tr><td>(N=56)</td><td>Hybrid-DDQN</td><td class="best">7.34</td><td>1017.82</td><td>39.0s</td><td class="pval">p = 0.00127 (Có ý nghĩa)</td></tr>
            <tr><td>Homberger-200</td><td>ALNS-Base</td><td>11.87</td><td>3009.91</td><td>3.9s</td><td>baseline</td></tr>
            <tr><td>(N=60)</td><td>Hybrid-DDQN</td><td class="best">11.58</td><td class="best">2844.73</td><td>35.8s</td><td class="pval">p = 1.34 × 10⁻⁹ (Cực kỳ mạnh)</td></tr>
          </table>

          <!-- Table 2 -->
          <table>
            <caption>Bảng 2. Chi tiết 6 họ bài toán Homberger-200 (5 seeds độc lập, giao thức Cold-Start)</caption>
            <tr><th>Nhóm</th><th>ALNS N_V</th><th>Hybrid N_V</th><th>ALNS D_T (km)</th><th>Hybrid D_T (km)</th><th>Chênh Lệch ΔD_T (km)</th></tr>
            <tr><td>C1_200</td><td>19.30</td><td class="best">18.70</td><td>2804</td><td>2734</td><td class="delta">−70</td></tr>
            <tr><td>C2_200</td><td>6.02</td><td class="best">6.00</td><td>1902</td><td>1827</td><td class="delta">−75</td></tr>
            <tr><td>R1_200</td><td>18.10</td><td>18.20†</td><td>4099</td><td class="best">3738</td><td class="delta">−362</td></tr>
            <tr><td>R2_200</td><td>4.16</td><td class="best">4.10</td><td>3012</td><td>2855</td><td class="delta">−158</td></tr>
            <tr><td>RC1_200</td><td>18.90</td><td class="best">18.00</td><td>3581</td><td>3361</td><td class="delta">−221</td></tr>
            <tr><td>RC2_200</td><td>4.74</td><td class="best">4.50</td><td>2660</td><td>2631</td><td class="delta">−29</td></tr>
          </table>

          <!-- 5 Key Findings -->
          <div class="finding-list">
            <div class="finding ok"><span class="tag">✅ Khả thi 100%:</span> 0 vi phạm ràng buộc trên toàn bộ 580 lần chạy độc lập. Mọi nghiệm xuất xưởng thỏa mãn tuyệt đối tải trọng và khung thời gian [Eᵢ, Lᵢ].</div>
            <div class="finding stat"><span class="tag">📊 Ý nghĩa thống kê:</span> Wilcoxon signed-rank test xác nhận ưu thế vượt trội: Solomon p = 0.00127, Homberger-200 p = 1.34 × 10⁻⁹ (mức ý nghĩa α = 0.01).</div>
            <div class="finding win"><span class="tag">🏆 Bước đột phá RC1_200:</span> Cắt giảm −0.90 xe và −220.56 km (−6.16%) nhờ cơ chế hướng dẫn cạnh của Contrastive GNN và Route Elimination.</div>
            <div class="finding warn"><span class="tag">⚠️ Đối sánh OR-Tools:</span> Google OR-Tools sử dụng thừa +80% số xe trên RC2 (6.50 xe vs BKS 3.25). Hybrid-DDQN đạt 3.25 xe (khớp tuyệt đối BKS).</div>
            <div class="finding scale"><span class="tag">📈 Quy mô 400 khách (Graceful Degradation):</span> Duy trì lợi thế dẫn trước 0.70 đến 0.80 xe có ý nghĩa thống kê cao (p = 0.0078 trên c2_4_1, p = 0.0156 trên r2_4_1).</div>
          </div>

          <!-- Boxplot -->
          <div class="fig-box">
            <img src="{box_b64}" alt="NV Gap to BKS Boxplots across 176 instances">
          </div>
          <div class="fig-caption">Hình 4. Phân phối độ lệch số xe đến BKS trên toàn bộ 176 bài toán (ALNS-Base xám vs Hybrid-DDQN xanh lá chứng minh tính ổn định cao)</div>
        </div>
      </div>

      <!-- CARD 4: CONTRIBUTIONS & REFERENCES -->
      <div class="card card-contribs">
        <div class="card-header"><span class="icon">🎓</span> ĐÓNG GÓP KHOA HỌC &amp; ĐỊNH HƯỚNG</div>
        <div class="card-body">
          <div>
            <div class="sec-lbl green">ĐÓNG GÓP KHOA HỌC CHÍNH</div>
            <div class="contrib-item"><span class="num">1.</span> <strong>Khung kiến trúc phân cấp Tri-Level Coordinated:</strong> Phối hợp Macro Plateau Controller, Micro Operator Controller (65 action pairs), và HiGHS Set Partitioning MILP trên Dual-Slot Route Pool.</div>
            <div class="contrib-item"><span class="num">2.</span> <strong>Contrastive GNN Edge Predictor:</strong> Message-passing 3 tầng huấn luyện với InfoNCE loss, cắt giảm 98.74% số cạnh không tiềm năng, tăng tốc giải mã heuristic.</div>
            <div class="contrib-item"><span class="num">3.</span> <strong>Quy chuẩn kiểm thử Cold-Start độc lập:</strong> Loại bỏ hiện tượng rò rỉ bộ nhớ giữa các lần chạy, thiết lập bộ kết quả đối chuẩn khách quan, đạt zero-shot gap 1.62% trên Solomon.</div>
          </div>

          <div>
            <div class="sec-lbl blue">HƯỚNG PHÁT TRIỂN ỨNG DỤNG</div>
            <div class="contrib-item">• <strong>Heterogeneous Fleet VRPTW:</strong> Mở rộng bài toán cho đội xe hỗn hợp tải trọng và phương tiện giao hàng xanh (xe điện EV).</div>
            <div class="contrib-item">• <strong>Dynamic &amp; Stochastic Routing:</strong> Tích hợp ràng buộc thời gian làm việc của tài xế (EU/VN) và tiếp nhận đơn hàng phát sinh thời gian thực (&lt; 1ms).</div>
            <div class="contrib-item">• <strong>Scalability:</strong> Mở rộng tối ưu hóa cho quy mô 600–1000 khách hàng (Homberger large-scale) và VRPTW ngẫu nhiên.</div>
          </div>

          <div>
            <div class="sec-lbl amber">CÔNG BỐ KHOA HỌC &amp; KHẢ NĂNG TÁI LẬP</div>
            <div class="contrib-item">• <strong>Bản thảo IEEE Access:</strong> Toàn văn công trình đã hoàn thiện bản thảo gửi đăng tại tạp chí uy tín IEEE Access (SCIE, Q1, IF 3.4). Toàn bộ mã nguồn mở và checkpoint mô hình được công khai minh bạch.</div>
          </div>

          <div>
            <div class="sec-lbl gray">TÀI LIỆU THAM KHẢO</div>
            <div class="ref-item">[1] S. Ropke, D. Pisinger, "An Adaptive Large Neighborhood Search Heuristic for Pick-up and Delivery," <em>Transportation Science</em>, 2006.</div>
            <div class="ref-item">[2] V. Mnih et al., "Human-level control through deep reinforcement learning," <em>Nature</em>, vol. 518, pp. 529–533, 2015.</div>
            <div class="ref-item">[3] H. Gehring, J. Homberger, "A Parallel Two-phase Metaheuristic for Routing Problems," <em>Asia-Pacific J. Oper. Res.</em>, 2001.</div>
            <div class="ref-item">[4] M. M. Solomon, "Algorithms for the Vehicle Routing Problem with Time Windows," <em>Operations Research</em>, vol. 35, 1987.</div>
          </div>
        </div>
      </div>

    </div>

  </div>

  <!-- ══════════════ FOOTER ══════════════ -->
  <div class="poster-footer">
    <div><strong>Hội đồng NCKHSV 2026</strong> — Khoa Công nghệ Thông tin, Trường Đại học Tôn Đức Thắng (TDTU)</div>
    <div>Đề tài: <em>Tri-Level Coordinated Hybrid DDQN-ALNS for Vehicle Routing Problem with Time Windows</em></div>
    <div>Môi trường: <code>PyTorch 2.1 • SciPy HiGHS • Numba JIT • FastAPI • Leaflet.js • Docker</code></div>
  </div>

</div>
</body>
</html>
"""

    poster_html_path = os.path.join(base_dir, "poster_v5.html")
    with open(poster_html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("Updated poster_v5.html successfully!")

    # Render with Playwright directly to PNG and PDF
    print("Launching Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Viewport: ISO A1 proportional (2245 x 3179 @ 96dpi, or 3508 x 4967 @ 150dpi)
        page = browser.new_page(viewport={"width": 2245, "height": 3179}, device_scale_factor=1.5)
        page.goto(f"file://{poster_html_path}")
        page.wait_for_timeout(1000)
        
        png_path = os.path.join(base_dir, "Poster_VRPTW_NCKHSV_2026.png")
        page.screenshot(path=png_path, full_page=True)
        print(f"Generated high-res PNG: {png_path}")
        
        pdf_path = os.path.join(base_dir, "Poster_VRPTW_NCKHSV_2026.pdf")
        page.pdf(
            path=pdf_path,
            width="594mm",
            height="841mm",
            print_background=True,
            margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"}
        )
        print(f"Generated high-res PDF: {pdf_path}")
        browser.close()

if __name__ == "__main__":
    main()
