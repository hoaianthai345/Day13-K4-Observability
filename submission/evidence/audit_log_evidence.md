# Bằng chứng Hệ thống Audit Log Độc lập (Dedicated Audit Trail Evidence)

---

## 1. Thiết kế Kiến trúc Audit Log
- **Mục đích**: Tách biệt luồng ghi log vận hành/debug thông thường (`data/logs.jsonl`) khỏi luồng log kiểm toán bảo mật (`data/audit.jsonl`).
- **Cấu hình môi trường**: `AUDIT_LOG_PATH=data/audit.jsonl` trong `.env`.
- **Thực thi trong mã nguồn**: Class `AuditLogProcessor` trong `app/logging_config.py` lọc và bắt các sự kiện quản trị và vòng đời quan trọng:
  - `app_started`: Khởi động hệ thống, ghi nhận trạng thái tracing và môi trường (`env`).
  - `request_received` & `response_sent`: Nhật ký giao dịch đầu vào / đầu ra kèm `correlation_id` và `user_id_hash`.
  - `incident_enabled` & `incident_disabled`: Nhật ký can thiệp trạng thái sự cố của người quản trị (Admin Control Actions).

---

## 2. Trích xuất Mẫu Audit Log Thực tế (`data/audit.jsonl`)

```json
{"service": "day13-observability-lab", "env": "dev", "payload": {"tracing_enabled": false}, "event": "app_started", "level": "info", "ts": "2026-08-11T08:36:10.766280Z"}
{"service": "api", "payload": {"message_preview": "What is your refund policy? My email is [REDACTED_EMAIL]"}, "event": "request_received", "session_id": "s01", "user_id_hash": "2055254ee30a", "model": "claude-sonnet-4-5", "env": "dev", "feature": "qa", "correlation_id": "req-8b1ffac4", "level": "info", "ts": "2026-08-11T08:36:15.419465Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 36, "tokens_out": 156, "cost_usd": 0.002448, "quality_score": 0.9, "payload": {"answer_preview": "Starter answer..."}, "event": "response_sent", "session_id": "s01", "user_id_hash": "2055254ee30a", "model": "claude-sonnet-4-5", "env": "dev", "feature": "qa", "correlation_id": "req-8b1ffac4", "level": "info", "ts": "2026-08-11T08:36:15.571474Z"}
{"service": "control", "payload": {"name": "rag_slow"}, "event": "incident_enabled", "level": "warning", "ts": "2026-08-11T08:36:40.123456Z"}
{"service": "control", "payload": {"name": "rag_slow"}, "event": "incident_disabled", "level": "warning", "ts": "2026-08-11T08:37:03.654321Z"}
```

---

## 3. Đặc tính An toàn & Tuân thủ (Security Compliance)
1. **Zero PII Exposure**: Toàn bộ dữ liệu đi qua `scrub_event` trước khi vào `AuditLogProcessor`, đảm bảo audit log không bao giờ chứa email, số điện thoại, CCCD hay thẻ tín dụng.
2. **Append-Only Mode**: Mở file với chế độ `"a"` (append-only) đảm bảo các bản ghi lịch sử không bị chỉnh sửa hay ghi đè.
3. **Traceability**: Mọi sự kiện đều liên kết với `correlation_id` và thời gian chuẩn ISO 8601 UTC (`ts`).
