import asyncio
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

import structlog

from app.agents.base_agent import AgentResponse, AgentTask, AgentType
from app.agents.connector_agent import ConnectorAgent
from app.agents.critic_agent import CriticAgent
from app.agents.synthesizer_agent import SynthesizerAgent
from app.core.config import settings
from app.core.logging import get_logger, log_agent_activity


class WorkflowType(str, Enum):
    """Types of multi-agent workflows"""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    COLLABORATIVE = "collaborative"


class WorkflowStatus(str, Enum):
    """Workflow execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """Individual step in a workflow"""

    step_id: str
    agent_type: AgentType
    query: str
    dependencies: List[str] = None
    inputs: Dict[str, Any] = None
    outputs: Dict[str, Any] = None
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.inputs is None:
            self.inputs = {}
        if self.outputs is None:
            self.outputs = {}


@dataclass
class Workflow:
    """Multi-agent workflow definition"""

    workflow_id: str
    workflow_type: WorkflowType
    query: str
    paper_ids: Optional[List[str]]
    steps: List[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: List[AgentResponse] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.results is None:
            self.results = []
        if self.metadata is None:
            self.metadata = {}


class AgentOrchestrator:
    """Orchestrates multi-agent workflows for complex research tasks"""

    def __init__(self):
        self.logger = get_logger("orchestrator")

        # Initialize agents
        self.agents = {
            AgentType.SYNTHESIZER: SynthesizerAgent(),
            AgentType.CRITIC: CriticAgent(),
            AgentType.CONNECTOR: ConnectorAgent(),
        }

        # Workflow management
        self.active_workflows: Dict[str, Workflow] = {}
        self.workflow_history: List[Workflow] = []
        self.max_concurrent_workflows = 5
        self.workflow_timeout = timedelta(minutes=30)

        self.logger.info(
            "Agent orchestrator initialized",
            agents=list(self.agents.keys()),
            max_concurrent=self.max_concurrent_workflows,
        )

    async def query_agent(
        self, agent_type: str, query: str, paper_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Query a single agent"""
        try:
            agent_enum = AgentType(agent_type)
            agent = self.agents[agent_enum]

            self.logger.info(
                "Querying single agent", agent_type=agent_type, query=query[:100]
            )

            response = await agent.query(query, paper_ids)

            return {
                "response": response.response,
                "sources": response.sources,
                "confidence": response.confidence,
                "agent_type": response.agent_type,
                "processing_time": response.processing_time,
                "metadata": response.metadata,
                "reasoning": response.reasoning,
            }

        except ValueError as e:
            raise ValueError(f"Invalid agent type: {agent_type}")
        except Exception as e:
            self.logger.error("Single agent query failed", error=str(e))
            raise

    async def execute_workflow(
        self,
        workflow_id: str,
        query: str,
        agents: List[str],
        paper_ids: Optional[List[str]] = None,
        workflow_type: str = "sequential",
    ) -> List[AgentResponse]:
        """Execute a multi-agent workflow"""
        try:
            workflow_type_enum = WorkflowType(workflow_type)

            # Create workflow
            workflow = await self._create_workflow(
                workflow_id, query, agents, paper_ids, workflow_type_enum
            )

            self.logger.info(
                "Starting workflow execution",
                workflow_id=workflow_id,
                workflow_type=workflow_type,
                agents=agents,
            )

            log_agent_activity(
                "orchestrator",
                "workflow_started",
                workflow_id=workflow_id,
                agents=agents,
            )

            # Execute based on workflow type
            if workflow_type_enum == WorkflowType.SEQUENTIAL:
                results = await self._execute_sequential_workflow(workflow)
            elif workflow_type_enum == WorkflowType.PARALLEL:
                results = await self._execute_parallel_workflow(workflow)
            elif workflow_type_enum == WorkflowType.COLLABORATIVE:
                results = await self._execute_collaborative_workflow(workflow)
            else:
                results = await self._execute_sequential_workflow(workflow)  # Default

            # Update workflow status
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()
            workflow.results = results

            log_agent_activity(
                "orchestrator",
                "workflow_completed",
                workflow_id=workflow_id,
                duration=(workflow.completed_at - workflow.started_at).total_seconds(),
                results_count=len(results),
            )

            self.logger.info(
                "Workflow execution completed",
                workflow_id=workflow_id,
                results_count=len(results),
            )

            return results

        except Exception as e:
            self.logger.error(
                "Workflow execution failed", error=str(e), workflow_id=workflow_id
            )

            # Update workflow status
            if workflow_id in self.active_workflows:
                workflow = self.active_workflows[workflow_id]
                workflow.status = WorkflowStatus.FAILED
                workflow.completed_at = datetime.utcnow()
                workflow.metadata["error"] = str(e)

            raise

    async def _create_workflow(
        self,
        workflow_id: str,
        query: str,
        agents: List[str],
        paper_ids: Optional[List[str]],
        workflow_type: WorkflowType,
    ) -> Workflow:
        """Create a workflow with steps"""

        # Create steps based on agents
        steps = []
        invalid_agents: List[str] = []
        for i, agent_type_str in enumerate(agents):
            try:
                agent_type = AgentType(agent_type_str)
                step = WorkflowStep(
                    step_id=f"{workflow_id}_step_{i}",
                    agent_type=agent_type,
                    query=query,
                    dependencies=[] if i == 0 else [f"{workflow_id}_step_{i-1}"],
                )
                steps.append(step)
            except ValueError:
                invalid_agents.append(agent_type_str)

        metadata: Dict[str, Any] = {}
        if invalid_agents:
            error_message = "Invalid agent types requested: " + ", ".join(invalid_agents)
            metadata["error"] = error_message
            self.logger.warning(
                "Invalid agent types requested for workflow",
                workflow_id=workflow_id,
                invalid_agents=invalid_agents,
            )

        workflow = Workflow(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            query=query,
            paper_ids=paper_ids,
            steps=steps,
            metadata=metadata if metadata else None,
        )

        self.active_workflows[workflow_id] = workflow
        return workflow

    async def _execute_sequential_workflow(
        self, workflow: Workflow
    ) -> List[AgentResponse]:
        """Execute agents sequentially, each building on previous results"""
        results = []

        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.utcnow()

        for i, step in enumerate(workflow.steps):
            try:
                self.logger.info(
                    "Executing workflow step",
                    workflow_id=workflow.workflow_id,
                    step_id=step.step_id,
                    agent_type=step.agent_type.value,
                )

                step.status = WorkflowStatus.RUNNING
                step.started_at = datetime.utcnow()

                # Get agent
                agent = self.agents[step.agent_type]

                # Build query context from previous results
                enhanced_query = step.query
                if i > 0 and results:
                    context = self._build_context_from_previous_results(
                        results, step.agent_type
                    )
                    enhanced_query = (
                        f"{step.query}\n\nContext from previous analysis:\n{context}"
                    )

                # Execute agent
                response = await agent.query(enhanced_query, workflow.paper_ids)
                results.append(response)

                # Update step
                step.status = WorkflowStatus.COMPLETED
                step.completed_at = datetime.utcnow()
                step.outputs = {
                    "response": response.response,
                    "confidence": response.confidence,
                    "sources": response.sources,
                }

                self.logger.info(
                    "Workflow step completed",
                    step_id=step.step_id,
                    agent_type=step.agent_type.value,
                    confidence=response.confidence,
                )

            except Exception as e:
                step.status = WorkflowStatus.FAILED
                step.error = str(e)
                step.completed_at = datetime.utcnow()

                self.logger.error(
                    "Workflow step failed", step_id=step.step_id, error=str(e)
                )

                # Continue with other steps unless critical failure
                if "critical" in str(e).lower():
                    break

        return results

    async def _execute_parallel_workflow(
        self, workflow: Workflow
    ) -> List[AgentResponse]:
        """Execute agents in parallel"""
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.utcnow()

        # Create tasks for all agents
        tasks = []
        for step in workflow.steps:
            agent = self.agents[step.agent_type]
            task = asyncio.create_task(
                agent.query(step.query, workflow.paper_ids),
                name=f"{step.step_id}_{step.agent_type.value}",
            )
            tasks.append((step, task))

        # Execute all tasks concurrently
        results = []
        for step, task in tasks:
            try:
                step.status = WorkflowStatus.RUNNING
                step.started_at = datetime.utcnow()

                response = await task
                results.append(response)

                step.status = WorkflowStatus.COMPLETED
                step.completed_at = datetime.utcnow()
                step.outputs = {
                    "response": response.response,
                    "confidence": response.confidence,
                    "sources": response.sources,
                }

            except Exception as e:
                step.status = WorkflowStatus.FAILED
                step.error = str(e)
                step.completed_at = datetime.utcnow()

                self.logger.error(
                    "Parallel workflow step failed", step_id=step.step_id, error=str(e)
                )

        return results

    async def _execute_collaborative_workflow(
        self, workflow: Workflow
    ) -> List[AgentResponse]:
        """Execute agents collaboratively with information sharing"""
        results = []

        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.utcnow()

        # Round 1: All agents analyze independently
        parallel_results = await self._execute_parallel_workflow(workflow)
        results.extend(parallel_results)

        # Round 2: Synthesizer creates final synthesis based on all results
        if len(parallel_results) > 1:
            try:
                synthesizer = self.agents[AgentType.SYNTHESIZER]

                # Build comprehensive context
                context = self._build_comprehensive_context(parallel_results)
                synthesis_query = f"""
                Create a final synthesis based on the following multi-agent analysis of: {workflow.query}
                
                {context}
                
                Provide a comprehensive synthesis that integrates insights from all agents.
                """

                final_response = await synthesizer.query(
                    synthesis_query, workflow.paper_ids
                )
                results.append(final_response)

                self.logger.info(
                    "Collaborative synthesis completed",
                    workflow_id=workflow.workflow_id,
                )

            except Exception as e:
                self.logger.error("Collaborative synthesis failed", error=str(e))

        return results

    def _build_context_from_previous_results(
        self, previous_results: List[AgentResponse], current_agent: AgentType
    ) -> str:
        """Build context from previous agent results"""
        context_parts = []

        for result in previous_results:
            context_parts.append(f"## {result.agent_type.title()} Analysis:")
            context_parts.append(f"**Confidence**: {result.confidence:.2f}")
            context_parts.append(f"**Key Points**: {result.response[:300]}...")
            if result.reasoning:
                context_parts.append(f"**Reasoning**: {result.reasoning}")
            context_parts.append("")

        return "\n".join(context_parts)

    def _build_comprehensive_context(self, results: List[AgentResponse]) -> str:
        """Build comprehensive context from all results"""
        context_parts = []

        for result in results:
            context_parts.append(f"## {result.agent_type.title()} Agent Results:")
            context_parts.append(f"**Confidence**: {result.confidence:.2f}")
            context_parts.append(f"**Analysis**: {result.response}")
            if result.sources:
                context_parts.append(f"**Sources**: {', '.join(result.sources)}")
            if result.reasoning:
                context_parts.append(f"**Reasoning**: {result.reasoning}")
            context_parts.append("---")

        return "\n".join(context_parts)

    async def execute_sequential_workflow(
        self,
        workflow_id: str,
        query: str,
        agents: List[str],
        paper_ids: Optional[List[str]] = None,
    ) -> None:
        """Execute sequential workflow as background task"""
        try:
            await self.execute_workflow(
                workflow_id=workflow_id,
                query=query,
                agents=agents,
                paper_ids=paper_ids,
                workflow_type="sequential",
            )
        except Exception as e:
            self.logger.error(
                "Background sequential workflow failed",
                error=str(e),
                workflow_id=workflow_id,
            )

    async def analyze_with_agent(
        self, agent_type: str, query: str, paper_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Perform detailed analysis with a specific agent"""
        try:
            agent_enum = AgentType(agent_type)
            agent = self.agents[agent_enum]

            # Create detailed analysis task
            task = AgentTask(
                task_id=f"analysis_{agent_type}_{int(datetime.utcnow().timestamp())}",
                query=query,
                paper_ids=paper_ids,
                context={"analysis_mode": "detailed"},
            )

            self.logger.info(
                "Starting detailed analysis",
                agent_type=agent_type,
                task_id=task.task_id,
            )

            response = await agent.process_task(task)

            return {
                "agent_type": agent_type,
                "analysis": {
                    "response": response.response,
                    "confidence": response.confidence,
                    "sources": response.sources,
                    "metadata": response.metadata,
                    "reasoning": response.reasoning,
                },
                "processing_time": response.processing_time,
                "task_id": task.task_id,
            }

        except ValueError as e:
            raise ValueError(f"Invalid agent type: {agent_type}")
        except Exception as e:
            self.logger.error("Detailed analysis failed", error=str(e))
            raise

    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get status of a running workflow"""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]

            if not workflow.steps:
                error_message = workflow.metadata.get("error") or "Workflow has no valid steps."
                if "error" not in workflow.metadata:
                    workflow.metadata["error"] = error_message

                return {
                    "workflow_id": workflow_id,
                    "status": workflow.status.value,
                    "progress": 0.0,
                    "query": workflow.query,
                    "workflow_type": workflow.workflow_type.value,
                    "created_at": workflow.created_at.isoformat(),
                    "started_at": (
                        workflow.started_at.isoformat() if workflow.started_at else None
                    ),
                    "completed_at": (
                        workflow.completed_at.isoformat()
                        if workflow.completed_at
                        else None
                    ),
                    "steps": [],
                    "results_count": len(workflow.results),
                    "error": error_message,
                }

            step_statuses = []
            for step in workflow.steps:
                step_statuses.append(
                    {
                        "step_id": step.step_id,
                        "agent_type": step.agent_type.value,
                        "status": step.status.value,
                        "started_at": (
                            step.started_at.isoformat() if step.started_at else None
                        ),
                        "completed_at": (
                            step.completed_at.isoformat() if step.completed_at else None
                        ),
                        "error": step.error,
                    }
                )

            total_steps = len(workflow.steps)
            completed_steps = len(
                [s for s in workflow.steps if s.status == WorkflowStatus.COMPLETED]
            )
            progress = completed_steps / total_steps if total_steps else 0.0

            return {
                "workflow_id": workflow_id,
                "status": workflow.status.value,
                "progress": progress,
                "query": workflow.query,
                "workflow_type": workflow.workflow_type.value,
                "created_at": workflow.created_at.isoformat(),
                "started_at": (
                    workflow.started_at.isoformat() if workflow.started_at else None
                ),
                "completed_at": (
                    workflow.completed_at.isoformat() if workflow.completed_at else None
                ),
                "steps": step_statuses,
                "results_count": len(workflow.results),
                "error": workflow.metadata.get("error"),
            }

        # Check workflow history
        for workflow in self.workflow_history:
            if workflow.workflow_id == workflow_id:
                return {
                    "workflow_id": workflow_id,
                    "status": workflow.status.value,
                    "progress": 1.0,
                    "completed_at": (
                        workflow.completed_at.isoformat()
                        if workflow.completed_at
                        else None
                    ),
                    "results_count": len(workflow.results),
                }

        return {"error": f"Workflow {workflow_id} not found"}

    def get_agent_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for all agents"""
        metrics = {}

        for agent_type, agent in self.agents.items():
            metrics[agent_type.value] = agent.get_performance_metrics()

        # Add orchestrator metrics
        metrics["orchestrator"] = {
            "active_workflows": len(self.active_workflows),
            "completed_workflows": len(self.workflow_history),
            "total_workflows": len(self.active_workflows) + len(self.workflow_history),
        }

        return metrics

    async def cleanup_completed_workflows(self) -> None:
        """Clean up completed workflows"""
        current_time = datetime.utcnow()
        completed_workflows = []

        for workflow_id, workflow in list(self.active_workflows.items()):
            # Move completed workflows to history
            if workflow.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]:
                completed_workflows.append(workflow)
                del self.active_workflows[workflow_id]

            # Cancel timed-out workflows
            elif (
                workflow.started_at
                and current_time - workflow.started_at > self.workflow_timeout
            ):
                workflow.status = WorkflowStatus.CANCELLED
                workflow.completed_at = current_time
                workflow.metadata["timeout"] = True
                completed_workflows.append(workflow)
                del self.active_workflows[workflow_id]

        # Add to history
        self.workflow_history.extend(completed_workflows)

        # Limit history size
        if len(self.workflow_history) > 100:
            self.workflow_history = self.workflow_history[-100:]

        if completed_workflows:
            self.logger.info("Cleaned up workflows", count=len(completed_workflows))

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on orchestrator and all agents"""
        health_status = {
            "orchestrator": {
                "status": "healthy",
                "active_workflows": len(self.active_workflows),
                "agents_available": len(self.agents),
            },
            "agents": {},
        }

        # Check each agent
        for agent_type, agent in self.agents.items():
            try:
                agent_health = await agent.health_check()
                health_status["agents"][agent_type.value] = agent_health
            except Exception as e:
                health_status["agents"][agent_type.value] = {
                    "status": "unhealthy",
                    "error": str(e),
                }

        # Overall status
        agent_statuses = [agent["status"] for agent in health_status["agents"].values()]
        if all(status == "healthy" for status in agent_statuses):
            health_status["overall"] = "healthy"
        elif any(status == "healthy" for status in agent_statuses):
            health_status["overall"] = "degraded"
        else:
            health_status["overall"] = "unhealthy"

        return health_status
