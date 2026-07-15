"""Pinecone vector store for paper embeddings"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from app.core import user_config
from app.core.logging import get_logger

logger = get_logger("pinecone")

try:
    from pinecone import Pinecone, ServerlessSpec

    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    Pinecone = None


class PineconeStore:
    """Pinecone vector store for paper embeddings"""

    def __init__(self):
        self._client: Optional[Any] = None
        self._index: Optional[Any] = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to Pinecone. Optional — the app runs fine without it."""
        api_key = user_config.get_key("PINECONE_API_KEY")
        if not PINECONE_AVAILABLE or not api_key:
            logger.info(
                "Pinecone not configured - semantic search will fall back to keywords"
            )
            self._connected = False
            return False

        host = user_config.get_key("PINECONE_HOST")
        index_name = user_config.get_key("PINECONE_INDEX_NAME")
        try:
            self._client = Pinecone(api_key=api_key)

            if host:
                self._index = self._client.Index(host=host)
            elif index_name:
                self._index = self._client.Index(index_name)
            else:
                logger.info("Pinecone key set but no index/host configured")
                self._connected = False
                return False

            self._connected = True
            logger.info("Connected to Pinecone", index=index_name, host=host)
            return True

        except Exception as e:
            logger.error("Failed to connect to Pinecone", error=str(e))
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Pinecone"""
        self._connected = False
        self._client = None
        self._index = None
        logger.info("Disconnected from Pinecone")

    @property
    def is_connected(self) -> bool:
        """Check if connected to Pinecone"""
        return self._connected and self._index is not None

    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: Optional[List[List[float]]] = None,
    ) -> List[str]:
        """Add documents to Pinecone using server-side integrated embeddings.

        The ``papertrail`` index has an integrated model (llama-text-embed-v2)
        that embeds the ``text`` field on upsert — no local embedding model
        (sentence-transformers / torch) is required.
        """
        if not self.is_connected:
            logger.warning("Pinecone not connected, skipping document addition")
            return []

        try:
            records: List[Dict[str, Any]] = []
            ids: List[str] = []
            for i, doc in enumerate(documents):
                meta = doc.get("metadata", {}) or {}
                arxiv_id = meta.get("arxiv_id") or doc.get("id") or f"doc_{i}"
                rec_id = doc.get("id") or f"paper_{arxiv_id}"
                ids.append(rec_id)
                authors = meta.get("authors", [])
                if isinstance(authors, list):
                    authors = ", ".join(str(a) for a in authors)
                records.append(
                    {
                        "_id": rec_id,
                        # embedded field (per the index field_map)
                        "text": (doc.get("text") or "")[:8000],
                        "type": "paper",
                        "arxiv_id": str(arxiv_id),
                        "title": meta.get("title", ""),
                        "authors": str(authors or ""),
                        "abstract": (meta.get("abstract") or doc.get("text") or "")[
                            :4000
                        ],
                    }
                )

            if records:
                self._index.upsert_records(namespace="papers", records=records)

            logger.info(f"Upserted {len(ids)} documents to Pinecone (integrated embed)")
            return ids

        except Exception as e:
            logger.error("Failed to add documents to Pinecone", error=str(e))
            return []

    async def search(
        self,
        query_text: Optional[str] = None,
        top_k: int = 10,
        k: Optional[int] = None,
        filter: Optional[Dict[str, Any]] = None,
        query_embedding: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Semantic search via the index's integrated embedding model."""
        if not self.is_connected:
            logger.warning("Pinecone not connected, returning empty results")
            return []

        if k:
            top_k = k
        if not query_text:
            logger.warning("No query text provided for search")
            return []

        try:
            resp = self._index.search(
                namespace="papers",
                query={"inputs": {"text": query_text}, "top_k": top_k},
                fields=["title", "abstract", "authors", "arxiv_id", "type", "text"],
            )
            data = resp.to_dict() if hasattr(resp, "to_dict") else dict(resp)
            hits = (data.get("result") or {}).get("hits") or []

            matches = []
            for h in hits:
                hit_id = h.get("_id") or h.get("id_") or h.get("id") or ""
                score = h.get("_score") or h.get("score_") or h.get("score") or 0.0
                fields = h.get("fields", {}) or {}
                matches.append(
                    {
                        "id": hit_id,
                        "score": score,
                        "metadata": {
                            "type": fields.get("type", "paper"),
                            "arxiv_id": fields.get("arxiv_id", ""),
                            "title": fields.get("title", ""),
                            "authors": fields.get("authors", ""),
                            "abstract": fields.get("abstract", ""),
                        },
                        "text": fields.get("text", ""),
                    }
                )

            logger.info(f"Found {len(matches)} similar documents")
            return matches

        except Exception as e:
            logger.error("Failed to search Pinecone", error=str(e))
            return []

    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document from Pinecone"""
        if not self.is_connected:
            return False

        try:
            self._index.delete(ids=[doc_id], namespace="papers")
            logger.info(f"Deleted document {doc_id} from Pinecone")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}", error=str(e))
            return False

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        if not self.is_connected:
            return None

        try:
            result = self._index.fetch(ids=[doc_id], namespace="papers")
            vectors = result.get("vectors", {})
            if doc_id in vectors:
                vector_data = vectors[doc_id]
                return {
                    "id": doc_id,
                    "metadata": vector_data.get("metadata", {}),
                    "score": 1.0,
                }
            return None

        except Exception as e:
            logger.error(f"Failed to fetch document {doc_id}", error=str(e))
            return None

    async def list_documents(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List all documents"""
        if not self.is_connected:
            return []

        try:
            stats = self._index.describe_index_stats(namespace="papers")
            total_count = stats.get("namespaces", {}).get("papers", {}).get("count", 0)

            documents = []
            if total_count > 0:
                query_params = {
                    "vector": [0.0] * 1024,
                    "top_k": min(limit, 1000),
                    "namespace": "papers",
                    "include_metadata": True,
                }
                results = self._index.query(**query_params)
                for match in results.get("matches", []):
                    documents.append(
                        {
                            "id": match.get("id"),
                            "metadata": match.get("metadata", {}),
                            "score": match.get("score", 0.0),
                        }
                    )

            return documents

        except Exception as e:
            logger.error("Failed to list documents", error=str(e))
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        if not self.is_connected:
            return {
                "total_documents": 0,
                "connected": False,
            }

        try:
            stats = self._index.describe_index_stats()
            namespaces = stats.get("namespaces", {})
            papers_count = namespaces.get("papers", {}).get("count", 0)

            return {
                "total_documents": papers_count,
                "connected": True,
                "index_name": user_config.get_key("PINECONE_INDEX_NAME"),
                "host": user_config.get_key("PINECONE_HOST"),
                "dimension": 1024,
            }

        except Exception as e:
            logger.error("Failed to get Pinecone stats", error=str(e))
            return {
                "total_documents": 0,
                "connected": True,
                "error": str(e),
            }


pinecone_store = PineconeStore()
