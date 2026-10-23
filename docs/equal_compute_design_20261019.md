# Thiết kế equal-compute và ablation — 2026-10-19

**Đã đóng băng một đề xuất có thể kiểm tra; chưa có kế hoạch chạy được phép
launch.** [design.json](../results/ablation_design_20261019/design.json) ghi
`launch_ready=false`, mọi job có `execution_binding=null`. Tool chỉ lập lịch,
kiểm hash và audit switch; không có executor hoặc tùy chọn `--launch`.

Đây là bước tiếp sau [LAC SA OR predictive](lac_sa_contract_20261019.md), phục vụ
R1.1–R1.3/R1.5, R2.4 và R3.2–R3.6/R3.8–R3.12. Các nhận xét chưa được coi là
đã giải quyết chỉ vì đã viết protocol. Không sửa runtime, manuscript, kết quả,
checkpoint hoặc tài liệu cũ trong bước này.

## Phát hiện phải sửa trước khi chạy

[switch_audit.json](../results/ablation_design_20261019/switch_audit.json) lưu
class/config thực tế, constructor probes và 21 call site kèm điều kiện AST.
Không có lời gọi `solve()`; một dispatch helper được thay bằng stub để kiểm tra
guard, không gọi MILP. Đây chưa phải audit động bao phủ mọi nhánh.

| Switch hiện tại | Bằng chứng | Hệ quả cho thiết kế |
| --- | --- | --- |
| `alns` / `gns` | Cùng class và toàn bộ requested config | Không phải hai treatment khác nhau |
| `gns_pool` / `gns_pool_lac` | Vẫn chọn ALNSSolver; vòng ALNS không gọi SP/LAC | Cumulative ladder hiện tại không hiện thực các bước như nhãn mô tả |
| `full_no_pool` | Chỉ tắt hai cờ recombine cuối; periodic/plateau còn bật. Ngay cả explicit `pool_recombine_enabled=False`, wrapper trung tâm vẫn dispatch | Chưa có SP-off toàn cục; phải kiểm tra cả main, committed search và tail |
| `RoutePool(..., limit=0)` | Constructor thay bằng 1000/1400/2000 cột ở n=100/200/400; SP time limit nội bộ là 9/14/24s | Zero requested limit không tắt pool. Config của solver chưa mô tả hết config lồng trong pool |
| `full_no_macro` | Pin mode DEFAULT; đồng thời chặn recombine/restart có macro guard | Không tách riêng giá trị của DDQN khỏi cơ hội dùng heuristic machinery |
| `full_no_gec` | Đặt depth=1 ở một routine; các ejection-chain/GES khác vẫn còn | Chưa phải recursive-ejection-off toàn cục |
| `split_enabled=False` | Main loop vẫn có thể gọi `split_ctrl.try_split`; method không đọc flag này | Một cơ chế học khác có thể hoạt động trong cell định ghi learning-off |
| `full` | Không tự load model nếu không cung cấp checkpoint | GNN-on phải bắt buộc đúng model hash; tên nhánh không chứng minh đã dùng GNN |

Giữ nguyên source hiện tại và các pilot của nó. Các sửa switch sẽ là thay đổi
riêng bằng TDD, có source identity mới; không đổi tên kết quả cũ thành ablation
hợp lệ. Đặc biệt, route feasibility và pre-cutoff certificate cũ không tự chứng
minh independence của các treatment.

## Benchmark chính được đề xuất

- Giữ đúng 74 input đã đóng băng: 56 Solomon-100, 12 GH200 (`_2_1`, `_2_5`
  của sáu family), sáu GH400 (`_4_1`). Tool kiểm lại SHA-256 từng file từ manifest
  đã audit; không chọn instance theo pilot score.
- Seeds 42–46; mỗi cutoff là một cold start riêng ở **10/60/300/900 giây**.
  900s là horizon đề xuất dài hơn, chưa phải compute đã được phê duyệt.
- Bốn comparator: Full (`F111111`), ALNS-Base, PyVRP-ILS 0.14.1 và
  NeuroLKH-adapted. Baseline precision, settings và tính đại diện của adaptation
  vẫn là gate; không gọi chúng là tái lập HGS hoặc author-original NeuroLKH.
- Chỉ 300s là cutoff chính cho inference; ba cutoff còn lại báo descriptive.
  Không lấy prefix của job 900s thay cho job 10/60/300s vì budget đổi cách phân
  bổ tail search.
- GNN mới cố định: validation-selected seed-42 checkpoint, SHA-256
  `365de53beba09097d1176a8b102ced8d6d97311f5a3ac82186b116d3290e1b97`.
  LAC là `sa_or_predictive_v1`. Không tuning threshold/settings trên test score.

## Sáu yếu tố và nghĩa chính xác cần hiện thực

Thứ tự bit trong case ID là **GEC, SP, Macro, Micro, LAC, GNN**. Tất cả case F
dùng cùng hybrid search infrastructure. `F000000` không phải ALNS-Base; các
heuristic nền còn lại phải được liệt kê và giữ giống nhau. ALNS là comparator
riêng của benchmark chính.

| Yếu tố | Mức 0 dự kiến | Mức 1 dự kiến |
| --- | --- | --- |
| GEC | Không recursive ejection trong mọi path đã inventory; giữ direct insertion/route reduction không đẩy khách khác | Recursive ejection machinery hiện tại với depth/branch limits cố định; không retune |
| SP | Không recombination/MILP và không seeding chỉ phục vụ SP ở main/committed/tail; giữ bookkeeping pool chung nếu state features cần | Route-pool recombination và SP-specific seeding có tính toàn bộ cost |
| Macro | Rule macro trên cùng mode set và cùng cơ hội heuristic; không pin DEFAULT | Macro DDQN tại eligibility chung |
| Micro | Rule micro trên cùng operator set | Micro DDQN cùng policy gate hiện tại; đây là một treatment package, chưa tách riêng gate |
| LAC | SA-only, không LAC inference/online updates | SA OR predictive rescue, warmup/horizon giữ nguyên |
| GNN | Không load/infer/use heatmap | Đúng checkpoint cố định, tính cost inference và guidance cả construction/search |

Ngoài sáu yếu tố, learned split phải tắt thật sự ở tất cả cell; không để
`use_rl=False` vô tình tắt nhiều yếu tố cùng lúc. Rule macro và rule micro phải
compose độc lập. Tất cả seed/replay/optimizer/archive khởi tạo mới cho mỗi job.
Phải ghi actual config của pool/controller và module execution counters; chỉ
ghi config outer solver hoặc tên class là chưa đủ.

Một kiểm tra không thấy module chạy trong job ngắn không chứng minh switch đã
tắt đúng. Test phải ép tới main/plateau/committed/tail hoặc boundary tương ứng,
kiểm tra không dispatch và không có update khi off, và kiểm tra đường on còn chạy.

## Ablation core: 16 cell, 17 contrasts

Ablation chọn trước 18 input: C101/C201/R101/R201/RC101/RC201, sáu family
`_2_1` và sáu family `_4_1`. Mỗi input có năm seed và independent 60/300s jobs.
Đây là tập cân bằng family/size dùng để attribution, không thay benchmark 74.

| Nhóm cell | Số cell | Mục đích |
| --- | ---: | --- |
| Tất cả off / tất cả on | 2 | Hai anchor của common hybrid infrastructure |
| Mỗi lần chỉ một yếu tố on | 6 | Đóng góp tại bối cảnh bare |
| Mỗi lần chỉ một yếu tố off | 6 | Đóng góp conditional tại bối cảnh Full |
| Chỉ GEC+SP / chỉ bốn learning factors | 2 | Hoàn thành factorial 2×2 của hai **nhóm** heuristic/learning |

[cases.csv](../results/ablation_design_20261019/cases.csv) ghi đủ từng bit;
[contrasts.json](../results/ablation_design_20261019/contrasts.json) ghi on/off
roles và trọng số. Tám pairwise contrasts tại 300s là family ablation chính:
sáu Full-minus-one, H-only vs all-off, Full vs H-only. Sáu bare effects,
hai bundle contrasts còn lại và bundle interaction là exploratory. Bundle
interaction chỉ phân tích NV ở đơn vị có đủ bốn cell hợp lệ, công khai selection;
không coi phép cộng pairwise win scores là linear factorial interaction.

**Không gọi 16 cell này là full factorial của sáu yếu tố.** Exact rational
elimination và phép kiểm NumPy độc lập cho rank **14/22** của model intercept +
sáu main effects + 15 pairwise interactions. Vì vậy không thể fit và diễn giải
riêng tất cả các hệ số đó. Thiết kế fractional cần chỉ rõ alias/model assumptions;
xem [NIST về DOE models](https://www.itl.nist.gov/div898/handbook/pri/section4/pri43.htm)
và [confounding](https://www.itl.nist.gov/div898/handbook/pri/section3/pri3343.htm).

Các lựa chọn 32/38/64 cell được định lượng trong manifest, chưa chọn để chạy.
Half32 dùng các vector có tổng bit chẵn; rank 22 chỉ áp dụng model bậc hai,
vẫn cần xét alias với higher-order effects. Half32 không chứa sáu Full-minus-one;
thêm chúng tạo 38 cell. Full64 liệt kê toàn bộ tổ hợp. Không nâng scope claim
về tương tác chỉ vì tăng số seed của một design thiếu rank.

R3.5 còn cần control để phân biệt predictive value với acceptance volume.
Core 16 cell chỉ tách SA với LAC, chưa đáp ứng toàn bộ câu hỏi đó. Một control
volume-calibrated phải dùng calibration riêng trên synthetic train/validation,
khóa trước test, kiểm cost và ghi rate thực tế; không chọn rate từ 74 test cases.
Phần bổ sung này chưa được triển khai, đưa vào compute hay coi là đã hoàn tất.

## Lịch, clock và failures

Job identity là `(input hash, case, seed, cutoff)`. Full trên tập ablation tại
60/300s được dùng chung đúng **một execution** với benchmark chính; không lấy
job khác version/timer để thay thế. Có 1.480 block input/seed/cutoff. Tool shuffle
block bằng seed 20261019, dùng cyclic case order cân bằng vị trí theo block size:
4 comparator ở block thường, 19 case ở block có ablation. Mọi thứ được ghi trước
khi có score. Executor tương lai chạy tuần tự, yêu cầu một thread; không coi đó
là đo được số thread thật của mọi backend hoặc host-load isolation.

Fresh process và empty data archive là bắt buộc. Đề xuất cũng yêu cầu
`NUMBA_CACHE_DIR` riêng, ban đầu rỗng cho từng child; compilation phát sinh sau
solve entry tính vào budget. Đây là cold-kernel-cache policy mới, cần operational
validation; không lấy timing cũ có cache khác để chứng nhận nó. Ghi cache/thread
settings, setup/model-load, solve và end-to-end riêng. Không warmup ngầm hoặc sleep
padding; cùng đầu vào/cold-start policy không có nghĩa mọi solver có cùng route
khởi tạo nội bộ. Construction riêng của từng solver phải được mô tả và tính cost.

Score cần process/result hợp lệ, identity đúng và route certificate hoàn tất
**strictly trước cutoff**, được audit độc lập trong original coordinates:
coverage, capacity, windows, depot, NV/TD. Late return không tạo incumbent mới
ở cutoff cũ. Return timing báo riêng; gate operational đề xuất giữ tolerance
cố định `[budget−0.05, budget+0.5]` giây, không nới theo phần trăm ở horizon dài.
Không có hard-return guarantee; gate này chưa được validate ở 60/300/900s.

Giữ mọi failure và không score-based rerun. No-solution/known algorithm failure
được ghi vào availability. Sai input/source/config/model là protocol integrity
error, phải dừng claims tổng hợp và giữ partial evidence; không biến lỗi executor
thành solver loss. Không xóa failed cells để giữ một tập successful-only.

## Estimand và uncertainty được khai báo trước

Endpoint chính là **feasibility-then-fleet paired win score**, không dùng TD
khi khác fleet. Với từng seed pair, treatment hợp lệ còn comparator không hợp
lệ được +1; ngược lại −1. Nếu cả hai hợp lệ, ít xe hơn được +1, nhiều hơn −1,
bằng NV được 0. Cả hai fail được 0 trong score nhưng phải ghi riêng là failure,
không quality tie. Lấy trung bình năm seed trong instance, rồi trung bình instance.
Dương nghĩa là được ưu tiên theo availability/fleet, không phải trực tiếp số xe
trung bình giảm bao nhiêu. Báo availability và fleet outcomes riêng để thấy nguyên nhân.

Đồng thời báo mean-NV W/T/L trên các instance có đủ năm run hợp lệ của cả hai
phương pháp, với denominator/exclusions rõ; đó là descriptive complete-case
analysis khi có failure. Mean/median/range và sample SD (`ddof=1`) của seed được
ghi rõ, không lẫn với population SD trong CSV cũ. Không best-of-five selection.

TD là secondary conditional: match **fleet của từng valid seed pair**, tính gap
từng pair, trung bình trong instance rồi giữa instance có pair phù hợp. Báo cả
số instance và số matched seed pairs. Đây không phải unconditional TD treatment
effect và không phải phép so trên nhóm chỉ có mean NV bằng nhau nhưng fleet
từng seed khác nhau.

Kế hoạch interval: 10.000 paired cluster-bootstrap replicates, RNG seed
20261019. Resample geometry groups trong mỗi size, giữ toàn bộ member; resample
năm seed labels bằng cùng indices trên mọi algorithm/cutoff trong replicate.
Tính lại matching/score, dùng mean trong stratum và weights gốc 56/74, 12/74,
6/74 cho benchmark chính; ablation dùng weights 1/3 mỗi size. Bốn geometry group
mỗi size và năm seed là rất ít: interval chỉ approximate, không bảo đảm power
hoặc coverage. Group IDs từ manifest cũ đã audit, không được suy có 74 geometry
độc lập từ tên file.

Pairing dùng cùng resampling indices là quy tắc được mô tả trong
[SciPy bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html).
Layer geometry/size/seed ở đây cần triển khai và test riêng; `paired=True` đơn
lẻ không tự thực hiện nó. Seed ID chung cũng không có nghĩa RNG trajectory của
hai thuật toán giống nhau.

Ở 300s, family benchmark ba contrasts dùng percentile levels
`1−0.05/3`; family ablation tám contrasts dùng `1−0.05/8`. Báo 95% descriptive
interval bên cạnh nếu cần, phân biệt với multiplicity-adjusted interval.
Bonferroni không sửa được coverage kém của bootstrap trong mẫu nhỏ. Không tự
đổi sang test khác sau khi thấy score. Nếu matched-TD denominator bằng 0 ở bất
kỳ replicate, giữ trạng thái undefined và không xuất interval đó, không điền 0.
Chưa triển khai statistics engine, tính CI/p-value hoặc tuyên bố significance.

## Budget dự toán và giới hạn launch

Các số sau được tính từ planned jobs, **không phải thời gian đã chạy**:

| Phần | Job count | Solve hours danh nghĩa |
| --- | ---: | ---: |
| Benchmark 74×5×4 cutoff×4 solver | 5.920 | 522.11 |
| Ablation 18×5×2 cutoff×16 cell | 2.880 | 144.00 |
| Full dùng chung, trừ trùng | −180 | −9.00 |
| Tổng physical jobs | **8.620** | **657.11** |

Không cộng giờ CPU thành ETA nhiều worker: proposal tuần tự và chưa có máy/CPU
allocation được chấp nhận. Setup, model loading, process cleanup, audits, failed
pilots, contention và overruns là thêm. Tương ứng chọn 32/38/64 ablation cells
sẽ thành khoảng 801.11/855.11/1089.11 solve hours tổng hợp theo cùng công thức.
Đây là các lựa chọn reviewable, không phải compute đã được user cho phép chạy.

Có 11 gate đang mở trong `design.json`: sửa/chứng nhận bảy vấn đề control,
timing mới, baseline protocol, statistics implementation và compute acceptance.
Acceptance-volume control bổ sung cũng chưa được thiết kế thành executable jobs.
Ưu tiên sửa SP-off và split-off bằng TDD, rồi compose controller controls và
kiểm toàn bộ GEC paths. Sau đó mới operational pilot với source/cache policy mới.

## Công cụ và bằng chứng

[prepare_ablation_design.py](../scripts/prepare_ablation_design.py) từ chối output
đã tồn tại, kiểm source/input/model identity trước và sau audit, lưu source/test
snapshot, cell/contrast/job manifests và artifact hashes. Nhập `--launch` bị parser
từ chối; tool không tạo subprocess benchmark hoặc lệnh chạy jobs.

```sh
env PYTHONPATH=src .venv/bin/python scripts/prepare_ablation_design.py \
  --output-dir /tmp/vrptw-new-ablation-design
```

Chỉ dùng thư mục mới khi tái chuẩn bị. Đừng ghi đè design/result cũ hoặc đọc
những `execution_binding=null` như config hiện đã chạy được.

TDD ban đầu Red vì module chưa tồn tại; 13 test đầu pass sau implementation.
Bốn regression về drift input/manifest/model/source sau đó fail trước guard và
pass sau guard. Target cuối **44 test pass trong 5.41s**: 18 planning tests và
26 LAC tests. Không đổi runtime nên không chạy lại full suite; 373-pass của bước
LAC trước vẫn giữ nguyên phạm vi source đã ghi. Static/integrity checks và log
được lưu riêng cùng biên bản bảo toàn, không dùng test plan làm performance evidence.

Kiểm tra cuối: hai lần prepare độc lập tạo chín artifact giống byte; hash của
tất cả 2.103 file có sẵn trong tập bảo vệ không đổi và toàn bộ tracked diff
giống byte snapshot đầu bước này. Ruff toàn repo, format hai file mới, kiểm
link/whitespace và `git diff --check` pass. Xác nhận lại độc lập: 5.920 primary
cells, 2.880 ablation cells, 180 cell dùng chung, tổng 8.620 execution identity
duy nhất và 2.365.600 solve seconds **dự kiến**. Không có solve nào được chạy.

Source/tool identity của design:
`421e43a6ffd4cf1a1b859a98d983e0f7075a1b1242059c8a7a9d6617637d8714`.
Hash này khác snapshot LAC do thêm preparation tool; các file runtime cũ vẫn
giống byte. Log Red/Green, source/test hashes và biên bản bảo toàn ở
[verification.json](../results/ablation_design_validation_20261019/verification.json).
