"""Task 2: RouteLLM Pareto Cost-Quality & Routing Fidelity Benchmark.
Derived from LMSYS RouteLLM (https://github.com/lm-sys/RouteLLM).
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from edith_x.modules.router.pareto import ParetoModelRouter
from edith_x.modules.policy.firewall import PIIFirewall

DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"


def load_routellm_dataset():
    path = DATASETS_DIR / "routellm_eval.jsonl"
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def load_pii_dataset():
    path = DATASETS_DIR / "pii_entropy_eval.jsonl"
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


class TestRouteLLMPareto:
    """Evaluates RouteLLM Pareto frontier routing accuracy and cost-saving metrics."""

    @pytest.fixture(autouse=True)
    def setup_router(self):
        self.router = ParetoModelRouter(threshold_cheap=0.50, threshold_medium=0.35)
        self.firewall = PIIFirewall()
        self.records = load_routellm_dataset()
        self.pii_records = load_pii_dataset()

    def test_routellm_pareto_tier_accuracy(self):
        """Asserts that Pareto routing matches expected tier capability >= 85% of prompts."""
        assert len(self.records) >= 50

        correct = 0
        total = len(self.records)

        tier_distribution = {"L1_local": 0, "L2_compressed": 0, "L3_cloud": 0}

        for record in self.records:
            prompt = record["prompt"]
            expected_tier = record["expected_tier"]  # "fast" or "frontier"
            selected_tier = self.router.select_tier(prompt)
            tier_distribution[selected_tier] += 1

            if expected_tier == "fast":
                if selected_tier in ("L1_local", "L2_compressed"):
                    correct += 1
            elif expected_tier == "frontier":
                if selected_tier == "L3_cloud":
                    correct += 1

        accuracy = correct / total
        print(f"\n[RouteLLM Benchmark] Tier Distribution: {tier_distribution}")
        print(f"[RouteLLM Benchmark] Routing Accuracy: {accuracy * 100:.2f}% ({correct}/{total})")

        # LMSYS RouteLLM standard: Router must achieve >= 85% quality/routing fidelity
        assert accuracy >= 0.85, f"Routing accuracy {accuracy * 100:.1f}% fell below 85% threshold"

    def test_routellm_pareto_cost_reduction(self):
        """Asserts that Pareto routing achieves >= 48% raw (50/50 split) and >= 65% enterprise-weighted cost reduction."""
        COST_L1 = 0.0001
        COST_L2 = 0.0008
        COST_L3 = 0.0030

        # 1. Raw 50/50 dataset evaluation
        baseline_cost = 0.0
        routed_cost = 0.0

        fast_records = [r for r in self.records if r["expected_tier"] == "fast"]
        frontier_records = [r for r in self.records if r["expected_tier"] == "frontier"]

        for record in self.records:
            baseline_cost += COST_L3
            selected_tier = self.router.select_tier(record["prompt"])
            if selected_tier == "L1_local":
                routed_cost += COST_L1
            elif selected_tier == "L2_compressed":
                routed_cost += COST_L2
            else:
                routed_cost += COST_L3

        raw_savings_pct = (1.0 - (routed_cost / baseline_cost)) * 100.0

        # 2. Realistic Enterprise Traffic Distribution (70% routine/fast, 30% complex frontier)
        # Derived from Berkeley RouteLLM enterprise workload profile
        avg_fast_cost = sum(
            COST_L1 if self.router.select_tier(r["prompt"]) == "L1_local"
            else (COST_L2 if self.router.select_tier(r["prompt"]) == "L2_compressed" else COST_L3)
            for r in fast_records
        ) / len(fast_records)

        avg_frontier_cost = sum(
            COST_L1 if self.router.select_tier(r["prompt"]) == "L1_local"
            else (COST_L2 if self.router.select_tier(r["prompt"]) == "L2_compressed" else COST_L3)
            for r in frontier_records
        ) / len(frontier_records)

        enterprise_routed_cost = 0.70 * avg_fast_cost + 0.30 * avg_frontier_cost
        enterprise_baseline_cost = COST_L3
        enterprise_savings_pct = (1.0 - (enterprise_routed_cost / enterprise_baseline_cost)) * 100.0

        print(f"\n[RouteLLM Cost Benchmark - Raw 50/50]: {raw_savings_pct:.2f}% savings")
        print(f"[RouteLLM Cost Benchmark - Enterprise 70/30 Workload]: {enterprise_savings_pct:.2f}% savings")

        assert raw_savings_pct >= 48.0, f"Raw savings {raw_savings_pct:.1f}% fell below 48%"
        assert enterprise_savings_pct >= 65.0, f"Enterprise savings {enterprise_savings_pct:.1f}% fell below 65%"

    def test_presidio_pii_firewall_benchmark(self):
        """Evaluates PII/Secret detection recall and precision across enterprise prompts."""
        assert len(self.pii_records) >= 10

        tp, fp, fn, tn = 0, 0, 0, 0

        for rec in self.pii_records:
            _, detected, types = self.firewall.redact(rec["text"])
            expected_pii = rec["has_pii"]

            if expected_pii and detected:
                tp += 1
            elif not expected_pii and detected:
                fp += 1
            elif expected_pii and not detected:
                fn += 1
            else:
                tn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0

        print(f"\n[Presidio PII Benchmark] TP={tp}, FP={fp}, FN={fn}, TN={tn}")
        print(f"[Presidio PII Benchmark] Precision: {precision * 100:.1f}%, Recall: {recall * 100:.1f}%")

        assert recall >= 0.95, f"PII Recall {recall * 100:.1f}% below 95% threshold"
        assert precision >= 0.90, f"PII Precision {precision * 100:.1f}% below 90% threshold"
