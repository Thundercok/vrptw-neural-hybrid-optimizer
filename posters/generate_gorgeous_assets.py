"""
generate_gorgeous_assets.py
Renders gorgeous, high-resolution (3x Retina, print-ready) standalone graphics
for the academic poster:
  1. Table 1: Benchmark Datasets (Academic Booktabs)
  2. Table 2: Benchmark Results (Solomon-100 & Homberger-200 with significance)
  3. Figure: 4 KPI Callout Cards (Glassmorphism & High-contrast typography)
  4. Figure: Side-by-side Authentic Publication Route Maps (R101 & RC101)
  5. Figure: Real-world NAMI Dispatch Control Tower Deployment Showcase
"""

import base64
import mimetypes
import os
import shutil

from playwright.sync_api import sync_playwright

REPO_ROOT = "/Users/thundercock2/Documents/Github/VRPTW-Research-Optimization"
SRC_ROOT = os.path.join(REPO_ROOT, "VRPTW-Research-Optimization")
OUT_DIR = "/Users/thundercock2/Desktop/Giao_Dien_Poster_Chat_Luong_Cao"
os.makedirs(OUT_DIR, exist_ok=True)


def get_b64(path):
    full = os.path.join(SRC_ROOT, path)
    if not os.path.exists(full):
        full = os.path.join(REPO_ROOT, path)
    ext = os.path.splitext(full)[1].lower()
    mime = mimetypes.types_map.get(ext, "image/png")
    with open(full, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode('utf-8')}"


r101_b64 = get_b64("docs/figures/route_R101.png")
rc101_b64 = get_b64("docs/figures/route_RC101.png")
nami_b64 = get_b64("docs/figures/nami_dispatch_real_hcmc.png")
arch_b64 = get_b64("docs/figures/poster_architecture.png")

html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800;900&family=Plus+Jakarta+Sans:wght@500;600;700;800&family=JetBrains+Mono:wght@600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #e2e8f0;
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    color: #0f172a;
    padding: 40px;
    display: flex;
    flex-direction: column;
    gap: 50px;
  }}

  .export-card {{
    background: #ffffff;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.1), 0 8px 10px -6px rgba(15, 23, 42, 0.05);
    border: 1px solid #cbd5e1;
    display: inline-block;
  }}

  /* HEADER BANNER */
  .section-badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #fef3d6;
    border-left: 6px solid #0c1e5a;
    padding: 8px 16px;
    border-radius: 4px;
    margin-bottom: 16px;
  }}
  .section-badge-title {{
    font-family: 'Montserrat', sans-serif;
    font-size: 19px;
    font-weight: 800;
    color: #0c1e5a;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .section-badge-title span {{ color: #1d4ed8; }}

  /* TABLE 1: DATASETS */
  #card-datasets {{ width: 920px; }}
  .booktabs-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 15px;
    text-align: left;
  }}
  .booktabs-table thead th {{
    border-top: 3px solid #0c1e5a;
    border-bottom: 1.5px solid #0c1e5a;
    padding: 12px 14px;
    font-family: 'Montserrat', sans-serif;
    font-weight: 800;
    color: #0c1e5a;
    background: #f8fafc;
    letter-spacing: 0.3px;
  }}
  .booktabs-table tbody td {{
    padding: 11px 14px;
    border-bottom: 1px solid #e2e8f0;
    color: #334155;
    line-height: 1.45;
  }}
  .booktabs-table tbody tr:last-child td {{
    border-bottom: 2.5px solid #0c1e5a;
  }}
  .badge-tag {{
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 700;
  }}
  .bt-blue {{ background: #dbeafe; color: #1e40af; }}
  .bt-purple {{ background: #f3e8ff; color: #6b21a8; }}
  .bt-amber {{ background: #fef3c7; color: #92400e; }}

  /* TABLE 2: RESULTS */
  #card-results {{ width: 1240px; }}
  .results-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 14.5px;
    text-align: center;
  }}
  .results-table thead th {{
    border-top: 3px solid #0c1e5a;
    border-bottom: 1.5px solid #0c1e5a;
    padding: 12px 10px;
    font-family: 'Montserrat', sans-serif;
    font-weight: 800;
    color: #0c1e5a;
    background: #f8fafc;
  }}
  .results-table tbody td {{
    padding: 10px 10px;
    border-bottom: 1px solid #e2e8f0;
    color: #334155;
  }}
  .results-table tbody tr:last-child td {{
    border-bottom: 2.5px solid #0c1e5a;
  }}
  .row-highlight {{
    background: #eff6ff !important;
  }}
  .row-highlight td {{
    font-weight: 700;
    color: #1e40af !important;
  }}
  .pill-stat {{
    display: inline-block;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 800;
  }}
  .ps-win {{ background: #dbeafe; color: #1e40af; border: 1px solid #93c5fd; }}
  .ps-sig {{ background: #dcfce7; color: #15803d; border: 1px solid #86efac; }}
  .ps-base {{ background: #f1f5f9; color: #64748b; }}

  /* KPI CARDS (2x2) */
  #card-kpi {{ width: 780px; }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }}
  .kpi-tile {{
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border: 1.5px solid #cbd5e1;
    border-radius: 10px;
    padding: 16px 20px;
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    gap: 4px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04);
  }}
  .kt-blue {{ border-left: 6px solid #1d4ed8; }}
  .kt-teal {{ border-left: 6px solid #0d9488; }}
  .kt-green {{ border-left: 6px solid #16a34a; }}
  .kt-purple {{ border-left: 6px solid #7e22ce; }}

  .kpi-val {{
    font-family: 'Montserrat', sans-serif;
    font-size: 32px;
    font-weight: 900;
    line-height: 1.1;
  }}
  .kv-blue {{ color: #1d4ed8; }}
  .kv-teal {{ color: #0f766e; }}
  .kv-green {{ color: #15803d; }}
  .kv-purple {{ color: #7e22ce; }}

  .kpi-tit {{
    font-size: 13.5px;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.35;
  }}
  .kpi-sub {{
    font-size: 11.5px;
    font-weight: 600;
    color: #64748b;
  }}

  /* ROUTE COMPARISON (FIGURE) */
  #card-routes {{ width: 1240px; }}
  .routes-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }}
  .route-panel {{
    background: #f8fafc;
    border: 1.5px solid #cbd5e1;
    border-radius: 8px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  .route-img {{
    width: 100%;
    height: 380px;
    object-fit: contain;
    border-radius: 4px;
    background: #ffffff;
  }}
  .route-caption {{
    margin-top: 10px;
    font-size: 13px;
    font-weight: 700;
    color: #334155;
    text-align: center;
    line-height: 1.4;
  }}
  .route-caption b {{ color: #0c1e5a; }}

  /* NAMI DISPATCH SHOWCASE */
  #card-nami {{ width: 780px; }}
  .nami-box {{
    background: #ffffff;
    border: 2px solid #86efac;
    border-radius: 10px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    box-shadow: 0 10px 15px -3px rgba(22, 101, 52, 0.08);
  }}
  .nami-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .nami-title {{
    font-family: 'Montserrat', sans-serif;
    font-size: 15px;
    font-weight: 900;
    color: #166534;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .nami-badge {{
    background: #dcfce7;
    color: #15803d;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 800;
    border: 1px solid #86efac;
  }}
  .nami-img-wrap {{
    width: 100%;
    height: 250px;
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid #cbd5e1;
    background: #0f172a;
  }}
  .nami-img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: top center;
  }}
  .nami-desc {{
    font-size: 13px;
    line-height: 1.5;
    color: #334155;
    text-align: justify;
  }}
  .nami-desc b {{ color: #166534; }}
</style>
</head>
<body>

  <!-- 1. TABLE DATASETS -->
  <div id="card-datasets" class="export-card">
    <div class="section-badge">
      <div class="section-badge-title"><span>[ ]</span> 2. TẬP DỮ LIỆU & THIẾT LẬP THỰC NGHIỆM</div>
    </div>
    <table class="booktabs-table">
      <thead>
        <tr>
          <th>Bộ Thực Nghiệm</th>
          <th>Số Bài</th>
          <th>Quy Mô</th>
          <th>Đặc Trưng Không - Thời Gian</th>
          <th>Phân Loại</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><b style="color: #0c1e5a; font-size: 16px;">Solomon-100</b></td>
          <td><b>56</b> bài</td>
          <td><b>100</b> khách</td>
          <td>6 họ bài toán: Cụm (C1, C2), Ngẫu nhiên (R1, R2), Hỗn hợp (RC1, RC2)</td>
          <td><span class="badge-tag bt-blue">Quy mô cơ sở</span></td>
        </tr>
        <tr>
          <td><b style="color: #0c1e5a; font-size: 16px;">Homberger-200</b></td>
          <td><b>60</b> bài</td>
          <td><b>200</b> khách</td>
          <td>10 bài toán &times; 6 họ cấu trúc địa hình không gian phức tạp</td>
          <td><span class="badge-tag bt-purple">Đột phá Quãng đường</span></td>
        </tr>
        <tr>
          <td><b style="color: #0c1e5a; font-size: 16px;">Homberger-400</b></td>
          <td><b>60</b> bài</td>
          <td><b>400</b> khách</td>
          <td>Quy mô lớn thử thách cực hạn năng lực tìm kiếm và tránh dừng sớm</td>
          <td><span class="badge-tag bt-amber">Thử thách Cực hạn</span></td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- 2. TABLE RESULTS -->
  <div id="card-results" class="export-card">
    <div class="section-badge">
      <div class="section-badge-title"><span>[ ]</span> 4. KẾT QUẢ THỰC NGHIỆM ĐỐI CHUẨN ĐỊNH LƯỢNG</div>
    </div>
    <table class="results-table">
      <thead>
        <tr>
          <th>Tập Dữ Liệu</th>
          <th>Thuật Toán</th>
          <th>Số Xe TB (N<sub>V</sub>) &darr;</th>
          <th>Quãng Đường TB (D<sub>T</sub>) &darr;</th>
          <th>Thời Gian (s)</th>
          <th>Ý Nghĩa Thống Kê (Wilcoxon)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td rowspan="3" style="font-weight: 800; font-size: 16px; color: #0c1e5a; background: #f8fafc; border-right: 1.5px solid #cbd5e1;">
            Solomon-100<br><span style="font-size: 12px; color: #64748b; font-weight: 500;">(56 bài toán)</span>
          </td>
          <td><b>BKS (Kỷ lục thế giới)</b></td>
          <td><span style="font-family: 'JetBrains Mono', monospace; font-weight: 700;">7.07</span></td>
          <td><span style="font-family: 'JetBrains Mono', monospace; font-weight: 700;">1013.36</span></td>
          <td>—</td>
          <td><span class="pill-stat ps-base">Ground Truth</span></td>
        </tr>
        <tr>
          <td>ALNS-Base (Ropke & Pisinger)</td>
          <td><span style="font-family: 'JetBrains Mono', monospace;">7.54</span></td>
          <td><span style="font-family: 'JetBrains Mono', monospace;">1017.31</span></td>
          <td>10.1s</td>
          <td><span class="pill-stat ps-base">Baseline</span></td>
        </tr>
        <tr class="row-highlight">
          <td><b>Hybrid-DDQN (Đề xuất)</b></td>
          <td><span style="font-family: 'JetBrains Mono', monospace; font-size: 16px;">7.34*</span></td>
          <td><span style="font-family: 'JetBrains Mono', monospace;">1017.82</span></td>
          <td>39.0s</td>
          <td><span class="pill-stat ps-win">p = 0.00127 (Thắng vượt trội)</span></td>
        </tr>

        <tr>
          <td rowspan="2" style="font-weight: 800; font-size: 16px; color: #0c1e5a; background: #f8fafc; border-right: 1.5px solid #cbd5e1;">
            Homberger-200<br><span style="font-size: 12px; color: #64748b; font-weight: 500;">(60 bài toán)</span>
          </td>
          <td>ALNS-Base (Ropke & Pisinger)</td>
          <td><span style="font-family: 'JetBrains Mono', monospace;">11.87</span></td>
          <td><span style="font-family: 'JetBrains Mono', monospace;">3009.91</span></td>
          <td>3.9s</td>
          <td><span class="pill-stat ps-base">Baseline</span></td>
        </tr>
        <tr class="row-highlight">
          <td><b>Hybrid-DDQN (Đề xuất)</b></td>
          <td><span style="font-family: 'JetBrains Mono', monospace; font-size: 16px;">11.58*</span></td>
          <td><span style="font-family: 'JetBrains Mono', monospace; font-size: 16px; color: #166534;">2844.73* (-165.18 km)</span></td>
          <td>35.8s</td>
          <td><span class="pill-stat ps-sig">p = 1.34&times;10<sup>-9</sup> (Đột phá thống kê)</span></td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- 3. KPI CARDS -->
  <div id="card-kpi" class="export-card">
    <div class="kpi-grid">
      <div class="kpi-tile kt-blue">
        <div class="kpi-val kv-blue">-165.18 km</div>
        <div class="kpi-tit">Quãng đường tiết kiệm TB (Homberger-200)</div>
        <div class="kpi-sub">Wilcoxon p = 1.34&times;10<sup>-9</sup> (Đột phá thống kê)</div>
      </div>
      <div class="kpi-tile kt-teal">
        <div class="kpi-val kv-teal">-98.74%</div>
        <div class="kpi-tit">Cắt tỉa không gian tìm kiếm cạnh</div>
        <div class="kpi-sub">Contrastive GNN &bull; O(N<sup>2</sup>) &rarr; O(kN)</div>
      </div>
      <div class="kpi-tile kt-green">
        <div class="kpi-val kv-green">100%</div>
        <div class="kpi-tit">Bảo toàn tính khả thi vận hành</div>
        <div class="kpi-sub">Zero vi phạm tải trọng & khung giờ (580 runs)</div>
      </div>
      <div class="kpi-tile kt-purple">
        <div class="kpi-val kv-purple">Zero-Shot</div>
        <div class="kpi-tit">Khả năng tổng quát hóa quy mô đồ thị</div>
        <div class="kpi-sub">Huấn luyện N&le;100 &rarr; Suy luận N=400 (Không fine-tuning)</div>
      </div>
    </div>
  </div>

  <!-- 4. ROUTE COMPARISON -->
  <div id="card-routes" class="export-card">
    <div class="section-badge">
      <div class="section-badge-title"><span>[ ]</span> HẢI ĐỒ LỘ TRÌNH TỐI ƯU THỰC NGHIỆM ĐỐI CHUẨN BKS</div>
    </div>
    <div class="routes-grid">
      <div class="route-panel">
        <img src="{r101_b64}" class="route-img" alt="Lộ trình R101">
        <div class="route-caption"><b>Hải đồ lộ trình R101:</b> Phân bố ngẫu nhiên đều, N<sub>V</sub> = 19 xe khớp chuẩn BKS, TD = 1650.8 km</div>
      </div>
      <div class="route-panel">
        <img src="{rc101_b64}" class="route-img" alt="Lộ trình RC101">
        <div class="route-caption"><b>Hải đồ lộ trình RC101:</b> Phân bố hỗn hợp cụm & ngẫu nhiên, N<sub>V</sub> = 15 xe khớp chuẩn BKS, TD = 1644.8 km</div>
      </div>
    </div>
  </div>

  <!-- 5. NAMI SHOWCASE -->
  <div id="card-nami" class="export-card">
    <div class="nami-box">
      <div class="nami-header">
        <div class="nami-title">🚀 Ứng Dụng Thực Tiễn: NAMI Dispatch Control Tower</div>
        <div class="nami-badge">Bản Đồ Đường Bộ TP.HCM</div>
      </div>
      <div class="nami-img-wrap">
        <img src="{nami_b64}" class="nami-img" alt="NAMI Dispatch">
      </div>
      <div class="nami-desc">
        <b>Triển khai thực tế:</b> Thuật toán điều phối chính xác 18 đội xe trên mạng lưới đường bộ thực tế TP.HCM, tiết kiệm <b>-1.40%</b> quãng đường so với ALNS Base (704.03 km vs 714.05 km) và lập lịch tài xế qua biểu đồ Gantt thời gian thực.
      </div>
    </div>
  </div>

</body>
</html>
"""

html_file = "/tmp/poster_assets_render.html"
with open(html_file, "w", encoding="utf-8") as f:
    f.write(html_content)

print("Starting Playwright high-res renderer (DeviceScaleFactor=3.0)...")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 3000}, device_scale_factor=3.0)
    page.goto(f"file://{html_file}", wait_until="networkidle")

    items = [
        ("card-datasets", "01_Bang_Tap_Du_Lieu_Datasets.png"),
        ("card-results", "02_Bang_Ket_Qua_Thuc_Nghiem_Results.png"),
        ("card-kpi", "03_Bo_4_The_KPI_Metrics.png"),
        ("card-routes", "04_Cap_Hai_Do_Lo_Trinh_R101_RC101.png"),
        ("card-nami", "05_Ung_Dung_Thuc_Te_NAMI_TPHCM.png"),
    ]

    for element_id, fname in items:
        elem = page.locator(f"#{element_id}")
        target_path = os.path.join(OUT_DIR, fname)
        elem.screenshot(path=target_path)
        print(f"Exported: {target_path}")

    browser.close()

# Also zip these ready-made graphic cards into Desktop
shutil.make_archive("/Users/thundercock2/Desktop/Anh_Render_Bang_Bieu_Figures_Poster", "zip", OUT_DIR)
print("Created zip archive at: /Users/thundercock2/Desktop/Anh_Render_Bang_Bieu_Figures_Poster.zip")
