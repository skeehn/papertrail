from typing import Any, Dict, List, Optional, Tuple

try:
    from neo4j import Driver, GraphDatabase, Session
    from neo4j.exceptions import AuthError, ServiceUnavailable

    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
import asyncio
from contextlib import asynccontextmanager
from functools import wraps

import structlog

from app.core.config import settings
from app.core.logging import get_logger
from app.database.mock_store import mock_store


class Neo4jClient:
    """Neo4j database client with connection management"""

    def __init__(self):
        self._driver: Optional[Driver] = None
        self.logger = get_logger("neo4j")

    async def connect(self) -> None:
        """Initialize Neo4j connection"""
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
            )

            # Test connection
            await self._test_connection()
            self.logger.info("Neo4j connection established")

        except Exception as e:
            self.logger.error("Failed to connect to Neo4j", error=str(e))
            raise

    async def _test_connection(self) -> None:
        """Test Neo4j connection"""
        try:
            with self._driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
        except Exception as e:
            self.logger.error("Neo4j connection test failed", error=str(e))
            raise

    async def close(self) -> None:
        """Close Neo4j connection"""
        if self._driver:
            self._driver.close()
            self.logger.info("Neo4j connection closed")

    @property
    def driver(self) -> Driver:
        """Get Neo4j driver"""
        if not self._driver:
            raise RuntimeError("Neo4j driver not initialized")
        return self._driver

    def get_session(self) -> Session:
        """Get Neo4j session"""
        return self.driver.session()


# Global Neo4j client instance
neo4j_client = Neo4jClient()


async def init_neo4j() -> None:
    """Initialize Neo4j connection"""
    await neo4j_client.connect()


async def close_neo4j() -> None:
    """Close Neo4j connection"""
    await neo4j_client.close()


def with_session(func):
    """Decorator to provide Neo4j session"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        with neo4j_client.get_session() as session:
            return func(session, *args, **kwargs)

    return wrapper


class GraphOperations:
    """Graph database operations for PaperTrail"""

    @staticmethod
    @with_session
    def create_paper_node(session: Session, paper_data: Dict[str, Any]) -> str:
        """Create a paper node in the graph"""
        query = """
        MERGE (p:Paper {arxiv_id: $arxiv_id})
        SET p += $properties
        RETURN p.arxiv_id as paper_id
        """

        properties = {
            "title": paper_data.get("title"),
            "authors": paper_data.get("authors", []),
            "abstract": paper_data.get("abstract"),
            "publication_date": paper_data.get("publication_date"),
            "journal": paper_data.get("journal"),
            "doi": paper_data.get("doi"),
            "created_at": paper_data.get("created_at"),
            "updated_at": paper_data.get("updated_at"),
        }

        result = session.run(
            query, arxiv_id=paper_data["arxiv_id"], properties=properties
        )
        return result.single()["paper_id"]

    @staticmethod
    @with_session
    def create_entity_node(session: Session, entity_data: Dict[str, Any]) -> str:
        """Create an entity node in the graph"""
        query = """
        MERGE (e:Entity {name: $name, type: $type})
        SET e += $properties
        RETURN e.name as entity_id
        """

        properties = {
            "description": entity_data.get("description"),
            "confidence": entity_data.get("confidence", 0.0),
            "created_at": entity_data.get("created_at"),
        }

        result = session.run(
            query,
            name=entity_data["name"],
            type=entity_data["type"],
            properties=properties,
        )
        return result.single()["entity_id"]

    @staticmethod
    @with_session
    def create_relationship(
        session: Session,
        from_node: str,
        to_node: str,
        relationship_type: str,
        properties: Dict[str, Any] = None,
    ) -> None:
        """Create a relationship between nodes"""
        query = f"""
        MATCH (a), (b)
        WHERE a.arxiv_id = $from_node OR a.name = $from_node
        AND b.arxiv_id = $to_node OR b.name = $to_node
        MERGE (a)-[r:{relationship_type}]->(b)
        SET r += $properties
        """

        session.run(
            query, from_node=from_node, to_node=to_node, properties=properties or {}
        )

    @staticmethod
    @with_session
    def get_paper_entities(session: Session, paper_id: str) -> List[Dict[str, Any]]:
        """Get all entities related to a paper"""
        query = """
        MATCH (p:Paper {arxiv_id: $paper_id})-[:MENTIONS]->(e:Entity)
        RETURN e.name as name, e.type as type, e.description as description
        """

        result = session.run(query, paper_id=paper_id)
        return [dict(record) for record in result]

    @staticmethod
    @with_session
    def get_related_papers(
        session: Session, paper_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get papers related to a given paper through shared entities"""
        query = """
        MATCH (p1:Paper {arxiv_id: $paper_id})-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(p2:Paper)
        WHERE p1 <> p2
        WITH p2, count(e) as shared_entities
        ORDER BY shared_entities DESC
        LIMIT $limit
        RETURN p2.arxiv_id as arxiv_id, p2.title as title, shared_entities
        """

        result = session.run(query, paper_id=paper_id, limit=limit)
        return [dict(record) for record in result]

    @staticmethod
    @with_session
    def get_entity_subgraph(
        session: Session, entity_name: str, depth: int = 2
    ) -> Dict[str, Any]:
        """Get subgraph around an entity"""
        query = """
        MATCH path = (e:Entity {name: $entity_name})-[*1..$depth]-(related)
        RETURN path
        """

        result = session.run(query, entity_name=entity_name, depth=depth)
        # Process path results into nodes and relationships
        nodes = set()
        relationships = set()

        for record in result:
            path = record["path"]
            for node in path.nodes:
                nodes.add((node.labels[0], dict(node)))
            for rel in path.relationships:
                relationships.add((rel.type, dict(rel)))

        return {"nodes": list(nodes), "relationships": list(relationships)}

    @staticmethod
    @with_session
    def search_entities(
        session: Session, query: str, entity_type: str = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for entities by name"""
        if entity_type:
            query_text = """
            MATCH (e:Entity)
            WHERE e.name CONTAINS $query AND e.type = $entity_type
            RETURN e.name as name, e.type as type, e.description as description
            ORDER BY e.name
            LIMIT $limit
            """
            result = session.run(
                query_text, query=query, entity_type=entity_type, limit=limit
            )
        else:
            query_text = """
            MATCH (e:Entity)
            WHERE e.name CONTAINS $query
            RETURN e.name as name, e.type as type, e.description as description
            ORDER BY e.name
            LIMIT $limit
            """
            result = session.run(query_text, query=query, limit=limit)

        return [dict(record) for record in result]

    @staticmethod
    @with_session
    def get_graph_statistics(session: Session) -> Dict[str, Any]:
        """Get graph statistics"""
        query = """
        MATCH (n)
        RETURN labels(n)[0] as node_type, count(n) as count
        UNION
        MATCH ()-[r]->()
        RETURN type(r) as relationship_type, count(r) as count
        """

        result = session.run(query)
        stats = {"nodes": {}, "relationships": {}}

        for record in result:
            if "node_type" in record:
                stats["nodes"][record["node_type"]] = record["count"]
            else:
                stats["relationships"][record["relationship_type"]] = record["count"]

        return stats


# Convenience functions
def create_paper(paper_data: Dict[str, Any]) -> str:
    """Create a paper node"""
    return GraphOperations.create_paper_node(paper_data)


def create_entity(entity_data: Dict[str, Any]) -> str:
    """Create an entity node"""
    return GraphOperations.create_entity_node(entity_data)


def create_relationship_between(
    from_node: str,
    to_node: str,
    relationship_type: str,
    properties: Dict[str, Any] = None,
) -> None:
    """Create a relationship between nodes"""
    GraphOperations.create_relationship(
        from_node, to_node, relationship_type, properties
    )


def get_paper_entities(paper_id: str) -> List[Dict[str, Any]]:
    """Get entities for a paper"""
    return GraphOperations.get_paper_entities(paper_id)


def get_related_papers(paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get related papers"""
    return GraphOperations.get_related_papers(paper_id, limit)


def get_entity_subgraph(entity_name: str, depth: int = 2) -> Dict[str, Any]:
    """Get entity subgraph"""
    return GraphOperations.get_entity_subgraph(entity_name, depth)


def search_entities(
    query: str, entity_type: str = None, limit: int = 20
) -> List[Dict[str, Any]]:
    """Search entities"""
    return GraphOperations.search_entities(query, entity_type, limit)


def get_graph_statistics() -> Dict[str, Any]:
    """Get graph statistics"""
    return GraphOperations.get_graph_statistics()
