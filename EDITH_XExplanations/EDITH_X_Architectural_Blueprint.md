# ⚡ EDITH-X: Deep-Dive Architectural & Operational Blueprint
> **The Exhaustive Technical Visual Guide — From Bitstream to Model Response**

---

## 1. System Overview: High-Level Component Topology

EDITH-X functions as a zero-trust, cost-optimizing reverse proxy and autonomous agent runtime. It is organized into **14 discrete micro-modules** adhering to strictly decoupled Python Protocol interfaces.

```mermaid
graph TB
    %% External Interfaces
    subgraph Layer0["🌐 INGRESS BOUNDARY"]
        ClientApp["💻 Client Application\n(OpenAI SDK, HTTP Client, cURL)"]
        CLI["💻 Typer CLI\n('edith run' / 'edith metrics')"]
        WebDash["📊 Enterprise Web Dashboard\n(HTML5 / Tailwind UI)"]
    end

    %% Gateway & Perimeter Security
    subgraph Layer1["🛡️ M1-M4 PERIMETER GOVERNANCE"]
        direction TB
        GW["M1: FastAPI Gateway\n• Header Auth Extraction\n• Sliding-Window Rate Limiting (Redis/RAM)\n• Request Context Creation"]
        ID["M2: Identity & Multi-Tenancy\n• Constant-Time HMAC API Key Validation\n• Tenant Plan Resolution (Free/Std/Ent)\n• Audit Event Dispatcher"]
        INT["M3: Intent Engine\n• Sub-2ms Centroid Classifier\n• Complexity Scoring (0.0 - 1.0)\n• Risk Profiling (Security/Code/Task)"]
        POL["M4: Policy & Redaction Firewall\n• Luhn Algorithm (Credit Cards)\n• Shannon Entropy (Secret/Key Detector)\n• Data Residency Check (EU/US/Local)"]
    end

    %% Cache & Orchestration
    subgraph Layer2["⚡ M5-M8 COGNITIVE & CACHE RUNTIME"]
        direction TB
        PLAN["M5: Autonomous Planner\n• LangGraph Cyclic State Graph\n• Step-by-Step Task Decomposition\n• State Memory Management"]
        KNOW["M6: Knowledge Base\n• Qdrant Hybrid Retrieval\n• Dense Vector + Keyword BM25\n• Document Chunk Ingestion"]
        CTX["M7: Context Builder\n• Token Budget Allocation (e.g. 6k/8k)\n• Deduplication & Ranking\n• Prompt Structuring"]
        CACHE["M8: Dual Semantic Cache\n• Exact SHA-256 Hash Table (<0.05ms)\n• Inverted Index Vector Cosine (≥0.92)\n• LRU Eviction + TTL Window"]
    end

    %% Routing & Execution
    subgraph Layer3["🎯 M9-M10 INTELLIGENT MODEL EXECUTION"]
        direction TB
        ROUTER["M9: Pareto Model Router\n• Complexity Marker Penalties\n• Domain Centroid Sparse Cosine\n• Sigmoid P(cheap) Calculation\n• Tier Selection (L1/L2/L3)"]
        EXEC["M10: Execution Engine & Waterfall\n• LiteLLM Abstraction Layer\n• 3-State Circuit Breakers\n• Resilient Fallback Cascades"]
    end

    %% Quality Control & Telemetry
    subgraph Layer4["🔍 M11-M14 AUDIT, QUALITY & STORAGE"]
        direction TB
        VERIFY["M11: Verification Engine\n• Hallucination & Grounding Check\n• Confidence Threshold Scoring"]
        REFLECT["M12: Reflection Loop\n• Evaluation of Quality vs Goal\n• Actions: Accept / Retry / Replan"]
        MEM["M13: Hierarchical Memory\n• Per-User Memory Scope\n• Team / Org Knowledge Scopes\n• Persistent Retrieval"]
        OBS["M14: Observability Ledger\n• Exact Token Cost Accounting\n• Dollar Savings Calculation vs GPT-4o\n• Prometheus /metrics Exporter"]
    end

    %% Physical Providers
    subgraph Layer5["☁️ COMPUTE & STORAGE FABRIC"]
        direction LR
        LocalLLM["🖥️ L1: Local vLLM / Ollama\n(Llama 3.2 3B / $0.00)"]
        NIM["⚡ L2: NVIDIA NIM\n(Llama 3.1 70B / $0.0008)"]
        CloudLLM["🌐 L3: Frontier Cloud\n(GPT-4o, Claude 3.5 Sonnet)"]
        QdrantDB[("📦 Qdrant Vector DB")]
        PostgresDB[("🐘 PostgreSQL / Redis")]
    end

    %% Ingress Connections
    ClientApp -->|HTTP POST /v1/chat/completions| GW
    CLI -->|Local Command| GW
    WebDash -->|REST API & SSE Stream| GW

    %% Perimeter Flow
    GW -->|Validate Key| ID
    ID -->|Authorized Context| INT
    INT -->|Query + Metadata| POL
    POL -->|Sanitized Prompt| PLAN

    %% Planner Orchestration
    PLAN <-->|Retrieve Chunks| KNOW
    KNOW <-->|Cosine Search| QdrantDB
    PLAN -->|Assemble History| CTX
    PLAN <-->|Check Cache Hit| CACHE

    %% Router & Execution
    PLAN -->|Cache Miss: Route| ROUTER
    ROUTER -->|Selected Tier & Model| EXEC

    %% Physical Execution
    EXEC -->|Tier L1| LocalLLM
    EXEC -->|Tier L2| NIM
    EXEC -->|Tier L3| CloudLLM

    %% Verification & Post-processing
    EXEC -->|Raw Result| VERIFY
    VERIFY -->|Grounding Status| REFLECT
    REFLECT -->|Approved Payload| MEM
    MEM -->|Sync History| PostgresDB
    REFLECT -->|Pipeline Event| OBS
    OBS -->|Prometheus / JSON Metric| WebDash
    OBS -->|Final Response with Cost Ledger| ClientApp
```

---

## 2. Detailed Data-Flow Sequence Diagram

This diagram traces the exact lifecycle of an incoming user request through all safety, caching, routing, execution, and verification steps:

```mermaid
sequenceDiagram
    autonumber
    actor Client as Client App (OpenAI SDK)
    participant GW as M1: Gateway
    participant ID as M2: Identity
    participant POL as M4: PII Firewall
    participant CACHE as M8: Semantic Cache
    participant ROUTER as M9: Pareto Router
    participant EXEC as M10: Execution Waterfall
    participant Primary as Primary LLM (e.g. NIM 70B)
    participant Fallback as Fallback LLM (e.g. OpenAI / Groq)
    participant VERIFY as M11/M12: Verification
    participant OBS as M14: Observability

    Client->>GW: POST /v1/chat/completions (Prompt + API Key)
    Note over GW: Extract Bearer Token & Run Sliding-Window Rate Limiter

    GW->>ID: Validate API Key (Constant-Time HMAC)
    ID-->>GW: AuthContext (org_id, role, plan="enterprise")

    GW->>POL: Scan Prompt for PII & Enterprise Secrets
    Note over POL: Run Luhn CC Check, SSN regex, Shannon Entropy (>3.8 bits)
    POL-->>GW: Sanitized Text + PolicyDecision (pii_detected=False)

    GW->>CACHE: Check Exact (SHA-256) & Semantic Similarity
    alt Cache Hit (Cosine Similarity ≥ 0.92)
        CACHE-->>GW: Return Cached Response ($0.00 compute, <20ms)
        GW->>OBS: Record Cache Hit (Tokens Saved, Cost Saved)
        OBS-->>Client: 200 OK + Cached Output (Fast Path!)
    else Cache Miss (< 0.92)
        CACHE-->>GW: Cache Miss

        GW->>ROUTER: Evaluate Query Complexity & Predict Tier
        Note over ROUTER: Calculate P(cheap) via Centroids & Vocabulary Markers
        ROUTER-->>GW: ModelSelection (Tier L2: nvidia_nim/llama-3.1-70b)

        GW->>EXEC: Execute Query with Resilient Waterfall
        EXEC->>Primary: acompletion(model="meta/llama-3.1-70b-instruct")

        alt Primary Succeeds
            Primary-->>EXEC: 200 OK (Content + Usage Tokens)
        else Primary Fails (HTTP 429 Rate Limit or 500 Outage)
            Primary-->>EXEC: Error: Service Unavailable
            Note over EXEC: Trip Circuit Breaker & Initiate Waterfall Cascade!
            EXEC->>Fallback: acompletion(model="gpt-4o-mini" or "groq/llama-3.1")
            Fallback-->>EXEC: 200 OK (Failover Response)
        end

        EXEC-->>GW: ExecutionResult (Tokens, Latency, Failover Status)

        GW->>VERIFY: Validate Grounding & Factuality
        VERIFY-->>GW: VerificationResult (Confidence ≥ 0.90)

        GW->>CACHE: Store Query + Response in LRU & Inverted Index
        GW->>OBS: Record Pipeline Event (Cost Incurred vs Baseline Saved)
        OBS-->>Client: 200 OK (Final Output + edith_metadata headers)
    end
```

---

## 3. The 4-Tier Cost Firewall Decision Matrix

How EDITH-X decides where each dollar of compute budget is spent:

```mermaid
flowchart TD
    Req["Incoming Enterprise Prompt\n100% of Workload"] --> CCheck{"Is Query in Cache?\nCosine Similarity ≥ 0.92"}
    
    %% Tier 0
    CCheck -->|YES: 25-35% of Requests| L0["🟢 TIER L0: Semantic Cache\n• Storage: In-Memory LRU + Qdrant\n• Model Cost: $0.00 / 1M tokens\n• Latency: < 20ms\n• Best for: FAQs, repetitive prompt templates"]
    
    %% Tier 1
    CCheck -->|NO: Evaluate Query| Pareto{"Pareto Router Prediction:\nP(cheap_sufficient)"}
    
    Pareto -->|P ≥ 0.50: 30-40% of Requests| L1["🔵 TIER L1: On-Premise Local\n• Models: Llama-3.2 3B / Mistral 7B\n• Host: Ollama / vLLM / LM Studio\n• Model Cost: ~$0.00 (Local Hardware)\n• Latency: 150-300ms\n• Best for: Extraction, grammar, translation, greetings"]
    
    %% Tier 2
    Pareto -->|0.25 ≤ P < 0.50: 20-30% of Requests| L2["🟡 TIER L2: Fast Compressed Cloud\n• Models: NVIDIA NIM Llama-3.1 70B\n• Host: NVIDIA Cloud / Groq LPU\n• Model Cost: ~$0.80 / 1M tokens (70% savings vs GPT-4o)\n• Latency: 400-1100ms\n• Best for: Code refactoring, multi-turn summaries, RAG"]
    
    %% Tier 3
    Pareto -->|P < 0.25: 5-10% of Requests| L3["🔴 TIER L3: Frontier Cloud Flagship\n• Models: OpenAI GPT-4o, Claude 3.5 Sonnet\n• Host: Azure / OpenAI / Anthropic\n• Model Cost: $2.50-$15.00 / 1M tokens\n• Latency: 1500-4000ms\n• Best for: Complex math proofs, zero-day threat modeling"]
```

---

## 4. LangGraph M5 Autonomous Planner State Machine

When a multi-step goal is sent to `/edith/v1/run`, EDITH-X does not just make a single completion call. It initiates an autonomous cyclic execution graph:

```mermaid
stateDiagram-v2
    [*] --> Retrieve: Goal Received

    state Retrieve {
        [*] --> FetchKnowledgeDocs: Search Qdrant
        FetchKnowledgeDocs --> FetchUserMemories: Query Mem0
        FetchUserMemories --> CombineChunks
    }

    Retrieve --> BuildContext: Structured chunks ready

    state BuildContext {
        [*] --> CalculateTokenBudget: Limit = 6000 Tokens
        CalculateTokenBudget --> DeduplicateAndRank
    }

    BuildContext --> Optimize: Formatted Context

    state Optimize {
        [*] --> CheckL0Cache
    }

    Optimize --> Route: Cache Miss
    Optimize --> Finalize: Cache Hit ($0.00 Path)

    state Route {
        [*] --> ClassifyIntent
        ClassifyIntent --> CheckPIIPolicy
        CheckPIIPolicy --> SelectOptimalTier
    }

    Route --> Execute: Selected ModelKwargs

    state Execute {
        [*] --> CallLiteLLM
        CallLiteLLM --> CheckUpstreamErrors
        CheckUpstreamErrors --> CascadeFallback: If 429/500/Timeout
        CheckUpstreamErrors --> EmitResult: If Success
    }

    Execute --> Verify: Raw Response

    state Verify {
        [*] --> ScoreConfidence
        ScoreConfidence --> CheckFactGrounding
    }

    Verify --> Reflect: Verification Metrics

    state Reflect {
        [*] --> EvaluateGoalAcceptance
    }

    Reflect --> Retrieve: Action == "replan" (Need More Docs)
    Reflect --> Execute: Action == "retry" (Low Confidence)
    Reflect --> Finalize: Action == "accept" (Goal Achieved)

    state Finalize {
        [*] --> StoreL0Cache
        StoreL0Cache --> SaveMem0Context
        SaveMem0Context --> RecordPrometheusLedger
    }

    Finalize --> [*]: Return Completed Response
```

---

## 5. Resilience Engineering: 3-State Circuit Breaker Waterfall

How EDITH-X isolates failing upstream providers and heals automatically without dropping client requests:

```mermaid
stateDiagram-v2
    [*] --> CLOSED: Normal Operational State

    state CLOSED {
        [*] --> MonitorRequests
        MonitorRequests --> IncrementFailureCounter: On 429/500/Timeout
        MonitorRequests --> ResetFailureCounter: On HTTP 200 OK
    }

    CLOSED --> OPEN: Consecutive Failures ≥ 3 OR Rolling Error Rate ≥ 50%

    state OPEN {
        [*] --> BlockProviderTraffic
        BlockProviderTraffic --> RouteImmediatelyToFallback: Zero Wait / Zero Timeout
        RouteImmediatelyToFallback --> AwaitCooldownTimer: Cooldown = 30.0 Seconds
    }

    OPEN --> HALF_OPEN: Cooldown Expired

    state HALF_OPEN {
        [*] --> SendCanaryProbe: Allow max 2 probe queries
        SendCanaryProbe --> EvaluateCanaryHealth
    }

    HALF_OPEN --> CLOSED: Canary Probes Succeeded (Provider Healed!)
    HALF_OPEN --> OPEN: Canary Probe Failed (Re-trip with Jittered Cooldown)
```

---

## 6. Security Inspection Pipeline: M4 Policy Firewall Deep Dive

The PII and secret redaction engine uses algorithmic validation before regular expressions to prevent false positives:

```mermaid
flowchart LR
    subgraph RawPayload["📥 Unsanitized User Query"]
        Raw["'My credit card is 4532 0150 1234 5678, \n SSN is 000-12-3456, \n and api_key is sk-ant-api03-abcdef1234567890...'"]
    end

    subgraph Engines["🔎 6-Layer Security Scanners"]
        direction TB
        E1["1. Cloud Key & Token Scanner\nRegex for 'sk-', 'AKIA', 'ghp_', 'Bearer'"]
        E2["2. SSN Standard & Spaced Scanner\nPatterns: ddd-dd-dddd, d d d - d d..."]
        E3["3. Luhn Algorithm Card Validator\nDigits 13-19 + Double-Add-Modulo-10 Check"]
        E4["4. Obfuscated Email Scanner\nMatches 'user[at]domain[dot]com'"]
        E5["5. International E.164 Phone Filter\nPattern: +1 (xxx) xxx-xxxx"]
        E6["6. Shannon Entropy Key Detector\nFlags tokens with Entropy ≥ 3.8 bits/char"]
    end

    subgraph Exceptions["🛡️ Hard-Negative Exemption Filter"]
        direction TB
        Ex1["Permits UUIDs: 8-4-4-4-12 hex format"]
        Ex2["Permits Git Commit SHAs: 40-char hashes"]
        Ex3["Permits ISO-8601 Timestamps & Hex Codes"]
    end

    subgraph CleanPayload["📤 Policy-Safe Payload Sent to Model"]
        Clean["'My credit card is [REDACTED_CREDIT_CARD], \n SSN is [REDACTED_SSN], \n and api_key is [REDACTED_SECRET]...'"]
    end

    RawPayload --> Engines
    Engines --> Exceptions
    Exceptions --> CleanPayload
```

---

## 7. Verifiable Cost Savings Ledger Mathematical Accounting

Every transaction calculates verifiable ROI based on standardized baseline frontier token costs:

$$\text{Baseline Cost (GPT-4o)} = \left(\text{Tokens}_{\text{in}} \times \frac{\$2.50}{10^6}\right) + \left(\text{Tokens}_{\text{out}} \times \frac{\$10.00}{10^6}\right)$$

$$\text{Actual Cost} = \left(\text{Tokens}_{\text{in}} \times P_{\text{model\_in}}\right) + \left(\text{Tokens}_{\text{out}} \times P_{\text{model\_out}}\right)$$

$$\text{Dollars Saved} = \text{Baseline Cost} - \text{Actual Cost}$$

```mermaid
flowchart LR
    subgraph AccountingEngine["M14 Observability Cost Ledger"]
        direction TB
        Req["Request: 1,500 Input Tokens / 600 Output Tokens"]
        
        CalcBase["Frontier Baseline (GPT-4o):\n(1,500 * $2.50/M) + (600 * $10.00/M)\n= $0.00375 + $0.00600 = $0.00975"]
        
        RouteChoice{"What Tier Executed?"}
        
        L0Cost["L0 Semantic Cache:\nActual Cost: $0.00000\nROI Saved: +$0.00975 (100% saved)"]
        L1Cost["L1 Local Model (Ollama):\nActual Cost: $0.00000\nROI Saved: +$0.00975 (100% saved)"]
        L2Cost["L2 NIM Llama 70B:\nActual Cost: $0.00168\nROI Saved: +$0.00807 (82% saved)"]
        L3Cost["L3 GPT-4o Cloud:\nActual Cost: $0.00975\nROI Saved: $0.00000 (0% saved)"]
    end

    Req --> CalcBase --> RouteChoice
    RouteChoice -->|L0 Hit| L0Cost
    RouteChoice -->|L1 Route| L1Cost
    RouteChoice -->|L2 Route| L2Cost
    RouteChoice -->|L3 Route| L3Cost
```

---

*Architectural Blueprint generated for EDITH-X Enterprise Distributed Intelligence Token Handler.*
