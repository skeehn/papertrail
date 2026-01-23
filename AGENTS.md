# AGENTS.md - PaperTrail Development Guide

This file contains comprehensive guidelines for PaperTrail development. Follow these rules when making changes to maintain code quality, consistency, and reliability.

## 🚀 Build/Lint/Test Commands

### Backend (Python/FastAPI)

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000

# Format code (Black)
black app/ tests/ scripts/

# Sort imports (isort)
isort app/ tests/ scripts/

# Type check (mypy)
mypy app/

# Lint (flake8)
flake8 app/ tests/ scripts/

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/api/test_papers_endpoints.py -v

# Run single test function
pytest tests/api/test_papers_endpoints.py::test_get_paper_by_id -v

# Run integration tests only
pytest tests/integration/ -v

# Run tests with coverage
pytest --cov=app --cov-report=html

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Debug failing tests
pytest -xvs --tb=short

# Run tests with Redis cache enabled
export REDIS_URL=redis://localhost:6379
pytest tests/api/test_agents_endpoints.py
```

### Frontend (Next.js/TypeScript)

```bash
# Install dependencies
cd frontend
npm install

# Development server
npm run dev

# Build for production
npm run build

# Lint and fix
npm run lint

# Type check
npx tsc --noEmit

# Run tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with UI
npm run test:ui

# Format code (if prettier configured)
npx prettier --write src/
```

### End-to-End Testing

```bash
# Full E2E test suite
npm run test:e2e

# Specific E2E test
npx playwright test tests/e2e/chat-interaction.spec.ts

# E2E tests with UI
npx playwright test --ui
```

### Database & Services

```bash
# Test all connections
cd backend
python scripts/test_connections.py

# Test individual services
python scripts/test_services.py

# Reset Neo4j database
# Connect to Neo4j browser and run:
# MATCH (n) DETACH DELETE n;

# Clear Pinecone index
# Use Pinecone console or:
python3 -c "from pinecone import Pinecone; pc = Pinecone(api_key='YOUR_KEY'); pc.Index('papertrail').delete(delete_all=True)"

# Clear Redis cache
redis-cli FLUSHALL
```

## 📋 Code Style Guidelines

### Python Backend Style

#### 1. Imports
```python
# Standard library imports first
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

# Third-party imports
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Local imports (alphabetical, with blank line separator)
from app.core.config import settings
from app.core.logging import get_logger
from app.database.neo4j_client import neo4j_client
from app.services.pinecone_store import pinecone_store
```

**Rules:**
- Use absolute imports (`from app.services.xyz import ABC`)
- Group imports: stdlib → third-party → local
- One import per line
- Use `isort` to sort imports automatically
- No wildcard imports (`from xyz import *`)

#### 2. Type Hints
```python
from typing import Any, Dict, List, Optional, Union

# Use descriptive types
def process_paper(paper_id: str, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process a single paper by ID."""
    pass

# Use generics for collections
def get_similar_papers(query: str, limit: int = 10) -> List[Dict[str, str]]:
    pass

# Use Union for multiple possible types
def validate_input(data: Union[str, Dict[str, Any]]) -> bool:
    pass

# Use dataclass for structured data
@dataclass
class PaperMetadata:
    title: str
    authors: List[str]
    abstract: str
    published_date: Optional[str] = None
```

**Rules:**
- Type hint ALL function parameters and return values
- Use `Optional[X]` instead of `X | None`
- Use `Union[X, Y]` for multiple types
- Use descriptive type aliases for complex types
- Use `mypy --strict` for maximum type safety

#### 3. Error Handling
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

async def process_paper(paper_id: str) -> Dict[str, Any]:
    """Process a paper with comprehensive error handling."""
    try:
        # Validate input
        if not paper_id:
            raise ValueError("paper_id cannot be empty")

        # Log operation start
        logger.info("Starting paper processing", paper_id=paper_id)

        # Core logic here
        result = await _process_paper_logic(paper_id)

        # Log success
        logger.info("Paper processed successfully", paper_id=paper_id)
        return result

    except ValueError as e:
        logger.warning("Invalid input for paper processing", paper_id=paper_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error("Failed to process paper", paper_id=paper_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

**Rules:**
- Use specific exception types (ValueError, KeyError, etc.)
- Log errors with structured data (`paper_id=paper_id`)
- Include `exc_info=True` for unexpected errors
- Use `HTTPException` for API errors
- Never expose internal error details to clients

#### 4. Async/Await Patterns
```python
# Async function naming
async def get_relevant_papers(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Asynchronously retrieve relevant papers."""
    pass

# Use asyncio.gather for concurrent operations
async def process_multiple_papers(paper_ids: List[str]) -> List[Dict[str, Any]]:
    """Process multiple papers concurrently."""
    tasks = [process_paper(paper_id) for paper_id in paper_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle exceptions in results
    processed_results = []
    for paper_id, result in zip(paper_ids, results):
        if isinstance(result, Exception):
            logger.error("Failed to process paper", paper_id=paper_id, error=str(result))
            continue
        processed_results.append(result)

    return processed_results

# Use semaphore for rate limiting
async def bulk_index_papers(paper_ids: List[str]) -> None:
    """Index papers with controlled concurrency."""
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent

    async def index_with_limit(paper_id: str):
        async with semaphore:
            return await index_single_paper(paper_id)

    tasks = [index_with_limit(paper_id) for paper_id in paper_ids]
    await asyncio.gather(*tasks)
```

**Rules:**
- All I/O operations must be async
- Use `asyncio.gather()` for concurrent operations
- Use semaphores for rate limiting
- Handle exceptions in gathered results
- Name async functions descriptively

#### 5. Logging
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

class PaperService:
    def __init__(self):
        self.logger = get_logger("paper_service")

    async def process_paper(self, paper_id: str) -> Dict[str, Any]:
        """Process a paper with structured logging."""
        self.logger.info("Starting paper processing", paper_id=paper_id)

        # Log with context
        self.logger.debug("Downloading PDF", paper_id=paper_id, url="https://arxiv.org/pdf/...")

        # Log errors with full context
        try:
            result = await self._download_and_process(paper_id)
        except Exception as e:
            self.logger.error(
                "Paper processing failed",
                paper_id=paper_id,
                error=str(e),
                stage="download",
                duration_seconds=10.5
            )
            raise

        self.logger.info(
            "Paper processed successfully",
            paper_id=paper_id,
            entities_found=len(result.get("entities", [])),
            processing_time_seconds=45.2
        )

        return result
```

**Rules:**
- Use structured logging with `structlog`
- Include relevant context in every log message
- Log at appropriate levels: DEBUG, INFO, WARNING, ERROR
- Use consistent field names (`paper_id`, `user_id`, etc.)
- Log performance metrics and counts

#### 6. Database Operations
```python
from app.database.neo4j_client import neo4j_client

class GraphService:
    """Service for graph database operations."""

    async def create_paper_node(self, paper_data: Dict[str, Any]) -> str:
        """Create a paper node in Neo4j."""
        query = """
        MERGE (p:Paper {arxiv_id: $arxiv_id})
        SET p.title = $title,
            p.abstract = $abstract,
            p.authors = $authors,
            p.created_at = datetime(),
            p.updated_at = datetime()
        RETURN p.arxiv_id as paper_id
        """

        try:
            async with neo4j_client.get_session() as session:
                result = await session.run(query, paper_data)
                record = await result.single()
                return record["paper_id"]
        except Exception as e:
            logger.error("Failed to create paper node", arxiv_id=paper_data.get("arxiv_id"), error=str(e))
            raise

    async def get_related_papers(self, paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find papers related to the given paper."""
        query = """
        MATCH (p1:Paper {arxiv_id: $paper_id})-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(p2:Paper)
        WHERE p1 <> p2
        RETURN p2.arxiv_id as arxiv_id, p2.title as title, count(*) as shared_entities
        ORDER BY shared_entities DESC
        LIMIT $limit
        """

        async with neo4j_client.get_session() as session:
            result = await session.run(query, paper_id=paper_id, limit=limit)
            return [dict(record) async for record in result]
```

**Rules:**
- Use async database operations
- Always use parameterized queries
- Include error handling and logging
- Use meaningful variable names in Cypher queries
- Close sessions properly with `async with`

#### 7. API Endpoints
```python
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter()

class PaperSearchRequest(BaseModel):
    """Request model for paper search."""
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)
    categories: Optional[List[str]] = Field(default=None)

class PaperResponse(BaseModel):
    """Response model for paper data."""
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    published_date: Optional[str] = None

@router.get("/papers/{paper_id}", response_model=PaperResponse)
async def get_paper(paper_id: str) -> PaperResponse:
    """Get a paper by its arXiv ID."""
    try:
        paper = await paper_service.get_paper_by_id(paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        return PaperResponse(**paper)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get paper", paper_id=paper_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/search", response_model=List[PaperResponse])
async def search_papers(request: PaperSearchRequest) -> List[PaperResponse]:
    """Search for papers matching the query."""
    try:
        papers = await search_service.semantic_search(
            query=request.query,
            limit=request.limit,
            categories=request.categories
        )
        return [PaperResponse(**paper) for paper in papers]
    except Exception as e:
        logger.error("Paper search failed", query=request.query, error=str(e))
        raise HTTPException(status_code=500, detail="Search failed")
```

**Rules:**
- Use Pydantic models for request/response validation
- Include comprehensive field validation
- Use appropriate HTTP status codes
- Include detailed error messages
- Log all API operations

### Frontend (Next.js/TypeScript) Style

#### 1. Component Structure
```typescript
// components/PaperCard.tsx
import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface PaperCardProps {
  paper: {
    arxiv_id: string;
    title: string;
    authors: string[];
    abstract: string;
  };
  onSelect?: (paperId: string) => void;
}

export function PaperCard({ paper, onSelect }: PaperCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <CardTitle className="text-lg font-semibold line-clamp-2">
          {paper.title}
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          {paper.authors.join(', ')}
        </p>
      </CardHeader>
      <CardContent>
        <p className="text-sm line-clamp-3">
          {paper.abstract}
        </p>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-sm text-blue-600 hover:underline mt-2"
        >
          {isExpanded ? 'Show less' : 'Show more'}
        </button>
      </CardContent>
    </Card>
  );
}
```

#### 2. API Integration
```typescript
// hooks/use-papers.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export function usePapers(limit = 20) {
  return useQuery({
    queryKey: ['papers', limit],
    queryFn: async () => {
      const response = await fetch(`/api/papers?limit=${limit}`);
      if (!response.ok) {
        throw new Error('Failed to fetch papers');
      }
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useSearchPapers() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ query, limit }: { query: string; limit: number }) => {
      const response = await fetch('/api/search/semantic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, limit }),
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      return response.json();
    },
    onSuccess: (data) => {
      // Cache search results
      queryClient.setQueryData(['search', data.query], data);
    },
  });
}
```

#### 3. Type Safety
```typescript
// types/paper.ts
export interface Paper {
  id: string;
  arxiv_id: string;
  title: string;
  authors: string[];
  abstract: string;
  published_date?: string;
  categories?: string[];
}

export interface SearchRequest {
  query: string;
  limit?: number;
  entity_type?: string;
}

export interface SearchResponse {
  results: Array<{
    id: string;
    text: string;
    metadata: Record<string, any>;
    score: number;
  }>;
  total: number;
  query: string;
}

// API function with proper typing
export async function searchPapers(request: SearchRequest): Promise<SearchResponse> {
  const response = await fetch('/api/search/semantic', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`);
  }

  return response.json();
}
```

## 🧪 Testing Guidelines

### Backend Testing
```python
# tests/api/test_papers_endpoints.py
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_get_paper_success(client: AsyncClient):
    """Test successful paper retrieval."""
    # Arrange
    paper_id = "1706.03762"

    # Act
    response = await client.get(f"/api/v1/papers/{paper_id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["arxiv_id"] == paper_id
    assert "title" in data
    assert "authors" in data

@pytest.mark.asyncio
async def test_get_paper_not_found(client: AsyncClient):
    """Test paper retrieval for non-existent paper."""
    response = await client.get("/api/v1/papers/nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_search_papers_with_query(client: AsyncClient):
    """Test semantic search functionality."""
    search_request = {
        "query": "transformer attention mechanism",
        "limit": 5
    }

    response = await client.post("/api/v1/search/semantic", json=search_request)

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data
    assert isinstance(data["results"], list)
```

### Frontend Testing
```typescript
// __tests__/components/PaperCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { PaperCard } from '@/components/PaperCard';

const mockPaper = {
  arxiv_id: '1706.03762',
  title: 'Attention Is All You Need',
  authors: ['Ashish Vaswani', 'Noam Shazeer'],
  abstract: 'The dominant sequence transduction models...',
};

describe('PaperCard', () => {
  it('renders paper information correctly', () => {
    render(<PaperCard paper={mockPaper} />);

    expect(screen.getByText(mockPaper.title)).toBeInTheDocument();
    expect(screen.getByText(mockPaper.authors.join(', '))).toBeInTheDocument();
    expect(screen.getByText(mockPaper.abstract)).toBeInTheDocument();
  });

  it('expands abstract when show more is clicked', () => {
    render(<PaperCard paper={mockPaper} />);

    const showMoreButton = screen.getByText('Show more');
    fireEvent.click(showMoreButton);

    expect(screen.getByText('Show less')).toBeInTheDocument();
  });

  it('calls onSelect when provided', () => {
    const mockOnSelect = jest.fn();
    render(<PaperCard paper={mockPaper} onSelect={mockOnSelect} />);

    const card = screen.getByRole('button');
    fireEvent.click(card);

    expect(mockOnSelect).toHaveBeenCalledWith(mockPaper.arxiv_id);
  });
});

// __tests__/hooks/use-papers.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { usePapers } from '@/hooks/use-papers';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('usePapers', () => {
  it('fetches papers successfully', async () => {
    const { result } = renderHook(() => usePapers(10), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
    expect(Array.isArray(result.current.data)).toBe(true);
  });
});
```

## 🔧 Development Workflow

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/add-paper-recommendations

# Make changes with proper commits
git add .
git commit -m "feat: add paper recommendation service

- Add recommendation algorithm based on citation patterns
- Include similarity scoring for related papers
- Add API endpoint for recommendations"

# Run tests before pushing
pytest tests/ -v
npm test

# Push and create PR
git push origin feature/add-paper-recommendations
```

### Code Review Checklist
- [ ] All tests pass (`pytest` and `npm test`)
- [ ] Code is formatted (`black`, `isort`, `prettier`)
- [ ] Type checking passes (`mypy`, `tsc`)
- [ ] Linting passes (`flake8`, `eslint`)
- [ ] Documentation updated
- [ ] No secrets committed
- [ ] Proper error handling
- [ ] Logging added for new features
- [ ] API endpoints documented

### Performance Guidelines
- Use async operations for all I/O
- Implement caching for expensive operations
- Use pagination for large result sets
- Monitor memory usage in PDF processing
- Limit concurrent operations with semaphores

## 🚨 Critical Rules

### Security
- Never log sensitive data (API keys, passwords)
- Validate all user inputs
- Use HTTPS for production
- Implement rate limiting
- Sanitize database queries

### Reliability
- Handle all exceptions gracefully
- Use timeouts for external API calls
- Implement circuit breakers for unstable services
- Log errors with full context
- Monitor key metrics (response times, error rates)

### Maintainability
- Write self-documenting code
- Use descriptive variable names
- Keep functions small and focused
- Add docstrings to all public functions
- Use type hints everywhere

## 📈 Enhanced Functionality

### Multi-Agent Research Workflow
The system supports sophisticated research workflows through specialized agents:

#### Synthesizer Agent
- **Purpose**: Synthesize information from multiple papers
- **Capabilities**: Paper summarization, claim extraction, theme identification, methodology analysis
- **Usage**: Complex questions requiring multi-paper analysis

#### Critic Agent
- **Purpose**: Critical analysis and quality assessment
- **Capabilities**: Assumption detection, contradiction identification, weakness analysis
- **Usage**: Peer review, methodology critique, research gap identification

#### Connector Agent
- **Purpose**: Find relationships and connections across papers
- **Capabilities**: Citation analysis, semantic similarity, research trend mapping
- **Usage**: Literature mapping, related work discovery

### GraphRAG Architecture
PaperTrail implements a sophisticated Graph Retrieval-Augmented Generation system:

```
User Query → Semantic Search → Graph Traversal → Multi-Hop Reasoning → Synthesized Answer

1. Vector Search: Find relevant papers using Pinecone
2. Graph Expansion: Traverse Neo4j relationships to find connected papers
3. Entity Linking: Connect concepts across papers via knowledge graph
4. Multi-Agent Analysis: Use specialized agents for different analysis types
5. Answer Synthesis: Combine insights from multiple sources
```

### Advanced Features

#### Real-time Paper Processing
```python
# Upload and process a new paper
response = await client.post("/api/v1/papers/upload",
    files={"file": pdf_file},
    data={"arxiv_id": "2301.12345"}
)

# Monitor processing status
status = await client.get(f"/api/v1/papers/{processing_id}/status")
```

#### Graph Exploration
```python
# Find papers connected through shared entities
related = await client.get("/api/v1/graph/related-papers",
    params={"paper_id": "1706.03762", "depth": 2}
)

# Get research trends
trends = await client.get("/api/v1/insights/trends",
    params={"topic": "transformers", "months": 24}
)
```

#### Agent Collaboration
```python
# Multi-agent analysis
analysis = await client.post("/api/v1/agents/collaborate", json={
    "query": "How have transformer architectures evolved?",
    "agents": ["synthesizer", "critic", "connector"],
    "strategy": "sequential"  # or "parallel"
})
```

## 🔄 Continuous Integration

### Automated Testing Pipeline
```bash
# Run full test suite
make test-all

# Run backend tests with coverage
make test-backend

# Run frontend tests
make test-frontend

# Run integration tests
make test-integration

# Lint and format all code
make lint-all
```

### Performance Monitoring
- **Response Times**: Track API endpoint latency
- **Vector Search**: Monitor Pinecone query performance
- **Graph Queries**: Track Neo4j query execution times
- **Agent Performance**: Monitor agent task completion rates

### Error Tracking
- Structured error logging with context
- Automated error reporting and alerting
- Performance regression detection
- Memory usage monitoring for PDF processing

## 🚀 Deployment & Scaling

### Production Configuration
```bash
# Environment variables for production
export ENVIRONMENT=production
export LOG_LEVEL=INFO
export MAX_CONCURRENT_PROCESSES=10
export REDIS_URL=redis://prod-redis:6379
export NEO4J_URI=neo4j+s://prod-cluster.databases.neo4j.io
export PINECONE_INDEX_NAME=papertrail-prod
```

### Horizontal Scaling
- **Backend**: Multiple FastAPI instances behind load balancer
- **Vector Store**: Pinecone serverless scaling
- **Graph DB**: Neo4j cluster with read replicas
- **Cache**: Redis cluster for session and result caching

### Monitoring & Observability
- **Metrics**: Prometheus metrics for all services
- **Logging**: Structured logging with correlation IDs
- **Tracing**: Distributed tracing for complex queries
- **Alerts**: Automated alerts for service degradation

This guide ensures PaperTrail remains a high-quality, maintainable, and scalable research platform. Follow these guidelines diligently! 🎯</content>
<parameter name="filePath">/Users/kstephenkeehn/paper/papertrail/AGENTS.md