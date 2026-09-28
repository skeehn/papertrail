"""Community detection service for identifying research topics and clusters"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import get_logger
from app.database import helix_store

logger = get_logger("community_detector")


class CommunityDetector:
    """Service for detecting research communities in the knowledge graph"""

    def __init__(self):
        self.logger = logger
        self.neo4j_client = helix_store

    async def detect_communities(
        self, algorithm: str = "louvain", min_community_size: int = 3
    ) -> Dict[str, Any]:
        """
        Detect communities in the entity graph

        Args:
            algorithm: Algorithm to use (louvain, label_propagation, wcc)
            min_community_size: Minimum number of entities per community

        Returns:
            Dictionary with communities and statistics
        """
        self.logger.info(f"Starting community detection with {algorithm}")

        try:
            # Step 1: Project graph for analysis
            graph_name = "entity-community-graph"
            await self._create_graph_projection(graph_name)

            # Step 2: Run community detection algorithm
            communities = await self._run_community_algorithm(graph_name, algorithm)

            # Step 3: Filter small communities
            filtered_communities = self._filter_communities(
                communities, min_community_size
            )

            # Step 4: Enrich communities with metadata
            enriched_communities = await self._enrich_communities(filtered_communities)

            # Step 5: Generate community summaries (using LLM)
            await self._generate_community_summaries(enriched_communities)

            # Step 6: Store communities in graph
            await self._store_communities(enriched_communities)

            # Clean up projection
            await self._drop_graph_projection(graph_name)

            result = {
                "total_communities": len(enriched_communities),
                "total_entities": sum(c["size"] for c in enriched_communities),
                "algorithm": algorithm,
                "communities": enriched_communities,
                "timestamp": datetime.now().isoformat(),
            }

            self.logger.info(f"Detected {len(enriched_communities)} communities")
            return result

        except Exception as e:
            self.logger.error(f"Community detection failed: {str(e)}")
            raise

    async def _create_graph_projection(self, graph_name: str):
        """Create graph projection for community detection"""

        # Drop existing projection if it exists
        await self._drop_graph_projection(graph_name)

        query = """
        CALL gds.graph.project(
            $graphName,
            'Entity',
            {
                MENTIONS: {orientation: 'UNDIRECTED'},
                RELATED_TO: {orientation: 'UNDIRECTED'},
                USES: {orientation: 'UNDIRECTED'},
                SUPPORTS: {orientation: 'UNDIRECTED'},
                EXTENDS: {orientation: 'UNDIRECTED'}
            }
        )
        YIELD graphName, nodeCount, relationshipCount
        RETURN graphName, nodeCount, relationshipCount
        """

        try:
            results = await helix_store.list_papers(limit=100)
            if result:
                self.logger.info(
                    f"Created graph projection: {result[0]['nodeCount']} nodes, "
                    f"{result[0]['relationshipCount']} relationships"
                )
        except Exception as e:
            # If GDS is not available, we'll use a simpler approach
            self.logger.warning(f"GDS not available, using simple clustering: {str(e)}")

    async def _drop_graph_projection(self, graph_name: str):
        """Drop graph projection"""
        query = """
        CALL gds.graph.exists($graphName) YIELD exists
        WITH exists
        WHERE exists = true
        CALL gds.graph.drop($graphName) YIELD graphName
        RETURN graphName
        """

        try:
            results = []  # Placeholder for GDS operations
        except:
            pass  # Ignore if doesn't exist

    async def _run_community_algorithm(
        self, graph_name: str, algorithm: str
    ) -> List[Dict[str, Any]]:
        """Run community detection algorithm"""

        if algorithm == "louvain":
            query = """
            CALL gds.louvain.stream($graphName)
            YIELD nodeId, communityId
            WITH gds.util.asNode(nodeId) AS entity, communityId
            RETURN communityId,
                   collect({
                       id: id(entity),
                       name: entity.name,
                       type: entity.type
                   }) as members
            """
        elif algorithm == "label_propagation":
            query = """
            CALL gds.labelPropagation.stream($graphName)
            YIELD nodeId, communityId
            WITH gds.util.asNode(nodeId) AS entity, communityId
            RETURN communityId,
                   collect({
                       id: id(entity),
                       name: entity.name,
                       type: entity.type
                   }) as members
            """
        else:  # Simple connected components as fallback
            query = """
            MATCH (e:Entity)-[r:RELATED_TO|USES|SUPPORTS|EXTENDS]-(e2:Entity)
            WITH e, collect(DISTINCT e2) as connected
            RETURN id(e) as communityId,
                   collect({
                       id: id(e),
                       name: e.name,
                       type: e.type
                   }) + [n IN connected | {id: id(n), name: n.name, type: n.type}] as members
            LIMIT 100
            """

        try:
            results = results = []  # Placeholder for GDS operations
            communities = []

            for record in results:
                communities.append(
                    {
                        "id": f"community_{record['communityId']}",
                        "members": record["members"],
                        "size": len(record["members"]),
                    }
                )

            return communities
        except Exception as e:
            self.logger.warning(f"GDS algorithm failed, using fallback: {str(e)}")
            # Fallback to simple entity clustering by type
            return await self._simple_clustering()

    async def _simple_clustering(self) -> List[Dict[str, Any]]:
        """Simple clustering fallback when GDS is not available"""
        query = """
        MATCH (e:Entity)
        WITH e.type as entityType, collect(e) as entities
        WHERE size(entities) >= 3
        RETURN entityType as communityId,
               [entity IN entities | {
                   id: id(entity),
                   name: entity.name,
                   type: entity.type
               }] as members
        """

        results = await helix_store.list_papers(limit=100)
        communities = []

        for i, record in enumerate(results):
            communities.append(
                {
                    "id": f"community_{i}",
                    "members": record["members"],
                    "size": len(record["members"]),
                    "type_based": True,
                    "primary_type": record["communityId"],
                }
            )

        return communities

    def _filter_communities(
        self, communities: List[Dict[str, Any]], min_size: int
    ) -> List[Dict[str, Any]]:
        """Filter out small communities"""
        filtered = [c for c in communities if c["size"] >= min_size]
        self.logger.info(
            f"Filtered {len(communities)} communities to {len(filtered)} "
            f"(min size: {min_size})"
        )
        return filtered

    async def _enrich_communities(
        self, communities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enrich communities with additional metadata"""

        enriched = []

        for community in communities:
            # Get entity names
            entity_names = [m["name"] for m in community["members"]]

            # Get entity types distribution
            type_counts = {}
            for member in community["members"]:
                etype = member.get("type", "unknown")
                type_counts[etype] = type_counts.get(etype, 0) + 1

            # Get papers that mention these entities
            query = """
            MATCH (p:Paper)-[:MENTIONS]->(e:Entity)
            WHERE e.name IN $entityNames
            WITH p, count(DISTINCT e) as mentionCount
            ORDER BY mentionCount DESC
            LIMIT 10
            RETURN p.arxiv_id as arxiv_id,
                   p.title as title,
                   mentionCount
            """

            papers = await helix_store.list_papers(
                query, {"entityNames": entity_names}
            )

            # Determine primary topic based on most common entity types and names
            primary_entities = sorted(
                entity_names, key=lambda x: entity_names.count(x), reverse=True
            )[:5]

            enriched.append(
                {
                    **community,
                    "primary_entities": primary_entities,
                    "entity_types": type_counts,
                    "top_papers": papers[:5] if papers else [],
                    "paper_count": len(papers) if papers else 0,
                }
            )

        return enriched

    async def _generate_community_summaries(self, communities: List[Dict[str, Any]]):
        """Generate LLM summaries for each community"""

        from app.services.entity_extractor import EntityExtractor

        extractor = EntityExtractor()

        for community in communities:
            try:
                # Build context for summary
                entity_list = ", ".join(community["primary_entities"][:10])
                paper_titles = [p["title"] for p in community.get("top_papers", [])]
                papers_context = "\n".join([f"- {t}" for t in paper_titles[:5]])

                prompt = f"""Analyze this research community and provide a concise summary.

Entities in this community: {entity_list}

Related papers:
{papers_context}

Provide a 2-3 sentence summary covering:
1. The main research theme/topic
2. Key approaches or methods
3. The research domain (e.g., NLP, Computer Vision, etc.)

Summary:"""

                # Generate summary
                response = await extractor.client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.7,
                )

                summary = response.choices[0].message.content.strip()

                # Generate a name based on top entities
                name_prompt = f"""Given these research entities: {entity_list}

Generate a concise, descriptive name for this research topic (max 5 words).

Examples:
- "Graph Neural Networks"
- "Transformer Architectures"
- "Few-Shot Learning Methods"

Name:"""

                name_response = await extractor.client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[{"role": "user", "content": name_prompt}],
                    max_tokens=20,
                    temperature=0.5,
                )

                name = name_response.choices[0].message.content.strip().strip('"')

                community["summary"] = summary
                community["name"] = name

            except Exception as e:
                self.logger.error(f"Failed to generate summary: {str(e)}")
                # Fallback to simple name
                community["name"] = (
                    f"Research Topic: {community['primary_entities'][0]}"
                )
                community["summary"] = (
                    f"Research community focused on {', '.join(community['primary_entities'][:3])}"
                )

    async def _store_communities(self, communities: List[Dict[str, Any]]):
        """Store community information in Neo4j"""

        for community in communities:
            # Create Community node
            create_query = """
            MERGE (c:Community {id: $id})
            SET c.name = $name,
                c.summary = $summary,
                c.size = $size,
                c.paper_count = $paperCount,
                c.entity_types = $entityTypes,
                c.updated_at = datetime()
            RETURN c
            """

            results = await helix_store.list_papers(limit=100)
            # Placeholder - GDS operations need Neo4j
            results = []

            # Link entities to community
            link_query = """
            MATCH (c:Community {id: $communityId})
            MATCH (e:Entity)
            WHERE e.name IN $entityNames
            MERGE (e)-[:BELONGS_TO]->(c)
            """

            entity_names = [m["name"] for m in community["members"]]
            results = await helix_store.list_papers(limit=100)
            # Using helix_store instead of neo4j_client
            # link_query would need Neo4j session - placeholder
            link_query = "MATCH (c:Community {id: $communityId}) RETURN c"
            {"communityId": community["id"], "entityNames": entity_names}

        self.logger.info(f"Stored {len(communities)} communities in graph")

    async def get_communities(self) -> List[Dict[str, Any]]:
        """Retrieve all detected communities"""

        query = """
        MATCH (c:Community)
        OPTIONAL MATCH (e:Entity)-[:BELONGS_TO]->(c)
        WITH c, collect(e.name) as entities
        RETURN c.id as id,
               c.name as name,
               c.summary as summary,
               c.size as size,
               c.paper_count as paperCount,
               entities[..10] as topEntities
        ORDER BY c.size DESC
        """

        results = await helix_store.list_papers(limit=100)

        communities = []
        for record in results:
            communities.append(
                {
                    "id": record["id"],
                    "name": record["name"],
                    "summary": record["summary"],
                    "size": record["size"],
                    "paper_count": record.get("paperCount", 0),
                    "top_entities": record.get("topEntities", []),
                }
            )

        return communities

    async def get_community_details(
        self, community_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific community"""

        query = """
        MATCH (c:Community {id: $communityId})
        OPTIONAL MATCH (e:Entity)-[:BELONGS_TO]->(c)
        OPTIONAL MATCH (p:Paper)-[:MENTIONS]->(e)
        WITH c,
             collect(DISTINCT e) as entities,
             collect(DISTINCT p) as papers
        RETURN c.id as id,
               c.name as name,
               c.summary as summary,
               c.size as size,
               [e IN entities | {name: e.name, type: e.type}] as entities,
               [p IN papers | {
                   arxiv_id: p.arxiv_id,
                   title: p.title,
                   authors: p.authors
               }][..20] as topPapers
        """

        results = await helix_store.list_papers(limit=100)  # Placeholder for GDS query

        if not results:
            return None

        record = results[0]
        return {
            "id": record["id"],
            "name": record["name"],
            "summary": record["summary"],
            "size": record["size"],
            "entities": record["entities"],
            "papers": record.get("topPapers", []),
        }


# Global community detector instance
community_detector = CommunityDetector()


async def detect_research_communities(
    algorithm: str = "louvain", min_size: int = 3
) -> Dict[str, Any]:
    """Detect research communities in the knowledge graph"""
    return await community_detector.detect_communities(algorithm, min_size)


async def get_all_communities() -> List[Dict[str, Any]]:
    """Get all detected communities"""
    return await community_detector.get_communities()


async def get_community_by_id(community_id: str) -> Optional[Dict[str, Any]]:
    """Get details of a specific community"""
    return await community_detector.get_community_details(community_id)
