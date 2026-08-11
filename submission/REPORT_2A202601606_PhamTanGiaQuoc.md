# Báo cáo Cá nhân — Day 13 AI Observability

---

## 1. Thông tin sinh viên
- **Họ và tên**: Phạm Tấn Gia Quốc
- **Mã số sinh viên (MSSV)**: `2A202601606`
- **Nhóm**: `Day13-K4-Team02`
- **Vai trò đảm nhiệm**: **Logging & PII Redaction Lead**

---

## 2. Phần việc đảm nhiệm & Phạm vi kỹ thuật
1. **Xây dựng Middleware Correlation ID**:
   - Hiện thực hóa `CorrelationIdMiddleware` trong `app/middleware.py`.
   - Gọi `clear_contextvars()` trước mỗi request để ngăn chặn triệt để hiện tượng rò rỉ ngữ cảnh (context leakage) giữa các async coroutines trong FastAPI.
   - Nhận header `x-request-id` từ client hoặc tự động sinh mới với định dạng chuẩn `req-<8-char-hex>` qua `uuid.uuid4().hex[:8]`.
   - Bind `correlation_id` vào `structlog.contextvars` và trả về `x-request-id` cùng `x-response-time-ms` trong response headers.
2. **Ngăn chặn rò rỉ dữ liệu nhạy cảm (PII Redaction Engine)**:
   - Mở rộng các biểu thức chính quy trong `app/pii.py` cho các loại dữ liệu: Email, Số điện thoại Việt Nam (+84, 09x, 08x...), CCCD (12 chữ số), Thẻ tín dụng (16 chữ số phân tách bằng dấu cách hoặc gạch ngang), Hộ chiếu (Passport VN).
   - Xây dựng cơ chế `scrub_text` thay thế chính xác thành `[REDACTED_<TYPE>]`.
3. **Cấu hình Logging Pipeline & Bonus Audit Logging**:
   - Tích hợp processor `scrub_event` vào pipeline structlog trong `app/logging_config.py` trước khi ghi ra file qua `JsonlFileProcessor` và render JSON.
   - Xây dựng `AuditLogProcessor` ghi log kiểm toán bảo mật riêng biệt vào `data/audit.jsonl` (*Bonus Feature*).
4. **Context Enrichment**:
   - Gán đầy đủ thông tin ngữ cảnh trong `app/main.py`: `user_id_hash` (băm SHA-256 12 ký tự), `session_id`, `feature`, `model`, `env`.

---

## 3. Bằng chứng đóng góp & Thay đổi mã nguồn (Git Evidence)
- **Commit/PR**: `feat(logging): implement correlation ID middleware, context enrichment and PII redaction`
- **Các tệp đã chỉnh sửa**:
  - `app/middleware.py` (Cơ chế Correlation ID và headers)
  - `app/pii.py` (Hệ thống regex và scrubbing PII)
  - `app/logging_config.py` (Chuỗi structlog processors và Audit log)
  - `app/main.py` (Context enrichment trong `/chat`)
- **Kết quả kiểm thử**:
  - Script `python scripts/validate_logs.py` đạt **100/100 điểm tuyệt đối**.
  - Kiểm tra độc lập phát hiện **0 PII leak**.

---

## 4. Trả lời câu hỏi chuyên sâu (Technical Understanding Q&A)

### Q1: PII cần được scrub trước hay sau khi render JSON? Vì sao?
> **Trả lời**: PII bắt buộc phải được scrub **TRƯỚC** khi render JSON và ghi xuống file log (`JsonlFileProcessor` / `JSONRenderer`). 
> - *Lý do 1*: Nếu render JSON trước rồi mới scrub, chuỗi JSON đã hoàn chỉnh có thể bị phá vỡ cấu trúc cú pháp nếu regex thay đổi độ dài chuỗi hoặc can thiệp vào các ký tự escape (`\`, `"`).
> - *Lý do 2*: Về mặt bảo mật (Defense in Depth), việc scrub ở tầng cấu trúc dữ liệu (`dict`) trước khi ghi đĩa đảm bảo không bao giờ tồn tại bản ghi chưa che trong buffer hoặc log file tạm, ngăn ngừa triệt để rủi ro rò rỉ dữ liệu khi gặp sự cố crash.

### Q2: Correlation ID khác Trace ID như thế nào?
> **Trả lời**:
> - **Correlation ID**: Là một định danh duy nhất (thường ở mức application/HTTP header, ví dụ `req-8b1ffac4`) được truyền qua tất cả các log messages và service boundaries trong vòng đời của một request. Mục đích chính là nhóm (correlate) toàn bộ log thuộc cùng một request lại với nhau.
> - **Trace ID**: Là định danh trong hệ thống Distributed Tracing (như OpenTelemetry/Langfuse) đại diện cho một cây thực thi phân tán (Trace Tree). Trace ID liên kết các `Span ID` con với nhau, đo lường chính xác thời gian bắt đầu, kết thúc (waterfall latency) và quan hệ cha-con (parent-child) của từng tác vụ.

### Q3: Vì sao phải gọi `clear_contextvars()` ở đầu middleware?
> **Trả lời**: Trong kiến trúc bất đồng bộ (AsyncIO / FastAPI), các worker threads có thể tái sử dụng context execution nếu không được dọn dẹp. Nếu một request trước đó đã bind `user_id_hash` hoặc `correlation_id` vào contextvars mà request sau không ghi đè hết các trường, các log của request mới có nguy cơ bị gán sai thông tin của request cũ (Context Contamination). Do đó, gọi `clear_contextvars()` ở đầu mỗi request đảm bảo tính độc lập và toàn vẹn dữ liệu.

---

## 5. Bài học kinh nghiệm & Kết luận
- Nắm vững cơ chế vận hành của Structured Logging trong môi trường sản xuất với định dạng JSON Lines chuẩn schema.
- Hiểu rõ phương pháp quản lý context bất đồng bộ và nguyên tắc tuân thủ bảo vệ dữ liệu cá nhân (GDPR/Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân).
