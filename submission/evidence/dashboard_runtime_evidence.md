# Bằng chứng Runtime Dashboard (6 Panels Observability Evidence)

Dữ liệu được tính toán trực tiếp từ nguồn chuẩn `data/logs.jsonl` theo đúng đặc tả `config/dashboard.yaml` và `docs/dashboard-spec.md`.

---

## 1. Kết quả quan sát 6 Panel ở trạng thái Baseline vs Khi có Incident

| Panel ID | Panel Title | Đơn vị | Ngưỡng SLO / Threshold | Giá trị Baseline (Bình thường) | Giá trị Khi xảy ra `rag_slow` | Đánh giá trạng thái |
|---|---|---|---|---|---|---|
| **latency** | Latency Percentiles | `ms` | **P95 $\le$ 3000 ms** | P50 = 150 ms<br>P95 = 150 ms<br>P99 = 150 ms | P50 = 150 ms<br>**P95 = 2651 ms**<br>P99 = 2651 ms | **Cảnh báo vượt threshold challenge (2000ms)**, tiệm cận ngưỡng SLO 3000ms |
| **traffic** | Request Traffic | `req/min` | **Rate $\ge$ 1 req/min** | 10 req/phút | 15 req/phút (tổng tích lũy) | **Đạt SLO** |
| **errors** | Error Rate & Breakdown | `%` | **Error Rate $\le$ 2.0%** | 0.0% (0 errors) | 0.0% (0 errors) | **Đạt SLO** |
| **cost** | Cost Over Time | `USD` | **Total Cost $\le$ $2.5 USD** | $0.0238 USD | $0.0322 USD | **Đạt SLO** (Rất an toàn) |
| **tokens** | Input and Output Tokens | `tokens` | **Sum $\le$ 50,000 tokens** | Tokens In: 345<br>Tokens Out: 1,483 | Tokens In: 505<br>Tokens Out: 2,043 | **Đạt SLO** |
| **quality** | Quality Proxy Score | `score (0-1)` | **Mean Score $\ge$ 0.75** | Mean = 0.88 | Mean = 0.87 | **Đạt SLO** |

---

## 2. Validator Output Confirmation

```text
$ python scripts/validate_dashboard.py
HỢP LỆ: 6/6 panel có trong dashboard contract.
```
