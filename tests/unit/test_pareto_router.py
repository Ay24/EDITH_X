import pytest
from edith_x.modules.router.pareto import ParetoModelRouter

def test_pareto_router_simple_query():
    router = ParetoModelRouter(threshold_cheap=0.50, threshold_medium=0.25)
    # Simple query should assign high cheap probability
    prob = router.predict_cheap_capability("What is the difference between list and tuple in python?")
    assert prob >= 0.50
    tier = router.select_tier("What is the difference between list and tuple in python?")
    assert tier == "L1_local"

def test_pareto_router_complex_query():
    router = ParetoModelRouter(threshold_cheap=0.50, threshold_medium=0.25)
    complex_query = (
        "Design a distributed consensus protocol with raft election algorithms, "
        "handling network partitions across 5 geo-replicated data centers with Byzantine fault tolerance. "
        "Provide mathematical formal proofs and step-by-step edge case state transitions in LaTeX."
    )
    prob = router.predict_cheap_capability(complex_query)
    assert prob < 0.25
    tier = router.select_tier(complex_query)
    assert tier == "L3_cloud"

def test_pareto_router_medium_query():
    router = ParetoModelRouter(threshold_cheap=0.50, threshold_medium=0.25)
    medium_query = "Write a python FastAPI endpoint to parse and validate incoming webhook headers"
    prob = router.predict_cheap_capability(medium_query)
    assert 0.25 <= prob <= 0.65
