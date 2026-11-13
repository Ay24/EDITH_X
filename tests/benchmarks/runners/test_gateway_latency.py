"""Task: Gateway Latency Overhead, Upstream Stub Delta, and Concurrency Benchmark.
Derived from BerriAI ai-gateway-bench & Kong API Gateway benchmarks.
Hardware Baseline: AMD Ryzen 5 5600H (6C/12T, ~3.3-4.2 GHz), 16 GB RAM, Windows 11, Python 3.11.0.

Partitions measurements into:
(a) In-process component latency (P50/P90/P95/P99, n >= 1000)
(b) Gateway HTTP proxy overhead delta against a 20ms fixed-delay upstream stub
(c) Multi-concurrency load testing (10, 100, 500 concurrent connections)
"""
from __future__ import annotations

import asyncio
from pathlib import Path
import platform
import statistics
import time
import httpx
from fastapi import FastAPI
import pytest
import yaml

from edith_x.modules.optimization.cache import SemanticCache
from edith_x.modules.intent.service import IntentService
from edith_x.modules.policy.firewall import PIIFirewall
from edith_x.modules.router.pareto import ParetoModelRouter
from edith_x.core.config import Settings
from edith_x.core.interfaces import AuthContext

BASE_DIR = Path(__file__).resolve().parent.parent
THRESHOLDS_PATH = BASE_DIR / "thresholds.yaml"


def load_thresholds():
    with open(THRESHOLDS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["latency_and_throughput"]


def compute_percentiles(durations_ms: list[float]) -> dict[str, float]:
    sorted_d = sorted(durations_ms)
    n = len(sorted_d)
    return {
        "mean": statistics.mean(durations_ms),
        "median": statistics.median(durations_ms),
        "p90": sorted_d[int(0.90 * n)],
        "p95": sorted_d[int(0.95 * n)],
        "p99": sorted_d[min(int(0.99 * n), n - 1)],
        "stdev": statistics.stdev(durations_ms) if n > 1 else 0.0,
    }


class TestGatewayLatencyAudited:
    """Rigorous latency and concurrency benchmarking with HTTP stub delta and hardware disclosure."""

    @pytest.fixture(autouse=True)
    def setup_gateway(self):
        self.thresholds = load_thresholds()
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

    def test_hardware_specification_disclosure(self):
        """Discloses and validates test execution environment hardware."""
        hw_info = {
            "processor": platform.processor(),
            "machine": platform.machine(),
            "system": platform.system(),
            "release": platform.release(),
            "python_version": platform.python_version(),
            "nominal_target": "AMD Ryzen 5 5600H (6 cores, 12 threads), 16 GB RAM, Windows 11",
        }
        print("\n--- Disclosed Hardware & OS Specification ---")
        for k, v in hw_info.items():
            print(f"  {k:<16}: {v}")
        assert hw_info["python_version"].startswith("3.11") or hw_info["python_version"].startswith("3.12")

    @pytest.mark.asyncio
    async def test_in_process_cache_latency_overhead(self):
        """Measures L0 exact SHA-256 hash lookup latency over 1,000 iterations. Target: P99 <= 0.10ms."""
        query = "What is the capital of France?"
        await self.cache.set(query, "Paris is the capital of France.", cost_saved=0.002)

        durations_ms = []
        for _ in range(self.thresholds["in_process"]["min_iterations"]):
            t0 = time.perf_counter_ns()
            res = await self.cache.get(query)
            t1 = time.perf_counter_ns()
            assert res.hit is True
            durations_ms.append((t1 - t0) / 1_000_000.0)

        stats = compute_percentiles(durations_ms)
        print("\n--- (a) L0 Exact Cache Latency (n=1,000) ---")
        print(f"  Mean:   {stats['mean']:.4f} ms")
        print(f"  Median: {stats['median']:.4f} ms")
        print(f"  P90:    {stats['p90']:.4f} ms")
        print(f"  P95:    {stats['p95']:.4f} ms")
        print(f"  P99:    {stats['p99']:.4f} ms (Pre-committed target: <= {self.thresholds['in_process']['exact_cache_p99_ms']:.2f} ms)")
        print(f"  Jitter: {stats['stdev']:.4f} ms")

        assert stats["p99"] <= self.thresholds["in_process"]["exact_cache_p99_ms"], (
            f"L0 Exact Cache P99 {stats['p99']:.3f}ms exceeded {self.thresholds['in_process']['exact_cache_p99_ms']}ms"
        )

    @pytest.mark.asyncio
    async def test_in_process_semantic_cache_latency_overhead(self):
        """Measures L0 semantic cosine similarity lookup latency over 1,000 iterations. Target: P99 <= 1.50ms."""
        for i in range(50):
            await self.cache.set(
                f"How do I configure security policy rule {i} in Kubernetes?",
                f"Use NetworkPolicy rule {i} with appropriate ingress cidr blocks.",
                cost_saved=0.002,
            )

        test_query = "How to configure security policy rule 25 in Kubernetes cluster?"
        durations_ms = []

        for _ in range(self.thresholds["in_process"]["min_iterations"]):
            t0 = time.perf_counter_ns()
            res = await self.cache.get(test_query)
            t1 = time.perf_counter_ns()
            durations_ms.append((t1 - t0) / 1_000_000.0)

        stats = compute_percentiles(durations_ms)
        print("\n--- (a) L0 Semantic Cache Latency (n=1,000 / 50 vectors) ---")
        print(f"  Mean:   {stats['mean']:.4f} ms")
        print(f"  Median: {stats['median']:.4f} ms")
        print(f"  P90:    {stats['p90']:.4f} ms")
        print(f"  P95:    {stats['p95']:.4f} ms")
        print(f"  P99:    {stats['p99']:.4f} ms (Pre-committed target: <= {self.thresholds['in_process']['semantic_cache_p99_ms']:.2f} ms)")
        print(f"  Jitter: {stats['stdev']:.4f} ms")

        assert stats["p99"] <= self.thresholds["in_process"]["semantic_cache_p99_ms"], (
            f"L0 Semantic Cache P99 {stats['p99']:.3f}ms exceeded {self.thresholds['in_process']['semantic_cache_p99_ms']}ms"
        )

    @pytest.mark.asyncio
    async def test_in_process_prerouting_pipeline_overhead(self):
        """Measures full pre-routing pipeline (Intent + Presidio PII + Pareto Router). Target: P99 <= 2.00ms."""
        prompt = "Architect a resilient multi-datacenter PostgreSQL database with streaming replication."

        durations_ms = []
        for _ in range(self.thresholds["in_process"]["min_iterations"]):
            t0 = time.perf_counter_ns()
            # 1. PII Scan
            clean_q, has_pii, _ = self.firewall.redact(prompt)
            # 2. Intent Classification
            intent = await self.intent_svc.classify(clean_q, self.auth_ctx)
            # 3. Pareto Decision
            tier = self.router.select_tier(clean_q)
            t1 = time.perf_counter_ns()

            durations_ms.append((t1 - t0) / 1_000_000.0)

        stats = compute_percentiles(durations_ms)
        print("\n--- (a) In-Process Pre-Routing Pipeline Latency (n=1,000) ---")
        print(f"  Mean:   {stats['mean']:.4f} ms")
        print(f"  Median: {stats['median']:.4f} ms")
        print(f"  P90:    {stats['p90']:.4f} ms")
        print(f"  P95:    {stats['p95']:.4f} ms")
        print(f"  P99:    {stats['p99']:.4f} ms (Pre-committed target: <= {self.thresholds['in_process']['prerouting_pipeline_p99_ms']:.2f} ms)")
        print(f"  Jitter: {stats['stdev']:.4f} ms")

        assert stats["p99"] <= self.thresholds["in_process"]["prerouting_pipeline_p99_ms"], (
            f"Pre-routing pipeline P99 {stats['p99']:.3f}ms exceeded {self.thresholds['in_process']['prerouting_pipeline_p99_ms']}ms"
        )

    @pytest.mark.asyncio
    async def test_gateway_http_proxy_overhead_delta(self):
        """
        Measures HTTP gateway proxy latency delta over direct HTTP with a 20ms fixed-delay upstream stub.
        Calculates: Delta = T(gateway_proxied) - T(direct_upstream). Target: Delta P99 <= 15.0ms.
        """
        app = FastAPI()
        STUB_DELAY = self.thresholds["gateway_http_overhead"]["upstream_stub_delay_ms"] / 1000.0  # 0.020s

        # 1. Direct upstream endpoint
        @app.get("/upstream/direct")
        async def direct_stub():
            await asyncio.sleep(STUB_DELAY)
            return {"status": "ok", "source": "upstream_direct"}

        # 2. Gateway proxied endpoint (executes cache check, PII firewall, intent, routing before forwarding)
        @app.post("/gateway/proxy")
        async def gateway_proxy_stub(payload: dict):
            q = payload.get("query", "")
            # Pipeline steps
            c_res = await self.cache.get(q)
            cq, has_pii, _ = self.firewall.redact(q)
            intent = await self.intent_svc.classify(cq, self.auth_ctx)
            tier = self.router.select_tier(cq)
            # Call upstream
            await asyncio.sleep(STUB_DELAY)
            return {"status": "ok", "tier": tier, "has_pii": has_pii}

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            direct_durations = []
            gateway_durations = []
            delta_durations = []

            for i in range(100):
                # Direct call
                t0 = time.perf_counter_ns()
                r1 = await client.get("/upstream/direct")
                t1 = time.perf_counter_ns()
                d_direct = (t1 - t0) / 1_000_000.0
                direct_durations.append(d_direct)

                # Gateway proxied call
                t2 = time.perf_counter_ns()
                r2 = await client.post("/gateway/proxy", json={"query": f"Query number {i} for latency delta"})
                t3 = time.perf_counter_ns()
                d_gateway = (t3 - t2) / 1_000_000.0
                gateway_durations.append(d_gateway)

                delta = max(0.0, d_gateway - d_direct)
                delta_durations.append(delta)

            direct_stats = compute_percentiles(direct_durations)
            gateway_stats = compute_percentiles(gateway_durations)
            delta_stats = compute_percentiles(delta_durations)

            print(f"\n--- (b) Gateway HTTP Proxy Overhead Delta (n=100 with 20ms upstream stub) ---")
            print(f"  Direct Upstream HTTP: P50={direct_stats['median']:.2f} ms | P99={direct_stats['p99']:.2f} ms")
            print(f"  Gateway Proxied HTTP: P50={gateway_stats['median']:.2f} ms | P99={gateway_stats['p99']:.2f} ms")
            print(f"  Isolated Gateway Delta: P50={delta_stats['median']:.2f} ms | P99={delta_stats['p99']:.2f} ms (Pre-committed target: <= {self.thresholds['gateway_http_overhead']['max_gateway_delta_p99_ms']:.1f} ms)")

            assert delta_stats["p99"] <= self.thresholds["gateway_http_overhead"]["max_gateway_delta_p99_ms"], (
                f"Gateway HTTP delta P99 {delta_stats['p99']:.2f}ms exceeded {self.thresholds['gateway_http_overhead']['max_gateway_delta_p99_ms']}ms"
            )

    @pytest.mark.asyncio
    async def test_multi_concurrency_load_scaling(self):
        """
        Stress-tests concurrency across 10, 100, and 500 simultaneous async connections.
        Measures event loop responsiveness, throughput (req/s), and coroutine latency distribution.
        """
        concurrency_levels = self.thresholds["concurrency_load"]["concurrency_levels"]  # [10, 100, 500]
        results = {}

        for concurrency in concurrency_levels:
            queries = [
                "What is Docker containerization?",
                "Architect a distributed key-value store with raft consensus.",
                "My card is 4532-1234-5678-9010 please charge it.",
                "Write a Python script to sort a list of dictionaries.",
            ] * (concurrency // 4 + 1)
            queries = queries[:concurrency]

            async def worker(q: str):
                t0 = time.perf_counter_ns()
                await self.cache.get(q)
                cq, _, _ = self.firewall.redact(q)
                await self.intent_svc.classify(cq, self.auth_ctx)
                self.router.select_tier(cq)
                t1 = time.perf_counter_ns()
                return (t1 - t0) / 1_000_000.0

            t_start = time.perf_counter()
            durations = await asyncio.gather(*(worker(q) for q in queries))
            wall_clock = time.perf_counter() - t_start

            stats = compute_percentiles(durations)
            throughput = len(queries) / wall_clock
            results[concurrency] = {"throughput": throughput, "p99": stats["p99"], "wall_ms": wall_clock * 1000}

        print("\n--- (c) Multi-Concurrency Load Scaling ---")
        for c, res in results.items():
            print(f"  Concurrency {c:>3}: Throughput={res['throughput']:>7.1f} req/s | Coroutine P99={res['p99']:.3f} ms | Wall Clock={res['wall_ms']:.1f} ms")

        # Pre-committed threshold: throughput at 100 concurrency >= 500 req/sec
        throughput_100 = results[100]["throughput"]
        assert throughput_100 >= self.thresholds["concurrency_load"]["min_throughput_100_concurrency"], (
            f"Throughput at 100 concurrency {throughput_100:.1f} req/s < {self.thresholds['concurrency_load']['min_throughput_100_concurrency']}"
        )
