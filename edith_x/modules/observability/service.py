"""M14 — Observability: Records pipeline events, cost, latency, cache metrics."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any

import structlog

from edith_x.core.config import Settings
from edith_x.core.interfaces import MetricsSummary, PipelineEvent

log = structlog.get_logger(__name__)


class ObservabilityService:
    """In-memory observability for Phase 0. Phase 5: Prometheus + Grafana."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # Ring buffer: last 1000 events
        self._events: deque[PipelineEvent] = deque(maxlen=1000)
        self._total_saved: float = 0.0
        self._total_cost: float = 0.0

    async def record(self, event: PipelineEvent) -> None:
        self._events.append(event)
        self._total_saved += event.cost_saved_usd
        self._total_cost += event.cost_usd
        log.info(
            "pipeline_event",
            run_id=event.run_id,
            model=event.model_selected,
            layer=event.layer,
            cache_hit=event.cache_hit,
            cost_usd=event.cost_usd,
            cost_saved=event.cost_saved_usd,
            latency_ms=event.latency_ms,
        )

    async def get_metrics(self, org_id: str, window: str = "24h") -> MetricsSummary:
        events = list(self._events)
        org_events = [e for e in events if e.org_id == org_id] if org_id else events

        if not org_events:
            return MetricsSummary()

        total = len(org_events)
        cache_hits = sum(1 for e in org_events if e.cache_hit)
        total_cost = sum(e.cost_usd for e in org_events)
        total_saved = sum(e.cost_saved_usd for e in org_events)
        avg_latency = sum(e.latency_ms for e in org_events) / total

        model_dist: dict[str, int] = defaultdict(int)
        layer_dist: dict[str, int] = defaultdict(int)
        for e in org_events:
            model_dist[e.model_selected] += 1
            layer_dist[e.layer] += 1

        return MetricsSummary(
            total_requests=total,
            cache_hit_rate=cache_hits / total,
            avg_cost_usd=total_cost / total,
            total_cost_usd=total_cost,
            total_saved_usd=total_saved,
            avg_latency_ms=avg_latency,
            model_distribution=dict(model_dist),
            layer_distribution=dict(layer_dist),
        )

    def get_recent_events(self, n: int = 50) -> list[PipelineEvent]:
        events = list(self._events)
        return events[-n:]

    def get_cumulative_savings(self) -> float:
        return self._total_saved

    def get_cumulative_cost(self) -> float:
        return self._total_cost
