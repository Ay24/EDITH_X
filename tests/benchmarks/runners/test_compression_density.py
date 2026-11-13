"""Task 3: Microsoft LLMLingua Information-Density Compression & Needle Recall Benchmark.
Derived from Microsoft LLMLingua (https://github.com/microsoft/LLMLingua).
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from edith_x.modules.optimization.compressor import InformationDensityCompressor

DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"


def load_compression_dataset():
    path = DATASETS_DIR / "compression_eval.jsonl"
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


class TestLLMLinguaCompression:
    """Evaluates information density compression and critical entity needle preservation."""

    @pytest.fixture(autouse=True)
    def setup_compressor(self):
        self.compressor = InformationDensityCompressor()
        self.records = load_compression_dataset()

    def test_compression_ratio_reduction(self):
        """Asserts that verbose documents achieve >= 35% token reduction (ratio <= 0.65)."""
        assert len(self.records) >= 5

        ratios = []
        for rec in self.records:
            res = self.compressor.compress(rec["text"], budget=rec["budget"])
            ratios.append(res.compression_ratio)
            print(f"\n[{rec['id']} - {rec['description']}]")
            print(f"  Original Tokens:   {res.original_tokens}")
            print(f"  Compressed Tokens: {res.compressed_tokens}")
            print(f"  Compression Ratio: {res.compression_ratio:.2f} (Savings: {(1 - res.compression_ratio) * 100:.1f}%)")

        avg_ratio = sum(ratios) / len(ratios)
        avg_savings = (1.0 - avg_ratio) * 100.0
        print(f"\n[LLMLingua Benchmark Summary] Average Token Savings: {avg_savings:.2f}% (Avg Ratio: {avg_ratio:.2f})")

        # Industry standard: At least 35% reduction on verbose compliance/operational prose
        assert avg_ratio <= 0.65, f"Average compression ratio {avg_ratio:.2f} exceeded 0.65 threshold"

    def test_entity_needle_recall(self):
        """Asserts that critical semantic needles (IDs, hashes, limits) are preserved >= 90%."""
        total_needles = 0
        retained_needles = 0

        for rec in self.records:
            res = self.compressor.compress(rec["text"], budget=rec["budget"])
            needles = rec["needles"]
            total_needles += len(needles)

            for needle in needles:
                if needle.lower() in res.compressed_text.lower():
                    retained_needles += 1
                else:
                    print(f"  [MISSING NEEDLE]: '{needle}' in {rec['id']}")

        recall = retained_needles / total_needles
        print(f"\n[LLMLingua Needle Recall]: {recall * 100:.2f}% ({retained_needles}/{total_needles} needles preserved)")

        # Industry standard: High-density compressor must retain >= 90% critical needles
        assert recall >= 0.90, f"Entity recall {recall * 100:.1f}% fell below 90% threshold"
