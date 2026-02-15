"""Tests for agents API endpoints"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestAgentQuery:
    """Test agent query endpoint"""

    @patch("app.api.v1.endpoints.agents.AgentOrchestrator")
    def test_query_synthesizer_agent(self, mock_orchestrator_class):
        """Test querying synthesizer agent"""
        mock_orchestrator = mock_orchestrator_class.return_value
        mock_orchestrator.query_agent = AsyncMock(
            return_value={
                "response": "Test response",
                "sources": [],
                "confidence": 0.9,
                "agent_type": "synthesizer",
                "processing_time": 1.5,
                "metadata": {},
                "reasoning": "Test reasoning",
            }
        )

        response = client.post(
            "/api/v1/agents/query",
            json={
                "agent_type": "synthesizer",
                "query": "Test query",
                "paper_ids": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["agent_type"] == "synthesizer"
        assert "response" in data

    @patch("app.api.v1.endpoints.agents.AgentOrchestrator")
    def test_query_critic_agent(self, mock_orchestrator_class):
        """Test querying critic agent"""
        mock_orchestrator = mock_orchestrator_class.return_value
        mock_orchestrator.query_agent = AsyncMock(
            return_value={
                "response": "Critic analysis",
                "sources": [],
                "confidence": 0.85,
                "agent_type": "critic",
                "processing_time": 2.0,
                "metadata": {},
                "reasoning": None,
            }
        )

        response = client.post(
            "/api/v1/agents/query",
            json={
                "agent_type": "critic",
                "query": "Analyze assumptions",
                "paper_ids": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["agent_type"] == "critic"

    def test_query_invalid_agent_type(self):
        """Test query with invalid agent type"""
        response = client.post(
            "/api/v1/agents/query",
            json={
                "agent_type": "invalid_agent",
                "query": "Test",
                "paper_ids": [],
            },
        )

        assert response.status_code == 500 or response.status_code == 400


class TestMultiAgentWorkflow:
    """Test multi-agent workflow endpoint"""

    @patch("app.api.v1.endpoints.agents.AgentOrchestrator")
    def test_multi_agent_sequential(self, mock_orchestrator_class):
        """Test sequential multi-agent workflow"""
        mock_orchestrator = mock_orchestrator_class.return_value
        mock_orchestrator.execute_workflow = AsyncMock(return_value=[])

        response = client.post(
            "/api/v1/agents/multi-agent",
            json={
                "query": "Complex query",
                "agents": ["synthesizer", "critic"],
                "workflow": "sequential",
                "paper_ids": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data


class TestAgentTypes:
    """Test agent types endpoint"""

    def test_get_agent_types(self):
        """Test getting available agent types"""
        response = client.get("/api/v1/agents/types")

        assert response.status_code == 200
        data = response.json()
        assert "agent_types" in data
        assert len(data["agent_types"]) > 0

    def test_get_agent_capabilities(self):
        """Test getting agent capabilities"""
        response = client.get("/api/v1/agents/synthesizer/capabilities")

        assert response.status_code == 200
        data = response.json()
        assert "agent_type" in data
        assert "capabilities" in data
