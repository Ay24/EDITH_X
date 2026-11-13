"""Task: Microsoft LLMLingua Compression & Needle-In-Haystack QA Benchmark.
Derived from Microsoft Research LLMLingua (https://github.com/microsoft/LLMLingua).
Evaluates downstream Question-Answering retention across 3 context lengths (500, 1000, 2000 tokens)
and needle positions (start, middle, end) against Naive Truncation and Random Token Dropping baselines.
"""
from __future__ import annotations

import json
from pathlib import Path
import random
import numpy as np
import pytest
import yaml

from edith_x.modules.optimization.compressor import InformationDensityCompressor

BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
THRESHOLDS_PATH = BASE_DIR / "thresholds.yaml"


def load_thresholds():
    with open(THRESHOLDS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["compression_benchmarks"]


def load_compression_qa_dataset():
    path = DATASETS_DIR / "compression_qa_eval.jsonl"
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def bootstrap_ci(data: list[float], n_resamples: int = 1000, ci: float = 0.95) -> tuple[float, float, float]:
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


def naive_truncation(text: str, budget_tokens: int) -> str:
    """Baseline 1: Keep first budget_tokens tokens."""
    words = text.split()
    target_words = int(budget_tokens / 1.3)
    return " ".join(words[:target_words])


def random_token_dropping(text: str, budget_tokens: int) -> str:
    """Baseline 2: Randomly drop tokens until budget is met."""
    words = text.split()
    target_words = min(len(words), max(1, int(budget_tokens / 1.3)))
    indices = sorted(random.sample(range(len(words)), target_words))
    return " ".join([words[i] for i in indices])


class TestCompressionQAAudited:
    """Audited Needle-In-A-Haystack QA benchmark across multiple lengths and baselines."""

    @pytest.fixture(autouse=True)
    def setup_compressor(self):
        self.thresholds = load_thresholds()
        self.compressor = InformationDensityCompressor()
        self.records = load_compression_qa_dataset()
        random.seed(42)

    def test_sample_size_and_lengths_enforcement(self):
        """Enforces at least 10 samples per context length across 500, 1000, 2000 tokens."""
        assert len(self.records) >= 30
        lengths = set(r["target_length"] for r in self.records)
        assert lengths == set(self.thresholds["context_lengths"])
        for l in lengths:
            matching = [r for r in self.records if r["target_length"] == l]
            assert len(matching) >= self.thresholds["min_samples_per_length"]

    def test_downstream_qa_accuracy_vs_baselines(self):
        """
        Compresses documents to target budget (50% tokens).
        Tests QA answer survival against Naive Truncation and Random Token Dropping.
        Computes 95% bootstrap confidence intervals.
        """
        compressor_qa_scores = []
        truncation_qa_scores = []
        random_drop_qa_scores = []
        compression_ratios = []

        per_length_results = {500: [], 1000: [], 2000: []}
        per_position_results = {"start": [], "middle": [], "end": []}

        for rec in self.records:
            # Set target budget to 50% to ensure whole sentence packing remains <= target threshold
            target_budget = int(rec["token_count"] * 0.50)
            expected = rec["expected_answer"].lower()

            # 1. EDITH-X InformationDensityCompressor
            res = self.compressor.compress(rec["full_text"], budget=target_budget)
            compression_ratios.append(res.compression_ratio)
            comp_hit = 1.0 if expected in res.compressed_text.lower() else 0.0
            compressor_qa_scores.append(comp_hit)

            # 2. Naive Truncation Baseline
            trunc_text = naive_truncation(rec["full_text"], target_budget)
            trunc_hit = 1.0 if expected in trunc_text.lower() else 0.0
            truncation_qa_scores.append(trunc_hit)

            # 3. Random Dropping Baseline
            rand_text = random_token_dropping(rec["full_text"], target_budget)
            rand_hit = 1.0 if expected in rand_text.lower() else 0.0
            random_drop_qa_scores.append(rand_hit)

            per_length_results[rec["target_length"]].append(comp_hit)
            per_position_results[rec["needle_position"]].append(comp_hit)

        # Statistical analysis with bootstrap CIs
        comp_acc, comp_lo, comp_hi = bootstrap_ci(compressor_qa_scores)
        trunc_acc, trunc_lo, trunc_hi = bootstrap_ci(truncation_qa_scores)
        rand_acc, rand_lo, rand_hi = bootstrap_ci(random_drop_qa_scores)
        avg_ratio = float(np.mean(compression_ratios))

        print("\n--- Needle-In-A-Haystack QA Retention vs Baselines (n=30) ---")
        print(f"Target Compression Ratio: {avg_ratio:.2f} ({(1 - avg_ratio)*100:.1f}% token reduction)")
        print(f"EDITH-X Compressor QA Acc: {comp_acc*100:.1f}% (95% CI: [{comp_lo*100:.1f}%, {comp_hi*100:.1f}%])")
        print(f"Naive Truncation Baseline:  {trunc_acc*100:.1f}% (95% CI: [{trunc_lo*100:.1f}%, {trunc_hi*100:.1f}%])")
        print(f"Random Dropping Baseline:  {rand_acc*100:.1f}% (95% CI: [{rand_lo*100:.1f}%, {rand_hi*100:.1f}%])")

        print("\n--- Breakdown by Context Length ---")
        for length, scores in per_length_results.items():
            l_acc, _, _ = bootstrap_ci(scores)
            print(f"  {length} tokens: {l_acc*100:.1f}% retention")

        print("\n--- Breakdown by Needle Position ---")
        for pos, scores in per_position_results.items():
            p_acc, _, _ = bootstrap_ci(scores)
            print(f"  Needle at {pos:<6}: {p_acc*100:.1f}% retention")

        # Pre-committed threshold assertions
        assert avg_ratio <= self.thresholds["target_compression_ratio"], (
            f"Average compression ratio {avg_ratio:.2f} > {self.thresholds['target_compression_ratio']}"
        )
        assert comp_acc >= self.thresholds["min_qa_accuracy_retention"], (
            f"Compressor QA accuracy {comp_acc*100:.1f}% < {self.thresholds['min_qa_accuracy_retention']*100:.1f}%"
        )

        gain_over_trunc = comp_acc - trunc_acc
        gain_over_rand = comp_acc - rand_acc

        print(f"\nGain over Naive Truncation: {gain_over_trunc*100:+.1f}% (Pre-committed target: >= {self.thresholds['min_gain_over_naive_truncation']*100:.1f}%)")
        print(f"Gain over Random Dropping:  {gain_over_rand*100:+.1f}% (Pre-committed target: >= {self.thresholds['min_gain_over_random_dropping']*100:.1f}%)")

        assert gain_over_trunc >= self.thresholds["min_gain_over_naive_truncation"], (
            f"Gain over truncation {gain_over_trunc:.2f} < {self.thresholds['min_gain_over_naive_truncation']}"
        )
        assert gain_over_rand >= self.thresholds["min_gain_over_random_dropping"], (
            f"Gain over random drop {gain_over_rand:.2f} < {self.thresholds['min_gain_over_random_dropping']}"
        )
