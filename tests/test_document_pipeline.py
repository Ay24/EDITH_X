"""Tests for M15 Document Pipeline (Parsing, Chunking, PII Redaction, Map-Reduce Summaries)."""
import pytest
from edith_x.modules.document.pipeline import DocumentPipeline, ParsedDocument
from edith_x.modules.optimization.cache import SemanticCache


@pytest.mark.asyncio
async def test_document_parsing_and_sha256():
    pipeline = DocumentPipeline()
    sample_text = b"Quarterly Operating Review\nRevenue exceeded expectations by 15%."
    parsed = pipeline.parse_document(sample_text, filename="review.txt")

    assert parsed.filename == "review.txt"
    assert "Quarterly Operating Review" in parsed.content
    assert parsed.sha256 is not None
    assert len(parsed.sha256) == 64


@pytest.mark.asyncio
async def test_document_per_chunk_pii_redaction():
    pipeline = DocumentPipeline()
    # Content with sensitive card and Aadhaar
    sensitive_text = (
        b"CONFIDENTIAL AUDIT NOTE\n"
        b"Customer payment method: 4532 0150 1234 5678.\n"
        b"Identity record: Aadhaar 9999 4105 7036.\n"
        b"Please verify accounts payable balance."
    )
    parsed = pipeline.parse_document(sensitive_text, filename="audit_note.txt")
    chunks = pipeline.chunk_and_redact(parsed)

    assert len(chunks) >= 1
    for chunk in chunks:
        assert "4532 0150 1234 5678" not in chunk.content
        assert "[REDACTED_CREDIT_CARD]" in chunk.content
        assert "9999 4105 7036" not in chunk.content
        assert "[REDACTED_AADHAAR]" in chunk.content
        assert chunk.has_pii is True


@pytest.mark.asyncio
async def test_document_map_reduce_summary_and_caching():
    cache = SemanticCache()
    pipeline = DocumentPipeline(cache=cache)

    long_text = (
        "Section 1: Enterprise Infrastructure\n"
        "The distributed gateway operates across 3 availability zones with automated failover.\n\n"
        "Section 2: Security Controls\n"
        "Zero-trust authentication enforces constant-time HMAC verification on all API keys.\n\n"
        "Section 3: Cost Optimization\n"
        "Semantic caching and Pareto routing reduce blended cloud token consumption by 54%."
    ).encode("utf-8")

    parsed = pipeline.parse_document(long_text, filename="whitepaper.txt")

    # Initial summary generation
    summary_1 = await pipeline.summarize_document(
        parsed,
        org_id="org_secops",
        prompt="Summarize core security and cost highlights",
    )

    assert summary_1.summary is not None
    assert len(summary_1.summary) > 20
    assert summary_1.cache_hit is False

    # Second summary with identical file hash and prompt must hit the cache ($0 cost)
    summary_2 = await pipeline.summarize_document(
        parsed,
        org_id="org_secops",
        prompt="Summarize core security and cost highlights",
    )

    assert summary_2.cache_hit is True
    assert summary_2.summary == summary_1.summary
    assert summary_2.cost_usd == 0.0
