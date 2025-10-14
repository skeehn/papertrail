from typing import List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.database.neo4j_client import get_entity_subgraph, search_entities
from app.models.schemas import EntityListResponse, EntityResponse

router = APIRouter()
logger = get_logger("entities")


@router.get("/", response_model=EntityListResponse)
async def list_entities(
    search: Optional[str] = Query(None, description="Search term for entity names"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(20, ge=1, le=100, description="Number of entities to return"),
    skip: int = Query(0, ge=0, description="Number of entities to skip"),
):
    """List entities with optional search and filtering"""
    try:
        if search:
            raw_entities = search_entities(search, entity_type, limit)
            entities = [EntityResponse(**entity) for entity in raw_entities]
        else:
            # TODO: Implement paginated entity listing
            entities = []

        return EntityListResponse(entities=entities, total=len(entities))

    except Exception as e:
        logger.error("Failed to list entities", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve entities")


@router.get("/types")
async def get_entity_types():
    """Get all available entity types"""
    try:
        # TODO: Implement entity type retrieval from database
        entity_types = [
            "concept",
            "method",
            "dataset",
            "claim",
            "assumption",
            "result",
            "author",
            "institution",
        ]

        return {"entity_types": entity_types}

    except Exception as e:
        logger.error("Failed to get entity types", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve entity types")


@router.get("/{entity_name}/subgraph")
async def get_entity_subgraph_endpoint(
    entity_name: str,
    depth: int = Query(2, ge=1, le=5, description="Depth of subgraph traversal"),
):
    """Get subgraph around a specific entity"""
    try:
        subgraph = get_entity_subgraph(entity_name, depth)

        return {"entity_name": entity_name, "depth": depth, "subgraph": subgraph}

    except Exception as e:
        logger.error(
            "Failed to get entity subgraph", error=str(e), entity_name=entity_name
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve entity subgraph"
        )


@router.get("/{entity_name}/papers")
async def get_entity_papers(
    entity_name: str,
    limit: int = Query(10, ge=1, le=50, description="Number of papers to return"),
):
    """Get papers that mention a specific entity"""
    try:
        # TODO: Implement paper retrieval by entity
        papers = []

        return {"entity_name": entity_name, "papers": papers, "total": len(papers)}

    except Exception as e:
        logger.error(
            "Failed to get entity papers", error=str(e), entity_name=entity_name
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve entity papers")


@router.get("/{entity_name}/related")
async def get_related_entities(
    entity_name: str,
    limit: int = Query(
        10, ge=1, le=50, description="Number of related entities to return"
    ),
):
    """Get entities related to a specific entity"""
    try:
        # TODO: Implement related entity retrieval
        related_entities = []

        return {
            "entity_name": entity_name,
            "related_entities": related_entities,
            "total": len(related_entities),
        }

    except Exception as e:
        logger.error(
            "Failed to get related entities", error=str(e), entity_name=entity_name
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve related entities"
        )


@router.get("/{entity_name}/timeline")
async def get_entity_timeline(entity_name: str):
    """Get timeline of entity mentions across papers"""
    try:
        # TODO: Implement entity timeline
        timeline = []

        return {"entity_name": entity_name, "timeline": timeline}

    except Exception as e:
        logger.error(
            "Failed to get entity timeline", error=str(e), entity_name=entity_name
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve entity timeline"
        )


@router.get("/{entity_name}/statistics")
async def get_entity_statistics(entity_name: str):
    """Get statistics for a specific entity"""
    try:
        # TODO: Implement entity statistics
        statistics = {
            "mention_count": 0,
            "paper_count": 0,
            "first_mention": None,
            "last_mention": None,
            "related_entities_count": 0,
        }

        return {"entity_name": entity_name, "statistics": statistics}

    except Exception as e:
        logger.error(
            "Failed to get entity statistics", error=str(e), entity_name=entity_name
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve entity statistics"
        )
