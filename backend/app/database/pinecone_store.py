import os
from typing import Any, Dict, List, Optional
import time

try:
    import pinecone
    from sentence_transformers import SentenceTransformer

    PINECONE_AVAILABLE = True
except ImportError:
    pinecone = None
    SentenceTransformer = None
    PINECONE_AVAILABLE = False

from app.core.config import settings
from app.core.logging import get_logger


class PineconeStore:
    """Pinecone vector store for semantic search"""

    def __init__(self):
        self.pc = None
        self.index = None
        self.embedding_model = None
        self.logger = get_logger("pinecone")
        self.index_name = settings.PINECONE_INDEX_NAME
        self.dimension = settings.PINECONE_DIMENSION

    def init_client(self) -> None:
        """Initialize Pinecone client"""
        if not PINECONE_AVAILABLE:
            self.logger.error("Pinecone library not available")
            raise RuntimeError("Pinecone library not installed")

        if not settings.PINECONE_API_KEY:
            self.logger.error("Pinecone API key not configured")
            raise RuntimeError("PINECONE_API_KEY not set in environment")

        try:
            pinecone.init(api_key=settings.PINECONE_API_KEY, environment="us-east-1")
            self.pc = pinecone
            self.logger.info("Pinecone client initialized")
        except Exception as e:
            self.logger.error("Failed to initialize Pinecone client", error=str(e))
            raise

    def init_embedding_model(self) -> None:
        """Initialize the sentence transformer model"""
        if not PINECONE_AVAILABLE:
            raise RuntimeError("SentenceTransformer not available")

        try:
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            self.logger.info(
                "Embedding model initialized", model=settings.EMBEDDING_MODEL
            )
        except Exception as e:
            self.logger.error("Failed to initialize embedding model", error=str(e))
            raise

    def create_index(self) -> None:
        """Create a new Pinecone index if it doesn't exist"""
        if not self.pc:
            self.init_client()

        try:
            # Check if index already exists
            existing_indexes = self.pc.list_indexes()

            if self.index_name in existing_indexes:
                self.logger.info("Index already exists", index_name=self.index_name)
                self.index = self.pc.Index(self.index_name)
            else:
                # Create new index
                self.pc.create_index(
                    name=self.index_name, dimension=self.dimension, metric="cosine"
                )
                self.logger.info("Pinecone index created", index_name=self.index_name)

                # Wait for index to be ready
                while not self.pc.describe_index(self.index_name).ready:
                    time.sleep(1)

                self.index = self.pc.Index(self.index_name)

        except Exception as e:
            self.logger.error("Failed to create Pinecone index", error=str(e))
            raise

    def connect_to_index(self) -> None:
        """Connect to existing Pinecone index"""
        if not self.pc:
            self.init_client()

        try:
            self.index = self.pc.Index(self.index_name)
            stats = self.index.describe_index_stats()
            self.logger.info(
                "Connected to Pinecone index",
                index_name=self.index_name,
                vector_count=stats.get("total_vector_count", 0),
            )
        except Exception as e:
            self.logger.error("Failed to connect to Pinecone index", error=str(e))
            # Try to create index if it doesn't exist
            self.create_index()

    def add_documents(
        self, documents: List[Dict[str, Any]], batch_size: int = 100
    ) -> None:
        """Add documents to the vector store"""
        if not self.embedding_model:
            self.init_embedding_model()

        if not self.index:
            self.connect_to_index()

        # Extract texts and prepare vectors
        vectors_to_upsert = []

        for i, doc in enumerate(documents):
            text = doc["text"]
            doc_id = doc.get("id", f"doc_{int(time.time())}_{i}")
            metadata = doc.get("metadata", {})

            # Add text to metadata for retrieval
            metadata["text"] = text[:1000]  # Store first 1000 chars in metadata

            # Generate embedding
            embedding = self.embedding_model.encode([text])[0].tolist()

            # Prepare vector
            vectors_to_upsert.append(
                {"id": doc_id, "values": embedding, "metadata": metadata}
            )

            # Batch upsert
            if len(vectors_to_upsert) >= batch_size:
                self.index.upsert(vectors=vectors_to_upsert)
                self.logger.info("Batch upserted", count=len(vectors_to_upsert))
                vectors_to_upsert = []

        # Upsert remaining vectors
        if vectors_to_upsert:
            self.index.upsert(vectors=vectors_to_upsert)
            self.logger.info("Final batch upserted", count=len(vectors_to_upsert))

        self.logger.info("Documents added to Pinecone", count=len(documents))

    def search(
        self, query: str, k: int = 10, filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        if not self.embedding_model or not self.index:
            if not self.index:
                self.connect_to_index()
            if not self.embedding_model:
                self.init_embedding_model()

        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])[0].tolist()

        # Build Pinecone filter
        pinecone_filter = None
        if filter_metadata:
            # Convert filter to Pinecone format
            pinecone_filter = {}
            for key, value in filter_metadata.items():
                pinecone_filter[key] = {"$eq": value}

        # Search
        try:
            response = self.index.query(
                vector=query_embedding,
                top_k=k,
                include_metadata=True,
                filter=pinecone_filter,
            )

            # Prepare results
            results = []
            for match in response["matches"]:
                result = {
                    "id": match["id"],
                    "score": float(match["score"]),
                    "metadata": match.get("metadata", {}),
                    "text": match.get("metadata", {}).get("text", ""),
                }
                results.append(result)

            return results

        except Exception as e:
            self.logger.error("Search failed", error=str(e))
            return []

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        if not self.index:
            self.connect_to_index()

        try:
            response = self.index.fetch(ids=[doc_id])
            if doc_id in response["vectors"]:
                vector_data = response["vectors"][doc_id]
                return {
                    "id": doc_id,
                    "metadata": vector_data.get("metadata", {}),
                    "text": vector_data.get("metadata", {}).get("text", ""),
                }
            return None
        except Exception as e:
            self.logger.error("Failed to fetch document", doc_id=doc_id, error=str(e))
            return None

    def update_document(
        self, doc_id: str, new_text: str, new_metadata: Dict[str, Any] = None
    ) -> bool:
        """Update a document in the vector store"""
        if not self.embedding_model:
            self.init_embedding_model()

        if not self.index:
            self.connect_to_index()

        try:
            # Generate new embedding
            new_embedding = self.embedding_model.encode([new_text])[0].tolist()

            # Prepare metadata
            metadata = new_metadata or {}
            metadata["text"] = new_text[:1000]

            # Upsert (update) vector
            self.index.upsert(
                vectors=[{"id": doc_id, "values": new_embedding, "metadata": metadata}]
            )

            self.logger.info("Document updated", doc_id=doc_id)
            return True

        except Exception as e:
            self.logger.error("Failed to update document", doc_id=doc_id, error=str(e))
            return False

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the vector store"""
        if not self.index:
            self.connect_to_index()

        try:
            self.index.delete(ids=[doc_id])
            self.logger.info("Document deleted", doc_id=doc_id)
            return True

        except Exception as e:
            self.logger.error("Failed to delete document", doc_id=doc_id, error=str(e))
            return False

    def delete_by_filter(self, filter_metadata: Dict[str, Any]) -> bool:
        """Delete documents matching filter"""
        if not self.index:
            self.connect_to_index()

        try:
            # Convert filter to Pinecone format
            pinecone_filter = {}
            for key, value in filter_metadata.items():
                pinecone_filter[key] = {"$eq": value}

            self.index.delete(filter=pinecone_filter)
            self.logger.info("Documents deleted by filter", filter=filter_metadata)
            return True

        except Exception as e:
            self.logger.error("Failed to delete by filter", error=str(e))
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        if not self.index:
            self.connect_to_index()

        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.get("total_vector_count", 0),
                "dimension": stats.get("dimension", self.dimension),
                "index_fullness": stats.get("index_fullness", 0),
                "namespaces": stats.get("namespaces", {}),
                "model_name": settings.EMBEDDING_MODEL,
            }
        except Exception as e:
            self.logger.error("Failed to get statistics", error=str(e))
            return {
                "total_vectors": 0,
                "dimension": self.dimension,
                "model_name": settings.EMBEDDING_MODEL,
                "error": str(e),
            }


# Global Pinecone store instance
pinecone_store = PineconeStore()


def init_pinecone() -> None:
    """Initialize Pinecone vector store"""
    pinecone_store.init_client()
    pinecone_store.init_embedding_model()
    pinecone_store.connect_to_index()


def add_documents_to_pinecone(documents: List[Dict[str, Any]]) -> None:
    """Add documents to the Pinecone vector store"""
    pinecone_store.add_documents(documents)


def search_pinecone(
    query: str, k: int = 10, filter_metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Search for documents in Pinecone"""
    return pinecone_store.search(query, k, filter_metadata)


def get_pinecone_document(doc_id: str) -> Optional[Dict[str, Any]]:
    """Get document by ID from Pinecone"""
    return pinecone_store.get_document_by_id(doc_id)


def update_pinecone_document(
    doc_id: str, new_text: str, new_metadata: Dict[str, Any] = None
) -> bool:
    """Update a document in Pinecone"""
    return pinecone_store.update_document(doc_id, new_text, new_metadata)


def delete_pinecone_document(doc_id: str) -> bool:
    """Delete a document from Pinecone"""
    return pinecone_store.delete_document(doc_id)


def get_pinecone_stats() -> Dict[str, Any]:
    """Get Pinecone vector store statistics"""
    return pinecone_store.get_statistics()
