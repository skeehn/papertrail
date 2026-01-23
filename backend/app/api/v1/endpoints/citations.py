from typing import List, Optional
import structlog
from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.services.citation_analyzer import CitationAnalyzer

router = APIRouter()
logger = get_logger("citations")


@router.get("/network", response_model=dict)
async def get_citation_network(paper_ids: Optional[List[str]] = Query(None)):
    """Get citation network for papers"""
    try:
        if not paper_ids:
            raise HTTPException(status_code=400, detail="paper_ids parameter required")
        
        network = CitationAnalyzer.analyze_citation_network(paper_ids)
        
        return {
            "success": True,
            "network": network
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get citation network", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get citation network: {str(e)}")


@router.get("/paths/{source_paper_id}/{target_paper_id}", response_model=dict)
async def get_citation_paths(
    source_paper_id: str,
    target_paper_id: str,
    max_hops: int = Query(3, ge=1, le=10)
):
    """Find citation paths between papers"""
    try:
        paths = CitationAnalyzer.find_citation_paths(source_paper_id, target_paper_id, max_hops)
        
        return {
            "success": True,
            "paths": paths,
            "count": len(paths),
        }
    
    except Exception as e:
        logger.error("Failed to find citation paths", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to find citation paths: {str(e)}")


@router.get("/clusters", response_model=dict)
async def get_citation_clusters(paper_ids: Optional[List[str]] = Query(None)):
    """Identify citation clusters"""
    try:
        if not paper_ids:
            raise HTTPException(status_code=400, detail="paper_ids parameter required")
        
        clusters = CitationAnalyzer.identify_citation_clusters(paper_ids)
        
        return {
            "success": True,
            "clusters": clusters,
            "count": len(clusters),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get citation clusters", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get citation clusters: {str(e)}")


@router.get("/metrics/{paper_id}", response_model=dict)
async def get_paper_citation_metrics(paper_id: str):
    """Get citation metrics for a paper"""
    try:
        metrics = CitationAnalyzer.get_paper_citation_metrics(paper_id)
        
        return {
            "success": True,
            "metrics": metrics,
        }
    
    except Exception as e:
        logger.error("Failed to get citation metrics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get citation metrics: {str(e)}")
