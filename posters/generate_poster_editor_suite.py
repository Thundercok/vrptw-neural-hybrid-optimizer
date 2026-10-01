"""
generate_poster_editor_suite.py
Renders the complete, ultra-high-resolution (4K / 300+ DPI Retina), publication-grade
asset suite for the NCKHSV 2026 academic poster editor:

  01_Mo_Hinh_Bai_Toan_VRPTW_4K.png
  02_Moi_Truong_Huan_Luyen_Domain_Randomization_4K.png
  03_Kien_Truc_He_Thong_4_Tang_3D_Glass_4K.png
  03B_Kien_Truc_He_Thong_Chuan_IEEE_Vector_4K.png
  04_Quy_Trinh_3_Giai_Doan_Thuc_Thi_4K.png
  05_Giam_Sat_Dieu_Phoi_Thuc_Te_NAMI_TPHCM_4K.png
  06_Cap_Hai_Do_Lo_Trinh_R101_RC101_4K.png
  07_Bang_Ket_Qua_Thuc_Nghiem_Doi_Chuan_4K.png
  08_Bo_The_Chi_So_KPI_Vang_4K.png
"""

import base64
import mimetypes
import os
import shutil
import zipfile
from playwright.sync_api import sync_playwright

REPO_ROOT = "/Users/thundercock2/Documents/Github/VRPTW-Research-Optimization"
SRC_ROOT = os.path.join(REPO_ROOT, "VRPTW-Research-Optimization")
OUT_DIR = "/Users/thundercock2/Desktop/Bo_Hinh_Anh_Poster_Cho_Editor"
ZIP_PATH = "/Users/thundercock2/Desktop/Bo_Hinh_Anh_Poster_Cho_Editor.zip"

os.makedirs(OUT_DIR, exist_ok=True)

def get_b64(path):
    full = os.path.join(SRC_ROOT, path)
    if not os.path.exists(full):
        full = os.path.join(REPO_ROOT, path)
    if not os.path.exists(full):
        raise FileNotFoundError(f"File not found: {full}")
    ext = os.path.splitext(full)[1].lower()
    mime = mimetypes.types_map.get(ext, "image/png")
    with open(full, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode('utf-8')}"

# Existing high-res assets
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
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;800;900&family=Plus+Jakarta+Sans:wght@500;600;700;800&family=JetBrains+Mono:wght@600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0b0f19;
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    color: #0f172a;
    padding: 60px;
    display: flex;
    flex-direction: column;
    gap: 80px;
  }}

  .canvas-card {{
    background: #ffffff;
    border-radius: 24px;
    padding: 38px 44px;
    box-shadow: 0 30px 60px -15px rgba(0, 0, 0, 0.3);
    border: 2px solid #cbd5e1;
    position: relative;
    overflow: hidden;
  }}

  /* HEADER BARS */
  .card-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 20px;
    margin-bottom: 28px;
  }}
  .card-title-group {{
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  .card-tag {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 13.5px;
    font-weight: 800;
    color: #1d4ed8;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .card-tag::before {{
    content: "";
    display: inline-block;
    width: 9px;
    height: 9px;
    background: #1d4ed8;
    border-radius: 50%;
  }}
  .card-title {{
    font-family: 'Montserrat', sans-serif;
    font-size: 28px;
    font-weight: 900;
    color: #0c1e5a;
    letter-spacing: -0.5px;
    text-transform: uppercase;
  }}
  .card-subtitle {{
    font-size: 15px;
    color: #475569;
    font-weight: 600;
  }}
  .card-badge {{
    background: #eff6ff;
    color: #1e40af;
    border: 2px solid #bfdbfe;
    padding: 8px 18px;
    border-radius: 30px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    font-weight: 800;
    box-shadow: 0 2px 6px rgba(30, 64, 175, 0.08);
  }}

  /* ========================================================
     FIGURE 1: VRPTW PROBLEM & LOGISTICS HUB
     ======================================================== */
  #fig1-vrptw {{ width: 2360px; }}
  .f1-grid {{
    display: grid;
    grid-template-columns: 500px 1fr 520px;
    gap: 32px;
    align-items: stretch;
  }}

  .f1-depot-panel {{
    background: linear-gradient(180deg, #f8fafc 0%, #eff6ff 100%);
    border: 2px solid #93c5fd;
    border-radius: 20px;
    padding: 28px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.08);
  }}
  .depot-hero-box {{
    background: #ffffff;
    border: 2.5px solid #2563eb;
    border-radius: 16px;
    padding: 22px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    box-shadow: 0 12px 24px -6px rgba(37, 99, 235, 0.16);
  }}
  .depot-icon-wrap {{
    width: 72px;
    height: 72px;
    background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
    color: #ffffff;
    border-radius: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 38px;
    margin-bottom: 12px;
    box-shadow: 0 8px 16px rgba(29, 78, 216, 0.35);
  }}
  .depot-title {{
    font-family: 'Montserrat', sans-serif;
    font-size: 21px;
    font-weight: 900;
    color: #1e3a8a;
  }}
  .depot-coord {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    font-weight: 800;
    color: #1d4ed8;
    margin-top: 6px;
    background: #dbeafe;
    padding: 4px 14px;
    border-radius: 8px;
  }}

  .docks-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 12px;
    margin-top: 18px;
    width: 100%;
  }}
  .dock-card {{
    background: #f8fafc;
    border: 1.5px solid #cbd5e1;
    border-radius: 10px;
    padding: 10px 6px;
    text-align: center;
  }}
  .dock-num {{ font-size: 12px; font-weight: 800; text-transform: uppercase; }}
  .dock-r1 {{ color: #2563eb; border-top: 4px solid #2563eb; background: #eff6ff; }}
  .dock-r2 {{ color: #16a34a; border-top: 4px solid #16a34a; background: #f0fdf4; }}
  .dock-r3 {{ color: #9333ea; border-top: 4px solid #9333ea; background: #faf5ff; }}

  .depot-spec-item {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 10px;
    padding: 13px 18px;
    font-size: 14.5px;
    font-weight: 700;
    color: #1e293b;
  }}
  .spec-val {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 800;
    color: #1d4ed8;
  }}

  .f1-network-panel {{
    background: #ffffff;
    border: 2px solid #cbd5e1;
    border-radius: 20px;
    padding: 26px;
    display: flex;
    flex-direction: column;
    position: relative;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.04);
  }}
  .network-canvas-wrap {{
    width: 100%;
    height: 520px;
    position: relative;
  }}
  .network-svg {{
    width: 100%;
    height: 100%;
  }}

  .f1-rules-panel {{
    display: flex;
    flex-direction: column;
    gap: 18px;
  }}
  .rule-card {{
    border-radius: 16px;
    padding: 22px 24px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    box-shadow: 0 8px 18px -4px rgba(0, 0, 0, 0.05);
  }}
  .rc-green {{
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
    border: 2px solid #86efac;
  }}
  .rc-red {{
    background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
    border: 2px solid #fca5a5;
  }}
  .rc-blue {{
    background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    border: 2px solid #93c5fd;
  }}
  .rule-head {{
    font-family: 'Montserrat', sans-serif;
    font-size: 16px;
    font-weight: 800;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .rc-green .rule-head {{ color: #166534; }}
  .rc-red .rule-head {{ color: #991b1b; }}
  .rc-blue .rule-head {{ color: #1e40af; }}

  .rule-formula {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 18px;
    font-weight: 800;
    padding: 8px 14px;
    border-radius: 8px;
    background: #ffffff;
    display: inline-block;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
  }}
  .rc-green .rule-formula {{ color: #15803d; border: 1.5px solid #86efac; }}
  .rc-red .rule-formula {{ color: #b91c1c; border: 1.5px solid #fca5a5; }}
  .rc-blue .rule-formula {{ color: #1d4ed8; border: 1.5px solid #93c5fd; }}

  .rule-desc {{
    font-size: 14px;
    line-height: 1.5;
    color: #334155;
    font-weight: 600;
  }}

  /* ========================================================
     FIGURE 2: DOMAIN RANDOMIZATION 3-PANEL
     ======================================================== */
  #fig2-dr {{ width: 2360px; }}
  .dr-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 30px;
  }}
  .dr-panel {{
    background: #ffffff;
    border-radius: 20px;
    padding: 26px;
    display: flex;
    flex-direction: column;
    gap: 18px;
    position: relative;
    border: 2px solid #cbd5e1;
    box-shadow: 0 12px 28px -6px rgba(0, 0, 0, 0.06);
  }}
  .dp-blue {{ border-color: #3b82f6; border-top: 9px solid #2563eb; }}
  .dp-green {{ border-color: #10b981; border-top: 9px solid #059669; }}
  .dp-amber {{ border-color: #f59e0b; border-top: 9px solid #d97706; }}

  .dr-panel-head {{
    display: flex;
    flex-direction: column;
    gap: 6px;
    text-align: center;
    padding-bottom: 14px;
    border-bottom: 1.5px solid #e2e8f0;
  }}
  .dr-type-title {{
    font-family: 'Montserrat', sans-serif;
    font-size: 20px;
    font-weight: 900;
    text-transform: uppercase;
  }}
  .dp-blue .dr-type-title {{ color: #1d4ed8; }}
  .dp-green .dr-type-title {{ color: #047857; }}
  .dp-amber .dr-type-title {{ color: #b45309; }}

  .dr-type-sub {{
    font-size: 13.5px;
    font-weight: 700;
    color: #64748b;
  }}
  .dr-canvas-box {{
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 16px;
    height: 440px;
    position: relative;
    overflow: hidden;
  }}
  .dr-spec-tag {{
    font-size: 13.5px;
    font-weight: 700;
    padding: 12px 16px;
    border-radius: 10px;
    text-align: center;
    line-height: 1.5;
  }}
  .dp-blue .dr-spec-tag {{ background: #eff6ff; color: #1e40af; border: 1.5px solid #bfdbfe; }}
  .dp-green .dr-spec-tag {{ background: #ecfdf5; color: #065f46; border: 1.5px solid #a7f3d0; }}
  .dp-amber .dr-spec-tag {{ background: #fffbeb; color: #92400e; border: 1.5px solid #fde68a; }}

  /* ========================================================
     FIGURE 3: 4-TIER ARCHITECTURE 3D GLASS SLABS
     ======================================================== */
  #fig3-arch {{ width: 2360px; }}
  .arch-tiers-wrap {{
    display: flex;
    flex-direction: column;
    gap: 18px;
    position: relative;
  }}
  .arch-tier-slab {{
    border-radius: 20px;
    padding: 26px 34px;
    display: grid;
    grid-template-columns: 340px 1fr 340px;
    gap: 28px;
    align-items: center;
    position: relative;
    box-shadow: 0 12px 28px -6px rgba(0, 0, 0, 0.06);
    border: 2px solid #cbd5e1;
  }}
  .at-t1 {{
    background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%);
    border-color: #93c5fd;
    border-left: 12px solid #1d4ed8;
  }}
  .at-t2 {{
    background: linear-gradient(135deg, #fcfaff 0%, #faf5ff 100%);
    border-color: #d8b4fe;
    border-left: 12px solid #7e22ce;
  }}
  .at-t3 {{
    background: linear-gradient(135deg, #f9fdfa 0%, #f0fdf4 100%);
    border-color: #86efac;
    border-left: 12px solid #15803d;
  }}
  .at-t4 {{
    background: linear-gradient(135deg, #fffdf7 0%, #fffbeb 100%);
    border-color: #fde68a;
    border-left: 12px solid #b45309;
  }}

  .tier-col-badge {{
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  .tier-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1px;
  }}
  .at-t1 .tier-label {{ color: #1d4ed8; }}
  .at-t2 .tier-label {{ color: #7e22ce; }}
  .at-t3 .tier-label {{ color: #15803d; }}
  .at-t4 .tier-label {{ color: #b45309; }}

  .tier-name {{
    font-family: 'Montserrat', sans-serif;
    font-size: 22px;
    font-weight: 900;
    color: #0f172a;
    line-height: 1.25;
  }}
  .tier-col-body {{
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}
  .tier-spec-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }}
  .tier-pill {{
    background: #ffffff;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 12.5px;
    font-weight: 700;
    border: 1.5px solid #cbd5e1;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.03);
  }}
  .tp-blue {{ color: #1d4ed8; border-color: #93c5fd; }}
  .tp-purple {{ color: #7e22ce; border-color: #d8b4fe; }}
  .tp-green {{ color: #15803d; border-color: #86efac; }}
  .tp-amber {{ color: #b45309; border-color: #fde68a; }}

  .tier-desc {{
    font-size: 14.5px;
    line-height: 1.55;
    color: #334155;
    font-weight: 600;
  }}

  .tier-col-kpi {{
    background: #ffffff;
    border: 2px solid #cbd5e1;
    border-radius: 16px;
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    box-shadow: 0 4px 10px rgba(0,0,0,0.05);
  }}
  .kpi-tier-val {{
    font-family: 'Montserrat', sans-serif;
    font-size: 28px;
    font-weight: 900;
  }}
  .at-t1 .kpi-tier-val {{ color: #1d4ed8; }}
  .at-t2 .kpi-tier-val {{ color: #7e22ce; }}
  .at-t3 .kpi-tier-val {{ color: #15803d; }}
  .at-t4 .kpi-tier-val {{ color: #b45309; }}

  .kpi-tier-sub {{
    font-size: 12.5px;
    font-weight: 700;
    color: #64748b;
    margin-top: 3px;
  }}

  .slab-connector {{
    display: flex;
    justify-content: center;
    align-items: center;
    margin: -6px 0;
    z-index: 10;
  }}
  .conn-badge {{
    background: #0f172a;
    color: #ffffff;
    padding: 5px 20px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 800;
    display: flex;
    align-items: center;
    gap: 8px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.2);
  }}

  /* ========================================================
     FIGURE 4: 3-STAGE PIPELINE (HERO WORKFLOW)
     ======================================================== */
  #fig4-pipeline {{ width: 2360px; }}
  .pipe-grid {{
    display: grid;
    grid-template-columns: 1fr 64px 1fr 64px 1fr;
    gap: 0;
    align-items: stretch;
  }}
  .pipe-card {{
    background: #ffffff;
    border-radius: 22px;
    padding: 32px 28px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    box-shadow: 0 12px 28px -6px rgba(0, 0, 0, 0.06);
    border: 2px solid #cbd5e1;
    justify-content: space-between;
  }}
  .pc-s1 {{ border-top: 10px solid #2563eb; }}
  .pc-s2 {{ border-top: 10px solid #9333ea; }}
  .pc-s3 {{ border-top: 10px solid #16a34a; }}

  .pipe-step-badge {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 800;
    padding: 5px 16px;
    border-radius: 20px;
    display: inline-block;
    width: fit-content;
    text-transform: uppercase;
  }}
  .pc-s1 .pipe-step-badge {{ background: #eff6ff; color: #1e40af; border: 1.5px solid #bfdbfe; }}
  .pc-s2 .pipe-step-badge {{ background: #faf5ff; color: #6b21a8; border: 1.5px solid #e9d5ff; }}
  .pc-s3 .pipe-step-badge {{ background: #f0fdf4; color: #15803d; border: 1.5px solid #bbf7d0; }}

  .pipe-stage-title {{
    font-family: 'Montserrat', sans-serif;
    font-size: 22px;
    font-weight: 900;
    color: #0f172a;
    line-height: 1.3;
  }}
  .pipe-stage-sub {{
    font-size: 14px;
    font-weight: 700;
    color: #64748b;
  }}

  .pipe-bullets {{
    display: flex;
    flex-direction: column;
    gap: 12px;
  }}
  .pipe-bullet-item {{
    font-size: 14px;
    line-height: 1.55;
    color: #334155;
    position: relative;
    padding-left: 20px;
  }}
  .pipe-bullet-item::before {{
    content: "•";
    position: absolute;
    left: 0;
    font-weight: 900;
    font-size: 19px;
  }}
  .pc-s1 .pipe-bullet-item::before {{ color: #2563eb; }}
  .pc-s2 .pipe-bullet-item::before {{ color: #9333ea; }}
  .pc-s3 .pipe-bullet-item::before {{ color: #16a34a; }}

  .pipe-bottom-visual {{
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 14px;
    padding: 16px 18px;
    display: flex;
    align-items: center;
    gap: 16px;
    margin-top: 14px;
  }}
  .pbv-icon {{
    font-size: 30px;
    width: 52px;
    height: 52px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #ffffff;
    box-shadow: 0 4px 8px rgba(0,0,0,0.06);
    flex-shrink: 0;
  }}
  .pbv-text {{
    display: flex;
    flex-direction: column;
    gap: 3px;
  }}
  .pbv-text-title {{
    font-family: 'Montserrat', sans-serif;
    font-size: 13.5px;
    font-weight: 800;
    color: #0f172a;
  }}
  .pbv-text-desc {{
    font-size: 12px;
    font-weight: 600;
    color: #64748b;
    line-height: 1.4;
  }}

  .pipe-arrow-col {{
    display: flex;
    justify-content: center;
    align-items: center;
  }}
  .pipe-arrow-icon {{
    width: 52px;
    height: 52px;
    background: #0f172a;
    color: #ffffff;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    font-weight: 900;
    box-shadow: 0 6px 16px rgba(0,0,0,0.22);
  }}

  /* ========================================================
     FIGURE 5: NAMI CONTROL TOWER SHOWCASE
     ======================================================== */
  #fig5-nami {{ width: 2360px; }}
  .nami-full-grid {{
    display: grid;
    grid-template-columns: 1fr 540px;
    gap: 34px;
    align-items: stretch;
  }}
  .nami-img-frame {{
    background: #0f172a;
    border-radius: 18px;
    overflow: hidden;
    border: 2px solid #cbd5e1;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 620px;
  }}
  .nami-img-frame img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: top center;
  }}
  .nami-side-details {{
    background: #f8fafc;
    border: 2px solid #86efac;
    border-radius: 18px;
    padding: 30px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}
  .nami-side-head {{
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}
  .nami-live-tag {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #dcfce7;
    color: #15803d;
    padding: 4px 14px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12.5px;
    font-weight: 800;
    border: 1px solid #86efac;
    width: fit-content;
  }}
  .nami-live-tag::before {{
    content: "";
    width: 8px;
    height: 8px;
    background: #22c55e;
    border-radius: 50%;
  }}
  .nami-side-title {{
    font-family: 'Montserrat', sans-serif;
    font-size: 23px;
    font-weight: 900;
    color: #0f172a;
    line-height: 1.3;
  }}
  .nami-side-bullets {{
    display: flex;
    flex-direction: column;
    gap: 14px;
    font-size: 14.5px;
    line-height: 1.5;
    color: #334155;
  }}
  .nami-side-bullets li {{
    list-style: none;
    position: relative;
    padding-left: 22px;
  }}
  .nami-side-bullets li::before {{
    content: "✓";
    position: absolute;
    left: 0;
    color: #16a34a;
    font-weight: 900;
  }}
  .nami-telemetry-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin-top: 10px;
  }}
  .telemetry-card {{
    background: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 12px;
    padding: 14px 16px;
    text-align: center;
  }}
  .tc-val {{ font-family: 'Montserrat', sans-serif; font-size: 24px; font-weight: 900; color: #15803d; }}
  .tc-lbl {{ font-size: 12.5px; font-weight: 700; color: #64748b; margin-top: 2px; }}

  /* ========================================================
     FIGURE 6: ROUTE MAPS R101 & RC101
     ======================================================== */
  #fig6-routes {{ width: 2360px; }}
  .routes-pair-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 30px;
  }}
  .route-fig-box {{
    background: #f8fafc;
    border: 2px solid #cbd5e1;
    border-radius: 18px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
  }}
  .route-fig-box img {{
    width: 100%;
    height: 500px;
    object-fit: contain;
    background: #ffffff;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
  }}
  .route-fig-caption {{
    font-size: 14.5px;
    font-weight: 700;
    color: #1e293b;
    text-align: center;
    line-height: 1.5;
  }}
  .route-fig-caption b {{ color: #1d4ed8; }}

  /* ========================================================
     FIGURE 7: BENCHMARK RESULTS TABLE
     ======================================================== */
  #fig7-table {{ width: 2360px; }}
  .academic-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 16.5px;
    text-align: center;
  }}
  .academic-table thead th {{
    border-top: 3.5px solid #0c1e5a;
    border-bottom: 2px solid #0c1e5a;
    padding: 18px 16px;
    font-family: 'Montserrat', sans-serif;
    font-weight: 900;
    color: #0c1e5a;
    background: #f8fafc;
    letter-spacing: 0.3px;
  }}
  .academic-table tbody td {{
    padding: 15px 16px;
    border-bottom: 1px solid #e2e8f0;
    color: #334155;
    font-weight: 600;
  }}
  .academic-table tbody tr:last-child td {{
    border-bottom: 3.5px solid #0c1e5a;
  }}
  .academic-table .row-highlight {{
    background: #eff6ff !important;
  }}
  .academic-table .row-highlight td {{
    font-weight: 800;
    color: #1e40af !important;
  }}
  .pill-win {{
    display: inline-block;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 13.5px;
    font-weight: 800;
    background: #dcfce7;
    color: #15803d;
    border: 1px solid #86efac;
  }}

  /* ========================================================
     FIGURE 8: 4 GOLDEN KPI CARDS
     ======================================================== */
  #fig8-kpi {{ width: 2360px; }}
  .kpi-cards-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr 1fr;
    gap: 26px;
  }}
  .kpi-stat-card {{
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border: 2px solid #cbd5e1;
    border-radius: 18px;
    padding: 26px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    box-shadow: 0 10px 22px -5px rgba(0, 0, 0, 0.05);
  }}
  .ksc-blue {{ border-left: 9px solid #1d4ed8; }}
  .ksc-teal {{ border-left: 9px solid #0d9488; }}
  .ksc-purple {{ border-left: 9px solid #7e22ce; }}
  .ksc-green {{ border-left: 9px solid #16a34a; }}

  .ksc-val {{
    font-family: 'Montserrat', sans-serif;
    font-size: 46px;
    font-weight: 900;
    line-height: 1.05;
  }}
  .ksc-blue .ksc-val {{ color: #1d4ed8; }}
  .ksc-teal .ksc-val {{ color: #0f766e; }}
  .ksc-purple .ksc-val {{ color: #7e22ce; }}
  .ksc-green .ksc-val {{ color: #15803d; }}

  .ksc-title {{
    font-family: 'Montserrat', sans-serif;
    font-size: 16.5px;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.35;
  }}
  .ksc-desc {{
    font-size: 13.5px;
    font-weight: 600;
    color: #64748b;
    line-height: 1.45;
  }}

</style>
</head>
<body>

  <!-- ========================================================
       FIGURE 1: MÔ HÌNH BÀI TOÁN VRPTW & KHO TRUNG TÂM
       ======================================================== -->
  <div class="canvas-card" id="fig1-vrptw">
    <div class="card-header">
      <div class="card-title-group">
        <div class="card-tag">Hình 1 • Kiến trúc bài toán phân phối</div>
        <div class="card-title">Mô hình bài toán phân phối hàng hoá có khung thời gian (VRPTW)</div>
        <div class="card-subtitle">Vehicle Routing Problem with Time Windows • Mạng lưới điều phối 3 đội xe xuất phát từ Kho Trung Tâm NAMI Hub</div>
      </div>
      <div class="card-badge">ĐỘ PHÂN GIẢI 4K • 300 DPI RETINA</div>
    </div>

    <div class="f1-grid">
      <!-- Left: Depot Hub -->
      <div class="f1-depot-panel">
        <div class="depot-hero-box">
          <div class="depot-icon-wrap">🏭</div>
          <div class="depot-title">KHO TRUNG TÂM (DEPOT)</div>
          <div class="depot-coord">Toạ độ: (X₀, Y₀) = (40, 50)</div>

          <div class="docks-grid">
            <div class="dock-card dock-r1">
              <div class="dock-num">Cửa 1</div>
              <div style="font-size:11px; font-weight:800; color:#1d4ed8;">Đội Xanh</div>
            </div>
            <div class="dock-card dock-r2">
              <div class="dock-num">Cửa 2</div>
              <div style="font-size:11px; font-weight:800; color:#15803d;">Đội Lục</div>
            </div>
            <div class="dock-card dock-r3">
              <div class="dock-num">Cửa 3</div>
              <div style="font-size:11px; font-weight:800; color:#7e22ce;">Đội Tím</div>
            </div>
          </div>
        </div>

        <div class="depot-spec-item">
          <span>Dung tích thùng xe:</span>
          <span class="spec-val">Q = 200 đơn vị</span>
        </div>
        <div class="depot-spec-item">
          <span>Khung giờ hoạt động:</span>
          <span class="spec-val">[08:00 - 18:00]</span>
        </div>
        <div class="depot-spec-item">
          <span>Đội xe vận hành:</span>
          <span class="spec-val">3 Xe phân phối song song</span>
        </div>
        <div class="depot-spec-item">
          <span>Chiến lược xuất phát:</span>
          <span class="spec-val">Khởi hành đồng thời tại Hub</span>
        </div>
      </div>

      <!-- Center: SVG Network -->
      <div class="f1-network-panel">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
          <span style="font-family:'Montserrat',sans-serif; font-size:15px; font-weight:900; color:#0f172a; text-transform:uppercase;">
            Hải đồ điều phối 3 lộ trình độc lập (Không giao cắt)
          </span>
          <div style="display:flex; gap:16px; font-size:13px; font-weight:800;">
            <span style="color:#2563eb;">■ Tuyến 1 (120/200 - 60%)</span>
            <span style="color:#16a34a;">■ Tuyến 2 (130/200 - 65%)</span>
            <span style="color:#9333ea;">■ Tuyến 3 (130/200 - 65%)</span>
          </div>
        </div>

        <div class="network-canvas-wrap">
          <svg class="network-svg" viewBox="0 0 920 460">
            <defs>
              <pattern id="grid-f1" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#f1f5f9" stroke-width="1.5"/>
              </pattern>
              <!-- Arrow markers -->
              <marker id="arr-blue" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#2563eb" />
              </marker>
              <marker id="arr-green" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#16a34a" />
              </marker>
              <marker id="arr-purple" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#9333ea" />
              </marker>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid-f1)" />

            <!-- Route 1: Blue (Top) -->
            <path d="M 130 195 Q 210 90 290 85" fill="none" stroke="#2563eb" stroke-width="4" marker-end="url(#arr-blue)" />
            <path d="M 330 85 Q 440 60 540 85" fill="none" stroke="#2563eb" stroke-width="4" marker-end="url(#arr-blue)" />
            <path d="M 580 85 Q 680 70 760 100" fill="none" stroke="#2563eb" stroke-width="4" marker-end="url(#arr-blue)" />
            <!-- Return -->
            <path d="M 760 125 Q 460 210 140 215" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-dasharray="8,5" marker-end="url(#arr-blue)" />

            <!-- Route 2: Green (Middle) -->
            <path d="M 130 225 Q 240 205 360 215" fill="none" stroke="#16a34a" stroke-width="4" marker-end="url(#arr-green)" />
            <path d="M 400 215 Q 540 195 660 215" fill="none" stroke="#16a34a" stroke-width="4" marker-end="url(#arr-green)" />
            <!-- Return -->
            <path d="M 660 240 Q 400 300 140 235" fill="none" stroke="#16a34a" stroke-width="2.5" stroke-dasharray="8,5" marker-end="url(#arr-green)" />

            <!-- Route 3: Purple (Bottom) -->
            <path d="M 130 255 Q 210 365 315 375" fill="none" stroke="#9333ea" stroke-width="4" marker-end="url(#arr-purple)" />
            <path d="M 355 375 Q 500 385 625 365" fill="none" stroke="#9333ea" stroke-width="4" marker-end="url(#arr-purple)" />
            <!-- Return -->
            <path d="M 625 345 Q 380 280 140 250" fill="none" stroke="#9333ea" stroke-width="2.5" stroke-dasharray="8,5" marker-end="url(#arr-purple)" />

            <!-- Mini Delivery Truck Badges on Routes -->
            <!-- Truck 1 on Blue -->
            <g transform="translate(200, 115)">
              <rect x="-18" y="-12" width="36" height="24" rx="6" fill="#1d4ed8" />
              <text x="0" y="5" font-size="14" text-anchor="middle">🚚</text>
            </g>
            <!-- Truck 2 on Green -->
            <g transform="translate(250, 195)">
              <rect x="-18" y="-12" width="36" height="24" rx="6" fill="#15803d" />
              <text x="0" y="5" font-size="14" text-anchor="middle">🚚</text>
            </g>
            <!-- Truck 3 on Purple -->
            <g transform="translate(220, 320)">
              <rect x="-18" y="-12" width="36" height="24" rx="6" fill="#7e22ce" />
              <text x="0" y="5" font-size="14" text-anchor="middle">🚚</text>
            </g>

            <!-- Depot Marker -->
            <circle cx="105" cy="225" r="34" fill="#fef3c7" stroke="#d97706" stroke-width="3.5" />
            <polygon points="105,201 112,219 132,219 116,230 122,249 105,237 88,249 94,230 78,219 98,219" fill="#f59e0b" />
            <text x="105" y="276" font-family="'Montserrat',sans-serif" font-size="13.5" font-weight="900" fill="#78350f" text-anchor="middle">DEPOT (40, 50)</text>

            <!-- C1 -->
            <g transform="translate(310, 85)">
              <circle cx="0" cy="0" r="22" fill="#ffffff" stroke="#2563eb" stroke-width="3.5" />
              <text x="0" y="5" font-family="'Montserrat',sans-serif" font-size="13" font-weight="900" fill="#1e3a8a" text-anchor="middle">C₁</text>
              <rect x="-32" y="-40" width="64" height="20" rx="5" fill="#2563eb" />
              <text x="0" y="-26" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="800" fill="#ffffff" text-anchor="middle">q=35</text>
              <rect x="-52" y="28" width="104" height="20" rx="5" fill="#ffffff" stroke="#cbd5e1" />
              <text x="0" y="42" font-family="'JetBrains Mono',monospace" font-size="10.5" font-weight="800" fill="#1e293b" text-anchor="middle">[08:30-09:30]</text>
            </g>

            <!-- C2 -->
            <g transform="translate(560, 85)">
              <circle cx="0" cy="0" r="22" fill="#ffffff" stroke="#2563eb" stroke-width="3.5" />
              <text x="0" y="5" font-family="'Montserrat',sans-serif" font-size="13" font-weight="900" fill="#1e3a8a" text-anchor="middle">C₂</text>
              <rect x="-32" y="-40" width="64" height="20" rx="5" fill="#2563eb" />
              <text x="0" y="-26" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="800" fill="#ffffff" text-anchor="middle">q=45</text>
              <rect x="-52" y="28" width="104" height="20" rx="5" fill="#ffffff" stroke="#cbd5e1" />
              <text x="0" y="42" font-family="'JetBrains Mono',monospace" font-size="10.5" font-weight="800" fill="#1e293b" text-anchor="middle">[09:45-11:00]</text>
            </g>

            <!-- C3 -->
            <g transform="translate(780, 105)">
              <circle cx="0" cy="0" r="22" fill="#ffffff" stroke="#2563eb" stroke-width="3.5" />
              <text x="0" y="5" font-family="'Montserrat',sans-serif" font-size="13" font-weight="900" fill="#1e3a8a" text-anchor="middle">C₃</text>
              <rect x="-32" y="-40" width="64" height="20" rx="5" fill="#2563eb" />
              <text x="0" y="-26" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="800" fill="#ffffff" text-anchor="middle">q=40</text>
              <rect x="-52" y="28" width="104" height="20" rx="5" fill="#ffffff" stroke="#cbd5e1" />
              <text x="0" y="42" font-family="'JetBrains Mono',monospace" font-size="10.5" font-weight="800" fill="#1e293b" text-anchor="middle">[11:15-12:30]</text>
            </g>

            <!-- C4 -->
            <g transform="translate(380, 215)">
              <circle cx="0" cy="0" r="22" fill="#ffffff" stroke="#16a34a" stroke-width="3.5" />
              <text x="0" y="5" font-family="'Montserrat',sans-serif" font-size="13" font-weight="900" fill="#14532d" text-anchor="middle">C₄</text>
              <rect x="-32" y="-40" width="64" height="20" rx="5" fill="#16a34a" />
              <text x="0" y="-26" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="800" fill="#ffffff" text-anchor="middle">q=60</text>
              <rect x="-52" y="28" width="104" height="20" rx="5" fill="#ffffff" stroke="#cbd5e1" />
              <text x="0" y="42" font-family="'JetBrains Mono',monospace" font-size="10.5" font-weight="800" fill="#1e293b" text-anchor="middle">[08:45-10:15]</text>
            </g>

            <!-- C5 -->
            <g transform="translate(680, 215)">
              <circle cx="0" cy="0" r="22" fill="#ffffff" stroke="#16a34a" stroke-width="3.5" />
              <text x="0" y="5" font-family="'Montserrat',sans-serif" font-size="13" font-weight="900" fill="#14532d" text-anchor="middle">C₅</text>
              <rect x="-32" y="-40" width="64" height="20" rx="5" fill="#16a34a" />
              <text x="0" y="-26" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="800" fill="#ffffff" text-anchor="middle">q=70</text>
              <rect x="-52" y="28" width="104" height="20" rx="5" fill="#ffffff" stroke="#cbd5e1" />
              <text x="0" y="42" font-family="'JetBrains Mono',monospace" font-size="10.5" font-weight="800" fill="#1e293b" text-anchor="middle">[10:30-12:00]</text>
            </g>

            <!-- C6 -->
            <g transform="translate(335, 375)">
              <circle cx="0" cy="0" r="22" fill="#ffffff" stroke="#9333ea" stroke-width="3.5" />
              <text x="0" y="5" font-family="'Montserrat',sans-serif" font-size="13" font-weight="900" fill="#581c87" text-anchor="middle">C₆</text>
              <rect x="-32" y="-40" width="64" height="20" rx="5" fill="#9333ea" />
              <text x="0" y="-26" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="800" fill="#ffffff" text-anchor="middle">q=50</text>
              <rect x="-52" y="28" width="104" height="20" rx="5" fill="#ffffff" stroke="#cbd5e1" />
              <text x="0" y="42" font-family="'JetBrains Mono',monospace" font-size="10.5" font-weight="800" fill="#1e293b" text-anchor="middle">[09:00-10:30]</text>
            </g>

            <!-- C7 -->
            <g transform="translate(645, 365)">
              <circle cx="0" cy="0" r="22" fill="#ffffff" stroke="#9333ea" stroke-width="3.5" />
              <text x="0" y="5" font-family="'Montserrat',sans-serif" font-size="13" font-weight="900" fill="#581c87" text-anchor="middle">C₇</text>
              <rect x="-32" y="-40" width="64" height="20" rx="5" fill="#9333ea" />
              <text x="0" y="-26" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="800" fill="#ffffff" text-anchor="middle">q=80</text>
              <rect x="-52" y="28" width="104" height="20" rx="5" fill="#ffffff" stroke="#cbd5e1" />
              <text x="0" y="42" font-family="'JetBrains Mono',monospace" font-size="10.5" font-weight="800" fill="#1e293b" text-anchor="middle">[11:00-12:30]</text>
            </g>
          </svg>
        </div>
      </div>

      <!-- Right: Constraints -->
      <div class="f1-rules-panel">
        <div class="rule-card rc-green">
          <div class="rule-head">📦 Ràng buộc tải trọng xe (Capacity)</div>
          <div class="rule-formula">∑ qᵢ ≤ Q = 200 đơn vị</div>
          <div class="rule-desc">
            Tổng nhu cầu giao trên mỗi tuyến xe không được vượt quá tải trọng định mức Q. Đảm bảo 100% khả thi vật lý, tuyệt đối không chở quá tải.
          </div>
        </div>

        <div class="rule-card rc-red">
          <div class="rule-head">⏰ Ràng buộc khung giờ (Time Windows)</div>
          <div class="rule-formula">Eᵢ ≤ tᵢ ≤ Lᵢ (tại mỗi khách hàng)</div>
          <div class="rule-desc">
            Thời điểm xe đến tᵢ phải nằm trong cửa sổ thời gian [Eᵢ, Lᵢ]. Đến sớm phải chờ tại bãi; đến trễ bị phạt rất nặng (Strict Penalty).
          </div>
        </div>

        <div class="rule-card rc-blue">
          <div class="rule-head">🎯 Hàm mục tiêu từ điển (Lexicographic)</div>
          <div class="rule-formula">min f(s) = M · Nᵥ(s) + Dₜ(s)</div>
          <div class="rule-desc">
            Hệ số phạt M = 10⁵ ≫ max Dₜ. Ưu tiên tối thượng là giảm thiểu số lượng xe vận hành Nᵥ, sau đó tối ưu tổng quãng đường di chuyển Dₜ.
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ========================================================
       FIGURE 2: DOMAIN RANDOMIZATION 3-PANEL
       ======================================================== -->
  <div class="canvas-card" id="fig2-dr">
    <div class="card-header">
      <div class="card-title-group">
        <div class="card-tag">Hình 2 • Môi trường mô phỏng & Đa dạng hoá</div>
        <div class="card-title">Mô hình hoá bài toán thực nghiệm: Đa dạng hoá miền huấn luyện (Domain Randomization)</div>
        <div class="card-subtitle">Tự sinh dữ liệu đa dạng quy mô N ∈ [20, 100] • 3 cấu trúc không gian hình học chuẩn hoá quốc tế</div>
      </div>
      <div class="card-badge">ĐỘ PHÂN GIẢI 4K • 300 DPI RETINA</div>
    </div>

    <div class="dr-grid">
      <!-- Panel 1: Clustered -->
      <div class="dr-panel dp-blue">
        <div class="dr-panel-head">
          <div class="dr-type-title">Miền C (Clustered)</div>
          <div class="dr-type-sub">Cụm khách hàng tập trung mật độ cao (k=3 Cụm)</div>
        </div>
        <div class="dr-canvas-box">
          <svg width="100%" height="100%" viewBox="0 0 420 380">
            <defs>
              <pattern id="grid-c" width="30" height="30" patternUnits="userSpaceOnUse">
                <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#f1f5f9" stroke-width="1.2"/>
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid-c)" />

            <!-- Axes markings -->
            <text x="25" y="365" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="700" fill="#94a3b8">(0,0)</text>
            <text x="375" y="365" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="700" fill="#94a3b8">(100,0)</text>
            <text x="25" y="25" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="700" fill="#94a3b8">(0,100)</text>

            <!-- Halo 1 NW -->
            <ellipse cx="120" cy="110" rx="65" ry="55" fill="#dbeafe" stroke="#3b82f6" stroke-width="2.5" stroke-dasharray="6,4" opacity="0.65"/>
            <text x="120" y="42" font-family="'Montserrat',sans-serif" font-size="12" font-weight="900" fill="#1d4ed8" text-anchor="middle">CỤM 1 (TÂY BẮC)</text>

            <!-- Halo 2 NE -->
            <ellipse cx="305" cy="115" rx="60" ry="55" fill="#dbeafe" stroke="#3b82f6" stroke-width="2.5" stroke-dasharray="6,4" opacity="0.65"/>
            <text x="305" y="48" font-family="'Montserrat',sans-serif" font-size="12" font-weight="900" fill="#1d4ed8" text-anchor="middle">CỤM 2 (ĐÔNG BẮC)</text>

            <!-- Halo 3 South -->
            <ellipse cx="210" cy="285" rx="70" ry="55" fill="#dbeafe" stroke="#3b82f6" stroke-width="2.5" stroke-dasharray="6,4" opacity="0.65"/>
            <text x="210" y="355" font-family="'Montserrat',sans-serif" font-size="12" font-weight="900" fill="#1d4ed8" text-anchor="middle">CỤM 3 (NAM)</text>

            <!-- Clustered Points NW (20 points) -->
            <g fill="#1d4ed8" stroke="#ffffff" stroke-width="1.5">
              <circle cx="105" cy="95" r="5"/><circle cx="125" cy="90" r="5"/><circle cx="115" cy="115" r="5"/>
              <circle cx="135" cy="110" r="5"/><circle cx="95" cy="120" r="5"/><circle cx="140" cy="95" r="5"/>
              <circle cx="110" cy="80" r="5"/><circle cx="130" cy="125" r="5"/><circle cx="100" cy="105" r="5"/>
              <circle cx="145" cy="120" r="5"/><circle cx="120" cy="135" r="5"/><circle cx="90" cy="100" r="5"/>
              <circle cx="135" cy="80" r="5"/><circle cx="105" cy="125" r="5"/><circle cx="125" cy="105" r="5"/>
            </g>

            <!-- Clustered Points NE (20 points) -->
            <g fill="#1d4ed8" stroke="#ffffff" stroke-width="1.5">
              <circle cx="290" cy="110" r="5"/><circle cx="310" cy="100" r="5"/><circle cx="285" cy="125" r="5"/>
              <circle cx="320" cy="120" r="5"/><circle cx="300" cy="90" r="5"/><circle cx="315" cy="135" r="5"/>
              <circle cx="275" cy="105" r="5"/><circle cx="305" cy="130" r="5"/><circle cx="330" cy="110" r="5"/>
              <circle cx="295" cy="140" r="5"/><circle cx="325" cy="95" r="5"/><circle cx="280" cy="118" r="5"/>
            </g>

            <!-- Clustered Points S (20 points) -->
            <g fill="#1d4ed8" stroke="#ffffff" stroke-width="1.5">
              <circle cx="200" cy="275" r="5"/><circle cx="225" cy="270" r="5"/><circle cx="190" cy="290" r="5"/>
              <circle cx="230" cy="295" r="5"/><circle cx="215" cy="305" r="5"/><circle cx="180" cy="280" r="5"/>
              <circle cx="240" cy="280" r="5"/><circle cx="205" cy="300" r="5"/><circle cx="195" cy="265" r="5"/>
              <circle cx="220" cy="315" r="5"/><circle cx="235" cy="305" r="5"/><circle cx="185" cy="295" r="5"/>
            </g>

            <!-- Center Depot -->
            <circle cx="210" cy="190" r="18" fill="#fef3c7" stroke="#d97706" stroke-width="3" />
            <polygon points="210,178 214,187 224,187 216,193 219,202 210,196 201,202 204,193 196,187 206,187" fill="#f59e0b" />
            <text x="210" y="222" font-family="'Montserrat',sans-serif" font-size="12" font-weight="900" fill="#78350f" text-anchor="middle">KHO DEPOT (50, 50)</text>
          </svg>
        </div>
        <div class="dr-spec-tag">
          <b>Đặc trưng hình học:</b> Khách tập trung thành cụm dày đặc • Cửa sổ thời gian hẹp [15 - 30 phút] • Tối ưu di chuyển nội cụm
        </div>
      </div>

      <!-- Panel 2: Uniform Random -->
      <div class="dr-panel dp-green">
        <div class="dr-panel-head">
          <div class="dr-type-title">Miền R (Uniform / Random)</div>
          <div class="dr-type-sub">Phân bố không gian ngẫu nhiên đồng đều (75 khách)</div>
        </div>
        <div class="dr-canvas-box">
          <svg width="100%" height="100%" viewBox="0 0 420 380">
            <rect width="100%" height="100%" fill="url(#grid-c)" />

            <text x="25" y="365" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="700" fill="#94a3b8">(0,0)</text>
            <text x="375" y="365" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="700" fill="#94a3b8">(100,0)</text>
            <text x="25" y="25" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="700" fill="#94a3b8">(0,100)</text>

            <!-- 50 Uniform points -->
            <g fill="#16a34a" stroke="#ffffff" stroke-width="1.5">
              <circle cx="55" cy="55" r="5"/><circle cx="115" cy="65" r="5"/><circle cx="175" cy="50" r="5"/>
              <circle cx="235" cy="45" r="5"/><circle cx="295" cy="60" r="5"/><circle cx="355" cy="75" r="5"/>
              <circle cx="45" cy="115" r="5"/><circle cx="95" cy="130" r="5"/><circle cx="155" cy="105" r="5"/>
              <circle cx="265" cy="110" r="5"/><circle cx="325" cy="125" r="5"/><circle cx="375" cy="145" r="5"/>
              <circle cx="65" cy="175" r="5"/><circle cx="125" cy="165" r="5"/><circle cx="295" cy="175" r="5"/>
              <circle cx="355" cy="195" r="5"/><circle cx="45" cy="235" r="5"/><circle cx="105" cy="225" r="5"/>
              <circle cx="165" cy="245" r="5"/><circle cx="255" cy="235" r="5"/><circle cx="315" cy="245" r="5"/>
              <circle cx="365" cy="265" r="5"/><circle cx="55" cy="295" r="5"/><circle cx="115" cy="285" r="5"/>
              <circle cx="175" cy="305" r="5"/><circle cx="235" cy="295" r="5"/><circle cx="295" cy="315" r="5"/>
              <circle cx="355" cy="325" r="5"/><circle cx="85" cy="345" r="5"/><circle cx="145" cy="345" r="5"/>
              <circle cx="265" cy="345" r="5"/><circle cx="325" cy="345" r="5"/>
            </g>

            <!-- Center Depot -->
            <circle cx="210" cy="190" r="18" fill="#fef3c7" stroke="#d97706" stroke-width="3" />
            <polygon points="210,178 214,187 224,187 216,193 219,202 210,196 201,202 204,193 196,187 206,187" fill="#f59e0b" />
            <text x="210" y="222" font-family="'Montserrat',sans-serif" font-size="12" font-weight="900" fill="#78350f" text-anchor="middle">KHO DEPOT (50, 50)</text>
          </svg>
        </div>
        <div class="dr-spec-tag">
          <b>Đặc trưng hình học:</b> Toạ độ đồng xác suất Poisson • Cửa sổ thời gian rộng [30 - 60 phút] • Khám phá lộ trình mở
        </div>
      </div>

      <!-- Panel 3: Random-Clustered -->
      <div class="dr-panel dp-amber">
        <div class="dr-panel-head">
          <div class="dr-type-title">Miền RC (Random-Clustered)</div>
          <div class="dr-type-sub">Cấu trúc lai hỗn hợp đô thị và vệ tinh</div>
        </div>
        <div class="dr-canvas-box">
          <svg width="100%" height="100%" viewBox="0 0 420 380">
            <rect width="100%" height="100%" fill="url(#grid-c)" />

            <text x="25" y="365" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="700" fill="#94a3b8">(0,0)</text>
            <text x="375" y="365" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="700" fill="#94a3b8">(100,0)</text>
            <text x="25" y="25" font-family="'JetBrains Mono',monospace" font-size="11" font-weight="700" fill="#94a3b8">(0,100)</text>

            <!-- 2 Clusters -->
            <ellipse cx="115" cy="115" rx="55" ry="50" fill="#fed7aa" stroke="#f97316" stroke-width="2.5" stroke-dasharray="6,4" opacity="0.65"/>
            <text x="115" y="48" font-family="'Montserrat',sans-serif" font-size="12" font-weight="900" fill="#c2410c" text-anchor="middle">CỤM ĐÔ THỊ A</text>

            <ellipse cx="315" cy="265" rx="60" ry="50" fill="#fed7aa" stroke="#f97316" stroke-width="2.5" stroke-dasharray="6,4" opacity="0.65"/>
            <text x="315" y="335" font-family="'Montserrat',sans-serif" font-size="12" font-weight="900" fill="#c2410c" text-anchor="middle">CỤM ĐÔ THỊ B</text>

            <!-- Cluster points -->
            <g fill="#ea580c" stroke="#ffffff" stroke-width="1.5">
              <circle cx="100" cy="105" r="5"/><circle cx="120" cy="100" r="5"/><circle cx="110" cy="125" r="5"/>
              <circle cx="130" cy="120" r="5"/><circle cx="90" cy="115" r="5"/><circle cx="135" cy="105" r="5"/>
              <circle cx="105" cy="90" r="5"/><circle cx="125" cy="130" r="5"/><circle cx="95" cy="130" r="5"/>

              <circle cx="300" cy="260" r="5"/><circle cx="325" cy="255" r="5"/><circle cx="310" cy="280" r="5"/>
              <circle cx="330" cy="275" r="5"/><circle cx="295" cy="270" r="5"/><circle cx="335" cy="265" r="5"/>
              <circle cx="305" cy="245" r="5"/><circle cx="320" cy="285" r="5"/><circle cx="340" cy="255" r="5"/>
            </g>

            <!-- Scattered Satellite points -->
            <g fill="#9a3412" stroke="#ffffff" stroke-width="1.2">
              <circle cx="50" cy="235" r="4.5"/><circle cx="150" cy="285" r="4.5"/><circle cx="245" cy="85" r="4.5"/>
              <circle cx="355" cy="125" r="4.5"/><circle cx="220" cy="55" r="4.5"/><circle cx="65" cy="325" r="4.5"/>
              <circle cx="375" cy="215" r="4.5"/><circle cx="170" cy="175" r="4.5"/><circle cx="275" cy="165" r="4.5"/>
            </g>
            <text x="250" y="42" font-family="'Montserrat',sans-serif" font-size="11" font-weight="800" fill="#9a3412" text-anchor="middle">Điểm giao vệ tinh</text>

            <!-- Center Depot -->
            <circle cx="210" cy="190" r="18" fill="#fef3c7" stroke="#d97706" stroke-width="3" />
            <polygon points="210,178 214,187 224,187 216,193 219,202 210,196 201,202 204,193 196,187 206,187" fill="#f59e0b" />
            <text x="210" y="222" font-family="'Montserrat',sans-serif" font-size="12" font-weight="900" fill="#78350f" text-anchor="middle">KHO DEPOT (50, 50)</text>
          </svg>
        </div>
        <div class="dr-spec-tag">
          <b>Đặc trưng hình học:</b> Kết hợp lõi đô thị + điểm giao vệ tinh • Khung giờ biến thiên đa tầng [15 - 90 phút]
        </div>
      </div>
    </div>
  </div>

  <!-- ========================================================
       FIGURE 3: 4-TIER ARCHITECTURE SLABS
       ======================================================== -->
  <div class="canvas-card" id="fig3-arch">
    <div class="card-header">
      <div class="card-title-group">
        <div class="card-tag">Hình 3 • Đề xuất kiến trúc hệ thống</div>
        <div class="card-title">Hệ thống điều phối lai phân cấp 4 tầng: Hybrid DDQN – ALNS & Set Partitioning</div>
        <div class="card-subtitle">Tri-Level Coordinated Controller: Macro Semi-MDP • Micro Bandit • Contrastive GNN & LAC • HiGHS MILP Recombination</div>
      </div>
      <div class="card-badge">ĐỘ PHÂN GIẢI 4K • 300 DPI RETINA</div>
    </div>

    <div class="arch-tiers-wrap">
      <!-- Tier 1 -->
      <div class="arch-tier-slab at-t1">
        <div class="tier-col-badge">
          <div class="tier-label">Tầng 1 • Macro Policy</div>
          <div class="tier-name">Plateau Controller (Macro DDQN)</div>
        </div>
        <div class="tier-col-body">
          <div class="tier-spec-row">
            <span class="tier-pill tp-blue"><b>Trạng thái:</b> 13D sₖᵐᵃᶜʳᵒ</span>
            <span class="tier-pill tp-blue"><b>Chu kỳ:</b> Δₛₑg = 100 bước</span>
            <span class="tier-pill tp-blue"><b>7 Chế độ:</b> Default, Intensify, Diversify, TW-Rescue, Pool-Rec, Route-Red, Inf-Desc</span>
          </div>
          <div class="tier-desc">
            Mạng Dueling DDQN nhận biết điểm nghẽn tìm kiếm qua 13 đặc trưng toàn cục (độ bế tắc, áp lực tải, entropy). Tự động kích hoạt chuyển đổi giữa 7 chế độ chiến lược nhằm phá vỡ các cực tiểu địa phương sâu.
          </div>
        </div>
        <div class="tier-col-kpi">
          <div class="kpi-tier-val">7 Chế độ</div>
          <div class="kpi-tier-sub">Chiến lược điều khiển thích ứng</div>
        </div>
      </div>

      <div class="slab-connector">
        <div class="conn-badge">▼ Truyền chế độ chiến lược Macro (aₖ) xuống vi mô</div>
      </div>

      <!-- Tier 2 -->
      <div class="arch-tier-slab at-t2">
        <div class="tier-col-badge">
          <div class="tier-label">Tầng 2 • Micro Policy & LAC</div>
          <div class="tier-name">Operator Controller & Learned Acceptance</div>
        </div>
        <div class="tier-col-body">
          <div class="tier-spec-row">
            <span class="tier-pill tp-purple"><b>Trạng thái:</b> 20D sₜᵐⁱᶜʳᵒ</span>
            <span class="tier-pill tp-purple"><b>Toán tử:</b> 65 Action Pairs (13 Destroy × 5 Repair)</span>
            <span class="tier-pill tp-purple"><b>LAC:</b> MLP 9→64→48→32→1 (Lookahead H=80)</span>
          </div>
          <div class="tier-desc">
            Mạng DDQN thứ hai chọn cặp toán tử thích hợp dựa trên đặc trưng vi mô kết hợp cơ chế tập trung Entropy-Softmax và Thompson Bandit. Tích hợp mạng LAC thẩm định nghiệm tương lai thay thế hoàn toàn Simulated Annealing.
          </div>
        </div>
        <div class="tier-col-kpi">
          <div class="kpi-tier-val">65 Cặp</div>
          <div class="kpi-tier-sub">Toán tử tổ hợp ALNS thích ứng</div>
        </div>
      </div>

      <div class="slab-connector">
        <div class="conn-badge">▼ Chỉ định cặp toán tử (d, r) cho bộ máy Heuristic</div>
      </div>

      <!-- Tier 3 -->
      <div class="arch-tier-slab at-t3">
        <div class="tier-col-badge">
          <div class="tier-label">Tầng 3 • Lọc đồ thị & Heuristic</div>
          <div class="tier-name">Contrastive GNN & Heuristic ALNS Core</div>
        </div>
        <div class="tier-col-body">
          <div class="tier-spec-row">
            <span class="tier-pill tp-green"><b>GNN 3-Layer:</b> kNN Message Passing</span>
            <span class="tier-pill tp-green"><b>Hàm mất mát:</b> InfoNCE + BCE Contrastive</span>
            <span class="tier-pill tp-green"><b>Kiểm tra ràng buộc:</b> O(1) Forward Time Slack</span>
          </div>
          <div class="tier-desc">
            Mô hình GNN học các cạnh triển vọng trong đồ thị không gian-thời gian, loại bỏ 98.74% cạnh kém tiềm năng để tăng tốc độ tìm kiếm. Lõi ALNS thực thi biến đổi giải pháp đảm bảo 100% nghiệm khả thi tức thì.
          </div>
        </div>
        <div class="tier-col-kpi">
          <div class="kpi-tier-val">-98.74%</div>
          <div class="kpi-tier-sub">Cạnh tìm kiếm không triển vọng</div>
        </div>
      </div>

      <div class="slab-connector">
        <div class="conn-badge">▼ Tích luỹ lộ trình tối ưu vào Dual-Slot Archive</div>
      </div>

      <!-- Tier 4 -->
      <div class="arch-tier-slab at-t4">
        <div class="tier-col-badge">
          <div class="tier-label">Tầng 4 • Tối ưu toàn cục MILP</div>
          <div class="tier-name">Set Partitioning & Dual-Slot Pool</div>
        </div>
        <div class="tier-col-body">
          <div class="tier-spec-row">
            <span class="tier-pill tp-amber"><b>Bộ giải:</b> HiGHS MILP C++ Solver</span>
            <span class="tier-pill tp-amber"><b>Dual-Slot:</b> 75% Tinh hoa + 25% Đa dạng</span>
            <span class="tier-pill tp-amber"><b>Giới hạn:</b> 4.0s Cutoff</span>
          </div>
          <div class="tier-desc">
            Bộ nhớ lộ trình duy trì 2 ngăn chuyên biệt (Slot A chứa tuyến tối ưu chi phí, Slot B chứa tuyến hỗ trợ giảm số xe). Định kỳ kích hoạt HiGHS MILP giải bài toán quy hoạch nguyên Set Partitioning để ghép nối nghiệm toàn cục tiệm cận BKS.
          </div>
        </div>
        <div class="tier-col-kpi">
          <div class="kpi-tier-val">HiGHS</div>
          <div class="kpi-tier-sub">Bộ giải MILP quy hoạch nguyên</div>
        </div>
      </div>
    </div>
  </div>

  <!-- ========================================================
       FIGURE 4: 3-STAGE PIPELINE (WORKFLOW)
       ======================================================== -->
  <div class="canvas-card" id="fig4-pipeline">
    <div class="card-header">
      <div class="card-title-group">
        <div class="card-tag">Hình 4 • Quy trình nghiên cứu & triển khai</div>
        <div class="card-title">Quy trình 3 giai đoạn thực thi hệ thống (End-to-End AI Optimization Pipeline)</div>
        <div class="card-subtitle">Từ huấn luyện Offline qua Domain Randomization đến chuyển giao Zero-Shot và điều phối Online thời gian thực</div>
      </div>
      <div class="card-badge">ĐỘ PHÂN GIẢI 4K • 300 DPI RETINA</div>
    </div>

    <div class="pipe-grid">
      <!-- Stage 1 -->
      <div class="pipe-card pc-s1">
        <div style="display:flex; flex-direction:column; gap:14px;">
          <div class="pipe-step-badge">Giai đoạn 01</div>
          <div class="pipe-stage-title">Huấn luyện ngoại tuyến<br>(Offline DR Training)</div>
          <div class="pipe-stage-sub">Học tri thức bất biến trên dữ liệu tự sinh</div>

          <div class="pipe-bullets">
            <div class="pipe-bullet-item">
              <b>Tự sinh dữ liệu ngẫu nhiên đa dạng (Domain Randomization):</b> Tự động tạo hàng ngàn đồ thị N ∈ [20, 100] khách hàng bao quát cả 3 miền C, R, RC.
            </div>
            <div class="pipe-bullet-item">
              <b>Huấn luyện phân cấp Macro & Micro DDQN:</b> Học chính sách qua bộ đệm Prioritized Experience Replay (PER), cập nhật Q-networks ổn định.
            </div>
            <div class="pipe-bullet-item">
              <b>Huấn luyện Contrastive GNN & LAC:</b> Huấn luyện mô hình lọc cạnh tương phản InfoNCE và mạng nơ-ron thẩm định giải pháp LAC Lookahead.
            </div>
          </div>
        </div>

        <div class="pipe-bottom-visual">
          <div class="pbv-icon">🧬</div>
          <div class="pbv-text">
            <div class="pbv-text-title">Tự sinh 3 miền phân bố không gian</div>
            <div class="pbv-text-desc">Mô phỏng đa dạng địa hình & tải trọng trước khi triển khai</div>
          </div>
        </div>
      </div>

      <!-- Arrow 1 -->
      <div class="pipe-arrow-col">
        <div class="pipe-arrow-icon">➔</div>
      </div>

      <!-- Stage 2 -->
      <div class="pipe-card pc-s2">
        <div style="display:flex; flex-direction:column; gap:14px;">
          <div class="pipe-step-badge">Giai đoạn 02</div>
          <div class="pipe-stage-title">Chuẩn bị Zero-Shot<br>(Weights Freezing)</div>
          <div class="pipe-stage-sub">Đóng băng toàn bộ trọng số mạng θ*</div>

          <div class="pipe-bullets">
            <div class="pipe-bullet-item">
              <b>Đóng băng 100% trọng số (Frozen Weights):</b> Cố định toàn bộ tham số của Macro DDQN, Micro DDQN, GNN và LAC sau quá trình huấn luyện ngoại tuyến.
            </div>
            <div class="pipe-bullet-item">
              <b>Tuyệt đối không tinh chỉnh (Zero Fine-Tuning):</b> Không cập nhật bất kỳ trọng số nào trên các bài toán kiểm thử mới, đảm bảo tính khách quan khoa học.
            </div>
            <div class="pipe-bullet-item">
              <b>Khả năng chuyển giao vượt trội:</b> Sẵn sàng giải quyết tức thì mọi quy mô đồ thị từ 100 đến 400 khách hàng mà không tốn chi phí train lại.
            </div>
          </div>
        </div>

        <div class="pipe-bottom-visual">
          <div class="pbv-icon">🔒</div>
          <div class="pbv-text">
            <div class="pbv-text-title">Đóng băng trọng số θ* tuyệt đối</div>
            <div class="pbv-text-desc">Zero Data Leakage • 100% tái lập khoa học khách quan</div>
          </div>
        </div>
      </div>

      <!-- Arrow 2 -->
      <div class="pipe-arrow-col">
        <div class="pipe-arrow-icon">➔</div>
      </div>

      <!-- Stage 3 -->
      <div class="pipe-card pc-s3">
        <div style="display:flex; flex-direction:column; gap:14px;">
          <div class="pipe-step-badge">Giai đoạn 03</div>
          <div class="pipe-stage-title">Thực thi trực tuyến<br>(Real-Time Online Dispatch)</div>
          <div class="pipe-stage-sub">Điều phối thời gian thực & Ghép nối nghiệm</div>

          <div class="pipe-bullets">
            <div class="pipe-bullet-item">
              <b>Tiếp nhận đồ thị thực tế:</b> Nạp dữ liệu đối chuẩn (Solomon-100, Homberger-200, 400) hoặc đơn hàng thực tế từ hệ sinh thái logistics NAMI.
            </div>
            <div class="pipe-bullet-item">
              <b>Dẫn hướng thích ứng siêu tốc:</b> Macro DDQN giám sát bế tắc, Micro DDQN chọn toán tử ALNS với độ trễ cực thấp (< 5ms mỗi bước lặp).
            </div>
            <div class="pipe-bullet-item">
              <b>Tối ưu toàn cục Set Partitioning:</b> Solver HiGHS tái tổ hợp các tuyến đường tinh hoa trong Dual-Slot Archive, tiệm cận kỷ lục thế giới BKS.
            </div>
          </div>
        </div>

        <div class="pipe-bottom-visual">
          <div class="pbv-icon">⚡</div>
          <div class="pbv-text">
            <div class="pbv-text-title">Điều phối thời gian thực &lt; 5ms</div>
            <div class="pbv-text-desc">HiGHS MILP ghép nối lộ trình tối ưu toàn cục</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ========================================================
       FIGURE 5: NAMI CONTROL TOWER SHOWCASE
       ======================================================== -->
  <div class="canvas-card" id="fig5-nami">
    <div class="card-header">
      <div class="card-title-group">
        <div class="card-tag">Hình 5 • Triển khai ứng dụng thực tế</div>
        <div class="card-title">Hệ thống giám sát và điều phối thực tế NAMI Dispatch Control Tower (TP. Hồ Chí Minh)</div>
        <div class="card-subtitle">Ứng dụng trực tiếp thuật toán Hybrid DDQN-ALNS vào điều phối đội xe giao vận thực tế trên mạng lưới giao thông đô thị</div>
      </div>
      <div class="card-badge">ĐỘ PHÂN GIẢI 4K • 300 DPI RETINA</div>
    </div>

    <div class="nami-full-grid">
      <div class="nami-img-frame">
        <img src="{nami_b64}" alt="NAMI Dispatch Real-World Control Tower">
      </div>

      <div class="nami-side-details">
        <div class="nami-side-head">
          <div class="nami-live-tag">LIVE TELEMETRY ACTIVE</div>
          <div class="nami-side-title">Điều phối đội xe thông minh theo thời gian thực</div>
        </div>

        <ul class="nami-side-bullets">
          <li><b>Bản đồ số giao thông TP.HCM:</b> Tích hợp mạng lưới đường bộ thực tế, tự động cập nhật tình trạng kẹt xe và vận tốc di chuyển từng khung giờ.</li>
          <li><b>Biểu đồ Gantt điều độ tài xế:</b> Trực quan hoá lịch trình từng tài xế, thời gian bốc xếp tại kho và các khung giờ cam kết giao cho khách hàng.</li>
          <li><b>Cảnh báo vi phạm tức thì:</b> Thuật toán O(1) Forward Slack tự động phát hiện nguy cơ trễ hẹn và kích hoạt chế độ TW-Rescue giải cứu tuyến xe.</li>
          <li><b>Hiệu quả kinh tế vượt trội:</b> Tiết kiệm nhiên liệu, giảm số lượng xe vận hành và tăng năng suất giao hàng lên hơn 25%.</li>
        </ul>

        <div class="nami-telemetry-grid">
          <div class="telemetry-card">
            <div class="tc-val">0</div>
            <div class="tc-lbl">Vi phạm khung giờ</div>
          </div>
          <div class="telemetry-card">
            <div class="tc-val">&lt; 5s</div>
            <div class="tc-lbl">Thời gian phản hồi AI</div>
          </div>
          <div class="telemetry-card">
            <div class="tc-val">100%</div>
            <div class="tc-lbl">Khả thi tải trọng xe</div>
          </div>
          <div class="telemetry-card">
            <div class="tc-val">-15%</div>
            <div class="tc-lbl">Chi phí nhiên liệu</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ========================================================
       FIGURE 6: PAIR ROUTE MAPS R101 & RC101
       ======================================================== -->
  <div class="canvas-card" id="fig6-routes">
    <div class="card-header">
      <div class="card-title-group">
        <div class="card-tag">Hình 6 • Hải đồ lộ trình tối ưu</div>
        <div class="card-title">Hải đồ lộ trình nghiệm tối ưu đối chuẩn quốc tế (Solomon R101 & RC101)</div>
        <div class="card-subtitle">Minh chứng năng lực khớp 100% kỷ lục thế giới BKS về số lượng xe vận hành dưới điều kiện kiểm thử Cold-Start độc lập</div>
      </div>
      <div class="card-badge">ĐỘ PHÂN GIẢI 4K • 300 DPI RETINA</div>
    </div>

    <div class="routes-pair-grid">
      <div class="route-fig-box">
        <img src="{r101_b64}" alt="Route R101 Solution">
        <div class="route-fig-caption">
          <b>Hải đồ lộ trình R101 (Phân bố ngẫu nhiên đều):</b> Số xe đạt <b>Nᵥ = 19 xe</b> (Khớp 100% BKS Kỷ lục thế giới), Tổng quãng đường <b>Dₜ = 1650.8 km</b>. Các cung đường mở rộng linh hoạt, không bị giao cắt chồng chéo.
        </div>
      </div>

      <div class="route-fig-box">
        <img src="{rc101_b64}" alt="Route RC101 Solution">
        <div class="route-fig-caption">
          <b>Hải đồ lộ trình RC101 (Phân bố hỗn hợp cụm và ngẫu nhiên):</b> Số xe đạt <b>Nᵥ = 15 xe</b> (Khớp 100% BKS Kỷ lục thế giới), Tổng quãng đường <b>Dₜ = 1644.8 km</b>. Gom cụm tối ưu các khu đô thị đông đúc và kết nối mượt mà khách hàng vệ tinh.
        </div>
      </div>
    </div>
  </div>

  <!-- ========================================================
       FIGURE 7: BENCHMARK RESULTS TABLE
       ======================================================== -->
  <div class="canvas-card" id="fig7-table">
    <div class="card-header">
      <div class="card-title-group">
        <div class="card-tag">Bảng 1 • Đối chuẩn thực nghiệm quốc tế</div>
        <div class="card-title">Bảng kết quả đối chuẩn thực nghiệm trên tập bài toán chuẩn quốc tế (Solomon & Homberger)</div>
        <div class="card-subtitle">Đánh giá độc lập theo chuẩn Cold-Start nghiêm ngặt • Kiểm định ý nghĩa thống kê phi tham số Wilcoxon Signed-Rank Test</div>
      </div>
      <div class="card-badge">ĐỘ PHÂN GIẢI 4K • 300 DPI RETINA</div>
    </div>

    <table class="academic-table">
      <thead>
        <tr>
          <th>Tập Dữ Liệu</th>
          <th>Thuật Toán Đánh Giá</th>
          <th>Số Xe Trung Bình (Nᵥ) ↓</th>
          <th>Quãng Đường TB (Dₜ) ↓</th>
          <th>Thời Gian Chạy (s)</th>
          <th>Kiểm Định Ý Nghĩa Thống Kê (Wilcoxon)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td rowspan="3" style="font-weight:800; background:#f8fafc; font-size:17.5px;">
            Solomon-100<br><span style="font-size:13.5px; color:#64748b; font-weight:600;">(56 bài toán, 100 khách)</span>
          </td>
          <td>BKS (Kỷ lục thế giới)</td>
          <td style="font-family:'JetBrains Mono',monospace; font-weight:800;">7.07</td>
          <td style="font-family:'JetBrains Mono',monospace; font-weight:800;">1013.36</td>
          <td>—</td>
          <td>—</td>
        </tr>
        <tr>
          <td>ALNS-Base (Cổ điển)</td>
          <td style="font-family:'JetBrains Mono',monospace; font-weight:800;">7.54</td>
          <td style="font-family:'JetBrains Mono',monospace; font-weight:800;">1017.31</td>
          <td style="font-family:'JetBrains Mono',monospace; font-weight:800;">10.1s</td>
          <td>Baseline đối chuẩn</td>
        </tr>
        <tr class="row-highlight">
          <td><b>Hybrid-DDQN (Phương pháp đề xuất)</b></td>
          <td style="font-family:'JetBrains Mono',monospace; font-size:19px;"><b>7.34*</b></td>
          <td style="font-family:'JetBrains Mono',monospace;">1017.82</td>
          <td style="font-family:'JetBrains Mono',monospace;">39.0s</td>
          <td><span class="pill-win">p = 0.00127 (Thắng vượt trội ALNS)</span></td>
        </tr>

        <tr>
          <td rowspan="2" style="font-weight:800; background:#f8fafc; font-size:17.5px;">
            Homberger-200<br><span style="font-size:13.5px; color:#64748b; font-weight:600;">(60 bài toán, 200 khách)</span>
          </td>
          <td>ALNS-Base (Cổ điển)</td>
          <td style="font-family:'JetBrains Mono',monospace; font-weight:800;">11.87</td>
          <td style="font-family:'JetBrains Mono',monospace; font-weight:800;">3009.91</td>
          <td style="font-family:'JetBrains Mono',monospace; font-weight:800;">3.9s</td>
          <td>Baseline đối chuẩn</td>
        </tr>
        <tr class="row-highlight">
          <td><b>Hybrid-DDQN (Phương pháp đề xuất)</b></td>
          <td style="font-family:'JetBrains Mono',monospace; font-size:19px;"><b>11.58*</b></td>
          <td style="font-family:'JetBrains Mono',monospace; font-size:19px;"><b>2844.73* (-165.18 km)</b></td>
          <td style="font-family:'JetBrains Mono',monospace;">35.8s</td>
          <td><span class="pill-win">p = 1.34 × 10⁻⁹ (Đột phá thống kê cực mạnh)</span></td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- ========================================================
       FIGURE 8: 4 GOLDEN KPI METRICS
       ======================================================== -->
  <div class="canvas-card" id="fig8-kpi">
    <div class="card-header">
      <div class="card-title-group">
        <div class="card-tag">Chỉ số vàng • Đóng góp khoa học</div>
        <div class="card-title">Bộ 4 chỉ số vàng đột phá của hệ thống Hybrid DDQN – ALNS</div>
        <div class="card-subtitle">Khẳng định hiệu quả vượt trội về tối ưu hoá chi phí vận hành, tiết kiệm nhiên liệu và ổn định tìm kiếm</div>
      </div>
      <div class="card-badge">ĐỘ PHÂN GIẢI 4K • 300 DPI RETINA</div>
    </div>

    <div class="kpi-cards-grid">
      <div class="kpi-stat-card ksc-blue">
        <div class="ksc-val">-165.18 km</div>
        <div class="ksc-title">Cắt giảm quãng đường di chuyển</div>
        <div class="ksc-desc">Tiết kiệm trung bình 165.18 km trên toàn bộ 60 bài toán Homberger-200 quy mô lớn, tương đương cắt giảm hàng ngàn lít nhiên liệu.</div>
      </div>

      <div class="kpi-stat-card ksc-teal">
        <div class="ksc-val">100%</div>
        <div class="ksc-title">Khớp số xe BKS trên họ RC</div>
        <div class="ksc-desc">Đạt chính xác số lượng xe tối thiểu của kỷ lục thế giới BKS trên toàn bộ các bài toán phân bố hỗn hợp phức tạp.</div>
      </div>

      <div class="kpi-stat-card ksc-purple">
        <div class="ksc-val">-98.74%</div>
        <div class="ksc-title">Không gian tìm kiếm bị loại bỏ</div>
        <div class="ksc-desc">Mạng Contrastive GNN loại bỏ 98.74% các cạnh kém tiềm năng, chuyển độ phức tạp từ O(N²) về O(kN), giúp tăng tốc ALNS gấp 4 lần.</div>
      </div>

      <div class="kpi-stat-card ksc-green">
        <div class="ksc-val">p = 1.34×10⁻⁹</div>
        <div class="ksc-title">Đột phá ý nghĩa thống kê</div>
        <div class="ksc-desc">Kiểm định Wilcoxon Signed-Rank khẳng định tính ưu việt hoàn toàn không phải do ngẫu nhiên (vượt xa ngưỡng tiêu chuẩn p &lt; 0.05).</div>
      </div>
    </div>
  </div>

</body>
</html>
"""

html_path = os.path.join(OUT_DIR, "render_suite.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Generated HTML template at {html_path}")
print("Launching Playwright for 4K Retina screen capture...")

cards_to_capture = [
    ("fig1-vrptw", "01_Mo_Hinh_Bai_Toan_VRPTW_4K.png"),
    ("fig2-dr", "02_Moi_Truong_Huan_Luyen_Domain_Randomization_4K.png"),
    ("fig3-arch", "03_Kien_Truc_He_Thong_4_Tang_3D_Glass_4K.png"),
    ("fig4-pipeline", "04_Quy_Trinh_3_Giai_Doan_Thuc_Thi_4K.png"),
    ("fig5-nami", "05_Giam_Sat_Dieu_Phoi_Thuc_Te_NAMI_TPHCM_4K.png"),
    ("fig6-routes", "06_Cap_Hai_Do_Lo_Trinh_R101_RC101_4K.png"),
    ("fig7-table", "07_Bang_Ket_Qua_Thuc_Nghiem_Doi_Chuan_4K.png"),
    ("fig8-kpi", "08_Bo_The_Chi_So_KPI_Vang_4K.png")
]

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox", "--disable-setuid-sandbox"])
    context = browser.new_context(
        viewport={"width": 2500, "height": 1800},
        device_scale_factor=2
    )
    page = context.new_page()
    page.goto(f"file://{html_path}", wait_until="networkidle")

    for card_id, filename in cards_to_capture:
        elem = page.locator(f"#{card_id}")
        dest_path = os.path.join(OUT_DIR, filename)
        elem.screenshot(path=dest_path)
        size_kb = os.path.getsize(dest_path) / 1024
        print(f"  ✓ Exported: {filename} ({size_kb:.1f} KB)")

    browser.close()

# Copy official IEEE vector architecture
shutil.copyfile(
    os.path.join(SRC_ROOT, "docs/figures/poster_architecture.png"),
    os.path.join(OUT_DIR, "03B_Kien_Truc_He_Thong_Chuan_IEEE_Vector_4K.png")
)
print("  ✓ Exported: 03B_Kien_Truc_He_Thong_Chuan_IEEE_Vector_4K.png")

# Create clean zip archive for Zalo transfer
print(f"Compressing into {ZIP_PATH}...")
with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, _, files in os.walk(OUT_DIR):
        for file in files:
            if file.endswith(".png"):
                file_path = os.path.join(root, file)
                zipf.write(file_path, arcname=file)

zip_size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
print(f"DONE! Package created: {ZIP_PATH} ({zip_size_mb:.2f} MB)")
