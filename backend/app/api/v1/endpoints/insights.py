"""Research insights API endpoints"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.agents.reasoning_agent import answer_complex_query
from app.core.logging import get_logger
from app.services.trend_analyzer import (
    analyze_trends,
    compare_entity_trends,
    find_emerging_topics,
    get_trending,
)

router = APIRouter()
logger = get_logger("insights_api")


# Request/Response Models
class ComplexQueryRequest(BaseModel):
    """Request model for complex reasoning"""

    query: str = Field(..., description="Complex research question")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional context"
    )


class TrendAnalysisRequest(BaseModel):
    """Request model for trend analysis"""

    entity_name: Optional[str] = Field(default=None, description="Entity to analyze")
    time_window_years: int = Field(
        default=5, ge=1, le=10, description="Years to analyze"
    )


class CompareTrendsRequest(BaseModel):
    """Request model for comparing trends"""

    entity_names: List[str] = Field(..., description="Entities to compare")
    time_window_years: int = Field(
        default=5, ge=1, le=10, description="Years to analyze"
    )


# Endpoints


@router.post("/reasoning", response_model=Dict[str, Any])
async def complex_reasoning(request: ComplexQueryRequest) -> Dict[str, Any]:
    """
    Answer a complex research question using multi-hop reasoning

    This endpoint decomposes complex questions into simpler sub-questions,
    answers each step using graph traversal and vector search, then synthesizes
    a final answer.

    Example queries:
    - "What methods used in sentiment analysis papers also appear in summarization research?"
    - "How have transformer architectures evolved from 2017 to 2023?"
    - "What datasets are commonly used for few-shot learning, and which methods work best on them?"

    - **query**: Complex research question
    - **context**: Optional context from previous queries

    Returns answer with reasoning steps and sources.
    """
    try:
        result = await answer_complex_query(request.query, request.context)
        return result

    except Exception as e:
        logger.error("Complex reasoning failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Reasoning failed: {str(e)}")


@router.post("/trends/analyze", response_model=Dict[str, Any])
async def analyze_entity_trends(request: TrendAnalysisRequest) -> Dict[str, Any]:
    """
    Analyze how entity mentions change over time

    - **entity_name**: Specific entity to analyze (None for all entities)
    - **time_window_years**: Years to look back (1-10)

    Returns yearly mention counts, growth rate, and trend direction.
    """
    try:
        result = await analyze_trends(
            entity_name=request.entity_name, time_window_years=request.time_window_years
        )
        return result

    except Exception as e:
        logger.error("Trend analysis failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/trends/emerging", response_model=List[Dict[str, Any]])
async def get_emerging_topics(
    lookback_months: int = Query(default=12, ge=1, le=36),
    min_growth_rate: float = Query(default=50.0, ge=0.0),
) -> List[Dict[str, Any]]:
    """
    Detect emerging research topics

    Identifies topics with significant growth in recent months compared to historical baseline.

    - **lookback_months**: Months to look back for comparison (1-36)
    - **min_growth_rate**: Minimum growth rate percentage to consider emerging

    Returns list of emerging topics with growth metrics.
    """
    try:
        result = await find_emerging_topics(lookback_months, min_growth_rate)
        return result

    except Exception as e:
        logger.error("Emerging topics detection failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


@router.get("/trends/trending", response_model=List[Dict[str, Any]])
async def get_trending_topics(
    recent_months: int = Query(default=6, ge=1, le=24),
    top_n: int = Query(default=10, ge=1, le=50),
) -> List[Dict[str, Any]]:
    """
    Get currently trending research topics

    Returns the most frequently mentioned entities in recent papers.

    - **recent_months**: Definition of "recent" (1-24 months)
    - **top_n**: Number of top trends to return (1-50)

    Returns list of trending topics with mention counts and example papers.
    """
    try:
        result = await get_trending(recent_months, top_n)
        return result

    except Exception as e:
        logger.error("Trending topics failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")


@router.post("/trends/compare", response_model=Dict[str, Any])
async def compare_trends(request: CompareTrendsRequest) -> Dict[str, Any]:
    """
    Compare trends across multiple entities

    Shows how different research topics have evolved relative to each other.

    - **entity_names**: List of entity names to compare
    - **time_window_years**: Years to analyze (1-10)

    Returns comparison matrix and individual trend data.
    """
    try:
        result = await compare_entity_trends(
            entity_names=request.entity_names,
            time_window_years=request.time_window_years,
        )
        return result

    except Exception as e:
        logger.error("Trend comparison failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.get("/summary", response_model=Dict[str, Any])
async def get_research_landscape_summary() -> Dict[str, Any]:
    """
    Get a high-level summary of the research landscape

    Returns key insights including:
    - Top trending topics
    - Emerging areas
    - Active research communities
    - Overall statistics

    This is useful for dashboard overview pages.
    """
    try:
        # Get multiple insights in parallel
        trending = await get_trending(recent_months=6, top_n=5)
        emerging = await find_emerging_topics(lookback_months=12, min_growth_rate=50.0)

        # Get overall trends
        all_trends = await analyze_trends(entity_name=None, time_window_years=3)

        summary = {
            "trending_now": trending,
            "emerging_topics": emerging[:5],
            "overall_trends": {
                "total_entities_tracked": all_trends.get("summary", {}).get(
                    "total_entities", 0
                ),
                "rising_topics": all_trends.get("summary", {}).get("rising", 0),
                "declining_topics": all_trends.get("summary", {}).get("declining", 0),
            },
            "top_rising": all_trends.get("top_rising", [])[:5],
            "most_mentioned": all_trends.get("most_mentioned", [])[:5],
            "generated_at": "2026-01-18T00:00:00Z",
        }

        return summary

    except Exception as e:
        logger.error("Summary generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Summary failed: {str(e)}")
