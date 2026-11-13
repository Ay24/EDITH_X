"""M9 — Calibrated Pareto Cost-Complexity Router (Reverse-Engineered from RouteLLM)."""
from __future__ import annotations

import math
import re


class ParetoModelRouter:
    """
    Calibrated routing engine that predicts whether a cheap/local model
    can satisfy the query with comparable quality to a flagship cloud LLM.
    """

    COMPLEX_MARKERS = [
        "proof", "prove", "formal", "byzantine", "consensus", "distributed",
        "quantum", "cryptography", "kernel", "assembly", "compiler", "ast",
        "latex", "derivation", "mathematical", "deadlock", "race condition",
        "zero-knowledge", "snark", "circuit", "combinatorial", "lock-free",
        "threat model", "security audit", "architect", "microservices",
        "cqrs", "event sourcing", "paxos", "raft", "multithreaded",
    ]

    STRUCTURED_MARKERS = [
        "step-by-step", "in detail", "scale", "benchmark", "optimize",
        "refactor", "algorithmic", "complexity", "vector search",
        "concurrency", "low latency", "fault-tolerant",
    ]

    SIMPLE_MARKERS = [
        "what is", "how do i", "define", "difference between", "example of",
        "hello", "hi", "help", "summary", "tldr", "syntax", "format",
        "command to", "convert", "chemical symbol", "port for",
    ]

    def __init__(self, threshold_cheap: float = 0.50, threshold_medium: float = 0.35) -> None:
        self.threshold_cheap = threshold_cheap
        self.threshold_medium = threshold_medium

    def predict_cheap_capability(self, query: str) -> float:
        """
        Calculate probability P(cheap_is_sufficient) in [0.0, 1.0].
        Higher score = simpler task, local/cheap model excels.
        Lower score = harder reasoning task, flagship cloud needed.
        """
        q_lower = query.lower()
        words = q_lower.split()
        word_count = len(words)

        # Baseline: moderate probability
        score = 0.65

        # 1. Length penalty (long context or multi-paragraph queries need larger reasoning context)
        if word_count > 150:
            score -= 0.35
        elif word_count > 60:
            score -= 0.15
        elif word_count < 15:
            score += 0.15

        # 2. Complex domain markers
        complex_hits = sum(1 for m in self.COMPLEX_MARKERS if m in q_lower)
        score -= complex_hits * 0.28

        # 3. Structural depth markers
        struct_hits = sum(1 for m in self.STRUCTURED_MARKERS if m in q_lower)
        score -= struct_hits * 0.14

        # 4. Simple / FAQ markers
        simple_hits = sum(1 for m in self.SIMPLE_MARKERS if m in q_lower)
        score += simple_hits * 0.18

        # 5. Code blocks / symbols detection
        if "```" in query or ("{" in query and "}" in query):
            score -= 0.10

        # Sigmoid clamping to [0.01, 0.99]
        clamped = 1.0 / (1.0 + math.exp(-3.0 * (score - 0.5)))
        return round(min(max(clamped, 0.01), 0.99), 3)

    def select_tier(self, query: str) -> str:
        """
        Map query to execution tier:
        - L1_local: Local model (Llama-3.2 3B/8B, $0.00)
        - L2_compressed: Fast cloud model (Llama-3.1 70B / NIM, low cost)
        - L3_cloud: Flagship frontier model (GPT-4o / Claude 3.5 Sonnet)
        """
        prob = self.predict_cheap_capability(query)
        if prob >= self.threshold_cheap:
            return "L1_local"
        elif prob >= self.threshold_medium:
            return "L2_compressed"
        else:
            return "L3_cloud"
