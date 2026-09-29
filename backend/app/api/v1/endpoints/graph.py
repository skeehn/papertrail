from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query

from app.core.cache import cached
from app.core.logging import get_logger, log_graph_operation
from app.database.mock_store import mock_store
from app.database import get_paper_entities, get_graph_statistics, HELIXDB_CONNECTED, helix_store
from app.database.hydradb_store import hydradb_store
from app.models.schemas import GraphQueryRequest, GraphResponse

router = APIRouter()
logger = get_logger("graph")


async def get_entity_subgraph(
    entity_name: str, depth: int = 1
) -> tuple:
    """Build a nodes/edges subgraph for an entity by matching papers whose
    text mentions it (HydraDB has no graph traversals; search stands in)."""
    nodes_by_id: dict = {}
    edges: List[dict] = []

    matching = await hydradb_store.list_papers(search=entity_name, limit=25)
    for _ in range(max(1, min(depth, 2)) - 1):
        if not matching:
            break
        # Expand one hop via shared entities.
        related = await hydradb_store.get_related_papers(matching[0].get("arxiv_id", ""), limit=25)
        for rel in related:
            if rel not in matching:
                matching.append(rel)

    for rank, paper in enumerate(matching):
        pid = paper.get("arxiv_id", "")
        if not pid or pid in nodes_by_id:
            continue
        nodes_by_id[pid] = {
            "id": pid,
            "label": (paper.get("title") or pid)[:60],
            "type": "Paper",
            "properties": {"title": paper.get("title", ""), "rank": rank},
        }
        edges.append(
            {
                "source": entity_name,
                "target": pid,
                "type": "MENTIONS",
                "properties": {},
            }
        )

    nodes_by_id.setdefault(
        entity_name,
        {
            "id": entity_name,
            "label": entity_name,
            "type": "Entity",
            "properties": {},
        },
    )
    return list(nodes_by_id.values()), edges


@router.post("/query", response_model=GraphResponse)
@cached(ttl_seconds=3600, key_prefix="graph_query:")  # Cache for 1 hour
async def query_graph(request: GraphQueryRequest):
    """Query the knowledge graph for nodes and relationships"""
    try:
        # Log graph operation
        log_graph_operation(
            "graph_query",
            entity_name=request.entity_name,
            paper_id=request.paper_id,
            depth=request.depth,
        )

        if request.entity_name:
            try:
                nodes, edges = await get_entity_subgraph(request.entity_name, request.depth)

                # Format nodes for response
                formatted_nodes = []
                for node in nodes:
                    formatted_nodes.append(
                        {
                            "id": node.get("id", ""),
                            "label": node.get("label", ""),
                            "type": node.get("type", "Entity"),
                            "properties": node.get("properties", {}),
                        }
                    )

                # Format edges for response
                formatted_edges = []
                for edge in edges:
                    formatted_edges.append(
                        {
                            "source": edge.get("source", ""),
                            "target": edge.get("target", ""),
                            "type": edge.get("type", "RELATED_TO"),
                            "properties": edge.get("properties", {}),
                        }
                    )

                return GraphResponse(nodes=formatted_nodes, edges=formatted_edges)
            except Exception as e:
                logger.warning(f"Neo4j query failed, using fallback: {e}")
                # Fallback to empty response if Neo4j fails
                return GraphResponse(nodes=[], edges=[])

        elif request.paper_id:
            # TODO: Implement paper-centric graph query
            # For now, return entities related to the paper
            try:
                from app.database import get_paper_entities

                entities = get_paper_entities(request.paper_id)

                nodes = []
                for entity in entities:
                    nodes.append(
                        {
                            "id": entity.get("name", ""),
                            "label": entity.get("name", ""),
                            "type": entity.get("type", "Entity"),
                            "properties": entity,
                        }
                    )

                return GraphResponse(nodes=nodes, edges=[])
            except Exception as e:
                logger.warning(f"Paper entities query failed: {e}")
                return GraphResponse(nodes=[], edges=[])

        else:
            # No specific entity/paper: return an overview of the graph
            # (papers + the entities they mention) so the page has content.
            try:
                from app.database import HELIXDB_CONNECTED, helix_store

                if not HELIXDB_CONNECTED:
                    return GraphResponse(nodes=[], edges=[])

                nodes_by_id: dict = {}
                edges = []
                papers = await helix_store.list_papers(skip=0, limit=200)
                for paper in papers:
                    pid = paper.get("arxiv_id", "")
                    if pid and pid not in nodes_by_id:
                        nodes_by_id[pid] = {
                            "id": pid,
                            "label": (paper.get("title", pid) or pid)[:60],
                            "type": "Paper",
                            "properties": {"title": paper.get("title", "")},
                        }
                    entities = await helix_store.get_paper_entities(pid)
                    for entity in entities:
                        ename = entity.get("name", "")
                        if ename and ename not in nodes_by_id:
                            nodes_by_id[ename] = {
                                "id": ename,
                                "label": ename,
                                "type": entity.get("type", "Entity"),
                                "properties": {},
                            }
                        if pid and ename:
                            edges.append({
                                "source": pid,
                                "target": ename,
                                "type": "MENTIONS",
                                "properties": {},
                            })
                return GraphResponse(nodes=list(nodes_by_id.values()), edges=edges)
            except Exception as e:
                logger.warning(f"Overview graph query failed: {e}")
                return GraphResponse(nodes=[], edges=[])

    except Exception as e:
        logger.error("Graph query failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Graph query failed: {str(e)}")


@router.get("/statistics")
@cached(ttl_seconds=1800, key_prefix="graph_stats:")  # Cache for 30 minutes
async def get_graph_statistics_endpoint():
    """Get statistics about the knowledge graph"""
    try:
        # Log graph operation
        log_graph_operation("statistics_retrieval")

        # Try to get real statistics from Neo4j
        try:
            from app.database import get_graph_statistics

            stats = get_graph_statistics()

            # Format statistics
            node_count = sum(stats.get("nodes", {}).values())
            relationship_count = sum(stats.get("relationships", {}).values())

            return {
                "statistics": {
                    "node_count": node_count,
                    "relationship_count": relationship_count,
                    "node_types": stats.get("nodes", {}),
                    "relationship_types": stats.get("relationships", {}),
                },
                "timestamp": datetime.utcnow().isoformat(),
                "source": "helixdb",
            }
        except Exception as e:
            logger.warning(f"Neo4j statistics failed, using fallback: {e}")
            # Fallback to mock store if Neo4j fails
        memory_count = (
            len(mock_store.entities) if hasattr(mock_store, "entities") else 0
        )
        paper_count = len(mock_store.papers) if hasattr(mock_store, "papers") else 0
        relationship_count = (
            len(mock_store.relationships) if hasattr(mock_store, "relationships") else 0
        )

        stats = {
            "node_count": memory_count + paper_count,
            "relationship_count": relationship_count,
            "node_types": {
                "Memory": memory_count,
                "Paper": paper_count,
                "Entity": max(0, memory_count // 3),
                "Concept": max(0, memory_count // 5),
            },
            "relationship_types": {
                "MENTIONS": max(0, memory_count // 2),
                "RELATES_TO": max(0, memory_count // 3),
                "AUTHORED_BY": paper_count * 2 if paper_count > 0 else 0,
                "CITES": max(0, paper_count // 2),
            },
        }

        return {
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "mock_store",
        }

    except Exception as e:
        logger.error("Failed to get graph statistics", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to retrieve graph statistics"
        )


@router.get("/nodes")
async def get_graph_nodes(
    node_type: Optional[str] = Query(None, description="Filter by node type"),
    limit: int = Query(100, ge=1, le=1000, description="Number of nodes to return"),
    skip: int = Query(0, ge=0, description="Number of nodes to skip"),
):
    """Get nodes from the knowledge graph"""
    try:
        from app.database import helix_store

        if not helix_store.is_connected:
            return {"nodes": [], "total": 0, "limit": limit, "skip": skip}

        # Get papers from HelixDB
        papers = await helix_store.list_papers(skip=skip, limit=limit)

        nodes = []
        for paper in papers:
            nodes.append(
                {
                    "id": paper.get("id", paper.get("arxiv_id", "")),
                    "label": paper.get("title", ""),
                    "type": "Paper",
                    "properties": paper,
                }
            )

        total = len(nodes)

        return {"nodes": nodes, "total": total, "limit": limit, "skip": skip}
    except Exception as e:
        logger.error("Failed to get graph nodes", error=str(e))
        # Return empty result on error rather than failing
        return {"nodes": [], "total": 0, "limit": limit, "skip": skip}

@router.get("/edges")
async def get_graph_edges(
    edge_type: Optional[str] = Query(None, description="Filter by edge type"),
    limit: int = Query(100, ge=1, le=1000, description="Number of edges to return"),
    skip: int = Query(0, ge=0, description="Number of edges to skip"),
):
    """Get edges from the knowledge graph"""
    try:
        from app.database import helix_store

        if not helix_store.is_connected:
            return {"edges": [], "total": 0, "limit": limit, "skip": skip}

        # Get papers from HelixDB
        papers = await helix_store.list_papers(skip=skip, limit=max(limit + skip, 20))

        # Build edges from stored relationships
        edges = []
        
        # Use helix_store to get entities and relationships
        # For now, return basic structure
        for paper in papers[:limit]:
            paper_id = paper.get("arxiv_id", "")
            entities = await helix_store.get_paper_entities(paper_id)
            for entity in entities[:5]:  # Limit entities per paper
                entity_name = entity.get("name", "")
                if entity_name:
                    edges.append({
                        "source": paper_id,
                        "target": entity_name,
                        "type": "MENTIONS",
                        "properties": {}
                    })

        # Get total count approximation
        total_papers = await helix_store.list_papers(limit=1)
        total = len(total_papers) if total_papers else 0

        return {"edges": edges, "total": total, "limit": limit, "skip": skip}

    except Exception as e:
        logger.error("Failed to get graph edges", error=str(e))
        # Return empty result on error rather than failing
        return {"edges": [], "total": 0, "limit": limit, "skip": skip}


@router.get("/communities")
async def get_graph_communities(
    algorithm: str = Query("louvain", description="Community detection algorithm"),
    min_size: int = Query(3, ge=1, description="Minimum community size"),
):
    """Get communities in the knowledge graph"""
    try:
        # TODO: Implement community detection
        communities = []

        return {
            "communities": communities,
            "algorithm": algorithm,
            "total_communities": len(communities),
        }

    except Exception as e:
        logger.error("Failed to get graph communities", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to retrieve graph communities"
        )


@router.get("/centrality")
async def get_node_centrality(
    centrality_type: str = Query(
        "betweenness", description="Type of centrality measure"
    ),
    limit: int = Query(20, ge=1, le=100, description="Number of top nodes to return"),
):
    """Get centrality measures for nodes"""
    try:
        # TODO: Implement centrality calculation
        centrality_scores = []

        return {
            "centrality_type": centrality_type,
            "scores": centrality_scores,
            "limit": limit,
        }

    except Exception as e:
        logger.error("Failed to get node centrality", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to retrieve node centrality"
        )


@router.get("/paths")
async def get_shortest_paths(
    source: str = Query(..., description="Source node ID"),
    target: str = Query(..., description="Target node ID"),
    max_length: int = Query(5, ge=1, le=10, description="Maximum path length"),
):
    """Get shortest paths between nodes"""
    try:
        from app.database import helix_store

        if not helix_store.is_connected:
            return {
                "source": source,
                "target": target,
                "paths": [],
                "max_length": max_length,
            }

        # Get shortest paths - use HelixDB traversal
            # Note: Graph path finding in HelixDB requires different approach
            # For now, use the list_papers method to get papers and build paths
            papers = await helix_store.list_papers(limit=100)
            paths = []

            paths = []
            for record in result:
                path = record["path"]
                path_nodes = []
                path_edges = []

                for node in path.nodes:
                    path_nodes.append(
                        {
                            "id": node.get("arxiv_id")
                            or node.get("name")
                            or str(node.id),
                            "label": node.get("title")
                            or node.get("name")
                            or str(node.id),
                            "type": list(node.labels)[0] if node.labels else "Node",
                        }
                    )

                for rel in path.relationships:
                    path_edges.append(
                        {
                            "source": str(rel.start_node.id),
                            "target": str(rel.end_node.id),
                            "type": rel.type,
                        }
                    )

                paths.append(
                    {
                        "nodes": path_nodes,
                        "edges": path_edges,
                        "length": len(path_edges),
                    }
                )

        return {
            "source": source,
            "target": target,
            "paths": paths,
            "max_length": max_length,
        }

    except Exception as e:
        logger.error("Failed to get shortest paths", error=str(e))
        # Return empty paths on error rather than failing
        return {
            "source": source,
            "target": target,
            "paths": [],
            "max_length": max_length,
        }


@router.get("/export")
async def export_graph(
    format: str = Query("json", description="Export format (json, csv, graphml)"),
    node_types: Optional[List[str]] = Query(None, description="Filter by node types"),
    edge_types: Optional[List[str]] = Query(None, description="Filter by edge types"),
):
    """Export the knowledge graph"""
    try:
        # TODO: Implement graph export
        export_data = {
            "format": format,
            "nodes": [],
            "edges": [],
            "metadata": {
                "exported_at": "2025-01-27T00:00:00Z",
                "node_count": 0,
                "edge_count": 0,
            },
        }

        return export_data

    except Exception as e:
        logger.error("Failed to export graph", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to export graph")


@router.get("/visualization")
async def get_visualization_data(
    layout: str = Query("force", description="Graph layout algorithm"),
    node_size: str = Query("degree", description="Node size metric"),
    edge_weight: str = Query("strength", description="Edge weight metric"),
):
    """Get data formatted for graph visualization"""
    try:
        # TODO: Implement visualization data preparation
        visualization_data = {
            "nodes": [],
            "edges": [],
            "layout": layout,
            "node_size": node_size,
            "edge_weight": edge_weight,
        }

        return visualization_data

    except Exception as e:
        logger.error("Failed to get visualization data", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to retrieve visualization data"
        )


@router.get("/analytics")
async def get_graph_analytics():
    """Get comprehensive graph analytics"""
    try:
        # TODO: Implement comprehensive graph analytics
        analytics = {
            "node_analytics": {
                "total_nodes": 0,
                "node_types": {},
                "degree_distribution": {},
            },
            "edge_analytics": {
                "total_edges": 0,
                "edge_types": {},
                "weight_distribution": {},
            },
            "community_analytics": {
                "total_communities": 0,
                "modularity": 0.0,
                "community_sizes": [],
            },
            "centrality_analytics": {"top_nodes": [], "centrality_distribution": {}},
        }

        return analytics

    except Exception as e:
        logger.error("Failed to get graph analytics", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to retrieve graph analytics"
        )
