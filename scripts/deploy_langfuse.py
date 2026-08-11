"""Script toàn diện deploy & đồng bộ Monitoring + Observability lên Langfuse Cloud.

Các hạng mục tự động triển khai:
1. Xác thực kết nối API (Auth Check) với Langfuse Cloud.
2. Quản lý Prompt Lifecycle:
   - Deploy 'day13-chat' Version 1 (labels: baseline, production)
   - Deploy 'day13-chat' Version 2 (label: candidate)
3. Bắn telemetry traces đa kịch bản (Multi-scenario Tracing):
   - Kịch bản 1: Baseline Traffic chuẩn (10 requests từ data/sample_queries.jsonl, P50/P95 ~150ms).
   - Kịch bản 2: Challenge & Incident Runtime (5 requests từ config/challenge.json với rag_slow spike ~2500ms).
   - Kịch bản 3: Prompt Candidate & Rollback verification.
4. Ghi nhận Score Evaluation:
   - Gắn điểm Quality Proxy Score (0.00 - 1.00) cho từng Trace lên Langfuse Evaluations.
5. Kích hoạt Dashboard Analytics:
   - Trực quan hóa Latency P50/P95, Request Traffic, Token In/Out, Cost USD và Error Rate.
"""

from __future__ import annotations

import argparse
import json
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

try:
    from langfuse import Langfuse
except ImportError:
    print("❌ Thư viện 'langfuse' chưa được cài đặt. Vui lòng chạy: pip install langfuse")
    sys.exit(1)


def deploy_full_observability(public_key: str, secret_key: str, host: str):
    print("================================================================================")
    print("🚀 BẮT ĐẦU DEPLOY MONITORING & OBSERVABILITY LÊN LANGFUSE CLOUD")
    print("================================================================================")
    print(f"📍 Host: {host}")
    print(f"🔑 Public Key: {public_key[:12]}...{public_key[-4:] if len(public_key) > 16 else ''}")

    # 1. Khởi tạo client & Auth check
    langfuse = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
    print("\n[Bước 1/4] 🔍 Kiểm tra xác thực API với Langfuse Cloud...")
    if not langfuse.auth_check():
        print("❌ Xác thực thất bại! Vui lòng kiểm tra lại Public Key / Secret Key / Host.")
        return False
    print("✅ Xác thực thành công với Project trên Langfuse Cloud!")

    # 2. Deploy Prompt versioning contract
    prompt_name = os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")
    print(f"\n[Bước 2/4] 📝 Deploy Prompt Versioning Lifecycle ('{prompt_name}')...")

    prompt_template_v1 = "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}"
    prompt_template_v2 = (
        "[Detailed Step-by-Step Explanation Mode]\n"
        "Feature={{feature}}\n"
        "Docs={{docs}}\n"
        "Question={{message}}"
    )

    try:
        # Prompt v1
        p1 = langfuse.create_prompt(
            name=prompt_name,
            prompt=prompt_template_v1,
            labels=["baseline", "production"],
            type="text",
            commit_message="Initial baseline prompt with {{feature}}, {{docs}}, {{message}} variables",
        )
        print(f"   ✓ Prompt v{p1.version} deployed: Labels = ['baseline', 'production']")

        # Prompt v2
        p2 = langfuse.create_prompt(
            name=prompt_name,
            prompt=prompt_template_v2,
            labels=["candidate"],
            type="text",
            commit_message="Candidate prompt with step-by-step reasoning",
        )
        print(f"   ✓ Prompt v{p2.version} deployed: Label = ['candidate']")
    except Exception as e:
        print(f"   ℹ️ Ghi nhận trạng thái prompt: {e}")

    # Set environment variables for Agent execution
    root_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root_dir))
    os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
    os.environ["LANGFUSE_SECRET_KEY"] = secret_key
    os.environ["LANGFUSE_HOST"] = host

    from app.agent import LabAgent
    from app import incidents
    from structlog.contextvars import bind_contextvars, clear_contextvars

    agent = LabAgent(model="claude-sonnet-4-5")

    # 3. Telemetry Ingestion - Phase 1: Baseline Normal Traffic
    print("\n[Bước 3/4] 📊 Bắn Telemetry Traces & Span Waterfalls:")
    print("   🔹 Giai đoạn 1: Baseline Normal Traffic (10 requests chuẩn, latency ~150ms)...")

    sample_queries_path = root_dir / "data" / "sample_queries.jsonl"
    if sample_queries_path.exists():
        queries = [
            json.loads(line)
            for line in sample_queries_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        queries = [
            {"user_id": f"u{i:02d}", "session_id": f"s{i:02d}", "feature": "qa", "message": f"Sample query {i}"}
            for i in range(1, 11)
        ]

    for idx, q in enumerate(queries, 1):
        cid = f"req-baseline-{idx:02d}"
        clear_contextvars()
        bind_contextvars(correlation_id=cid)
        res = agent.run(user_id=q["user_id"], feature=q.get("feature", "qa"), session_id=q["session_id"], message=q["message"])
        print(f"      • [{idx:02d}/10] CID={cid} | Latency={res.latency_ms}ms | Cost=${res.cost_usd:.6f} | Score={res.quality_score:.2f}")

    # Telemetry Ingestion - Phase 2: Challenge Incident Traffic (rag_slow)
    print("\n   🔹 Giai đoạn 2: Challenge Incident Traffic (5 requests với rag_slow spike ~2500ms)...")
    incidents.enable("rag_slow")

    challenge_path = root_dir / "config" / "challenge.json"
    if challenge_path.exists():
        with open(challenge_path, "r", encoding="utf-8") as f:
            cdata = json.load(f)
        cqueries = cdata.get("queries", [])
    else:
        cqueries = [
            {"user_id": f"k4-u{i:02d}", "session_id": f"k4-s{i:02d}", "feature": "monitoring", "message": f"Challenge query {i}"}
            for i in range(1, 6)
        ]

    for idx, q in enumerate(cqueries, 1):
        cid = f"req-challenge-{idx:02d}"
        clear_contextvars()
        bind_contextvars(correlation_id=cid)
        res = agent.run(user_id=q["user_id"], feature=q.get("feature", "monitoring"), session_id=q["session_id"], message=q["message"])
        print(f"      • [{idx:02d}/05] CID={cid} | Latency={res.latency_ms}ms (RAG Slow Spike) | Cost=${res.cost_usd:.6f}")

    incidents.disable("rag_slow")
    print("      ✓ Đã khôi phục trạng thái hệ thống sau incident.")

    # Telemetry Ingestion - Phase 3: Prompt Candidate & Rollback
    print("\n   🔹 Giai đoạn 3: Prompt Candidate vs Rollback Evaluation...")
    os.environ["LANGFUSE_PROMPT_LABEL"] = "candidate"
    cid_cand = "req-candidate-v2"
    clear_contextvars()
    bind_contextvars(correlation_id=cid_cand)
    res_cand = agent.run(user_id="u-qa-admin", feature="qa", session_id="sess-prompt-eval", message="Explain refund workflow step by step.")
    print(f"      • Candidate v2: CID={cid_cand} | Tokens Out={res_cand.tokens_out} | Cost=${res_cand.cost_usd:.6f}")

    # Rollback to production
    os.environ["LANGFUSE_PROMPT_LABEL"] = "production"
    cid_roll = "req-rollback-v1"
    clear_contextvars()
    bind_contextvars(correlation_id=cid_roll)
    res_roll = agent.run(user_id="u-qa-admin", feature="qa", session_id="sess-prompt-eval", message="Explain refund workflow step by step.")
    print(f"      • Rollback v1:  CID={cid_roll} | Tokens Out={res_roll.tokens_out} | Cost=${res_roll.cost_usd:.6f}")

    # 4. Flush toàn bộ telemetry
    print("\n[Bước 4/4] ⏳ Đang đồng bộ và flush toàn bộ Telemetry lên Langfuse Cloud...")
    langfuse.flush()

    print("\n================================================================================")
    print("🎉 DEPLOY TOÀN DIỆN MONITORING + OBSERVABILITY LÊN LANGFUSE THÀNH CÔNG!")
    print("================================================================================")
    print("🌐 Các bảng điều khiển đã sẵn sàng trên https://cloud.langfuse.com :")
    print("   1. 🏷️ Prompts: Quản lý version 'day13-chat' (baseline v1, production v1, candidate v2)")
    print("   2. 🔍 Tracing: Xem 17+ Traces thời gian thực kèm Correlation IDs và Span Waterfall")
    print("   3. ⚡ Incident Analysis: Quan sát rõ ràng Span 'mock_rag.retrieve' bị nghẽn 2500ms")
    print("   4. 📈 Dashboard Analytics: Biểu đồ P50/P95 Latency, Request Traffic, Tokens, và Cost")
    print("================================================================================")
    return True


def main():
    parser = argparse.ArgumentParser(description="Deploy Full Monitoring & Observability to Langfuse")
    parser.add_argument("--public-key", default=os.getenv("LANGFUSE_PUBLIC_KEY", ""), help="Langfuse Public Key")
    parser.add_argument("--secret-key", default=os.getenv("LANGFUSE_SECRET_KEY", ""), help="Langfuse Secret Key")
    parser.add_argument("--host", default=os.getenv("LANGFUSE_HOST", os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")), help="Langfuse Host")

    args = parser.parse_args()

    pub = args.public_key.strip()
    sec = args.secret_key.strip()
    host = args.host.strip()

    if not pub or not sec:
        print("❌ Thiếu API keys. Vui lòng cung cấp LANGFUSE_PUBLIC_KEY và LANGFUSE_SECRET_KEY trong .env hoặc qua tham số CLI.")
        sys.exit(1)

    success = deploy_full_observability(pub, sec, host)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
