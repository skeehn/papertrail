"""Batch indexing service for arXiv papers"""

import asyncio
import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.database.neo4j_client import Neo4jClient
from app.database.pinecone_store import pinecone_store
from app.services.arxiv_client import arxiv_client
from app.services.entity_extractor import EntityExtractor
from app.services.graph_builder import GraphBuilder
from app.services.pdf_processor import PDFProcessor


class ProcessingStatus(str, Enum):
    """Status of paper processing"""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING_PDF = "processing_pdf"
    EXTRACTING_ENTITIES = "extracting_entities"
    BUILDING_GRAPH = "building_graph"
    INDEXING_VECTORS = "indexing_vectors"
    COMPLETED = "completed"
    FAILED = "failed"


class BatchIndexer:
    """Service for batch indexing arXiv papers"""

    def __init__(self):
        self.logger = get_logger("batch_indexer")
        self.pdf_processor = PDFProcessor()
        self.entity_extractor = EntityExtractor()
        self.graph_builder = GraphBuilder()
        self.jobs = {}  # Store job status

    async def index_papers_by_ids(
        self, arxiv_ids: List[str], job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Index multiple papers by their arXiv IDs

        Args:
            arxiv_ids: List of arXiv IDs to index
            job_id: Optional job ID for tracking

        Returns:
            Job status dictionary
        """
        if not job_id:
            job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Initialize job status
        self.jobs[job_id] = {
            "job_id": job_id,
            "total_papers": len(arxiv_ids),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "status": "running",
            "papers": {},
            "started_at": datetime.now().isoformat(),
            "errors": [],
        }

        self.logger.info(
            "Starting batch indexing job", job_id=job_id, total=len(arxiv_ids)
        )

        # Process papers with controlled concurrency
        semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_PROCESSES)

        async def process_with_semaphore(arxiv_id: str):
            async with semaphore:
                return await self._index_single_paper(arxiv_id, job_id)

        # Process all papers
        results = await asyncio.gather(
            *[process_with_semaphore(arxiv_id) for arxiv_id in arxiv_ids],
            return_exceptions=True,
        )

        # Update job status
        for arxiv_id, result in zip(arxiv_ids, results):
            self.jobs[job_id]["processed"] += 1

            if isinstance(result, Exception):
                self.jobs[job_id]["failed"] += 1
                self.jobs[job_id]["errors"].append(
                    {"arxiv_id": arxiv_id, "error": str(result)}
                )
            elif result and result.get("status") == "completed":
                self.jobs[job_id]["successful"] += 1
            else:
                self.jobs[job_id]["failed"] += 1

        self.jobs[job_id]["status"] = "completed"
        self.jobs[job_id]["completed_at"] = datetime.now().isoformat()

        self.logger.info(
            "Batch indexing job completed",
            job_id=job_id,
            successful=self.jobs[job_id]["successful"],
            failed=self.jobs[job_id]["failed"],
        )

        return self.jobs[job_id]

    async def _index_single_paper(self, arxiv_id: str, job_id: str) -> Dict[str, Any]:
        """Index a single paper"""
        paper_status = {
            "arxiv_id": arxiv_id,
            "status": ProcessingStatus.PENDING,
            "error": None,
        }

        self.jobs[job_id]["papers"][arxiv_id] = paper_status

        try:
            # 1. Download PDF
            paper_status["status"] = ProcessingStatus.DOWNLOADING
            pdf_path = arxiv_client.download_paper(arxiv_id)

            if not pdf_path or not os.path.exists(pdf_path):
                raise Exception(f"Failed to download PDF for {arxiv_id}")

            # 2. Get paper metadata
            paper_metadata = arxiv_client.get_paper_by_id(arxiv_id)

            if not paper_metadata:
                raise Exception(f"Failed to fetch metadata for {arxiv_id}")

            # 3. Process PDF
            paper_status["status"] = ProcessingStatus.PROCESSING_PDF
            pdf_content = self.pdf_processor.process_pdf(pdf_path)

            if not pdf_content:
                raise Exception(f"Failed to process PDF for {arxiv_id}")

            # 4. Extract entities
            paper_status["status"] = ProcessingStatus.EXTRACTING_ENTITIES
            full_text = pdf_content.get("full_text", "")
            entities = self.entity_extractor.extract_entities(full_text)

            # 5. Build graph
            paper_status["status"] = ProcessingStatus.BUILDING_GRAPH

            # Create paper node in Neo4j
            paper_node = {
                "arxiv_id": arxiv_id,
                "title": paper_metadata["title"],
                "abstract": paper_metadata["abstract"],
                "authors": paper_metadata["authors"],
                "categories": paper_metadata["categories"],
                "published_date": paper_metadata["published_date"],
                "pdf_url": paper_metadata["pdf_url"],
            }

            # Use graph builder to create nodes and relationships
            self.graph_builder.create_paper_node(paper_node)

            for entity in entities:
                self.graph_builder.create_entity_node(entity)
                self.graph_builder.create_relationship(
                    arxiv_id,
                    entity["name"],
                    "MENTIONS",
                    {"confidence": entity.get("confidence", 0.5)},
                )

            # 6. Index in vector store
            paper_status["status"] = ProcessingStatus.INDEXING_VECTORS

            # Add paper abstract to vector store
            documents = [
                {
                    "id": f"paper_{arxiv_id}",
                    "text": f"{paper_metadata['title']}. {paper_metadata['abstract']}",
                    "metadata": {
                        "arxiv_id": arxiv_id,
                        "type": "paper",
                        "title": paper_metadata["title"],
                        "authors": ",".join(paper_metadata["authors"][:3]),
                        "published_date": paper_metadata["published_date"],
                        "categories": ",".join(paper_metadata["categories"]),
                    },
                }
            ]

            # Add high-confidence entities to vector store
            for entity in entities:
                if entity.get("confidence", 0) > 0.7:
                    documents.append(
                        {
                            "id": f"entity_{arxiv_id}_{entity['name']}",
                            "text": f"{entity['name']}: {entity.get('description', '')}",
                            "metadata": {
                                "arxiv_id": arxiv_id,
                                "type": "entity",
                                "entity_type": entity.get("type", "unknown"),
                                "entity_name": entity["name"],
                            },
                        }
                    )

            # Add to Pinecone
            pinecone_store.add_documents(documents)

            # Mark as completed
            paper_status["status"] = ProcessingStatus.COMPLETED
            paper_status["entities_count"] = len(entities)
            paper_status["indexed_vectors"] = len(documents)

            self.logger.info("Paper indexed successfully", arxiv_id=arxiv_id)

            return paper_status

        except Exception as e:
            paper_status["status"] = ProcessingStatus.FAILED
            paper_status["error"] = str(e)
            self.logger.error("Failed to index paper", arxiv_id=arxiv_id, error=str(e))
            return paper_status

    async def index_papers_by_query(
        self, query: str, max_results: int = 50, categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search arXiv and index results

        Args:
            query: Search query
            max_results: Maximum papers to index
            categories: Filter by categories

        Returns:
            Job status dictionary
        """
        # Search for papers
        self.logger.info("Searching arXiv", query=query, max_results=max_results)
        papers = arxiv_client.search_papers(query, max_results, categories=categories)

        if not papers:
            self.logger.warning("No papers found", query=query)
            return {
                "status": "completed",
                "total_papers": 0,
                "successful": 0,
                "failed": 0,
            }

        # Extract arXiv IDs
        arxiv_ids = [paper["arxiv_id"] for paper in papers]

        # Index papers
        return await self.index_papers_by_ids(arxiv_ids)

    async def index_trending_papers(
        self, categories: List[str], days_back: int = 7, max_results: int = 50
    ) -> Dict[str, Any]:
        """
        Index trending papers from specific categories

        Args:
            categories: List of arXiv categories
            days_back: Number of days to look back
            max_results: Maximum papers to index

        Returns:
            Job status dictionary
        """
        self.logger.info(
            "Indexing trending papers", categories=categories, days_back=days_back
        )

        papers = arxiv_client.get_trending_papers(categories, days_back, max_results)

        if not papers:
            self.logger.warning("No trending papers found")
            return {
                "status": "completed",
                "total_papers": 0,
                "successful": 0,
                "failed": 0,
            }

        arxiv_ids = [paper["arxiv_id"] for paper in papers]
        return await self.index_papers_by_ids(arxiv_ids)

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a batch indexing job"""
        return self.jobs.get(job_id)

    def get_all_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Get all jobs"""
        return self.jobs

    async def index_ai_research_papers(self, max_results: int = 100) -> Dict[str, Any]:
        """
        Index a diverse set of AI research papers for demo purposes

        Returns:
            Job status dictionary
        """
        self.logger.info(
            "Indexing AI research papers for demo", max_results=max_results
        )

        # Define diverse research topics
        topics = [
            "large language models",
            "graph neural networks",
            "retrieval augmented generation",
            "transformers attention mechanism",
            "few-shot learning",
            "reinforcement learning",
            "computer vision",
            "natural language processing",
            "multimodal learning",
            "neural architecture search",
        ]

        # Get papers per topic
        papers_per_topic = max(5, max_results // len(topics))

        all_arxiv_ids = set()

        for topic in topics:
            papers = arxiv_client.search_papers(
                query=topic,
                max_results=papers_per_topic,
                categories=["cs.AI", "cs.LG", "cs.CL", "cs.CV"],
            )

            for paper in papers:
                all_arxiv_ids.add(paper["arxiv_id"])

        # Limit to max_results
        arxiv_ids = list(all_arxiv_ids)[:max_results]

        self.logger.info(f"Found {len(arxiv_ids)} unique papers to index")

        # Index papers
        return await self.index_papers_by_ids(arxiv_ids)


# Global batch indexer instance
batch_indexer = BatchIndexer()


async def index_arxiv_papers(arxiv_ids: List[str]) -> Dict[str, Any]:
    """Index papers by arXiv IDs"""
    return await batch_indexer.index_papers_by_ids(arxiv_ids)


async def index_papers_by_search(query: str, max_results: int = 50) -> Dict[str, Any]:
    """Search and index papers"""
    return await batch_indexer.index_papers_by_query(query, max_results)


async def index_demo_papers(max_results: int = 100) -> Dict[str, Any]:
    """Index demo papers for AI research"""
    return await batch_indexer.index_ai_research_papers(max_results)
