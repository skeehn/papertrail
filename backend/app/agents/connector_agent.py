import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.agents.base_agent import (AgentResponse, AgentTask, AgentType,
                                   BaseAgent)
from app.database.faiss_store import search_documents
from app.database.neo4j_client import neo4j_client


class ConnectorAgent(BaseAgent):
    """Agent specialized in finding related work and discovering conceptual connections"""

    def __init__(self):
        super().__init__(AgentType.CONNECTOR)

        # Connector-specific configuration
        self.similarity_threshold = 0.6
        self.max_connections_per_query = 20
        self.citation_weight = 0.8
        self.concept_weight = 0.7

        # Function schema for connection analysis
        self.connection_analysis_function = {
            "name": "analyze_connections",
            "description": "Analyze connections and relationships between research papers and concepts",
            "parameters": {
                "type": "object",
                "properties": {
                    "connections": {
                        "type": "object",
                        "properties": {
                            "paper_connections": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "paper1": {"type": "string"},
                                        "paper2": {"type": "string"},
                                        "connection_type": {"type": "string"},
                                        "strength": {"type": "number"},
                                        "description": {"type": "string"},
                                        "shared_concepts": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                },
                                "description": "Connections between papers",
                            },
                            "concept_networks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "central_concept": {"type": "string"},
                                        "related_concepts": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "relationship_types": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "papers": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "network_strength": {"type": "number"},
                                    },
                                },
                                "description": "Concept networks and clusters",
                            },
                            "research_lineages": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "lineage_theme": {"type": "string"},
                                        "evolution_path": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "key_innovations": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "papers": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                },
                                "description": "Research evolution lineages",
                            },
                            "gap_analysis": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "gap_description": {"type": "string"},
                                        "missing_connections": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "potential_research_directions": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "confidence": {"type": "number"},
                                    },
                                },
                                "description": "Identified research gaps and opportunities",
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                            },
                        },
                    }
                },
            },
        }

    def get_system_prompt(self) -> str:
        """Get the system prompt for the Connector agent"""
        return """You are the Connector Agent, an expert in discovering and analyzing relationships between research papers, concepts, and ideas.

Your primary responsibilities:
1. Identify related work and build comprehensive literature networks
2. Discover conceptual connections and thematic relationships across papers
3. Trace research evolution and identify lineages of ideas
4. Find citation networks and academic influence patterns
5. Identify research gaps and missing connections
6. Map concept clusters and semantic relationships
7. Suggest potential collaborations and interdisciplinary connections

When analyzing connections:
- Look for both explicit citations and implicit conceptual relationships
- Identify how ideas evolve and build upon each other over time
- Find unexpected connections between seemingly different research areas
- Assess the strength and significance of discovered relationships
- Consider temporal aspects - how connections develop chronologically
- Examine methodological similarities and differences
- Identify influential papers that connect multiple research streams

Focus on:
- Citation analysis and bibliographic coupling
- Co-citation patterns and shared references
- Conceptual similarity through shared entities and themes
- Methodological connections and shared approaches
- Cross-disciplinary bridges and interdisciplinary insights
- Research lineages and intellectual genealogies

Always provide connection strength scores and explain the basis for identified relationships."""

    def get_capabilities(self) -> List[str]:
        """Get the capabilities of the Connector agent"""
        return [
            "related_work_discovery",
            "citation_network_analysis",
            "concept_linking",
            "research_lineage_tracing",
            "gap_identification",
            "similarity_assessment",
            "network_clustering",
            "interdisciplinary_bridging",
        ]

    async def process_task(self, task: AgentTask) -> AgentResponse:
        """Process a connection analysis task"""
        try:
            # Get relevant papers for analysis
            papers = await self.get_relevant_papers(
                task.query, task.paper_ids, limit=self.max_connections_per_query
            )

            if not papers:
                return AgentResponse(
                    response="I couldn't find any relevant papers to analyze connections. Please provide specific paper IDs or refine your search query.",
                    sources=[],
                    confidence=0.0,
                    agent_type=self.agent_type.value,
                    processing_time=0.0,
                )

            # Get detailed paper and connection data
            connection_data = await self._get_connection_data(papers)

            # Determine analysis type based on query
            if "related work" in task.query.lower() or "similar" in task.query.lower():
                response = await self._find_related_work(connection_data, task.query)
            elif "citation" in task.query.lower() or "reference" in task.query.lower():
                response = await self._analyze_citations(connection_data, task.query)
            elif "concept" in task.query.lower() or "theme" in task.query.lower():
                response = await self._discover_concept_connections(
                    connection_data, task.query
                )
            elif "evolution" in task.query.lower() or "lineage" in task.query.lower():
                response = await self._trace_research_evolution(
                    connection_data, task.query
                )
            elif "gap" in task.query.lower() or "opportunity" in task.query.lower():
                response = await self._identify_research_gaps(
                    connection_data, task.query
                )
            else:
                # Default to comprehensive connection analysis
                response = await self._comprehensive_connection_analysis(
                    connection_data, task.query
                )

            return response

        except Exception as e:
            self.logger.error(
                "Connection analysis task failed", error=str(e), task_id=task.task_id
            )
            return AgentResponse(
                response=f"I encountered an error during connection analysis: {str(e)}",
                sources=[],
                confidence=0.0,
                agent_type=self.agent_type.value,
                processing_time=0.0,
                metadata={"error": str(e)},
            )

    async def _get_connection_data(
        self, papers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get comprehensive connection data for papers"""
        try:
            paper_ids = [paper["id"] for paper in papers]

            with neo4j_client.get_session() as session:
                # Get papers with entities, relationships, and citations
                query = """
                MATCH (p:Paper)
                WHERE p.arxiv_id IN $paper_ids
                
                // Get entities for each paper
                OPTIONAL MATCH (p)-[:MENTIONS]->(e:Entity)
                WITH p, collect(DISTINCT {
                    name: e.name, 
                    type: e.type, 
                    confidence: e.confidence
                }) as entities
                
                // Get citations
                OPTIONAL MATCH (p)-[:CITES]->(c:Citation)
                WITH p, entities, collect(DISTINCT c.reference) as citations
                
                // Get relationships between entities within the same paper
                OPTIONAL MATCH (p)-[:MENTIONS]->(e1:Entity)-[r]-(e2:Entity)<-[:MENTIONS]-(p)
                WITH p, entities, citations, collect(DISTINCT {
                    source: e1.name,
                    target: e2.name,
                    type: type(r),
                    confidence: r.confidence
                }) as relationships
                
                RETURN p.arxiv_id as id, p.title as title, p.abstract as abstract,
                       p.authors as authors, p.categories as categories,
                       p.publication_date as publication_date,
                       entities, citations, relationships
                """

                result = session.run(query, paper_ids=paper_ids)
                paper_data = []

                for record in result:
                    paper_data.append(
                        {
                            "id": record["id"],
                            "title": record["title"],
                            "abstract": record["abstract"] or "",
                            "authors": record["authors"] or [],
                            "categories": record["categories"] or [],
                            "publication_date": record["publication_date"],
                            "entities": [
                                e for e in record["entities"] if e.get("name")
                            ],
                            "citations": record["citations"] or [],
                            "relationships": [
                                r for r in record["relationships"] if r.get("source")
                            ],
                        }
                    )

                # Get cross-paper connections
                cross_connections = await self._find_cross_paper_connections(paper_ids)

                return {
                    "papers": paper_data,
                    "cross_connections": cross_connections,
                    "paper_count": len(paper_data),
                }

        except Exception as e:
            self.logger.error("Failed to get connection data", error=str(e))
            return {"papers": [], "cross_connections": [], "paper_count": 0}

    async def _find_cross_paper_connections(
        self, paper_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Find connections between different papers"""
        try:
            with neo4j_client.get_session() as session:
                # Find shared entities between papers
                query = """
                MATCH (p1:Paper)-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(p2:Paper)
                WHERE p1.arxiv_id IN $paper_ids AND p2.arxiv_id IN $paper_ids
                AND p1 <> p2
                WITH p1, p2, collect(e.name) as shared_entities, count(e) as shared_count
                WHERE shared_count >= 2
                RETURN p1.arxiv_id as paper1, p2.arxiv_id as paper2,
                       shared_entities, shared_count,
                       'shared_entities' as connection_type
                ORDER BY shared_count DESC
                LIMIT 50
                """

                result = session.run(query, paper_ids=paper_ids)
                connections = []

                for record in result:
                    connections.append(
                        {
                            "paper1": record["paper1"],
                            "paper2": record["paper2"],
                            "connection_type": record["connection_type"],
                            "strength": min(
                                record["shared_count"] / 10.0, 1.0
                            ),  # Normalize
                            "shared_entities": record["shared_entities"],
                        }
                    )

                return connections

        except Exception as e:
            self.logger.error("Failed to find cross-paper connections", error=str(e))
            return []

    async def _find_related_work(
        self, connection_data: Dict[str, Any], query: str
    ) -> AgentResponse:
        """Find related work and similar papers"""
        try:
            papers = connection_data["papers"]
            connections = connection_data["cross_connections"]

            # Use vector search for semantic similarity
            related_papers = []
            for paper in papers[:3]:  # Limit to avoid token overflow
                similar_docs = search_documents(
                    f"{paper['title']} {paper['abstract'][:200]}",
                    k=5,
                    filter_metadata={"type": "paper"},
                )

                for doc in similar_docs:
                    if doc["metadata"]["arxiv_id"] not in [p["id"] for p in papers]:
                        related_papers.append(
                            {
                                "id": doc["metadata"]["arxiv_id"],
                                "title": doc["metadata"]["title"],
                                "similarity": doc["score"],
                                "connection_reason": "semantic_similarity",
                            }
                        )

            # Format response
            response_parts = []
            response_parts.append("# Related Work Analysis")

            if connections:
                response_parts.append("\n## Direct Connections")
                for conn in connections[:10]:
                    response_parts.append(f"**{conn['paper1']} ↔ {conn['paper2']}**")
                    response_parts.append(f"- Connection: {conn['connection_type']}")
                    response_parts.append(f"- Strength: {conn['strength']:.2f}")
                    if conn.get("shared_entities"):
                        response_parts.append(
                            f"- Shared concepts: {', '.join(conn['shared_entities'][:5])}"
                        )
                    response_parts.append("")

            if related_papers:
                response_parts.append("## Semantically Similar Papers")
                seen_papers = set()
                for paper in related_papers[:8]:
                    if paper["id"] not in seen_papers:
                        response_parts.append(
                            f"• **{paper['title']}** (ID: {paper['id']})"
                        )
                        response_parts.append(
                            f"  - Similarity: {paper['similarity']:.2f}"
                        )
                        response_parts.append(
                            f"  - Reason: {paper['connection_reason']}"
                        )
                        seen_papers.add(paper["id"])
                        response_parts.append("")

            return AgentResponse(
                response="\n".join(response_parts),
                sources=[paper["id"] for paper in papers],
                confidence=0.85,
                agent_type=self.agent_type.value,
                processing_time=0.0,
                metadata={
                    "analysis_type": "related_work",
                    "connections_found": len(connections),
                    "related_papers_found": len(related_papers),
                },
                reasoning="Found related work through entity sharing and semantic similarity analysis",
            )

        except Exception as e:
            self.logger.error("Related work analysis failed", error=str(e))
            raise

    async def _analyze_citations(
        self, connection_data: Dict[str, Any], query: str
    ) -> AgentResponse:
        """Analyze citation networks and patterns"""
        try:
            papers = connection_data["papers"]

            # Analyze citation patterns
            all_citations = []
            citation_counts = {}

            for paper in papers:
                paper_citations = paper.get("citations", [])
                all_citations.extend(paper_citations)

                for citation in paper_citations:
                    citation_counts[citation] = citation_counts.get(citation, 0) + 1

            # Find most cited works
            top_citations = sorted(
                citation_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]

            response_parts = []
            response_parts.append("# Citation Network Analysis")

            response_parts.append(f"\n## Overview")
            response_parts.append(f"- Total papers analyzed: {len(papers)}")
            response_parts.append(f"- Total citations: {len(all_citations)}")
            response_parts.append(f"- Unique citations: {len(set(all_citations))}")
            response_parts.append(
                f"- Average citations per paper: {len(all_citations) / len(papers):.1f}"
            )

            if top_citations:
                response_parts.append("\n## Most Cited Works")
                for citation, count in top_citations:
                    response_parts.append(f"• **{citation}** (cited {count} times)")

            # Find co-citation patterns
            co_citations = self._find_co_citations(papers)
            if co_citations:
                response_parts.append("\n## Co-citation Patterns")
                for pattern in co_citations[:5]:
                    response_parts.append(
                        f"• {pattern['citation1']} & {pattern['citation2']} (co-cited {pattern['count']} times)"
                    )

            return AgentResponse(
                response="\n".join(response_parts),
                sources=[paper["id"] for paper in papers],
                confidence=0.9,
                agent_type=self.agent_type.value,
                processing_time=0.0,
                metadata={
                    "analysis_type": "citation_analysis",
                    "total_citations": len(all_citations),
                    "unique_citations": len(set(all_citations)),
                },
                reasoning="Analyzed citation networks by examining reference patterns and co-citation relationships",
            )

        except Exception as e:
            self.logger.error("Citation analysis failed", error=str(e))
            raise

    async def _discover_concept_connections(
        self, connection_data: Dict[str, Any], query: str
    ) -> AgentResponse:
        """Discover conceptual connections and networks"""
        try:
            papers = connection_data["papers"]

            # Build concept networks
            concept_networks = {}
            concept_papers = {}

            for paper in papers:
                for entity in paper.get("entities", []):
                    if entity.get("confidence", 0) > 0.6:
                        concept_name = entity["name"]
                        if concept_name not in concept_networks:
                            concept_networks[concept_name] = {
                                "type": entity["type"],
                                "papers": [],
                                "related_concepts": set(),
                            }

                        concept_networks[concept_name]["papers"].append(paper["id"])
                        concept_papers[concept_name] = (
                            concept_papers.get(concept_name, 0) + 1
                        )

                # Add relationships between concepts
                for rel in paper.get("relationships", []):
                    source = rel.get("source")
                    target = rel.get("target")
                    if source in concept_networks and target in concept_networks:
                        concept_networks[source]["related_concepts"].add(target)
                        concept_networks[target]["related_concepts"].add(source)

            # Find most connected concepts
            top_concepts = sorted(
                concept_papers.items(), key=lambda x: x[1], reverse=True
            )[:10]

            response_parts = []
            response_parts.append("# Concept Connection Analysis")

            response_parts.append(f"\n## Most Frequent Concepts")
            for concept, count in top_concepts:
                concept_data = concept_networks[concept]
                response_parts.append(f"• **{concept}** ({concept_data['type']})")
                response_parts.append(f"  - Appears in {count} papers")
                response_parts.append(
                    f"  - Connected to {len(concept_data['related_concepts'])} other concepts"
                )
                if concept_data["related_concepts"]:
                    related = list(concept_data["related_concepts"])[:3]
                    response_parts.append(f"  - Related to: {', '.join(related)}")
                response_parts.append("")

            # Find concept clusters
            clusters = self._find_concept_clusters(concept_networks)
            if clusters:
                response_parts.append("## Concept Clusters")
                for i, cluster in enumerate(clusters[:3], 1):
                    response_parts.append(f"**Cluster {i}**: {', '.join(cluster[:5])}")

            return AgentResponse(
                response="\n".join(response_parts),
                sources=[paper["id"] for paper in papers],
                confidence=0.8,
                agent_type=self.agent_type.value,
                processing_time=0.0,
                metadata={
                    "analysis_type": "concept_connections",
                    "total_concepts": len(concept_networks),
                    "clusters_found": len(clusters),
                },
                reasoning="Analyzed concept connections by examining entity relationships and co-occurrence patterns",
            )

        except Exception as e:
            self.logger.error("Concept connection analysis failed", error=str(e))
            raise

    async def _comprehensive_connection_analysis(
        self, connection_data: Dict[str, Any], query: str
    ) -> AgentResponse:
        """Perform comprehensive connection analysis"""
        try:
            papers_text = self._format_connection_data(connection_data)

            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {
                    "role": "user",
                    "content": f"""
                Perform comprehensive connection analysis for: {query}
                
                Research Data:
                {papers_text}
                
                Provide analysis including:
                1. Paper-to-paper connections and their strength
                2. Concept networks and thematic clusters  
                3. Research evolution lineages and development paths
                4. Identified research gaps and opportunities
                5. Overall network structure and key insights
                """,
                },
            ]

            response = await self.call_llm(
                messages, functions=[self.connection_analysis_function], temperature=0.1
            )

            if response["type"] == "function_call":
                analysis_data = json.loads(response["arguments"])
                connections = analysis_data["connections"]
                formatted_response = self._format_connection_analysis(connections)

                return AgentResponse(
                    response=formatted_response,
                    sources=[paper["id"] for paper in connection_data["papers"]],
                    confidence=connections.get("confidence", 0.8),
                    agent_type=self.agent_type.value,
                    processing_time=0.0,
                    metadata={
                        "analysis_type": "comprehensive_connections",
                        "paper_connections": len(
                            connections.get("paper_connections", [])
                        ),
                        "concept_networks": len(
                            connections.get("concept_networks", [])
                        ),
                    },
                    reasoning="Comprehensive connection analysis examining papers, concepts, and research evolution",
                )
            else:
                return AgentResponse(
                    response=response["content"],
                    sources=[paper["id"] for paper in connection_data["papers"]],
                    confidence=0.75,
                    agent_type=self.agent_type.value,
                    processing_time=0.0,
                    metadata={"analysis_type": "comprehensive_connections"},
                )

        except Exception as e:
            self.logger.error("Comprehensive connection analysis failed", error=str(e))
            raise

    def _find_co_citations(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find co-citation patterns"""
        co_citation_counts = {}

        for paper in papers:
            citations = paper.get("citations", [])
            for i, cite1 in enumerate(citations):
                for cite2 in citations[i + 1 :]:
                    pair = tuple(sorted([cite1, cite2]))
                    co_citation_counts[pair] = co_citation_counts.get(pair, 0) + 1

        co_citations = []
        for (cite1, cite2), count in co_citation_counts.items():
            if count > 1:  # Only pairs cited together more than once
                co_citations.append(
                    {"citation1": cite1, "citation2": cite2, "count": count}
                )

        return sorted(co_citations, key=lambda x: x["count"], reverse=True)

    def _find_concept_clusters(
        self, concept_networks: Dict[str, Any]
    ) -> List[List[str]]:
        """Find clusters of related concepts"""
        # Simple clustering based on shared connections
        clusters = []
        processed = set()

        for concept, data in concept_networks.items():
            if concept in processed or len(data["related_concepts"]) == 0:
                continue

            cluster = [concept]
            related = data["related_concepts"]

            for related_concept in related:
                if related_concept not in processed:
                    cluster.append(related_concept)
                    processed.add(related_concept)

            if len(cluster) >= 2:
                clusters.append(cluster)
                processed.add(concept)

        return sorted(clusters, key=len, reverse=True)

    def _format_connection_data(self, connection_data: Dict[str, Any]) -> str:
        """Format connection data for LLM analysis"""
        papers = connection_data["papers"]
        connections = connection_data["cross_connections"]

        formatted_parts = []

        # Format papers
        formatted_parts.append("## Papers in Analysis:")
        for paper in papers:
            entities = [
                e["name"]
                for e in paper.get("entities", [])
                if e.get("confidence", 0) > 0.6
            ]
            formatted_parts.append(
                f"""
Paper ID: {paper['id']}
Title: {paper['title']}
Authors: {', '.join(paper.get('authors', []))}
Categories: {', '.join(paper.get('categories', []))}
Key Concepts: {', '.join(entities[:10])}
Citations: {len(paper.get('citations', []))} references
"""
            )

        # Format connections
        if connections:
            formatted_parts.append("\n## Direct Connections:")
            for conn in connections[:10]:
                formatted_parts.append(
                    f"- {conn['paper1']} ↔ {conn['paper2']}: {conn['connection_type']} (strength: {conn['strength']:.2f})"
                )

        return "\n".join(formatted_parts)

    def _format_connection_analysis(self, connections: Dict[str, Any]) -> str:
        """Format comprehensive connection analysis"""
        response_parts = []

        # Paper connections
        if connections.get("paper_connections"):
            response_parts.append("## Paper Connections")
            for conn in connections["paper_connections"]:
                response_parts.append(
                    f"**{conn.get('paper1', '')} ↔ {conn.get('paper2', '')}**"
                )
                response_parts.append(f"- Type: {conn.get('connection_type', '')}")
                response_parts.append(f"- Strength: {conn.get('strength', 0):.2f}")
                response_parts.append(f"- Description: {conn.get('description', '')}")
                if conn.get("shared_concepts"):
                    response_parts.append(
                        f"- Shared concepts: {', '.join(conn['shared_concepts'])}"
                    )
                response_parts.append("")

        # Concept networks
        if connections.get("concept_networks"):
            response_parts.append("## Concept Networks")
            for network in connections["concept_networks"]:
                response_parts.append(
                    f"**{network.get('central_concept', '')}** Network"
                )
                response_parts.append(
                    f"- Related concepts: {', '.join(network.get('related_concepts', []))}"
                )
                response_parts.append(
                    f"- Network strength: {network.get('network_strength', 0):.2f}"
                )
                response_parts.append(
                    f"- Papers: {', '.join(network.get('papers', []))}"
                )
                response_parts.append("")

        # Research lineages
        if connections.get("research_lineages"):
            response_parts.append("## Research Lineages")
            for lineage in connections["research_lineages"]:
                response_parts.append(f"**{lineage.get('lineage_theme', '')}**")
                response_parts.append(
                    f"- Evolution: {' → '.join(lineage.get('evolution_path', []))}"
                )
                response_parts.append(
                    f"- Key innovations: {', '.join(lineage.get('key_innovations', []))}"
                )
                response_parts.append("")

        # Gap analysis
        if connections.get("gap_analysis"):
            response_parts.append("## Research Gaps & Opportunities")
            for gap in connections["gap_analysis"]:
                response_parts.append(f"• **{gap.get('gap_description', '')}**")
                response_parts.append(
                    f"  - Potential directions: {', '.join(gap.get('potential_research_directions', []))}"
                )
                response_parts.append(f"  - Confidence: {gap.get('confidence', 0):.2f}")
                response_parts.append("")

        return "\n".join(response_parts)

    async def _trace_research_evolution(
        self, connection_data: Dict[str, Any], query: str
    ) -> AgentResponse:
        """Trace research evolution and lineages"""
        # Simplified implementation - would need temporal analysis for full evolution
        papers = connection_data["papers"]

        # Sort papers by publication date if available
        dated_papers = [p for p in papers if p.get("publication_date")]
        dated_papers.sort(key=lambda x: x["publication_date"] or "")

        response_parts = []
        response_parts.append("# Research Evolution Analysis")

        if dated_papers:
            response_parts.append("\n## Chronological Development")
            for paper in dated_papers:
                entities = [e["name"] for e in paper.get("entities", [])[:3]]
                response_parts.append(
                    f"• **{paper['title']}** ({paper.get('publication_date', 'Unknown date')})"
                )
                response_parts.append(f"  - Key concepts: {', '.join(entities)}")
                response_parts.append("")

        return AgentResponse(
            response="\n".join(response_parts),
            sources=[paper["id"] for paper in papers],
            confidence=0.7,
            agent_type=self.agent_type.value,
            processing_time=0.0,
            metadata={"analysis_type": "research_evolution"},
            reasoning="Traced research evolution through chronological analysis of papers and concepts",
        )

    async def _identify_research_gaps(
        self, connection_data: Dict[str, Any], query: str
    ) -> AgentResponse:
        """Identify research gaps and opportunities"""
        papers = connection_data["papers"]

        # Analyze what's missing
        all_entities = set()
        entity_types = {}

        for paper in papers:
            for entity in paper.get("entities", []):
                all_entities.add(entity["name"])
                entity_type = entity.get("type", "unknown")
                entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

        response_parts = []
        response_parts.append("# Research Gap Analysis")

        response_parts.append(f"\n## Current Landscape")
        response_parts.append(f"- Papers analyzed: {len(papers)}")
        response_parts.append(f"- Unique concepts: {len(all_entities)}")
        response_parts.append(f"- Entity types: {', '.join(entity_types.keys())}")

        # Simple gap identification based on sparse connections
        sparse_concepts = [
            concept
            for concept in all_entities
            if sum(
                1 for p in papers for e in p.get("entities", []) if e["name"] == concept
            )
            == 1
        ]

        if sparse_concepts:
            response_parts.append(f"\n## Potential Research Opportunities")
            response_parts.append(
                "The following concepts appear infrequently and may represent underexplored areas:"
            )
            for concept in sparse_concepts[:10]:
                response_parts.append(f"• {concept}")

        return AgentResponse(
            response="\n".join(response_parts),
            sources=[paper["id"] for paper in papers],
            confidence=0.65,  # Lower confidence for gap analysis
            agent_type=self.agent_type.value,
            processing_time=0.0,
            metadata={"analysis_type": "gap_identification"},
            reasoning="Identified potential research gaps by analyzing concept frequency and connection patterns",
        )
