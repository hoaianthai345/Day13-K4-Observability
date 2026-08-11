# Báo cáo Cá nhân — Day 13 AI Observability

---

## 1. Thông tin sinh viên
- **Họ và tên**: Thái Hoài An
- **Mã số sinh viên (MSSV)**: `2A202601862`
- **Nhóm**: `Day13-K4-Team02`
- **Vai trò đảm nhiệm**: **Incident Investigation, Challenge Debugging, Report & Demo Lead (Trưởng nhóm)**

---

## 2. Phần việc đảm nhiệm & Phạm vi kỹ thuật
1. **Chỉ đạo và Điều phối Toàn diện Dự án Lab**:
   - Lập kế hoạch triển khai (Implementation Plan) bám sát Rubric 100 điểm và phân chia vai trò 4 thành viên.
   - Quản trị chất lượng code, rà soát test suite `pytest` (22/22 passed), đảm bảo không vi phạm bất kỳ quy định nào trong [RULES.md](file:///d:/VINUNI_AI2026/LABS/Day13-K4-2A202601862/RULES.md) (không commit secret, không leak PII).
2. **Điều tra Incident Challenge Chính thức (Cohort K4)**:
   - Đọc cấu hình chính thức từ `config/challenge.json` (Cohort: `K4`, ID: `day13-k4-observability-v1`, Incident: `rag_slow`, Feature: `monitoring`, Threshold: `2000 ms`).
   - Kích hoạt sự cố qua `python scripts/inject_incident.py` và thực hiện load test chính thức `python scripts/load_test.py --challenge --concurrency 5`.
   - Chứng minh toàn vẹn chuỗi bằng chứng 3 lớp: **Metrics** $\rightarrow$ **Traces** $\rightarrow$ **Logs**.
3. **Phân tích Nguyên nhân gốc rễ (Root Cause Analysis - RCA) & Giải pháp**:
   - **Root Cause**: Xác định chính xác hàm `retrieve()` trong `app/mock_rag.py` bị nghẽn `time.sleep(2.5)` khi xử lý các truy vấn chứa từ khóa liên quan đến domain `monitoring`.
   - **Fix Action**: Đề xuất timeout 1.5s cho retrieval, bật bộ nhớ đệm cache kết quả tìm kiếm và trả về fallback document khi timeout.
   - **Preventive Measure**: Cài đặt alert rule cho retrieval latency P95 > 1000ms và cơ chế Circuit Breaker giữa API layer và Vector Database.
4. **Tổng hợp Báo cáo & Kịch bản Demo**:
   - Biên soạn báo cáo tổng thể `submission/REPORT.md`, tài liệu điều tra `submission/evidence/challenge_k4_investigation.md` và chuẩn bị kịch bản demo trực quan cho buổi chấm.

---

## 3. Bằng chứng đóng góp & Thay đổi mã nguồn (Git Evidence)
- **Commit/PR**: `feat(incident): investigate K4 challenge, prove Metrics->Traces->Logs RCA and author report`
- **Các tệp đã chỉnh sửa/phụ trách**:
  - `submission/REPORT.md` (Báo cáo tổng hợp bài nộp)
  - `submission/evidence/challenge_k4_investigation.md` (Báo cáo điều tra chi tiết RCA)
  - `submission/evidence/validate_logs_result.txt` (100/100)
  - `submission/evidence/validate_dashboard_result.txt` (6/6 panel hợp lệ)
  - `app/challenge.py` & `scripts/inject_incident.py` (Xác thực và chạy kịch bản challenge)
- **Kết quả kiểm thử**:
  - Test suite `tests/test_challenge_config.py` **PASSED 100%**.
  - Toàn bộ chuỗi bằng chứng được chứng minh bằng dữ liệu runtime thực tế trong `data/logs.jsonl` và `/metrics`.

---

## 4. Trả lời câu hỏi chuyên sâu (Technical Understanding Q&A)

### Q1: Khi Error Rate hoặc Latency tăng đột biến, bạn sẽ mở Metric, Trace hay Log trước? Vì sao?
> **Trả lời**: Quy trình chuẩn là: **METRICS $\rightarrow$ TRACES $\rightarrow$ LOGS**.
> 1. **Mở Metrics trước**: Để nắm bắt bức tranh toàn cảnh (Macro view): Thời điểm sự cố bắt đầu, mức độ ảnh hưởng (P50/P95, traffic tổng, error rate) và khoanh vùng loại dịch vụ/endpoint bị ảnh hưởng.
> 2. **Mở Traces tiếp theo**: Từ khoảng thời gian bất thường trên metric, lọc lấy các Trace ID có latency cao nhất hoặc trạng thái error để mở Waterfall View, từ đó khoanh vùng chính xác **Span con nào** đang chiếm 90%+ thời gian hoặc phát sinh lỗi (Micro view).
> 3. **Mở Logs sau cùng**: Dùng `correlation_id` từ trace để tra cứu dòng log chi tiết (Log line) chứa stack trace, payload parameters, biến môi trường và thông điệp lỗi cụ thể để chứng minh nguyên nhân gốc rễ (Root Cause).

### Q2: Bằng chứng nào là đủ để kết luận một Span là Root Cause của sự cố?
> **Trả lời**: Cần thỏa mãn đồng thời 3 điều kiện:
> 1. **Tương quan thời gian và tỷ trọng**: Thời gian thực thi của span đó chiếm phần lớn tổng thời gian request (ví dụ: span `mock_rag.retrieve` chiếm 2500ms / 2650ms tổng thời gian request).
> 2. **Độc lập nguyên nhân**: Các span trước đó chạy bình thường và các span sau đó chỉ bị chậm do phải chờ kết quả từ span này.
> 3. **Log & Code bằng chứng xác thực**: Dòng log hoặc exception liên kết trực tiếp với mã nguồn của span đó giải thích được cơ chế gây chậm (ví dụ: cờ `rag_slow` kích hoạt lệnh sleep/timeout trong `retrieve()`).

### Q3: Vì sao `validate_logs.py` đạt 100/100 điểm chưa đồng nghĩa bài lab đạt 100 điểm Rubric?
> **Trả lời**:
> - `validate_logs.py` chỉ là một script kiểm tra kỹ thuật tĩnh về cấu trúc schema, sự có mặt của correlation ID, contextvars enrichment và quét nhanh regex PII trên tệp log mẫu.
> - Điểm Rubric tối đa 100 điểm đòi hỏi toàn diện: Quản trị Prompt versioning và bằng chứng Rollback trên Tracing, Dashboard 6 panels có bằng chứng runtime và threshold rõ ràng, Báo cáo điều tra Incident chuẩn luồng Metrics $\rightarrow$ Traces $\rightarrow$ Logs, cùng khả năng giải thích và đóng góp cá nhân minh bạch qua Git commit history.

---

## 5. Bài học kinh nghiệm & Kết luận
- Nắm vững tư duy Observability-driven Development: Không thể tối ưu hoặc sửa chữa một hệ thống nếu không thể quan sát và đo lường nó một cách khách quan.
- Rèn luyện kỹ năng lãnh đạo kỹ thuật, phân công công việc mạch lạc và phối hợp nhóm hiệu quả để đưa dự án đạt kết quả hoàn hảo.
