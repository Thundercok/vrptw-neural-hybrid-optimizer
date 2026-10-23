# Bảng bằng chứng và xử lý 23 ý phản biện

Mốc: 2026-10-19. Đối chiếu đúng **6 ý R1 + 5 ý R2 + 12 ý R3** trong
[bản chép nhận xét gốc](reviewer_comments_20261016.md). Đây là kế hoạch xử lý
nội bộ, chưa phải thư trả lời đã hoàn thành, không xác nhận đã sửa manuscript
và không cho phép khởi chạy sweep.

**Chưa ý nào đóng hoàn toàn.** `Một phần` nghĩa là có tài liệu/code/artifact
hữu ích nhưng chưa đủ đáp ứng phản biện; `Còn thiếu` nghĩa là cần bổ sung bằng
chứng hoặc thu hẹp claim. P0 ảnh hưởng trực tiếp tính hợp lệ của claim; P1 là
phần bắt buộc tiếp theo để trình bày và đánh giá đầy đủ.

Các nguồn dùng trong bảng:

- **A — Audit lịch sử:** [báo cáo](legacy_provenance_20261019.md),
  [JSON tính lại](../results/legacy_provenance_20261019_v2/summary.json) và
  [lineage Git](../results/legacy_provenance_20261019_v2/git_lineage.json).
  Arithmetic khớp headline, execution provenance còn thiếu, phụ lục không khớp.
- **B — Native hiện tại:** [certification](native_certification_20261019.md),
  [pilot 18 job](native_certification_pilot_20261019.md),
  [diagnostic cũ](native_diagnostic_20261019.md). Pilot là kiểm tra vận hành,
  không chứng minh lợi ích hiệu năng hay tính hợp lệ của dữ liệu lịch sử.
- **C — Baseline:** [OR-Tools](ortools_contract_20261018.md),
  [PyVRP](pyvrp_contract_20261018.md),
  [NeuroLKH-adapted](neurolkh_contract_20261018.md).
  Có adapter/pilot, chưa có so sánh publication đủ rộng.
- **D — Training:** [GNN mới](gnn_retraining_20261017.md),
  [protocol đang chuẩn bị](resubmission_protocol.md). Model mới có manifest;
  không phục hồi provenance training của model lịch sử.
- **E — Văn bản chưa sửa:** [manuscript](manuscript.tex) và
  [supplement](supplementary_proofs.tex). Nội dung tồn tại không tự là chứng cứ đúng.
- **F — LAC:** [probe/code identity](../results/lac_semantics_audit_20261019_v2/summary.json),
  [implementation](../src/vrptw/rl.py), [call site](../src/vrptw/solvers.py).

## Reviewer 1

| ID / mức | Concern | Bằng chứng hiện có | Còn thiếu / hành động cụ thể |
| --- | --- | --- | --- |
| R1.1 — P0, một phần | Equal wall-clock phải là cơ sở chính; 10/60/300s và dài hơn, đủ 100/200/400 | B có cert trước cutoff và 18 job ở 10s trên ba input/hai seed. E có anytime 300s nhưng ghi pre-GNN, không bao phủ 400. A chưa xác nhận effective budget cũ. | Khóa tập phân tầng hoặc full suite, seeds, horizon dài, scope đồng hồ và failure policy trước chạy. Đo fleet trước, TD có điều kiện sau; ghi capture và return riêng. Pilot ba input không thay thế yêu cầu này. |
| R1.2 — P0, một phần | Baseline classical mạnh và learning-augmented được chạy trực tiếp | C có PyVRP 0.14.1 ILS và NeuroLKH-adapted độc lập; OR-Tools cũ trong A là placeholder. | Chấp nhận precision, settings, tuning firewall, initialization, timer và seed protocol chung; kiểm tra tính đại diện của adaptation trước so sánh rộng. Không gọi PyVRP hiện tại là HGS; không gọi adapted NeuroLKH là tái lập nguyên bản. Nếu thiếu bằng chứng, giới hạn claim tương ứng và trả lời cả R3.3. |
| R1.3 — P0, còn thiếu | Tách learning khỏi GEC/SP bằng wall-clock factorial | E có ladder/LOCO nhưng budget iteration và nhiều claim chưa được provenance audit riêng. | Khai báo sáu yếu tố GEC, SP, macro DDQN, micro DDQN, LAC, GNN; kiểm tra switch thật sự độc lập và biến phụ thuộc. Chọn full factorial hoặc thiết kế giảm có contrasts/interactions ước lượng được; khóa budget/seed, ghi uncertainty và compute. Không quy toàn bộ gain cho learning. |
| R1.4 — P0, còn thiếu | Rút hoặc chứng minh bảo đảm hội tụ SA của LAC | E vẫn giữ claim. F cho thấy implementation sau warmup là threshold OR 0.05, khác công thức OR SA trong bài; có phản ví dụ cho “giữ mọi SA-approved move”. | Chốt mô tả phương pháp khớp implementation hoặc thay đổi có chủ đích bằng TDD trước chạy mới. Sau đó rút claim hội tụ nếu không có proof đúng giả thiết. Không thay ngay bằng câu yếu hơn của reviewer khi code hiện tại cũng chưa thỏa câu đó. |
| R1.5 — P0, một phần | Đơn vị thống kê và seed uncertainty; TD conditional | A tái tính mean-five 23/49/2 và conditional −1.8016%. E nêu mean-five cho headline nhưng ladder dùng median; p-values chưa tái xác minh. | Tách endpoint/aggregator từng bảng. Cần seed IDs/order và cold-start thật, không coi vị trí vector raw là seed pairing đã chứng nhận. Khóa hierarchical resampling qua instance/seed, CI và multiplicity; thêm sensitivity theo geometry group. Giữ TD matched-fleet là phân tích có điều kiện. |
| R1.6 — P0, một phần | Giới hạn claim GNN và lexicographic guarantee | D chỉ có validation-teacher recall của model mới; B không cho thấy stable GNN benefit. E có proof penalty trên candidate/route-pool space. | Báo recall và routing outcome theo size, failure/pruning risk và uncertainty; 400 là size shift. Giải thích penalty chỉ sắp thứ tự trong feasible candidate/pool space, không chứng minh global VRPTW optimum. Không suy lợi ích GNN từ tính đúng của penalty. |

## Reviewer 2

| ID / mức | Concern | Bằng chứng hiện có | Còn thiếu / hành động cụ thể |
| --- | --- | --- | --- |
| R2.1 — P1, còn thiếu | Fundamental innovation ngoài việc ghép kỹ thuật | E mô tả hierarchy và integration; chưa đủ chứng cứ nhân quả cho incremental learning benefit. | Lập contribution map: thành phần kế thừa, thiết kế phối hợp cụ thể, giả thuyết kiểm chứng và kết quả hỗ trợ. Viết novelty theo bằng chứng sau R1.3/R2.4; không tuyên bố phát minh lại kỹ thuật có sẵn hoặc mặc định phải có định lý mới. |
| R2.2 — P0, còn thiếu | Aggregated SMDP có Markov không; guarantee/error bound | E có phần state/SMDP và supplement suy từ Bellman contraction sang neural DDQN hội tụ Q*. Audit này chưa xác minh theorem. | Kiểm tra state có đủ thông tin cho transition/reward khi route, replay, online weights, temperature thay đổi. Nêu approximation/partial observability nếu chưa chứng minh sufficient state; không coi contraction tabular là proof hội tụ neural replay/DDQN. Chỉ đưa bound nếu chứng minh được với giả thiết đúng; nếu không, rút claim và công khai giới hạn. |
| R2.3 — P0, còn thiếu | LAC còn bảo đảm hội tụ SA không | Cùng bằng chứng F và claim E như R1.4. | Trả lời riêng ý này, dẫn cùng sửa method/theory với R1.4. Một decision rule nhận thêm move hoặc thay SA đều không tự chứng minh định lý hội tụ. Chưa có proof trong audit này. |
| R2.4 — P0, còn thiếu | Vì sao thêm learning khi A1 có TD trung bình tốt hơn A4 | E có ladder, trộn câu chuyện fleet-first với average TD; không có wall-clock contrasts mới. | Tái phân tích A1/A4 đúng fleet-first, conditional TD và compute với nguồn rung/seed riêng; audit provenance ladder riêng, không lấy A làm chứng nhận cho ladder. Chạy contrasts sau khóa thiết kế R1.3. Nếu learning không tạo gain rõ, báo giới hạn/chi phí; không dùng TD khác fleet để biện hộ. |
| R2.5 — P0, một phần | Recall 95.8% xuống 78.2% ảnh hưởng quality/generalization | E nêu số lịch sử; D có synthetic 100/200 validation và model mới khác identity. B chỉ operational check 400. | Cần test recall/retention và routing NV/conditional TD/time với/không pruning theo size, matched compute. Không dùng validation recall hoặc smoke 400 để xác nhận generalization chất lượng; không trộn checkpoint mới với số recall lịch sử. |

## Reviewer 3

| ID / mức | Concern | Bằng chứng hiện có | Còn thiếu / hành động cụ thể |
| --- | --- | --- | --- |
| R3.1 — P1, còn thiếu | Novelty so với learning-guided ALNS | E mô tả kiến trúc nhưng chưa có contribution map đã kiểm chứng. | Dùng contribution map R2.1, đối chiếu đúng phương pháp liên quan bằng nguồn gốc và contrasts. Trả lời riêng reviewer này; novelty không chỉ là danh sách module. |
| R3.2 — P0, còn thiếu | Ablation đủ plateau, micro, LAC, GNN, GEC, SP | E có LOCO/ladder iteration-matched; B không phải ablation study. | Thiết kế chung R1.3 phải tách đủ sáu module; ghi điều kiện phụ thuộc, hiệu ứng chính/interactions được ước lượng, cold starts và wall-clock cho mỗi cell. Không coi một `use_rl=False` là tách được mọi module học. |
| R3.3 — P0, một phần | So sánh fair về compute, stopping, hardware, tuning | B/C có timing/certification contract, source snapshots và pilot nhỏ; precision/baseline representativeness vẫn mở. | Khóa protocol thống nhất và budget; ghi CPU/thread/env, run-order blocks, tuning data và setup/inference cost. Kết hợp R1.1/R1.2; báo tất cả thất bại, không đổi timing gate hoặc chọn lại settings theo test score. |
| R3.4 — P0, một phần | Training/testing, unseen distributions/windows/sizes | D có 48 synthetic train/12 validation, 74 test identities, kiểm collision và 12 geometry groups. Chỉ một training seed và không có historical-model consumed-data manifest. | Phân biệt GNN offline với macro/micro/LAC học online: reset weights/replay/archive và seed ở mỗi run; làm rõ controller nào thực sự pretrained. Nêu validation-only selection, test exposure qua các pilot và 400 OOD; không khái quát split GNN thành proof cho mọi controller. |
| R3.5 — P0, một phần | LAC labels horizon 80; so với SA và strategy khác | F: `decide` tăng counter, enqueue feature/best.cost; `observe` mature sau 80 decision calls, label khi best.cost giảm. Config warmup 300 decision calls. | Viết đúng đơn vị horizon/warmup, labels, online buffer, imbalance và giới hạn credit assignment. Chốt semantics F trước so sánh SA, fixed/random acceptance và predictive LAC; acceptance-volume control giúp tách dự đoán khỏi số move được nhận. Best-cost label chưa là chứng cứ causal hoặc fleet-first delayed gain. |
| R3.6 — P0, một phần | Pruning có loại insertion hứa hẹn không | D có missed teacher edges/validation diagnostics; B không cho stable GNN gain. | Ghi reference-edge recall, candidate retention, fallback policy và paired routing effect tại equal compute; test hại do pruning, không chỉ độ nhanh. Teacher edges không phải optimal edges và edge retention không phải số move được duyệt. Liên kết R2.5. |
| R3.7 — P1, một phần | Điều kiện/data structure cho insertion check O(1) | `heuristics.py` có timing/slack arrays, `_insert_feasible_numba` truy cập prefix/suffix; precompute có loop theo route. E có proof slack cần đối chiếu chi tiết. | Chỉ claim O(1) cho một query với cache hợp lệ, prefix khả thi và capacity check được xử lý; rebuild/update sau route mutation là O(m), scan nhiều vị trí không O(1). Kiểm tra waiting, service, depot return, insertion cuối và cache invalidation; chưa xác nhận toàn bộ proof supplement ở bước này. |
| R3.8 — P0, còn thiếu | Tổng compute theo DDQN, GNN, GEC, SP | B có solve/return measurements và profile cũ với call-tree anomaly được công khai. | Instrument phase timing theo clock chung, tránh double count, kiểm tổng/overlap và overhead; tách instrumented profile khỏi unprofiled quality study. Không dùng profile lỗi làm exact decomposition; inference/training/certification và setup phải có scope rõ. |
| R3.9 — P1, một phần | Fleet-first được thực thi xuyên search thế nào | `Plan.dominates` so NV trước TD; B certifier chỉ promote feasible lexicographic incumbent. E có scalar/pool ordering. | Phân biệt current search state có thể tăng NV/tạm infeasible với incumbent trả về; map comparator, acceptance, reward, SP và return. Kiểm tra bound của từng scalarization đúng phạm vi; giải thích heuristic không bảo đảm tìm fleet tối ưu toàn cục. |
| R3.10 — P0, một phần | Variability và significance qua independent runs | A có năm giá trị từng native row và population std khớp; không có seed labels/cold-start proof. B có hai seed nhưng chỉ operational pilot. | Kế hoạch seed-level uncertainty và hierarchical/paired inference theo R1.5 với dữ liệu execution có provenance; khớp family/geometry dependence và multiple contrasts. Không công bố p-value mới hoặc significance từ pilot nhỏ. |
| R3.11 — P0, một phần | Feasibility sau complex moves/SP; claim 100% | B kiểm exact cover/capacity/windows/depot và pre-cutoff snapshot; 55 certifier tests, pilot độc lập 18/18. A chỉ có OnTime aggregate. | Mô tả move checks, cache invalidation, SP coverage và final original-space validation, với failures được giữ. Chứng nhận mới chỉ áp dụng đúng snapshot/run được lưu, không chứng nhận ngược 100% feasibility của lịch sử hoặc hard return deadline. |
| R3.12 — P0, còn thiếu | Learning vs GEC/SP attribution | Cùng gap thực nghiệm như R1.3/R3.2. | Báo riêng heuristic gain, learning incremental gain và interactions tại equal compute; nếu evidence yếu/non-significant, diễn giải đúng uncertainty thay vì biến tổng gain thành DDQN gain. Trả lời riêng ý này với bảng contrasts chung. |

## Thứ tự công việc và điều kiện đóng

1. **Đã làm ở bước này:** chép đủ comment; audit aggregate/Git; lưu diff 74 dòng;
   xác nhận mismatch LAC bằng probe nhỏ; bảo toàn dữ liệu và source cũ.
2. **Bước kế tiếp đề xuất:** chốt semantics LAC, taxonomy claim và thiết kế
   factorial/contrasts trên giấy; xác định switch độc lập và endpoint thống kê.
   Nếu đổi runtime, dùng TDD trong một thay đổi riêng; không ghi đè pilot cũ.
3. **Trước thí nghiệm lớn:** đóng precision/baseline/protocol, nguồn dữ liệu,
   compute plan, cutoff/seed/failure policy và pilot ở các cutoff cần thiết.
   Thời lượng horizon dài và tổng compute vẫn chưa chốt; chưa launch full sweep.
4. **Sau khi có kết quả hợp lệ:** tái sinh bảng từ nguồn đã chọn, diễn giải
   đúng uncertainty và giới hạn; sau đó mới sửa manuscript và viết rebuttal.
   Đồng bộ phụ lục không phải chỉ chọn bộ số có kết quả đẹp hơn.

Một ý chỉ đóng khi có response đúng concern, action thực hiện, evidence có
identity và vị trí sửa thật sự trong bài. Các ý trùng vẫn phải có từng mục trả
lời riêng. Không dùng thì quá khứ “we have revised/evaluated” cho việc còn dự kiến.

Yêu cầu của editor từ thư đã cung cấp: response theo concern/response/action,
PDF highlight tất cả thay đổi, clean source và PDF; chỉ dùng byline form nếu
thực sự đổi tác giả. Chưa tạo bộ nộp, sửa authorship hoặc gửi bất kỳ thư nào.
