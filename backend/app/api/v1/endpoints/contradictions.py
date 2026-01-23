from typing import List, Optional
import structlog
from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.services.contradiction_detector import ContradictionDetector

router = APIRouter()
logger = get_logger("contradictions")


@router.post("/detect", response_model=dict)
async def detect_contradictions(paper_ids: List[str]):
    """Detect contradictions across papers"""
    try:
        if not paper_ids:
            raise HTTPException(status_code=400, detail="paper_ids parameter required")
        
        result = ContradictionDetector.detect_contradictions(paper_ids)
        
        return {
            "success": True,
            "contradictions": result["contradictions"],
            "metrics": result["metrics"],
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to detect contradictions", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to detect contradictions: {str(e)}")


@router.get("/summary/{paper_id}", response_model=dict)
async def get_contradiction_summary(paper_id: str):
    """Get contradiction summary for a paper"""
    try:
        summary = ContradictionDetector.get_contradiction_summary(paper_id)
        
        return {
            "success": True,
            "summary": summary,
        }
    
    except Exception as e:
        logger.error("Failed to get contradiction summary", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get contradiction summary: {str(e)}")


@router.get("/grouped", response_model=dict)
async def get_grouped_contradictions(paper_ids: List[str] = Query(None)):
    """Get grouped contradictions"""
    try:
        if not paper_ids:
            raise HTTPException(status_code=400, detail="paper_ids parameter required")
        
        # Detect contradictions first
        detection = ContradictionDetector.detect_contradictions(paper_ids)
        
        # Group them
        grouped = ContradictionDetector.group_contradictions(detection["contradictions"])
        
        return {
            "success": True,
            "groups": grouped,
            "total_groups": len(grouped),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get grouped contradictions", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get grouped contradictions: {str(e)}")
