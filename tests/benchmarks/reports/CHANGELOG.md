# Benchmark Suite Audit & Metric Changelog

This document tracks all shifted numbers, methodology upgrades, and architectural rationale following the technical audit of `tests/benchmarks/`.

| Evaluation Dimension | Previous Value (v1.0) | Audited Value (v2.0) | Rationale for Shift |
| :--- | :--- | :--- | :--- |
| **Routing Accuracy / Fidelity** | 98.0% (Circular self-authored keywords) | **91.0%** (GSM8K held-out test split, n=100) | Eliminated self-authored keyword contamination; evaluated on real mathematical reasoning queries with bootstrap 95% CIs. |
| **Pareto Area Under Curve (AUC)** | Not evaluated (Assumed single 70/30 mix) | **AUC = 0.6820 ($\Delta = +0.0786$ vs Random)** | Added full threshold sweep ($\tau \in [0.1, 0.9]$) and comparative baselines (Always-Strong, Always-Weak, Random Router). |
| **Enterprise Cost Reduction** | 68.5% (Estimated single traffic split) | **70.28%** (70/30 mix, 95% CI: [70.21%, 70.35%]) | Evaluated across multiple empirical distributions (50/50: 52.7%, 70/30: 70.3%, 90/10: 87.9%). |
| **Downgrade Failure Rate** | 0% disclosed | **5.0%** (5/100 test samples) | Explicitly disclosed concrete failure cases where the router assigned multi-step reasoning queries to the cheap tier. |
| **Context Compression Evaluation** | 5 documents (~130 tokens each, matching regex) | **Needle-In-Haystack QA across 500, 1000, 2000 tokens (n=30)** | Replaced hand-crafted filler sentences with multi-length technical text testing downstream QA answer survival at start/mid/end positions. |
| **Downstream QA Retention** | String match on 4 hand-picked needles | **90.0% retention** (+50.0% over truncation, +43.3% over random drop) | Tested against Naive Truncation (40.0%) and Random Token Dropping (46.7%) at the exact same compression budget. |
| **Benign Prompts Sample Size** | 5 prompts | **1,000 real benign developer prompts** | Tested false positive rate on 1,000 real prompts; observed 0 false alarms (0.00% FPR). |
| **Adversarial PII Recall** | 0 adversarial cases tested | **100.0%** (40/40 vs Naive Regex 12.5%) | Added spaced credit card digits, obfuscated emails (`[at]`), and hyphenated API tokens. |
| **Hard Negatives Specificity** | Not tested | **0.00% FPR on UUIDs, Git commit SHAs, and Base64** | Added hard-negative exemption filters in high-entropy detection to eliminate false positives on developer hashes and IDs. |
| **Gateway Latency Reporting** | Conflated in-process loop with HTTP | **Partitioned: In-Process P99 = 0.647 ms, HTTP Stub Delta P99 = 16.00 ms** | Disclosed hardware (AMD Ryzen 5 5600H, 16GB RAM) and isolated gateway proxy overhead from HTTP server hops using a 20ms upstream stub. |
