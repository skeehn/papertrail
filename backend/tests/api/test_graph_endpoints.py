"""Tests for graph API endpoints"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)


class TestGraphQuery:
    """Test graph query endpoint"""

    @patch("app.api.v1.endpoints.graph.get_entity_subgraph")
    def test_query_graph_by_entity(self, mock_get_subgraph):
        """Test querying graph by entity name"""
        mock_get_subgraph.return_value = (
            [
                {
                    "id": "entity1",
                    "label": "Entity 1",
                    "type": "Entity",
                    "properties": {},
                }
            ],
            [
                {
                    "source": "entity1",
                    "target": "entity2",
                    "type": "RELATED_TO",
                    "properties": {},
                }
            ],
        )
        
        response = client.post(
            "/api/v1/graph/query",
            json={
                "entity_name": "test_entity",
                "depth": 2,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data

    def test_query_graph_by_paper_id(self):
        """Test querying graph by paper ID"""
        response = client.post(
            "/api/v1/graph/query",
            json={
                "paper_id": "test-paper-123",
                "depth": 1,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data

    def test_query_graph_empty(self):
        """Test querying graph with no parameters"""
        response = client.post(
            "/api/v1/graph/query",
            json={},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data


class TestGraphStatistics:
    """Test graph statistics endpoint"""

    @patch("app.api.v1.endpoints.graph.get_graph_statistics")
    def test_get_graph_statistics(self, mock_get_stats):
        """Test getting graph statistics"""
        mock_get_stats.return_value = {
            "nodes": {"Entity": 10, "Paper": 5},
            "relationships": {"MENTIONS": 20},
        }
        
        response = client.get("/api/v1/graph/statistics")
        
        assert response.status_code == 200
        data = response.json()
        assert "statistics" in data
        assert "node_count" in data["statistics"]


class TestGraphNodes:
    """Test graph nodes endpoint"""

    def test_get_graph_nodes(self):
        """Test getting graph nodes"""
        response = client.get("/api/v1/graph/nodes")
        
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "total" in data

    def test_get_graph_nodes_with_filter(self):
        """Test getting graph nodes with type filter"""
        response = client.get("/api/v1/graph/nodes?node_type=Entity")
        
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data

    def test_get_graph_nodes_with_pagination(self):
        """Test getting graph nodes with pagination"""
        response = client.get("/api/v1/graph/nodes?skip=10&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert "skip" in data
        assert "limit" in data


class TestGraphEdges:
    """Test graph edges endpoint"""

    def test_get_graph_edges(self):
        """Test getting graph edges"""
        response = client.get("/api/v1/graph/edges")
        
        assert response.status_code == 200
        data = response.json()
        assert "edges" in data
        assert "total" in data

    def test_get_graph_edges_with_filter(self):
        """Test getting graph edges with type filter"""
        response = client.get("/api/v1/graph/edges?edge_type=MENTIONS")
        
        assert response.status_code == 200
        data = response.json()
        assert "edges" in data


class TestGraphPaths:
    """Test graph paths endpoint"""

    def test_get_shortest_paths(self):
        """Test getting shortest paths between nodes"""
        response = client.get(
            "/api/v1/graph/paths?source=node1&target=node2&max_length=5"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "source" in data
        assert "target" in data
        assert "paths" in data

    def test_get_shortest_paths_missing_params(self):
        """Test getting paths with missing parameters"""
        response = client.get("/api/v1/graph/paths")
        
        assert response.status_code == 422  # Validation error
