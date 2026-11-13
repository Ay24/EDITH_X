"""Task 4: AI Gateway Latency Overhead & Jitter Benchmark.
Derived from BerriAI ai-gateway-bench & Kong API Gateway benchmarks.
"""
from __future__ import annotations

import asyncio
import statistics
import time
import pytest

from edith_x.modules.optimization.cache import SemanticCache
from edith_x.modules.intent.service import IntentService
from edith_x.modules.policy.firewall import PIIFirewall
from edith_x.modules.router.pareto import ParetoModelRouter
from edith_x.core.config import Settings
from edith_x.core.interfaces import AuthContext, Context, IntentResult, PolicyDecision


def compute_percentiles(durations_ms: list[float]) -> dict[str, float]:
    sorted_d = sorted(durations_ms)
    n = len(sorted_d)
    return {
        "mean": statistics.mean(durations_ms),
        "median": statistics.median(durations_ms),
        "p90": sorted_d[int(0.90 * n)],
        "p95": sorted_d[int(0.95 * n)],
        "p99": sorted_d[int(0.99 * n)],
        "stdev": statistics.stdev(durations_ms) if n > 1 else 0.0,
    }


class TestGatewayLatency:
    """Measures pure internal EDITH-X gateway latency overhead, independent of remote LLM provider."""

    @pytest.fixture(autouse=True)
    def setup_gateway(self):
        self.cache = SemanticCache(similarity_threshold=0.85)
        self.firewall = PIIFirewall()
        self.router = ParetoModelRouter()
        self.settings = Settings()
        self.intent_svc = IntentService(self.settings)
        self.auth_ctx = AuthContext(
            user_id="bench_user",
            org_id="bench_org",
            email="bench@enterprise.local",
            role="admin",
            api_key_id="bench_key_01",
        )

    @pytest.mark.asyncio
    async def test_exact_cache_latency_overhead(self):
        """Measures L0 exact SHA-256 hash lookup latency over 1,000 iterations. Target: P99 < 1.0ms."""
        query = "What is the capital of France?"
        await self.cache.set(query, "Paris is the capital of France.", cost_saved=0.002)

        durations_ms = []
        # 1,000 warm iterations
        for _ in range(1000):
            t0 = time.perf_counter_ns()
            res = await self.cache.get(query)
            t1 = time.perf_counter_ns()
            assert res.hit is True
            durations_ms.append((t1 - t0) / 1_000_000.0)

        stats = compute_percentiles(durations_ms)
        print("\n[L0 Exact Cache Latency Benchmark (1,000 reqs)]")
        print(f"  Mean:   {stats['mean']:.4f} ms")
        print(f"  Median: {stats['median']:.4f} ms")
        print(f"  P90:    {stats['p90']:.4f} ms")
        print(f"  P99:    {stats['p99']:.4f} ms")
        print(f"  Jitter: {stats['stdev']:.4f} ms")

        # Industry standard: Exact match cache overhead must be strictly sub-millisecond
        assert stats["p99"] < 1.0, f"L0 Exact Cache P99 {stats['p99']:.3f}ms exceeded 1.0ms threshold"

    @pytest.mark.asyncio
    async def test_semantic_cache_latency_overhead(self):
        """Measures L0 semantic cosine similarity lookup latency over 500 iterations. Target: P99 < 3.0ms."""
        # Seed cache with 50 diverse items
        for i in range(50):
            await self.cache.set(
                f"How do I configure security policy rule {i} in Kubernetes?",
                f"Use NetworkPolicy rule {i} with appropriate ingress cidr blocks.",
                cost_saved=0.002,
            )

        test_query = "How to configure security policy rule 25 in Kubernetes cluster?"
        durations_ms = []

        for _ in range(500):
            t0 = time.perf_counter_ns()
            res = await self.cache.get(test_query)
            t1 = time.perf_counter_ns()
            durations_ms.append((t1 - t0) / 1_000_000.0)

        stats = compute_percentiles(durations_ms)
        print("\n[L0 Semantic Cache Latency Benchmark (500 reqs / 50 vectors)]")
        print(f"  Mean:   {stats['mean']:.4f} ms")
        print(f"  Median: {stats['median']:.4f} ms")
        print(f"  P90:    {stats['p90']:.4f} ms")
        print(f"  P99:    {stats['p99']:.4f} ms")
        print(f"  Jitter: {stats['stdev']:.4f} ms")

        # In-memory dual-layer vector search must be sub-3ms P99
        assert stats["p99"] < 3.0, f"L0 Semantic Cache P99 {stats['p99']:.3f}ms exceeded 3.0ms threshold"

    @pytest.mark.asyncio
    async def test_prerouting_pipeline_overhead(self):
        """Measures full pre-routing pipeline (Intent + Presidio PII + Pareto Router). Target: P99 < 5.0ms."""
        prompt = "Architect a resilient multi-datacenter PostgreSQL database with streaming replication."

        durations_ms = []
        for _ in range(500):
            t0 = time.perf_counter_ns()
            # 1. PII Scan
            _, has_pii, _ = self.firewall.redact(prompt)
            # 2. Intent Classification
            intent = await self.intent_svc.classify(prompt, self.auth_ctx)
            # 3. Pareto Decision
            tier = self.router.select_tier(prompt)
            t1 = time.perf_counter_ns()

            assert tier in ("L1_local", "L2_compressed", "L3_cloud")
            assert intent is not None
            durations_ms.append((t1 - t0) / 1_000_000.0)

        stats = compute_percentiles(durations_ms)
        print("\n[Full Pre-Routing Pipeline Latency (500 reqs)]")
        print(f"  Mean:   {stats['mean']:.4f} ms")
        print(f"  Median: {stats['median']:.4f} ms")
        print(f"  P90:    {stats['p90']:.4f} ms")
        print(f"  P99:    {stats['p99']:.4f} ms")
        print(f"  Jitter: {stats['stdev']:.4f} ms")

        # Enterprise AI Gateway budget: Internal overhead must add < 5ms before network LLM hop
        assert stats["p99"] < 5.0, f"Pre-routing pipeline P99 {stats['p99']:.3f}ms exceeded 5.0ms threshold"

    @pytest.mark.asyncio
    async def test_concurrent_async_gateway_load(self):
        """Stress-tests async concurrent pipeline execution across 100 simultaneous coroutines."""
        queries = [
            "What is Docker containerization?",
            "Architect a distributed key-value store with raft consensus.",
            "My card is 4532-1234-5678-9010 please charge it.",
            "Write a Python script to sort a list of dictionaries.",
        ] * 25  # 100 queries

        async def worker(q: str):
            t0 = time.perf_counter_ns()
            # 1. Cache probe
            c_res = await self.cache.get(q)
            # 2. PII Firewall
            clean_q, has_pii, _ = self.firewall.redact(q)
            # 3. Intent
            intent = await self.intent_svc.classify(clean_q, self.auth_ctx)
            # 4. Pareto route
            tier = self.router.select_tier(clean_q)
            t1 = time.perf_counter_ns()
            return (t1 - t0) / 1_000_000.0

        t_start = time.perf_counter()
        durations = await asyncio.gather(*(worker(q) for q in queries))
        t_total = time.perf_counter() - t_start

        stats = compute_percentiles(durations)
        throughput = len(queries) / t_total

        print("\n[Concurrent Async Load Test (100 concurrent workers)]")
        print(f"  Total Wall Clock: {t_total * 1000:.2f} ms")
        print(f"  Throughput:       {throughput:.1f} req/sec")
        print(f"  Mean Coroutine:   {stats['mean']:.4f} ms")
        print(f"  P99 Coroutine:    {stats['p99']:.4f} ms")

        assert len(durations) == 100
        assert throughput > 100.0, f"Async throughput {throughput:.1f} req/s fell below 100 req/s"
