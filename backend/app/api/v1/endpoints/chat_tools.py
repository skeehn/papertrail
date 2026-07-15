"""Tool endpoints for the streaming chat.

These are the "harness" the chat model drives itself: semantic search over the
indexed papers, and on-demand arXiv indexing. Deliberately thin and
single-purpose — one retrieval path shared by every model, instead of the
per-agent retrieval that used to be duplicated across four agent classes.
"""

import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.database import (
    NEO4J_CONNECTED,
    neo4j_client,
    store_entities,
    store_paper,
    store_relationships,
)
from app.services.arxiv_client import arxiv_client
from app.services.pinecone_store import pinecone_store

router = APIRouter()
logger = get_logger("chat_tools")


class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    limit: int = Field(default=6, ge=1, le=20)


class IndexRequest(BaseModel):
    id_or_url: str = Field(..., description="arXiv id or any arXiv URL")


def _keyword_fallback(query: str, limit: int) -> List[Dict[str, Any]]:
    """Keyword-rank papers in Neo4j when vector search returns nothing."""
    if not NEO4J_CONNECTED:
        return []
    words = [w.lower() for w in query.split() if len(w) > 3]
    try:
        with neo4j_client.get_session() as session:
            if words:
                result = session.run(
                    """
                    MATCH (p:Paper)
                    WITH p, toLower(coalesce(p.title,'') + ' ' + coalesce(p.abstract,'')) AS hay
                    WITH p, size([w IN $words WHERE hay CONTAINS w]) AS score
                    WHERE score > 0
                    RETURN p.arxiv_id AS arxiv_id, p.title AS title,
                           p.abstract AS abstract, p.authors AS authors
                    ORDER BY score DESC LIMIT $limit
                    """,
                    words=words,
                    limit=limit,
                )
                rows = [dict(r) for r in result]
                if rows:
                    return rows
            result = session.run(
                """
                MATCH (p:Paper)
                RETURN p.arxiv_id AS arxiv_id, p.title AS title,
                       p.abstract AS abstract, p.authors AS authors
                ORDER BY p.created_at DESC LIMIT $limit
                """,
                limit=limit,
            )
            return [dict(r) for r in result]
    except Exception as e:  # noqa: BLE001
        logger.warning("Keyword fallback failed", error=str(e))
        return []


@router.post("/search-papers")
async def search_papers(request: SearchRequest) -> Dict[str, Any]:
    """Semantic search over indexed papers (vector, with keyword fallback)."""
    papers: List[Dict[str, Any]] = []
    try:
        hits = await pinecone_store.search(
            query_text=request.query, top_k=request.limit
        )
        for h in hits:
            md = h.get("metadata", {}) or {}
            papers.append(
                {
                    "arxiv_id": md.get("arxiv_id") or h.get("id", ""),
                    "title": md.get("title", ""),
                    "abstract": (md.get("abstract") or "")[:1200],
                    "authors": md.get("authors", ""),
                    "score": round(float(h.get("score") or 0), 4),
                }
            )
    except Exception as e:  # noqa: BLE001
        logger.warning("Vector search failed", error=str(e))

    if not papers:
        papers = _keyword_fallback(request.query, request.limit)

    logger.info("chat search-papers", query=request.query, results=len(papers))
    return {"papers": papers[: request.limit], "count": len(papers[: request.limit])}


@router.post("/index-arxiv")
async def index_arxiv(request: IndexRequest) -> Dict[str, Any]:
    """Index a single arXiv paper by id or URL: Neo4j + Pinecone + entities."""
    token = request.id_or_url.strip()
    m = re.search(r"(\d{4}\.\d{4,5}(v\d+)?)", token)
    arxiv_id = m.group(1) if m else token.rstrip("/").split("/")[-1]

    paper = arxiv_client.get_paper_by_id(arxiv_id)
    if not paper:
        return {"ok": False, "error": f"Paper {arxiv_id} not found on arXiv"}

    aid = paper.get("arxiv_id", arxiv_id)
    title = (paper.get("title") or "").strip()
    abstract = (paper.get("abstract") or "").strip()

    store_paper(
        {
            "arxiv_id": aid,
            "title": title,
            "abstract": abstract,
            "authors": paper.get("authors", []),
            "publication_date": paper.get("published_date"),
            "doi": paper.get("doi"),
            "categories": paper.get("categories", []),
            "pdf_url": paper.get("pdf_url"),
        }
    )

    if pinecone_store.is_connected:
        await pinecone_store.add_documents(
            [
                {
                    "id": f"paper_{aid}",
                    "text": f"{title}. {abstract}",
                    "metadata": {
                        "arxiv_id": aid,
                        "title": title,
                        "abstract": abstract,
                        "authors": paper.get("authors", []),
                    },
                }
            ]
        )

    n_entities = 0
    try:
        from app.services.entity_extractor import EntityExtractor

        ex = EntityExtractor()
        ents, rels = await ex.extract_entities_and_relationships(f"{title}. {abstract}")
        store_entities(
            aid,
            [
                {"name": e.name, "type": e.type.value, "confidence": e.confidence}
                for e in ents
            ],
        )
        store_relationships(
            aid,
            [
                {
                    "source": r.source,
                    "target": r.target,
                    "type": r.type.value if hasattr(r.type, "value") else str(r.type),
                    "confidence": r.confidence,
                }
                for r in rels
            ],
        )
        n_entities = len(ents)
    except Exception as e:  # noqa: BLE001
        logger.warning("Entity extraction skipped", error=str(e))

    logger.info("chat index-arxiv", arxiv_id=aid, entities=n_entities)
    return {
        "ok": True,
        "arxiv_id": aid,
        "title": title,
        "authors": paper.get("authors", [])[:5],
        "entities_extracted": n_entities,
    }
