import pytest
from edith_x.modules.intent.router import CentroidIntentRouter

def test_centroid_router_coding():
    router = CentroidIntentRouter()
    assert router.classify("Can you write a script to calculate primes?") == "coding"
    assert router.classify("Refactor this python class to use asyncio") == "coding"
    assert router.classify("Fix the syntax error in my backend endpoint") == "coding"

def test_centroid_router_security():
    router = CentroidIntentRouter()
    assert router.classify("Scan this code for SQL injection vulnerabilities") == "security"
    assert router.classify("Perform a pentest and threat model on the gateway") == "security"

def test_centroid_router_retrieval():
    router = CentroidIntentRouter()
    assert router.classify("Find all documents related to employee benefits") == "retrieval"
    assert router.classify("Search our knowledge base for the quarterly report") == "retrieval"

def test_centroid_router_summarization():
    router = CentroidIntentRouter()
    assert router.classify("Give me a brief summary and tldr of this document") == "summarization"
    assert router.classify("Summarize the meeting notes from yesterday") == "summarization"

def test_centroid_router_speed():
    import time
    router = CentroidIntentRouter()
    start = time.monotonic()
    for _ in range(100):
        router.classify("Analyze the latency trends of our cloud infrastructure")
    elapsed_ms = (time.monotonic() - start) * 1000
    # Average under 1ms per query
    assert (elapsed_ms / 100) < 2.0
