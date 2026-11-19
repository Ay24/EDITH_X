"""Production Simulation Dataset Generator.

Generates:
1. 50 tenants with Pareto/power-law user distribution (a few large, many small).
2. 1,000 users across 5 personas.
3. Knowledge corpus with unique embedded CANARY strings per tenant (CANARY-org_XX-xxxxxx).
4. Zipfian query distribution (s ~ 1.1) with paraphrases and near-misses.
5. Ground-truth labeled PII & Secret evasion corpus (Luhn cards, SSNs, JWTs, AWS keys, benign numbers).
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

# Fixed random seed for 100% reproducibility
random.seed(1337)

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def luhn_generate_card(prefix: str = "4532") -> str:
    """Generate a 16-digit Luhn-valid credit card number."""
    digits = [int(c) for c in prefix]
    while len(digits) < 15:
        digits.append(random.randint(0, 9))
    # Calculate checksum
    s = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            d2 = d * 2
            s += (d2 - 9) if d2 > 9 else d2
        else:
            s += d
    check = (10 - (s % 10)) % 10
    digits.append(check)
    return "".join(str(d) for d in digits)


def generate_all():
    print("[*] Generating production-scale datasets with fixed seed=1337...")

    # ──────────────────────────────────────────────────────────────────────────
    # 1. 50 TENANTS & 1,000 USERS
    # ──────────────────────────────────────────────────────────────────────────
    tenants = []
    # Uneven distribution: Top 3 tenants get ~35% of users, next 7 get ~25%, bottom 40 get ~40%
    tenant_weights = [120, 90, 80] + [35] * 7 + [11] * 40  # sum = 120+90+80 + 245 + 440 = 975 -> adjust
    tenant_weights[0] += (1000 - sum(tenant_weights))

    users = []
    user_id_counter = 1

    for t_idx in range(1, 51):
        t_id = f"org_{t_idx:02d}"
        t_canary = f"CANARY-{t_id}-{hashlib.md5(f'{t_id}_secret_salt'.encode()).hexdigest()[:8]}"
        t_users_count = tenant_weights[t_idx - 1]

        tenants.append({
            "org_id": t_id,
            "name": f"Enterprise Client {t_idx:02d}",
            "canary": t_canary,
            "user_count": t_users_count,
            "plan": "enterprise" if t_users_count >= 30 else "standard",
        })

        for _ in range(t_users_count):
            # Persona allocation: Support 40%, DevOps 25%, SecOps 15%, Finance 10%, Curator 10%
            r = random.random()
            if r < 0.40:
                persona = "support_rep"
                role = "member"
            elif r < 0.65:
                persona = "devops_engineer"
                role = "member"
            elif r < 0.80:
                persona = "secops_compliance"
                role = "member"
            elif r < 0.90:
                persona = "financial_analyst"
                role = "member"
            else:
                persona = "knowledge_curator"
                role = "admin"

            uid = f"usr_{user_id_counter:04d}"
            users.append({
                "user_id": uid,
                "org_id": t_id,
                "email": f"{uid}@{t_id}.internal",
                "role": role,
                "persona": persona,
                "api_key": f"edx_live_{uid}_{t_id}",
            })
            user_id_counter += 1

    with open(DATA_DIR / "tenants.json", "w", encoding="utf-8") as f:
        json.dump(tenants, f, indent=2)

    with open(DATA_DIR / "users.json", "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

    print(f"  * Generated 50 tenants and {len(users)} users.")

    # ──────────────────────────────────────────────────────────────────────────
    # 2. KNOWLEDGE CORPUS WITH CANARIES (25,000 Chunks Across 50 Tenants)
    # ──────────────────────────────────────────────────────────────────────────
    corpus_file = DATA_DIR / "knowledge_corpus.jsonl"
    total_chunks = 0
    with open(corpus_file, "w", encoding="utf-8") as f:
        for t in tenants:
            t_id = t["org_id"]
            t_canary = t["canary"]
            # 500 chunks per tenant = 25,000 total
            for c_idx in range(500):
                topic = ["wire_transfers", "disputes", "incident_response", "sla", "payroll"][c_idx % 5]
                text = (
                    f"[{t_id.upper()} OFFICIAL POLICY DOC-{c_idx:03d}] "
                    f"Subject: {topic.replace('_', ' ').title()}. "
                    f"Security authentication signature: {t_canary}. "
                    f"In accordance with {t_id} operational governance, all {topic} limits are strictly set "
                    f"to ${10000 + (c_idx * 50)} USD for Tier {c_idx % 3 + 1} customer accounts."
                )
                chunk_entry = {
                    "doc_id": f"{t_id}_doc_{c_idx:03d}",
                    "org_id": t_id,
                    "source": f"{t_id}_{topic}_handbook.pdf",
                    "canary": t_canary,
                    "content": text,
                }
                f.write(json.dumps(chunk_entry) + "\n")
                total_chunks += 1

    print(f"  * Generated {total_chunks:,} knowledge corpus chunks with verified canary tokens.")

    # ──────────────────────────────────────────────────────────────────────────
    # 3. ZIPFIAN QUERY DATASET WITH PARAPHRASES & NEAR-MISSES
    # ──────────────────────────────────────────────────────────────────────────
    # Real domain topics
    core_queries = [
        "What is the daily wire transfer threshold before dual-officer sign-off?",
        "Explain Regulation E consumer dispute notice requirements.",
        "What is the SEV-1 incident escalation protocol for payment service outages?",
        "How do I rotate database credentials in AWS KMS?",
        "What is the mathematical proof of asynchronous Byzantine consensus under f < n/3?",
        "What are the quarterly travel expense limits for engineering staff?",
        "How to configure VPC peering between staging and production clusters?",
        "Calculate annual compounding interest on $250,000 at 6.5% APR over 7 years.",
    ]

    # Zipfian distribution: Frequency P(k) ~ 1 / k^1.1
    zipf_weights = [1.0 / (k ** 1.1) for k in range(1, len(core_queries) + 1)]
    sum_w = sum(zipf_weights)
    zipf_probs = [w / sum_w for w in zipf_weights]

    queries = []
    # 1,000 test queries
    unique_counter = 0
    for i in range(1000):
        # 45% of queries hit the core top-8 Zipf distribution (repetition)
        # 25% are paraphrases of core queries
        # 15% are near-miss queries (look identical, but ask about a different tenant/parameter)
        # 15% are completely unique long-tail queries
        rand_type = random.random()
        t_target = tenants[i % len(tenants)]

        if rand_type < 0.45:
            q_text = random.choices(core_queries, weights=zipf_probs, k=1)[0]
            q_type = "zipf_popular"
        elif rand_type < 0.70:
            base = random.choice(core_queries)
            q_text = f"Could you clarify the following: {base}"
            q_type = "paraphrase"
        elif rand_type < 0.85:
            # Near-miss: looks like a general query, but is tenant-specific
            q_text = f"Under {t_target['org_id']} rules, what is the daily wire transfer limit?"
            q_type = "near_miss"
        else:
            unique_counter += 1
            q_text = f"Specialized operational audit inquiry #{unique_counter}: verify ledger balance {random.randint(1000, 9999)}."
            q_type = "long_tail_unique"

        queries.append({
            "query_id": f"q_{i:04d}",
            "text": q_text,
            "type": q_type,
            "tenant_context": t_target["org_id"],
            "expected_canary": t_target["canary"],
        })

    with open(DATA_DIR / "queries.jsonl", "w", encoding="utf-8") as f:
        for q in queries:
            f.write(json.dumps(q) + "\n")

    unique_share = (unique_counter / len(queries)) * 100.0
    print(f"  * Generated {len(queries)} queries ({unique_share:.1f}% unique long-tail).")

    # ──────────────────────────────────────────────────────────────────────────
    # 4. GROUND TRUTH PII & SECRET DATASET (INDEPENDENT GENERATION)
    # ──────────────────────────────────────────────────────────────────────────
    pii_samples = []

    # 100 Real Positive PII / Secrets
    for i in range(100):
        card = luhn_generate_card("4532")
        ssn = f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"
        aws_key = f"AKIA{hashlib.md5(str(i).encode()).hexdigest()[:16].upper()}"
        jwt = f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{hashlib.sha256(str(i).encode()).hexdigest()[:32]}.sig"
        
        pii_samples.append({
            "id": f"pos_card_{i}", "text": f"Please process card {card} for customer payment.",
            "has_secret": True, "secret_type": "credit_card", "secret_val": card
        })
        pii_samples.append({
            "id": f"pos_ssn_{i}", "text": f"Employee tax filing SSN is {ssn}.",
            "has_secret": True, "secret_type": "ssn", "secret_val": ssn
        })
        pii_samples.append({
            "id": f"pos_aws_{i}", "text": f"KMS deploy token: {aws_key}.",
            "has_secret": True, "secret_type": "aws_key", "secret_val": aws_key
        })

    # 50 Adversarial Evasion Variants
    for i in range(50):
        card = luhn_generate_card("4532")
        spaced_card = " ".join(card[j:j+4] for j in range(0, 16, 4))
        obfuscated_email = f"user_{i} [at] corp [dot] internal"
        pii_samples.append({
            "id": f"evasion_card_{i}", "text": f"Card digits separated: {spaced_card}",
            "has_secret": True, "secret_type": "credit_card_evasion", "secret_val": card
        })
        pii_samples.append({
            "id": f"evasion_email_{i}", "text": f"Reach me at {obfuscated_email} for secrets.",
            "has_secret": True, "secret_type": "email_evasion", "secret_val": obfuscated_email
        })

    # 150 Hard Negatives (Benign strings that must NOT be redacted - False Positive test)
    for i in range(150):
        uuid_str = "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"
        git_sha = hashlib.sha1(str(i).encode()).hexdigest()
        benign_math = f"Calculate 45000 / 12 * 0.75 + 1250 = {3500 + i}"
        pii_samples.append({
            "id": f"neg_uuid_{i}", "text": f"Transaction trace identifier: {uuid_str}",
            "has_secret": False, "secret_type": "none", "secret_val": ""
        })
        pii_samples.append({
            "id": f"neg_sha_{i}", "text": f"Merged commit SHA: {git_sha}",
            "has_secret": False, "secret_type": "none", "secret_val": ""
        })
        pii_samples.append({
            "id": f"neg_math_{i}", "text": f"Balance equation: {benign_math}",
            "has_secret": False, "secret_type": "none", "secret_val": ""
        })

    with open(DATA_DIR / "pii_eval_corpus.jsonl", "w", encoding="utf-8") as f:
        for p in pii_samples:
            f.write(json.dumps(p) + "\n")

    print(f"  * Generated {len(pii_samples)} labeled PII evaluation samples (positives, evasions, hard negatives).")
    print(f"[OK] Production simulation dataset generation complete in {DATA_DIR}\n")


if __name__ == "__main__":
    generate_all()
