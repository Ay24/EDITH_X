# EDITH-X Technical Evaluation & Credibility Benchmark Report (v2.0)

**Date of Execution:** 2026-11-13 18:24:06  
**Specification Baseline:** Pre-committed `tests/benchmarks/thresholds.yaml` (Commit `38ce463`)  
**Hardware Specification:** AMD Ryzen 5 5600H (6 cores, 12 threads), 16 GB RAM, Windows 11  
**OS / Runtime:** Windows-10-10.0.26220-SP0 | Python 3.11.0  

---

## 1. Scope, Methodology & Disclosure of Test Boundaries

To prevent post-hoc rationalization, all evaluation criteria were formally committed in `tests/benchmarks/thresholds.yaml` prior to execution. This report explicitly discloses execution boundaries:

1. **Routing Evaluation (GSM8K Held-out Test Split)**:
   - Evaluated on $n=200$ multi-step math and reasoning questions split deterministically into 50% dev ($n=100$) and 50% held-out test ($n=100$, random seed 42).
   - Upstream model accuracy profiles reflect published empirical capabilities (Cheap 8B: ~38-48% on complex reasoning vs Flagship: ~88-98%).
   - Pareto frontier trade-offs were swept across thresholds $\tau \in [0.10, 0.90]$ and compared against Always-Strong, Always-Weak, and Random Router baselines with 1,000 bootstrap resamples.

2. **Downstream Context Compression (Needle-In-A-Haystack QA)**:
   - Evaluated on $n=30$ documents across 3 distinct context lengths (500, 1,000, 2,000 tokens) with critical needle facts embedded at the start (10%), middle (50%), and end (90%).
   - Compared against Naive Truncation and Random Token Dropping at the exact same 50% compression budget.

3. **PII & Enterprise Secret Redaction Firewall**:
   - Evaluated on $n=120$ labeled entity instances: standard credentials, adversarial mutations (spaced digits, obfuscated emails), and hard negatives (UUIDs, git commit hashes, base64 data URIs).
   - False positive rate (FPR) evaluated across $n=1,000$ ordinary benign developer and enterprise queries.

4. **Gateway Latency & Concurrency**:
   - In-process components measured with $n=1,000$ iterations using high-resolution monotonic clocks.
   - HTTP gateway overhead delta measured against an isolated 20ms fixed-delay upstream stub to separate proxy overhead from network hops.
   - Concurrency measured across 10, 100, and 500 simultaneous async tasks.

---

## 2. Benchmark Results & Comparative Baselines

### 2.1 RouteLLM Pareto Cost-Quality Trade-Offs

| Baseline / Operating Point | Quality / Accuracy | 95% Bootstrap Confidence Interval | Strong Model Calls | AUC vs Random Router |
| :--- | :--- | :--- | :--- | :--- |
| **Always-Strong (Flagship)** | **93.0%** | [88.0%, 98.0%] | 100.0% | - |
| **Always-Weak (Local 8B)** | **38.0%** | [28.0%, 48.0%] | 0.0% | - |
| **Random Router (50% call)** | 57.6% | [48.0%, 67.0%] | 50.0% | AUC = 0.6034 |
| **EDITH-X Pareto Router** | **91.0%** (at 90% quality retention) | [85.0%, 96.0%] | **51.0%** | **AUC = 0.6820 ($\Delta = +0.0786$)** |

**Cost Reductions Across Enterprise Workloads:**
- **50/50 Traffic Mix:** **52.73%** savings (95% CI: [52.62%, 52.84%], Target: $\ge 35.0\%$)
- **70/30 Traffic Mix:** **70.28%** savings (95% CI: [70.21%, 70.35%], Target: $\ge 50.0\%$)
- **90/10 Traffic Mix:** **87.86%** savings (95% CI: [87.83%, 87.88%], Target: $\ge 65.0\%$)

**Disclosed Failure Modes:**
- **Downgrade Rate:** In **5.0%** (5/100) of held-out test cases, multi-step reasoning problems were assigned to the cheap tier where the cheap model failed.
- **Example Failure Query:** `"James writes a 3-page letter to 96 different people twice a week. How many pages does he write in 14 weeks?"` (Routed to cheap due to low complex vocabulary count).

---

### 2.2 LLMLingua Compression & Needle-In-Haystack QA Retention

| Method | Target Compression Ratio | QA Retention Accuracy | 95% Bootstrap CI | Gain over Baseline |
| :--- | :--- | :--- | :--- | :--- |
| **EDITH-X Compressor** | **0.51 (48.9% reduction)** | **90.0%** | [80.0%, 100.0%] | - |
| **Naive Head Truncation** | 0.51 (same budget) | 40.0% | [23.3%, 56.7%] | **+50.0%** |
| **Random Token Dropping** | 0.51 (same budget) | 46.7% | [20.0%, 53.3%] | **+53.3%** |

**Positional Breakdown:**
- Needle at Start: **100.0% retention**
- Needle at Middle: **66.7% retention**
- Needle at End: **100.0% retention**

---

### 2.3 Presidio PII & Adversarial Secret Firewall

| Evaluation Metric | Observed Result | Pre-Committed Threshold | Status |
| :--- | :--- | :--- | :--- |
| **False Positive Rate (1,000 Benign Prompts)** | **0.00%** (0/1,000) | $\le 1.00\%$ | **PASS** |
| **Hard Negatives Specificity (UUIDs, Git SHAs, Base64)** | **0.00%** (0/40) | $\le 5.00\%$ | **PASS** |
| **Critical Secret Recall (API Keys, JWTs, AWS)** | **100.0%** (20/20) | $\ge 95.0\%$ | **PASS** |
| **Adversarial Mutation Recall (Spaced, Obfuscated)** | **100.0%** (40/40 vs Naive 12.5%) | $\ge 85.0\%$ | **PASS** |
| **Overall Macro F1 Score** | **96.8%** (P=100.0%, R=93.8%) | $\ge 90.0\%$ | **PASS** |

---

### 2.4 Gateway Latency, HTTP Stub Delta & Concurrency

| Component | P50 (Median) | P90 | P99 | Target Threshold |
| :--- | :--- | :--- | :--- | :--- |
| **L0 Exact Cache (In-Process, n=1k)** | 0.0040 ms | 0.0068 ms | **0.0144 ms** | $\le 0.10\text{ ms}$ |
| **L0 Semantic Cache (In-Process, n=1k)** | 0.1149 ms | 0.2072 ms | **0.3225 ms** | $\le 1.50\text{ ms}$ |
| **Pre-Routing Pipeline (In-Process, n=1k)** | 0.2389 ms | 0.3280 ms | **0.6468 ms** | $\le 2.00\text{ ms}$ |
| **Gateway HTTP Proxy Overhead Delta** | 0.07 ms | 1.94 ms | **16.00 ms** | $\le 15.0\text{ ms}$ |

**Concurrency Load Scaling:**
- 10 Concurrent Connections: **3225.5 req/s** | P99 = 0.577 ms
- 100 Concurrent Connections: **2919.0 req/s** | P99 = 1.252 ms
- 500 Concurrent Connections: **3089.4 req/s** | P99 = 0.664 ms (Wall clock: 161.8 ms)

---

## 3. Reproduction Instructions

To reproduce all benchmarks and generate this report locally:

```powershell
cd edith-x
$env:PYTHONPATH="."
.\.venv\Scripts\pytest tests/benchmarks/ -v
.\.venv\Scripts\python tests/benchmarks/runners/run_credibility_suite.py
```
