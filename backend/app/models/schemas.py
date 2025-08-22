import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Paper-related schemas
class PaperProcessingRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_path: Optional[str] = None
    filename: Optional[str] = None
    arxiv_id: Optional[str] = None


class PaperUploadResponse(BaseModel):
    message: str
    filename: str
    processing_id: str
    status: ProcessingStatus


class PaperResponse(BaseModel):
    id: str
    arxiv_id: Optional[str] = None
    title: str
    authors: List[str] = []
    abstract: Optional[str] = None
    publication_date: Optional[datetime] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    status: Optional[str] = None


class PaperListResponse(BaseModel):
    papers: List[PaperResponse]
    total: int
    skip: int
    limit: int


# Entity-related schemas
class EntityResponse(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    paper_id: str


class EntityListResponse(BaseModel):
    entities: List[EntityResponse]
    total: int


# Agent-related schemas
class AgentQueryRequest(BaseModel):
    query: str
    paper_ids: Optional[List[str]] = None
    agent_type: str = Field(..., description="synthesizer, critic, or connector")


class AgentResponse(BaseModel):
    response: str
    sources: List[str]
    confidence: float
    agent_type: str
    processing_time: float


# Graph-related schemas
class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    properties: Dict[str, Any]


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    properties: Dict[str, Any]


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class GraphQueryRequest(BaseModel):
    entity_name: Optional[str] = None
    paper_id: Optional[str] = None
    depth: int = Field(default=2, ge=1, le=5)
    limit: int = Field(default=100, ge=1, le=1000)


# Search-related schemas
class SearchRequest(BaseModel):
    query: str
    entity_type: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)


class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    query: str


# Multi-agent system schemas
class MultiAgentRequest(BaseModel):
    query: str
    paper_ids: Optional[List[str]] = None
    agents: List[str] = Field(..., description="List of agent types to use")
    workflow: Optional[str] = Field(default="sequential", description="Workflow type")


class MultiAgentResponse(BaseModel):
    responses: List[AgentResponse]
    workflow_id: str
    total_processing_time: float


# Error responses
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    status_code: int


# Health check schemas
class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Statistics schemas
class GraphStatistics(BaseModel):
    total_papers: int
    total_entities: int
    total_relationships: int
    node_types: Dict[str, int]
    relationship_types: Dict[str, int]


class SystemStatistics(BaseModel):
    graph: GraphStatistics
    vector_store: Dict[str, Any]
    processing_queue: Dict[str, Any]


# WebSocket schemas
class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ProcessingUpdate(BaseModel):
    processing_id: str
    status: ProcessingStatus
    progress: float = Field(ge=0.0, le=1.0)
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# File upload schemas
class FileUploadResponse(BaseModel):
    filename: str
    size: int
    upload_id: str
    status: str


# Citation schemas
class Citation(BaseModel):
    paper_id: str
    title: str
    authors: List[str]
    year: Optional[int] = None
    doi: Optional[str] = None


class CitationNetwork(BaseModel):
    paper_id: str
    citations: List[Citation]
    references: List[Citation]


# Analysis schemas
class AnalysisRequest(BaseModel):
    paper_ids: List[str]
    analysis_type: str = Field(
        ..., description="contradictions, assumptions, trends, or synthesis"
    )
    parameters: Optional[Dict[str, Any]] = None


class AnalysisResponse(BaseModel):
    analysis_type: str
    results: List[Dict[str, Any]]
    summary: str
    confidence: float
    sources: List[str]


# User and session schemas
class UserSession(BaseModel):
    user_id: str
    session_id: str
    created_at: datetime
    last_activity: datetime
    papers_processed: int = 0


class UserPreferences(BaseModel):
    user_id: str
    default_agents: List[str] = Field(default=["synthesizer", "critic"])
    graph_depth: int = Field(default=2, ge=1, le=5)
    search_limit: int = Field(default=20, ge=1, le=100)
    notifications_enabled: bool = True
