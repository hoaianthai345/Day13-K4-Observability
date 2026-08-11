# Báo cáo Cá nhân — Day 13 AI Observability

---

## 1. Thông tin sinh viên
- **Họ và tên**: Dương Đức Minh
- **Mã số sinh viên (MSSV)**: `2A202601306`
- **Nhóm**: `Day13-K4-Team02`
- **Vai trò đảm nhiệm**: **Dashboard, SLO & Alert Rules Lead**

---

## 2. Phần việc đảm nhiệm & Phạm vi kỹ thuật
1. **Đặc tả & Xác thực Dashboard Contract (6 Panels)**:
   - Nghiên cứu và hiện thực hóa contract [`config/dashboard.yaml`](../config/dashboard.yaml) theo đúng chuẩn 6 panel: `latency` (P50/P95/P99), `traffic` (count/rate), `errors` (rate % & breakdown), `cost` (sum/total), `tokens` (sum in/out), `quality` (mean score).
   - Hoàn thiện tài liệu đặc tả chi tiết [`docs/dashboard-spec.md`](../docs/dashboard-spec.md) bao gồm query pseudocode, đơn vị đo, và ngưỡng threshold cho từng panel.
   - Phát triển công cụ trực quan hóa động [`scripts/dashboard_app.py`](../scripts/dashboard_app.py) đọc trực tiếp từ `data/logs.jsonl`.
2. **Thiết lập Service Level Objectives (SLOs)**:
   - Cập nhật [`config/slo.yaml`](../config/slo.yaml) định lượng rõ ràng 4 chỉ số SLI/SLO then chốt:
     - `latency_p95_ms`: Mục tiêu $\le$ 3000 ms với target 99.5% requests.
     - `error_rate_pct`: Mục tiêu $\le$ 2.0% với target 99.0% requests.
     - `daily_cost_usd`: Mục tiêu $\le$ $2.5 USD với target 100.0% ngày vận hành.
     - `quality_score_avg`: Mục tiêu $\ge$ 0.75 với target 95.0% requests.
3. **Thiết kế Cảnh báo Triệu chứng (Symptom-based Alert Rules) & Runbooks**:
   - Cấu hình 3 alert rules trong [`config/alert_rules.yaml`](../config/alert_rules.yaml):
     1. `HighLatencyP95` (Warning, `p95_latency_ms > 3000 for 3m`, Owner: `backend-team`).
     2. `HighErrorRate` (Critical, `error_rate_pct > 2.0 for 5m`, Owner: `platform-sre`).
     3. `CostSpikeAnomaly` (Warning, `daily_cost_usd > 2.5 or tokens_per_min > 50000 for 5m`, Owner: `ai-operations`).
   - Viết toàn diện Runbook cho cả 3 alerts trong [`docs/alerts.md`](../docs/alerts.md) chỉ rõ quy trình 3 bước điều tra (Metrics $\rightarrow$ Traces $\rightarrow$ Logs), ảnh hưởng người dùng và biện pháp mitigation tạm thời.

---

## 3. Bằng chứng đóng góp & Thay đổi mã nguồn (Git Evidence)
- **Commit/PR**: `feat(observability): define SLOs, symptom-based alert rules and 6-panel dashboard spec`
- **Các tệp đã chỉnh sửa/phụ trách**:
  - `config/dashboard.yaml` (Cấu hình 6 panels contract)
  - `docs/dashboard-spec.md` (Đặc tả chi tiết 6 panels)
  - `config/slo.yaml` (Mục tiêu và ngưỡng SLO)
  - `config/alert_rules.yaml` (Quy tắc cảnh báo symptom-based)
  - `docs/alerts.md` (Hướng dẫn xử lý sự cố Runbook)
  - `scripts/dashboard_app.py` (CLI Dashboard visualizer)
  - `submission/evidence/validate_dashboard_result.txt` & `dashboard_runtime_evidence.md`
- **Kết quả kiểm thử**:
  - `python scripts/validate_dashboard.py` trả về: **`HỢP LỆ: 6/6 panel có trong dashboard contract.`**
  - Toàn bộ test trong `tests/test_dashboard_validator.py` **PASSED 100%**.

---

## 4. Trả lời câu hỏi chuyên sâu (Technical Understanding Q&A)

### Q1: Vì sao chỉ nhìn Average Latency (Độ trễ trung bình) có thể bỏ sót vấn đề nghiêm trọng?
> **Trả lời**:
> - Giá trị trung bình (Average/Mean) che giấu phân phối đuôi dài (Tail Latency). Ví dụ: 95 request có độ trễ 100ms và 5 request bị timeout 10,000ms thì Average chỉ khoảng 595ms (trông có vẻ chấp nhận được).
> - Tuy nhiên, 5% người dùng này đang trải nghiệm hệ thống bị đơ hoàn toàn. Độ trễ P95/P99 (Percentile 95th/99th) phản ánh chính xác ranh giới mà 95% hoặc 99% người dùng nhận được phản hồi nhanh hơn mức đó, giúp phát hiện ngay các hiện tượng nghẽn mạng, lock contention hoặc cold-start.

### Q2: Thế nào là một Symptom-based Alert (Cảnh báo dựa trên triệu chứng) và vì sao nó tốt hơn Cause-based Alert?
> **Trả lời**:
> - **Symptom-based Alert**: Cảnh báo dựa trên trực tiếp những gì người dùng đang gánh chịu hoặc vi phạm SLO (ví dụ: "Tỷ lệ lỗi 5xx vượt 2%" hoặc "P95 Latency > 3000ms").
> - **Cause-based Alert**: Cảnh báo dựa trên một nguyên nhân nội bộ phỏng đoán (ví dụ: "CPU đạt 80%" hoặc "Database connection pool tăng").
> - *Ưu điểm*: Symptom-based alert giảm thiểu triệt để Alert Fatigue (báo động giả khi CPU cao nhưng người dùng vẫn được phục vụ nhanh chóng), đồng thời đảm bảo mọi alert phát ra đều đại diện cho một tác động thực sự tới người dùng.

### Q3: Một Alert Rule hoàn chỉnh cần những thành phần bắt buộc nào?
> **Trả lời**:
> 1. **Condition (Điều kiện)**: Ngưỡng toán học rõ ràng (ví dụ: `error_rate > 2.0%`).
> 2. **Duration (Thời gian duy trì)**: Khoảng thời gian điều kiện phải thỏa mãn trước khi bắn alert (ví dụ: `for 5m`) để lọc nhiễu transient spikes.
> 3. **Severity (Mức độ nghiêm trọng)**: Info, Warning, Critical (để phân luồng kênh thông báo: Slack, PagerDuty, SMS).
> 4. **Owner (Đội ngũ chịu trách nhiệm)**: Gán cụ thể team phụ trách (`backend-team`, `platform-sre`).
> 5. **Runbook URL**: Đường dẫn tới tài liệu hướng dẫn các bước xử lý chuẩn.

---

## 5. Bài học kinh nghiệm & Kết luận
- Hiểu rõ phương pháp luận Site Reliability Engineering (SRE): Phân biệt rõ SLI (Chỉ số đo), SLO (Mục tiêu cam kết nội bộ), SLA (Cam kết hợp đồng với khách hàng).
- Nắm vững kỹ thuật trực quan hóa dữ liệu quan sát (Observability Dashboards) phục vụ ra quyết định tức thời trong vận hành hệ thống AI.
