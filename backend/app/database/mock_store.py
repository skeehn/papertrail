"""
Mock storage implementations for development and testing
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class MockPaperStore:
    """In-memory paper storage for development with JSON persistence"""

    def __init__(self):
        self.data_file = "papertrail_data.json"
        self.papers: Dict[str, Dict[str, Any]] = {}
        self.entities: Dict[str, List[Dict[str, Any]]] = {}
        self.relationships: Dict[str, List[Dict[str, Any]]] = {}
        self.memories: List[
            Dict[str, Any]
        ] = []  # Simple list for conversation memories
        self._load_data()

    def _load_data(self):
        """Load data from JSON file if it exists"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                    self.papers = data.get("papers", {})
                    self.entities = data.get("entities", {})
                    self.relationships = data.get("relationships", {})
                    self.memories = data.get("memories", [])
                    print(f"Loaded {len(self.memories)} memories from {self.data_file}")
        except Exception as e:
            print(f"Failed to load data: {e}")

    def _save_data(self):
        """Save data to JSON file"""
        try:
            data = {
                "papers": self.papers,
                "entities": self.entities,
                "relationships": self.relationships,
                "memories": self.memories,
            }
            with open(self.data_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Failed to save data: {e}")

    def store_paper(self, paper_data: Dict[str, Any]) -> str:
        """Store a paper and return its ID"""
        paper_id = paper_data.get("arxiv_id", str(uuid.uuid4()))

        self.papers[paper_id] = {
            **paper_data,
            "id": paper_id,
            "created_at": datetime.utcnow().isoformat(),
            "status": "processed",
        }

        return paper_id

    def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get paper by ID"""
        return self.papers.get(paper_id)

    def list_papers(
        self, skip: int = 0, limit: int = 20, search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List papers with optional search"""
        papers = list(self.papers.values())

        if search:
            search_lower = search.lower()
            papers = [
                p
                for p in papers
                if search_lower in p.get("title", "").lower()
                or search_lower in p.get("abstract", "").lower()
            ]

        return papers[skip : skip + limit]

    def store_entities(self, paper_id: str, entities: List[Dict[str, Any]]):
        """Store entities for a paper"""
        self.entities[paper_id] = entities

    def store_relationships(self, paper_id: str, relationships: List[Dict[str, Any]]):
        """Store relationships for a paper"""
        self.relationships[paper_id] = relationships

    def get_paper_entities(self, paper_id: str) -> List[Dict[str, Any]]:
        """Get entities for a paper"""
        return self.entities.get(paper_id, [])

    def get_related_papers(
        self, paper_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get related papers (mock implementation)"""
        # For now, just return other papers
        all_papers = list(self.papers.values())
        return [p for p in all_papers if p["id"] != paper_id][:limit]

    def search_entities(
        self, query: str, entity_type: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search entities across all papers"""
        results = []
        query_lower = query.lower()

        for paper_id, entities in self.entities.items():
            for entity in entities:
                if entity_type and entity.get("type") != entity_type:
                    continue

                if query_lower in entity.get("name", "").lower():
                    results.append(
                        {
                            **entity,
                            "paper_id": paper_id,
                            "paper_title": self.papers.get(paper_id, {}).get(
                                "title", "Unknown"
                            ),
                        }
                    )

        return results[:limit]

    def get_graph_data(
        self,
        entity_name: Optional[str] = None,
        paper_id: Optional[str] = None,
        depth: int = 2,
        limit: int = 50,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Generate mock graph data"""
        nodes = []
        edges = []

        # Add paper nodes
        papers_to_include = []
        if paper_id and paper_id in self.papers:
            papers_to_include = [self.papers[paper_id]]
        else:
            papers_to_include = list(self.papers.values())[: limit // 2]

        for paper in papers_to_include:
            nodes.append(
                {
                    "id": paper["id"],
                    "label": paper.get("title", "Untitled"),
                    "type": "paper",
                    "size": 20,
                }
            )

        # Add entity nodes and edges
        entity_count = 0
        for paper in papers_to_include:
            paper_entities = self.entities.get(paper["id"], [])

            for entity in paper_entities[:10]:  # Limit entities per paper
                if entity_count >= limit // 2:
                    break

                entity_id = f"entity_{entity_count}"
                nodes.append(
                    {
                        "id": entity_id,
                        "label": entity.get("name", "Unknown"),
                        "type": entity.get("type", "concept"),
                        "size": 10,
                    }
                )

                edges.append(
                    {"source": paper["id"], "target": entity_id, "type": "contains"}
                )

                entity_count += 1

        return {
            "nodes": nodes,
            "edges": edges,
            "statistics": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "paper_count": len(papers_to_include),
                "entity_count": entity_count,
            },
        }

    def store_memory(self, memory_data: Dict[str, Any]) -> str:
        """Store a conversation memory"""
        memory_id = memory_data.get("id", str(uuid.uuid4()))

        memory = {
            **memory_data,
            "id": memory_id,
            "created_at": memory_data.get("created_at", datetime.utcnow().isoformat()),
            "updated_at": datetime.utcnow().isoformat(),
        }

        self.memories.append(memory)
        self._save_data()  # Persist to JSON
        return memory_id

    def get_memories(self, limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
        """Get stored memories with pagination"""
        start_idx = skip
        end_idx = skip + limit
        return self.memories[start_idx:end_idx]

    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific memory by ID"""
        for memory in self.memories:
            if memory.get("id") == memory_id:
                return memory
        return None


# Global mock store instance
mock_store = MockPaperStore()
