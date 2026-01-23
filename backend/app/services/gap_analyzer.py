from typing import Dict, List, Optional
from collections import Counter
from app.database import list_papers
from app.core.logging import get_logger

logger = get_logger("gap_analyzer")


class GapAnalyzer:
    """Identifies research gaps in the paper library"""

    @staticmethod
    def extract_entities_and_topics(papers: List[Dict[str, any]]) -> Dict[str, any]:
        """Extract entities and topics from papers"""
        entities = Counter()
        topics = Counter()
        methods = Counter()
        
        for paper in papers:
            abstract = paper.get("abstract", "")
            text = paper.get("text", "")
            full_text = f"{abstract} {text}"
            
            # Simple entity extraction (capitalized words likely to be entities)
            import re
            entity_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
            found_entities = re.findall(entity_pattern, full_text)
            
            # Filter to keep only significant entities (appearing multiple times across papers)
            for entity in found_entities:
                entities[entity] += 1
            
            # Extract methods from common patterns
            method_patterns = [
                r'(?:using|with|by means of)\s+([a-z]+\s*(?:method|approach|technique|algorithm|model))',
                r'(?:we propose|introduce|our method uses)\s+([a-z]+\s*(?:method|approach|technique))',
            ]
            
            for pattern in method_patterns:
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                for match in matches:
                    methods[match.lower()] += 1
            
            # Extract topics from keywords
            topic_keywords = [
                'transformer', 'attention', 'neural network', 'deep learning',
                'machine learning', 'reinforcement learning', 'convolutional',
                'graph neural network', 'natural language', 'computer vision',
                'generative model', 'language model', 'diffusion model',
            ]
            
            for topic in topic_keywords:
                if topic.lower() in full_text.lower():
                    topics[topic] += 1
        
        return {
            "entities": dict(entities.most_common(50)),
            "topics": dict(topics.most_common(30)),
            "methods": dict(methods.most_common(30)),
        }

    @staticmethod
    def analyze_topic_coverage(analysis: Dict[str, any]) -> List[Dict[str, any]]:
        """Analyze which topics are well-covered vs underrepresented"""
        coverage_analysis = []
        
        total_entities = sum(analysis["entities"].values())
        total_topics = sum(analysis["topics"].values())
        
        # Categorize entities by frequency
        well_studied = []
        moderately_studied = []
        understudied = []
        
        for entity, count in analysis["entities"].items():
            if count >= total_entities * 0.05:  # Top 5%
                well_studied.append(entity)
            elif count >= total_entities * 0.01:  # Top 1-5%
                moderately_studied.append(entity)
            else:
                understudied.append(entity)
        
        # Do the same for topics
        well_covered_topics = []
        underrepresented_topics = []
        
        for topic, count in analysis["topics"].items():
            if count >= total_topics * 0.03:
                well_covered_topics.append(topic)
            else:
                underrepresented_topics.append(topic)
        
        coverage_analysis.append({
            "category": "entities",
            "well_studied": well_studied[:20],
            "moderately_studied": moderately_studied[:20],
            "understudied": understudied[:20],
        })
        
        coverage_analysis.append({
            "category": "topics",
            "well_covered": well_covered_topics,
            "underrepresented": underrepresented_topics,
        })
        
        return coverage_analysis

    @staticmethod
    def identify_missing_connections(analysis: Dict[str, any], papers: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """Identify potential connections that are missing"""
        missing_connections = []
        
        # Find combinations of entities that don't appear together
        entities = list(analysis["entities"].keys())
        top_entities = entities[:20]
        
        for i, entity1 in enumerate(top_entities):
            for entity2 in top_entities[i+1:]:
                # Check if these entities appear together in any paper
                found_together = False
                for paper in papers:
                    text = (paper.get("abstract", "") + " " + paper.get("text", "")).lower()
                    if entity1.lower() in text and entity2.lower() in text:
                        found_together = True
                        break
                
                if not found_together:
                    missing_connections.append({
                        "entity1": entity1,
                        "entity2": entity2,
                        "reason": "Not studied together in any paper",
                        "priority": "medium",
                    })
        
        return missing_connections[:50]

    @staticmethod
    def suggest_research_questions(analysis: Dict[str, any], gaps: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """Generate research questions based on gaps"""
        questions = []
        
        # Questions about understudied entities
        understudied_entities = [g for g in gaps if g.get("category") == "entities"][0].get("understudied", [])[:10]
        for entity in understudied_entities:
            questions.append({
                "question": f"What is the role of {entity} in this research domain?",
                "type": "exploration",
                "target_entity": entity,
                "confidence": 0.7,
            })
        
        # Questions about missing connections
        missing_conns = [g for g in gaps if g.get("category") == "missing_connections"][:10]
        for conn in missing_conns:
            questions.append({
                "question": f"How do {conn['entity1']} and {conn['entity2']} interact or influence each other?",
                "type": "connection",
                "entities": [conn["entity1"], conn["entity2"]],
                "confidence": 0.6,
            })
        
        # Questions about underrepresented topics
        underrep_topics = [g for g in gaps if g.get("category") == "topics"][0].get("underrepresented", [])[:10]
        for topic in underrep_topics:
            questions.append({
                "question": f"What are the key challenges and opportunities in {topic} research?",
                "type": "topic",
                "target_topic": topic,
                "confidence": 0.65,
            })
        
        # Questions about methodological gaps
        methods = list(analysis["methods"].keys())
        if len(methods) > 10:
            new_methods = [m for m in ["neural architecture", "pre-training", "fine-tuning", "prompt engineering"] 
                        if m not in [method.lower() for method in methods]]
            for method in new_methods:
                questions.append({
                    "question": f"How can {method} be applied to improve performance in this domain?",
                    "type": "methodology",
                    "target_method": method,
                    "confidence": 0.6,
                })
        
        return questions

    @staticmethod
    def analyze_research_gaps(paper_ids: Optional[List[str]] = None) -> Dict[str, any]:
        """Main method to analyze research gaps in the library"""
        try:
            # Get papers from database
            papers = list_papers(limit=100, skip=0)
            
            if not papers or len(papers) == 0:
                return {
                    "message": "No papers available for gap analysis",
                    "gaps": [],
                    "recommendations": [],
                }
            
            # Extract entities and topics
            analysis = GapAnalyzer.extract_entities_and_topics(papers)
            
            # Analyze coverage
            coverage_gaps = GapAnalyzer.analyze_topic_coverage(analysis)
            
            # Identify missing connections
            missing_connections = GapAnalyzer.identify_missing_connections(analysis, papers)
            
            # Compile all gaps
            all_gaps = coverage_gaps + [{"category": "missing_connections", **gap} for gap in missing_connections]
            
            # Generate research questions
            questions = GapAnalyzer.suggest_research_questions(analysis, all_gaps)
            
            return {
                "total_papers_analyzed": len(papers),
                "analysis": analysis,
                "gaps": all_gaps,
                "research_questions": questions,
                "summary": {
                    "total_entities": len(analysis["entities"]),
                    "total_topics": len(analysis["topics"]),
                    "total_methods": len(analysis["methods"]),
                    "understudied_entities": len([g for g in gaps if g.get("category") == "entities"][0].get("understudied", [])),
                    "underrepresented_topics": len([g for g in gaps if g.get("category") == "topics"][0].get("underrepresented", [])),
                    "missing_connections": len(missing_connections),
                    "suggested_questions": len(questions),
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze research gaps: {e}")
            return {
                "error": str(e),
                "gaps": [],
                "research_questions": [],
            }

    @staticmethod
    def find_trending_gaps(timeframe_days: int = 365) -> Dict[str, any]:
        """Find gaps in recent research trends"""
        try:
            from datetime import datetime, timedelta
            
            # Get recent papers
            cutoff_date = (datetime.now() - timedelta(days=timeframe_days)).isoformat()
            
            # Note: This would require papers to have publication dates
            # For now, return a placeholder analysis
            return {
                "timeframe_days": timeframe_days,
                "cutoff_date": cutoff_date,
                "trends": {
                    "emerging_topics": [],
                    "declining_topics": [],
                    "gap_areas": [],
                },
                "recommendations": [
                    "Monitor recent publications for emerging techniques",
                    "Investigate areas with declining research interest",
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to find trending gaps: {e}")
            return {
                "error": str(e),
                "trends": {},
            }
