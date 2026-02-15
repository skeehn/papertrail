from typing import List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.services.gap_analyzer import GapAnalyzer

router = APIRouter()
logger = get_logger("gaps")


@router.get("/analyze", response_model=dict)
async def analyze_gaps(paper_ids: Optional[List[str]] = Query(None)):
    """Analyze research gaps in the paper library"""
    try:
        result = GapAnalyzer.analyze_research_gaps(paper_ids)

        return {
            "success": True,
            "analysis": result,
        }

    except Exception as e:
        logger.error("Failed to analyze research gaps", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze research gaps: {str(e)}"
        )


@router.get("/trending", response_model=dict)
async def get_trending_gaps(timeframe_days: int = Query(365, ge=30, le=1095)):
    """Get trending gaps over a time period"""
    try:
        result = GapAnalyzer.find_trending_gaps(timeframe_days)

        return {
            "success": True,
            "trends": result,
        }

    except Exception as e:
        logger.error("Failed to get trending gaps", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get trending gaps: {str(e)}"
        )
