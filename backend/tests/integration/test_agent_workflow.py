"""Integration tests for agent workflows"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
class TestAgentWorkflow:
    """Test multi-agent workflow integration"""

    @patch("app.api.v1.endpoints.agents.AgentOrchestrator")
    async def test_sequential_workflow(self, mock_orchestrator_class):
        """Test sequential agent workflow"""
        mock_orchestrator = mock_orchestrator_class.return_value
        mock_orchestrator.execute_workflow = AsyncMock(
            return_value=[
                MagicMock(
                    response="Synthesizer response",
                    sources=[],
                    confidence=0.9,
                    agent_type="synthesizer",
                ),
                MagicMock(
                    response="Critic response",
                    sources=[],
                    confidence=0.85,
                    agent_type="critic",
                ),
            ]
        )

        response = client.post(
            "/api/v1/agents/multi-agent",
            json={
                "query": "Analyze this paper",
                "agents": ["synthesizer", "critic"],
                "workflow": "sequential",
                "paper_ids": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data

    @patch("app.api.v1.endpoints.agents.AgentOrchestrator")
    async def test_parallel_workflow(self, mock_orchestrator_class):
        """Test parallel agent workflow"""
        from app.models.schemas import AgentResponse as AgentResponseModel

        mock_orchestrator = mock_orchestrator_class.return_value
        mock_orchestrator.execute_workflow = AsyncMock(
            return_value=[
                AgentResponseModel(
                    response="Response 1",
                    agent_type="synthesizer",
                    sources=[],
                    confidence=0.9,
                    processing_time=1.0,
                ),
                AgentResponseModel(
                    response="Response 2",
                    agent_type="critic",
                    sources=[],
                    confidence=0.85,
                    processing_time=1.0,
                ),
            ]
        )

        response = client.post(
            "/api/v1/agents/multi-agent",
            json={
                "query": "Complex analysis",
                "agents": ["synthesizer", "critic", "connector"],
                "workflow": "parallel",
                "paper_ids": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "responses" in data or "workflow_id" in data

    @patch("app.api.v1.endpoints.agents.AgentOrchestrator")
    async def test_workflow_status_tracking(self, mock_orchestrator_class):
        """Test workflow status tracking"""
        mock_orchestrator = mock_orchestrator_class.return_value
        mock_orchestrator.get_workflow_status = MagicMock(
            return_value={
                "workflow_id": "test-workflow",
                "status": "running",
                "progress": 0.5,
                "steps": [],
            }
        )

        response = client.get("/api/v1/agents/workflow/test-workflow/status")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
