"""Tests for papers API endpoints"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import tempfile
import os

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_paper_data():
    """Mock paper data for testing"""
    return {
        "id": "test-paper-123",
        "title": "Test Paper",
        "authors": ["Author One", "Author Two"],
        "arxiv_id": "1234.5678",
        "status": "processed",
    }


@pytest.fixture
def sample_pdf_file():
    """Create a temporary PDF file for testing"""
    # Create a minimal PDF file
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 1\ntrailer\n<< /Root 1 0 R >>\nstartxref\n10\n%%EOF"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(pdf_content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestPaperUpload:
    """Test paper upload endpoint"""

    def test_upload_pdf_success(self, sample_pdf_file):
        """Test successful PDF upload"""
        with open(sample_pdf_file, "rb") as f:
            response = client.post(
                "/api/v1/papers/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "processing_id" in data
        assert data["status"] in ["pending", "processing"]

    def test_upload_invalid_file_type(self):
        """Test upload with invalid file type"""
        response = client.post(
            "/api/v1/papers/upload",
            files={"file": ("test.txt", b"not a pdf", "text/plain")},
        )
        
        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

    def test_upload_empty_file(self):
        """Test upload with empty file"""
        response = client.post(
            "/api/v1/papers/upload",
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        
        assert response.status_code == 400

    def test_upload_file_too_large(self):
        """Test upload with file exceeding size limit"""
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        response = client.post(
            "/api/v1/papers/upload",
            files={"file": ("large.pdf", large_content, "application/pdf")},
        )
        
        assert response.status_code == 400


class TestPaperList:
    """Test paper listing endpoint"""

    @patch("app.api.v1.endpoints.papers.list_papers")
    def test_list_papers_success(self, mock_list):
        """Test successful paper listing"""
        mock_list.return_value = {
            "papers": [
                {"id": "1", "title": "Paper 1"},
                {"id": "2", "title": "Paper 2"},
            ],
            "total": 2,
            "skip": 0,
            "limit": 20,
        }
        
        response = client.get("/api/v1/papers/")
        assert response.status_code == 200
        data = response.json()
        assert "papers" in data
        assert len(data["papers"]) == 2

    def test_list_papers_with_pagination(self):
        """Test paper listing with pagination"""
        response = client.get("/api/v1/papers/?skip=10&limit=5")
        assert response.status_code == 200

    def test_list_papers_with_search(self):
        """Test paper listing with search query"""
        response = client.get("/api/v1/papers/?search=transformer")
        assert response.status_code == 200


class TestPaperGet:
    """Test get paper endpoint"""

    @patch("app.api.v1.endpoints.papers.get_paper_by_id")
    def test_get_paper_success(self, mock_get):
        """Test successful paper retrieval"""
        mock_get.return_value = {
            "id": "test-123",
            "title": "Test Paper",
            "authors": ["Author"],
        }
        
        response = client.get("/api/v1/papers/test-123")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Paper"

    def test_get_paper_not_found(self):
        """Test get paper that doesn't exist"""
        response = client.get("/api/v1/papers/non-existent")
        assert response.status_code == 404


class TestPaperDelete:
    """Test paper deletion endpoint"""

    @patch("app.api.v1.endpoints.papers.delete_paper")
    def test_delete_paper_success(self, mock_delete):
        """Test successful paper deletion"""
        mock_delete.return_value = True
        
        response = client.delete("/api/v1/papers/test-123")
        assert response.status_code == 200
        assert "message" in response.json()

    def test_delete_paper_not_found(self):
        """Test delete paper that doesn't exist"""
        response = client.delete("/api/v1/papers/non-existent")
        assert response.status_code == 404
