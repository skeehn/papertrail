from typing import List, Optional
import structlog
from fastapi import APIRouter, HTTPException, Query, Body

from app.core.logging import get_logger
from app.services.recommender import Recommender

router = APIRouter()
logger = get_logger("recommendations")


@router.post("/papers", response_model=dict)
async def recommend_papers(paper_ids: List[str] = Body(..., embed=True)):
    """Recommend papers based on current library"""
    try:
        recommendations = Recommender.recommend_papers(paper_ids)
        
        return {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to recommend papers", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to recommend papers: {str(e)}")


@router.post("/for-question", response_model=dict)
async def recommend_for_question(request: dict = Body(...)):
    """Recommend papers based on a research question"""
    try:
        question = request.get("question", "")
        paper_ids = request.get("paper_ids")
        limit = request.get("limit", 5)
        
        if not question:
            raise HTTPException(status_code=400, detail="question parameter required")
        
        recommendations = Recommender.recommend_for_question(question, paper_ids, limit)
        
        return {
            "success": True,
            "question": question,
            "recommendations": recommendations,
            "count": len(recommendations),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to recommend for question", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to recommend: {str(e)}")


@router.get("/trending-topics", response_model=dict)
async def get_trending_topics(limit: int = Query(10, ge=1, le=50)):
    """Get trending research topics"""
    try:
        topics = Recommender.get_trending_topics(limit)
        
        return {
            "success": True,
            "topics": topics,
            "count": len(topics),
        }
    
    except Exception as e:
        logger.error("Failed to get trending topics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get trending topics: {str(e)}")
