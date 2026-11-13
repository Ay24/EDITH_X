# Benchmark & Credibility Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and execute an enterprise-grade benchmark and scenario credibility suite for EDITH-X derived from LMSYS RouteLLM, Microsoft LLMLingua, and ai-gateway-bench.

**Architecture:** A non-destructive, isolated benchmark testbed located in `tests/benchmarks/` containing calibrated datasets (RouteLLM tasks, LLMLingua compression documents, PII vectors), dedicated runners for Pareto accuracy, token density reduction, and internal gateway latency, with an automated executive report generator.

**Tech Stack:** Python 3.11+, pytest, pytest-asyncio, httpx, rich, EDITH-X Core Interfaces.

---

### File Structure Map

- **Datasets**:
  - `tests/benchmarks/datasets/routellm_eval.jsonl`: 50 categorized reasoning, coding, and routine tasks.
  - `tests/benchmarks/datasets/compression_eval.jsonl`: Long enterprise compliance documents with key entity needles.
  - `tests/benchmarks/datasets/pii_entropy_eval.jsonl`: Synthetic enterprise records with ground-truth secrets.
- **Runners & Tests**:
  - `tests/benchmarks/runners/test_routellm_pareto.py`: Evaluates Pareto routing tier distribution and theoretical cost reduction.
  - `tests/benchmarks/runners/test_compression_density.py`: Evaluates token compression ratio and domain entity recall.
  - `tests/benchmarks/runners/test_gateway_latency.py`: Measures pure internal gateway overhead and P99 latency percentiles.
  - `tests/benchmarks/runners/run_credibility_suite.py`: Master CLI runner generating the consolidated report.
- **Reports**:
  - `tests/benchmarks/reports/benchmark_report_latest.md`: Comprehensive executive report with statistics and tables.

---

### Task 1: Create Calibrated Evaluation Datasets

**Files:**
- Create: `tests/benchmarks/datasets/routellm_eval.jsonl`
- Create: `tests/benchmarks/datasets/compression_eval.jsonl`
- Create: `tests/benchmarks/datasets/pii_entropy_eval.jsonl`

- [x] **Step 1: Create RouteLLM evaluation dataset**
  Populate with 50 diverse queries labeled by ground-truth tier (`simple`, `medium`, `complex`).
- [x] **Step 2: Create LLMLingua compression evaluation dataset**
  Populate with verbose policy/legal/technical documents and target numerical/code needles.
- [x] **Step 3: Create PII & Secret evaluation dataset**
  Populate with synthetic test cases covering credit cards, SSNs, API tokens, and clean baselines.
- [x] **Step 4: Commit datasets**

---

### Task 2: Implement RouteLLM Pareto Cost-Quality Runner

**Files:**
- Create: `tests/benchmarks/runners/test_routellm_pareto.py`

- [x] **Step 1: Write RouteLLM Pareto test runner**
  Test Pareto routing decisions across the 50 dataset prompts; compute routing tier accuracy and cost savings vs. 100% GPT-4o baseline.
- [x] **Step 2: Run test with pytest**
  `pytest tests/benchmarks/runners/test_routellm_pareto.py -v`
- [x] **Step 3: Verify $\ge 85\%$ routing accuracy and $\ge 60\%$ cost reduction**
- [x] **Step 4: Commit**

---

### Task 3: Implement LLMLingua Compression & Entity Recall Runner

**Files:**
- Create: `tests/benchmarks/runners/test_compression_density.py`

- [x] **Step 1: Write compression density and entity recall test runner**
  Compress documents and assert token reduction $\ge 50\%$ with entity needle recall $\ge 90\%$.
- [x] **Step 2: Run test with pytest**
  `pytest tests/benchmarks/runners/test_compression_density.py -v`
- [x] **Step 3: Verify tests pass**
- [x] **Step 4: Commit**

---

### Task 4: Implement Gateway Latency Overhead & Jitter Runner

**Files:**
- Create: `tests/benchmarks/runners/test_gateway_latency.py`

- [x] **Step 1: Write async gateway latency benchmark runner**
  Benchmark L0 exact cache ($P_{99} < 1\text{ms}$), L0 semantic vector cache ($P_{99} < 2\text{ms}$), and internal pre-routing pipeline overhead.
- [x] **Step 2: Run test with pytest**
  `pytest tests/benchmarks/runners/test_gateway_latency.py -v`
- [x] **Step 3: Verify tests pass**
- [x] **Step 4: Commit**

---

### Task 5: Master Credibility Suite Orchestrator & Executive Report Generator

**Files:**
- Create: `tests/benchmarks/runners/run_credibility_suite.py`
- Output: `tests/benchmarks/reports/benchmark_report_latest.md`

- [x] **Step 1: Implement `run_credibility_suite.py` CLI**
  Executes all 3 modules in sequence, aggregates statistics, renders rich console tables, and writes out `benchmark_report_latest.md`.
- [x] **Step 2: Run simulation**
  `python tests/benchmarks/runners/run_credibility_suite.py`
- [x] **Step 3: Verify generated report formatting and data accuracy**
- [x] **Step 4: Commit and push to git**
