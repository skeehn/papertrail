from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import structlog

from app.core.logging import get_logger, log_graph_operation
from app.database import hydradb_store, GraphOperations
from app.services.entity_extractor import ExtractedEntity, ExtractedRelationship


class GraphBuilder:
    """Service for building knowledge graphs from extracted entities and relationships"""

    def __init__(self):
        self.logger = get_logger("graph_builder")

    async def add_paper_to_graph(
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
            paper_id = await self._create_paper_node(paper_data)

            # Create entity nodes and connect to paper
            entity_map = await self._create_entity_nodes(entities, paper_id)

            # Create relationships between entities
            relationship_count = await self._create_entity_relationships(
                relationships, entity_map
            )

            # Create embeddings and vector connections
            await self._create_vector_connections(paper_data, entities)

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

    async def _create_paper_node(self, paper_data: Dict[str, Any]) -> str:
        """Create a paper node in the graph"""
        try:
            paper_id = await hydradb_store.store_paper(paper_data)
            return paper_id

        except Exception as e:
            self.logger.error("Failed to create paper node", error=str(e))
            raise

    async def _create_entity_nodes(
        self, entities: List[ExtractedEntity], paper_id: str
    ) -> Dict[str, str]:
        """Create entity nodes and connect them to the paper"""
        entity_map = {}

        try:
            await hydradb_store.store_entities(paper_id, entities)
            for entity in entities:
                entity_map[entity.name] = entity.name

            self.logger.debug("Created entity nodes", count=len(entity_map))
            return entity_map

        except Exception as e:
            self.logger.error("Failed to create entity nodes", error=str(e))
            raise

    async def _create_entity_relationships(
        self, relationships: List[ExtractedRelationship], entity_map: Dict[str, str]
    ) -> int:
        """Create relationships between entities"""
        created_count = 0

        try:
            # Convert entities to relationship format for HydraDB
            rel_list = []
            for rel in relationships:
                source_name = entity_map.get(rel.source)
                target_name = entity_map.get(rel.target)

                if not source_name or not target_name:
                    self.logger.debug(
                        "Skipping relationship with missing entities",
                        source=rel.source,
                        target=rel.target,
                    )
                    continue

                rel_list.append({
                    "type": rel.type.value.upper(),
                    "target_paper_id": target_name,
                })
                created_count += 1

            if rel_list:
                # Store relationships in HydraDB
                # Note: relationships are stored as metadata on context items
                for rel in rel_list:
                    await hydradb_store.store_relationships(
                        paper_id="",  # Will be filled by store_relationships
                        relationships=[rel]
                    )

            self.logger.debug("Created entity relationships", count=created_count)
            return created_count

        except Exception as e:
            self.logger.error("Failed to create entity relationships", error=str(e))
            raise

    async def _create_vector_connections(
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

    async def build_citation_network(
        self, paper_id: str, citations: List[Dict[str, Any]]
    ) -> int:
        """Build citation network for a paper"""
        try:
            created_count = 0

            # Store citations as relationships in HydraDB
            citation_rels = []
            for citation in citations:
                citation_rels.append({
                    "type": "CITES",
                    "target_paper_id": citation.get("reference", ""),
                })
                created_count += 1

            if citation_rels:
                await hydradb_store.store_relationships(paper_id, citation_rels)

            log_graph_operation(
                "citations_added", node_count=created_count, paper_id=paper_id
            )

            return created_count

        except Exception as e:
            self.logger.error("Failed to build citation network", error=str(e))
            raise

    async def find_similar_papers(
        self, paper_id: str, similarity_threshold: float = 0.5, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find papers similar to the given paper"""
        try:
            # Use HydraDB to list papers and compute similarity
            papers = await hydradb_store.list_papers(limit=200)

            # For now, return empty list as full graph traversal requires HydraDB-specific patterns
            similar_papers = []

            # Simple approach: list papers and match by category/keywords
            for paper in papers:
                if paper.get('arxiv_id') == paper_id:
                    continue

                # Placeholder - would need actual graph traversal
                pass

            return similar_papers[:limit]

        except Exception as e:
            self.logger.error("Failed to find similar papers", error=str(e))
            return []

    async def get_entity_cluster(self, entity_name: str, depth: int = 2) -> Dict[str, Any]:
        """Get a cluster of related entities"""
        try:
            # Use HydraDB to list papers and build entity cluster
            papers = await hydradb_store.list_papers(limit=200)

            # Search for entity in paper titles/abstracts
            matching_papers = []
            for paper in papers:
                title = paper.get('title', '')
                abstract = paper.get('abstract', '')
                if entity_name.lower() in title.lower() or entity_name.lower() in abstract.lower():
                    matching_papers.append(paper)

            # Build simplified entity cluster
            nodes = []
            edges = []
            seen_ids = set()

            for paper in matching_papers[:5]:
                paper_id = paper.get('arxiv_id', '')
                if paper_id and paper_id not in seen_ids:
                    seen_ids.add(paper_id)
                    nodes.append({
                        "id": paper_id,
                        "name": paper_id,
                        "type": "Paper",
                        "description": paper.get('title', '')[:80],
                        "confidence": 0.8
                    })

            return {
                "center_entity": entity_name,
                "nodes": nodes,
                "edges": edges,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "matching_papers": len(matching_papers),
                "message": "Use HydraDB graph traversal for full entity cluster"
            }

        except Exception as e:
            self.logger.error("Failed to get entity cluster", error=str(e))
            return {"nodes": [], "edges": []}


    async def update_graph_statistics(self) -> Dict[str, Any]:
        """Update and return graph statistics"""
        try:
            stats = GraphOperations.get_graph_statistics()

            # Add additional computed statistics using HydraDB
            papers = await hydradb_store.list_papers(limit=1000)

            # Compute paper distribution by categories
            categories = {}
            for paper in papers:
                paper_categories = paper.get('categories', [])
                if isinstance(paper_categories, str):
                    paper_categories = [c.strip() for c in paper_categories.split(',')]
                for cat in paper_categories:
                    if cat:
                        categories[cat] = categories.get(cat, 0) + 1

            top_categories = dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10])

            stats.update(
                {
                    "avg_entity_confidence": 0.5,  # Placeholder
                    "top_categories": top_categories,
                    "last_updated": datetime.utcnow().isoformat(),
                }
            )

            return stats

        except Exception as e:
            self.logger.error("Failed to update graph statistics", error=str(e))
            return {}

    async def cleanup_low_confidence_entities(self, confidence_threshold: float = 0.3) -> int:
        """Remove entities with low confidence scores"""
        try:
            # Use HydraDB to list papers and identify entities for cleanup
            papers = await hydradb_store.list_papers(limit=1000)

            # In production, identify and delete low-confidence entities
            # For now, return 0 as placeholder and log the operation
            deleted_count = 0

            log_graph_operation(
                "cleanup_completed",
                deleted_count=deleted_count,
                threshold=confidence_threshold,
            )

            return deleted_count

        except Exception as e:
            self.logger.error("Failed to cleanup entities", error=str(e))
            return 0