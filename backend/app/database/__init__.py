"""Database module with fallback implementations"""

from app.database.mock_store import mock_store


# Convenience functions that work with or without Neo4j
def get_paper_by_id(paper_id: str):
    """Get paper by ID"""
    return mock_store.get_paper(paper_id)


def list_papers(skip: int = 0, limit: int = 20, search: str = None):
    """List papers"""
    return mock_store.list_papers(skip=skip, limit=limit, search=search)


def delete_paper(paper_id: str) -> bool:
    """Delete a paper"""
    if paper_id in mock_store.papers:
        del mock_store.papers[paper_id]
        if paper_id in mock_store.entities:
            del mock_store.entities[paper_id]
        if paper_id in mock_store.relationships:
            del mock_store.relationships[paper_id]
        return True
    return False


def get_paper_entities(paper_id: str):
    """Get entities for a paper"""
    return mock_store.get_paper_entities(paper_id)


def get_related_papers(paper_id: str, limit: int = 10):
    """Get related papers"""
    return mock_store.get_related_papers(paper_id, limit=limit)


def store_paper(paper_data: dict) -> str:
    """Store a paper"""
    return mock_store.store_paper(paper_data)


def store_entities(paper_id: str, entities: list):
    """Store entities for a paper"""
    mock_store.store_entities(paper_id, entities)


def store_relationships(paper_id: str, relationships: list):
    """Store relationships for a paper"""
    mock_store.store_relationships(paper_id, relationships)
