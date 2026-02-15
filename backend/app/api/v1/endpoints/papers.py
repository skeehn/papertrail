from typing import List, Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import settings
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

router = APIRouter()
logger = get_logger("papers")

# PDF processing - requires PyMuPDF
try:
    import fitz

    from app.services.pdf_processor import PDFProcessor

    PDF_PROCESSOR_AVAILABLE = True
except ImportError:
    fitz = None
    PDFProcessor = None
    PDF_PROCESSOR_AVAILABLE = False


@router.post("/upload", response_model=PaperUploadResponse)
async def upload_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    arxiv_id: Optional[str] = None,
):
    """Upload and process a PDF paper"""
    try:
        # Read file content first
        content = await file.read()

        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        # Validate file size
        if len(content) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")

        # Validate file content is actually a PDF
        if not content.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="File is not a valid PDF")

        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # Ensure upload directory exists
        import json
        import os

        from app.core.config import settings

        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        # Save uploaded file with sanitized filename
        safe_filename = os.path.basename(file.filename)
        file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

        with open(file_path, "wb") as buffer:
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

    except HTTPException:
        raise
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

        # Ensure required fields are present
        if not paper.get("title"):
            paper["title"] = paper.get("filename", "Untitled Paper")

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

        # #region agent log
        try:
            import json

            # Removed debug logging
        except Exception:
            pass
        # #endregion agent log

        # Handle None search parameter properly - empty string means no search filter
        search_param = search if search else None

        papers = db_list_papers(skip=skip, limit=limit, search=search_param)

        # Bug fix: total should be count of ALL matching papers, not just returned slice
        # Get total count by getting all matching papers (before pagination)
        # This is inefficient but correct until mock_store has a count method
        all_matching_papers = db_list_papers(skip=0, limit=999999, search=search_param)
        total_count = len(all_matching_papers)

        return PaperListResponse(
            papers=papers, total=total_count, skip=skip, limit=limit
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

        # Debug logging (only in development)
        if settings.ENVIRONMENT == "development":
            try:
                import json
                import os

                debug_log_path = os.path.join(os.getcwd(), ".cursor", "debug.log")
                os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)
                with open(debug_log_path, "a") as f:
                    f.write(
                        json.dumps(
                            {
                                "id": "log_pdf_processor_check",
                                "timestamp": __import__("time").time() * 1000,
                                "location": "papers.py:241",
                                "message": "PDFProcessor availability check",
                                "data": {
                                    "pdf_processor_available": PDF_PROCESSOR_AVAILABLE,
                                    "has_file_path": bool(request.file_path),
                                    "has_arxiv_id": bool(request.arxiv_id),
                                    "hypothesisId": "H",
                                },
                                "sessionId": "debug-session",
                                "runId": "run1",
                            }
                        )
                        + "\n"
                    )
            except Exception:
                pass

        if not PDF_PROCESSOR_AVAILABLE or PDFProcessor is None:
            error_msg = "PDF processing is not available. PDFProcessor library is not installed."
            logger.error("PDFProcessor not available", request_id=request.id)
            raise RuntimeError(error_msg)

        pdf_processor = PDFProcessor()

        if request.file_path:
            # Process local file
            paper_data = await pdf_processor.process_file(request.file_path)
        elif request.arxiv_id:
            # Download from arXiv
            paper_data = await pdf_processor.download_from_arxiv(request.arxiv_id)
        else:
            # Bug fix: HTTPException doesn't work in background tasks, use ValueError instead
            error_msg = "Either file_path or arxiv_id must be provided"
            logger.error(
                "Background task validation failed",
                error=error_msg,
                request_id=request.id,
            )
            raise ValueError(error_msg)

        # Step 2: Extract entities and relationships
        await processing_notifier.update_progress(
            request.id,
            0.4,
            "Extracting entities and relationships",
            "entity_extraction",
        )
        log_processing_step("entity_extraction", request.id)
        entity_extractor = EntityExtractor()

        text_content = paper_data.get("text", "")
        if not text_content:
            raise ValueError("PDF processing did not extract any text content")

        entities, relationships = (
            await entity_extractor.extract_entities_and_relationships(text_content)
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

        paper_id_for_store = (
            paper_data.get("arxiv_id")
            or paper_data.get("id")
            or str(__import__("uuid").uuid4())
        )
        add_documents_to_store(
            [
                {
                    "id": paper_id_for_store,
                    "text": paper_data.get("text", ""),
                    "metadata": {
                        "title": paper_data.get("title", ""),
                        "authors": paper_data.get("authors", []),
                        "arxiv_id": paper_data.get("arxiv_id"),
                    },
                }
            ]
        )

        # Complete processing
        await processing_notifier.complete_processing(
            request.id,
            {
                "paper_id": paper_data.get("arxiv_id")
                or paper_data.get("id")
                or request.id,
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
