# Audit nguồn số liệu lịch sử — 2026-10-19

**Headline có thể tái tính; điều kiện thực thi lịch sử chưa được chứng nhận.**
Audit nối được toàn bộ CSV chính với năm checkpoint trong Git, nhưng không tìm
được bằng chứng gắn từng lượt chạy với source/config/seed/model đã thực sự dùng.
Không thay headline bằng số cộng từ phụ lục, và chưa coi CSV này là kết quả
cold-start/equal-wall-clock đã được xác minh để làm cơ sở chính cho resubmission.

Đây là bước kiểm kê bằng chứng, dùng workflow `data:validate-data`. Chỉ thêm
script audit, bản chép nhận xét, báo cáo và artifact mới. Không chạy solver,
training hoặc sweep; không sửa manuscript, bảng cũ hay solver. Ba probe LAC
bên dưới chỉ gọi hàm quyết định với prediction được tiêm cố định.

## Số liệu tái tính được

Nguồn: [summary.json](../results/legacy_provenance_20261019_v2/summary.json).
CSV chính là `results/ultimate-publication-suite/combined_clean.csv`, SHA-256
`272c5c6c51d3e435f4c90cf4853e03fcc1753b45960bc4eeccb5908540bb0fc1`.

Tập 74 được lọc tường minh trong
[selection.json](../results/legacy_provenance_20261019_v2/selection.json):
56 Solomon, 12 Homberger-200 (mỗi family lấy `_2_1`, `_2_5`), sáu
Homberger-400 (mỗi family lấy `_4_1`). Full là **GNN-Hybrid-DDQN**, so với
**ALNS-Base**; `Hybrid-DDQN` là nhánh khác và không được thay vào phép tính này.

| Phép tính | CSV chính | Bảng phụ lục đang in |
| --- | ---: | ---: |
| Thắng / hòa / thua về NV trung bình từng instance | 23 / 49 / 2 | 31 / 40 / 3 |
| Số instance có NV trung bình bằng nhau | 49 / 74 | 40 / 74 |
| Trung bình gap TD từng instance trong nhóm đó | −1.801632% | −3.733038% |

Gap là `mean(100 * (TD_full - TD_base) / TD_base)` trên nhóm có NV trung bình
bằng nhau; không phải ratio của tổng TD và không phải so sánh fleet từng seed.
Dùng trung bình tính từ các vector raw đã lưu cho kết quả 23/49/2 và
−1.801637%; khác biệt nhỏ do làm tròn. Chưa tái kiểm định các p-value của bài.

CSV có 1,056 khóa instance/algorithm duy nhất: 176 instance × sáu nhãn.
Năm nhánh native có 880 dòng, mỗi dòng lưu năm NV và năm TD. Tất cả mean và
**population standard deviation** khớp vector raw trong sai số làm tròn
0.005051; kiểm tra này không xác nhận seed hay tính độc lập của lượt chạy.
Phụ lục gọi một số độ lệch chuẩn là sample standard deviation; hai định nghĩa
phải được phân biệt khi chuẩn hóa lại báo cáo, không tự đổi nhãn dữ liệu cũ.

**176 dòng OR-Tools đều trống objective/raw/OnTime và có Time_s=0.** Đây là
dòng thiếu kết quả, không phải bằng chứng 880 lượt OR-Tools đã hoàn tất, cũng
không đủ để kết luận đã có 176 lần chạy lỗi. Tuyên bố lưu trữ “5,280 runs,
zero failures” trong handoff cũ không được CSV này hỗ trợ. Có 4,400 cặp NV/TD
được ghi cho native; số cặp được ghi không chứng nhận số execution độc lập.

`OnTime=100.0` của các dòng native không thay thế route audit về capacity,
exact cover và giờ quay về depot. CSV không chứa route từng seed để kiểm tra
độc lập những điều kiện đó.

## Git nối được gì, chưa nối được gì

[git_lineage.json](../results/legacy_provenance_20261019_v2/git_lineage.json)
ghi blob, SHA-256, lịch sử object và các bản source được phục hồi.

| Mốc lưu trữ/source | Commit | Kết quả kiểm tra |
| --- | --- | --- |
| Năm checkpoint hiện tại đã xuất hiện | `e47b4b77f871a2b6994bd30133400b68bf4c0a53` — 24-Aug-2026 | Từng byte khớp năm checkpoint local và tag archive |
| Sửa vòng benchmark sang `init=None` | `08479fbfb607b0cab888920ccf395b858d881b22` — 25-Aug-2026 | Source trước/sau khác về khởi tạo độc lập |
| Tag `research-history-before-cleanup` | `d1a48ecc312f1d6c2a2438dc4ea7b68992b46d99` | Suite trong tag chỉ có năm checkpoint |
| Combined CSV được lưu trong merge | `39a8cfe534d5a7a161df8d035ef33f49faef3024` — 09-Oct-2026 | Blob combined hiện tại đã có ở mốc này |

Ngày commit là mốc lưu artifact/source trong Git, không phải ngày solve hoặc
bằng chứng source nào đã thực thi. Trong lịch sử object reachable đã kiểm tra,
`e47b4b7` là mốc lưu sớm nhất của đúng các blob checkpoint hiện tại.

Hợp của năm checkpoint có đúng 1,056 khóa và khớp **mọi trường trong 17 cột**
của combined. Các file `benchmark_clean.csv` local cũng khớp toàn bộ parsed
rows với checkpoint tương ứng; bốn cặp khác byte định dạng, một cặp giống byte.
Vì vậy không được dùng bất đồng byte này làm bằng chứng khác số liệu.

Source benchmark tại mốc lưu checkpoint còn có:

```python
init = best_overall.copy() if best_overall is not None else _diversified_init(i, inst, archive, cfg)
```

Nó có thể truyền nghiệm tốt của lượt trước sang lượt sau; `_diversified_init`
còn có nhánh lấy elite archive. Commit ngày hôm sau mới thay bằng `init=None`.
Đây là **bằng chứng source trái với điều kiện cold-start được mô tả**, nhưng
không chứng minh các tiến trình tạo CSV chắc chắn đã chạy source đó: không có
snapshot source/config/runtime gắn với từng lượt. Source mới không chứng nhận
ngược điều kiện của kết quả cũ.

Launcher lưu cùng giai đoạn cũng không khớp shape kết quả: năm thuật toán
(không có nhãn GNN riêng), Solomon bảy lượt/5,000 iterations, H200 năm/800,
H400 ba/600 trên 24 instance. CSV lại có sáu nhãn, năm giá trị cho mọi dòng
native và 60 H400. Có thể từng có lệnh chạy khác; chưa phục hồi được lệnh đó.
Không được suy effective config từ default hoặc từ launcher không khớp.

Seed default 42 và biểu thức `cfg.seed+i` chỉ gợi ý 42–46; CSV không ghi seed
IDs/order để xác nhận cặp seed. Tương tự, đường dẫn model hay checkpoint hiện
còn không chứng minh model hash đã được load trong những execution cũ.

74 input hiện tại giống byte file cùng đường dẫn ở `e47b4b7`, được ghi trong
[current_input_identity.json](../results/legacy_provenance_20261019_v2/current_input_identity.json).
Điều này xác nhận identity file lưu, không xác nhận input một tiến trình cũ đã đọc.

## Phụ lục chưa có nguồn được xác nhận

[appendix_differences.csv](../results/legacy_provenance_20261019_v2/appendix_differences.csv)
liệt kê đủ 74 dòng: **56 dòng Full và 51 dòng ALNS** khác CSV chính về NV hoặc TD.

| Instance | ALNS NV trong cả hai nguồn | Full NV ở CSV / phụ lục | Full TD ở CSV / phụ lục |
| --- | ---: | ---: | ---: |
| RC1_2_1 | 19.0 | 18.6 / 19.2 | 3961.24 / 3637.12 |
| RC2_4_1 | 12.8 | 12.6 / 13.0 | 6747.51 / 6786.83 |

Không so TD giữa hai phương pháp khi fleet khác nhau. Hai ví dụ trên chỉ chỉ
ra identity kết quả và kết luận fleet thay đổi giữa các nguồn, không đánh giá
phương pháp nào tốt hơn bằng TD.

Đã quét 137 CSV trong tag archive; 131 có schema aggregate cần thiết. Không
tìm thấy cặp Full NV/TD đang in của hai ví dụ trên ở các nhãn hybrid đủ điều
kiện đã kiểm tra. Chi tiết ở
[appendix_archive_search.json](../results/legacy_provenance_20261019_v2/appendix_archive_search.json).
Một số dòng khác có giá trị trùng ở nhiều bản backup; trùng aggregate không
xác định duy nhất nguồn execution. Phạm vi tìm kiếm này không chứng minh dữ
liệu gốc chưa từng tồn tại ở nơi khác. Route của CSV cũ hơn cũng không được
thế vào năm vector hiện tại nếu không có identity khớp.

## LAC: code và mô tả cần đối chiếu trước khi viết trả lời

Reviewer R1.4/R2.3 phản biện quy tắc trong bài `LAC OR SA`. Kiểm tra thêm code
cho thấy có khác biệt ngay cả trước khi bàn đến định lý hội tụ:

- Source hiện tại và tag archive: sau warmup dùng prediction vượt threshold
  **hoặc xác suất cố định 0.05**; không OR với xác suất SA của move đó.
- Source `e47b4b7`: sau warmup lấy mẫu với xác suất prediction `p`.
- Call site hiện tại nhận trực tiếp quyết định từ `lac.decide`; không OR thêm
  SA ở bên ngoài nhánh đó. Warmup dùng SA; nhánh không bật LAC cũng dùng SA.

[Ba probe đã lưu](../results/lac_semantics_audit_20261019_v2/summary.json)
dùng đúng method hiện tại với prediction cố định: tại bước LAC 300,
`metro=0.9, p=0.1, tau=0.5, u=0.1` cho LAC reject trong khi phép lấy mẫu SA
`u < metro` sẽ accept. Probe warmup accept và predictive rescue cũng khớp code.
Đây là phản ví dụ cho tính chất “giữ mọi bước SA chấp nhận” của implementation
hiện tại, không phải đo chất lượng routing hoặc xác định code đã chạy lịch sử.

`lac_horizon=80` và warmup 300 được đếm bằng số lần gọi `decide()`, không phải
tất cả vòng ALNS. Nhãn hiện tại so sánh `best.cost` khi enqueue và khi mature;
đây là nhãn delayed best-distance improvement, chưa chứng minh tác động nhân quả
của move hay delayed lexicographic improvement. Cần giải thích đúng hoặc thay
đổi có chủ đích bằng TDD trong bước riêng. Chưa sửa thuật toán trong audit này.

## Hướng xử lý sau audit

[Bảng 23 ý](resubmission_evidence_matrix_20261019.md) phân biệt bằng chứng đã có
với phần còn thiếu. Không đánh dấu ý nào là đã giải quyết hoàn toàn chỉ vì đã
viết bảng hoặc pilot vận hành pass.

Ưu tiên tiếp theo là chốt semantics LAC và thiết kế factorial/contrasts, scope
claim, baseline và thống kê bằng văn bản trước khi chi compute. Kết quả lịch sử
giữ vai trò dữ liệu tái tính có caveat; chỉ nâng lên bằng chứng thực nghiệm đã
chứng nhận nếu phục hồi được log source/config/seed/model/route phù hợp. Nếu
không, cần thí nghiệm mới theo protocol đã khai báo để hỗ trợ claim chính.
Chưa tự động chọn giữa giữ nguyên implementation và đổi sang `SA OR LAC`,
vì đó là thay đổi phương pháp có thể làm đổi kết quả.

## Tái kiểm tra và bảo toàn

Script stdlib-only:
[audit_legacy_provenance.py](../scripts/audit_legacy_provenance.py).
Chạy lại cần chỉ định **thư mục mới**, không ghi đè audit đã lưu:

```sh
.venv/bin/python scripts/audit_legacy_provenance.py --output-dir /tmp/vrptw-new-legacy-audit
```

Bản source của script, source Git phục hồi và manifest hash được giữ trong
thư mục audit v2. Lần đầu dừng ở giả định so sánh byte clean/checkpoint được
giữ riêng trong `results/legacy_provenance_20261019/`; chưa xuất kết quả audit.
Probe LAC đầu tiên dừng ở giả định nhầm rằng hai phiên bản archive có cùng
rule; source và trạng thái được giữ trong `results/lac_semantics_audit_20261019/`.
Các bản v2 hoàn tất sau khi phân biệt đúng dữ liệu/semantics; không có lần solve
nào bị loại hoặc chạy lại trong công việc này.

Kiểm tra cuối: audit chạy lại vào thư mục tạm mới cho artifact giống byte bản
v2; cách tính headline độc lập cũng cho cùng kết quả. Ba probe LAC pass; Ruff,
format check và `git diff --check` pass. Bản chép có đủ 23 ID duy nhất, matrix
đủ 23 dòng tương ứng và các link local hợp lệ. Hash của **1,966 file cũ** trong
docs/results/checkpoints không đổi, và diff của **13 file tracked đã sửa từ
trước** giống byte snapshot đầu bước này. Không chạy lại full test suite vì
không đổi runtime; kết quả 347 tests của bước certification trước được giữ
đúng phạm vi source đã ghi, không trình bày như lần test mới.

Biên bản kiểm tra và hash bảo toàn được lưu tại
[verification.json](../results/legacy_review_readiness_20261019/verification.json).
