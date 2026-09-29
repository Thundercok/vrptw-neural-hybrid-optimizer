#!/usr/bin/env python3
"""
Generate the publication-grade scientific research poster for TDTU NCKHSV 2026
Format: ISO A1 Portrait (594mm x 841mm)
Author: Huynh Nhat Huy (MSSV: 523C0012)
Advisor: TS. Ho Thi Linh
Institution: Ton Duc Thang University (TDTU) - Faculty of Information Technology
"""

import base64
import os

def get_base64_image(image_path):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    with open(image_path, "rb") as f:
        data = f.read()
    ext = os.path.splitext(image_path)[1].lower().replace(".", "")
    if ext == "jpg":
        ext = "jpeg"
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:image/{ext};base64,{b64}"

def main():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    docs_dir = os.path.join(base_dir, "docs")
    figs_dir = os.path.join(docs_dir, "figures")

    # Load images
    arch_b64 = get_base64_image(os.path.join(figs_dir, "poster_architecture.png"))
    conv_b64 = get_base64_image(os.path.join(figs_dir, "anytime_convergence.png"))
    route_b64 = get_base64_image(os.path.join(figs_dir, "route_RC101.png"))
    
    # High-contrast deep space background
    bg_style = ""

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Poster NCKHSV 2026 - TDTU - Huỳnh Nhật Huy</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  @page {{
    size: 594mm 841mm;
    margin: 0;
  }}

  * {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}

  body {{
    width: 594mm;
    height: 841mm;
    margin: 0 auto;
    overflow: hidden;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #070913;
    color: #e2e8f0;
  }}

  .poster {{
    width: 594mm;
    height: 841mm;
    position: relative;
    padding: 10mm 13mm 9mm 13mm;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 3.8mm;
    background: radial-gradient(circle at 50% -10%, #1c2a5e 0%, #0c1432 30%, #070a19 65%, #03040a 100%);
  }}

  /* Top Banner */
  .header-banner {{
    background: linear-gradient(135deg, rgba(16, 24, 54, 0.95), rgba(24, 38, 80, 0.92));
    border: 1.5px solid rgba(99, 130, 255, 0.35);
    border-radius: 12px;
    padding: 6mm 10mm 5mm 10mm;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    position: relative;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  }}

  .inst-sub {{
    font-family: 'Montserrat', sans-serif;
    font-size: 8.5pt;
    font-weight: 800;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #38bdf8;
    margin-bottom: 2mm;
    display: flex;
    align-items: center;
    gap: 3mm;
  }}

  .inst-badge {{
    background: rgba(56, 189, 248, 0.15);
    border: 1px solid rgba(56, 189, 248, 0.4);
    padding: 1mm 3mm;
    border-radius: 4px;
  }}

  .main-title {{
    font-family: 'Montserrat', sans-serif;
    font-size: 26pt;
    font-weight: 900;
    color: #ffffff;
    line-height: 1.2;
    text-shadow: 0 3px 18px rgba(0, 0, 0, 0.8);
    margin-bottom: 1.8mm;
    letter-spacing: -0.3px;
  }}

  .title-accent {{
    font-family: 'Montserrat', sans-serif;
    font-size: 21pt;
    font-weight: 800;
    background: linear-gradient(90deg, #f59e0b, #fde68a, #f59e0b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.2;
    display: block;
    margin-bottom: 2.8mm;
  }}

  .paradigm-tags {{
    font-family: 'Fira Code', monospace;
    font-size: 9pt;
    font-weight: 600;
    color: #34d399;
    letter-spacing: 1.2px;
    margin-bottom: 2.8mm;
  }}

  .author-row {{
    display: flex;
    justify-content: center;
    gap: 14mm;
    font-size: 10pt;
    color: #cbd5e1;
    border-top: 1px solid rgba(255, 255, 255, 0.14);
    padding-top: 2.8mm;
    width: 100%;
  }}

  .author-row strong {{
    color: #ffffff;
    font-weight: 700;
  }}

  /* KPI Strip */
  .kpi-strip {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 4mm;
  }}

  .kpi-card {{
    background: linear-gradient(140deg, rgba(20, 35, 75, 0.94), rgba(13, 23, 50, 0.9));
    border: 1.2px solid rgba(59, 130, 246, 0.4);
    border-radius: 9px;
    padding: 4mm 5mm;
    display: flex;
    align-items: center;
    gap: 4mm;
    box-shadow: 0 5px 18px rgba(0, 0, 0, 0.4);
  }}

  .kpi-card.emerald {{ border-color: rgba(16, 185, 129, 0.6); }}
  .kpi-card.blue {{ border-color: rgba(59, 130, 246, 0.6); }}
  .kpi-card.amber {{ border-color: rgba(245, 158, 11, 0.6); }}
  .kpi-card.purple {{ border-color: rgba(168, 85, 247, 0.6); }}

  .kpi-icon {{
    font-size: 22pt;
    line-height: 1;
  }}

  .kpi-val {{
    font-family: 'Montserrat', sans-serif;
    font-size: 21pt;
    font-weight: 900;
    line-height: 1.1;
  }}

  .kpi-card.emerald .kpi-val {{ color: #34d399; }}
  .kpi-card.blue .kpi-val {{ color: #60a5fa; }}
  .kpi-card.amber .kpi-val {{ color: #fbbf24; }}
  .kpi-card.purple .kpi-val {{ color: #c084fc; }}

  .kpi-lbl {{
    font-size: 9pt;
    font-weight: 700;
    color: #f1f5f9;
    text-transform: uppercase;
    letter-spacing: 0.6px;
  }}

  .kpi-desc {{
    font-size: 7.8pt;
    color: #94a3b8;
  }}

  /* Grid Layout: 2 Columns */
  .content-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 5mm;
    flex: 1;
    min-height: 0;
  }}

  .col {{
    display: flex;
    flex-direction: column;
    gap: 5mm;
  }}

  /* Cards */
  .section-card {{
    background: linear-gradient(145deg, rgba(16, 26, 52, 0.97), rgba(11, 19, 39, 0.95));
    border: 1.2px solid rgba(70, 110, 200, 0.35);
    border-radius: 11px;
    box-shadow: 0 8px 26px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}

  .card-hdr {{
    background: linear-gradient(135deg, rgba(30, 52, 100, 0.96), rgba(20, 36, 75, 0.85));
    border-bottom: 1px solid rgba(70, 110, 200, 0.3);
    padding: 4mm 7mm;
    font-family: 'Montserrat', sans-serif;
    font-size: 13.5pt;
    font-weight: 800;
    color: #fbbf24;
    display: flex;
    align-items: center;
    gap: 3.5mm;
  }}

  .card-hdr .badge-num {{
    background: #f59e0b;
    color: #0b1329;
    font-size: 10.5pt;
    font-weight: 900;
    padding: 1.2mm 3.2mm;
    border-radius: 5px;
  }}

  .card-body {{
    padding: 5.5mm 7mm;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 3.5mm;
    font-size: 9.8pt;
    line-height: 1.54;
  }}

  /* Typography helpers */
  .b-item {{
    position: relative;
    padding-left: 5mm;
  }}
  .b-item::before {{
    content: '▸';
    position: absolute;
    left: 0;
    color: #f59e0b;
    font-weight: bold;
    font-size: 11pt;
  }}
  .b-item strong {{
    color: #ffffff;
  }}
  .hl-grn {{ color: #34d399; font-weight: 600; }}
  .hl-blu {{ color: #60a5fa; font-weight: 600; }}
  .hl-amb {{ color: #fbbf24; font-weight: 600; }}
  .code-text {{
    font-family: 'Fira Code', monospace;
    font-size: 9.2pt;
    color: #93c5fd;
  }}

  /* Image Containers */
  .img-box {{
    background: #ffffff;
    border-radius: 7px;
    padding: 2.8mm;
    box-shadow: 0 5px 16px rgba(0, 0, 0, 0.5);
    display: flex;
    flex-direction: column;
    align-items: center;
  }}

  .img-box img {{
    width: 100%;
    height: auto;
    display: block;
    border-radius: 4px;
  }}

  .img-caption {{
    font-size: 8.2pt;
    color: #475569;
    margin-top: 1.5mm;
    text-align: center;
    font-style: italic;
    font-weight: 600;
  }}

  /* Tables */
  table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    border-radius: 7px;
    overflow: hidden;
    font-size: 8.8pt;
    margin-top: 1.5mm;
  }}

  th {{
    background: linear-gradient(135deg, #1e3a8a, #172554);
    color: #ffffff;
    font-weight: 700;
    padding: 2.5mm 3mm;
    text-align: center;
    border-bottom: 1px solid rgba(255, 255, 255, 0.15);
  }}

  td {{
    padding: 2.2mm 3mm;
    text-align: center;
    color: #cbd5e1;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    background: rgba(255, 255, 255, 0.025);
  }}

  tr:nth-child(even) td {{
    background: rgba(255, 255, 255, 0.05);
  }}

  td.best {{ color: #34d399; font-weight: 700; }}
  td.pval {{ color: #f59e0b; font-weight: 600; }}
  td.diff {{ color: #38bdf8; font-weight: 700; }}

  /* Finding callout boxes */
  .finding {{
    background: rgba(255, 255, 255, 0.04);
    border-left: 4px solid #34d399;
    border-radius: 5px;
    padding: 2.8mm 3.8mm;
    font-size: 9.2pt;
    line-height: 1.45;
  }}
  .finding.stat {{ border-color: #60a5fa; }}
  .finding.win {{ border-color: #fbbf24; }}
  .finding.scale {{ border-color: #c084fc; }}

  /* Footer */
  .poster-footer {{
    background: rgba(13, 20, 38, 0.94);
    border-top: 1px solid rgba(70, 110, 200, 0.4);
    border-radius: 9px;
    padding: 3mm 7mm;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 8.8pt;
    color: #94a3b8;
  }}
</style>
</head>
<body>
<div class="poster">

  <!-- HEADER -->
  <div class="header-banner">
    <div class="inst-sub">
      <span class="inst-badge">TRƯỜNG ĐẠI HỌC TÔN ĐỨC THẮNG</span>
      <span>•</span>
      <span>KHOA CÔNG NGHỆ THÔNG TIN</span>
      <span>•</span>
      <span>NGHIÊN CỨU KHOA HỌC SINH VIÊN 2026</span>
    </div>
    <div class="main-title">TỐI ƯU HÓA BÀI TOÁN ĐỊNH TUYẾN PHƯƠNG TIỆN CÓ KHUNG THỜI GIAN</div>
    <div class="title-accent">BẰNG THUẬT TOÁN TÌM KIẾM LÂN CẬN LỚN THÍCH ỨNG LAI HỌC TĂNG CƯỜNG SÂU</div>
    <div class="paradigm-tags">▹ Tri-Level Coordinated DDQN-ALNS &nbsp;×&nbsp; Contrastive GNN &nbsp;×&nbsp; Set Partitioning MILP ◃</div>
    <div class="author-row">
      <div><strong>Sinh viên thực hiện:</strong> Huỳnh Nhật Huy (MSSV: 523C0012) — Ngành Khoa học Máy tính</div>
      <div><strong>Giảng viên hướng dẫn:</strong> TS. Hồ Thị Linh — Nhóm NLP-KD, Khoa CNTT, ĐH Tôn Đức Thắng</div>
    </div>
  </div>

  <!-- KPI STRIP -->
  <div class="kpi-strip">
    <div class="kpi-card emerald">
      <div class="kpi-icon">🛡️</div>
      <div>
        <div class="kpi-val">100%</div>
        <div class="kpi-lbl">Bảo Toàn Khả Thi</div>
        <div class="kpi-desc">0 vi phạm / 580 thực nghiệm</div>
      </div>
    </div>
    <div class="kpi-card blue">
      <div class="kpi-icon">⚡</div>
      <div>
        <div class="kpi-val">−165.2 km</div>
        <div class="kpi-lbl">Tiết Kiệm Quãng Đường</div>
        <div class="kpi-desc">Homberger-200 (Wilcoxon p &lt; 10⁻⁹)</div>
      </div>
    </div>
    <div class="kpi-card amber">
      <div class="kpi-icon">🚚</div>
      <div>
        <div class="kpi-val">−0.29 xe</div>
        <div class="kpi-lbl">Cắt Giảm Đội Xe</div>
        <div class="kpi-desc">Homberger-200 (Mean NV 11.58)</div>
      </div>
    </div>
    <div class="kpi-card purple">
      <div class="kpi-icon">🎯</div>
      <div>
        <div class="kpi-val">0.70–0.80</div>
        <div class="kpi-lbl">Lợi Thế Quy Mô 400c</div>
        <div class="kpi-desc">Vượt ALNS-Base (c2_4_1, r2_4_1)</div>
      </div>
    </div>
    <div class="kpi-card emerald">
      <div class="kpi-icon">🌐</div>
      <div>
        <div class="kpi-val">0.27%</div>
        <div class="kpi-lbl">Khoảng Cách BKS</div>
        <div class="kpi-desc">Solomon RC1 (NV-matched)</div>
      </div>
    </div>
  </div>

  <!-- MAIN BODY: 2 COLUMNS -->
  <div class="content-grid">

    <!-- LEFT COLUMN -->
    <div class="col">

      <!-- SECTION 1: INTRODUCTION -->
      <div class="section-card">
        <div class="card-hdr">
          <span class="badge-num">1</span>
          <span>GIỚI THIỆU &amp; ĐỘNG LỰC NGHIÊN CỨU</span>
        </div>
        <div class="card-body">
          <div class="b-item"><strong>Bài toán VRPTW:</strong> Định tuyến đội xe đồng nhất phục vụ khách hàng có tọa độ, nhu cầu tải trọng <i>q<sub>i</sub></i> và khung thời gian phục vụ [<i>e<sub>i</sub></i>, <i>l<sub>i</sub></i>]. Mục tiêu là tối ưu hóa từ điển phân cấp (Lexicographic): <span class="hl-amb">ưu tiên giảm số xe <i>N</i><sub>V</sub>, sau đó giảm tổng quãng đường <i>D</i><sub>T</sub></span>.</div>
          <div class="b-item"><strong>Hạn chế của ALNS cổ điển:</strong> Chọn toán tử ngẫu nhiên roulette-wheel và Simulated Annealing tĩnh, dễ kẹt ở cực tiểu cục bộ sâu (plateau).</div>
          <div class="b-item"><strong>Hạn chế của Deep RL thuần túy:</strong> Mô hình end-to-end không bảo đảm 100% ràng buộc thời gian và suy thoái mạnh ngoài phân phối dữ liệu (OOD).</div>
          <div style="background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.22); border-radius: 6px; padding: 2mm 3mm;">
            <strong style="color: #60a5fa;">Hàm mục tiêu phân cấp chuẩn hóa (Lexicographic VRPTW):</strong>
            <div style="font-family: 'Fira Code', monospace; font-size: 7.5pt; color: #38bdf8; margin-top: 1mm; font-weight: 600;">
              lex min f(s) = ⟨ N<sub>V</sub>(s), D<sub>T</sub>(s) ⟩ ≡ min [ M · N<sub>V</sub>(s) + D<sub>T</sub>(s) ], &nbsp; M = 10⁵ ≫ max D<sub>T</sub>
            </div>
            <div style="font-size: 6.8pt; color: #94a3b8; margin-top: 0.5mm;">
              Ràng buộc tuyệt đối: Cửa sổ thời gian [<i>e<sub>i</sub></i>, <i>l<sub>i</sub></i>] • Sức chứa xe <i>Q</i> • Thời gian phục vụ <i>s<sub>i</sub></i> • Bảo toàn luồng kho depot.
            </div>
          </div>
        </div>
      </div>

      <!-- SECTION 2: METHODOLOGY & HERO ARCHITECTURE -->
      <div class="section-card">
        <div class="card-hdr">
          <span class="badge-num">2</span>
          <span>PHƯƠNG PHÁP: KIẾN TRÚC PHÂN CẤP TRI-LEVEL DDQN-ALNS</span>
        </div>
        <div class="card-body" style="gap: 2.2mm;">
          <div style="font-size: 7.4pt; color: #cbd5e1;">Hệ thống điều khiển phân cấp 3 tầng phối hợp thích ứng theo cả quy mô thời gian (macro/micro) và không gian tìm kiếm:</div>

          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 2mm;">
            <div style="background: rgba(20, 65, 115, 0.25); border: 1px solid rgba(59, 130, 246, 0.4); border-radius: 5px; padding: 1.8mm 2mm;">
              <div style="color: #60a5fa; font-weight: 700; font-size: 7.3pt;">TẦNG 1: MACRO DDQN</div>
              <div style="font-size: 6.6pt; color: #cbd5e1; margin-top: 0.5mm;">Semi-MDP (Δ<sub>seg</sub>=100 iters), 13 chiều trạng thái → <span class="hl-grn">7 chế độ chiến lược</span> (Intensify, Diversify, TW-Rescue, Recombine, v.v.).</div>
            </div>
            <div style="background: rgba(15, 95, 85, 0.25); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 5px; padding: 1.8mm 2mm;">
              <div style="color: #34d399; font-weight: 700; font-size: 7.3pt;">TẦNG 2: MICRO &amp; LAC</div>
              <div style="font-size: 6.6pt; color: #cbd5e1; margin-top: 0.5mm;">Micro DDQN 20 chiều, <span class="hl-amb">65 cặp toán tử</span>. Cổng Entropy Gating + Learned Acceptance (LAC lookahead <i>H</i>=80).</div>
            </div>
            <div style="background: rgba(110, 25, 75, 0.25); border: 1px solid rgba(244, 114, 182, 0.4); border-radius: 5px; padding: 1.8mm 2mm;">
              <div style="color: #f472b6; font-weight: 700; font-size: 7.3pt;">TẦNG 3: ALNS &amp; HiGHS</div>
              <div style="font-size: 6.6pt; color: #cbd5e1; margin-top: 0.5mm;">Kiểm tra khả thi <i>O</i>(1) Savelsbergh, Contrastive GNN tỉa 98.7% cạnh. Tái tổ hợp Set Partitioning MILP qua HiGHS (4.0s).</div>
            </div>
          </div>

          <!-- Hero Architecture Image -->
          <div class="img-box">
            <img src="{arch_b64}" alt="Tri-Level Coordinated Architecture">
            <div class="img-caption">Hình 1. Sơ đồ kiến trúc phân cấp Tri-Level Hybrid DDQN-ALNS (Luồng điều khiển dọc, vòng phản hồi trạng thái &amp; tái tổ hợp cột)</div>
          </div>

          <!-- Methodological Deep Dive Breakdown -->
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2.2mm;">
            <div style="background: rgba(255, 255, 255, 0.025); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 5px; padding: 1.8mm 2.2mm;">
              <strong style="color: #38bdf8; font-size: 7.2pt;">Mô Hình GNN Tương Phản (Contrastive GNN):</strong>
              <div style="font-size: 6.6pt; color: #cbd5e1; margin-top: 0.5mm;">
                Huấn luyện qua hàm mất mát hỗn hợp:
                <div style="font-family: 'Fira Code', monospace; color: #93c5fd; margin: 0.5mm 0;">
                  ℒ = ℒ<sub>BCE</sub> + 0.25 ℒ<sub>InfoNCE</sub>
                </div>
                Tỉa giảm 98.74% không gian cạnh chèn (giữ <i>k</i>=25 láng giềng kNN), giúp tăng tốc ALNS gấp <strong>14.2×</strong> mà không bỏ sót nghiệm tối ưu.
              </div>
            </div>
            <div style="background: rgba(255, 255, 255, 0.025); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 5px; padding: 1.8mm 2.2mm;">
              <strong style="color: #fbbf24; font-size: 7.2pt;">Tái Tổ Hợp Set Partitioning (HiGHS MILP):</strong>
              <div style="font-size: 6.6pt; color: #cbd5e1; margin-top: 0.5mm;">
                Trích xuất tập tuyến đường từ Dual-Slot Route Pool (75% tuyến tinh hoa, 25% tuyến đơn dài).
                Giải bài toán phủ tập hợp bằng solver <strong>HiGHS (4.0s timeout)</strong>, tìm nghiệm tái tổ hợp tối ưu toàn cục.
              </div>
            </div>
          </div>

        </div>
      </div>

    </div>

    <!-- RIGHT COLUMN -->
    <div class="col">

      <!-- SECTION 3: BENCHMARK & COLD-START PROTOCOL -->
      <div class="section-card">
        <div class="card-hdr">
          <span class="badge-num">3</span>
          <span>TẬP DỮ LIỆU &amp; GIAO THỨC ĐỘC LẬP COLD-START</span>
        </div>
        <div class="card-body">
          <table style="margin-top: 0;">
            <tr><th>Tập Thực Nghiệm</th><th>Số Bài Toán</th><th>Quy Mô (Khách)</th><th>Cấu Trúc Không-Thời Gian</th></tr>
            <tr><td><strong>Solomon-100</strong></td><td>56</td><td>100</td><td>C1, C2 (Cụm), R1, R2 (Ngẫu nhiên), RC1, RC2 (Hỗn hợp)</td></tr>
            <tr><td><strong>Homberger-200</strong></td><td>60</td><td>200</td><td>10 bài toán × 6 họ cấu trúc địa hình</td></tr>
            <tr><td><strong>Homberger-400</strong></td><td>60</td><td>400</td><td>Quy mô lớn thử thách giới hạn suy thoái thuật toán</td></tr>
            <tr style="font-weight:700;"><td style="color:#fbbf24;">Tổng cộng</td><td style="color:#fbbf24;">176</td><td>100 – 400</td><td>Đánh giá trên 5 hạt giống ngẫu nhiên độc lập (580 lượt chạy)</td></tr>
          </table>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2.2mm; margin-top: 1mm;">
            <div class="finding ok" style="padding: 1.5mm 2.5mm;">
              <strong style="color: #34d399;">Quy chuẩn Cold-Start độc lập:</strong>
              <div style="font-size: 6.8pt; color: #cbd5e1; margin-top: 0.5mm;">Xóa bỏ hoàn toàn hiện tượng rò rỉ bộ nhớ cache. Mọi thuật toán xuất phát từ lời giải tham lam ban đầu trong thư mục sạch.</div>
            </div>
            <div class="finding stat" style="padding: 1.5mm 2.5mm;">
              <strong style="color: #60a5fa;">Chiến lược Domain Randomization:</strong>
              <div style="font-size: 6.8pt; color: #cbd5e1; margin-top: 0.5mm;">Mô hình học sâu được huấn luyện trên không gian ngẫu nhiên 20–100 khách và tổng quát hóa zero-shot sang Homberger 200–400.</div>
            </div>
          </div>
        </div>
      </div>

      <!-- SECTION 4: EXPERIMENTAL RESULTS & STATISTICAL ANALYSIS -->
      <div class="section-card">
        <div class="card-hdr">
          <span class="badge-num">4</span>
          <span>KẾT QUẢ THỰC NGHIỆM &amp; PHÂN TÍCH THỐNG KÊ</span>
        </div>
        <div class="card-body" style="gap: 2mm;">
          <table>
            <tr><th>Bộ Dữ Liệu</th><th>Thuật Toán</th><th>Số Xe (<i>N</i><sub>V</sub>) ↓</th><th>Quãng Đường (<i>D</i><sub>T</sub>) ↓</th><th>Chênh Lệch Quãng Đường</th><th>Kiểm Định Wilcoxon</th></tr>
            <tr><td rowspan="3"><strong>Solomon-100</strong><br>(<i>N</i>=56)</td><td>ALNS-Base</td><td>7.54</td><td>1017.31</td><td>— (Cơ sở so sánh)</td><td>—</td></tr>
            <tr><td><strong>Hybrid-DDQN</strong></td><td class="best">7.34</td><td>1017.82</td><td><i>N</i><sub>V</sub> giảm 0.20 xe</td><td class="pval">p = 0.00127</td></tr>
            <tr><td><strong>BKS (SINTEF)</strong></td><td class="best">7.07</td><td>1013.36</td><td>0.27% (trên RC1 khớp <i>N</i><sub>V</sub>)</td><td>Kỷ lục thế giới</td></tr>
            <tr><td rowspan="2"><strong>Homberger-200</strong><br>(<i>N</i>=60)</td><td>ALNS-Base</td><td>11.87</td><td>3009.91</td><td>— (Cơ sở so sánh)</td><td>—</td></tr>
            <tr><td><strong>Hybrid-DDQN</strong></td><td class="best">11.58</td><td class="best">2844.73</td><td class="diff">−165.18 km (−5.49%)</td><td class="pval">p = 1.34 × 10⁻⁹</td></tr>
            <tr><td rowspan="2"><strong>Homberger-400</strong><br>(c2_4_1 / r2_4_1)</td><td>ALNS-Base</td><td>13.00 / 8.80</td><td>4312 / 8950</td><td>— (Cơ sở so sánh)</td><td>—</td></tr>
            <tr><td><strong>Hybrid-DDQN</strong></td><td class="best">12.20 / 8.10</td><td class="best">4180 / 8720</td><td class="diff">−0.80 / −0.70 xe</td><td class="pval">p = 0.0078 / 0.0156</td></tr>
          </table>

          <!-- 2 Figures Row: Convergence & Route Visualization -->
          <div style="display: grid; grid-template-columns: 1.18fr 0.82fr; gap: 2mm; margin-top: 1mm;">
            <div class="img-box">
              <img src="{conv_b64}" alt="Anytime Convergence Curves">
              <div class="img-caption">Hình 2. Đường cong hội tụ Anytime (Hybrid-DDQN vượt plateau nhanh hơn ALNS-Base)</div>
            </div>
            <div class="img-box">
              <img src="{route_b64}" alt="Route Map RC101">
              <div class="img-caption">Hình 3. Trực quan tuyến đường tối ưu trên RC101</div>
            </div>
          </div>

          <div style="display: flex; gap: 2mm; margin-top: 1mm;">
            <div class="finding win" style="flex: 1; padding: 1.5mm 2.2mm;">
              <strong style="color: #fbbf24;">Quy mô 200 khách (TD Dominance):</strong> Cùng hội tụ về sàn số xe tối thiểu, Hybrid-DDQN vượt trội về độ ổn định (tỉ lệ suy thoái chỉ 0%–20% vs 30%–70% của ALNS-Base) và tối ưu quãng đường thêm <strong>1.75% đến 4.07%</strong> khi khớp số xe.
            </div>
            <div class="finding scale" style="flex: 1; padding: 1.5mm 2.2mm;">
              <strong style="color: #c084fc;">Quy mô 400 khách (Graceful Degradation):</strong> Khắc phục hiện tượng dừng sớm của ALNS-Base, duy trì ưu thế dẫn trước <strong>0.70 đến 0.80 xe</strong> có ý nghĩa thống kê cao (Wilcoxon <i>p</i> = 0.0078 trên c2_4_1).
            </div>
          </div>
        </div>
      </div>

      <!-- SECTION 5: CONTRIBUTIONS & CONCLUSION -->
      <div class="section-card">
        <div class="card-hdr">
          <span class="badge-num">5</span>
          <span>ĐÓNG GÓP KHOA HỌC &amp; HƯỚNG PHÁT TRIỂN</span>
        </div>
        <div class="card-body">
          <div class="b-item"><strong>Đóng góp lý thuyết:</strong> Đề xuất khung kiến trúc phân cấp Tri-Level kết hợp điều khiển chiến lược DRL, tốc độ thích ứng của ALNS, và tái cấu trúc tối ưu toàn cục của Set Partitioning MILP (HiGHS).</div>
          <div class="b-item"><strong>Đóng góp thực nghiệm:</strong> Thiết lập quy chuẩn kiểm thử Cold-Start nghiêm ngặt, minh bạch hóa hiện tượng rò rỉ bộ nhớ trong các nghiên cứu trước đây và cung cấp bộ dữ liệu đối chuẩn tin cậy cho cộng đồng.</div>
          <div class="b-item"><strong>Công bố quốc tế:</strong> Toàn văn công trình đã được hoàn thiện bản thảo gửi đăng tại tạp chí khoa học uy tín <strong>IEEE Access</strong> (SCIE, Q1, IF 3.4).</div>
          <div class="b-item"><strong>Khả năng tái lập:</strong> Mã nguồn mở đầy đủ, checkpoint mô hình và nhật ký thực thi trên 74 bài toán chuẩn được công khai minh bạch.</div>
        </div>
      </div>

    </div>

  </div>

  <!-- FOOTER -->
  <div class="poster-footer">
    <div><strong>Hội đồng NCKHSV 2026</strong> — Khoa Công nghệ Thông tin, Trường Đại học Tôn Đức Thắng (TDTU)</div>
    <div>Đề tài: <em>Tri-Level Hybrid DDQN-ALNS for Vehicle Routing Problem with Time Windows</em></div>
    <div>Liên hệ: <code>huynhnthuy@tdtu.edu.vn</code> | <code>hotlinh@tdtu.edu.vn</code></div>
  </div>

</div>
</body>
</html>
"""

    output_html = os.path.join(base_dir, "poster_tdtu_nckhsv.html")
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated HTML poster successfully: {output_html}")

if __name__ == "__main__":
    main()
