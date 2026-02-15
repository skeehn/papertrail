from typing import Any, Dict

from fastapi import APIRouter

from app.core.logging import get_logger

router = APIRouter()
logger = get_logger("dashboard")


@router.get("/stats", response_model=Dict[str, Any])
async def get_dashboard_stats() -> Dict[str, Any]:
    """Get dashboard statistics"""
    try:
        from app.database import list_papers
        from app.database.mock_store import mock_store

        papers = list_papers(skip=0, limit=1000)

        stats = {
            "totalPapers": len(papers),
            "activeConversations": 0,
            "claimsExtracted": len(mock_store.entities),
            "graphNodes": len(mock_store.entities) + len(mock_store.papers),
            "relationships": len(mock_store.relationships),
        }

        return stats

    except Exception as e:
        logger.error("Failed to get dashboard stats", error=str(e))
        return {
            "totalPapers": 0,
            "activeConversations": 0,
            "claimsExtracted": 0,
            "graphNodes": 0,
            "relationships": 0,
        }
