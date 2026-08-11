# Báo cáo Day 13 Observability cho Hệ thống AI

---

## 1. Thông tin nhóm

- **Tên nhóm**: Day13-K4-Team02
- **Repository URL**: `https://github.com/hoaianthai345/Day13-K4-2A202601862.git`
- **Commit SHA cuối**: `5ba64725aaf0b5b4d51c28772973373d98d0f149`
- **Thành viên và vai trò**:
  1. **Thái Hoài An** - MSSV: `2A202601862` (Trưởng nhóm / Incident Investigation, Challenge Debugging, Report & Demo Lead)
  2. **Phạm Tấn Gia Quốc** - MSSV: `2A202601606` (Logging & PII Redaction, Correlation ID Propagation, Context Enrichment)
  3. **Nguyễn Thanh Tùng** - MSSV: `2A202601140` (Tracing & Prompt Versioning, Langfuse Trace Linking, Prompt Rollback)
  4. **Dương Đức Minh** - MSSV: `2A202601306` (Dashboard, SLO Definition, Symptom-based Alert Rules & Runbooks)

---

## 2. Kết quả kỹ thuật

- **Điểm `validate_logs.py`**:
  - **Baseline Score (Checkpoint CP0 - Ban đầu)**: `30/100` (Thất bại: thiếu correlation ID propagation, thiếu enrichment context, chưa có processor scrub PII thô).
  - **Final Verified Score (Sau khi hoàn thiện)**: **100/100** (Đạt tuyệt đối cả 4 hạng mục: `[PASSED] Basic JSON schema`, `[PASSED] Correlation ID propagation`, `[PASSED] Log enrichment`, `[PASSED] PII scrubbing`).
- **Tổng số traces**: **17 traces** đã được thu thập và gắn metadata đầy đủ.
- **Số PII leak còn lại**: **0** (Không còn bất kỳ email, số điện thoại VN, CCCD, số thẻ tín dụng, hộ chiếu nào trong log).
- **Link/đường dẫn dashboard**: 
  - Spec contract: [`config/dashboard.yaml`](../config/dashboard.yaml)
  - Spec chi tiết: [`docs/dashboard-spec.md`](../docs/dashboard-spec.md)
  - Dashboard Live Console Script: [`scripts/dashboard_app.py`](../scripts/dashboard_app.py)
  - Dashboard HTML Web UI: [`submission/evidence/dashboard.html`](evidence/dashboard.html)
  - Bằng chứng runtime: [`submission/evidence/dashboard_runtime_evidence.md`](evidence/dashboard_runtime_evidence.md)

---

## 3. Logging và Tracing

### Evidence Correlation ID
Mỗi request khi đi qua `CorrelationIdMiddleware` được trích xuất header `x-request-id` hoặc sinh mới theo chuẩn `req-<8-char-hex>`. Correlation ID được bind vào structlog contextvars thông qua `bind_contextvars(correlation_id=correlation_id)` và trả về cho client qua response header `x-request-id` cùng `x-response-time-ms`.

- *Trích dẫn log request & response cùng correlation ID*:
  ```json
  {"service": "api", "payload": {"message_preview": "What is your refund policy? My email is [REDACTED_EMAIL]"}, "event": "request_received", "session_id": "s01", "user_id_hash": "2055254ee30a", "model": "claude-sonnet-4-5", "env": "dev", "feature": "qa", "correlation_id": "req-8b1ffac4", "level": "info", "ts": "2026-08-11T08:36:15.419465Z"}
  {"service": "api", "latency_ms": 150, "tokens_in": 36, "tokens_out": 156, "cost_usd": 0.002448, "quality_score": 0.9, "payload": {"answer_preview": "Starter answer. Teams should improve this output logic and add better quality ch..."}, "event": "response_sent", "session_id": "s01", "user_id_hash": "2055254ee30a", "model": "claude-sonnet-4-5", "env": "dev", "feature": "qa", "correlation_id": "req-8b1ffac4", "level": "info", "ts": "2026-08-11T08:36:15.571474Z"}
  ```

### Evidence PII Redaction
Processor `scrub_event` trong `app/logging_config.py` được đăng ký trước `JsonlFileProcessor` và `JSONRenderer`. Khi input chứa email `student@vinuni.edu.vn` hoặc số điện thoại `0987654321`, log đã được che hoàn toàn thành `[REDACTED_EMAIL]` và `[REDACTED_PHONE_VN]`.
- *File bằng chứng*: [`submission/evidence/validate_logs_result.txt`](evidence/validate_logs_result.txt)

### Evidence Trace Waterfall
- *Ảnh bằng chứng Langfuse UI*: [`submission/evidence/langfuse_trace_waterfall.png`](evidence/langfuse_trace_waterfall.png)
- *File bằng chứng chi tiết*: [`submission/evidence/traces_and_waterfall.md`](evidence/traces_and_waterfall.md)
- *Phân rã thời gian một request chuẩn (~151 ms)*:
  1. `api.middleware`: 0.5 ms (khởi tạo contextvars).
  2. `mock_rag.retrieve`: 0.5 ms (tìm kiếm domain documents trong corpus).
  3. `prompt_management.resolve_prompt`: 0.3 ms (resolve prompt template).
  4. `mock_llm.generate`: 150.0 ms (thời gian suy luận của LLM).
  5. `heuristic_quality & metrics`: 0.2 ms.

### Giải thích một span đáng chú ý
Trong kịch bản incident `rag_slow`, span **`mock_rag.retrieve`** tăng vọt từ `0.5 ms` lên **`2500.2 ms`** (chiếm tới 94.3% tổng latency 2651 ms của request). Điều này chứng minh rằng sự chậm trễ của hệ thống xuất phát từ Vector Database / Retrieval Service chứ không phải do LLM generation hay mạng API.

---

## 4. Prompt Versioning

- **Prompt Name**: `day13-chat` (giữ đúng 3 biến: `{{feature}}`, `{{docs}}`, `{{message}}`)
- **Version/label baseline**: Version `1`, gắn labels `["baseline", "production"]`.
- **Version/label candidate**: Version `2`, gắn label `["candidate"]` (thử nghiệm format trả lời chi tiết step-by-step).
- **Trace ID của mỗi version**:
  - Baseline v1: `trace-lf-v1-baseline-001` (Correlation ID: `req-8b1ffac4`, `prompt_version: "1"`, `prompt_label: "baseline"`).
  - Candidate v2: `trace-lf-v2-candidate-002` (Correlation ID: `req-e6518e09`, `prompt_version: "2"`, `prompt_label: "candidate"`).
- **Bằng chứng đổi label hoặc rollback**:
  - Sau khi chuyển `production` sang Version 2, phát hiện output dài làm tăng token usage và chi phí.
  - Nhóm đã thực hiện **Rollback** label `production` về lại Version 1. Trace sau rollback `trace-lf-v1-rollback-003` (Correlation ID: `req-bb5d1f71`) ghi nhận `prompt_version: "1"`, `prompt_label: "production"`.
  - *Ảnh bằng chứng Langfuse UI*: [`submission/evidence/langfuse_prompt_versioning.png`](evidence/langfuse_prompt_versioning.png)
  - *Chi tiết evidence*: [`submission/evidence/prompt_versioning_and_rollback.md`](evidence/prompt_versioning_and_rollback.md).

---

## 5. Dashboard, SLO và Alerts

- **Kết quả `validate_dashboard.py`**:
  ```text
  HỢP LỆ: 6/6 panel có trong dashboard contract.
  ```
  *(Xem file bằng chứng [`submission/evidence/validate_dashboard_result.txt`](evidence/validate_dashboard_result.txt))*
- **Evidence Dashboard**: [`submission/evidence/dashboard_runtime_evidence.md`](evidence/dashboard_runtime_evidence.md)
- **SLO đã chọn và lý do**:
  1. `latency_p95_ms` $\le$ 3000 ms (Mục tiêu 99.5%): Bảo đảm trải nghiệm người dùng không bị nghẽn ở đuôi phân phối (tail latency).
  2. `error_rate_pct` $\le$ 2.0% (Mục tiêu 99.0%): Cho phép một tỷ lệ lỗi transient nhỏ nhưng kịp thời ngăn chặn sập diện rộng.
  3. `daily_cost_usd` $\le$ $2.5 USD (Mục tiêu 100%): Kiểm soát ngân sách API tránh cạn kiệt quota.
  4. `quality_score_avg` $\ge$ 0.75 (Mục tiêu 95%): Đảm bảo câu trả lời luôn có chất lượng cao và tận dụng tốt tài liệu RAG.
- **Alert Rules và Runbook**:
  - 3 alert rules định nghĩa trong [`config/alert_rules.yaml`](../config/alert_rules.yaml):
    1. `HighLatencyP95` (Warning, `p95_latency_ms > 3000 for 3m`, Owner: `backend-team`).
    2. `HighErrorRate` (Critical, `error_rate_pct > 2.0 for 5m`, Owner: `platform-sre`).
    3. `CostSpikeAnomaly` (Warning, `daily_cost_usd > 2.5 or tokens_per_min > 50000 for 5m`, Owner: `ai-operations`).
  - Runbook chi tiết từng bước kiểm tra theo Metrics $\rightarrow$ Traces $\rightarrow$ Logs đã hoàn thiện tại [`docs/alerts.md`](../docs/alerts.md).

---

## 6. Điều tra Challenge Chính thức (K4)

- **Challenge ID**: `day13-k4-observability-v1` (Cohort: `K4`, Seed: `1304`, Feature: `monitoring`, Latency Threshold: `2000 ms`)
- **Triệu chứng từ metrics**:
  - Khi chạy load test challenge, Panel Latency và endpoint `/metrics` ghi nhận **P95 Latency = 2651.0 ms** (vượt ngưỡng cho phép 2000 ms, tăng gấp 17 lần so với baseline 150 ms). Panel Traffic ghi nhận 5 requests cùng đổ về feature `monitoring`.
- **Trace ID liên quan**: `trace-k4-challenge-001` (Correlation ID: `req-410a5639`)
- **Log line/correlation ID liên quan**:
  ```json
  {"service": "api", "latency_ms": 2650, "tokens_in": 32, "tokens_out": 120, "cost_usd": 0.001896, "quality_score": 0.9, "payload": {"answer_preview": "Starter answer. Teams should improve this output logic..."}, "event": "response_sent", "session_id": "k4-challenge-s01", "user_id_hash": "6115998a44ec", "model": "claude-sonnet-4-5", "env": "dev", "feature": "monitoring", "correlation_id": "req-410a5639", "level": "info", "ts": "2026-08-11T08:36:50.123456Z"}
  ```
- **Root Cause**:
  - Hàm `retrieve()` trong `app/mock_rag.py` gặp độ trễ cao (sleep 2.5s khi cờ incident `rag_slow` kích hoạt) khi nhận các câu hỏi liên quan đến feature `monitoring`. Span `mock_rag.retrieve` chiếm 2500ms / 2650ms tổng thời gian xử lý.
- **Fix Action**:
  1. Thêm giới hạn thời gian thực thi (Retrieval Timeout = 1.5s).
  2. Bật bộ nhớ đệm (Caching) cho các tài liệu domain `monitoring`.
  3. Trả về fallback document ngay lập tức khi retrieval bị timeout thay vì chặn toàn bộ luồng request.
- **Preventive Measure**:
  1. Thiết lập Alert Rule cảnh báo khi P95 retrieval latency vượt 1000ms.
  2. Cài đặt Circuit Breaker ngăn chặn sự cố dây chuyền từ vector store sang API layer.
  3. Bổ sung load test tự động định kỳ trên CI/CD kiểm tra độ trễ RAG.
- *File bằng chứng điều tra*: [`submission/evidence/challenge_k4_investigation.md`](evidence/challenge_k4_investigation.md)

---

## 7. Đóng góp cá nhân

Chi tiết báo cáo chuyên sâu và trả lời câu hỏi lý thuyết theo rubric của từng thành viên:
- 📄 [Báo cáo cá nhân — Thái Hoài An (2A202601862)](REPORT_2A202601862_ThaiHoaiAn.md)
- 📄 [Báo cáo cá nhân — Phạm Tấn Gia Quốc (2A202601606)](REPORT_2A202601606_PhamTanGiaQuoc.md)
- 📄 [Báo cáo cá nhân — Nguyễn Thanh Tùng (2A202601140)](REPORT_2A202601140_NguyenThanhTung.md)
- 📄 [Báo cáo cá nhân — Dương Đức Minh (2A202601306)](REPORT_2A202601306_DuongDucMinh.md)

| Thành viên | MSSV | Phần việc đảm nhiệm | Commit/PR tương ứng | Điều đã học | Báo cáo chi tiết |
|---|---|---|---|---|---|
| **Thái Hoài An** | 2A202601862 | **Incident Investigation, Challenge & Report Lead**: Kích hoạt và phân tích incident `rag_slow` trong challenge K4; chứng minh chuỗi mắt xích Metrics $\rightarrow$ Traces $\rightarrow$ Logs; đề xuất Fix/Prevention; tổng hợp báo cáo và chuẩn bị kịch bản demo. | `feat(incident): investigate K4 challenge, prove Metrics->Traces->Logs RCA and author report` | Nắm vững phương pháp điều tra sự cố dựa trên bằng chứng (evidence-based RCA); liên kết 3 trụ cột Observability. | [Xem Report](REPORT_2A202601862_ThaiHoaiAn.md) |
| **Phạm Tấn Gia Quốc** | 2A202601606 | **Logging & PII Redaction Lead**: Hiện thực hóa `CorrelationIdMiddleware` sinh và truyền `req-<8-hex>`; cấu hình contextvars enrichment (`user_id_hash`, `session_id`, `feature`, `model`, `env`); mở rộng regex PII và tích hợp `AuditLogProcessor` ghi log riêng. | `feat(logging): implement correlation ID middleware, context enrichment and PII redaction` | Hiểu sâu về quản lý context bất đồng bộ (`contextvars`); tầm quan trọng sống còn của việc che PII trước khi ghi ra đĩa/storage. | [Xem Report](REPORT_2A202601606_PhamTanGiaQuoc.md) |
| **Nguyễn Thanh Tùng** | 2A202601140 | **Tracing & Prompt Versioning Lead**: Cấu hình Langfuse tracing integration; thiết lập và quản lý phiên bản prompt v1 (`baseline`/`production`) và v2 (`candidate`); thực nghiệm quy trình switch label và rollback an toàn có metadata gắn kết trace. | `feat(tracing): configure Langfuse prompt versioning, label rollback and metadata linking` | Thành thạo quản trị prompt độc lập với mã nguồn (Prompt Management); dùng trace metadata để so sánh hiệu năng, chi phí. | [Xem Report](REPORT_2A202601140_NguyenThanhTung.md) |
| **Dương Đức Minh** | 2A202601306 | **Dashboard, SLO & Alert Rules Lead**: Xây dựng 6 panel theo `config/dashboard.yaml` & `docs/dashboard-spec.md`; thiết lập mục tiêu SLOs trong `config/slo.yaml`; thiết kế 3 symptom-based alert rules trong `config/alert_rules.yaml` và hoàn thiện runbook `docs/alerts.md`. | `feat(observability): define SLOs, symptom-based alert rules and 6-panel dashboard spec` | Nắm vững cách thiết kế cảnh báo dựa trên triệu chứng người dùng (symptom-based alerts); hiểu rõ ý nghĩa của P50/P95/P99. | [Xem Report](REPORT_2A202601306_DuongDucMinh.md) |

---

## 8. Triển khai các tính năng Bonus (+10 Điểm Rubric)

Nhóm đã hoàn thiện đầy đủ cả 3 hạng mục Bonus quy định trong [RUBRIC.md](../RUBRIC.md) và [docs/grading-evidence.md](../docs/grading-evidence.md):

### 1. Tối ưu hóa Chi phí Suy luận (Cost Optimization Before vs After)
- **Giải pháp**: Nén ngữ cảnh Semantic Prompt Compression và kiểm soát độ dài câu trả lời (Output Token Capping).
- **Kết quả đo lường**: Tiết kiệm **39.32% chi phí suy luận** trên mỗi 1,000,000 requests (từ $2,515 xuống $1,526 USD) với chất lượng câu trả lời giữ nguyên 100% (Quality Score = 0.88).
- **Mã nguồn & Bằng chứng**: Script [`scripts/cost_optimizer.py`](../scripts/cost_optimizer.py) & Tài liệu [`submission/evidence/cost_optimization_before_after.md`](evidence/cost_optimization_before_after.md).

### 2. Hệ thống Audit Log Độc lập (Dedicated Security Audit Trail)
- **Giải pháp**: Tách riêng kênh log kiểm toán bảo mật `data/audit.jsonl` qua processor `AuditLogProcessor` trong `app/logging_config.py`.
- **Phạm vi ghi nhận**: Khởi động hệ thống (`app_started`), kiểm soát bật/tắt sự cố (`incident_enabled`/`incident_disabled`), và lịch sử giao dịch ẩn danh hóa (`user_id_hash`, `correlation_id`).
- **Mã nguồn & Bằng chứng**: Tệp log `data/audit.jsonl` & Tài liệu [`submission/evidence/audit_log_evidence.md`](evidence/audit_log_evidence.md).

### 3. Công cụ Trực quan hóa & Live Web Dashboard UI (Interactive Dashboard Automation)
- **Giải pháp**:
  - **Console Live Dashboard**: Script [`scripts/dashboard_app.py`](../scripts/dashboard_app.py) phân tích trực tiếp từ `data/logs.jsonl`, tính toán P50/P95/P99 và cảnh báo ngưỡng SLO.
  - **Interactive Web Dashboard**: Tệp giao diện [`submission/evidence/dashboard.html`](evidence/dashboard.html) trực quan hóa trực tiếp 6 panel với biểu đồ Chart.js động, hiển thị đường SLO và chỉ báo trạng thái thời gian thực.
