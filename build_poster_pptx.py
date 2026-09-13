#!/usr/bin/env python3
"""
Populate the official TDTU PowerPoint template: Template poster NCKHSV.pptx
Generates: Poster_NCKHSV_2026_HuynhNhatHuy.pptx
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt, Mm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def main():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_pptx = os.path.join(base_dir, "Template poster NCKHSV.pptx")
    output_pptx = os.path.join(base_dir, "Poster_NCKHSV_2026_HuynhNhatHuy.pptx")
    figs_dir = os.path.join(base_dir, "docs", "figures")
    
    arch_img = os.path.join(figs_dir, "poster_architecture.png")
    conv_img = os.path.join(figs_dir, "anytime_convergence.png")
    route_img = os.path.join(figs_dir, "route_RC101.png")

    prs = Presentation(template_pptx)
    slide = prs.slides[0]

    # Color Palette
    c_navy = RGBColor(16, 37, 66)
    c_gold = RGBColor(217, 119, 6)
    c_teal = RGBColor(13, 148, 136)
    c_text = RGBColor(30, 41, 59)
    c_dark = RGBColor(15, 23, 42)
    c_sub = RGBColor(71, 85, 105)

    # 1. Update Title & Author shapes
    # Shape 0: NGHIÊN CỨU KHOA HỌC SINH VIÊN
    # Shape 4: Khoa Công nghệ Thông tin
    # Shape 1: Đề tài
    # Shape 2: SVTH / GVHD
    # Shape 3: Ngành / Bộ môn
    
    for s in slide.shapes:
        if not s.has_text_frame:
            continue
        text = s.text_frame.text.strip()
        if "Đề" in text and "tài" in text:
            tf = s.text_frame
            tf.clear()
            p = tf.paragraphs[0]
            p.text = "TỐI ƯU HÓA BÀI TOÁN ĐỊNH TUYẾN PHƯƠNG TIỆN CÓ KHUNG THỜI GIAN"
            p.font.name = "Montserrat"
            p.font.size = Pt(17)
            p.font.bold = True
            p.font.color.rgb = RGBColor(255, 255, 255)
            
            p2 = tf.add_paragraph()
            p2.text = "BẰNG THUẬT TOÁN TÌM KIẾM LÂN CẬN LỚN THÍCH ỨNG LAI HỌC TĂNG CƯỜNG SÂU"
            p2.font.name = "Montserrat"
            p2.font.size = Pt(14)
            p2.font.bold = True
            p2.font.color.rgb = RGBColor(251, 191, 36) # Gold accent
            
        elif "SVTH" in text and "GVHD" in text:
            tf = s.text_frame
            tf.clear()
            p = tf.paragraphs[0]
            p.text = "SVTH: Huỳnh Nhật Huy (MSSV: 523C0012)        GVHD: TS. Hồ Thị Linh"
            p.font.name = "Montserrat"
            p.font.size = Pt(11)
            p.font.bold = True
            p.font.color.rgb = RGBColor(255, 255, 255)
            
        elif "Sinh" in text and "ngành" in text:
            tf = s.text_frame
            tf.clear()
            p = tf.paragraphs[0]
            p.text = "Sinh viên ngành: Khoa học Máy tính                 Nhóm nghiên cứu: NLP-KD, Khoa Công nghệ Thông tin"
            p.font.name = "Montserrat"
            p.font.size = Pt(10)
            p.font.color.rgb = RGBColor(226, 232, 240)

    # 2. Add Content Box for Section 1: GIỚI THIỆU
    # Position under Shape 6 (left=45.9mm, top=228mm, width=205mm, height=100mm)
    s1_box = slide.shapes.add_textbox(Mm(45.9), Mm(228), Mm(205), Mm(100))
    tf1 = s1_box.text_frame
    tf1.word_wrap = True
    
    def add_p(tf, bold_txt, norm_txt, pt_sz=8.5, space=2):
        p = tf.add_paragraph() if tf.paragraphs[0].text else tf.paragraphs[0]
        p.space_after = Pt(space)
        r1 = p.add_run()
        r1.text = "• " + bold_txt + " "
        r1.font.name = "Arial"
        r1.font.bold = True
        r1.font.size = Pt(pt_sz)
        r1.font.color.rgb = c_navy
        
        r2 = p.add_run()
        r2.text = norm_txt
        r2.font.name = "Arial"
        r2.font.size = Pt(pt_sz)
        r2.font.color.rgb = c_text

    add_p(tf1, "Bài toán VRPTW:", "Định tuyến đội xe phục vụ tập khách hàng có vị trí, tải trọng và khung thời gian giao hàng [e_i, l_i], thỏa mãn sức chứa Q và bảo toàn luồng depot.")
    add_p(tf1, "Hàm mục tiêu:", "Tối ưu hóa từ điển phân cấp (Lexicographic): min f(s) = M · N_V(s) + D_T(s) với M = 10⁵ (ưu tiên tối thượng giảm số xe, sau đó giảm tổng quãng đường).")
    add_p(tf1, "Hạn chế ALNS cổ điển:", "Phụ thuộc vào cơ chế roulette-wheel ngẫu nhiên tĩnh, dễ sa lầy tại các vùng bình nguyên (search plateaus).")
    add_p(tf1, "Hạn chế End-to-End DRL:", "Mô hình nơ-ron thuần túy dễ vi phạm khung thời gian khi gặp phân phối kích thước mở rộng (out-of-distribution).")

    # 3. Add Content Box for Section 2: TẬP DỮ LIỆU
    # Position under Shape 8 (left=262.3mm, top=228mm, width=285mm, height=100mm)
    # Add a compact table for benchmarks
    s2_table_shape = slide.shapes.add_table(4, 4, Mm(262.3), Mm(228), Mm(284.6), Mm(45))
    table = s2_table_shape.table
    table.columns[0].width = Mm(55)
    table.columns[1].width = Mm(35)
    table.columns[2].width = Mm(55)
    table.columns[3].width = Mm(139.6)
    
    headers = ["Bộ Thực Nghiệm", "Số Bài", "Quy Mô", "Đặc Trưng Không-Thời Gian"]
    rows_data = [
        ["Solomon-100", "56", "100 khách", "6 họ: Cụm (C1,C2), Ngẫu nhiên (R1,R2), Hỗn hợp (RC1,RC2)"],
        ["Homberger-200", "60", "200 khách", "10 bài toán × 6 họ cấu trúc địa hình không gian"],
        ["Homberger-400", "60", "400 khách", "Quy mô lớn thử thách giới hạn tìm kiếm thuật toán"]
    ]
    
    for c_idx, h in enumerate(headers):
        cell = table.cell(0, c_idx)
        cell.text = h
        for p in cell.text_frame.paragraphs:
            p.font.name = "Arial"
            p.font.bold = True
            p.font.size = Pt(8)
            p.font.color.rgb = RGBColor(255, 255, 255)
            p.alignment = PP_ALIGN.CENTER
        cell.fill.solid()
        cell.fill.fore_color.rgb = c_navy

    for r_idx, row in enumerate(rows_data):
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx + 1, c_idx)
            cell.text = val
            for p in cell.text_frame.paragraphs:
                p.font.name = "Arial"
                p.font.size = Pt(7.5)
                p.font.color.rgb = c_text
                if c_idx < 3:
                    p.alignment = PP_ALIGN.CENTER

    # Additional text under table
    s2_txt = slide.shapes.add_textbox(Mm(262.3), Mm(275), Mm(284.6), Mm(50))
    tf2 = s2_txt.text_frame
    tf2.word_wrap = True
    add_p(tf2, "Quy chuẩn Cold-Start độc lập:", "Bộ nhớ đệm được làm sạch hoàn toàn giữa các lượt chạy. Mọi bộ giải bắt đầu độc lập từ nghiệm tham lam ban đầu (100% tái lập, zero rò rỉ bộ nhớ).", pt_sz=8)
    add_p(tf2, "Domain Randomization:", "Huấn luyện trên 20-100 khách và chuyển giao zero-shot sang Homberger 200-400.", pt_sz=8)

    # 4. Add Content Box for Section 3: PHƯƠNG PHÁP THỰC HIỆN
    # Position under Shape 7 (left=45.9mm, top=350mm, width=500.5mm, height=225mm)
    s3_desc = slide.shapes.add_textbox(Mm(45.9), Mm(348), Mm(500.5), Mm(30))
    tf3 = s3_desc.text_frame
    tf3.word_wrap = True
    add_p(tf3, "Kiến trúc 3 Tầng Phối Hợp:", "Tầng 1 (Macro DDQN, 7 chế độ SMDP) điều phối chiến lược khai phá/tăng cường • Tầng 2 (Micro DDQN 65 cặp toán tử + Learned Acceptance lookahead H=80) • Tầng 3 (Granular ALNS O(1) slack check + Contrastive GNN tỉa 98.7% cạnh + Set Partitioning MILP qua HiGHS cutoff 4.0s).", pt_sz=8.5, space=1)

    # Insert Hero Architecture Image
    if os.path.exists(arch_img):
        slide.shapes.add_picture(arch_img, Mm(55), Mm(372), width=Mm(482))

    # 5. Add Content Box for Section 4: KẾT QUẢ THỰC NGHIỆM
    # Position under Shape 9 (left=51.9mm, top=598mm, width=335mm, height=135mm)
    # Add Results Table
    s4_table_shape = slide.shapes.add_table(5, 5, Mm(51.9), Mm(597), Mm(210), Mm(48))
    t4 = s4_table_shape.table
    t4.columns[0].width = Mm(45)
    t4.columns[1].width = Mm(42)
    t4.columns[2].width = Mm(35)
    t4.columns[3].width = Mm(44)
    t4.columns[4].width = Mm(44)
    
    t4_headers = ["Tập Dữ Liệu", "Thuật Toán", "Số Xe NV", "Quãng Đường TD", "Ý Nghĩa Thống Kê"]
    t4_rows = [
        ["Solomon-100", "ALNS-Base", "7.54", "1017.31", "Baseline"],
        ["(56 bài toán)", "Hybrid-DDQN", "7.34", "1017.82", "p = 0.00127 (Thắng)"],
        ["Homberger-200", "ALNS-Base", "11.87", "3009.91", "Baseline"],
        ["(60 bài toán)", "Hybrid-DDQN", "11.58", "2844.73 (-165.2 km)", "p = 1.34×10⁻⁹ (Vượt trội)"]
    ]
    
    for c_idx, h in enumerate(t4_headers):
        cell = t4.cell(0, c_idx)
        cell.text = h
        for p in cell.text_frame.paragraphs:
            p.font.name = "Arial"
            p.font.bold = True
            p.font.size = Pt(7.5)
            p.font.color.rgb = RGBColor(255, 255, 255)
            p.alignment = PP_ALIGN.CENTER
        cell.fill.solid()
        cell.fill.fore_color.rgb = c_navy

    for r_idx, row in enumerate(t4_rows):
        for c_idx, val in enumerate(row):
            cell = t4.cell(r_idx + 1, c_idx)
            cell.text = val
            for p in cell.text_frame.paragraphs:
                p.font.name = "Arial"
                p.font.size = Pt(7)
                if "Hybrid" in row[1] and (c_idx == 2 or c_idx == 3):
                    p.font.bold = True
                    p.font.color.rgb = c_teal
                else:
                    p.font.color.rgb = c_text
                p.alignment = PP_ALIGN.CENTER

    # Insert Convergence plot next to results table
    if os.path.exists(conv_img):
        slide.shapes.add_picture(conv_img, Mm(265), Mm(597), width=Mm(120))

    # Bullets below table in Section 4
    s4_txt = slide.shapes.add_textbox(Mm(51.9), Mm(648), Mm(335), Mm(45))
    tf4 = s4_txt.text_frame
    tf4.word_wrap = True
    add_p(tf4, "100% Bảo Toàn Khả Thi:", "0 vi phạm trên toàn bộ 580 lần chạy thực nghiệm (176 bài toán × 5 seeds).", pt_sz=7.5, space=1)
    add_p(tf4, "Ưu thế Quy mô 200:", "Cùng hội tụ về số xe sàn, Hybrid-DDQN giảm quãng đường từ 1.75% đến 4.07% khi khớp số xe.", pt_sz=7.5, space=1)
    add_p(tf4, "Đột phá Quy mô 400:", "Khắc phục hiện tượng dừng sớm của ALNS-Base, dẫn trước 0.70-0.80 xe trên c2_4_1 (p=0.0078) và r2_4_1 (p=0.0156).", pt_sz=7.5, space=1)

    # 6. Add Content Box for Section 5: KẾT LUẬN & ĐÓNG GÓP
    # Position under Shape 11 (left=400.2mm, top=598mm, width=136mm, height=135mm)
    s5_txt = slide.shapes.add_textbox(Mm(398.1), Mm(597), Mm(140), Mm(135))
    tf5 = s5_txt.text_frame
    tf5.word_wrap = True
    add_p(tf5, "Đóng góp lý thuyết:", "Khung Tri-Level hài hòa giữa năng lực khái quát hóa của RL và độ chuẩn xác của MILP.", pt_sz=7.5, space=1.5)
    add_p(tf5, "Đóng góp thực nghiệm:", "Minh bạch hóa giao thức Cold-Start độc lập và cung cấp bộ dữ liệu đối chuẩn tin cậy.", pt_sz=7.5, space=1.5)
    add_p(tf5, "Công bố quốc tế:", "Bản thảo nghiên cứu toàn văn gửi đăng tạp chí uy tín IEEE Access (SCIE, Q1, IF 3.4).", pt_sz=7.5, space=1.5)
    add_p(tf5, "Tái lập khoa học:", "Mã nguồn mở và toàn bộ trọng số mô hình được cung cấp công khai.", pt_sz=7.5, space=1.5)

    prs.save(output_pptx)
    print(f"Generated official PPTX poster successfully: {output_pptx}")

if __name__ == "__main__":
    main()
