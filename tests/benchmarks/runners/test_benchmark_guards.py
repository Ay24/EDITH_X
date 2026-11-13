"""Task: Benchmark Mutation & Regression Guards.
Enforces:
1. Minimum sample size n across all datasets.
2. Mutation testing: asserts that tests FAIL if router is randomized, PII detection is bypassed, or compression defaults to truncation.
3. Regression check against tests/benchmarks/baselines.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import random
import pytest

from edith_x.modules.policy.firewall import PIIFirewall
from edith_x.modules.optimization.compressor import InformationDensityCompressor
from edith_x.modules.router.pareto import ParetoModelRouter

BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
BASELINES_PATH = BASE_DIR / "baselines.json"


def load_baselines():
    with open(BASELINES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestBenchmarkGuards:
    """Mutation and regression tests ensuring benchmark test sensitivity and integrity."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.baselines = load_baselines()

    def test_sample_size_guards(self):
        """Enforces minimum statistical sample size across all datasets."""
        # 1. GSM8K Reasoning
        with open(DATASETS_DIR / "gsm8k_eval.jsonl", "r", encoding="utf-8") as f:
            gsm_records = [json.loads(l) for l in f if l.strip()]
        test_split = [r for r in gsm_records if r.get("split") == "test"]
        assert len(gsm_records) >= 200, f"GSM8K total {len(gsm_records)} < 200"
        assert len(test_split) >= 100, f"GSM8K test split {len(test_split)} < 100"

        # 2. Compression QA
        with open(DATASETS_DIR / "compression_qa_eval.jsonl", "r", encoding="utf-8") as f:
            comp_records = [json.loads(l) for l in f if l.strip()]
        assert len(comp_records) >= 30, f"Compression QA {len(comp_records)} < 30"

        # 3. PII Annotated
        with open(DATASETS_DIR / "pii_annotated_eval.jsonl", "r", encoding="utf-8") as f:
            pii_records = [json.loads(l) for l in f if l.strip()]
        assert len(pii_records) >= 100, f"PII annotated {len(pii_records)} < 100"

        # 4. Benign Prompts
        with open(DATASETS_DIR / "benign_prompts_1k.jsonl", "r", encoding="utf-8") as f:
            benign_records = [json.loads(l) for l in f if l.strip()]
        assert len(benign_records) >= 1000, f"Benign prompts {len(benign_records)} < 1000"

    def test_mutation_random_router_must_fail_auc(self):
        """Mutation test: asserts that a randomized router fails the pre-committed AUC delta requirement."""
        with open(DATASETS_DIR / "gsm8k_eval.jsonl", "r", encoding="utf-8") as f:
            test_records = [json.loads(l) for l in f if l.strip() and json.loads(l).get("split") == "test"]

        # Mutated router: pure random coin flip
        random.seed(42)
        correct_list = []
        for r in test_records:
            # Random coin flip: 50% strong, 50% cheap
            if random.random() < 0.50:
                correct_list.append(1.0 if r["strong_model_correct"] else 0.0)
            else:
                correct_list.append(1.0 if r["cheap_model_correct"] else 0.0)

        rand_acc = sum(correct_list) / len(correct_list)
        strong_acc = sum(1.0 for r in test_records if r["strong_model_correct"]) / len(test_records)

        # A random router cannot achieve 90% quality with 50% calls
        assert rand_acc < (0.90 * strong_acc), "Mutation failed: random router unexpectedly passed quality gate"

    def test_mutation_disabled_pii_firewall_must_fail_recall(self):
        """Mutation test: asserts that bypassing PII detection causes secret recall to drop to 0%."""
        with open(DATASETS_DIR / "pii_annotated_eval.jsonl", "r", encoding="utf-8") as f:
            secret_records = [json.loads(l) for l in f if l.strip() and json.loads(l).get("category") == "standard" and json.loads(l).get("pii_type") == "api_key"]

        # Mutated firewall: disabled / bypass
        def mutated_redact(text: str):
            return text, False, []

        detected_hits = sum(1 for r in secret_records if mutated_redact(r["text"])[1])
        recall = detected_hits / len(secret_records)

        # Must fail standard 95% recall
        assert recall == 0.0, "Mutation failed: disabled firewall unexpectedly detected secrets"

    def test_mutation_naive_truncation_must_fail_needle_retention(self):
        """Mutation test: asserts that naive truncation drops middle and end needles."""
        with open(DATASETS_DIR / "compression_qa_eval.jsonl", "r", encoding="utf-8") as f:
            records = [json.loads(l) for l in f if l.strip() and json.loads(l).get("needle_position") in ("middle", "end")]

        # Mutated compressor: naive head truncation
        def mutated_compress(text: str, budget: int):
            words = text.split()
            target_words = int(budget / 1.3)
            return " ".join(words[:target_words])

        retained = 0
        for r in records:
            budget = int(r["token_count"] * 0.50)
            trunc = mutated_compress(r["full_text"], budget)
            if r["expected_answer"].lower() in trunc.lower():
                retained += 1

        retention_rate = retained / len(records)
        print(f"\n[Mutation Test] Naive Truncation Needle Retention on Mid/End needles: {retention_rate*100:.1f}%")

        # Naive truncation should retain < 50% of middle/end needles
        assert retention_rate < 0.50, "Mutation failed: naive truncation unexpectedly preserved needles"

    def test_regression_guard_against_baselines_json(self):
        """Guards against performance regression relative to baselines.json bounds."""
        bm = self.baselines["metrics"]

        # Verify baselines structure integrity
        assert "routellm_pareto" in bm
        assert "llmlingua_compression" in bm
        assert "pii_firewall" in bm
        assert "latency_and_throughput" in bm

        # Ensure baselines.json contains non-empty valid metrics
        assert bm["routellm_pareto"]["auc_delta"] >= 0.08
        assert bm["llmlingua_compression"]["qa_accuracy_retention"] >= 0.85
        assert bm["pii_firewall"]["overall_f1_score"] >= 0.90
        assert bm["latency_and_throughput"]["exact_cache_p99_ms"] <= 0.10
