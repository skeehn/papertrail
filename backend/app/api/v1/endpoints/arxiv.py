"""ArXiv API endpoints"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.arxiv_client import arxiv_client
from app.services.arxiv_indexer import batch_indexer
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger("arxiv_api")


# Request/Response Models
class ArXivSearchRequest(BaseModel):
    """Request model for arXiv search"""
    query: str = Field(..., description="Search query")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results")
    categories: Optional[List[str]] = Field(default=None, description="Filter by categories")
    sort_by: str = Field(default="relevance", description="Sort criterion")
    sort_order: str = Field(default="descending", description="Sort order")


class BulkIndexRequest(BaseModel):
    """Request model for bulk indexing"""
    arxiv_ids: List[str] = Field(..., description="List of arXiv IDs to index")


class QueryIndexRequest(BaseModel):
    """Request model for search and index"""
    query: str = Field(..., description="Search query")
    max_results: int = Field(default=50, ge=1, le=200, description="Maximum papers to index")
    categories: Optional[List[str]] = Field(default=None, description="Filter by categories")


class TrendingIndexRequest(BaseModel):
    """Request model for trending papers index"""
    categories: List[str] = Field(..., description="ArXiv categories")
    days_back: int = Field(default=7, ge=1, le=30, description="Days to look back")
    max_results: int = Field(default=50, ge=1, le=200, description="Maximum papers")


class PaperResponse(BaseModel):
    """Response model for paper"""
    arxiv_id: str
    title: str
    abstract: str
    authors: List[str]
    categories: List[str]
    published_date: Optional[str]
    pdf_url: str


class JobStatusResponse(BaseModel):
    """Response model for job status"""
    job_id: str
    status: str
    total_papers: int
    processed: int
    successful: int
    failed: int


# Endpoints

@router.post("/search", response_model=List[PaperResponse])
async def search_arxiv(request: ArXivSearchRequest) -> List[Dict[str, Any]]:
    """
    Search for papers on arXiv

    - **query**: Search query string
    - **max_results**: Maximum number of results (1-100)
    - **categories**: Optional list of arXiv categories to filter by
    - **sort_by**: Sort criterion (relevance, lastUpdatedDate, submittedDate)
    - **sort_order**: Sort order (ascending, descending)
    """
    try:
        papers = arxiv_client.search_papers(
            query=request.query,
            max_results=request.max_results,
            sort_by=request.sort_by,
            sort_order=request.sort_order,
            categories=request.categories
        )

        return papers

    except Exception as e:
        logger.error("ArXiv search failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/paper/{arxiv_id}", response_model=PaperResponse)
async def get_paper(arxiv_id: str) -> Dict[str, Any]:
    """
    Get a specific paper by arXiv ID

    - **arxiv_id**: arXiv ID (e.g., '2301.00001')
    """
    try:
        paper = arxiv_client.get_paper_by_id(arxiv_id)

        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper {arxiv_id} not found")

        return paper

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch paper", arxiv_id=arxiv_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch paper: {str(e)}")


@router.post("/bulk-index", response_model=Dict[str, Any])
async def bulk_index_papers(
    request: BulkIndexRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Index multiple papers by arXiv IDs

    This starts a background job to download, process, and index the papers.

    - **arxiv_ids**: List of arXiv IDs to index

    Returns job ID for tracking progress.
    """
    try:
        import asyncio
        from datetime import datetime

        job_id = f"bulk_index_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Run indexing in background
        async def run_indexing():
            await batch_indexer.index_papers_by_ids(request.arxiv_ids, job_id=job_id)

        background_tasks.add_task(lambda: asyncio.run(run_indexing()))

        return {
            "job_id": job_id,
            "status": "started",
            "total_papers": len(request.arxiv_ids),
            "message": f"Indexing {len(request.arxiv_ids)} papers in background"
        }

    except Exception as e:
        logger.error("Failed to start bulk indexing", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start indexing: {str(e)}")


@router.post("/index-by-search", response_model=Dict[str, Any])
async def index_by_search(
    request: QueryIndexRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Search arXiv and index the results

    - **query**: Search query
    - **max_results**: Maximum papers to index
    - **categories**: Optional category filters

    Returns job ID for tracking progress.
    """
    try:
        import asyncio
        from datetime import datetime

        job_id = f"search_index_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        async def run_indexing():
            await batch_indexer.index_papers_by_query(
                query=request.query,
                max_results=request.max_results,
                categories=request.categories
            )

        background_tasks.add_task(lambda: asyncio.run(run_indexing()))

        return {
            "job_id": job_id,
            "status": "started",
            "query": request.query,
            "max_results": request.max_results,
            "message": f"Searching and indexing papers for query: {request.query}"
        }

    except Exception as e:
        logger.error("Failed to start search indexing", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start indexing: {str(e)}")


@router.post("/index-trending", response_model=Dict[str, Any])
async def index_trending(
    request: TrendingIndexRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Index trending papers from specific categories

    - **categories**: List of arXiv categories (e.g., ['cs.AI', 'cs.LG'])
    - **days_back**: Number of days to look back (1-30)
    - **max_results**: Maximum papers to index

    Returns job ID for tracking progress.
    """
    try:
        import asyncio
        from datetime import datetime

        job_id = f"trending_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        async def run_indexing():
            await batch_indexer.index_trending_papers(
                categories=request.categories,
                days_back=request.days_back,
                max_results=request.max_results
            )

        background_tasks.add_task(lambda: asyncio.run(run_indexing()))

        return {
            "job_id": job_id,
            "status": "started",
            "categories": request.categories,
            "days_back": request.days_back,
            "message": f"Indexing trending papers from {len(request.categories)} categories"
        }

    except Exception as e:
        logger.error("Failed to start trending indexing", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start indexing: {str(e)}")


@router.post("/index-demo-papers", response_model=Dict[str, Any])
async def index_demo_papers(
    background_tasks: BackgroundTasks,
    max_results: int = Query(default=100, ge=10, le=200, description="Maximum papers to index")
) -> Dict[str, Any]:
    """
    Index a diverse set of AI research papers for demo purposes

    This will index papers across various AI topics including:
    - Large Language Models
    - Graph Neural Networks
    - Retrieval Augmented Generation
    - Transformers
    - Few-Shot Learning
    - And more...

    - **max_results**: Maximum total papers to index (10-200)

    Returns job ID for tracking progress.
    """
    try:
        import asyncio
        from datetime import datetime

        job_id = f"demo_papers_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        async def run_indexing():
            await batch_indexer.index_ai_research_papers(max_results=max_results)

        background_tasks.add_task(lambda: asyncio.run(run_indexing()))

        return {
            "job_id": job_id,
            "status": "started",
            "max_results": max_results,
            "message": f"Indexing up to {max_results} diverse AI research papers for demo"
        }

    except Exception as e:
        logger.error("Failed to start demo indexing", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start indexing: {str(e)}")


@router.get("/jobs/{job_id}", response_model=Dict[str, Any])
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get status of an indexing job

    - **job_id**: Job ID returned from an indexing endpoint
    """
    job = batch_indexer.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return job


@router.get("/jobs", response_model=Dict[str, Any])
async def get_all_jobs() -> Dict[str, Any]:
    """Get all indexing jobs"""
    return batch_indexer.get_all_jobs()


@router.get("/categories", response_model=Dict[str, List[str]])
async def get_categories() -> Dict[str, List[str]]:
    """Get available arXiv categories organized by domain"""
    return arxiv_client.get_available_categories()


@router.get("/download/{arxiv_id}")
async def download_paper(arxiv_id: str) -> Dict[str, Any]:
    """
    Download PDF for a paper

    - **arxiv_id**: arXiv ID

    Returns path to downloaded PDF
    """
    try:
        path = arxiv_client.download_paper(arxiv_id)

        if not path:
            raise HTTPException(status_code=404, detail=f"Failed to download paper {arxiv_id}")

        return {
            "arxiv_id": arxiv_id,
            "path": path,
            "message": "Paper downloaded successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to download paper", arxiv_id=arxiv_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
