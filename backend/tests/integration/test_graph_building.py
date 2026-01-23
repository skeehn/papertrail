"""Integration tests for graph building"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
class TestGraphBuilding:
    """Test graph construction integration"""

    @patch("app.api.v1.endpoints.graph.get_entity_subgraph")
    def test_entity_to_graph_flow(self, mock_get_subgraph):
        """Test querying entity and building graph visualization"""
        mock_get_subgraph.return_value = (
            [
                {
                    "id": "entity1",
                    "label": "Transformer",
                    "type": "Entity",
                    "properties": {"name": "Transformer"},
                },
                {
                    "id": "entity2",
                    "label": "Attention",
                    "type": "Entity",
                    "properties": {"name": "Attention"},
                },
            ],
            [
                {
                    "source": "entity1",
                    "target": "entity2",
                    "type": "USES",
                    "properties": {},
                },
            ],
        )
        
        # Query graph
        response = client.post(
            "/api/v1/graph/query",
            json={
                "entity_name": "Transformer",
                "depth": 2,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) > 0
        assert len(data["edges"]) > 0

    @patch("app.api.v1.endpoints.graph.get_graph_statistics")
    def test_graph_statistics_flow(self, mock_get_stats):
        """Test getting graph statistics"""
        mock_get_stats.return_value = {
            "nodes": {
                "Entity": 50,
                "Paper": 20,
            },
            "relationships": {
                "MENTIONS": 100,
                "CITES": 30,
            },
        }
        
        response = client.get("/api/v1/graph/statistics")
        
        assert response.status_code == 200
        data = response.json()
        assert "statistics" in data
        assert data["statistics"]["node_count"] > 0
