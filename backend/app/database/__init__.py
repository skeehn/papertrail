"""Database module with Neo4j support and fallback to mock store"""

from typing import Any, Dict, List, Optional

import structlog

from app.core.config import settings
from app.core.logging import get_logger
from app.database.mock_store import mock_store
from app.database.neo4j_client import Neo4jClient, neo4j_client

logger = get_logger("database")

# Flag to track if Neo4j is connected
NEO4J_CONNECTED = False


async def init_database() -> None:
    """Initialize database connections"""
    global NEO4J_CONNECTED
    try:
        await neo4j_client.connect()
        NEO4J_CONNECTED = True
        logger.info("Database initialized with Neo4j connection")
    except Exception as e:
        logger.warning(f"Neo4j connection failed, using mock store: {e}")
        NEO4J_CONNECTED = False


def get_paper_by_id(paper_id: str) -> Optional[Dict[str, Any]]:
    """Get paper by ID from Neo4j or mock store"""
    if NEO4J_CONNECTED:
        try:
            with neo4j_client.get_session() as session:
                result = session.run(
                    "MATCH (p:Paper {arxiv_id: $id}) RETURN p LIMIT 1", id=paper_id
                )
                record = result.single()
                if record:
                    paper = dict(record["p"])
                    paper["id"] = paper.get("arxiv_id", paper_id)
                    return paper
        except Exception as e:
            logger.error(f"Failed to get paper from Neo4j: {e}")

    return mock_store.get_paper(paper_id)


def list_papers(
    skip: int = 0, limit: int = 20, search: str = None
) -> List[Dict[str, Any]]:
    """List papers from Neo4j or mock store"""
    if NEO4J_CONNECTED and search:
        try:
            with neo4j_client.get_session() as session:
                # Search with Neo4j
                result = session.run(
                    """
                    MATCH (p:Paper)
                    WHERE p.title CONTAINS $search OR p.abstract CONTAINS $search
                    RETURN p
                    SKIP $skip
                    LIMIT $limit
                    """,
                    search=search,
                    skip=skip,
                    limit=limit,
                )
                papers = []
                for record in result:
                    paper = dict(record["p"])
                    paper["id"] = paper.get("arxiv_id", str(record["p"].id))
                    papers.append(paper)
                return papers
        except Exception as e:
            logger.error(f"Failed to search papers in Neo4j: {e}")

    # Fall back to mock or Neo4j without search
    if NEO4J_CONNECTED:
        try:
            with neo4j_client.get_session() as session:
                result = session.run(
                    """
                    MATCH (p:Paper)
                    RETURN p
                    SKIP $skip
                    LIMIT $limit
                    """,
                    skip=skip,
                    limit=limit,
                )
                papers = []
                for record in result:
                    paper = dict(record["p"])
                    paper["id"] = paper.get("arxiv_id", str(record["p"].id))
                    papers.append(paper)
                return papers
        except Exception as e:
            logger.error(f"Failed to get papers from Neo4j: {e}")

    return mock_store.list_papers(skip=skip, limit=limit, search=search)


def delete_paper(paper_id: str) -> bool:
    """Delete a paper from Neo4j or mock store"""
    if NEO4J_CONNECTED:
        try:
            with neo4j_client.get_session() as session:
                result = session.run(
                    "MATCH (p:Paper {arxiv_id: $id}) DETACH DELETE p", id=paper_id
                )
                return True
        except Exception as e:
            logger.error(f"Failed to delete paper from Neo4j: {e}")

    return mock_store.delete_paper(paper_id)


def get_paper_entities(paper_id: str) -> List[Dict[str, Any]]:
    """Get entities for a paper from Neo4j or mock store"""
    if NEO4J_CONNECTED:
        try:
            with neo4j_client.get_session() as session:
                result = session.run(
                    """
                    MATCH (p:Paper {arxiv_id: $id})-[:MENTIONS]->(e:Entity)
                    RETURN e
                    """,
                    id=paper_id,
                )
                entities = []
                for record in result:
                    entity = dict(record["e"])
                    entities.append(entity)
                return entities
        except Exception as e:
            logger.error(f"Failed to get entities from Neo4j: {e}")

    return mock_store.get_paper_entities(paper_id)


def get_related_papers(paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get related papers from Neo4j or mock store"""
    if NEO4J_CONNECTED:
        try:
            with neo4j_client.get_session() as session:
                result = session.run(
                    """
                    MATCH (p1:Paper {arxiv_id: $id})-[:CITES|RELATED_TO]-(p2:Paper)
                    WITH p2, count(*) as rel_count
                    ORDER BY rel_count DESC
                    LIMIT $limit
                    RETURN p2
                    """,
                    id=paper_id,
                    limit=limit,
                )
                papers = []
                for record in result:
                    paper = dict(record["p2"])
                    paper["id"] = paper.get("arxiv_id", str(record["p2"].id))
                    papers.append(paper)
                return papers
        except Exception as e:
            logger.error(f"Failed to get related papers from Neo4j: {e}")

    return mock_store.get_related_papers(paper_id, limit=limit)


def store_paper(paper_data: dict) -> str:
    """Store a paper to Neo4j or mock store"""
    paper_id = paper_data.get("arxiv_id") or paper_data.get("id")

    if NEO4J_CONNECTED and paper_id:
        try:
            with neo4j_client.get_session() as session:
                session.run(
                    """
                    MERGE (p:Paper {arxiv_id: $arxiv_id})
                    SET p.title = $title,
                        p.abstract = $abstract,
                        p.authors = $authors,
                        p.publication_date = $publication_date,
                        p.journal = $journal,
                        p.doi = $doi,
                        p.created_at = $created_at
                    """,
                    arxiv_id=paper_id,
                    title=paper_data.get("title", ""),
                    abstract=paper_data.get("abstract", ""),
                    authors=paper_data.get("authors", []),
                    publication_date=paper_data.get("publication_date"),
                    journal=paper_data.get("journal"),
                    doi=paper_data.get("doi"),
                    created_at=paper_data.get("created_at"),
                )
                return paper_id
        except Exception as e:
            logger.error(f"Failed to store paper to Neo4j: {e}")

    return mock_store.store_paper(paper_data)


def store_entities(paper_id: str, entities: list):
    """Store entities to Neo4j or mock store"""
    if NEO4J_CONNECTED:
        try:
            with neo4j_client.get_session() as session:
                for entity in entities:
                    session.run(
                        """
                        MERGE (e:Entity {name: $name})
                        SET e.type = $type,
                            e.confidence = $confidence
                        WITH e
                        MATCH (p:Paper {arxiv_id: $paper_id})
                        MERGE (p)-[:MENTIONS]->(e)
                        """,
                        name=entity.get("name"),
                        type=entity.get("type", "Entity"),
                        confidence=entity.get("confidence", 0.0),
                        paper_id=paper_id,
                    )
                return
        except Exception as e:
            logger.error(f"Failed to store entities to Neo4j: {e}")

    mock_store.store_entities(paper_id, entities)


def store_relationships(paper_id: str, relationships: list):
    """Store relationships to Neo4j or mock store"""
    if NEO4J_CONNECTED:
        try:
            with neo4j_client.get_session() as session:
                for rel in relationships:
                    session.run(
                        """
                        MATCH (e1:Entity {name: $source})
                        MATCH (e2:Entity {name: $target})
                        MERGE (e1)-[r:RELATES_TO {type: $rel_type}]->(e2)
                        SET r.confidence = $confidence,
                            r.paper_id = $paper_id
                        """,
                        source=rel.get("source"),
                        target=rel.get("target"),
                        rel_type=rel.get("type", "RELATED_TO"),
                        confidence=rel.get("confidence", 0.0),
                        paper_id=paper_id,
                    )
                return
        except Exception as e:
            logger.error(f"Failed to store relationships to Neo4j: {e}")

    mock_store.store_relationships(paper_id, relationships)


def get_graph_statistics() -> Dict[str, Any]:
    """Get graph statistics from Neo4j or mock store"""
    if NEO4J_CONNECTED:
        try:
            with neo4j_client.get_session() as session:
                # Get node counts by type
                node_result = session.run(
                    """
                    MATCH (n)
                    RETURN labels(n)[0] as type, count(*) as count
                """
                )
                node_types = {}
                for record in node_result:
                    node_types[record["type"] or "Node"] = record["count"]

                # Get relationship counts by type
                rel_result = session.run(
                    """
                    MATCH ()-[r]->()
                    RETURN type(r) as type, count(*) as count
                """
                )
                rel_types = {}
                for record in rel_result:
                    rel_types[record["type"] or "RELATED"] = record["count"]

                total_nodes = sum(node_types.values())
                total_rels = sum(rel_types.values())

                return {
                    "node_count": total_nodes,
                    "relationship_count": total_rels,
                    "node_types": node_types,
                    "relationship_types": rel_types,
                    "source": "neo4j",
                }
        except Exception as e:
            logger.error(f"Failed to get graph stats from Neo4j: {e}")

    # Fall back to mock
    return {
        "node_count": len(mock_store.entities) + len(mock_store.papers),
        "relationship_count": len(mock_store.relationships),
        "node_types": {
            "Memory": len([k for k in mock_store.memories]),
            "Paper": len(mock_store.papers),
            "Entity": len(mock_store.entities),
            "Concept": len(set(e.get("type") for e in mock_store.entities.values())),
        },
        "relationship_types": {
            "MENTIONS": len(mock_store.entities) * 2,
            "RELATES_TO": len(mock_store.relationships),
            "AUTHORED_BY": len(mock_store.papers) * 2,
            "CITES": len(mock_store.papers),
        },
        "source": "mock_store",
    }
