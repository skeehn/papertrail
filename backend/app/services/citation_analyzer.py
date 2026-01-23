from typing import Dict, List, Optional
from app.database.neo4j_client import GraphOperations
from app.core.logging import get_logger

logger = get_logger("citation_analyzer")


class CitationAnalyzer:
    """Analyzes citation networks in research papers"""

    @staticmethod
    def extract_citations(text: str) -> List[str]:
        """Extract citations from paper text"""
        import re
        
        # Match common citation patterns
        # Pattern 1: (Author, Year) - e.g., "(Vaswani et al., 2017)"
        pattern1 = r'\(([A-Z][a-z]+(?:\s+et\s+al\.)?,?\s+\d{4})\)'
        citations = re.findall(pattern1, text)
        
        # Pattern 2: [数字] style citations
        pattern2 = r'\[(\d+)\]'
        numbered_citations = re.findall(pattern2, text)
        citations.extend([f"[{c}]" for c in numbered_citations])
        
        # Pattern 3: Common citation markers like "see [Author et al.]" or "as discussed in [Title]"
        pattern3 = r'(?:see|as discussed in|according to|referenced in)\s+([A-Z][a-z]+(?:\s+et\s+al\.)?)', re.IGNORECASE
        text_citations = re.findall(pattern3, text)
        citations.extend([c.capitalize() for c in text_citations])
        
        return list(set(citations))

    @staticmethod
    def analyze_citation_network(paper_ids: List[str]) -> Dict[str, any]:
        """Analyze the citation network between papers"""
        network = {
            "nodes": [],
            "edges": [],
            "metrics": {
                "total_citations": 0,
                "highly_cited_papers": [],
                "citation_clusters": [],
            }
        }
        
        for paper_id in paper_ids:
            try:
                from app.database import get_paper_by_id
                paper = get_paper_by_id(paper_id)
                
                if paper:
                    network["nodes"].append({
                        "id": paper_id,
                        "title": paper.get("title", ""),
                        "authors": paper.get("authors", []),
                        "citation_count": 0,
                    })
                    
                    # Extract citations from paper text/abstract
                    abstract = paper.get("abstract", "")
                    text = paper.get("text", "")
                    full_text = f"{abstract} {text}"
                    
                    citations = CitationAnalyzer.extract_citations(full_text)
                    network["metrics"]["total_citations"] += len(citations)
                    
                    # Store citation count
                    network["nodes"][-1]["citation_count"] = len(citations)
                    
            except Exception as e:
                logger.warning(f"Failed to analyze paper {paper_id}: {e}")
                continue
        
        # Sort papers by citation count
        network["nodes"].sort(key=lambda x: x["citation_count"], reverse=True)
        
        # Identify highly cited papers (top 20%)
        if network["nodes"]:
            threshold = max(1, len(network["nodes"]) // 5)
            network["metrics"]["highly_cited_papers"] = network["nodes"][:threshold]
        
        # Create citation edges (simplified - would need actual citation links)
        for i, node in enumerate(network["nodes"]):
            if node["citation_count"] > 0:
                # In a real implementation, you would link to actual cited papers
                # For now, create a dummy network structure
                pass
        
        return network

    @staticmethod
    def find_citation_paths(source_paper_id: str, target_paper_id: str, max_hops: int = 3) -> List[Dict[str, any]]:
        """Find citation paths between two papers"""
        paths = []
        
        try:
            from app.database.neo4j_client import neo4j_client
            
            # Query Neo4j for citation paths
            query = f"""
            MATCH path = (source:Paper {{arxiv_id: $source_id}})-[*1..{max_hops}*CITES*]-(target:Paper {{arxiv_id: $target_id}})
            RETURN path
            LIMIT 10
            """
            
            result = neo4j_client.driver.session().run(query, source_id=source_paper_id, target_id=target_paper_id)
            
            for record in result:
                path = record["path"]
                paths.append({
                    "length": len(path.nodes),
                    "papers": [node.properties.get("title", node.id) for node in path.nodes]
                })
                
        except Exception as e:
            logger.error(f"Failed to find citation paths: {e}")
        
        return paths

    @staticmethod
    def identify_citation_clusters(paper_ids: List[str]) -> List[Dict[str, any]]:
        """Identify clusters of frequently co-cited papers"""
        clusters = []
        
        try:
            from app.database.neo4j_client import neo4j_client
            
            # Find papers that cite similar sets of papers
            query = """
            MATCH (p:Paper)<-[r:CITES]-(cited:Paper)
            WITH p, collect(cited.arxiv_id) as cited_papers
            WITH cited_papers, count(cited_papers) as citation_count
            WHERE citation_count > 2
            RETURN p.arxiv_id as paper_id, p.title, cited_papers, citation_count
            ORDER BY citation_count DESC
            LIMIT 20
            """
            
            result = neo4j_client.driver.session().run(query)
            
            for record in result:
                clusters.append({
                    "paper_id": record["paper_id"],
                    "title": record["title"],
                    "cited_papers": record["cited_papers"],
                    "citation_count": record["citation_count"],
                })
                
        except Exception as e:
            logger.error(f"Failed to identify citation clusters: {e}")
        
        return clusters

    @staticmethod
    def get_paper_citation_metrics(paper_id: str) -> Dict[str, any]:
        """Get detailed citation metrics for a paper"""
        metrics = {
            "paper_id": paper_id,
            "total_citations": 0,
            "self_citations": 0,
            "citation_impact": 0.0,
            "recent_citations": [],
        }
        
        try:
            from app.database import get_paper_by_id
            paper = get_paper_by_id(paper_id)
            
            if not paper:
                return metrics
            
            # Count citations
            citations = CitationAnalyzer.extract_citations(paper.get("text", "") + " " + paper.get("abstract", ""))
            metrics["total_citations"] = len(citations)
            
            # Calculate citation impact (normalized by age)
            publication_date = paper.get("publication_date")
            if publication_date:
                import datetime
                from datetime import datetime
                
                try:
                    pub_date = datetime.fromisoformat(publication_date)
                    age_years = (datetime.now() - pub_date).days / 365
                    if age_years > 0:
                        metrics["citation_impact"] = round(len(citations) / age_years, 2)
                except:
                    pass
            
            # Track recent citations (last 5 years)
            current_year = datetime.now().year
            metrics["recent_citations"] = citations  # Placeholder - would need actual dates
            
        except Exception as e:
            logger.error(f"Failed to get citation metrics for {paper_id}: {e}")
        
        return metrics
