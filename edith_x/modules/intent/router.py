"""M3 — Sub-2ms Centroid Vector Intent Router (Reverse-Engineered from semantic-router)."""
from __future__ import annotations

import math
import re

ROUTE_EXEMPLARS: dict[str, list[str]] = {
    "coding": [
        "write a python script to process files",
        "implement a new rest api endpoint",
        "debug this function error",
        "fix bug in authentication logic",
        "refactor this class to use async",
        "write unit tests for this module",
        "create a react component for modal",
        "solve this algorithmic programming problem",
        "compile and build dockerfile",
        "fix syntax error and traceback",
        "write code to parse json",
    ],
    "security": [
        "scan this application for vulnerabilities",
        "check for sql injection or xss attacks",
        "perform a penetration test on the api",
        "audit iam permissions and rbac policies",
        "threat model for microservices network",
        "check if this password hash is secure",
        "remediate security compliance findings",
        "pentest the cloud infrastructure",
    ],
    "retrieval": [
        "find all documents related to enterprise policies",
        "search the knowledge base for onboarding guides",
        "look up user account records in database",
        "retrieve employee health insurance docs",
        "fetch the latest financial statements",
        "search our vector database for notes",
    ],
    "summarization": [
        "give me a brief summary of this article",
        "tldr for the 50 page legal contract",
        "summarize meeting notes and action items",
        "condense this customer feedback into bullet points",
        "create an executive overview of the report",
        "summarize this transcript briefly",
    ],
    "analysis": [
        "analyze quarterly financial performance trends",
        "evaluate pros and cons of microservices vs monolith",
        "compare aws vs gcp cloud hosting costs",
        "assess risk of customer churn in this dataset",
        "deep dive into system latency metrics",
        "perform statistical analysis on conversion rate",
    ],
    "planning": [
        "create a project roadmap for the next quarter",
        "plan migration from legacy database to postgres",
        "schedule sprint tasks and deliverables",
        "outline strategy for product launch",
        "build an implementation timeline for feature",
    ],
    "automation": [
        "automate recurring billing invoice generation",
        "schedule daily backup cron job",
        "trigger ci cd deployment workflow",
        "run pipeline across batch worker nodes",
        "automate customer email notifications",
    ],
    "question": [
        "what is the capital of france",
        "how does quantum computing work",
        "why is the sky blue",
        "who was the first person on the moon",
        "explain the difference between tcp and udp",
        "when was python released",
    ],
}


def _tokenize(text: str) -> list[str]:
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    words = clean.split()
    tokens = list(words)
    for i in range(len(words) - 1):
        tokens.append(f"{words[i]}_{words[i+1]}")
    return tokens


def _compute_vector(tokens: list[str]) -> dict[str, float]:
    tf: dict[str, float] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0.0) + 1.0
    norm = math.sqrt(sum(v * v for v in tf.values()))
    if norm > 0:
        for k in tf:
            tf[k] /= norm
    return tf


def _dot_product(vec1: dict[str, float], vec2: dict[str, float]) -> float:
    if len(vec1) > len(vec2):
        vec1, vec2 = vec2, vec1
    return sum(v1 * vec2[k] for k, v1 in vec1.items() if k in vec2)


class CentroidIntentRouter:
    """Classifies user intent using precomputed route centroids in < 2ms."""

    def __init__(self, threshold: float = 0.12) -> None:
        self.threshold = threshold
        self._centroids: dict[str, dict[str, float]] = {}
        self._build_centroids()

    def _build_centroids(self) -> None:
        for route_name, exemplars in ROUTE_EXEMPLARS.items():
            acc_vector: dict[str, float] = {}
            for ex in exemplars:
                vec = _compute_vector(_tokenize(ex))
                for k, v in vec.items():
                    acc_vector[k] = acc_vector.get(k, 0.0) + v
            # Normalize centroid vector
            norm = math.sqrt(sum(v * v for v in acc_vector.values()))
            if norm > 0:
                for k in acc_vector:
                    acc_vector[k] /= norm
            self._centroids[route_name] = acc_vector

    def classify(self, query: str) -> str:
        q_tokens = _tokenize(query)
        if not q_tokens:
            return "question"

        q_vec = _compute_vector(q_tokens)
        best_route = "task"
        best_score = -1.0

        for route_name, centroid in self._centroids.items():
            score = _dot_product(q_vec, centroid)
            if score > best_score:
                best_score = score
                best_route = route_name

        if best_score < self.threshold:
            return "question" if any(w in query.lower().split() for w in ("what", "how", "why", "who", "when")) else "task"

        return best_route
