"""Pinecone vector store for paper embeddings"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from app.core.config import settings
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
        _index: Optional[Any] = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to Pinecone"""
        if not PINECONE_AVAILABLE or not settings.PINECONE_API_KEY:
            logger.warning("Pinecone not available - missing client or API key")
            return False

        try:
            self._client = Pinecone(api_key=settings.PINECONE_API_KEY)

            if settings.PINECONE_HOST:
                self._index = self._client.Index(host=settings.PINECONE_HOST)
            elif settings.PINECONE_INDEX_NAME:
                self._index = self._client.Index(settings.PINECONE_INDEX_NAME)

            self._connected = True
            logger.info(
                "Connected to Pinecone",
                index=settings.PINECONE_INDEX_NAME,
                host=settings.PINECONE_HOST,
            )
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
        """Add documents to Pinecone"""
        if not self.is_connected:
            logger.warning("Pinecone not connected, skipping document addition")
            return []

        try:
            ids = []
            vectors = []
            target_dimension = 1024  # Pinecone index dimension

            # Generate embeddings if not provided
            if not embeddings:
                try:
                    from sentence_transformers import SentenceTransformer

                    model = SentenceTransformer("all-MiniLM-L6-v2")
                    texts = [doc.get("text", "")[:1000] for doc in documents]
                    raw_embeddings = model.encode(texts, show_progress_bar=False)
                    embeddings = [emb.tolist() for emb in raw_embeddings]
                except ImportError:
                    logger.error("sentence-transformers not available")
                    return []

            for i, doc in enumerate(documents):
                doc_id = doc.get("id", f"doc_{i}")
                ids.append(doc_id)

                # Pad or truncate embedding to target dimension
                embedding = embeddings[i] if i < len(embeddings) else []
                if len(embedding) < target_dimension:
                    # Pad with zeros
                    embedding = embedding + [0.0] * (target_dimension - len(embedding))
                else:
                    # Truncate if too long
                    embedding = embedding[:target_dimension]

                metadata = {
                    "text": doc.get("text", "")[:10000],
                    "title": doc.get("metadata", {}).get("title", ""),
                    "arxiv_id": doc.get("metadata", {}).get("arxiv_id", ""),
                    "authors": doc.get("metadata", {}).get("authors", []),
                    "created_at": datetime.utcnow().isoformat(),
                }

                vectors.append(
                    {
                        "id": doc_id,
                        "values": embedding,
                        "metadata": metadata,
                    }
                )

            if vectors:
                self._index.upsert(vectors=vectors, namespace="papers")

            logger.info(f"Added {len(ids)} documents to Pinecone")
            return ids

        except Exception as e:
            logger.error("Failed to add documents to Pinecone", error=str(e))
            return []

    async def search(
        self,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
        query_text: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        if not self.is_connected:
            logger.warning("Pinecone not connected, returning empty results")
            return []

        try:
            # Generate embedding from text if query_text is provided
            if query_text and not query_embedding:
                try:
                    from sentence_transformers import SentenceTransformer

                    model = SentenceTransformer("all-MiniLM-L6-v2")
                    raw_embedding = model.encode(
                        [query_text], show_progress_bar=False
                    ).tolist()[0]
                    # Pad to target dimension
                    target_dimension = 1024
                    if len(raw_embedding) < target_dimension:
                        query_embedding = raw_embedding + [0.0] * (
                            target_dimension - len(raw_embedding)
                        )
                    else:
                        query_embedding = raw_embedding[:target_dimension]
                except ImportError:
                    logger.error(
                        "sentence-transformers not available for query embedding"
                    )
                    return []

            if not query_embedding:
                logger.error("No query embedding or text provided for search")
                return []

            # Build query params
            query_params = {
                "vector": query_embedding,
                "top_k": top_k,
                "namespace": "papers",
                "include_metadata": True,
            }

            if filter:
                query_params["filter"] = filter

            results = self._index.query(**query_params)

            matches = []
            for match in results.get("matches", []):
                matches.append(
                    {
                        "id": match.get("id"),
                        "score": match.get("score", 0.0),
                        "metadata": match.get("metadata", {}),
                        "text": match.get("metadata", {}).get("text", ""),
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
                    "vector": [0.0] * settings.PINECONE_DIMENSION,
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
                "index_name": settings.PINECONE_INDEX_NAME,
                "host": settings.PINECONE_HOST,
                "dimension": settings.PINECONE_DIMENSION,
            }

        except Exception as e:
            logger.error("Failed to get Pinecone stats", error=str(e))
            return {
                "total_documents": 0,
                "connected": True,
                "error": str(e),
            }


pinecone_store = PineconeStore()
