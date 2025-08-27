import time
from typing import List, Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core.logging import get_logger, log_agent_activity
from app.models.schemas import (
    AgentQueryRequest,
    AgentResponse,
    MultiAgentRequest,
    MultiAgentResponse,
)
from app.services.agent_orchestrator import AgentOrchestrator

router = APIRouter()
logger = get_logger("agents")


@router.post("/query", response_model=AgentResponse)
async def query_agent(request: AgentQueryRequest):
    """Query a specific agent with a question"""
    try:
        start_time = time.time()

        # Log agent activity
        log_agent_activity(request.agent_type, "query_started", query=request.query)

        # Initialize agent orchestrator
        orchestrator = AgentOrchestrator()

        # Get agent response
        response = await orchestrator.query_agent(
            agent_type=request.agent_type,
            query=request.query,
            paper_ids=request.paper_ids,
        )

        processing_time = time.time() - start_time

        # Log completion
        log_agent_activity(
            request.agent_type,
            "query_completed",
            processing_time=processing_time,
            confidence=response.get("confidence", 0.0),
        )

        return AgentResponse(
            response=response["response"],
            sources=response.get("sources", []),
            confidence=response.get("confidence", 0.0),
            agent_type=request.agent_type,
            processing_time=processing_time,
        )

    except Exception as e:
        logger.error("Agent query failed", error=str(e), agent_type=request.agent_type)
        raise HTTPException(status_code=500, detail=f"Agent query failed: {str(e)}")


@router.post("/multi-agent", response_model=MultiAgentResponse)
async def multi_agent_query(
    background_tasks: BackgroundTasks, request: MultiAgentRequest
):
    """Query multiple agents in a coordinated workflow"""
    try:
        start_time = time.time()

        # Log multi-agent activity
        log_agent_activity(
            "multi_agent",
            "workflow_started",
            agents=request.agents,
            workflow=request.workflow,
        )

        # Initialize agent orchestrator
        orchestrator = AgentOrchestrator()

        # Execute multi-agent workflow
        workflow_id = f"workflow_{int(time.time())}"

        # Start background task for long-running workflows
        if request.workflow == "sequential":
            background_tasks.add_task(
                orchestrator.execute_sequential_workflow,
                workflow_id=workflow_id,
                query=request.query,
                agents=request.agents,
                paper_ids=request.paper_ids,
            )

            return MultiAgentResponse(
                responses=[], workflow_id=workflow_id, total_processing_time=0.0
            )
        else:
            # Execute immediately for simple workflows
            responses = await orchestrator.execute_workflow(
                workflow_id=workflow_id,
                query=request.query,
                agents=request.agents,
                paper_ids=request.paper_ids,
                workflow_type=request.workflow,
            )

            processing_time = time.time() - start_time

            return MultiAgentResponse(
                responses=responses,
                workflow_id=workflow_id,
                total_processing_time=processing_time,
            )

    except Exception as e:
        logger.error("Multi-agent query failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Multi-agent query failed: {str(e)}"
        )


@router.get("/workflow/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get the status of a multi-agent workflow"""
    try:
        # TODO: Implement workflow status tracking
        status = {
            "workflow_id": workflow_id,
            "status": "completed",  # or "running", "failed"
            "progress": 1.0,
            "responses": [],
            "error": None,
        }

        return status

    except Exception as e:
        logger.error(
            "Failed to get workflow status", error=str(e), workflow_id=workflow_id
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve workflow status"
        )


@router.get("/types")
async def get_agent_types():
    """Get available agent types"""
    try:
        agent_types = [
            {
                "type": "synthesizer",
                "description": "Summarizes papers and extracts key claims",
                "capabilities": [
                    "paper_summarization",
                    "claim_extraction",
                    "argument_identification",
                ],
            },
            {
                "type": "critic",
                "description": "Flags assumptions and identifies contradictions",
                "capabilities": [
                    "assumption_detection",
                    "contradiction_identification",
                    "methodology_critique",
                ],
            },
            {
                "type": "connector",
                "description": "Finds related work and argument relationships",
                "capabilities": [
                    "related_work_discovery",
                    "citation_analysis",
                    "concept_linking",
                ],
            },
        ]

        return {"agent_types": agent_types}

    except Exception as e:
        logger.error("Failed to get agent types", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve agent types")


@router.get("/{agent_type}/capabilities")
async def get_agent_capabilities(agent_type: str):
    """Get capabilities of a specific agent type"""
    try:
        capabilities = {
            "synthesizer": {
                "paper_summarization": "Create structured summaries of papers",
                "claim_extraction": "Extract key claims and findings",
                "argument_identification": "Identify main arguments and evidence",
            },
            "critic": {
                "assumption_detection": "Identify unstated assumptions",
                "contradiction_identification": "Find contradictions between papers",
                "methodology_critique": "Evaluate methodological strengths and weaknesses",
            },
            "connector": {
                "related_work_discovery": "Find papers with similar themes",
                "citation_analysis": "Analyze citation networks",
                "concept_linking": "Link related concepts across papers",
            },
        }

        if agent_type not in capabilities:
            raise HTTPException(status_code=404, detail="Agent type not found")

        return {"agent_type": agent_type, "capabilities": capabilities[agent_type]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get agent capabilities", error=str(e), agent_type=agent_type
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve agent capabilities"
        )


@router.post("/{agent_type}/analyze")
async def analyze_with_agent(agent_type: str, request: AgentQueryRequest):
    """Analyze papers with a specific agent"""
    try:
        start_time = time.time()

        # Validate agent type
        valid_agents = ["synthesizer", "critic", "connector"]
        if agent_type not in valid_agents:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent type. Must be one of: {valid_agents}",
            )

        # Log analysis activity
        log_agent_activity(agent_type, "analysis_started", query=request.query)

        # Initialize agent orchestrator
        orchestrator = AgentOrchestrator()

        # Perform analysis
        analysis_result = await orchestrator.analyze_with_agent(
            agent_type=agent_type, query=request.query, paper_ids=request.paper_ids
        )

        processing_time = time.time() - start_time

        # Log completion
        log_agent_activity(
            agent_type, "analysis_completed", processing_time=processing_time
        )

        return {
            "agent_type": agent_type,
            "analysis": analysis_result,
            "processing_time": processing_time,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Agent analysis failed", error=str(e), agent_type=agent_type)
        raise HTTPException(status_code=500, detail=f"Agent analysis failed: {str(e)}")


@router.get("/performance")
async def get_agent_performance():
    """Get performance metrics for all agents"""
    try:
        # TODO: Implement agent performance tracking
        performance_metrics = {
            "synthesizer": {
                "total_queries": 0,
                "average_response_time": 0.0,
                "success_rate": 1.0,
            },
            "critic": {
                "total_queries": 0,
                "average_response_time": 0.0,
                "success_rate": 1.0,
            },
            "connector": {
                "total_queries": 0,
                "average_response_time": 0.0,
                "success_rate": 1.0,
            },
        }

        return {"performance_metrics": performance_metrics}

    except Exception as e:
        logger.error("Failed to get agent performance", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to retrieve agent performance"
        )
