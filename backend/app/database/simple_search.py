"""Simple text-based search as fallback for FAISS"""

from typing import Any, Dict, List, Optional

from app.database.mock_store import mock_store


def add_documents_to_store(documents: List[Dict[str, Any]]):
    """Add documents to search store (mock implementation)"""
    # For now, just store in mock store
    for doc in documents:
        if "id" in doc and "text" in doc:
            # Store as a "paper" for simplicity
            mock_store.store_paper(
                {
                    "id": doc["id"],
                    "arxiv_id": doc["id"],
                    "title": doc.get("metadata", {}).get("title", "Unknown Title"),
                    "text": doc["text"],
                    "authors": doc.get("metadata", {}).get("authors", []),
                    "abstract": (
                        doc["text"][:500] + "..."
                        if len(doc["text"]) > 500
                        else doc["text"]
                    ),
                }
            )


def search_documents(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search documents using simple text matching"""
    results = []
    query_lower = query.lower()

    # Search through stored papers
    for paper in mock_store.papers.values():
        score = 0

        # Check title
        if query_lower in paper.get("title", "").lower():
            score += 10

        # Check abstract/text
        if query_lower in paper.get("abstract", "").lower():
            score += 5

        # Check authors
        authors_text = " ".join(paper.get("authors", [])).lower()
        if query_lower in authors_text:
            score += 3

        if score > 0:
            results.append({"document": paper, "score": score, "id": paper["id"]})

    # Sort by score and return top results
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
