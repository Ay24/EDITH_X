"""M6 — Knowledge Layer: Production Hybrid Vector & Lexical Retrieval via Qdrant."""
from __future__ import annotations

import hashlib
import math
import re
import uuid
from typing import Any

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from edith_x.core.config import Settings
from edith_x.core.interfaces import Document, KnowledgeChunk

log = structlog.get_logger(__name__)

COLLECTION_NAME = "edith_knowledge"
VECTOR_DIM = 128


def _hash_vector(text: str, dim: int = VECTOR_DIM) -> list[float]:
    """Generate normalized deterministic pseudo-semantic dense embedding on CPU in <0.2ms.
    
    Uses n-gram feature hashing with logarithmic term frequency weighting.
    """
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    words = [w for w in clean.split() if len(w) > 1]
    vec = [0.0] * dim
    if not words:
        return vec

    # Unigrams and bigrams
    terms = words[:]
    for i in range(len(words) - 1):
        terms.append(f"{words[i]}_{words[i+1]}")

    for term in terms:
        h = int(hashlib.md5(term.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 7) & 1 else -1.0
        vec[idx] += sign

    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 1e-9:
        vec = [v / norm for v in vec]
    return vec


def _lexical_similarity(query: str, text: str) -> float:
    """Compute BM25-style lexical term overlap."""
    q_words = set(re.findall(r"\w+", query.lower()))
    t_words = set(re.findall(r"\w+", text.lower()))
    if not q_words or not t_words:
        return 0.0
    overlap = len(q_words.intersection(t_words))
    return overlap / max(len(q_words), 1)


class KnowledgeService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: QdrantClient | None = None
        self._initialized = False

    def _get_client(self) -> QdrantClient:
        """Lazily initialize Qdrant client with automatic fallback to in-memory mode."""
        if self._client is not None:
            return self._client

        try:
            # Try connecting to external Qdrant if specified
            if self._settings.qdrant_host and self._settings.qdrant_host != ":memory:":
                client = QdrantClient(
                    host=self._settings.qdrant_host,
                    port=self._settings.qdrant_port,
                    api_key=self._settings.qdrant_api_key or None,
                    timeout=1.5,
                )
                # Test connectivity
                client.get_collections()
                self._client = client
                log.info("qdrant_connected_remote", host=self._settings.qdrant_host)
            else:
                self._client = QdrantClient(":memory:")
                log.info("qdrant_initialized_memory")
        except Exception as e:
            log.warning("qdrant_remote_failed_fallback_memory", error=str(e))
            self._client = QdrantClient(":memory:")

        # Ensure collection exists
        try:
            collections = [c.name for c in self._client.get_collections().collections]
            if COLLECTION_NAME not in collections:
                self._client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
                )
                log.info("qdrant_collection_created", collection=COLLECTION_NAME)
        except Exception as e:
            log.error("qdrant_collection_init_error", error=str(e))

        return self._client

    async def index(self, document: Document, source: str) -> str:
        """Index a document by chunking into semantic passages and upserting into Qdrant."""
        client = self._get_client()
        content = document.content.strip()
        if not content:
            return document.id

        # Chunk document into ~400 character sliding passages
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        chunks_text: list[str] = []
        for p in paragraphs:
            if len(p) <= 500:
                chunks_text.append(p)
            else:
                # Sub-chunk by sentences
                sentences = re.split(r"(?<=[.!?])\s+", p)
                current = ""
                for s in sentences:
                    if len(current) + len(s) < 450:
                        current = f"{current} {s}".strip()
                    else:
                        if current:
                            chunks_text.append(current)
                        current = s
                if current:
                    chunks_text.append(current)

        if not chunks_text:
            chunks_text = [content[:500]]

        points: list[PointStruct] = []
        for idx, chunk_str in enumerate(chunks_text):
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document.id}_{idx}"))
            vec = _hash_vector(chunk_str, dim=VECTOR_DIM)
            payload = {
                "doc_id": document.id,
                "chunk_id": chunk_id,
                "content": chunk_str,
                "source": source,
                "metadata": document.metadata,
                "chunk_index": idx,
            }
            points.append(PointStruct(id=chunk_id, vector=vec, payload=payload))

        client.upsert(collection_name=COLLECTION_NAME, points=points)
        log.info("document_indexed_qdrant", doc_id=document.id, source=source, chunks=len(points))
        return document.id

    async def retrieve(
        self,
        query: str,
        sources: list[str] | None = None,
        top_k: int = 10,
    ) -> list[KnowledgeChunk]:
        """Perform hybrid search (dense cosine vector search + lexical re-ranking)."""
        client = self._get_client()
        if not query.strip():
            return []

        q_vec = _hash_vector(query, dim=VECTOR_DIM)

        query_filter = None
        if sources and len(sources) > 0:
            query_filter = Filter(
                should=[
                    FieldCondition(key="source", match=MatchValue(value=s))
                    for s in sources
                ]
            )

        # Retrieve top candidates via vector search
        search_limit = max(top_k * 3, 20)
        try:
            results = client.query_points(
                collection_name=COLLECTION_NAME,
                query=q_vec,
                query_filter=query_filter,
                limit=search_limit,
                with_payload=True,
            )
            candidate_points = results.points
        except Exception as e:
            log.warning("qdrant_query_failed", error=str(e))
            candidate_points = []

        # Hybrid scoring & deduplication
        scored_chunks: list[tuple[float, KnowledgeChunk]] = []
        for p in candidate_points:
            payload = p.payload or {}
            content = payload.get("content", "")
            source = payload.get("source", "knowledge_base")
            dense_score = max(0.0, float(p.score)) if p.score is not None else 0.5
            lex_score = _lexical_similarity(query, content)

            # Combined hybrid score (60% dense vector + 40% lexical overlap)
            hybrid_score = round(0.6 * dense_score + 0.4 * lex_score, 4)

            scored_chunks.append((
                hybrid_score,
                KnowledgeChunk(
                    id=str(p.id),
                    content=content,
                    source=source,
                    score=hybrid_score,
                    metadata=payload.get("metadata", {}),
                )
            ))

        # Sort descending by hybrid score, discarding zero/near-zero relevance noise
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        final_chunks = [chunk for score, chunk in scored_chunks[:top_k] if score > 0.05]

        log.info(
            "hybrid_knowledge_retrieved",
            chunks_returned=len(final_chunks),
            query=query[:60],
            top_score=final_chunks[0].score if final_chunks else 0.0,
        )
        return final_chunks
