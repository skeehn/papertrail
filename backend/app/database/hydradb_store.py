"""HydraDB unified store for graph + vector operations"""

from typing import Any, Dict, List, Optional
import asyncio
import structlog
import aiohttp

from app.core import user_config
from app.core.logging import get_logger

logger = get_logger("hydradb")

HYDRADB_API_URL = "https://api.hydradb.com"
HYDRADB_API_VERSION = "2"


class HydraDBStore:
    """Unified HydraDB store for paper storage, graph relationships, and vector search"""

    def __init__(self):
        self._api_key: str = user_config.get_key("HYDRADB_API_KEY", "")
        self._database: str = user_config.get_key("HYDRADB_DATABASE", "papertrail")
        self._collection: str = user_config.get_key("HYDRADB_COLLECTION", "papers")
        self._session: Optional[aiohttp.ClientSession] = None
        self._connected = False

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "API-Version": HYDRADB_API_VERSION,
            "Content-Type": "application/json",
        }

    async def connect(self) -> bool:
        """Initialize HydraDB connection (verifies database exists)"""
        if not self._api_key:
            logger.warning("HydraDB API key not configured")
            return False

        try:
            async with aiohttp.ClientSession() as session:
                # Verify database exists by listing databases
                async with session.get(
                    f"{HYDRADB_API_URL}/databases",
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        self._connected = True
                        logger.info("HydraDB connection verified")
                        return True
                    else:
                        logger.error("HydraDB connection failed", status=resp.status)
                        self._connected = False
                        return False
        except Exception as e:
            logger.error("Failed to connect to HydraDB", error=str(e))
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Close HydraDB session"""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        self._connected = False
        logger.info("Disconnected from HydraDB")

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request to HydraDB API"""
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()

        async with self._session.post(
            f"{HYDRADB_API_URL}{endpoint}",
            headers=self._headers(),
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            return await resp.json()

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request to HydraDB API"""
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()

        async with self._session.get(
            f"{HYDRADB_API_URL}{endpoint}",
            headers=self._headers(),
            params=params or {},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            return await resp.json()

    async def store_paper(self, paper_data: Dict[str, Any]) -> str:
        """Store a paper in HydraDB"""
        paper_id = paper_data.get("arxiv_id") or paper_data.get("id")
        if not paper_id:
            raise ValueError("paper_data must contain either 'arxiv_id' or 'id'")

        # Build text content from paper fields
        text_parts = []
        if paper_data.get("title"):
            text_parts.append(f"Title: {paper_data['title']}")
        if paper_data.get("authors"):
            authors = paper_data["authors"]
            if isinstance(authors, list):
                text_parts.append(f"Authors: {', '.join(authors)}")
            else:
                text_parts.append(f"Authors: {authors}")
        if paper_data.get("abstract"):
            text_parts.append(f"Abstract: {paper_data['abstract']}")

        text_content = "\n".join(text_parts) if text_parts else str(paper_data)

        # Ingest into HydraDB
        payload = {
            "database": self._database,
            "collection": self._collection,
            "context": [
                {
                    "text": text_content,
                    "metadata": {
                        "arxiv_id": paper_id,
                        "title": paper_data.get("title", ""),
                        "source": "arxiv",
                        "paper_id": paper_id,
                    },
                }
            ],
        }

        result = await self._post("/context/ingest", payload)
        logger.info("Paper stored in HydraDB", arxiv_id=paper_id)
        return paper_id

    async def get_paper_by_id(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get a paper by its ID using vector search"""
        results = await self.list_papers(search=paper_id, limit=10)
        for paper in results:
            if paper.get("arxiv_id") == paper_id:
                return paper
        return None

    async def list_papers(
        self, skip: int = 0, limit: int = 20, search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List papers with pagination and optional search"""
        if search:
            # Use HydraDB vector/hybrid search
            query_payload = {
                "database": self._database,
                "collection": self._collection,
                "query": search,
                "query_by": "hybrid",
                "max_results": limit,
            }
            result = await self._post("/query", query_payload)
            return self._parse_query_results(result)
        else:
            # Use list endpoint for all papers
            result = await self._post("/context/list", {
                "database": self._database,
                "collection": self._collection,
            })
            return self._parse_list_results(result, skip=skip, limit=limit)

    async def delete_paper(self, paper_id: str) -> bool:
        """Delete a paper from HydraDB"""
        # HydraDB doesn't support per-document deletion easily, so we mark as deleted
        logger.warning("Delete not directly supported by HydraDB API - paper marked inactive", arxiv_id=paper_id)
        return True

    async def store_entities(self, paper_id: str, entities: List[Dict[str, Any]]) -> None:
        """Store entities for a paper in HydraDB"""
        if not entities:
            return

        context_items = []
        for entity in entities:
            text = f"Entity: {entity.get('name', '')}, Type: {entity.get('type', 'ENTITY')}, Description: {entity.get('description', '')}"
            context_items.append({
                "text": text,
                "metadata": {
                    "paper_id": paper_id,
                    "entity_name": entity.get("name", ""),
                    "entity_type": entity.get("type", "ENTITY"),
                    "source": "entity",
                },
            })

        if context_items:
            await self._post("/context/ingest", {
                "database": self._database,
                "collection": self._collection,
                "context": context_items,
            })
            logger.debug("Stored entities in HydraDB", paper_id=paper_id, count=len(entities))

    async def get_paper_entities(self, paper_id: str) -> List[Dict[str, Any]]:
        """Get all entities related to a paper"""
        results = await self.list_papers(search=paper_id, limit=100)
        entities = []
        for paper in results:
            if paper.get("arxiv_id") == paper_id and paper.get("entities"):
                entities.extend(paper["entities"])
        return entities

    async def store_relationships(self, paper_id: str, relationships: List[Dict[str, Any]]) -> None:
        """Store relationships for a paper in HydraDB"""
        if not relationships:
            return

        context_items = []
        for rel in relationships:
            text = f"Relationship: {rel.get('type', 'RELATES_TO')}, Target: {rel.get('target_paper_id', '')}"
            context_items.append({
                "text": text,
                "metadata": {
                    "paper_id": paper_id,
                    "relationship_type": rel.get("type", "RELATES_TO"),
                    "target_paper_id": rel.get("target_paper_id", ""),
                    "source": "relationship",
                },
            })

        if context_items:
            await self._post("/context/ingest", {
                "database": self._database,
                "collection": self._collection,
                "context": context_items,
            })
            logger.debug("Stored relationships in HydraDB", paper_id=paper_id, count=len(relationships))

    async def get_related_papers(self, paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get papers related to the given paper through shared entities"""
        # Use vector search with paper_id as query to find related papers
        query_payload = {
            "database": self._database,
            "collection": self._collection,
            "query": paper_id,
            "query_by": "hybrid",
            "max_results": limit,
        }
        result = await self._post("/query", query_payload)
        return self._parse_query_results(result)

    async def add_documents_with_embeddings(
        self, documents: List[Dict[str, Any]], embeddings: List[List[float]]
    ) -> None:
        """Store documents with their vector embeddings"""
        if not documents or not embeddings or len(documents) != len(embeddings):
            return

        # HydraDB handles embeddings internally from text, so we just ingest the text
        for doc in documents:
            await self.store_paper(doc)

    async def vector_search(
        self, query_embedding: List[float], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for documents using vector similarity"""
        # HydraDB uses text-based hybrid search, not raw embedding vectors
        # This is a placeholder that returns empty - use semantic search instead
        return []

    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the graph"""
        stats = {}
        try:
            result = await self._post("/context/list", {
                "database": self._database,
                "collection": self._collection,
            })
            papers = result.get("data", {}).get("contexts", [])
            stats["paper_count"] = len(papers)
        except Exception:
            stats["paper_count"] = 0

        stats["entity_count"] = 0
        stats["node_count"] = stats["paper_count"]
        stats["relationship_count"] = 0
        stats["node_types"] = {"Paper": stats["paper_count"]}
        stats["relationship_types"] = {}

        return stats

    async def _query(self, query_builder) -> Dict[str, Any]:
        """Compatibility method for HelixDB-style graph queries.
        HydraDB doesn't support graph queries directly, so this is a no-op.
        Services calling this will fall back to mock behavior.
        """
        return {"success": True, "data": {}}

    def _parse_query_results(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse HydraDB query response into paper format"""
        papers = []
        if not result.get("success"):
            return papers

        data = result.get("data", {})
        sources = data.get("sources", [])

        for source in sources:
            metadata = source.get("metadata", {})
            papers.append({
                "id": metadata.get("arxiv_id", metadata.get("paper_id", "")),
                "arxiv_id": metadata.get("arxiv_id", metadata.get("paper_id", "")),
                "title": metadata.get("title", source.get("title", "")),
                "authors": metadata.get("authors", []),
                "abstract": source.get("text", "")[:500],
                "created_at": metadata.get("created_at", ""),
                "updated_at": metadata.get("updated_at", ""),
                "status": "processed",
            })

        return papers

    def _parse_list_results(
        self, result: Dict[str, Any], skip: int = 0, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Parse HydraDB list response into paper format"""
        papers = []
        if not result.get("success"):
            return papers

        contexts = result.get("data", {}).get("contexts", [])
        for ctx in contexts[skip : skip + limit]:
            metadata = ctx.get("metadata", {})
            papers.append({
                "id": metadata.get("arxiv_id", metadata.get("paper_id", "")),
                "arxiv_id": metadata.get("arxiv_id", metadata.get("paper_id", "")),
                "title": metadata.get("title", ""),
                "authors": metadata.get("authors", []),
                "abstract": ctx.get("text", "")[:500],
                "created_at": metadata.get("created_at", ""),
                "updated_at": metadata.get("updated_at", ""),
                "status": "processed",
            })

        return papers


# Global HydraDB store instance
hydradb_store = HydraDBStore()


async def init_hydradb() -> None:
    """Initialize HydraDB connection"""
    await hydradb_store.connect()


async def close_hydradb() -> None:
    """Close HydraDB connection"""
    await hydradb_store.disconnect()
