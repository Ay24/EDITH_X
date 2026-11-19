"""Build 1,000 Enterprise User Profiles & Multi-Level Workload Dataset.

Synthesizes realistic enterprise cohorts across 50 multi-tenant organizations
and 5 professional enterprise personas.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

random.seed(42)

BASE_DIR = Path(__file__).resolve().parent
BENIGN_PATH = BASE_DIR / "benign_prompts_1k.jsonl"
GSM8K_PATH = BASE_DIR / "gsm8k_eval.jsonl"
PII_PATH = BASE_DIR / "pii_annotated_eval.jsonl"
OUTPUT_PATH = BASE_DIR / "enterprise_1000_users.json"

# Load source datasets
with open(BENIGN_PATH, "r", encoding="utf-8") as f:
    benign_prompts = [json.loads(line) for line in f]

with open(GSM8K_PATH, "r", encoding="utf-8") as f:
    gsm8k_prompts = [json.loads(line) for line in f]

with open(PII_PATH, "r", encoding="utf-8") as f:
    pii_prompts = [json.loads(line) for line in f]

TENANTS = [f"org_fintech_{i:02d}" for i in range(1, 51)]

PERSONAS = {
    "support_rep": {
        "weight": 0.40,  # 400 users
        "role": "member",
        "description": "Customer Support Representative querying policy FAQs and resolving transaction disputes.",
    },
    "devops_engineer": {
        "weight": 0.25,  # 250 users
        "role": "member",
        "description": "Software & Platform Engineer querying code snippets and running system diagnostics tools.",
    },
    "secops_compliance": {
        "weight": 0.15,  # 150 users
        "role": "member",
        "description": "Compliance & Security Auditor verifying zero-trust PII filtering on sensitive data.",
    },
    "financial_strategist": {
        "weight": 0.10,  # 100 users
        "role": "member",
        "description": "Quantitative Financial Analyst solving complex multi-step reasoning problems.",
    },
    "knowledge_curator": {
        "weight": 0.10,  # 100 users
        "role": "admin",
        "description": "Knowledge Base Curator ingesting tenant policies and validating RAG retrieval isolation.",
    },
}

POLICIES = [
    "Wire transfer daily threshold is $50,000 without VP approval.",
    "Regulation E requires consumer notice within 60 days of statement issuance.",
    "PCI-DSS standard mandates encryption of cardholder data in transit and at rest.",
    "GDPR Article 17 grants users the right to erasure of personal data within 30 days.",
    "Health insurance pre-authorization claims must be processed within 72 business hours.",
]

CALCULATOR_EXPRESSIONS = [
    "1500 * 1.18 - 250",
    "45000 / 12 * 0.75",
    "250000 * 0.045 / 365 * 30",
    "1000000 * (1 + 0.07)**5",
    "(850 - 320) * 1.05 + 45",
]


def generate_enterprise_1000():
    users = []
    
    # 400 support, 250 devops, 150 secops, 100 financial, 100 knowledge
    persona_pool = (
        ["support_rep"] * 400
        + ["devops_engineer"] * 250
        + ["secops_compliance"] * 150
        + ["financial_strategist"] * 100
        + ["knowledge_curator"] * 100
    )
    random.shuffle(persona_pool)

    # Reusable FAQ queries for cache hit simulation (Power-law Zipfian distribution)
    popular_faq_queries = [
        "What is the standard dispute timeframe under Regulation E?",
        "What is the daily maximum limit for international SWIFT wire transfers?",
        "How do I reset my multi-factor authentication token?",
        "What is the procedure for an immediate stop-payment order on a cashier check?",
        "What are the mandatory AML know-your-customer verification tiers?",
    ]

    for user_idx in range(1, 1001):
        user_id = f"usr_{user_idx:04d}"
        tenant_id = random.choice(TENANTS)
        persona_name = persona_pool[user_idx - 1]
        persona_info = PERSONAS[persona_name]

        user_profile = {
            "user_id": user_id,
            "org_id": tenant_id,
            "email": f"{user_id}@{tenant_id.replace('_', '-')}.enterprise.internal",
            "role": persona_info["role"],
            "persona": persona_name,
            "api_key": f"edx_live_{user_id}_{tenant_id}",
            "journey": {},
        }

        # Level 1: Authentication Profile
        user_profile["journey"]["level_1_auth"] = {
            "user_id": user_id,
            "org_id": tenant_id,
            "role": persona_info["role"],
        }

        # Level 2: Knowledge Ingestion or RAG Query
        policy_text = f"[{tenant_id.upper()} OFFICIAL POLICY] {random.choice(POLICIES)}"
        user_profile["journey"]["level_2_knowledge"] = {
            "action": "ingest_and_retrieve" if persona_name == "knowledge_curator" else "retrieve",
            "document": {
                "content": policy_text,
                "source": f"policy_{tenant_id}.pdf",
                "org_id": tenant_id,
            },
            "query": "wire transfer daily limit" if "wire" in policy_text.lower() else "regulation dispute timeframe",
        }

        # Level 3: Cold Query Submission
        if persona_name == "support_rep":
            # 60% chance to select a popular FAQ (creates high cache hit probability in production)
            if random.random() < 0.60:
                cold_q = random.choice(popular_faq_queries)
            else:
                cold_q = benign_prompts[(user_idx * 7) % len(benign_prompts)]["prompt"]
        elif persona_name == "financial_strategist":
            gsm = gsm8k_prompts[(user_idx * 3) % len(gsm8k_prompts)]
            cold_q = gsm["question"]
        elif persona_name == "secops_compliance":
            pii_item = pii_prompts[(user_idx * 5) % len(pii_prompts)]
            cold_q = pii_item["text"]
        elif persona_name == "devops_engineer":
            cold_q = benign_prompts[(user_idx * 11) % len(benign_prompts)]["prompt"]
        else:  # knowledge_curator
            cold_q = f"According to {tenant_id} policy, what is the exact operational protocol for high-risk audits?"

        user_profile["journey"]["level_3_cold_query"] = {
            "query": cold_q,
            "expected_pii_check": persona_name == "secops_compliance",
        }

        # Level 4: Follow-up / Semantic Cache Query
        if persona_name == "support_rep":
            # Paraphrased or repeated query to test L0 Cache
            followup_q = cold_q if random.random() < 0.5 else f"Please tell me again: {cold_q}"
        else:
            followup_q = cold_q

        user_profile["journey"]["level_4_cache_query"] = {
            "query": followup_q,
            "is_duplicate_or_paraphrase": True,
        }

        # Level 5: Sandboxed Tool Execution
        tool_choice = "calculator" if persona_name in ("devops_engineer", "financial_strategist") else "datetime_now"
        tool_args = {"expression": random.choice(CALCULATOR_EXPRESSIONS)} if tool_choice == "calculator" else {}
        user_profile["journey"]["level_5_tool"] = {
            "tool": tool_choice,
            "args": tool_args,
        }

        users.append(user_profile)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

    print(f"Successfully generated {len(users)} enterprise user profiles at {OUTPUT_PATH}")
    print(f"  * Organizations: {len(TENANTS)} tenants ({TENANTS[0]}..{TENANTS[-1]})")
    print(f"  * Personas: Support ({400}), DevOps ({250}), SecOps ({150}), Finance ({100}), Curators ({100})")


if __name__ == "__main__":
    generate_enterprise_1000()
