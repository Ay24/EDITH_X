# Design Specification: EDITH-X Benchmark & Credibility Suite

**Date**: 2026-11-13  
**Status**: Approved  
**Author**: Antigravity (Pair Programming with User)  
**Target System**: EDITH-X Enterprise AI Runtime  

---

## 1. Executive Summary

To validate the production viability, cost reduction, quality retention, and low-latency claims of the EDITH-X Enterprise AI Runtime, this specification establishes an automated **Benchmark & Credibility Suite**.

Inspired by industry-standard open-source evaluation frameworks:
1. **LMSYS / UC Berkeley `RouteLLM`**: Cost-Quality Pareto frontier routing evaluation across simple, medium, and complex reasoning tasks.
2. **Microsoft Research `LLMLingua`**: Information-density context compression and critical entity recall on verbose enterprise documentation.
3. **`BerriAI/ai-gateway-bench` & Kong k6 Benchmarks**: Pure gateway internal latency overhead, concurrency throughput, and P99 jitter under concurrent virtual user load.

---

## 2. Directory Structure

The benchmark suite is placed within the `edith-x` repository under `tests/benchmarks/`:

```
edith-x/tests/benchmarks/
├── datasets/
│   ├── routellm_eval.jsonl           # 50 calibrated reasoning, coding, and routine tasks
│   ├── compression_eval.jsonl        # Long enterprise compliance/technical texts with key entity needles
│   └── pii_entropy_eval.jsonl        # Synthetic enterprise data vectors with ground-truth PII/secrets
├── runners/
│   ├── test_routellm_pareto.py       # Pareto cost-complexity evaluation runner
│   ├── test_compression_density.py  # Prompt compression & entity recall runner
│   ├── test_gateway_latency.py       # Pure gateway internal overhead & concurrent latency runner
│   └── run_credibility_suite.py      # Master orchestrator producing Markdown/JSON reports
└── reports/
    └── benchmark_report_latest.md    # Auto-generated comprehensive executive audit report
```

---

## 3. Detailed Benchmark Modules

### Module A: LMSYS RouteLLM Pareto Cost-Quality Benchmark (`test_routellm_pareto.py`)
- **Objective**: Verify that the Pareto Model Router correctly routes queries across Tiers (`L1_local`, `L2_compressed`, `L3_cloud`) based on intrinsic complexity, maximizing cost reduction while maintaining zero degradation on routine tasks.
- **Dataset (`routellm_eval.jsonl`)**:
  - 50 categorized prompts:
    - 20 Simple Tasks: Formatting, basic regex, lookup, single-fact queries (Ground truth: `L1_local` / `L2_compressed`).
    - 15 Medium Tasks: Summarization, text restructuring, basic business logic (Ground truth: `L2_compressed`).
    - 15 Complex Tasks: Distributed system design, formal invariant proofs, complex algorithms (Ground truth: `L3_cloud`).
- **Success Criteria**:
  - Routing Tier Accuracy: $\ge 85\%$.
  - Theoretical Token Spend Reduction: $\ge 60\%$ compared to an always-frontier (`100% GPT-4o`) baseline.

### Module B: Microsoft LLMLingua Information-Density Benchmark (`test_compression_density.py`)
- **Objective**: Validate that the information-density compressor sheds boilerplate tokens while preserving critical domain entities.
- **Dataset (`compression_eval.jsonl`)**:
  - Enterprise policy documents (300 to 1,200 tokens) embedded with specific numerical needles (dollar amounts, deadlines, compliance codes, server names).
- **Evaluation**:
  - Original prompt size $vs.$ Compressed prompt size.
  - Entity Recall: Checks presence of ground-truth entity needles in the compressed text.
- **Success Criteria**:
  - Compression Token Reduction: $\ge 50\%$.
  - Critical Entity Recall: $\ge 90\%$.

### Module C: Gateway Overhead & Concurrency Benchmark (`test_gateway_latency.py`)
- **Objective**: Measure the pure internal latency overhead added by EDITH-X (Intent classification + Policy firewall + L0 Cache check + Pareto routing) without upstream model variance.
- **Evaluation**:
  - Simulates 50 concurrent requests using `asyncio` and `httpx`.
  - Measures latency percentiles ($P_{50}$, $P_{90}$, $P_{99}$).
- **Success Criteria**:
  - L0 Exact Cache Latency: $P_{99} < 1.0\text{ms}$.
  - L0 Semantic Vector Latency: $P_{99} < 2.0\text{ms}$.
  - Overall Gateway Internal Overhead: $P_{99} < 5.0\text{ms}$.

### Module D: Executive Credibility Report Generator (`run_credibility_suite.py`)
- **Objective**: An executable CLI orchestrator that runs all tests, calculates cumulative statistics, and formats an executive report at `tests/benchmarks/reports/benchmark_report_latest.md`.

---

## 4. Architectural Safety & Isolation

- All benchmark modules are completely non-destructive and read-only.
- Upstream LLM calls use isolated mock handlers during benchmarking to guarantee deterministic measurements of pure gateway performance.
- Results are saved to durable markdown files for inclusion in documentation and investor/stakeholder decks.
