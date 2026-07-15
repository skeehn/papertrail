import os
import pickle
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import faiss
    from sentence_transformers import SentenceTransformer

    FAISS_AVAILABLE = True
except ImportError:
    faiss = None
    SentenceTransformer = None
    FAISS_AVAILABLE = False

import structlog

from app.core.config import settings
from app.core.logging import get_logger


class FAISSStore:
    """FAISS vector store for semantic search"""

    def __init__(self):
        self.index = None
        self.embedding_model = None
        self.documents = []
        self.document_ids = []
        self.logger = get_logger("faiss")
        self.index_path = settings.FAISS_INDEX_PATH
        self.model_path = os.path.join(self.index_path, "model.pkl")
        self.documents_path = os.path.join(self.index_path, "documents.pkl")
        self.ids_path = os.path.join(self.index_path, "ids.pkl")

    def init_embedding_model(self) -> None:
        """Initialize the sentence transformer model"""
        try:
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            self.logger.info(
                "Embedding model initialized", model=settings.EMBEDDING_MODEL
            )
        except Exception as e:
            self.logger.error("Failed to initialize embedding model", error=str(e))
            raise

    def create_index(self, dimension: int = 384) -> None:
        """Create a new FAISS index"""
        try:
            # Use IndexFlatIP for inner product (cosine similarity)
            self.index = faiss.IndexFlatIP(dimension)
            self.logger.info("FAISS index created", dimension=dimension)
        except Exception as e:
            self.logger.error("Failed to create FAISS index", error=str(e))
            raise

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Add documents to the vector store"""
        if not self.embedding_model:
            self.init_embedding_model()

        if not self.index:
            # Create index with embedding dimension
            embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            self.create_index(embedding_dim)

        # Extract texts and metadata
        texts = [doc["text"] for doc in documents]
        metadata = [doc.get("metadata", {}) for doc in documents]

        # Generate embeddings
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)

        # Add to index
        self.index.add(embeddings.astype("float32"))

        # Store documents and IDs
        start_idx = len(self.documents)
        for i, doc in enumerate(documents):
            self.documents.append(
                {
                    "text": doc["text"],
                    "metadata": doc.get("metadata", {}),
                    "id": doc.get("id", f"doc_{start_idx + i}"),
                }
            )
            self.document_ids.append(doc.get("id", f"doc_{start_idx + i}"))

        self.logger.info("Documents added to vector store", count=len(documents))

    def search(
        self, query: str, k: int = 10, filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        if not self.embedding_model or not self.index:
            raise RuntimeError("Vector store not initialized")

        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])
        faiss.normalize_L2(query_embedding)

        # Search
        scores, indices = self.index.search(query_embedding.astype("float32"), k)

        # Prepare results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.documents):
                doc = self.documents[idx].copy()
                doc["score"] = float(score)
                doc["index"] = int(idx)

                # Apply metadata filter if provided
                if filter_metadata:
                    if self._matches_filter(doc["metadata"], filter_metadata):
                        results.append(doc)
                else:
                    results.append(doc)

        return results

    def _matches_filter(
        self, doc_metadata: Dict[str, Any], filter_metadata: Dict[str, Any]
    ) -> bool:
        """Check if document metadata matches filter"""
        for key, value in filter_metadata.items():
            if key not in doc_metadata or doc_metadata[key] != value:
                return False
        return True

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        try:
            idx = self.document_ids.index(doc_id)
            return self.documents[idx]
        except ValueError:
            return None

    def update_document(
        self, doc_id: str, new_text: str, new_metadata: Dict[str, Any] = None
    ) -> bool:
        """Update a document in the vector store"""
        try:
            idx = self.document_ids.index(doc_id)

            # Remove old document
            self.index.remove_ids(np.array([idx]))

            # Generate new embedding
            new_embedding = self.embedding_model.encode([new_text])
            faiss.normalize_L2(new_embedding)

            # Add new embedding
            self.index.add(new_embedding.astype("float32"))

            # Update document
            self.documents[idx]["text"] = new_text
            if new_metadata:
                self.documents[idx]["metadata"].update(new_metadata)

            self.logger.info("Document updated", doc_id=doc_id)
            return True

        except ValueError:
            self.logger.warning("Document not found for update", doc_id=doc_id)
            return False

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the vector store"""
        try:
            idx = self.document_ids.index(doc_id)

            # Remove from index
            self.index.remove_ids(np.array([idx]))

            # Remove from documents list
            del self.documents[idx]
            del self.document_ids[idx]

            self.logger.info("Document deleted", doc_id=doc_id)
            return True

        except ValueError:
            self.logger.warning("Document not found for deletion", doc_id=doc_id)
            return False

    def save_index(self) -> None:
        """Save the index and documents to disk"""
        os.makedirs(self.index_path, exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, os.path.join(self.index_path, "index.faiss"))

        # Save embedding model
        with open(self.model_path, "wb") as f:
            pickle.dump(self.embedding_model, f)

        # Save documents
        with open(self.documents_path, "wb") as f:
            pickle.dump(self.documents, f)

        # Save document IDs
        with open(self.ids_path, "wb") as f:
            pickle.dump(self.document_ids, f)

        self.logger.info("Vector store saved", path=self.index_path)

    def load_index(self) -> bool:
        """Load the index and documents from disk"""
        try:
            index_file = os.path.join(self.index_path, "index.faiss")
            if not os.path.exists(index_file):
                return False

            # Load FAISS index
            self.index = faiss.read_index(index_file)

            # Load embedding model
            if os.path.exists(self.model_path):
                with open(self.model_path, "rb") as f:
                    self.embedding_model = pickle.load(f)

            # Load documents
            if os.path.exists(self.documents_path):
                with open(self.documents_path, "rb") as f:
                    self.documents = pickle.load(f)

            # Load document IDs
            if os.path.exists(self.ids_path):
                with open(self.ids_path, "rb") as f:
                    self.document_ids = pickle.load(f)

            self.logger.info(
                "Vector store loaded",
                document_count=len(self.documents),
                index_size=self.index.ntotal,
            )
            return True

        except Exception as e:
            self.logger.error("Failed to load vector store", error=str(e))
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        return {
            "total_documents": len(self.documents),
            "index_size": self.index.ntotal if self.index else 0,
            "embedding_dimension": self.index.d if self.index else None,
            "model_name": settings.EMBEDDING_MODEL,
        }


# Global FAISS store instance
faiss_store = FAISSStore()


def init_faiss() -> None:
    """Initialize FAISS vector store"""
    if not faiss_store.load_index():
        # Create new index if loading fails
        faiss_store.init_embedding_model()
        faiss_store.create_index()


def add_documents_to_store(documents: List[Dict[str, Any]]) -> None:
    """Add documents to the local FAISS store.

    Optional: FAISS + sentence-transformers are not installed by default (they
    pull in torch, ~2GB). Semantic search is served by Pinecone's integrated
    embeddings instead, so this is a no-op unless the extras are installed.
    """
    if not FAISS_AVAILABLE:
        get_logger("faiss").debug("FAISS not installed - skipping local vector index")
        return
    faiss_store.add_documents(documents)


def search_documents(
    query: str, k: int = 10, filter_metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Search the local FAISS store (empty when FAISS is not installed)."""
    if not FAISS_AVAILABLE:
        return []
    return faiss_store.search(query, k, filter_metadata)


def get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    """Get document by ID"""
    return faiss_store.get_document_by_id(doc_id)


def update_document(
    doc_id: str, new_text: str, new_metadata: Dict[str, Any] = None
) -> bool:
    """Update a document"""
    return faiss_store.update_document(doc_id, new_text, new_metadata)


def delete_document(doc_id: str) -> bool:
    """Delete a document"""
    return faiss_store.delete_document(doc_id)


def save_vector_store() -> None:
    """Save the vector store"""
    faiss_store.save_index()


def get_vector_store_stats() -> Dict[str, Any]:
    """Get vector store statistics"""
    return faiss_store.get_statistics()
