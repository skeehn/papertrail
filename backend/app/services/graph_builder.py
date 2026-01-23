from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import structlog

from app.core.logging import get_logger, log_graph_operation
from app.database.neo4j_client import GraphOperations, neo4j_client
from app.services.entity_extractor import ExtractedEntity, ExtractedRelationship


class GraphBuilder:
    """Service for building knowledge graphs from extracted entities and relationships"""

    def __init__(self):
        self.logger = get_logger("graph_builder")

    def add_paper_to_graph(
        self,
        paper_data: Dict[str, Any],
        entities: List[ExtractedEntity],
        relationships: List[ExtractedRelationship],
    ) -> Dict[str, Any]:
        """Add a paper and its extracted knowledge to the graph"""
        try:
            self.logger.info(
                "Adding paper to graph",
                paper_id=paper_data.get("arxiv_id"),
                entity_count=len(entities),
                relationship_count=len(relationships),
            )

            # Create paper node
            paper_id = self._create_paper_node(paper_data)

            # Create entity nodes and connect to paper
            entity_map = self._create_entity_nodes(entities, paper_id)

            # Create relationships between entities
            relationship_count = self._create_entity_relationships(
                relationships, entity_map
            )

            # Create embeddings and vector connections
            self._create_vector_connections(paper_data, entities)

            log_graph_operation(
                "paper_added",
                node_count=1 + len(entity_map),
                relationship_count=relationship_count,
                paper_id=paper_id,
            )

            result = {
                "paper_id": paper_id,
                "entities_created": len(entity_map),
                "relationships_created": relationship_count,
                "status": "success",
            }

            self.logger.info("Paper added to graph successfully", **result)
            return result

        except Exception as e:
            self.logger.error("Failed to add paper to graph", error=str(e))
            raise

    def _create_paper_node(self, paper_data: Dict[str, Any]) -> str:
        """Create a paper node in the graph"""
        try:
            with neo4j_client.get_session() as session:
                query = """
                MERGE (p:Paper {arxiv_id: $arxiv_id})
                SET p.title = $title,
                    p.authors = $authors,
                    p.abstract = $abstract,
                    p.publication_date = $publication_date,
                    p.journal = $journal,
                    p.doi = $doi,
                    p.categories = $categories,
                    p.created_at = $created_at,
                    p.updated_at = $updated_at,
                    p.text_length = $text_length,
                    p.page_count = $page_count
                RETURN p.arxiv_id as paper_id
                """

                result = session.run(
                    query,
                    arxiv_id=paper_data.get("arxiv_id"),
                    title=paper_data.get("title", ""),
                    authors=paper_data.get("authors", []),
                    abstract=paper_data.get("abstract", ""),
                    publication_date=paper_data.get("publication_date"),
                    journal=paper_data.get("journal"),
                    doi=paper_data.get("doi"),
                    categories=paper_data.get("categories", []),
                    created_at=paper_data.get(
                        "created_at", datetime.utcnow()
                    ).isoformat(),
                    updated_at=paper_data.get(
                        "updated_at", datetime.utcnow()
                    ).isoformat(),
                    text_length=len(paper_data.get("text", "")),
                    page_count=paper_data.get("page_count"),
                )

                return result.single()["paper_id"]

        except Exception as e:
            self.logger.error("Failed to create paper node", error=str(e))
            raise

    def _create_entity_nodes(
        self, entities: List[ExtractedEntity], paper_id: str
    ) -> Dict[str, str]:
        """Create entity nodes and connect them to the paper"""
        entity_map = {}

        try:
            with neo4j_client.get_session() as session:
                for entity in entities:
                    # Create or update entity node
                    entity_query = """
                    MERGE (e:Entity {name: $name, type: $type})
                    SET e.description = COALESCE(e.description, $description),
                        e.confidence = CASE 
                            WHEN e.confidence IS NULL OR e.confidence < $confidence 
                            THEN $confidence 
                            ELSE e.confidence 
                        END,
                        e.updated_at = $updated_at,
                        e.contexts = COALESCE(e.contexts, []) + [$context]
                    RETURN e.name as entity_name
                    """

                    entity_result = session.run(
                        entity_query,
                        name=entity.name,
                        type=entity.type.value,
                        description=entity.description,
                        confidence=entity.confidence,
                        context=entity.context,
                        updated_at=datetime.utcnow().isoformat(),
                    )

                    entity_name = entity_result.single()["entity_name"]
                    entity_map[entity.name] = entity_name

                    # Create MENTIONS relationship between paper and entity
                    mention_query = """
                    MATCH (p:Paper {arxiv_id: $paper_id})
                    MATCH (e:Entity {name: $entity_name})
                    MERGE (p)-[r:MENTIONS]->(e)
                    SET r.confidence = $confidence,
                        r.context = $context,
                        r.entity_type = $entity_type
                    """

                    session.run(
                        mention_query,
                        paper_id=paper_id,
                        entity_name=entity_name,
                        confidence=entity.confidence,
                        context=entity.context,
                        entity_type=entity.type.value,
                    )

            self.logger.debug("Created entity nodes", count=len(entity_map))
            return entity_map

        except Exception as e:
            self.logger.error("Failed to create entity nodes", error=str(e))
            raise

    def _create_entity_relationships(
        self, relationships: List[ExtractedRelationship], entity_map: Dict[str, str]
    ) -> int:
        """Create relationships between entities"""
        created_count = 0

        try:
            with neo4j_client.get_session() as session:
                for rel in relationships:
                    # Check if both entities exist in our map
                    source_name = entity_map.get(rel.source)
                    target_name = entity_map.get(rel.target)

                    if not source_name or not target_name:
                        self.logger.debug(
                            "Skipping relationship with missing entities",
                            source=rel.source,
                            target=rel.target,
                        )
                        continue

                    # Create relationship
                    rel_query = f"""
                    MATCH (source:Entity {{name: $source_name}})
                    MATCH (target:Entity {{name: $target_name}})
                    MERGE (source)-[r:{rel.type.value.upper()}]->(target)
                    SET r.description = $description,
                        r.confidence = CASE 
                            WHEN r.confidence IS NULL OR r.confidence < $confidence 
                            THEN $confidence 
                            ELSE r.confidence 
                        END,
                        r.context = $context,
                        r.updated_at = $updated_at
                    RETURN r
                    """

                    result = session.run(
                        rel_query,
                        source_name=source_name,
                        target_name=target_name,
                        description=rel.description,
                        confidence=rel.confidence,
                        context=rel.context,
                        updated_at=datetime.utcnow().isoformat(),
                    )

                    if result.single():
                        created_count += 1

            self.logger.debug("Created entity relationships", count=created_count)
            return created_count

        except Exception as e:
            self.logger.error("Failed to create entity relationships", error=str(e))
            raise

    def _create_vector_connections(
        self, paper_data: Dict[str, Any], entities: List[ExtractedEntity]
    ) -> None:
        """Create vector-based connections using FAISS"""
        try:
            from app.database.faiss_store import add_documents_to_store

            # Add paper to vector store
            documents = [
                {
                    "id": paper_data.get("arxiv_id"),
                    "text": paper_data.get("text", ""),
                    "metadata": {
                        "title": paper_data.get("title", ""),
                        "authors": paper_data.get("authors", []),
                        "arxiv_id": paper_data.get("arxiv_id"),
                        "abstract": paper_data.get("abstract", ""),
                        "type": "paper",
                    },
                }
            ]

            # Add entities as separate documents for vector search
            for entity in entities:
                if entity.confidence > 0.7:  # Only high-confidence entities
                    documents.append(
                        {
                            "id": f"{paper_data.get('arxiv_id')}_{entity.name}",
                            "text": f"{entity.name}: {entity.description}. {entity.context}",
                            "metadata": {
                                "entity_name": entity.name,
                                "entity_type": entity.type.value,
                                "paper_id": paper_data.get("arxiv_id"),
                                "confidence": entity.confidence,
                                "type": "entity",
                            },
                        }
                    )

            add_documents_to_store(documents)
            self.logger.debug("Added to vector store", document_count=len(documents))

        except Exception as e:
            self.logger.warning("Failed to add to vector store", error=str(e))
            # Don't raise - vector store is supplementary

    def build_citation_network(
        self, paper_id: str, citations: List[Dict[str, Any]]
    ) -> int:
        """Build citation network for a paper"""
        try:
            created_count = 0

            with neo4j_client.get_session() as session:
                for citation in citations:
                    if citation.get("type") == "numbered":
                        # Create generic citation node
                        citation_query = """
                        MATCH (p:Paper {arxiv_id: $paper_id})
                        MERGE (c:Citation {reference: $reference})
                        SET c.number = $number,
                            c.type = 'numbered'
                        MERGE (p)-[:CITES]->(c)
                        """

                        session.run(
                            citation_query,
                            paper_id=paper_id,
                            reference=citation.get("reference"),
                            number=citation.get("number"),
                        )
                        created_count += 1

                    elif citation.get("type") == "author_year":
                        # Create author-year citation
                        citation_query = """
                        MATCH (p:Paper {arxiv_id: $paper_id})
                        MERGE (c:Citation {reference: $reference})
                        SET c.author = $author,
                            c.year = $year,
                            c.type = 'author_year'
                        MERGE (p)-[:CITES]->(c)
                        """

                        session.run(
                            citation_query,
                            paper_id=paper_id,
                            reference=citation.get("reference"),
                            author=citation.get("author"),
                            year=citation.get("year"),
                        )
                        created_count += 1

            log_graph_operation(
                "citations_added", node_count=created_count, paper_id=paper_id
            )

            return created_count

        except Exception as e:
            self.logger.error("Failed to build citation network", error=str(e))
            raise

    def find_similar_papers(
        self, paper_id: str, similarity_threshold: float = 0.5, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find papers similar to the given paper"""
        try:
            with neo4j_client.get_session() as session:
                # Find papers with shared entities
                query = """
                MATCH (p1:Paper {arxiv_id: $paper_id})-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(p2:Paper)
                WHERE p1 <> p2
                WITH p2, count(e) as shared_entities, collect(e.name) as shared_entity_names
                WHERE shared_entities >= 3
                MATCH (p2:Paper)-[:MENTIONS]->(all_entities:Entity)
                WITH p2, shared_entities, shared_entity_names, count(all_entities) as total_entities
                WITH p2, shared_entities, shared_entity_names, 
                     toFloat(shared_entities) / toFloat(total_entities) as similarity
                WHERE similarity >= $similarity_threshold
                RETURN p2.arxiv_id as arxiv_id, 
                       p2.title as title,
                       p2.authors as authors,
                       shared_entities,
                       similarity,
                       shared_entity_names
                ORDER BY similarity DESC
                LIMIT $limit
                """

                result = session.run(
                    query,
                    paper_id=paper_id,
                    similarity_threshold=similarity_threshold,
                    limit=limit,
                )

                similar_papers = []
                for record in result:
                    similar_papers.append(
                        {
                            "arxiv_id": record["arxiv_id"],
                            "title": record["title"],
                            "authors": record["authors"],
                            "shared_entities": record["shared_entities"],
                            "similarity": record["similarity"],
                            "shared_entity_names": record["shared_entity_names"],
                        }
                    )

                return similar_papers

        except Exception as e:
            self.logger.error("Failed to find similar papers", error=str(e))
            return []

    def get_entity_cluster(self, entity_name: str, depth: int = 2) -> Dict[str, Any]:
        """Get a cluster of related entities"""
        try:
            with neo4j_client.get_session() as session:
                query = """
                MATCH path = (e:Entity {name: $entity_name})-[*1..$depth]-(related:Entity)
                RETURN path
                LIMIT 100
                """

                result = session.run(query, entity_name=entity_name, depth=depth)

                nodes = []
                edges = []
                seen_nodes = set()
                seen_edges = set()

                for record in result:
                    path = record["path"]

                    # Extract nodes
                    for node in path.nodes:
                        node_id = node.get("name")
                        if node_id not in seen_nodes:
                            nodes.append(
                                {
                                    "id": node_id,
                                    "name": node.get("name"),
                                    "type": node.get("type"),
                                    "description": node.get("description"),
                                    "confidence": node.get("confidence", 0.0),
                                }
                            )
                            seen_nodes.add(node_id)

                    # Extract relationships
                    for rel in path.relationships:
                        edge_id = f"{rel.start_node.get('name')}-{rel.type}-{rel.end_node.get('name')}"
                        if edge_id not in seen_edges:
                            edges.append(
                                {
                                    "source": rel.start_node.get("name"),
                                    "target": rel.end_node.get("name"),
                                    "type": rel.type,
                                    "description": rel.get("description", ""),
                                    "confidence": rel.get("confidence", 0.0),
                                }
                            )
                            seen_edges.add(edge_id)

                return {
                    "center_entity": entity_name,
                    "nodes": nodes,
                    "edges": edges,
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                }

        except Exception as e:
            self.logger.error("Failed to get entity cluster", error=str(e))
            return {"nodes": [], "edges": []}

    def update_graph_statistics(self) -> Dict[str, Any]:
        """Update and return graph statistics"""
        try:
            stats = GraphOperations.get_graph_statistics()

            # Add additional computed statistics
            with neo4j_client.get_session() as session:
                # Get average entity confidence
                confidence_query = """
                MATCH (e:Entity)
                WHERE e.confidence IS NOT NULL
                RETURN avg(e.confidence) as avg_confidence, count(e) as entity_count
                """
                confidence_result = session.run(confidence_query)
                confidence_record = confidence_result.single()

                # Get paper distribution by categories
                category_query = """
                MATCH (p:Paper)
                WHERE p.categories IS NOT NULL AND size(p.categories) > 0
                UNWIND p.categories as category
                RETURN category, count(p) as paper_count
                ORDER BY paper_count DESC
                LIMIT 10
                """
                category_result = session.run(category_query)
                categories = {
                    record["category"]: record["paper_count"]
                    for record in category_result
                }

            stats.update(
                {
                    "avg_entity_confidence": (
                        confidence_record["avg_confidence"]
                        if confidence_record
                        else 0.0
                    ),
                    "top_categories": categories,
                    "last_updated": datetime.utcnow().isoformat(),
                }
            )

            return stats

        except Exception as e:
            self.logger.error("Failed to update graph statistics", error=str(e))
            return {}

    def cleanup_low_confidence_entities(self, confidence_threshold: float = 0.3) -> int:
        """Remove entities with low confidence scores"""
        try:
            with neo4j_client.get_session() as session:
                # Delete low-confidence entities and their relationships
                cleanup_query = """
                MATCH (e:Entity)
                WHERE e.confidence < $threshold
                DETACH DELETE e
                RETURN count(e) as deleted_count
                """

                result = session.run(cleanup_query, threshold=confidence_threshold)
                deleted_count = result.single()["deleted_count"]

                log_graph_operation(
                    "cleanup_completed",
                    deleted_count=deleted_count,
                    threshold=confidence_threshold,
                )

                return deleted_count

        except Exception as e:
            self.logger.error("Failed to cleanup entities", error=str(e))
            return 0
