"""Community detection API endpoints"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.community_detector import (
    community_detector,
    detect_research_communities,
    get_all_communities,
    get_community_by_id,
)
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger("communities_api")


# Request/Response Models
class CommunityDetectionRequest(BaseModel):
    """Request model for community detection"""

    algorithm: str = Field(
        default="louvain", description="Algorithm (louvain, label_propagation, wcc)"
    )
    min_community_size: int = Field(
        default=3, ge=2, le=50, description="Minimum community size"
    )


class CommunityResponse(BaseModel):
    """Response model for community"""

    id: str
    name: str
    summary: str
    size: int
    paper_count: int
    top_entities: List[str]


# Endpoints


@router.post("/detect", response_model=Dict[str, Any])
async def detect_communities(
    request: CommunityDetectionRequest, background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Detect research communities in the knowledge graph

    This analyzes the entity-entity relationships to identify clusters of related research topics.

    - **algorithm**: Algorithm to use (louvain, label_propagation, or wcc)
    - **min_community_size**: Minimum number of entities per community

    Returns detected communities with names, summaries, and member entities.
    """
    try:
        result = await detect_research_communities(
            algorithm=request.algorithm, min_size=request.min_community_size
        )

        logger.info(f"Detected {result['total_communities']} communities")
        return result

    except Exception as e:
        logger.error("Community detection failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


@router.get("/", response_model=List[CommunityResponse])
async def list_communities() -> List[Dict[str, Any]]:
    """
    Get all detected communities

    Returns a list of all research communities that have been detected in the graph.
    """
    try:
        communities = await get_all_communities()
        return communities

    except Exception as e:
        logger.error("Failed to fetch communities", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch: {str(e)}")


@router.get("/{community_id}", response_model=Dict[str, Any])
async def get_community(community_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific community

    - **community_id**: Community ID

    Returns detailed information including all member entities and related papers.
    """
    try:
        community = await get_community_by_id(community_id)

        if not community:
            raise HTTPException(
                status_code=404, detail=f"Community {community_id} not found"
            )

        return community

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch community {community_id}", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch: {str(e)}")


@router.get("/{community_id}/papers", response_model=List[Dict[str, Any]])
async def get_community_papers(
    community_id: str, limit: int = Query(default=20, ge=1, le=100)
) -> List[Dict[str, Any]]:
    """
    Get papers related to a community

    - **community_id**: Community ID
    - **limit**: Maximum number of papers to return

    Returns papers that mention entities in this community.
    """
    try:
        community = await get_community_by_id(community_id)

        if not community:
            raise HTTPException(
                status_code=404, detail=f"Community {community_id} not found"
            )

        return community.get("papers", [])[:limit]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to fetch papers for community {community_id}", error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to fetch: {str(e)}")
