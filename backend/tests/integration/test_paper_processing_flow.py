"""Integration tests for paper processing flow"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import tempfile
import os

from app.main import app

client = TestClient(app)


@pytest.fixture
def sample_pdf():
    """Create a sample PDF file"""
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 1\ntrailer\n<< /Root 1 0 R >>\nstartxref\n10\n%%EOF"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(pdf_content)
        temp_path = f.name
    
    yield temp_path
    
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.mark.asyncio
class TestPaperProcessingFlow:
    """Test end-to-end paper processing flow"""

    @patch("app.api.v1.endpoints.papers.PDFProcessor")
    @patch("app.api.v1.endpoints.papers.EntityExtractor")
    @patch("app.api.v1.endpoints.papers.GraphBuilder")
    @patch("app.api.v1.endpoints.papers.add_documents_to_store")
    async def test_complete_paper_processing(
        self, mock_vector_store, mock_graph_builder, mock_entity_extractor, mock_pdf_processor, sample_pdf
    ):
        """Test complete paper processing from upload to graph"""
        # Mock PDF processing
        mock_pdf_instance = mock_pdf_processor.return_value
        mock_pdf_instance.process_file = AsyncMock(return_value={
            "id": "test-paper",
            "title": "Test Paper",
            "authors": ["Author"],
            "text": "Sample paper text content",
            "arxiv_id": None,
        })
        
        # Mock entity extraction
        mock_entity_instance = mock_entity_extractor.return_value
        mock_entity_instance.extract_entities_and_relationships = AsyncMock(return_value=(
            [
                {"name": "Entity1", "type": "METHOD", "description": "Test entity"},
            ],
            [
                {"source": "Entity1", "target": "Entity2", "type": "RELATED_TO"},
            ],
        ))
        
        # Mock graph building
        mock_graph_instance = mock_graph_builder.return_value
        mock_graph_instance.add_paper_to_graph = MagicMock(return_value={
            "paper_id": "test-paper",
            "entities_added": 1,
            "relationships_added": 1,
        })
        
        # Mock vector store
        mock_vector_store.return_value = None
        
        # Upload paper
        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/api/v1/papers/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "processing_id" in data
        
        # Note: In a real integration test, we would wait for background processing
        # and verify the results in the database

    @patch("app.api.v1.endpoints.papers.processing_notifier")
    async def test_paper_processing_with_notifications(self, mock_notifier, sample_pdf):
        """Test paper processing with WebSocket notifications"""
        mock_notifier.start_processing = AsyncMock()
        mock_notifier.update_progress = AsyncMock()
        mock_notifier.complete_processing = AsyncMock()
        
        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/api/v1/papers/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        
        assert response.status_code == 200
        # Verify notifications were called (in real test, would check WebSocket messages)
