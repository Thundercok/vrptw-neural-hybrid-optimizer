import base64
import mimetypes
import os
import shutil

from playwright.sync_api import sync_playwright
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Mm

WORKSPACE_DIR = os.path.abspath(os.path.dirname(__file__))

def get_base64_image(image_name):
    full_path = os.path.join(WORKSPACE_DIR, image_name)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Missing image: {full_path}")
    ext = os.path.splitext(image_name)[1].lower()
    mime = mimetypes.types_map.get(ext, 'image/jpeg')
    with open(full_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def build_poster():
    bg_b64 = get_base64_image("extracted_rId2.jpg")
    qr_b64 = get_base64_image("extracted_rId3.png")
    arch_b64 = get_base64_image("docs/figures/poster_architecture.png")
    r101_b64 = get_base64_image("docs/figures/route_R101.png")
    rc101_b64 = get_base64_image("docs/figures/route_RC101.png")
    nami_b64 = get_base64_image("docs/figures/nami_dispatch_real_hcmc.png")

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Poster NCKHSV 2026 - TDTU - VRPTW Hybrid DDQN-ALNS</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400;1,700&family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}

  body {{
    width: 2362px;
    height: 3341px;
    position: relative;
    background-color: #0c0820;
    background-image: url('{bg_b64}');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    font-family: 'Plus Jakarta Sans', 'Montserrat', -apple-system, sans-serif;
    color: #1e293b;
    overflow: hidden;
    -webkit-font-smoothing: antialiased;
  }}

  /* HEADER TEXT BLOCK */
  .header-block {{
    position: absolute;
    top: 85px;
    left: 135px;
    width: 1680px;
  }}

  .header-dept-1 {{
    font-family: 'Montserrat', sans-serif;
    font-size: 38px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }}

  .header-dept-2 {{
    font-family: 'Montserrat', sans-serif;
    font-size: 26px;
    font-weight: 600;
    font-style: italic;
    color: #b4aad2;
    margin-top: 4px;
    letter-spacing: 0.3px;
  }}

  .header-title-box {{
    margin-top: 24px;
  }}

  .header-title-main {{
    font-family: 'Montserrat', sans-serif;
    font-size: 40px;
    font-weight: 900;
    color: #ffffff;
    line-height: 1.25;
    text-transform: uppercase;
    letter-spacing: -0.3px;
  }}

  .header-title-sub {{
    font-family: 'Montserrat', sans-serif;
    font-size: 33px;
    font-weight: 900;
    color: #f6c343;
    line-height: 1.25;
    text-transform: uppercase;
    margin-top: 6px;
    letter-spacing: -0.2px;
  }}

  .header-author-row {{
    margin-top: 22px;
    font-size: 23px;
    font-weight: 700;
    color: #ffffff;
    display: flex;
    gap: 40px;
  }}

  .header-author-row b {{
    color: #f6c343;
  }}

  .header-affil-row {{
    margin-top: 10px;
    font-size: 17.5px;
    font-weight: 500;
    font-style: italic;
    color: #cbd5e1;
    line-height: 1.45;
  }}

  /* QR CODE PLACEMENT (Dedicated white box in template) */
  .qr-box {{
    position: absolute;
    top: 310px;
    left: 1870px;
    width: 340px;
    height: 350px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }}

  .qr-img {{
    width: 280px;
    height: 280px;
    display: block;
  }}

  .qr-label {{
    font-size: 13.5px;
    font-weight: 800;
    color: #0c1e5a;
    text-transform: uppercase;
    letter-spacing: 0.6px;
  }}

  /* MAIN WHITE POSTER CANVAS (x=135 to 2225, y=745 to 3160) */
  .poster-content {{
    position: absolute;
    top: 760px;
    left: 155px;
    width: 2052px;
    height: 2390px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }}

  /* SECTION HEADER BANNER (Golden Ribbon from School Template) */
  .section-banner {{
    background: #fef3d6;
    border-left: 6px solid #0c1e5a;
    padding: 9px 18px;
    display: flex;
    align-items: center;
    border-radius: 4px;
    margin-bottom: 12px;
  }}

  .section-banner-title {{
    font-family: 'Montserrat', sans-serif;
    font-size: 24px;
    font-weight: 800;
    color: #0c1e5a;
    letter-spacing: 0.4px;
    text-transform: uppercase;
  }}

  .section-banner-title span {{
    color: #1d4ed8;
    margin-right: 8px;
  }}

  /* ROW 1: GIỚI THIỆU & TẬP DỮ LIỆU */
  .row-top {{
    display: grid;
    grid-template-columns: 880px 1fr;
    gap: 30px;
    height: 480px;
  }}

  .col-intro {{
    display: flex;
    flex-direction: column;
  }}

  .intro-text {{
    font-size: 16.5px;
    line-height: 1.55;
    color: #1e293b;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}

  .intro-text p {{
    text-align: justify;
  }}

  .intro-bullet {{
    list-style: none;
    position: relative;
    padding-left: 18px;
    text-align: justify;
  }}

  .intro-bullet::before {{
    content: "•";
    position: absolute;
    left: 0;
    color: #0c1e5a;
    font-weight: 900;
    font-size: 20px;
    line-height: 1;
  }}

  .formula-box {{
    background: #f8fafc;
    border: 1.5px solid #cbd5e1;
    border-left: 4px solid #1d4ed8;
    border-radius: 6px;
    padding: 10px 14px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    color: #0f172a;
    line-height: 1.55;
    margin: 4px 0;
  }}

  .formula-box b {{
    color: #1e40af;
  }}

  .col-data {{
    display: flex;
    flex-direction: column;
  }}

  /* ACADEMIC BOOKTABS TABLE */
  .academic-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 15px;
    line-height: 1.4;
    text-align: left;
    margin-bottom: 12px;
  }}

  .academic-table thead th {{
    border-top: 2.5px solid #0c1e5a;
    border-bottom: 1.5px solid #0c1e5a;
    padding: 8px 10px;
    font-weight: 800;
    color: #0c1e5a;
    background: #f8fafc;
  }}

  .academic-table tbody td {{
    padding: 7px 10px;
    border-bottom: 1px solid #e2e8f0;
    color: #334155;
  }}

  .academic-table tbody tr:last-child td {{
    border-bottom: 2px solid #0c1e5a;
  }}

  .data-bullets {{
    font-size: 15px;
    line-height: 1.5;
    color: #334155;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}

  .data-bullets li {{
    list-style: none;
    position: relative;
    padding-left: 18px;
    text-align: justify;
  }}

  .data-bullets li::before {{
    content: "•";
    position: absolute;
    left: 0;
    color: #0c1e5a;
    font-weight: 900;
    font-size: 18px;
  }}

  /* ROW 2: PHƯƠNG PHÁP NGHIÊN CỨU (HERO ARCHITECTURE) */
  .row-method {{
    display: flex;
    flex-direction: column;
    height: 870px;
  }}

  .arch-container {{
    display: grid;
    grid-template-columns: 1180px 1fr;
    gap: 24px;
    align-items: center;
    flex: 1;
    background: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px;
  }}

  .arch-img-wrap {{
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }}

  .arch-img {{
    width: 100%;
    max-height: 780px;
    object-fit: contain;
    border-radius: 6px;
  }}

  .arch-details-col {{
    display: flex;
    flex-direction: column;
    gap: 14px;
    height: 100%;
    justify-content: space-between;
  }}

  .arch-card {{
    background: #f8fafc;
    border: 1.5px solid #cbd5e1;
    border-radius: 6px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}

  .ac-tier1 {{ border-left: 4px solid #1d4ed8; }}
  .ac-tier2 {{ border-left: 4px solid #0d9488; }}
  .ac-tier3 {{ border-left: 4px solid #7e22ce; }}
  .ac-milp  {{ border-left: 4px solid #b45309; }}

  .arch-card-head {{
    font-size: 15.5px;
    font-weight: 800;
    color: #0c1e5a;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}

  .arch-card-badge {{
    font-size: 11px;
    font-weight: 800;
    padding: 2px 7px;
    border-radius: 3px;
    text-transform: uppercase;
  }}

  .ab-blue   {{ background: #dbeafe; color: #1e40af; }}
  .ab-teal   {{ background: #ccfbf1; color: #0f766e; }}
  .ab-purple {{ background: #f3e8ff; color: #6b21a8; }}
  .ab-amber  {{ background: #fef3c7; color: #b45309; }}

  .arch-card-desc {{
    font-size: 13.5px;
    line-height: 1.45;
    color: #334155;
    text-align: justify;
  }}

  /* ROW 3: KẾT QUẢ THỰC NGHIỆM & KẾT LUẬN */
  .row-bottom {{
    display: grid;
    grid-template-columns: 1260px 1fr;
    gap: 28px;
    flex: 1;
  }}

  .col-results {{
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}

  .res-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13.5px;
    text-align: center;
  }}

  .res-table thead th {{
    border-top: 2.5px solid #0c1e5a;
    border-bottom: 1.5px solid #0c1e5a;
    padding: 6px 8px;
    font-weight: 800;
    color: #0c1e5a;
    background: #f8fafc;
  }}

  .res-table tbody td {{
    padding: 5px 8px;
    border-bottom: 1px solid #e2e8f0;
    color: #334155;
  }}

  .res-table tbody tr:last-child td {{
    border-bottom: 2px solid #0c1e5a;
  }}

  .res-table .row-best td {{
    font-weight: 800;
    color: #1e40af;
    background: #eff6ff;
  }}

  .res-figs-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    height: 335px;
  }}

  .res-fig-box {{
    background: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}

  .res-fig-caption {{
    font-size: 12px;
    font-weight: 700;
    color: #475569;
    text-align: center;
    padding-top: 4px;
  }}

  .res-fig-box img {{
    width: 100%;
    height: 100%;
    object-fit: contain;
  }}

  .findings-bullets {{
    font-size: 13.5px;
    line-height: 1.48;
    color: #1e293b;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}

  .findings-bullets li {{
    list-style: none;
    position: relative;
    padding-left: 18px;
    text-align: justify;
  }}

  .findings-bullets li::before {{
    content: "•";
    position: absolute;
    left: 0;
    color: #1d4ed8;
    font-weight: 900;
    font-size: 17px;
  }}

  .col-conclusion {{
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 8px;
  }}

  .concl-bullets {{
    font-size: 13.5px;
    line-height: 1.45;
    color: #1e293b;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}

  .concl-bullets li {{
    list-style: none;
    position: relative;
    padding-left: 18px;
    text-align: justify;
  }}

  .concl-bullets li::before {{
    content: "•";
    position: absolute;
    left: 0;
    color: #0c1e5a;
    font-weight: 900;
    font-size: 17px;
  }}

  /* KPI METRICS 2x2 GRID */
  .kpi-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin: 4px 0;
  }}

  .kpi-card {{
    background: #f8fafc;
    border: 1.5px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 12px;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }}

  .kpi-num {{
    font-family: 'Montserrat', sans-serif;
    font-size: 22px;
    font-weight: 900;
    color: #1e40af;
    line-height: 1.1;
  }}

  .kpi-label {{
    font-size: 12px;
    font-weight: 700;
    color: #0f172a;
    margin-top: 2px;
    line-height: 1.3;
  }}

  .kpi-tag {{
    font-size: 10.5px;
    font-weight: 600;
    color: #64748b;
    margin-top: 1px;
  }}

  /* NAMI REAL DEPLOYMENT SHOWCASE */
  .deploy-showcase-box {{
    background: #ffffff;
    border: 1.5px solid #86efac;
    border-radius: 8px;
    padding: 8px 10px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    box-shadow: 0 4px 12px -2px rgba(22, 101, 52, 0.08);
  }}

  .deploy-head-bar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}

  .deploy-head-title {{
    font-size: 13px;
    font-weight: 800;
    color: #166534;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }}

  .deploy-head-tag {{
    font-size: 10px;
    font-weight: 700;
    color: #15803d;
    background: #dcfce7;
    padding: 2px 7px;
    border-radius: 10px;
  }}

  .deploy-img-container {{
    width: 100%;
    height: 190px;
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid #cbd5e1;
    background: #f8fafc;
  }}

  .deploy-screenshot {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: top center;
    display: block;
  }}

  .deploy-caption {{
    font-size: 11px;
    line-height: 1.4;
    color: #334155;
    text-align: justify;
  }}

  .refs-box {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 11px;
    line-height: 1.4;
    color: #475569;
  }}

  .refs-box b {{
    color: #0c1e5a;
    font-size: 11.5px;
  }}
</style>
</head>
<body>

  <!-- HEADER TEXT BLOCK -->
  <div class="header-block">
    <div class="header-dept-1">NGHIÊN CỨU KHOA HỌC SINH VIÊN</div>
    <div class="header-dept-2">Khoa Công nghệ Thông tin</div>

    <div class="header-title-box">
      <div class="header-title-main">XÂY DỰNG MÔ HÌNH ĐỂ TỐI ƯU HÓA TUYẾN ĐƯỜNG TRONG LOGISTICS</div>
      <div class="header-title-sub">TIẾP CẬN BÀI TOÁN VRPTW BẰNG THUẬT TOÁN TÌM KIẾM LÂN CẬN LỚN THÍCH ỨNG LAI HỌC TĂNG CƯỜNG SÂU (HYBRID DDQN-ALNS)</div>
    </div>

    <div class="header-author-row">
      <div>SVTH: <b>Huỳnh Nhật Huy</b> (MSSV: 523C0012)</div>
      <div>GVHD: <b>TS. Hồ Thị Linh*</b></div>
    </div>

    <div class="header-affil-row">
      <div>Sinh viên ngành: Khoa học Máy tính &bull; Khoa Công nghệ Thông tin</div>
      <div>* Nhóm nghiên cứu Xử lý Ngôn ngữ Tự nhiên & Khai phá Dữ liệu (NLP-KD), Trường Đại học Tôn Đức Thắng</div>
    </div>
  </div>

  <!-- QR CODE IN DEDICATED TEMPLATE BOX -->
  <div class="qr-box">
    <img src="{qr_b64}" class="qr-img" alt="QR Code">
    <div class="qr-label">Quét mã xem demo hệ thống & bài báo</div>
  </div>

  <!-- MAIN POSTER CANVAS -->
  <div class="poster-content">

    <!-- ROW 1: GIỚI THIỆU & TẬP DỮ LIỆU -->
    <div class="row-top">
      <!-- Col 1: Giới thiệu -->
      <div class="col-intro">
        <div class="section-banner">
          <div class="section-banner-title"><span>[ ]</span> 1. GIỚI THIỆU BÀI TOÁN & ĐỘNG LỰC NGHIÊN CỨU</div>
        </div>
        <div class="intro-text">
          <p>
            <b>Bài toán VRPTW (Vehicle Routing Problem with Time Windows):</b> Xác định tập hợp lộ trình tối ưu cho đội xe đồng nhất xuất phát từ kho trung tâm phục vụ tập khách hàng rải rác địa lý, thỏa mãn tải trọng xe <i>Q</i> và phục vụ trong khung thời gian bắt buộc <i>[e<sub>i</sub>, l<sub>i</sub>]</i>.
          </p>

          <div class="formula-box">
            <b>Hàm mục tiêu từ điển (Lexicographic):</b><br>
            min f(s) = M &middot; N<sub>V</sub>(s) + D<sub>T</sub>(s), &nbsp; với M = 10<sup>5</sup> &gg; max D<sub>T</sub><br>
            <i>(Ưu tiên tối thượng giảm số xe vận hành N<sub>V</sub>, sau đó giảm quãng đường D<sub>T</sub>)</i>
          </div>

          <ul>
            <li class="intro-bullet">
              <b>Hạn chế ALNS truyền thống:</b> Chọn toán tử ngẫu nhiên qua bánh xe Roulette tĩnh, thiếu cơ chế cảm nhận bế tắc, dễ sa lầy tại các cực tiểu địa phương sâu.
            </li>
            <li class="intro-bullet">
              <b>Hạn chế End-to-End DRL:</b> Các mô hình nơ-ron thuần túy dễ vi phạm khung thời gian và bùng nổ nghiệm không khả thi khi mở rộng quy mô đồ thị.
            </li>
            <li class="intro-bullet">
              <b>Đột phá đề xuất:</b> Hệ thống lai 3 tầng DDQN-ALNS kết hợp điều khiển phân cấp (Macro/Micro), lọc cạnh bằng Contrastive GNN và tối ưu toàn cục qua Set Partitioning MILP.
            </li>
          </ul>
        </div>
      </div>

      <!-- Col 2: Tập dữ liệu -->
      <div class="col-data">
        <div class="section-banner">
          <div class="section-banner-title"><span>[ ]</span> 2. TẬP DỮ LIỆU & THIẾT LẬP THỰC NGHIỆM</div>
        </div>

        <table class="academic-table">
          <thead>
            <tr>
              <th>Bộ Thực Nghiệm</th>
              <th>Số Bài</th>
              <th>Quy Mô</th>
              <th>Đặc Trưng Không - Thời Gian</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><b>Solomon-100</b></td>
              <td>56</td>
              <td>100 khách</td>
              <td>6 họ bài toán: Cụm (C1, C2), Ngẫu nhiên (R1, R2), Hỗn hợp (RC1, RC2)</td>
            </tr>
            <tr>
              <td><b>Homberger-200</b></td>
              <td>60</td>
              <td>200 khách</td>
              <td>10 bài toán &times; 6 họ cấu trúc địa hình không gian phức tạp</td>
            </tr>
            <tr>
              <td><b>Homberger-400</b></td>
              <td>60</td>
              <td>400 khách</td>
              <td>Quy mô lớn thử thách cực hạn năng lực tìm kiếm và tránh dừng sớm</td>
            </tr>
          </tbody>
        </table>

        <ul class="data-bullets">
          <li>
            <b>Quy chuẩn Cold-Start độc lập:</b> Toàn bộ bộ nhớ đệm (EliteArchive) được làm sạch hoàn toàn giữa các lượt chạy. Mọi bộ giải bắt đầu độc lập từ nghiệm tham lam ban đầu (100% tái lập khoa học, zero rò rỉ nghiệm).
          </li>
          <li>
            <b>Domain Randomization (DR):</b> Huấn luyện mô hình DRL duy nhất trên đồ thị tự sinh quy mô nhỏ N &isin; [20, 100], đóng băng tham số &theta;* và chuyển giao trực tiếp <b>Zero-Shot</b> sang toàn bộ 176 bài toán chuẩn mà không cần fine-tuning.
          </li>
          <li>
            <b>Môi trường thực nghiệm:</b> Triển khai trên Python 3.10, PyTorch 2.1, HiGHS MILP C++ Solver, biên dịch JIT qua Numba; thực thi trên phần cứng Apple Silicon M1 (8 nhân, 16GB RAM) và Linux HPC.
          </li>
        </ul>
      </div>
    </div>

    <!-- ROW 2: PHƯƠNG PHÁP NGHIÊN CỨU (HERO FULL-WIDTH ARCHITECTURE) -->
    <div class="row-method">
      <div class="section-banner">
        <div class="section-banner-title"><span>[ ]</span> 3. PHƯƠNG PHÁP THỰC HIỆN: KIẾN TRÚC LAI PHÂN CẤP HYBRID DDQN – ALNS</div>
      </div>

      <div class="arch-container">
        <!-- Hero Architecture Diagram -->
        <div class="arch-img-wrap">
          <img src="{arch_b64}" class="arch-img" alt="Hybrid DDQN Architecture">
        </div>

        <!-- Architecture Detail Cards -->
        <div class="arch-details-col">
          <div class="arch-card ac-tier1">
            <div class="arch-card-head">
              <span>Tầng 1: Macro Plateau Controller (&pi;<sub>macro</sub>)</span>
              <span class="arch-card-badge ab-blue">Semi-MDP &bull; 13D</span>
            </div>
            <div class="arch-card-desc">
              Mạng Dueling DDQN nhận vector trạng thái 13 chiều đặc trưng (độ bế tắc, áp lực tải, nhiệt độ). Cứ sau &Delta;<sub>seg</sub> = 100 bước, mô hình chuyển đổi linh hoạt giữa <b>7 chế độ chiến lược</b> (Default, Intensify, Diversify, TW-Rescue, Pool-Recombine, Route-Reduce, Infeasible-Descent) để chủ động phá vỡ cực tiểu địa phương.
            </div>
          </div>

          <div class="arch-card ac-tier2">
            <div class="arch-card-head">
              <span>Tầng 2: Micro Selection & LAC (&pi;<sub>micro</sub>)</span>
              <span class="arch-card-badge ab-teal">65 Action Pairs &bull; 20D</span>
            </div>
            <div class="arch-card-desc">
              Mạng DDQN thứ hai điều hành 65 cặp toán tử (13 Phá huỷ &times; 5 Sửa chữa) dựa trên vector 20D và cơ chế tập trung Entropy-Softmax. Tích hợp mạng <b>Learned Acceptance (LAC)</b> với MLP Lookahead H=80 bước, <b>thay thế hoàn toàn Simulated Annealing cổ điển</b>.
            </div>
          </div>

          <div class="arch-card ac-tier3">
            <div class="arch-card-head">
              <span>Tầng 3: Contrastive GNN Edge Pruning</span>
              <span class="arch-card-badge ab-purple">-98.74% Search Edges</span>
            </div>
            <div class="arch-card-desc">
              Mô hình Graph Neural Network 3 lớp huấn luyện qua hàm mất mát tương phản InfoNCE + BCE. Mô hình lọc sạch <b>98.74% các cạnh kém hứa hẹn</b> trong đồ thị không gian-thời gian, giảm độ phức tạp từ O(N<sup>2</sup>) xuống O(kN), giúp tăng tốc ALNS gấp 4 lần.
            </div>
          </div>

          <div class="arch-card ac-milp">
            <div class="arch-card-head">
              <span>Tầng 4: Set Partitioning Recombination</span>
              <span class="arch-card-badge ab-amber">HiGHS MILP Solver</span>
            </div>
            <div class="arch-card-desc">
              Tích luỹ các tuyến tốt nhất vào <b>Dual-Slot Route Archive</b> (75% lộ trình tinh hoa + 25% lộ trình đa dạng). Định kỳ kích hoạt solver HiGHS giải bài toán quy hoạch nguyên Set Partitioning trong giới hạn 4.0s để lắp ghép nghiệm tối ưu toàn cục, tiệm cận kỷ lục thế giới BKS.
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ROW 3: KẾT QUẢ THỰC NGHIỆM & KẾT LUẬN -->
    <div class="row-bottom">
      <!-- Col 1: Kết quả thực nghiệm -->
      <div class="col-results">
        <div class="section-banner">
          <div class="section-banner-title"><span>[ ]</span> 4. KẾT QUẢ THỰC NGHIỆM & PHÂN TÍCH ĐỐI CHUẨN QUỐC TẾ</div>
        </div>

        <!-- Top: Results Table -->
        <table class="res-table">
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
              <td rowspan="3" style="font-weight:700; background:#f8fafc;">Solomon-100<br><span style="font-size:11.5px; color:#64748b; font-weight:500;">(56 bài toán)</span></td>
              <td>BKS (Kỷ lục thế giới)</td>
              <td>7.07</td>
              <td>1013.36</td>
              <td>—</td>
              <td>—</td>
            </tr>
            <tr>
              <td>ALNS-Base</td>
              <td>7.54</td>
              <td>1017.31</td>
              <td>10.1s</td>
              <td>Baseline</td>
            </tr>
            <tr class="row-best">
              <td>Hybrid-DDQN (Đề xuất)</td>
              <td>7.34*</td>
              <td>1017.82</td>
              <td>39.0s</td>
              <td>p = 0.00127 (Thắng vượt trội)</td>
            </tr>

            <tr>
              <td rowspan="2" style="font-weight:700; background:#f8fafc;">Homberger-200<br><span style="font-size:11.5px; color:#64748b; font-weight:500;">(60 bài toán)</span></td>
              <td>ALNS-Base</td>
              <td>11.87</td>
              <td>3009.91</td>
              <td>3.9s</td>
              <td>Baseline</td>
            </tr>
            <tr class="row-best">
              <td>Hybrid-DDQN (Đề xuất)</td>
              <td>11.58*</td>
              <td>2844.73* (-165.18 km)</td>
              <td>35.8s</td>
              <td>p = 1.34&times;10<sup>-9</sup> (Đột phá thống kê)</td>
            </tr>
          </tbody>
        </table>

        <!-- Middle: 2 Authentic Publication Route Figures Side by Side -->
        <div class="res-figs-grid">
          <div class="res-fig-box">
            <img src="{r101_b64}" alt="R101 Route Solution">
            <div class="res-fig-caption">Hải đồ lộ trình R101 (Phân bố ngẫu nhiên đều, N<sub>V</sub> = 19 xe khớp BKS, TD = 1650.8 km)</div>
          </div>
          <div class="res-fig-box">
            <img src="{rc101_b64}" alt="RC101 Route Solution">
            <div class="res-fig-caption">Hải đồ lộ trình RC101 (Phân bố hỗn hợp cụm và ngẫu nhiên, N<sub>V</sub> = 15 xe khớp BKS, TD = 1644.8 km)</div>
          </div>
        </div>

        <!-- Bottom: Scientific Findings Bullets -->
        <ul class="findings-bullets">
          <li>
            <b>100% Bảo Toàn Tính Khả Thi:</b> Không ghi nhận bất kỳ vi phạm khung giờ hay tải trọng nào trên toàn bộ 580 lượt chạy độc lập (176 bài toán &times; 5 seeds).
          </li>
          <li>
            <b>Ưu thế Quãng đường tại Quy mô 200:</b> Khi khớp số lượng xe sàn, Hybrid-DDQN giảm tổng quãng đường di chuyển từ <b>1.75% đến 4.07%</b> (tiết kiệm trung bình 165.18 km, p = 1.34&times;10<sup>-9</sup>).
          </li>
          <li>
            <b>Khắc phục Lạm phát Xe của Google OR-Tools:</b> Trên họ RC2, OR-Tools lạm phát tới 6.50 xe (+80%), trong khi Hybrid-DDQN duy trì đúng mức sàn 3.25 xe, tối ưu chi phí vận hành đội xe thực tế.
          </li>
        </ul>
      </div>

      <!-- Col 2: Kết luận & Đóng góp -->
      <div class="col-conclusion">
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <div class="section-banner">
            <div class="section-banner-title"><span>[ ]</span> 5. KẾT LUẬN & ĐÓNG GÓP KHOA HỌC</div>
          </div>

          <ul class="concl-bullets">
            <li>
              <b>Đóng góp Lý thuyết:</b> Thiết lập khung tối ưu lai Tri-Level đầu tiên cho VRPTW, hài hòa năng lực điều hướng của Deep RL, tốc độ tỉa cạnh của GNN và độ chính xác toàn cục của MILP.
            </li>
            <li>
              <b>Khả năng Tổng quát hóa Zero-Shot:</b> Chiến lược Domain Randomization chứng minh mô hình huấn luyện trên đồ thị nhỏ N &isin; [20, 100] có thể chuyển giao trực tiếp sang đồ thị 400 khách mà không cần fine-tuning.
            </li>
            <li>
              <b>Minh bạch Thực nghiệm & Tái lập:</b> Tuân thủ nghiêm ngặt quy chuẩn Independent Cold-Start, công bố toàn bộ log nghiệm và mã nguồn đối chuẩn tin cậy cho cộng đồng vận trù học.
            </li>
            <li>
              <b>Hướng Mở Rộng Đầy Hứa Hẹn:</b> Mở rộng khung lai cho đội xe không đồng nhất (Heterogeneous Fleet) và bài toán xe tải điện kết hợp trạm sạc pin (EVRPTW).
            </li>
          </ul>

          <!-- 4 KPI CARDS (2x2) -->
          <div class="kpi-grid">
            <div class="kpi-card">
              <div class="kpi-num">-165.18 km</div>
              <div class="kpi-label">Quãng đường tiết kiệm TB (Homberger-200)</div>
              <div class="kpi-tag">Wilcoxon p = 1.34&times;10<sup>-9</sup> (Đột phá)</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-num">-98.74%</div>
              <div class="kpi-label">Cắt tỉa không gian tìm kiếm cạnh</div>
              <div class="kpi-tag">Contrastive GNN &bull; O(N<sup>2</sup>) &rarr; O(kN)</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-num">100%</div>
              <div class="kpi-label">Bảo toàn tính khả thi vận hành</div>
              <div class="kpi-tag">Zero vi phạm tải & khung giờ (580 runs)</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-num">Zero-Shot</div>
              <div class="kpi-label">Tổng quát hóa quy mô đồ thị</div>
              <div class="kpi-tag">Huấn luyện N&le;100 &rarr; Suy luận N=400</div>
            </div>
          </div>

          <!-- NAMI REAL DEPLOYMENT SHOWCASE -->
          <div class="deploy-showcase-box">
            <div class="deploy-head-bar">
              <div class="deploy-head-title">🚀 Ứng Dụng Thực Tiễn: NAMI Dispatch Control Tower</div>
              <span class="deploy-head-tag">Bản Đồ Đường Bộ TP.HCM</span>
            </div>
            <div class="deploy-img-container">
              <img src="{nami_b64}" alt="NAMI Dispatch Real HCMC Map" class="deploy-screenshot">
            </div>
            <div class="deploy-caption">
              <b>Triển khai thực tế:</b> Thuật toán điều phối chính xác 18 đội xe trên mạng lưới đường bộ thực tế TP.HCM, tiết kiệm <b>-1.40%</b> quãng đường so với ALNS Base (704.03 km vs 714.05 km) và lập lịch tài xế qua biểu đồ Gantt thời gian thực.
            </div>
          </div>
        </div>

        <!-- Academic References -->
        <div class="refs-box">
          <b>Tài liệu tham khảo chọn lọc:</b><br>
          [1] S. Ropke & D. Pisinger, "An Adaptive Large Neighborhood Search Heuristic for the VRPTW", <i>Transportation Science</i>, 40(4), pp. 455–472, 2006.<br>
          [2] V. Mnih et al., "Human-level control through deep reinforcement learning", <i>Nature</i>, vol. 518, pp. 529–533, 2015.<br>
          [3] H. Gehring & J. Homberger, "A Parallel Two-phase Metaheuristic for Routing Problems", <i>APJOR</i>, vol. 18, pp. 35–47, 2001.
        </div>
      </div>
    </div>

  </div>

</body>
</html>
"""

    html_file = os.path.join(WORKSPACE_DIR, "official_school_poster.html")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Wrote clean academic HTML to {html_file}")

    pdf_file = os.path.join(WORKSPACE_DIR, "Poster_VRPTW_NCKHSV_2026.pdf")
    png_file = os.path.join(WORKSPACE_DIR, "Poster_VRPTW_NCKHSV_2026.png")

    print("Rendering with Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 2362, "height": 3341}, device_scale_factor=1.0)
        page.goto(f"file://{html_file}", wait_until="networkidle")

        page.screenshot(path=png_file, full_page=True)
        print(f"Exported PNG to {png_file}")

        page.pdf(path=pdf_file, width="594mm", height="841mm", print_background=True, margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"})
        print(f"Exported PDF to {pdf_file}")

        browser.close()

    # Generate PPTX files
    export_pptx_and_sync(png_file, pdf_file)

def export_pptx_and_sync(png_file, pdf_file):
    print("Generating PPTX deliverables...")
    pptx_a1 = os.path.join(WORKSPACE_DIR, "Poster_VRPTW_NCKHSV_2026_A1.pptx")
    pptx_169 = os.path.join(WORKSPACE_DIR, "Poster_VRPTW_NCKHSV_2026.pptx")

    # 1. ISO A1 Presentation (594 x 841 mm)
    prs_a1 = Presentation()
    prs_a1.slide_width = Mm(594)
    prs_a1.slide_height = Mm(841)
    slide_a1 = prs_a1.slides.add_slide(prs_a1.slide_layouts[6])
    slide_a1.shapes.add_picture(png_file, 0, 0, width=Mm(594), height=Mm(841))
    prs_a1.save(pptx_a1)
    print(f"Exported ISO A1 PPTX to {pptx_a1}")

    # 2. 16:9 Presentation (13.333 x 7.5 in)
    prs_169 = Presentation()
    prs_169.slide_width = Inches(13.333)
    prs_169.slide_height = Inches(7.5)
    slide_169 = prs_169.slides.add_slide(prs_169.slide_layouts[6])

    bg_shape = slide_169.shapes.add_shape(1, 0, 0, Inches(13.333), Inches(7.5))
    bg_shape.fill.solid()
    bg_shape.fill.fore_color.rgb = RGBColor(12, 8, 32)
    bg_shape.line.fill.background()

    img_h = Inches(7.3)
    img_w = img_h * (2362.0 / 3341.0)
    left = (Inches(13.333) - img_w) / 2
    slide_169.shapes.add_picture(png_file, left, Inches(0.1), width=img_w, height=img_h)
    prs_169.save(pptx_169)
    print(f"Exported 16:9 PPTX to {pptx_169}")

    # Synchronize to parent workspace & artifact directory
    parent_dir = os.path.dirname(WORKSPACE_DIR)
    artifact_dir = "/Users/thundercock2/.gemini/antigravity/brain/dc00c957-f7cf-4b6e-b6ea-c8356bbb8d9a"

    files_to_sync = [
        ("Poster_VRPTW_NCKHSV_2026.png", png_file),
        ("Poster_VRPTW_NCKHSV_2026.pdf", pdf_file),
        ("Poster_VRPTW_NCKHSV_2026_A1.pptx", pptx_a1),
        ("Poster_VRPTW_NCKHSV_2026.pptx", pptx_169),
    ]

    for fname, src in files_to_sync:
        p_dst = os.path.join(parent_dir, fname)
        shutil.copy2(src, p_dst)
        print(f"Synced {fname} -> {p_dst}")

        if os.path.exists(artifact_dir):
            a_dst = os.path.join(artifact_dir, fname)
            shutil.copy2(src, a_dst)
            print(f"Synced {fname} -> {a_dst}")

if __name__ == "__main__":
    build_poster()
