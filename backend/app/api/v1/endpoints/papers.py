from typing import List, Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.logging import get_logger, log_processing_step
from app.models.schemas import (
    PaperListResponse,
    PaperProcessingRequest,
    PaperResponse,
    PaperUploadResponse,
    ProcessingStatus,
)
from app.services.entity_extractor import EntityExtractor
from app.services.graph_builder import GraphBuilder
from app.services.pdf_processor import PDFProcessor

router = APIRouter()
logger = get_logger("papers")


@router.post("/upload", response_model=PaperUploadResponse)
async def upload_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    arxiv_id: Optional[str] = None,
):
    """Upload and process a PDF paper"""
    try:
        # Validate file type
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        # Save uploaded file
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Create processing request
        processing_request = PaperProcessingRequest(
            file_path=file_path, filename=file.filename, arxiv_id=arxiv_id
        )

        # Start background processing
        background_tasks.add_task(process_paper_background, processing_request)

        logger.info("Paper upload started", filename=file.filename, arxiv_id=arxiv_id)

        return PaperUploadResponse(
            message="Paper uploaded successfully",
            filename=file.filename,
            processing_id=processing_request.id,
            status=ProcessingStatus.PENDING,
        )

    except Exception as e:
        logger.error("Paper upload failed", error=str(e), filename=file.filename)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/process", response_model=PaperUploadResponse)
async def process_arxiv_paper(
    background_tasks: BackgroundTasks, request: PaperProcessingRequest
):
    """Process a paper from arXiv ID"""
    try:
        # Start background processing
        background_tasks.add_task(process_paper_background, request)

        logger.info("ArXiv paper processing started", arxiv_id=request.arxiv_id)

        return PaperUploadResponse(
            message="Paper processing started",
            filename=request.filename,
            processing_id=request.id,
            status=ProcessingStatus.PENDING,
        )

    except Exception as e:
        logger.error(
            "ArXiv paper processing failed", error=str(e), arxiv_id=request.arxiv_id
        )
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(paper_id: str):
    """Get paper details"""
    try:
        # Get paper from database
        from app.database import get_paper_by_id

        paper = get_paper_by_id(paper_id)

        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        return PaperResponse(**paper)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get paper", error=str(e), paper_id=paper_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve paper")


@router.get("/", response_model=PaperListResponse)
async def list_papers(skip: int = 0, limit: int = 20, search: Optional[str] = None):
    """List all papers with optional search"""
    try:
        from app.database import list_papers as db_list_papers

        papers = db_list_papers(skip=skip, limit=limit, search=search)

        return PaperListResponse(
            papers=papers, total=len(papers), skip=skip, limit=limit
        )

    except Exception as e:
        logger.error("Failed to list papers", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve papers")


@router.delete("/{paper_id}")
async def delete_paper(paper_id: str):
    """Delete a paper and its associated data"""
    try:
        from app.database import delete_paper as db_delete_paper

        success = db_delete_paper(paper_id)

        if not success:
            raise HTTPException(status_code=404, detail="Paper not found")

        logger.info("Paper deleted", paper_id=paper_id)
        return {"message": "Paper deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete paper", error=str(e), paper_id=paper_id)
        raise HTTPException(status_code=500, detail="Failed to delete paper")


@router.get("/{paper_id}/entities")
async def get_paper_entities(paper_id: str):
    """Get entities extracted from a paper"""
    try:
        from app.database import get_paper_entities as db_get_paper_entities

        entities = db_get_paper_entities(paper_id)

        return {"entities": entities}

    except Exception as e:
        logger.error("Failed to get paper entities", error=str(e), paper_id=paper_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve paper entities")


@router.get("/{paper_id}/related")
async def get_related_papers(paper_id: str, limit: int = 10):
    """Get papers related to the given paper"""
    try:
        from app.database import get_related_papers as db_get_related_papers

        related = db_get_related_papers(paper_id, limit=limit)

        return {"related_papers": related}

    except Exception as e:
        logger.error("Failed to get related papers", error=str(e), paper_id=paper_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve related papers")


async def process_paper_background(request: PaperProcessingRequest):
    """Background task to process uploaded paper"""
    try:
        # Import WebSocket notifier
        from app.websocket.websocket_manager import processing_notifier

        logger.info(
            "Starting paper processing",
            filename=request.filename,
            arxiv_id=request.arxiv_id,
        )

        # Notify start of processing
        await processing_notifier.start_processing(
            request.id,
            "paper_processing",
            {"filename": request.filename, "arxiv_id": request.arxiv_id},
        )

        # Step 1: Extract text from PDF
        await processing_notifier.update_progress(
            request.id, 0.1, "Extracting text from PDF", "pdf_extraction"
        )
        log_processing_step("pdf_extraction", request.id)
        pdf_processor = PDFProcessor()

        if request.arxiv_id:
            # Download from arXiv
            paper_data = await pdf_processor.download_from_arxiv(request.arxiv_id)
        else:
            # Process local file
            paper_data = await pdf_processor.process_file(request.file_path)

        # Step 2: Extract entities and relationships
        await processing_notifier.update_progress(
            request.id,
            0.4,
            "Extracting entities and relationships",
            "entity_extraction",
        )
        log_processing_step("entity_extraction", request.id)
        entity_extractor = EntityExtractor()
        entities, relationships = (
            await entity_extractor.extract_entities_and_relationships(
                paper_data["text"]
            )
        )

        # Step 3: Build knowledge graph
        await processing_notifier.update_progress(
            request.id, 0.7, "Building knowledge graph", "graph_construction"
        )
        log_processing_step("graph_construction", request.id)
        graph_builder = GraphBuilder()
        result = graph_builder.add_paper_to_graph(paper_data, entities, relationships)

        # Step 4: Add to vector store
        await processing_notifier.update_progress(
            request.id, 0.9, "Adding to vector search index", "vector_store"
        )
        log_processing_step("vector_store", request.id)
        from app.database.faiss_store import add_documents_to_store

        add_documents_to_store(
            [
                {
                    "id": paper_data["arxiv_id"],
                    "text": paper_data["text"],
                    "metadata": {
                        "title": paper_data["title"],
                        "authors": paper_data["authors"],
                        "arxiv_id": paper_data["arxiv_id"],
                    },
                }
            ]
        )

        # Complete processing
        await processing_notifier.complete_processing(
            request.id,
            {
                "paper_id": paper_data["arxiv_id"],
                "entities_extracted": len(entities),
                "relationships_extracted": len(relationships),
                "graph_result": result,
            },
        )

        logger.info(
            "Paper processing completed",
            filename=request.filename,
            arxiv_id=request.arxiv_id,
        )

    except Exception as e:
        logger.error(
            "Paper processing failed",
            error=str(e),
            filename=request.filename,
            arxiv_id=request.arxiv_id,
        )

        # Notify processing error
        await processing_notifier.error_processing(
            request.id, str(e), "paper_processing_error"
        )
        # This would typically update a database record
