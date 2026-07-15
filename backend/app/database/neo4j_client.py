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

from app.core import user_config
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
                user_config.get_key("NEO4J_URI"),
                auth=(
                    user_config.get_key("NEO4J_USERNAME"),
                    user_config.get_key("NEO4J_PASSWORD"),
                ),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
            )

            # Test connection
            await self._test_connection()
            self.logger.info("Neo4j connection established")

        except Exception as e:
            self.logger.error("Failed to connect to Neo4j", error=str(e))
            # Drop the half-initialized driver so callers (and execute_query's
            # fallback) treat this client as disconnected and degrade to the
            # mock store instead of retrying a dead socket on every query.
            if self._driver is not None:
                try:
                    self._driver.close()
                except Exception:
                    pass
                self._driver = None
            raise

    async def _test_connection(self) -> None:
        """Test Neo4j connection"""
        try:
            with self._driver.session(database=settings.NEO4J_DATABASE) as session:
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
        return self.driver.session(database=settings.NEO4J_DATABASE)

    def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Run a Cypher query and return records as a list of dicts.

        Degrades gracefully: when no Neo4j connection is available (e.g. the
        app is running against the in-memory mock store), this returns an
        empty list instead of raising, so callers fall through to their
        "no data" branches rather than surfacing a 500.

        Service classes construct their own ``Neo4jClient()`` instances that
        are never connected directly, so we fall back to the shared global
        connection established at startup when this instance has no driver.
        """
        driver = self._driver
        if driver is None:
            global_client = globals().get("neo4j_client")
            if global_client is not None and global_client is not self:
                driver = global_client._driver
        if driver is None:
            return []

        with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]


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
    def _ensure_indexes(session: Session):
        """Ensure indexes exist for optimal query performance"""
        indexes = [
            "CREATE INDEX paper_arxiv_id IF NOT EXISTS FOR (p:Paper) ON (p.arxiv_id)",
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX paper_title IF NOT EXISTS FOR (p:Paper) ON (p.title)",
        ]

        for index_query in indexes:
            try:
                session.run(index_query)
            except Exception:
                # Index might already exist or query syntax might differ
                pass

    @staticmethod
    @with_session
    def create_paper_node(session: Session, paper_data: Dict[str, Any]) -> str:
        """Create a paper node in the graph"""
        GraphOperations._ensure_indexes(session)

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

        arxiv_id_value = paper_data.get("arxiv_id") or paper_data.get("id")
        if not arxiv_id_value:
            raise ValueError("paper_data must contain either 'arxiv_id' or 'id'")
        result = session.run(query, arxiv_id=arxiv_id_value, properties=properties)
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
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Get subgraph around an entity, returns (nodes, edges) - optimized with indexes"""
        GraphOperations._ensure_indexes(session)

        # Optimized query using index on entity name
        query = """
        MATCH (e:Entity {name: $entity_name})
        WITH e
        MATCH path = (e)-[*1..$depth]-(related)
        WITH path, e, related
        UNWIND nodes(path) as node
        UNWIND relationships(path) as rel
        WITH DISTINCT node, rel, e, related
        RETURN 
            collect(DISTINCT {
                id: coalesce(node.arxiv_id, node.name, toString(id(node))),
                label: coalesce(node.title, node.name, node.arxiv_id, toString(id(node))),
                type: labels(node)[0],
                properties: properties(node)
            }) as nodes,
            collect(DISTINCT {
                source: coalesce(startNode(rel).arxiv_id, startNode(rel).name, toString(id(startNode(rel)))),
                target: coalesce(endNode(rel).arxiv_id, endNode(rel).name, toString(id(endNode(rel)))),
                type: type(rel),
                properties: properties(rel)
            }) as edges
        LIMIT 1000
        """

        result = session.run(query, entity_name=entity_name, depth=depth)
        record = result.single()

        if not record:
            # If no results, return at least the entity itself
            query_entity = """
            MATCH (e:Entity {name: $entity_name})
            RETURN {
                id: coalesce(e.arxiv_id, e.name, toString(id(e))),
                label: coalesce(e.title, e.name, e.arxiv_id, toString(id(e))),
                type: labels(e)[0],
                properties: properties(e)
            } as node
            """
            result_entity = session.run(query_entity, entity_name=entity_name)
            entity_record = result_entity.single()
            if entity_record:
                return ([entity_record["node"]], [])
            return ([], [])

        nodes = record["nodes"] or []
        edges = record["edges"] or []

        # Remove duplicates based on id
        seen_nodes = {}
        unique_nodes = []
        for node in nodes:
            node_id = node.get("id")
            if node_id and node_id not in seen_nodes:
                seen_nodes[node_id] = True
                unique_nodes.append(node)

        # Remove duplicate edges
        seen_edges = set()
        unique_edges = []
        for edge in edges:
            edge_key = (edge.get("source"), edge.get("target"), edge.get("type"))
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                unique_edges.append(edge)

        return (unique_nodes, unique_edges)

    @staticmethod
    @with_session
    def search_entities(
        session: Session, query: str, entity_type: str = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for entities by name - optimized with index"""
        GraphOperations._ensure_indexes(session)

        # Use index on entity name for faster searches
        if entity_type:
            query_text = """
            MATCH (e:Entity)
            WHERE e.name CONTAINS $query AND e.type = $entity_type
            USING INDEX e:Entity(name)
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
            USING INDEX e:Entity(name)
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
        node_query = """
        MATCH (n)
        RETURN labels(n)[0] as type, count(n) as count
        """
        node_result = session.run(node_query)
        stats = {"nodes": {}, "relationships": {}}
        for record in node_result:
            stats["nodes"][record["type"] or "Node"] = record["count"]

        rel_query = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        """
        rel_result = session.run(rel_query)
        for record in rel_result:
            stats["relationships"][record["type"] or "RELATED"] = record["count"]

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


def get_entity_subgraph(
    entity_name: str, depth: int = 2
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Get entity subgraph, returns (nodes, edges)"""
    return GraphOperations.get_entity_subgraph(entity_name, depth)


def search_entities(
    query: str, entity_type: str = None, limit: int = 20
) -> List[Dict[str, Any]]:
    """Search entities"""
    return GraphOperations.search_entities(query, entity_type, limit)


def get_graph_statistics() -> Dict[str, Any]:
    """Get graph statistics"""
    return GraphOperations.get_graph_statistics()
