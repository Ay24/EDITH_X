"""EDITH-X Dependency Injection Container"""
from __future__ import annotations

from dependency_injector import containers, providers

from edith_x.core.config import Settings, get_settings
from edith_x.modules.context.service import ContextBuilderService
from edith_x.modules.execution.service import ExecutionService
from edith_x.modules.gateway.service import GatewayService
from edith_x.modules.identity.service import IdentityService
from edith_x.modules.intent.service import IntentService
from edith_x.modules.knowledge.service import KnowledgeService
from edith_x.modules.memory.service import MemoryService
from edith_x.modules.observability.service import ObservabilityService
from edith_x.modules.optimization.service import OptimizationService
from edith_x.modules.planner.service import PlannerService
from edith_x.modules.policy.service import PolicyService
from edith_x.modules.reflection.service import ReflectionService
from edith_x.modules.router.service import RouterService
from edith_x.modules.verification.service import VerificationService


class Container(containers.DeclarativeContainer):
    """EDITH-X Dependency Injection Container.
    
    All modules are wired here. No module imports another directly.
    """
    config: providers.Singleton[Settings] = providers.Singleton(get_settings)

    # ── Core Services ────────────────────────────────────────────────────
    observability: providers.Singleton[ObservabilityService] = providers.Singleton(
        ObservabilityService, settings=config
    )

    identity: providers.Singleton[IdentityService] = providers.Singleton(
        IdentityService, settings=config
    )

    gateway: providers.Singleton[GatewayService] = providers.Singleton(
        GatewayService, settings=config, identity=identity
    )

    intent: providers.Singleton[IntentService] = providers.Singleton(
        IntentService, settings=config
    )

    policy: providers.Singleton[PolicyService] = providers.Singleton(
        PolicyService, settings=config
    )

    # ── Knowledge Pipeline ───────────────────────────────────────────────
    knowledge: providers.Singleton[KnowledgeService] = providers.Singleton(
        KnowledgeService, settings=config
    )

    context: providers.Singleton[ContextBuilderService] = providers.Singleton(
        ContextBuilderService, settings=config
    )

    # ── Optimization + Routing ───────────────────────────────────────────
    optimization: providers.Singleton[OptimizationService] = providers.Singleton(
        OptimizationService, settings=config
    )

    router: providers.Singleton[RouterService] = providers.Singleton(
        RouterService, settings=config
    )

    # ── Execution Loop ───────────────────────────────────────────────────
    execution: providers.Singleton[ExecutionService] = providers.Singleton(
        ExecutionService, settings=config
    )

    verification: providers.Singleton[VerificationService] = providers.Singleton(
        VerificationService, settings=config
    )

    reflection: providers.Singleton[ReflectionService] = providers.Singleton(
        ReflectionService, settings=config
    )

    # ── Memory ───────────────────────────────────────────────────────────
    memory: providers.Singleton[MemoryService] = providers.Singleton(
        MemoryService, settings=config
    )

    # ── Planner (depends on all execution services) ──────────────────────
    planner: providers.Singleton[PlannerService] = providers.Singleton(
        PlannerService,
        settings=config,
        knowledge=knowledge,
        context=context,
        optimization=optimization,
        router=router,
        execution=execution,
        verification=verification,
        reflection=reflection,
        memory=memory,
        observability=observability,
    )


# Global container instance
container = Container()
