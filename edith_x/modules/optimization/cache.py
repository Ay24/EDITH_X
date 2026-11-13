"""M8 — L0 Semantic & Exact-Match Cache Engine with Inverted Index & Two-Tier L1/L2 Sync."""
from __future__ import annotations

import hashlib
import math
import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Protocol

from edith_x.core.interfaces import CacheResult


def _normalize(text: str) -> str:
    """Normalize text for consistent hashing and tokenization."""
    lowered = text.lower().strip()
    return re.sub(r"[^\w\s]", "", lowered)


def _tokenize(text: str) -> list[str]:
    """Tokenize into words and character n-grams for semantic matching."""
    norm = _normalize(text)
    words = norm.split()
    tokens = list(words)
    # Add bigrams
    for i in range(len(words) - 1):
        tokens.append(f"{words[i]}_{words[i+1]}")
    # Add character 3-grams for typo and inflection tolerance
    for w in words:
        if len(w) >= 3:
            for i in range(len(w) - 2):
                tokens.append(w[i:i+3])
    return tokens


def _compute_vector(tokens: list[str]) -> dict[str, float]:
    """Compute normalized term-frequency vector."""
    tf: dict[str, float] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0.0) + 1.0
    norm = math.sqrt(sum(v * v for v in tf.values()))
    if norm > 0:
        for k in tf:
            tf[k] /= norm
    return tf


def _cosine_similarity(vec1: dict[str, float], vec2: dict[str, float]) -> float:
    """Compute cosine similarity between two sparse normalized vectors."""
    if len(vec1) > len(vec2):
        vec1, vec2 = vec2, vec1
    dot = 0.0
    for k, v1 in vec1.items():
        if k in vec2:
            dot += v1 * vec2[k]
    return min(max(dot, 0.0), 1.0)


@dataclass
class CacheEntry:
    query: str
    response: str
    cost_saved: float
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    vector: dict[str, float] = field(default_factory=dict)
    hits: int = 0


class L2DistributedStore(Protocol):
    """Protocol for external distributed cache backends (e.g., Redis, Valkey, Memcached)."""

    async def get_exact(self, key_hash: str) -> CacheEntry | None:
        ...

    async def set_exact(self, key_hash: str, entry: CacheEntry) -> None:
        ...


class InMemoryL2Store:
    """In-memory mock/adapter for L2 distributed storage."""

    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}

    async def get_exact(self, key_hash: str) -> CacheEntry | None:
        return self._store.get(key_hash)

    async def set_exact(self, key_hash: str, entry: CacheEntry) -> None:
        self._store[key_hash] = entry


class SemanticCache:
    """Two-tier cache: L1 in-memory sub-millisecond LRU + L2 distributed adapter

    powered by an inverted candidate index for sub-millisecond vector similarity.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.90,
        max_entries: int = 10000,
        default_ttl_seconds: float = 86400.0,  # 24 hours
        l2_backend: L2DistributedStore | None = None,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.max_entries = max_entries
        self.default_ttl = default_ttl_seconds
        self._l2_backend = l2_backend

        # L1 LRU storage: normalized_hash -> CacheEntry
        self._exact_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        # Inverted index for O(k) candidate pruning: token -> set[entry_hash]
        self._inverted_index: dict[str, set[str]] = {}

    def _hash_query(self, query: str) -> str:
        norm = _normalize(query)
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    async def get(self, query: str) -> CacheResult:
        now = time.time()
        q_hash = self._hash_query(query)

        # 1. Exact Match Fast-Path (< 0.05ms) in L1 LRU
        if q_hash in self._exact_cache:
            entry = self._exact_cache[q_hash]
            if entry.expires_at is None or entry.expires_at > now:
                self._exact_cache.move_to_end(q_hash)
                entry.hits += 1
                return CacheResult(
                    hit=True,
                    response=entry.response,
                    saved_cost_usd=entry.cost_saved,
                    similarity=1.0,
                )
            else:
                self._remove_entry(q_hash)

        # 1b. Check L2 Distributed Store if configured
        if self._l2_backend:
            l2_entry = await self._l2_backend.get_exact(q_hash)
            if l2_entry and (l2_entry.expires_at is None or l2_entry.expires_at > now):
                # Backfill L1
                self._insert_l1(q_hash, l2_entry)
                l2_entry.hits += 1
                return CacheResult(
                    hit=True,
                    response=l2_entry.response,
                    saved_cost_usd=l2_entry.cost_saved,
                    similarity=1.0,
                )

        # 2. Semantic Similarity Path with Inverted Index Candidate Pruning
        q_tokens = _tokenize(query)
        if not q_tokens:
            return CacheResult(hit=False, response="", saved_cost_usd=0.0)

        q_vector = _compute_vector(q_tokens)

        # Fast candidate gathering: only inspect entries sharing at least 1 token
        candidate_hashes: set[str] = set()
        for token in q_vector.keys():
            if token in self._inverted_index:
                candidate_hashes.update(self._inverted_index[token])

        if not candidate_hashes:
            return CacheResult(hit=False, response="", saved_cost_usd=0.0, similarity=0.0)

        best_score = 0.0
        best_entry: CacheEntry | None = None

        for c_hash in candidate_hashes:
            entry = self._exact_cache.get(c_hash)
            if not entry:
                continue
            if entry.expires_at is not None and entry.expires_at <= now:
                continue
            sim = _cosine_similarity(q_vector, entry.vector)
            if sim > best_score:
                best_score = sim
                best_entry = entry

        if best_entry and best_score >= self.similarity_threshold:
            best_entry.hits += 1
            return CacheResult(
                hit=True,
                response=best_entry.response,
                saved_cost_usd=best_entry.cost_saved,
                similarity=best_score,
            )

        return CacheResult(hit=False, response="", saved_cost_usd=0.0, similarity=best_score)

    def _remove_entry(self, q_hash: str) -> None:
        entry = self._exact_cache.pop(q_hash, None)
        if entry:
            for token in entry.vector.keys():
                if token in self._inverted_index:
                    self._inverted_index[token].discard(q_hash)
                    if not self._inverted_index[token]:
                        del self._inverted_index[token]

    def _insert_l1(self, q_hash: str, entry: CacheEntry) -> None:
        if len(self._exact_cache) >= self.max_entries:
            oldest_hash, _ = self._exact_cache.popitem(last=False)
            self._remove_entry(oldest_hash)

        self._exact_cache[q_hash] = entry
        for token in entry.vector.keys():
            self._inverted_index.setdefault(token, set()).add(q_hash)

    async def set(
        self,
        query: str,
        response: str,
        cost_saved: float = 0.0,
        ttl_seconds: float | None = None,
    ) -> None:
        if not query.strip() or not response.strip():
            return

        now = time.time()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = (now + ttl) if ttl > 0 else None

        q_hash = self._hash_query(query)
        tokens = _tokenize(query)
        vector = _compute_vector(tokens)

        entry = CacheEntry(
            query=query,
            response=response,
            cost_saved=cost_saved,
            created_at=now,
            expires_at=expires_at,
            vector=vector,
        )

        self._insert_l1(q_hash, entry)

        if self._l2_backend:
            await self._l2_backend.set_exact(q_hash, entry)
