# Enterprise Technical Drawbacks Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all 12 enterprise architectural fixes across EDITH-X: entity-aware numerical cache guards, RBAC-partitioned caching & invalidation, fail-closed RAG retrieval, global/regional PII checksums (Aadhaar/PAN/NHS/IBAN), reversible pseudonymization vault, output DLP, untrusted RAG envelopes, data residency failover governance, and aligned enterprise presentation.

**Architecture:** Extend existing modules using clean OOP and standard library / existing dependencies: add `EphemeralVault` for reversible pseudonymization, enhance `PIIFirewall` with Verhoeff/Mod11/ISO7064 algorithms, add numeric/entity guards & RBAC namespacing to `SemanticCache`, add fail-closed RAG diagnostics, wire Output DLP into REST app, and update router residency policy.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, pytest, python-pptx, standard library (`hmac`, `hashlib`, `re`, `time`, `collections`, `math`).

---

### Task 1: Numerical & Entity Discrepancy Guard and RBAC Partitioning in Cache (Points 1 & 2)

**Files:**
- Create: `tests/test_cache_enterprise_guards.py`
- Modify: `edith_x/modules/optimization/cache.py`
- Modify: `edith_x/modules/optimization/service.py`
- Modify: `edith_x/modules/planner/service.py`

- [ ] **Step 1: Write failing tests for numerical/entity discrepancy and RBAC cache partitioning**
  - Test 1: `"What was Q3 2024 revenue?"` vs `"What was Q3 2025 revenue?"` must return `None` (cache miss) despite high character n-gram overlap.
  - Test 2: `"Transfer $500 to Alice"` vs `"Transfer $500 to Bob"` must return `None`.
  - Test 3: Cache entries tagged with `user_role="admin"` are not served to `user_role="junior"`.
  - Test 4: Document invalidation `invalidate_by_document("doc_hr_123")` purges associated cached queries.

- [ ] **Step 2: Run test to verify it fails**
  - Run: `.venv\Scripts\python -m pytest tests/test_cache_enterprise_guards.py -v`
  - Expected: FAIL

- [ ] **Step 3: Implement Entity & Number Extraction and RBAC Partitioning**
  - In `cache.py`:
    - Add `_extract_entities_and_numbers(query: str) -> tuple[set[str], set[str]]` extracting digits/percentages/quarters/years/capitalized entity words.
    - In `get()`: compare query's extracted numbers and entities against cached entry's extracted numbers and entities. If they differ, abort candidate match.
    - Add `user_role: str = "default"`, `acl_scope: str = "public"`, `doc_ids: list[str] = []` to `CacheEntry`.
    - Update `set()` and hash key generator to namespace by `f"{org_id}:{user_role}:{acl_scope}"` when `acl_scope != "public"`.
    - Implement `invalidate_by_document(doc_id: str)` and `invalidate_by_tag(tag: str)`.
  - Thread through `OptimizationService` and `PlannerService`.

- [ ] **Step 4: Run test to verify it passes**
  - Run: `.venv\Scripts\python -m pytest tests/test_cache_enterprise_guards.py -v`
  - Expected: PASS

---

### Task 2: Fail-Closed Vector Retrieval Policy (Point 3)

**Files:**
- Create: `tests/test_knowledge_fail_closed.py`
- Modify: `edith_x/modules/knowledge/service.py`
- Modify: `edith_x/modules/planner/service.py`

- [ ] **Step 1: Write failing tests for fail-closed RAG behavior**
  - Test 1: When Qdrant connection raises an exception and `strict_rag=True`, `knowledge.retrieve()` raises `ServiceUnavailableError` (or returns status `DEGRADED_OFFLINE` with `success=False`) instead of silently returning mock empty results.
  - Test 2: Planner marks state `rag_degraded: True` and returns explicit diagnostic metadata when knowledge retrieval is unavailable.

- [ ] **Step 2: Run test to verify it fails**
  - Run: `.venv\Scripts\python -m pytest tests/test_knowledge_fail_closed.py -v`
  - Expected: FAIL

- [ ] **Step 3: Implement fail-closed retrieval and degraded state tracking**
  - In `knowledge/service.py`: Add `strict_mode: bool = True` to `KnowledgeService`. When Qdrant fails, if `strict_mode` is enabled, log error and return structured error result with `status="DEGRADED_OFFLINE"` and `chunks=[]` instead of fake canned items.
  - In `planner/service.py`: When `retrieve` returns `DEGRADED_OFFLINE`, flag `state["rag_degraded"] = True` and set header / response metadata `rag_status: "DEGRADED_OFFLINE"`.

- [ ] **Step 4: Run test to verify it passes**
  - Run: `.venv\Scripts\python -m pytest tests/test_knowledge_fail_closed.py -v`
  - Expected: PASS

---

### Task 3: Global & Regional PII Checksums (Aadhaar, PAN, NHS, IBAN, DOB) & Calibrated Entropy (Point 4)

**Files:**
- Create: `tests/test_global_pii_checksums.py`
- Modify: `edith_x/modules/policy/firewall.py`

- [ ] **Step 1: Write failing tests for international PII checksums and false positive reduction**
  - Test 1: Indian Aadhaar validation (12 digits passing Verhoeff checksum) is redacted as `[REDACTED_AADHAAR]`; invalid 12 digits (like arbitrary timestamp or serial number) are NOT redacted.
  - Test 2: Indian PAN card (e.g. `ABCDE1234F`) is redacted as `[REDACTED_PAN]`.
  - Test 3: UK NHS number (10 digits passing Modulus 11) is redacted as `[REDACTED_NHS]`.
  - Test 4: UUIDs and Git commit hashes without secret context are NOT redacted (0% false positives on developer text).
  - Test 5: Date of Birth with context (`DOB: 15/08/1992`) is redacted as `[REDACTED_DOB]`.

- [ ] **Step 2: Run test to verify it fails**
  - Run: `.venv\Scripts\python -m pytest tests/test_global_pii_checksums.py -v`
  - Expected: FAIL

- [ ] **Step 3: Implement Verhoeff, Modulus 11, Indian PAN, and Context-Boosted Entropy**
  - In `firewall.py`:
    - Implement Verhoeff algorithm table multiplication for Aadhaar verification.
    - Implement Modulus 11 algorithm for UK NHS verification.
    - Implement PAN pattern: `r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"`.
    - Implement DOB pattern with context keywords (`dob`, `born`, `birth date`, `date of birth`).
    - Tighten high-entropy token check to require proximity to secret keywords.

- [ ] **Step 4: Run test to verify it passes**
  - Run: `.venv\Scripts\python -m pytest tests/test_global_pii_checksums.py -v`
  - Expected: PASS

---

### Task 4: Reversible Ephemeral Pseudonymization Vault (Point 5)

**Files:**
- Create: `edith_x/modules/policy/vault.py`
- Create: `tests/test_ephemeral_vault.py`
- Modify: `edith_x/modules/policy/service.py`
- Modify: `edith_x/interfaces/rest/app.py`

- [ ] **Step 1: Write failing tests for Ephemeral Pseudonymization Vault**
  - Test 1: `vault.tokenize("Send card 4532015012345678 to test@domain.com")` returns surrogate tokens `{{CARD_REF_...}}` and `{{EMAIL_REF_...}}` with a `vault_session_id`.
  - Test 2: `vault.detokenize("Processed {{CARD_REF_...}} successfully", session_id, mask_mode="partial")` restores text with masked card `4532 **** **** 5678`.
  - Test 3: Vault entries expire and are pruned after TTL (e.g., 60 seconds).

- [ ] **Step 2: Run test to verify it fails**
  - Run: `.venv\Scripts\python -m pytest tests/test_ephemeral_vault.py -v`
  - Expected: FAIL

- [ ] **Step 3: Implement EphemeralVault and wire into PolicyService and REST App**
  - Create `edith_x/modules/policy/vault.py` with `EphemeralVault` class, thread-safe session map with TTL and LRU expiration.
  - Wire into `PolicyService.tokenize()` and `PolicyService.detokenize()`.
  - In `app.py`: Support `X-EDITH-Pseudonymize: true` header to tokenize incoming prompts, execute through planner, and detokenize response before delivery to caller.

- [ ] **Step 4: Run test to verify it passes**
  - Run: `.venv\Scripts\python -m pytest tests/test_ephemeral_vault.py -v`
  - Expected: PASS

---

### Task 5: Output DLP & Untrusted RAG Envelopes (Point 6)

**Files:**
- Create: `tests/test_output_dlp_and_rag_envelopes.py`
- Modify: `edith_x/interfaces/rest/app.py`
- Modify: `edith_x/modules/planner/service.py`

- [ ] **Step 1: Write failing tests for Output DLP and Untrusted RAG Envelopes**
  - Test 1: If model output contains an unmasked credit card or private key, REST response sanitizes output via Output DLP before delivering to client.
  - Test 2: Planner formats retrieved knowledge chunks into `<retrieved_untrusted_context source="...">...</retrieved_untrusted_context>` and prefixes safety guard instructions against indirect injection.

- [ ] **Step 2: Run test to verify it fails**
  - Run: `.venv\Scripts\python -m pytest tests/test_output_dlp_and_rag_envelopes.py -v`
  - Expected: FAIL

- [ ] **Step 3: Implement Output DLP in REST app and XML envelopes in Planner**
  - In `app.py`: Apply `policy_svc.sanitize_payload()` to `final_response` before returning JSON response in `/edith/v1/run` and `/v1/chat/completions`.
  - In `planner/service.py`: Format retrieved chunks in `_node_retrieve()` using XML envelope structure with untrusted context guidance.

- [ ] **Step 4: Run test to verify it passes**
  - Run: `.venv\Scripts\python -m pytest tests/test_output_dlp_and_rag_envelopes.py -v`
  - Expected: PASS

---

### Task 6: Data Residency Constrained Routing (Point 9)

**Files:**
- Create: `tests/test_residency_constrained_routing.py`
- Modify: `edith_x/modules/router/service.py`

- [ ] **Step 1: Write failing tests for data residency routing**
  - Test 1: When request has `data_residency="EU"`, router selects strictly from EU-compliant models; non-EU models are excluded from candidate and fallback pools.
  - Test 2: If all EU models fail/unavailable, router raises `DataResidencyViolationError` (or returns fail-closed 503) rather than routing to US models.

- [ ] **Step 2: Run test to verify it fails**
  - Run: `.venv\Scripts\python -m pytest tests/test_residency_constrained_routing.py -v`
  - Expected: FAIL

- [ ] **Step 3: Implement residency filtering in RouterService**
  - Add region metadata to models in `RouterService`.
  - Filter available models by `data_residency` if specified in request context.

- [ ] **Step 4: Run test to verify it passes**
  - Run: `.venv\Scripts\python -m pytest tests/test_residency_constrained_routing.py -v`
  - Expected: PASS

---

### Task 7: Update Pitch Deck & Documentation (Points 7, 8, 10, 11, 12)

**Files:**
- Modify: `scripts/generate_pitch_deck.py`
- Output: `docs/presentations/EDITH_X_Enterprise_Pitch_Deck.pptx`

- [ ] **Step 1: Update slide generator script with accurate benchmarks, pricing, and positioning**
  - Slide 4 (Architecture): Highlight Ephemeral Vault & Hybrid RAG Envelopes.
  - Slide 6 (Cache): Disclose Numerical/Entity Guard + Local ONNX L1 + Composite RBAC partitioning.
  - Slide 7 (PII & Compliance): Include India DPDP Act 2023, Aadhaar/PAN/NHS/IBAN checksums, frame as "Technical Controls Enabling Compliance".
  - Slide 9 (Benchmarks & Latency): Replace GSM8K with FinanceBench/RAGAS enterprise benchmarks, disclose full latency waterfall.
  - Slide 10 (Model Pricing & Economics): Update late-2026 pricing cards and factor provider prompt caching (projecting 45-60% net savings).
  - Slide 11 (Competitive Matrix): Clear comparison vs LiteLLM, Portkey, Cloudflare AI Gateway.
- [ ] **Step 2: Run script to regenerate presentation**
  - Run: `.venv\Scripts\python scripts/generate_pitch_deck.py`
  - Verify PPTX file generated without error.

---

### Task 8: Full Regression & Production Simulation Verification

**Files:**
- Run: Full unit test suite
- Synchronize: Mirror all changes to `D:\EDITH-Enterprise\edith-x\`

- [ ] **Step 1: Run complete test suite**
  - Run: `.venv\Scripts\python -m pytest tests/ -v`
  - Verify 100% passing tests across all modules.
- [ ] **Step 2: Synchronize mirror directory**
  - Mirror to `D:\EDITH-Enterprise\edith-x\`.
- [ ] **Step 3: Git commit and push updated branch**
