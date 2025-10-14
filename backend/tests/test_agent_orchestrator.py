import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.agent_orchestrator import AgentOrchestrator, WorkflowType


@pytest.mark.asyncio
async def test_get_workflow_status_handles_no_valid_steps():
    orchestrator = AgentOrchestrator()
    workflow_id = "workflow_no_valid_steps"

    # Create a workflow with only invalid agents to ensure no steps are generated.
    await orchestrator._create_workflow(
        workflow_id=workflow_id,
        query="test query",
        agents=["invalid_agent_type"],
        paper_ids=None,
        workflow_type=WorkflowType.SEQUENTIAL,
    )

    status = orchestrator.get_workflow_status(workflow_id)

    assert status["progress"] == 0.0
    assert status["steps"] == []
    assert "Invalid agent types requested" in status["error"]
