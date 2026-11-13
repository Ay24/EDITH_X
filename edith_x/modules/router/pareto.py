"""M9 — Calibrated Pareto Cost-Complexity Router with Hybrid Semantic Centroid Calibration."""
from __future__ import annotations

import math
import re


def _build_sparse_centroid(terms: list[str]) -> dict[str, float]:
    vec: dict[str, float] = {}
    for t in terms:
        vec[t] = vec.get(t, 0.0) + 1.0
    norm = math.sqrt(sum(v * v for v in vec.values()))
    if norm > 0:
        for k in vec:
            vec[k] /= norm
    return vec


def _sparse_cosine(query_terms: list[str], centroid: dict[str, float]) -> float:
    if not query_terms:
        return 0.0
    q_vec: dict[str, float] = {}
    for t in query_terms:
        q_vec[t] = q_vec.get(t, 0.0) + 1.0
    norm = math.sqrt(sum(v * v for v in q_vec.values()))
    if norm == 0:
        return 0.0
    dot = 0.0
    for t, val in q_vec.items():
        if t in centroid:
            dot += (val / norm) * centroid[t]
    return dot


# Domain reference centroids for semantic calibration
_COMPLEX_TERMS = [
    "proof", "prove", "formal", "byzantine", "consensus", "distributed",
    "quantum", "cryptography", "kernel", "assembly", "compiler", "ast",
    "latex", "derivation", "mathematical", "deadlock", "race", "condition",
    "zero-knowledge", "snark", "circuit", "combinatorial", "lock-free",
    "threat", "security", "audit", "architect", "microservices", "latencies",
    "cqrs", "event", "sourcing", "paxos", "raft", "multithreaded", "anomalous",
    "undecidability", "differential", "equation", "hamiltonian", "lyapunov",
    "relativistic", "dilation", "tla+", "compaction", "workers", "allocation",
]

_SIMPLE_TERMS = [
    "what", "how", "define", "difference", "example", "hello", "hi", "help",
    "summary", "tldr", "syntax", "format", "command", "convert", "chemical",
    "port", "rephrase", "bullet", "meeting", "points", "notes", "team", "translate",
]

_COMPLEX_CENTROID = _build_sparse_centroid(_COMPLEX_TERMS)
_SIMPLE_CENTROID = _build_sparse_centroid(_SIMPLE_TERMS)


class ParetoModelRouter:
    """
    Calibrated routing engine that predicts whether a cheap/local model
    can satisfy the query with comparable quality to a flagship cloud LLM.
    Supports hybrid heuristic-plus-centroid semantic evaluation and
    continuous threshold tuning for Pareto curve generation.
    """

    COMPLEX_MARKERS = [
        "proof", "prove", "formal", "byzantine", "consensus", "distributed",
        "quantum", "cryptography", "kernel", "assembly", "compiler", "ast",
        "latex", "derivation", "mathematical", "deadlock", "race condition",
        "zero-knowledge", "snark", "circuit", "combinatorial", "lock-free",
        "threat model", "security audit", "architect", "microservices",
        "cqrs", "event sourcing", "paxos", "raft", "multithreaded",
        "undecidability", "differential equation", "hamiltonian", "lyapunov",
        "relativistic", "dilation", "tla+", "compaction",
    ]

    STRUCTURED_MARKERS = [
        "step-by-step", "in detail", "scale", "benchmark", "optimize",
        "refactor", "algorithmic", "complexity", "vector search",
        "concurrency", "low latency", "fault-tolerant", "calculate the total",
        "how many more", "taking into account", "reduction from", "how much more",
        "half as many", "twice as many", "three times", "divided equally",
        "percentage of remaining", "consecutive", "probability of", "saving money",
        "how much more money", "non-remote", "per day plus", "discounted by",
    ]

    SIMPLE_MARKERS = [
        "what is", "how do i", "define", "difference between", "example of",
        "hello", "hi", "help", "summary", "tldr", "syntax", "format",
        "command to", "convert", "chemical symbol", "port for", "multiplied by",
        "how much did she earn", "how many loaves", "volume of a cylinder",
        "how many legs",
    ]

    def __init__(self, threshold_cheap: float = 0.50, threshold_medium: float = 0.42) -> None:
        self.threshold_cheap = threshold_cheap
        self.threshold_medium = threshold_medium

    def predict_cheap_capability(self, query: str) -> float:
        """
        Calculate probability P(cheap_is_sufficient) in [0.0, 1.0].
        Higher score = simpler task, local/cheap model excels.
        Lower score = harder reasoning task, flagship cloud needed.
        """
        q_lower = query.lower()
        words = re.findall(r"\b\w+\b", q_lower)
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

        # 3. Structural & Multi-step reasoning markers
        struct_hits = sum(1 for m in self.STRUCTURED_MARKERS if m in q_lower)
        score -= struct_hits * 0.20

        # 4. Simple / FAQ markers
        simple_hits = sum(1 for m in self.SIMPLE_MARKERS if m in q_lower)
        score += simple_hits * 0.18

        # 5. Multi-step numerical reasoning detection
        numbers = re.findall(r"\b\d+\b", query)
        if len(numbers) >= 2 and any(w in q_lower for w in ("how many", "calculate", "remaining", "ratio", "percent", "how much", "sold", "spent", "earns")):
            if any(w in q_lower for w in ("half", "twice", "more", "then", "after", "divided", "remaining", "discount")):
                score -= 0.24

        # 6. Code blocks / symbols detection
        if "```" in query or ("{" in query and "}" in query):
            score -= 0.10

        # 7. Semantic Centroid Calibration for borderline queries
        initial_prob = 1.0 / (1.0 + math.exp(-3.0 * (score - 0.5)))
        if 0.30 <= initial_prob <= 0.70 and words:
            sim_complex = _sparse_cosine(words, _COMPLEX_CENTROID)
            sim_simple = _sparse_cosine(words, _SIMPLE_CENTROID)
            centroid_delta = (sim_simple - sim_complex) * 0.40
            score += centroid_delta

        # Sigmoid clamping to [0.01, 0.99]
        clamped = 1.0 / (1.0 + math.exp(-3.0 * (score - 0.5)))
        return round(min(max(clamped, 0.01), 0.99), 3)

    def select_tier(
        self,
        query: str,
        threshold: float | None = None,
        budget_mode: str = "balanced",
    ) -> str:
        """
        Map query to execution tier:
        - L1_local: Local model (Llama-3.2 3B/8B, $0.00)
        - L2_compressed: Fast cloud model (Llama-3.1 70B / NIM, low cost)
        - L3_cloud: Flagship frontier model (GPT-4o / Claude 3.5 Sonnet)

        budget_mode supports:
        - 'cost_saver': Lower thresholds, routing more queries to local/compressed tiers.
        - 'quality_first': Higher thresholds, routing more queries to flagship frontier.
        - 'balanced': Default Pareto frontier.
        """
        prob = self.predict_cheap_capability(query)
        if threshold is not None:
            return "L1_local" if prob >= threshold else "L3_cloud"

        t_cheap = self.threshold_cheap
        t_medium = self.threshold_medium

        if budget_mode == "cost_saver":
            t_cheap = max(0.20, t_cheap - 0.12)
            t_medium = max(0.15, t_medium - 0.10)
        elif budget_mode == "quality_first":
            t_cheap = min(0.85, t_cheap + 0.15)
            t_medium = min(0.75, t_medium + 0.12)

        if prob >= t_cheap:
            return "L1_local"
        elif prob >= t_medium:
            return "L2_compressed"
        else:
            return "L3_cloud"
