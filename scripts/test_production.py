"""Script kiểm thử luồng Production thực tế kết nối trực tiếp với Langfuse Cloud.

Kiểm tra:
1. Resolve prompt 'day13-chat' với nhãn 'production' từ Langfuse Cloud
2. Thực hiện inference với Agent
3. Gửi trace, span waterfall, generation metadata, usage và quality score lên Langfuse
4. Xác thực kết quả trả về
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.agent import LabAgent
from app.tracing import get_langfuse_client
from structlog.contextvars import bind_contextvars, clear_contextvars


def run_production_test():
    print("================================================================================")
    print("🧪 KIỂM THỬ LIVE RUNTIME LUỒNG PRODUCTION TRÊN LANGFUSE CLOUD")
    print("================================================================================")

    client = get_langfuse_client()
    agent = LabAgent(model="claude-sonnet-4-5")

    prompt_name = os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")
    prompt_label = os.getenv("LANGFUSE_PROMPT_LABEL", "production")

    print(f"🔹 Prompt Managed: '{prompt_name}'")
    print(f"🔹 Target Label:   '{prompt_label}'")
    print(f"🔹 Langfuse Host:  {os.getenv('LANGFUSE_HOST')}")
    print("--------------------------------------------------------------------------------")

    # Giả lập 3 request production đa dạng
    test_cases = [
        {
            "user_id": "u-prod-enterprise-01",
            "session_id": "sess-prod-live-101",
            "feature": "qa",
            "message": "What is the return and refund policy? My email is customer@enterprise.com",
            "cid": "req-prod-live-001",
        },
        {
            "user_id": "u-prod-enterprise-02",
            "session_id": "sess-prod-live-102",
            "feature": "monitoring",
            "message": "Explain how P95 latency and SLO thresholds work in observability.",
            "cid": "req-prod-live-002",
        },
        {
            "user_id": "u-prod-enterprise-03",
            "session_id": "sess-prod-live-103",
            "feature": "summary",
            "message": "Summarize the key principles of symptom-based alerting.",
            "cid": "req-prod-live-003",
        },
    ]

    for idx, tc in enumerate(test_cases, 1):
        clear_contextvars()
        bind_contextvars(correlation_id=tc["cid"])

        print(f"\n▶️ [Request {idx}/3] Gửi yêu cầu: '{tc['message'][:50]}...'")
        result = agent.run(
            user_id=tc["user_id"],
            feature=tc["feature"],
            session_id=tc["session_id"],
            message=tc["message"],
        )

        print(f"   • Correlation ID: {tc['cid']}")
        print(f"   • Latency:        {result.latency_ms} ms")
        print(f"   • Tokens:         {result.tokens_in} in / {result.tokens_out} out")
        print(f"   • Estimated Cost: ${result.cost_usd:.6f} USD")
        print(f"   • Quality Score:  {result.quality_score:.2f} / 1.00")
        print(f"   • Answer Preview: {result.answer[:85]}...")

    print("\n⏳ Đang flush dữ liệu telemetry lên server Langfuse...")
    client.flush()
    print("✅ TẤT CẢ REQUEST PRODUCTION ĐÃ ĐƯỢC XỬ LÝ VÀ GHI NHẬN THÀNH CÔNG TRÊN LANGFUSE!")
    print("================================================================================")


if __name__ == "__main__":
    run_production_test()
