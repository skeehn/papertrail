"""
Web search API endpoints for academic paper discovery
"""

from typing import List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.models.schemas import SearchRequest, SearchResponse
from app.services.web_search import web_search_service

router = APIRouter()
logger = get_logger("web_search_api")


@router.post("/search", response_model=SearchResponse)
async def search_papers(
    query: str = Query(..., description="Search query for academic papers"),
    sources: Optional[List[str]] = Query(
        default=None, description="Sources to search: arxiv, pubmed, semantic_scholar"
    ),
    max_results: int = Query(
        default=20, ge=1, le=100, description="Maximum number of results to return"
    ),
):
    """
    Search for academic papers across multiple sources

    Supported sources:
    - arxiv: arXiv preprint repository
    - pubmed: PubMed biomedical literature
    - semantic_scholar: Semantic Scholar academic search
    """
    try:
        logger.info(
            "Starting paper search",
            query=query,
            sources=sources,
            max_results=max_results,
        )

        # Validate sources
        valid_sources = {"arxiv", "pubmed", "semantic_scholar"}
        if sources:
            invalid_sources = set(sources) - valid_sources
            if invalid_sources:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid sources: {list(invalid_sources)}. Valid sources: {list(valid_sources)}",
                )

        # Perform search
        results = await web_search_service.search(
            query=query, max_results=max_results, sources=sources
        )

        logger.info("Paper search completed", query=query, results_count=len(results))

        return SearchResponse(results=results, total=len(results), query=query)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Paper search failed", error=str(e), query=query)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/search/sources")
async def get_available_sources():
    """Get list of available search sources"""
    return {
        "sources": [
            {
                "id": "arxiv",
                "name": "arXiv",
                "description": "Preprint repository covering physics, mathematics, computer science, and more",
                "url": "https://arxiv.org",
            },
            {
                "id": "pubmed",
                "name": "PubMed",
                "description": "Biomedical and life science literature database",
                "url": "https://pubmed.ncbi.nlm.nih.gov",
            },
            {
                "id": "semantic_scholar",
                "name": "Semantic Scholar",
                "description": "Academic search engine with AI-powered paper recommendations",
                "url": "https://www.semanticscholar.org",
            },
        ]
    }


@router.get("/search/trending")
async def get_trending_papers(
    field: Optional[str] = Query(default=None, description="Research field filter"),
    days: int = Query(
        default=7, ge=1, le=30, description="Number of days to look back"
    ),
):
    """
    Get trending papers from recent publications
    This is a placeholder - in production you'd implement trending algorithms
    """
    try:
        # For now, return popular search terms as trending topics
        trending_queries = [
            "transformer architecture",
            "large language models",
            "diffusion models",
            "reinforcement learning",
            "computer vision",
            "natural language processing",
            "machine learning",
            "artificial intelligence",
            "deep learning",
            "neural networks",
        ]

        if field:
            # Filter by field if provided
            field_keywords = {
                "ai": [
                    "artificial intelligence",
                    "machine learning",
                    "deep learning",
                    "neural networks",
                ],
                "nlp": [
                    "natural language processing",
                    "large language models",
                    "transformer architecture",
                ],
                "cv": ["computer vision", "diffusion models"],
                "ml": ["machine learning", "reinforcement learning", "deep learning"],
            }

            trending_queries = field_keywords.get(field.lower(), trending_queries)

        return {
            "trending_topics": trending_queries[:10],
            "period_days": days,
            "field": field,
        }

    except Exception as e:
        logger.error("Failed to get trending papers", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get trending papers")


@router.post("/search/batch")
async def batch_search_papers(
    queries: List[str],
    sources: Optional[List[str]] = None,
    max_results_per_query: int = Query(default=10, ge=1, le=50),
):
    """
    Perform batch search for multiple queries
    """
    try:
        if len(queries) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 queries per batch")

        logger.info("Starting batch search", queries=queries, sources=sources)

        results = {}
        for query in queries:
            try:
                search_results = await web_search_service.search(
                    query=query, max_results=max_results_per_query, sources=sources
                )
                results[query] = search_results
            except Exception as e:
                logger.error(f"Batch search failed for query: {query}", error=str(e))
                results[query] = []

        return {
            "batch_results": results,
            "queries_processed": len(results),
            "total_papers": sum(len(papers) for papers in results.values()),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch search failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Batch search failed: {str(e)}")


@router.get("/search/recommendations")
async def get_paper_recommendations(
    paper_title: Optional[str] = Query(
        default=None, description="Base paper title for recommendations"
    ),
    keywords: Optional[List[str]] = Query(
        default=None, description="Keywords for recommendations"
    ),
    max_results: int = Query(default=10, ge=1, le=50),
):
    """
    Get paper recommendations based on existing paper or keywords
    """
    try:
        if not paper_title and not keywords:
            raise HTTPException(
                status_code=400,
                detail="Either paper_title or keywords must be provided",
            )

        # Build search query from inputs
        if paper_title:
            # Extract key terms from title for search
            # This is simplified - in production you'd use NLP to extract key terms
            query = paper_title
        else:
            query = " ".join(keywords)

        logger.info("Getting paper recommendations", query=query)

        # Use semantic scholar for recommendations as it has good related paper features
        results = await web_search_service.search(
            query=query, max_results=max_results, sources=["semantic_scholar", "arxiv"]
        )

        return {
            "recommendations": results,
            "based_on": {"paper_title": paper_title, "keywords": keywords},
            "total": len(results),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Paper recommendations failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Recommendations failed: {str(e)}")
