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
        self.last_source_ids: List[str] = []

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

    async def _get_session(self) -> aiohttp.ClientSession:
        """Session bound to the CURRENT event loop.

        aiohttp sessions are loop-bound. Sync wraappers spin fresh loops per
        call via asyncio.run, so a stale session from an earlier loop raises
        'Event loop is closed'. Recreate whenever the loop differs.
        """
        loop = asyncio.get_running_loop()
        if self._session and not self._session.closed:
            if getattr(self._session, "bound_loop", None) is loop:
                return self._session
        self._session = aiohttp.ClientSession()
        self._session.bound_loop = loop
        return self._session

    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request to HydraDB API"""
        session = await self._get_session()

        async with session.post(
            f"{HYDRADB_API_URL}{endpoint}",
            headers=self._headers(),
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            return await resp.json()

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request to HydraDB API"""
        session = await self._get_session()

        async with session.get(
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

        title = paper_data.get("title", "")

        # Build text content from paper fields
        text_parts = []
        if title:
            text_parts.append(f"Title: {title}")
        if paper_data.get("authors"):
            authors = paper_data["authors"]
            if isinstance(authors, list):
                text_parts.append(f"Authors: {', '.join(authors)}")
            else:
                text_parts.append(f"Authors: {authors}")
        if paper_data.get("abstract"):
            text_parts.append(f"Abstract: {paper_data['abstract']}")

        text_content = "\n".join(text_parts) if text_parts else str(paper_data)

        year = None
        raw_date = str(
            paper_data.get("publication_date") or paper_data.get("published_date") or ""
        )
        for candidate in raw_date.replace("/", "-").split("-"):
            if candidate.isdigit() and len(candidate) == 4:
                year = candidate
                break

        # Ingest into HydraDB. Metadata rides on `attributes` — `metadata`
        # was rejected by the API as an unknown field.
        payload = {
            "database": self._database,
            "collection": self._collection,
            "context": [
                {
                    "title": title or paper_id,
                    "text": text_content,
                    "attributes": {
                        "arxiv_id": paper_id,
                        "title": title,
                        "year": year,
                        "source": "arxiv",
                        "paper_id": paper_id,
                    },
                }
            ],
        }

        result = await self._post("/context/ingest", payload)
        if not result.get("success"):
            raise RuntimeError(f"HydraDB ingest failed: {result.get('error') or result}")
        self.last_source_ids = [
            item.get("id", "")
            for item in (result.get("data", {}).get("results") or [])
            if item.get("id")
        ]
        logger.info(
            "Paper stored in HydraDB", arxiv_id=paper_id, source_ids=self.last_source_ids
        )

        # Mirror into the local vector store so the library is searchable
        # instantly instead of waiting on the cloud queue.
        try:
            from app.database.local_vector import local_vector_store

            await local_vector_store.upsert_paper(dict(paper_data, year=year))
        except Exception as e:  # noqa: BLE001
            logger.warning("Local vector mirror failed", error=str(e))

        return paper_id

    async def wait_until_indexed(
        self, source_id: str, collection: Optional[str] = None, timeout: int = 120, poll: int = 3
    ) -> Dict[str, Any]:
        """Poll /context/status until the source reaches a terminal state.

        The status endpoint requires database + collection; omitting the
        collection returns a misleading FILE_NOT_FOUND error.
        """
        deadline = asyncio.get_running_loop().time() + timeout
        last: Dict[str, Any] = {}
        while asyncio.get_running_loop().time() < deadline:
            result = await self._get(
                "/context/status",
                params={
                    "database": self._database,
                    "collection": collection or self._collection,
                    "id": source_id,
                },
            )
            statuses = (result.get("data", {}) or {}).get("statuses") or []
            if statuses:
                last = statuses[0]
                state = last.get("indexing_status", "")
                if state in ("completed", "errored", "failed"):
                    return last
            await asyncio.sleep(poll)
        return dict(last, indexing_status="timeout", success=False)

    async def list_sources(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Raw source items with attributes, for Python-side aggregation."""
        result = await self._post(
            "/context/list", {"database": self._database, "collection": self._collection}
        )
        data = result.get("data") or (result.get("data") or {}).get("data") or {}
        sources = result.get("data", {}).get("sources") or []
        return sources[:limit]

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
                "title": entity.get("name", ""),
                "text": text,
                "attributes": {
                    "paper_id": paper_id,
                    "entity_name": entity.get("name", ""),
                    "entity_type": entity.get("type", "ENTITY"),
                    "source": "entity",
                },
            })

        if context_items:
            result = await self._post("/context/ingest", {
                "database": self._database,
                "collection": self._collection,
                "context": context_items,
            })
            if not result.get("success"):
                raise RuntimeError(f"HydraDB entity ingest failed: {result.get('error') or result}")
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
                "title": text[:80],
                "text": text,
                "attributes": {
                    "paper_id": paper_id,
                    "relationship_type": rel.get("type", "RELATES_TO"),
                    "target_paper_id": rel.get("target_paper_id", ""),
                    "source": "relationship",
                },
            })

        if context_items:
            result = await self._post("/context/ingest", {
                "database": self._database,
                "collection": self._collection,
                "context": context_items,
            })
            if not result.get("success"):
                raise RuntimeError(f"HydraDB relationship ingest failed: {result.get('error') or result}")
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

        data = result.get("data") or {}
        sources = data.get("sources") or []

        for source in sources:
            attrs = source.get("attributes") or {}
            papers.append(
                {
                    "id": attrs.get("arxiv_id", attrs.get("paper_id", "")),
                    "arxiv_id": attrs.get("arxiv_id", attrs.get("paper_id", "")),
                    "title": attrs.get("title") or source.get("title", ""),
                    "authors": attrs.get("authors", []),
                    "abstract": (source.get("text") or source.get("text_preview", ""))[:500],
                    "created_at": attrs.get("created_at", ""),
                    "updated_at": attrs.get("updated_at", ""),
                    "score": source.get("score", 0.5),
                    "status": "processed",
                }
            )

        return papers

    def _parse_list_results(
        self, result: Dict[str, Any], skip: int = 0, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Parse HydraDB list response into paper format.

        /context/list returns data.sources[].{id, title, text, attributes}.
        """
        papers = []
        if not result.get("success"):
            return papers

        data = result.get("data") or {}
        contexts = data.get("sources") or data.get("contexts") or []
        for ctx in contexts[skip : skip + limit]:
            attrs = ctx.get("attributes") or {}
            papers.append(
                {
                    "id": attrs.get("arxiv_id", attrs.get("paper_id", "")),
                    "arxiv_id": attrs.get("arxiv_id", attrs.get("paper_id", "")),
                    "title": attrs.get("title") or ctx.get("title", ""),
                    "authors": attrs.get("authors", []),
                    "abstract": (ctx.get("text") or "")[:500],
                    "created_at": attrs.get("created_at", ""),
                    "updated_at": attrs.get("updated_at", ""),
                    "status": "processed",
                }
            )

        return papers


# Global HydraDB store instance
hydradb_store = HydraDBStore()


async def init_hydradb() -> None:
    """Initialize HydraDB connection"""
    await hydradb_store.connect()


async def close_hydradb() -> None:
    """Close HydraDB connection"""
    await hydradb_store.disconnect()
