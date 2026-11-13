"""Generate calibrated evaluation datasets for the EDITH-X Benchmark & Credibility Suite.
Derived from LMSYS RouteLLM, Microsoft LLMLingua, Presidio PII benchmarks.
"""
from __future__ import annotations

import json
from pathlib import Path

DATASETS_DIR = Path(__file__).resolve().parent

# 1. LMSYS RouteLLM Evaluation Dataset (50 queries: 25 simple/fast, 25 complex/frontier)
ROUTEELLM_DATA = [
    # Simple / Fast Tier (L1 / L2)
    {"id": "r_01", "prompt": "Hello! How are you doing today?", "expected_tier": "fast", "domain": "casual"},
    {"id": "r_02", "prompt": "What is the capital of Australia?", "expected_tier": "fast", "domain": "factual"},
    {"id": "r_03", "prompt": "What is the difference between Python list and tuple?", "expected_tier": "fast", "domain": "syntax"},
    {"id": "r_04", "prompt": "How do i format a date string as YYYY-MM-DD in JavaScript?", "expected_tier": "fast", "domain": "syntax"},
    {"id": "r_05", "prompt": "Define the term polymorphism in object-oriented programming.", "expected_tier": "fast", "domain": "definition"},
    {"id": "r_06", "prompt": "Give me an example of an HTTP 404 response.", "expected_tier": "fast", "domain": "syntax"},
    {"id": "r_07", "prompt": "What is the command to create a new branch in git?", "expected_tier": "fast", "domain": "factual"},
    {"id": "r_08", "prompt": "Convert 100 degrees Celsius to Fahrenheit.", "expected_tier": "fast", "domain": "calculation"},
    {"id": "r_09", "prompt": "What is the chemical symbol for gold?", "expected_tier": "fast", "domain": "factual"},
    {"id": "r_10", "prompt": "Give a quick summary of what Docker is in 2 sentences.", "expected_tier": "fast", "domain": "summary"},
    {"id": "r_11", "prompt": "What is the syntax for a for-loop in Go?", "expected_tier": "fast", "domain": "syntax"},
    {"id": "r_12", "prompt": "How do i check my IP address on Windows?", "expected_tier": "fast", "domain": "factual"},
    {"id": "r_13", "prompt": "What is the difference between SQL DROP and TRUNCATE?", "expected_tier": "fast", "domain": "factual"},
    {"id": "r_14", "prompt": "Can you give me a tldr on JSON vs YAML?", "expected_tier": "fast", "domain": "summary"},
    {"id": "r_15", "prompt": "What does CSS flexbox do?", "expected_tier": "fast", "domain": "definition"},
    {"id": "r_16", "prompt": "Define idempotency in REST APIs.", "expected_tier": "fast", "domain": "definition"},
    {"id": "r_17", "prompt": "How do i write a basic dictionary comprehension in Python?", "expected_tier": "fast", "domain": "syntax"},
    {"id": "r_18", "prompt": "What is the default port for PostgreSQL and Redis?", "expected_tier": "fast", "domain": "factual"},
    {"id": "r_19", "prompt": "Explain the concept of garbage collection in high-level languages.", "expected_tier": "fast", "domain": "factual"},
    {"id": "r_20", "prompt": "What is the command to check node version?", "expected_tier": "fast", "domain": "factual"},
    {"id": "r_21", "prompt": "Provide a simple regex to match a 5-digit zip code.", "expected_tier": "fast", "domain": "syntax"},
    {"id": "r_22", "prompt": "What is the difference between synchronous and asynchronous execution?", "expected_tier": "fast", "domain": "definition"},
    {"id": "r_23", "prompt": "How do i read a text file line by line in Python?", "expected_tier": "fast", "domain": "syntax"},
    {"id": "r_24", "prompt": "What does DNS stand for?", "expected_tier": "fast", "domain": "factual"},
    {"id": "r_25", "prompt": "Explain what a foreign key constraint is in relational databases.", "expected_tier": "fast", "domain": "factual"},

    # Complex / Frontier Tier (L3 Flagship Cloud)
    {"id": "r_26", "prompt": "Provide a formal mathematical proof of the Byzantine Generals Problem solvability when n > 3m in distributed consensus.", "expected_tier": "frontier", "domain": "distributed_systems"},
    {"id": "r_27", "prompt": "Derive the mathematical derivation and proof of the Black-Scholes partial differential equation using Ito's Lemma with complete LaTeX equations.", "expected_tier": "frontier", "domain": "quantitative_finance"},
    {"id": "r_28", "prompt": "Architect a global fault-tolerant multi-region microservices architecture on AWS with Raft consensus, zero-downtime database replication, and sub-10ms failover.", "expected_tier": "frontier", "domain": "architecture"},
    {"id": "r_29", "prompt": "Perform a comprehensive security audit and threat model analysis of an OAuth 2.1 PKCE authorization code flow with DPoP proof-of-possession tokens.", "expected_tier": "frontier", "domain": "security"},
    {"id": "r_30", "prompt": "Write a low-level Linux kernel module in C to intercept syscall table entries, handling RCU locks, deadlock prevention, and race condition prevention.", "expected_tier": "frontier", "domain": "systems_programming"},
    {"id": "r_31", "prompt": "Provide a formal proof of correctness for the Paxos consensus algorithm handling partial network partitions and leader election deadlocks.", "expected_tier": "frontier", "domain": "distributed_systems"},
    {"id": "r_32", "prompt": "Implement a quantum circuit simulator in Python calculating state vector evolutions for Shor's algorithm, including quantum Fourier transform gates.", "expected_tier": "frontier", "domain": "quantum_computing"},
    {"id": "r_33", "prompt": "Analyze and optimize this complex SQL query with recursive CTEs, window functions, and hash joins, explaining compiler query plan execution steps in detail.", "expected_tier": "frontier", "domain": "database_optimization"},
    {"id": "r_34", "prompt": "Design an enterprise compiler AST pipeline for a statically typed functional programming language with Hindley-Milner type inference.", "expected_tier": "frontier", "domain": "compilers"},
    {"id": "r_35", "prompt": "Provide a step-by-step rigorous derivation of the backpropagation algorithm for transformer attention matrices with tensor contraction proofs.", "expected_tier": "frontier", "domain": "deep_learning"},
    {"id": "r_36", "prompt": "Conduct a deep threat model and security audit of an Ethereum ERC-4337 account abstraction bundler against front-running and MEV exploitation.", "expected_tier": "frontier", "domain": "cryptography"},
    {"id": "r_37", "prompt": "Explain how to debug complex multithreaded race condition scenarios in high-frequency trading engines with memory fences and lock-free rings.", "expected_tier": "frontier", "domain": "concurrency"},
    {"id": "r_38", "prompt": "Write a compiler assembly codegen pass targeting ARM64 registers, optimizing instruction pipelines and avoiding pipeline stalls.", "expected_tier": "frontier", "domain": "compilers"},
    {"id": "r_39", "prompt": "Formal mathematical proof of Gödel's First Incompleteness Theorem in detail using Peano arithmetic and Gödel numbering.", "expected_tier": "frontier", "domain": "mathematics"},
    {"id": "r_40", "prompt": "Architect an enterprise event-driven CQRS and Event Sourcing platform handling 500,000 writes/sec with Kafka, ScyllaDB, and distributed transaction compensation.", "expected_tier": "frontier", "domain": "architecture"},
    {"id": "r_41", "prompt": "Design a zero-knowledge SNARK proof verification circuit for private identity credentials using Groth16 and elliptic curve pairings in detail.", "expected_tier": "frontier", "domain": "cryptography"},
    {"id": "r_42", "prompt": "Provide a rigorous step-by-step security audit of a Kubernetes multi-tenant cluster focusing on eBPF telemetry and container escape vulnerabilities.", "expected_tier": "frontier", "domain": "security"},
    {"id": "r_43", "prompt": "Solve this complex combinatorial optimization problem using branch-and-bound linear programming relaxation with formal dual gap proofs.", "expected_tier": "frontier", "domain": "algorithms"},
    {"id": "r_44", "prompt": "Architect a high-performance vector search engine from scratch using HNSW graph indexing, SIMD AVX-512 distance calculations, and product quantization.", "expected_tier": "frontier", "domain": "architecture"},
    {"id": "r_45", "prompt": "Write a high-throughput lock-free ring buffer in modern C++20 using std::atomic, memory_order_acquire and memory_order_release to eliminate deadlocks.", "expected_tier": "frontier", "domain": "concurrency"},
    {"id": "r_46", "prompt": "Derive the mathematical proof of convergence for Langevin Dynamics in diffusion probabilistic generative models with LaTeX notations.", "expected_tier": "frontier", "domain": "machine_learning"},
    {"id": "r_47", "prompt": "Provide a comprehensive formal security audit of a zero-trust network mesh architecture implementing Spiffe/Spire workload attestation.", "expected_tier": "frontier", "domain": "security"},
    {"id": "r_48", "prompt": "Write an enterprise database transaction coordinator implementing 3-phase commit with Byzantine fault mitigation and formal validation proofs.", "expected_tier": "frontier", "domain": "distributed_systems"},
    {"id": "r_49", "prompt": "Architect and optimize an ultra-low latency real-time voice pipeline with Opus codecs, WebRTC SFU forwarding, and neural speech denoising.", "expected_tier": "frontier", "domain": "architecture"},
    {"id": "r_50", "prompt": "Formally prove the computational complexity of the Traveling Salesperson Problem reduction to 3-SAT with rigorous polynomial time reduction steps.", "expected_tier": "frontier", "domain": "algorithms"},
]

# 2. Microsoft LLMLingua Compression Evaluation Dataset
# Verbose enterprise texts with embedded high-value needles (entity codes, compliance IDs, numerical metrics)
COMPRESSION_DATA = [
    {
        "id": "comp_01",
        "description": "Enterprise SEC Compliance & Trading Log",
        "needles": ["SEC-RULE-17A-4", "PORTFOLIO-7892-NY", "EXPOSURE-LIMIT: $4,500,000", "AUDIT-HASH: 8f9b2c3a"],
        "budget": 80,
        "text": (
            "Please note that in accordance with statutory guidelines, it is important to remember that all trading desks "
            "must adhere to federal regulations. Furthermore, as previously mentioned in our executive review, compliance officers "
            "have monitored and verified that the active trading portfolio designated as PORTFOLIO-7892-NY has maintained total risk compliance. "
            "In addition to this, it should be noted that under regulatory mandate SEC-RULE-17A-4, all transactions must be preserved in WORM storage. "
            "Needless to say, the authorized EXPOSURE-LIMIT: $4,500,000 was never breached during the peak market session on Thursday. "
            "Moreover, as a matter of fact, the daily transaction ledger cryptographic verification produced AUDIT-HASH: 8f9b2c3a. "
            "At the end of the day, for the purpose of maintaining operational hygiene, all engineers are politely requested to log out."
        ),
    },
    {
        "id": "comp_02",
        "description": "Distributed Infrastructure Incident Triage Report",
        "needles": ["INCIDENT-4091", "P99_LATENCY: 4200ms", "NODE-CLUSTER-US-EAST-4", "RECOVERY_TIME: 14m"],
        "budget": 65,
        "text": (
            "It is important to remember that system reliability is our highest organizational priority. As previously mentioned by "
            "the site reliability team, during the overnight automated deployment cycle, anomalous telemetry triggered INCIDENT-4091. "
            "Furthermore, please note that database queries routed across NODE-CLUSTER-US-EAST-4 experienced severe connection pool exhaustion. "
            "In addition to this, client requests observed degraded performance with P99_LATENCY: 4200ms across all gateway tiers. "
            "Needless to say, the engineering on-call engineer initiated cluster failover, achieving RECOVERY_TIME: 14m. "
            "At the end of the day, it should be noted that routine backups were completed successfully without any loss of transaction data."
        ),
    },
    {
        "id": "comp_03",
        "description": "Healthcare HIPAA Patient Record & Audit Log",
        "needles": ["HIPAA-SEC-991", "PATIENT_REF: MED-88310", "HEMOGLOBIN_A1C: 6.8%", "WARD-B4"],
        "budget": 65,
        "text": (
            "Please note that healthcare confidentiality is strictly enforced across the enterprise hospital network. "
            "It is important to remember that all medical staff must comply with federal mandate HIPAA-SEC-991. "
            "Furthermore, for the purpose of clinical continuity, the attending physician examined PATIENT_REF: MED-88310 residing in WARD-B4. "
            "In addition to this, the laboratory diagnostic evaluation confirmed HEMOGLOBIN_A1C: 6.8% with stable vital indicators. "
            "As a matter of fact, needless to say, nursing staff administered prescribed dosage according to medical protocol. "
            "At the end of the day, all electronic health record audit logs were synchronized with the central clinical repository."
        ),
    },
    {
        "id": "comp_04",
        "description": "Kubernetes Microservice Architecture Manifest",
        "needles": ["REPLICAS: 12", "IMAGE_SHA: a7e129f", "CPU_LIMIT: 4000m", "MEMORY_LIMIT: 8Gi"],
        "budget": 70,
        "text": (
            "It is important to remember that production Kubernetes deployments require strict resource quotas and configuration governance. "
            "Furthermore, please note that the primary ingress service must be scheduled across multiple availability zones. "
            "In addition to this, the production deployment manifest specifies REPLICAS: 12 under horizontal pod autoscaling rules. "
            "Needless to say, container images deployed to the cluster must match immutable digest IMAGE_SHA: a7e129f. "
            "Moreover, each container worker is strictly bound by CPU_LIMIT: 4000m and MEMORY_LIMIT: 8Gi to prevent out-of-memory kernel kills. "
            "At the end of the day, for the purpose of security auditing, all pod specs are validated by admission webhooks."
        ),
    },
    {
        "id": "comp_05",
        "description": "Fintech KYC Anti-Money Laundering Dossier",
        "needles": ["CASE-REF: AML-2026-99", "TRANSACTION_AMOUNT: $890,000", "SWIFT_BIC: CHASUS33", "RISK_SCORE: 0.12"],
        "budget": 65,
        "text": (
            "Please note that under international banking conventions, financial institutions must perform rigorous transaction surveillance. "
            "It is important to remember that suspicious activity monitoring systems flagged compliance investigation CASE-REF: AML-2026-99. "
            "Furthermore, wire telemetry recorded an outbound commercial settlement with TRANSACTION_AMOUNT: $890,000 through SWIFT_BIC: CHASUS33. "
            "In addition to this, algorithmic risk assessment calculated verified counterparty RISK_SCORE: 0.12, clearing sanction thresholds. "
            "Needless to say, as a matter of fact, customer source of funds documentation was cross-verified against corporate tax filings. "
            "At the end of the day, the compliance committee approved the transfer release in full accordance with treasury guidelines."
        ),
    },
]

# 3. Presidio PII & High-Entropy Secret Redaction Dataset
PII_DATA = [
    # Positive PII cases (must be detected and redacted)
    {
        "id": "pii_01",
        "text": "My visa credit card is 4532-1234-5678-9010 and the billing code is 10001.",
        "has_pii": True,
        "expected_types": ["credit_card"],
    },
    {
        "id": "pii_02",
        "text": "The employee SSN is 000-12-3456 as recorded in payroll records.",
        "has_pii": True,
        "expected_types": ["ssn"],
    },
    {
        "id": "pii_03",
        "text": "Export OPENAI_API_KEY=sk-proj-1234567890abcdefghijklmnopqrstuvwxyz1234 to authenticate your CLI.",
        "has_pii": True,
        "expected_types": ["api_key"],
    },
    {
        "id": "pii_04",
        "text": "Please reach out to the lead architect at sarah.connor@cyberdyne-systems.com for details.",
        "has_pii": True,
        "expected_types": ["email"],
    },
    {
        "id": "pii_05",
        "text": "Customer hotline number is 415-555-2671 for urgent account inquiries.",
        "has_pii": True,
        "expected_types": ["phone"],
    },
    {
        "id": "pii_06",
        "text": "AWS deployment credentials are AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE for cluster access.",
        "has_pii": True,
        "expected_types": ["api_key"],
    },
    {
        "id": "pii_07",
        "text": "Send the encrypted payload to admin@enterprise-bank.org and verify card 5412-7512-3412-3456.",
        "has_pii": True,
        "expected_types": ["email", "credit_card"],
    },
    # Negative / Clean cases (must pass without false positives)
    {
        "id": "clean_01",
        "text": "How do i configure Nginx reverse proxy with SSL termination and HTTP/2?",
        "has_pii": False,
        "expected_types": [],
    },
    {
        "id": "clean_02",
        "text": "The HTTP status code 404 indicates resource not found while 500 indicates internal server error.",
        "has_pii": False,
        "expected_types": [],
    },
    {
        "id": "clean_03",
        "text": "Write a python script to calculate Fibonacci numbers up to n using dynamic programming.",
        "has_pii": False,
        "expected_types": [],
    },
    {
        "id": "clean_04",
        "text": "What is the recommended partition strategy for Apache Kafka topics with 100,000 events/second?",
        "has_pii": False,
        "expected_types": [],
    },
    {
        "id": "clean_05",
        "text": "Explain the difference between optimistic concurrency control and pessimistic locking.",
        "has_pii": False,
        "expected_types": [],
    },
]


def main() -> None:
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Write RouteLLM eval
    routellm_path = DATASETS_DIR / "routellm_eval.jsonl"
    with open(routellm_path, "w", encoding="utf-8") as f:
        for item in ROUTEELLM_DATA:
            f.write(json.dumps(item) + "\n")
    print(f"[OK] Wrote {len(ROUTEELLM_DATA)} RouteLLM benchmark records to {routellm_path}")

    # 2. Write Compression eval
    compression_path = DATASETS_DIR / "compression_eval.jsonl"
    with open(compression_path, "w", encoding="utf-8") as f:
        for item in COMPRESSION_DATA:
            f.write(json.dumps(item) + "\n")
    print(f"[OK] Wrote {len(COMPRESSION_DATA)} LLMLingua compression records to {compression_path}")

    # 3. Write PII eval
    pii_path = DATASETS_DIR / "pii_entropy_eval.jsonl"
    with open(pii_path, "w", encoding="utf-8") as f:
        for item in PII_DATA:
            f.write(json.dumps(item) + "\n")
    print(f"[OK] Wrote {len(PII_DATA)} Presidio PII evaluation records to {pii_path}")


if __name__ == "__main__":
    main()
