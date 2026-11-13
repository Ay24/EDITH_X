"""Task: LMSYS RouteLLM Pareto Cost-Quality & Baselines Benchmark.
Derived from UC Berkeley / LMSYS RouteLLM (https://github.com/lm-sys/RouteLLM).
Evaluates on held-out test split of GSM8K / reasoning corpus (n >= 100 test samples).
Computes 95% bootstrap confidence intervals, baselines (Always-Strong, Always-Weak, Random),
and Pareto frontier trade-offs.
"""
from __future__ import annotations

import json
from pathlib import Path
import random
import numpy as np
import pytest
import yaml

from edith_x.modules.router.pareto import ParetoModelRouter

BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
THRESHOLDS_PATH = BASE_DIR / "thresholds.yaml"


def load_thresholds():
    with open(THRESHOLDS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_gsm8k_test_split():
    path = DATASETS_DIR / "gsm8k_eval.jsonl"
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    # Held-out test split only
    test_records = [r for r in records if r.get("split") == "test"]
    return test_records, records


def bootstrap_ci(data: list[float], n_resamples: int = 1000, ci: float = 0.95) -> tuple[float, float, float]:
    """Calculate mean and (lower, upper) bootstrap confidence interval."""
    if not data:
        return 0.0, 0.0, 0.0
    arr = np.array(data)
    means = []
    np.random.seed(42)
    for _ in range(n_resamples):
        sample = np.random.choice(arr, size=len(arr), replace=True)
        means.append(np.mean(sample))
    mean_val = float(np.mean(arr))
    alpha = (1.0 - ci) / 2.0
    lower = float(np.percentile(means, alpha * 100))
    upper = float(np.percentile(means, (1.0 - alpha) * 100))
    return mean_val, lower, upper


class TestRouteLLMParetoAudited:
    """Rigorous evaluation of Pareto routing against held-out GSM8K reasoning data."""

    @pytest.fixture(autouse=True)
    def setup_router(self):
        self.thresholds = load_thresholds()["routing_benchmarks"]
        self.router = ParetoModelRouter()
        self.test_records, self.all_records = load_gsm8k_test_split()
        random.seed(42)

    def test_held_out_sample_size_enforcement(self):
        """Enforces that total samples >= 200 and held-out test samples >= 100."""
        assert len(self.all_records) >= self.thresholds["min_total_samples"], (
            f"Total records {len(self.all_records)} < {self.thresholds['min_total_samples']}"
        )
        assert len(self.test_records) >= self.thresholds["min_test_samples"], (
            f"Held-out test records {len(self.test_records)} < {self.thresholds['min_test_samples']}"
        )

    def test_pareto_curve_and_baselines_with_ci(self):
        """
        Evaluates Pareto curve against Always-Strong, Always-Weak, and Random Router baselines.
        Computes 95% bootstrap confidence intervals over 1,000 resamples.
        """
        n = len(self.test_records)
        always_strong_correct = [1.0 if r["strong_model_correct"] else 0.0 for r in self.test_records]
        always_weak_correct = [1.0 if r["cheap_model_correct"] else 0.0 for r in self.test_records]

        strong_acc, strong_lo, strong_hi = bootstrap_ci(always_strong_correct)
        weak_acc, weak_lo, weak_hi = bootstrap_ci(always_weak_correct)

        print("\n--- RouteLLM Baselines (Held-out Test, n=100) ---")
        print(f"Always-Strong (Flagship): {strong_acc*100:.2f}% (95% CI: [{strong_lo*100:.2f}%, {strong_hi*100:.2f}%])")
        print(f"Always-Weak   (Local 8B): {weak_acc*100:.2f}% (95% CI: [{weak_lo*100:.2f}%, {weak_hi*100:.2f}%])")

        # Threshold sweep across tau in [0.05, 0.95] to construct Pareto curve
        pareto_points = []
        random_points = []
        thresholds_sweep = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]

        for tau in thresholds_sweep:
            strong_calls = 0
            correct_list = []
            for r in self.test_records:
                tier = self.router.select_tier(r["question"], threshold=tau)
                if tier == "L3_cloud":
                    strong_calls += 1
                    correct_list.append(1.0 if r["strong_model_correct"] else 0.0)
                else:
                    correct_list.append(1.0 if r["cheap_model_correct"] else 0.0)

            strong_call_ratio = strong_calls / n
            acc, lo, hi = bootstrap_ci(correct_list)
            pareto_points.append({
                "tau": tau,
                "strong_ratio": strong_call_ratio,
                "accuracy": acc,
                "ci_lower": lo,
                "ci_upper": hi,
            })

            # Random router baseline matching same strong_ratio
            rand_correct = []
            for r in self.test_records:
                if random.random() < strong_call_ratio:
                    rand_correct.append(1.0 if r["strong_model_correct"] else 0.0)
                else:
                    rand_correct.append(1.0 if r["cheap_model_correct"] else 0.0)
            rand_acc, _, _ = bootstrap_ci(rand_correct)
            random_points.append({"strong_ratio": strong_call_ratio, "accuracy": rand_acc})

        # Calculate AUC (Area under curve) for Pareto router vs Random router
        # Sort by strong_ratio
        pareto_points.sort(key=lambda x: x["strong_ratio"])
        random_points.sort(key=lambda x: x["strong_ratio"])

        auc_pareto = np.trapezoid([p["accuracy"] for p in pareto_points], [p["strong_ratio"] for p in pareto_points])
        auc_random = np.trapezoid([p["accuracy"] for p in random_points], [p["strong_ratio"] for p in random_points])
        auc_delta = float(auc_pareto - auc_random)

        print("\n--- RouteLLM Pareto Trade-Off Curve ---")
        for p in pareto_points:
            print(f"  Threshold={p['tau']:.2f} | % Strong Calls={p['strong_ratio']*100:.1f}% | Acc={p['accuracy']*100:.1f}% (CI: [{p['ci_lower']*100:.1f}%, {p['ci_upper']*100:.1f}%])")

        print(f"\nRouter AUC: {auc_pareto:.4f} vs Random Router AUC: {auc_random:.4f} (Delta: {auc_delta:+.4f})")

        # Pre-committed threshold assertion: AUC delta must exceed random router by >= 0.10
        assert auc_delta >= self.thresholds["min_auc_delta_vs_random"], (
            f"Router AUC delta {auc_delta:.4f} fell below pre-committed {self.thresholds['min_auc_delta_vs_random']}"
        )

        # Check % strong calls to retain 90% of always-strong quality
        target_90pct_acc = 0.90 * strong_acc
        points_meeting_90 = [p for p in pareto_points if p["accuracy"] >= target_90pct_acc]
        assert len(points_meeting_90) > 0, "No operating point achieved 90% quality"
        min_strong_for_90 = min(p["strong_ratio"] for p in points_meeting_90)

        print(f"Strong model calls required to retain 90% quality: {min_strong_for_90*100:.1f}% (Pre-committed target: <= {self.thresholds['max_strong_calls_for_90pct_quality']*100:.0f}%)")
        assert min_strong_for_90 <= self.thresholds["max_strong_calls_for_90pct_quality"], (
            f"Strong calls {min_strong_for_90:.2f} exceeded threshold {self.thresholds['max_strong_calls_for_90pct_quality']}"
        )

    def test_enterprise_workload_cost_savings(self):
        """
        Evaluates cost reduction across 50/50, 70/30, and 90/10 traffic distributions
        with 1,000 bootstrap resamples for 95% confidence intervals.
        """
        COST_CHEAP = 0.0001
        COST_STRONG = 0.0030

        simple_records = [r for r in self.test_records if r["complexity_level"] == "simple"]
        complex_records = [r for r in self.test_records if r["complexity_level"] == "complex"]

        mixes = {
            "split_50_50": (0.50, 0.50, self.thresholds["cost_reduction"]["split_50_50_min_pct"]),
            "split_70_30": (0.70, 0.30, self.thresholds["cost_reduction"]["split_70_30_min_pct"]),
            "split_90_10": (0.90, 0.10, self.thresholds["cost_reduction"]["split_90_10_min_pct"]),
        }

        print("\n--- Enterprise Workload Cost Savings (Bootstrap 95% CIs) ---")
        for mix_name, (w_simple, w_complex, min_pct) in mixes.items():
            savings_samples = []
            np.random.seed(42)
            for _ in range(1000):
                # Resample simple and complex
                s_sample = [random.choice(simple_records) for _ in range(len(simple_records))]
                c_sample = [random.choice(complex_records) for _ in range(len(complex_records))]

                cost_s = sum(
                    COST_STRONG if self.router.select_tier(r["question"]) == "L3_cloud" else COST_CHEAP
                    for r in s_sample
                ) / len(s_sample)
                cost_c = sum(
                    COST_STRONG if self.router.select_tier(r["question"]) == "L3_cloud" else COST_CHEAP
                    for r in c_sample
                ) / len(c_sample)

                routed_cost = w_simple * cost_s + w_complex * cost_c
                savings_pct = (1.0 - (routed_cost / COST_STRONG)) * 100.0
                savings_samples.append(savings_pct)

            mean_s, lo_s, hi_s = bootstrap_ci(savings_samples)
            print(f"  {mix_name} ({int(w_simple*100)}/{int(w_complex*100)} mix): {mean_s:.2f}% (95% CI: [{lo_s:.2f}%, {hi_s:.2f}%]), Pre-committed: >= {min_pct:.1f}%")
            assert mean_s >= min_pct, f"{mix_name} mean savings {mean_s:.2f}% < {min_pct:.1f}%"

    def test_documented_failure_cases(self):
        """
        Discloses concrete failure cases:
        1. Downgraded response: Complex reasoning query routed to cheap model that failed.
        2. Over-routed query: Simple query routed to expensive model.
        """
        downgraded_cases = []
        overrouted_cases = []

        for r in self.test_records:
            tier = self.router.select_tier(r["question"])
            # Downgrade: complex question routed to cheap tier, and cheap model failed
            if r["complexity_level"] == "complex" and tier != "L3_cloud" and not r["cheap_model_correct"]:
                downgraded_cases.append(r)
            # Over-routed: simple question routed to L3
            elif r["complexity_level"] == "simple" and tier == "L3_cloud":
                overrouted_cases.append(r)

        print("\n--- Disclosed Failure Cases Analysis ---")
        print(f"Total test samples: {len(self.test_records)}")
        print(f"Downgraded reasoning cases (routed cheap, model failed): {len(downgraded_cases)}")
        print(f"Over-routed routine cases (routed L3 unnecessarily): {len(overrouted_cases)}")

        if downgraded_cases:
            print(f"Example Downgrade: '{downgraded_cases[0]['question'][:90]}...'")
        if overrouted_cases:
            print(f"Example Over-route: '{overrouted_cases[0]['question'][:90]}...'")

        # Failure cases are expected in realistic routing, verify they are bounded (< 20%)
        downgrade_rate = len(downgraded_cases) / len(self.test_records)
        assert downgrade_rate < 0.20, f"Downgrade rate {downgrade_rate*100:.1f}% exceeded 20% safety limit"
