# Document Pipeline, Output Services, Streaming & Tool-Calling Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Priority 1 (M15 Document Pipeline with per-chunk PII redaction and map-reduce caching, M16 Output Services with multi-format generation and output DLP) and Priority 2 (Native SSE Streaming with live redaction and OpenAI-compatible function-calling / tool-execution).

**Architecture:** Create modular `edith_x/modules/document` containing `DocumentPipeline` (parsing, chunking, PII redaction, map-reduce summarization with `file_hash + prompt_hash` caching) and `OutputServices` (generating PDF, PPTX via `python-pptx`, XLSX via `xlsxwriter`, with Output DLP). Extend REST API with `/v1/files` and `/edith/v1/files/summarize`. Extend `/v1/chat/completions` with native SSE streaming and OpenAI tool-calling schema compatibility.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, python-pptx, xlsxwriter, reportlab / pure-python PDF generator, pytest, pytest-asyncio.

---

### Task 1: M15 Document Pipeline — Parsing, Chunking & Per-Chunk PII Redaction

**Files:**
- Create: `edith_x/modules/document/__init__.py`
- Create: `edith_x/modules/document/pipeline.py`
- Create: `tests/test_document_pipeline.py`

- [ ] **Step 1: Write failing tests for DocumentPipeline**
  - Test 1: Parse plain text and CSV/markdown files with SHA-256 deduplication.
  - Test 2: Verify per-chunk PII redaction (e.g. credit cards and Aadhaar in document chunks are redacted before storage or summary).
  - Test 3: Map-Reduce summarization: chunks summarized into hierarchical final synthesis.
  - Test 4: Cache hit on `file_hash + prompt_hash`: repeat summaries return from cache with $0 cost.

- [ ] **Step 2: Run test to verify it fails**
  - Run: `.venv\Scripts\python -m pytest tests/test_document_pipeline.py -v`
  - Expected: FAIL

- [ ] **Step 3: Implement DocumentPipeline**
  - In `pipeline.py`:
    - `parse_document(file_bytes: bytes, filename: str) -> ParsedDocument`
    - `chunk_document(text: str, chunk_size: int = 500) -> list[str]`
    - Redact PII on every chunk using `PIIFirewall`.
    - `summarize_document(parsed: ParsedDocument, org_id: str, prompt: str = "") -> DocumentSummaryResult`:
      - Checks cache using `hashlib.sha256(f"{org_id}:{parsed.sha256}:{prompt}".encode())`.
      - If miss: maps across chunks, reduces intermediate summaries, stores in cache.

- [ ] **Step 4: Run test to verify it passes**
  - Run: `.venv\Scripts\python -m pytest tests/test_document_pipeline.py -v`
  - Expected: PASS

---

### Task 2: M16 Output Services — Document Generation (PDF, PPTX, XLSX) & Output DLP

**Files:**
- Create: `edith_x/modules/document/output.py`
- Create: `tests/test_output_services.py`
- Modify: `edith_x/modules/execution/service.py`

- [ ] **Step 1: Write failing tests for OutputServices**
  - Test 1: Generate PDF report with headers, metadata, and sections.
  - Test 2: Generate PPTX presentation with slides and bullet points using `python-pptx`.
  - Test 3: Generate XLSX workbook with tabular data using `xlsxwriter`.
  - Test 4: Output DLP verification: any card or secret in the generated document input is automatically redacted.
  - Test 5: FastMCP Tool Registration: tool `generate_document` executable through `EnterpriseToolRegistry`.

- [ ] **Step 2: Run test to verify it fails**
  - Run: `.venv\Scripts\python -m pytest tests/test_output_services.py -v`
  - Expected: FAIL

- [ ] **Step 3: Implement OutputServices and register tool**
  - Implement `OutputServices` in `output.py` supporting `pdf`, `pptx`, `xlsx`, `markdown`.
  - Apply `PIIFirewall.redact()` on all content prior to document compilation.
  - Register `generate_document` in `EnterpriseToolRegistry`.

- [ ] **Step 4: Run test to verify it passes**
  - Run: `.venv\Scripts\python -m pytest tests/test_output_services.py -v`
  - Expected: PASS

---

### Task 3: Priority 2 — Native SSE Streaming with Live Redaction

**Files:**
- Modify: `edith_x/interfaces/rest/app.py`
- Create: `tests/test_streaming_live_redaction.py`

- [ ] **Step 1: Write failing tests for live streaming redaction**
  - Test 1: POST `/v1/chat/completions` with `stream=True` returns `text/event-stream` with valid `data: {"id":"chatcmpl-...","choices":[{"delta":{"content":"..."}}]}`.
  - Test 2: Live token streaming redacts card numbers and secrets before delivering chunks over SSE.
  - Test 3: Stream terminates cleanly with `data: [DONE]`.

- [ ] **Step 2: Run test to verify it fails**
  - Run: `.venv\Scripts\python -m pytest tests/test_streaming_live_redaction.py -v`
  - Expected: FAIL

- [ ] **Step 3: Implement native streaming in REST app**
  - Refactor `_stream_response` in `app.py` to stream tokens, buffer tokens to prevent leaking split entities, and yield SSE compliant JSON chunks.

- [ ] **Step 4: Run test to verify it passes**
  - Run: `.venv\Scripts\python -m pytest tests/test_streaming_live_redaction.py -v`
  - Expected: PASS

---

### Task 4: Priority 2 — OpenAI Function Calling & Tool-Execution Loop

**Files:**
- Modify: `edith_x/interfaces/rest/app.py`
- Modify: `edith_x/modules/planner/service.py`
- Create: `tests/test_function_calling_openai_compat.py`

- [ ] **Step 1: Write failing tests for function calling compatibility**
  - Test 1: POST `/v1/chat/completions` with `tools=[...]` passes tool schemas into planner/execution.
  - Test 2: When user asks `"What is 450 * 1.18?"` with calculator tool enabled, system invokes `calculator` in `EnterpriseToolRegistry` and returns structured `tool_calls` and final answer.
  - Test 3: Structured tool call results match standard OpenAI response format.

- [ ] **Step 2: Run test to verify it fails**
  - Run: `.venv\Scripts\python -m pytest tests/test_function_calling_openai_compat.py -v`
  - Expected: FAIL

- [ ] **Step 3: Implement tool routing and execution loop**
  - In `app.py`: accept `tools` and `tool_choice` in `ChatCompletionRequest`.
  - In `PlannerService`: if tools are requested, allow planner to execute matching tools from `EnterpriseToolRegistry` and include `tool_calls` in completion choices.

- [ ] **Step 4: Run test to verify it passes**
  - Run: `.venv\Scripts\python -m pytest tests/test_function_calling_openai_compat.py -v`
  - Expected: PASS

---

### Task 5: REST API Integration for File Endpoints & Regression Verification

**Files:**
- Modify: `edith_x/interfaces/rest/app.py`
- Create: `tests/test_file_api_endpoints.py`

- [ ] **Step 1: Write failing test for `/v1/files` and `/edith/v1/files/summarize`**
  - Upload file multipart/form-data.
  - Call document summarization endpoint and verify cached repeat summary.

- [ ] **Step 2: Implement endpoints in `app.py`**
  - Wire `DocumentPipeline` into container and expose endpoints.

- [ ] **Step 3: Run all tests to verify 100% pass rate**
  - Run: `.venv\Scripts\python -m pytest tests/ -v`

- [ ] **Step 4: Sync to `D:\EDITH-Enterprise\edith-x\` and git commit & push**
