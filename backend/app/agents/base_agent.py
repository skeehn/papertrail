import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import openai
import structlog

from app.core.config import settings
from app.core.logging import get_logger, log_agent_activity
from app.services.pinecone_store import pinecone_store
from app.database.neo4j_client import neo4j_client


class AgentType(str, Enum):
    """Types of available agents"""

    SYNTHESIZER = "synthesizer"
    CRITIC = "critic"
    CONNECTOR = "connector"
    REASONING = "reasoning"


class TaskPriority(str, Enum):
    """Task priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class AgentTask:
    """Task for agent processing"""

    task_id: str
    query: str
    paper_ids: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class AgentResponse:
    """Standard agent response format"""

    response: str
    sources: List[str]
    confidence: float
    agent_type: str
    processing_time: float
    metadata: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None


class BaseAgent(ABC):
    """Base class for all PaperTrail agents"""

    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.logger = get_logger(f"agent.{agent_type.value}")
        # Initialize OpenAI client with optional base_url for OpenRouter support
        client_kwargs = {"api_key": settings.OPENAI_API_KEY}
        if settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = settings.OPENAI_BASE_URL
            # Add OpenRouter-specific headers if using OpenRouter
            if "openrouter.ai" in settings.OPENAI_BASE_URL:
                default_headers = {}
                if settings.OPENROUTER_HTTP_REFERER:
                    default_headers["HTTP-Referer"] = settings.OPENROUTER_HTTP_REFERER
                if settings.OPENROUTER_X_TITLE:
                    default_headers["X-Title"] = settings.OPENROUTER_X_TITLE
                if default_headers:
                    client_kwargs["default_headers"] = default_headers
        self.client = openai.AsyncOpenAI(**client_kwargs)

        # Agent configuration
        self.max_retries = settings.AGENT_MAX_RETRIES
        self.timeout = settings.AGENT_TIMEOUT
        self.model = settings.OPENAI_MODEL

        # Performance tracking
        self.task_count = 0
        self.total_processing_time = 0.0
        self.success_count = 0
        self.error_count = 0

        self.logger.info("Agent initialized", agent_type=agent_type.value)

    @abstractmethod
    async def process_task(self, task: AgentTask) -> AgentResponse:
        """Process a task and return a response"""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get the capabilities of this agent"""
        pass

    async def query(
        self,
        query: str,
        paper_ids: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Main query interface for the agent"""
        try:
            start_time = datetime.utcnow()

            # Create task
            task = AgentTask(
                task_id=f"{self.agent_type.value}_{int(start_time.timestamp())}",
                query=query,
                paper_ids=paper_ids,
                context=context or {},
            )

            self.logger.info(
                "Processing query",
                task_id=task.task_id,
                query=query[:100] + "..." if len(query) > 100 else query,
            )

            log_agent_activity(
                self.agent_type.value, "query_started", task_id=task.task_id
            )

            # Process task with timeout
            response = await asyncio.wait_for(
                self.process_task(task), timeout=self.timeout
            )

            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            response.processing_time = processing_time

            # Update performance metrics
            self._update_metrics(processing_time, success=True)

            log_agent_activity(
                self.agent_type.value,
                "query_completed",
                task_id=task.task_id,
                processing_time=processing_time,
                confidence=response.confidence,
            )

            self.logger.info(
                "Query completed successfully",
                task_id=task.task_id,
                processing_time=processing_time,
                confidence=response.confidence,
            )

            return response

        except asyncio.TimeoutError:
            self.logger.error("Query timeout", task_id=task.task_id)
            self._update_metrics(self.timeout, success=False)

            return AgentResponse(
                response="Query timed out. Please try with a more specific question.",
                sources=[],
                confidence=0.0,
                agent_type=self.agent_type.value,
                processing_time=self.timeout,
                metadata={"error": "timeout"},
            )

        except Exception as e:
            self.logger.error("Query failed", error=str(e), task_id=task.task_id)
            self._update_metrics(0.0, success=False)

            return AgentResponse(
                response=f"Sorry, I encountered an error processing your query: {str(e)}",
                sources=[],
                confidence=0.0,
                agent_type=self.agent_type.value,
                processing_time=0.0,
                metadata={"error": str(e)},
            )

    async def get_relevant_papers(
        self, query: str, paper_ids: Optional[List[str]] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get papers relevant to the query"""
        try:
            relevant_papers = []

            # If specific paper IDs are provided, get those papers
            if paper_ids:
                with neo4j_client.get_session() as session:
                    query_cypher = """
                    MATCH (p:Paper)
                    WHERE p.arxiv_id IN $paper_ids
                    RETURN p.arxiv_id as id, p.title as title, p.abstract as abstract,
                           p.authors as authors, p.text_length as text_length
                    """

                    result = session.run(query_cypher, paper_ids=paper_ids)
                    for record in result:
                        relevant_papers.append(dict(record))

            else:
                # Use vector search to find relevant papers
                search_results = await pinecone_store.search(
                    query_text=query,
                    top_k=limit,
                )

                for result in search_results:
                    if result.get("metadata", {}).get("type") == "paper" or result.get("id", "").startswith("paper_"):
                        relevant_papers.append(
                            {
                                "id": result.get("metadata", {}).get("arxiv_id", result.get("id", "")),
                                "title": result.get("metadata", {}).get("title", ""),
                                "authors": result.get("metadata", {}).get("authors", ""),
                                "abstract": result.get("metadata", {}).get("abstract", ""),
                                "similarity_score": result.get("score", 0.0),
                            }
                        )

            return relevant_papers[:limit]

        except Exception as e:
            self.logger.error("Failed to get relevant papers", error=str(e))
            return []

    async def get_relevant_entities(
        self, query: str, entity_types: Optional[List[str]] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get entities relevant to the query"""
        try:
            with neo4j_client.get_session() as session:
                # Build Cypher query based on entity types
                if entity_types:
                    type_filter = "AND e.type IN $entity_types"
                else:
                    type_filter = ""

                query_cypher = f"""
                MATCH (e:Entity)
                WHERE (e.name CONTAINS $query OR e.description CONTAINS $query)
                {type_filter}
                RETURN e.name as name, e.type as type, e.description as description,
                       e.confidence as confidence
                ORDER BY e.confidence DESC
                LIMIT $limit
                """

                result = session.run(
                    query_cypher,
                    query=query.lower(),
                    entity_types=entity_types,
                    limit=limit,
                )

                entities = []
                for record in result:
                    entities.append(dict(record))

                return entities

        except Exception as e:
            self.logger.error("Failed to get relevant entities", error=str(e))
            return []

    async def call_llm(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Call OpenAI LLM with standard error handling"""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = await self.client.chat.completions.create(**kwargs)

            choice = response.choices[0]

            # Handle tool call response
            if choice.message.tool_calls:
                tool_call = choice.message.tool_calls[0]
                return {
                    "type": "tool_call",
                    "tool_call_id": tool_call.id,
                    "function_name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                    "content": choice.message.content,
                }

            # Handle regular text response
            return {
                "type": "text",
                "content": choice.message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            }

        except Exception as e:
            self.logger.error("LLM call failed", error=str(e))
            raise

    def _update_metrics(self, processing_time: float, success: bool) -> None:
        """Update agent performance metrics"""
        self.task_count += 1
        self.total_processing_time += processing_time

        if success:
            self.success_count += 1
        else:
            self.error_count += 1

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        if self.task_count == 0:
            return {
                "agent_type": self.agent_type.value,
                "tasks_processed": 0,
                "success_rate": 0.0,
                "average_processing_time": 0.0,
                "total_processing_time": 0.0,
            }

        return {
            "agent_type": self.agent_type.value,
            "tasks_processed": self.task_count,
            "success_rate": self.success_count / self.task_count,
            "error_rate": self.error_count / self.task_count,
            "average_processing_time": self.total_processing_time / self.task_count,
            "total_processing_time": self.total_processing_time,
        }

    def reset_metrics(self) -> None:
        """Reset performance metrics"""
        self.task_count = 0
        self.total_processing_time = 0.0
        self.success_count = 0
        self.error_count = 0

        self.logger.info("Performance metrics reset", agent_type=self.agent_type.value)

    async def health_check(self) -> Dict[str, Any]:
        """Perform agent health check"""
        try:
            # Simple test query to check if agent is working
            test_response = await self.call_llm(
                [
                    {"role": "system", "content": "You are a test agent."},
                    {"role": "user", "content": "Say 'healthy' if you can respond."},
                ]
            )

            is_healthy = "healthy" in test_response.get("content", "").lower()

            return {
                "agent_type": self.agent_type.value,
                "status": "healthy" if is_healthy else "unhealthy",
                "last_check": datetime.utcnow().isoformat(),
                "metrics": self.get_performance_metrics(),
            }

        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            return {
                "agent_type": self.agent_type.value,
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat(),
            }

    def __str__(self) -> str:
        return f"{self.agent_type.value.title()}Agent"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(agent_type={self.agent_type.value})"
