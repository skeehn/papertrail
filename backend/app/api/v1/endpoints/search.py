from typing import List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.services.pinecone_store import pinecone_store
from app.models.schemas import SearchRequest, SearchResponse

router = APIRouter()
logger = get_logger("search")


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(request: SearchRequest):
    """Perform semantic search across papers and entities"""
    try:
        # Build filter if entity_type is specified
        filter_dict = None
        if request.entity_type:
            filter_dict = {"entity_type": request.entity_type}

        # Perform semantic search using Pinecone (with auto-embedding)
        results = await pinecone_store.search(
            query_text=request.query,
            top_k=request.limit,
            filter=filter_dict,
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "id": result.get("id", ""),
                    "text": result.get("text", ""),
                    "metadata": result.get("metadata", {}),
                    "score": result.get("score", 0.0),
                }
            )

        return SearchResponse(
            results=formatted_results, total=len(formatted_results), query=request.query
        )

    except Exception as e:
        logger.error("Semantic search failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/papers")
async def search_papers(
    query: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
):
    """Search for papers by title, abstract, or content"""
    try:
        # TODO: Implement paper-specific search
        results = []

        return {
            "query": query,
            "results": results,
            "total": len(results),
            "limit": limit,
            "skip": skip,
        }

    except Exception as e:
        logger.error("Paper search failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to search papers")


@router.get("/entities")
async def search_entities(
    query: str = Query(..., description="Search query"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
):
    """Search for entities by name or description"""
    try:
        from app.database.neo4j_client import search_entities

        results = search_entities(query, entity_type, limit)

        return {
            "query": query,
            "entity_type": entity_type,
            "results": results,
            "total": len(results),
        }

    except Exception as e:
        logger.error("Entity search failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to search entities")


@router.get("/concepts")
async def search_concepts(
    query: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
):
    """Search for concepts and their relationships"""
    try:
        # TODO: Implement concept search
        results = []

        return {"query": query, "results": results, "total": len(results)}

    except Exception as e:
        logger.error("Concept search failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to search concepts")


@router.get("/similar")
async def find_similar(
    paper_id: Optional[str] = Query(
        None, description="Paper ID to find similar papers for"
    ),
    entity_name: Optional[str] = Query(
        None, description="Entity name to find similar entities for"
    ),
    limit: int = Query(
        10, ge=1, le=50, description="Number of similar items to return"
    ),
):
    """Find similar papers or entities"""
    try:
        if paper_id:
            # Find similar papers
            from app.database.neo4j_client import get_related_papers

            similar_items = get_related_papers(paper_id, limit)

            return {
                "type": "papers",
                "reference_id": paper_id,
                "similar_items": similar_items,
                "total": len(similar_items),
            }

        elif entity_name:
            # Find similar entities
            from app.database.neo4j_client import search_entities

            similar_items = search_entities(entity_name, limit=limit)

            return {
                "type": "entities",
                "reference_name": entity_name,
                "similar_items": similar_items,
                "total": len(similar_items),
            }

        else:
            raise HTTPException(
                status_code=400, detail="Must provide either paper_id or entity_name"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Similar search failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to find similar items")


@router.get("/suggestions")
async def get_search_suggestions(
    query: str = Query(..., description="Partial search query"),
    type: str = Query(
        "all", description="Type of suggestions (papers, entities, concepts, all)"
    ),
):
    """Get search suggestions based on partial query"""
    try:
        # TODO: Implement search suggestions
        suggestions = []

        return {"query": query, "type": type, "suggestions": suggestions}

    except Exception as e:
        logger.error("Search suggestions failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get search suggestions")


@router.get("/trending")
async def get_trending_topics(
    timeframe: str = Query("week", description="Timeframe for trending analysis"),
    limit: int = Query(
        10, ge=1, le=50, description="Number of trending topics to return"
    ),
):
    """Get trending topics and concepts"""
    try:
        # TODO: Implement trending topics analysis
        trending_topics = []

        return {
            "timeframe": timeframe,
            "trending_topics": trending_topics,
            "total": len(trending_topics),
        }

    except Exception as e:
        logger.error("Trending topics failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get trending topics")


@router.get("/advanced")
async def advanced_search(
    query: str = Query(..., description="Search query"),
    filters: Optional[str] = Query(None, description="JSON string of search filters"),
    sort_by: str = Query(
        "relevance", description="Sort by (relevance, date, citations)"
    ),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
):
    """Advanced search with filters and sorting"""
    try:
        # TODO: Implement advanced search with filters
        results = []

        return {
            "query": query,
            "filters": filters,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "results": results,
            "total": len(results),
            "limit": limit,
            "skip": skip,
        }

    except Exception as e:
        logger.error("Advanced search failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to perform advanced search")


@router.get("/autocomplete")
async def autocomplete_search(
    query: str = Query(..., description="Partial search query"),
    type: str = Query(
        "all", description="Type of autocomplete (papers, entities, concepts, all)"
    ),
):
    """Get autocomplete suggestions for search queries"""
    try:
        # TODO: Implement autocomplete functionality
        suggestions = []

        return {"query": query, "type": type, "suggestions": suggestions}

    except Exception as e:
        logger.error("Autocomplete failed", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to get autocomplete suggestions"
        )


@router.get("/faceted")
async def faceted_search(
    query: str = Query(..., description="Search query"),
    facets: Optional[List[str]] = Query(
        None, description="Facets to include in results"
    ),
):
    """Get faceted search results with aggregations"""
    try:
        # TODO: Implement faceted search
        results = {"query": query, "results": [], "facets": {}, "total": 0}

        return results

    except Exception as e:
        logger.error("Faceted search failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to perform faceted search")
