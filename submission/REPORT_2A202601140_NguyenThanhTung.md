# Báo cáo Cá nhân — Day 13 AI Observability

---

## 1. Thông tin sinh viên
- **Họ và tên**: Nguyễn Thanh Tùng
- **Mã số sinh viên (MSSV)**: `2A202601140`
- **Nhóm**: `Day13-K4-Team02`
- **Vai trò đảm nhiệm**: **Tracing & Prompt Versioning Lead**

---

## 2. Phần việc đảm nhiệm & Phạm vi kỹ thuật
1. **Thiết lập và Tích hợp Tracing (OpenTelemetry & Langfuse SDK Integration)**:
   - Cấu hình OpenTelemetry `TracerProvider`, `InMemorySpanExporter` và `SimpleSpanProcessor` chuẩn trong `app/tracing.py`.
   - Sử dụng decorator `@observe(as_type="span")` trên các sub-components: `retrieve` trong `app/mock_rag.py` và `generate` trong `app/mock_llm.py` để tạo cấu trúc waterfall đa tầng phân tách rõ RAG và LLM.
   - Gắn kết siêu dữ liệu ngữ cảnh OpenTelemetry Attributes (`app.correlation_id`, `app.user_id_hash`, `app.feature`, `llm.model`, `llm.tokens.input`, `llm.tokens.output`, `app.cost_usd`, `app.quality_score`).
   - Tích hợp Langfuse decorator `@observe(as_type="generation")` gắn kết metadata: `user_id_hash`, `session_id`, `tags`, `prompt_name`, `prompt_label`, `prompt_version`, `prompt_source`.
2. **Quản lý Vòng đời Prompt (Prompt Management & Versioning)**:
   - Hiện thực hóa module `app/prompt_management.py` theo đúng contract 3 biến: `{{feature}}`, `{{docs}}`, `{{message}}`.
   - Tạo Prompt **Version 1** (với labels `baseline` và `production`) và **Version 2** (với label `candidate`).
   - Xây dựng cơ chế dự phòng an toàn (Local Fallback): Nếu mất kết nối Langfuse, hệ thống tự động fallback về prompt cục bộ với metadata ghi rõ `prompt_source="local-fallback"` và `fetch_error` thay vì che giấu lỗi.
3. **Thực nghiệm Chuyển đổi Label và Rollback Prompt**:
   - Chạy các request kiểm thử với `LANGFUSE_PROMPT_LABEL=baseline` và `candidate`.
   - Thực hiện chuyển label `production` sang Version 2; sau khi quan sát thấy token generation tăng cao, đã thực hiện **Rollback** an toàn label `production` về lại Version 1.
   - Thu thập trace IDs và ảnh minh chứng quá trình rollback đưa vào `submission/evidence/prompt_versioning_and_rollback.md`.

---

## 3. Bằng chứng đóng góp & Thay đổi mã nguồn (Git Evidence)
- **Commit/PR**: `feat(tracing): configure Langfuse prompt versioning, label rollback and metadata linking`
- **Các tệp đã chỉnh sửa/phụ trách**:
  - `app/prompt_management.py` (Xử lý resolve prompt, versioning và fallback)
  - `app/tracing.py` (Cấu hình Langfuse client và enable check)
  - `app/agent.py` (Gắn kết trace metadata, token usage, cost details)
  - `submission/evidence/prompt_versioning_and_rollback.md` (Tài liệu evidence rollback)
  - `submission/evidence/traces_and_waterfall.md` (Danh sách 17 traces)
- **Kết quả kiểm thử**:
  - Toàn bộ unit tests liên quan trong `tests/test_prompt_management.py` và `tests/test_agent_prompt_trace.py` đều **PASSED 100%**.

---

## 4. Trả lời câu hỏi chuyên sâu (Technical Understanding Q&A)

### Q1: Vì sao cần tách biệt quản lý Prompt (Prompt Management) ra khỏi mã nguồn (Hardcoded Code)?
> **Trả lời**: 
> 1. **Khả năng cập nhật và Rollback tức thì (Zero Downtime)**: Cho phép kỹ sư AI điều chỉnh câu lệnh prompt, thử nghiệm các kỹ thuật prompting mới hoặc rollback ngay lập tức khi phát hiện hallucination/bias mà không cần build lại Docker image hay thực hiện quy trình CI/CD deploy code.
> 2. **Auditability và Reproducibility**: Mỗi request đều được gắn chặt với một `prompt_version` cụ thể trong trace metadata. Khi xảy ra phản hồi sai, kỹ sư có thể mở lại chính xác phiên bản prompt đã được dùng tại thời điểm đó để tái hiện lỗi.

### Q2: Khi hệ thống không kết nối được tới Prompt Registry (Langfuse), app nên hành xử thế nào?
> **Trả lời**:
> - Hệ thống **không được phép crash** (chống Single Point of Failure). Hệ thống cần fallback về prompt template cục bộ (`DEFAULT_PROMPT_TEMPLATE`).
> - Tuy nhiên, trace metadata và log **phải phản ánh trung thực**: Ghi nhận `prompt_source="local-fallback"` và `fetch_error="<ErrorType>"`, tuyệt đối không giả mạo rằng đã lấy thành công prompt từ Langfuse.

### Q3: Khi phân tích Trace Waterfall của một ứng dụng AI/LLM, những span nào quan trọng nhất?
> **Trả lời**:
> - **Retrieval Span (`mock_rag.retrieve`)**: Đo lường thời gian vector search / semantic search và truy xuất dữ liệu từ database.
> - **Generation Span (`mock_llm.generate`)**: Đo lường Time To First Token (TTFT) và tổng thời gian sinh từ LLM.
> - **Tool/API Spans**: Đo lường thời gian gọi các bên thứ ba.
> Phân tích waterfall giúp phân định rõ ràng độ trễ đến từ hạ tầng nội bộ (RAG) hay do model provider bên ngoài (LLM).

---

## 5. Bài học kinh nghiệm & Kết luận
- Hiểu sâu sắc về Distributed Tracing trong kỷ nguyên Generative AI: Tracing không chỉ theo dõi latency mà còn theo dõi Token Usage, Cost per Request và Prompt Metadata.
- Nắm vững quy trình CI/CD cho Prompt Engineering và quản trị rủi ro thông qua cơ chế Fallback & Canary Labeling.
