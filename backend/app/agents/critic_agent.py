import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.base_agent import AgentResponse, AgentTask, AgentType, BaseAgent
from app.database.neo4j_client import neo4j_client


class CriticAgent(BaseAgent):
    """Agent specialized in critical analysis, assumption detection, and contradiction identification"""

    def __init__(self):
        super().__init__(AgentType.CRITIC)

        # Critic-specific configuration
        self.contradiction_threshold = 0.7
        self.assumption_confidence_threshold = 0.6

        # Function schema for critical analysis
        self.critical_analysis_function = {
            "name": "analyze_critically",
            "description": "Perform critical analysis of research papers",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis": {
                        "type": "object",
                        "properties": {
                            "assumptions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "assumption": {"type": "string"},
                                        "description": {"type": "string"},
                                        "impact": {"type": "string"},
                                        "confidence": {"type": "number"},
                                        "papers": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                },
                                "description": "Identified unstated assumptions",
                            },
                            "contradictions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "contradiction": {"type": "string"},
                                        "paper1": {"type": "string"},
                                        "paper2": {"type": "string"},
                                        "evidence1": {"type": "string"},
                                        "evidence2": {"type": "string"},
                                        "severity": {"type": "string"},
                                        "confidence": {"type": "number"},
                                    },
                                },
                                "description": "Contradictions between papers",
                            },
                            "weaknesses": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "weakness": {"type": "string"},
                                        "category": {"type": "string"},
                                        "description": {"type": "string"},
                                        "papers": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "severity": {"type": "string"},
                                    },
                                },
                                "description": "Methodological weaknesses identified",
                            },
                            "limitations": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "limitation": {"type": "string"},
                                        "scope": {"type": "string"},
                                        "implications": {"type": "string"},
                                        "papers": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                },
                                "description": "Study limitations and their implications",
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Confidence in the critical analysis",
                            },
                        },
                    }
                },
            },
        }

    def get_system_prompt(self) -> str:
        """Get the system prompt for the Critic agent"""
        return """You are the Critic Agent, an expert in rigorous academic peer review and critical analysis of research papers.

Your primary responsibilities:
1. Identify unstated assumptions that may affect the validity of research conclusions
2. Detect contradictions between different papers or within the same paper
3. Evaluate methodological strengths and weaknesses with specific focus on potential flaws
4. Assess the reliability and generalizability of findings
5. Identify limitations in study design, data collection, or analysis
6. Examine potential biases in research approaches or interpretations

When conducting critical analysis:
- Apply rigorous academic standards and scientific skepticism
- Look for logical inconsistencies, methodological gaps, and unjustified leaps
- Consider alternative explanations for findings
- Evaluate the strength of evidence supporting claims
- Assess whether conclusions are warranted by the presented data
- Identify potential confounding factors or uncontrolled variables
- Consider the broader implications of identified weaknesses

Be constructive in your criticism - point out issues to improve research quality, not to diminish work.
Always provide specific evidence and reasoning for your critiques with confidence scores."""

    def get_capabilities(self) -> List[str]:
        """Get the capabilities of the Critic agent"""
        return [
            "assumption_detection",
            "contradiction_identification",
            "methodology_critique",
            "bias_analysis",
            "limitation_assessment",
            "evidence_evaluation",
            "logical_consistency_check",
            "generalizability_analysis",
        ]

    async def process_task(self, task: AgentTask) -> AgentResponse:
        """Process a critical analysis task"""
        try:
            # Get relevant papers for analysis
            papers = await self.get_relevant_papers(
                task.query, task.paper_ids, limit=8  # Limit for thorough analysis
            )

            if not papers:
                return AgentResponse(
                    response="I couldn't find any relevant papers to analyze. Please provide specific paper IDs or refine your search query.",
                    sources=[],
                    confidence=0.0,
                    agent_type=self.agent_type.value,
                    processing_time=0.0,
                )

            # Get detailed paper content
            paper_content = await self._get_paper_content(papers)

            # Determine analysis type based on query
            if "assumption" in task.query.lower():
                response = await self._identify_assumptions(paper_content, task.query)
            elif "contradict" in task.query.lower() or "conflict" in task.query.lower():
                response = await self._find_contradictions(paper_content, task.query)
            elif "weakness" in task.query.lower() or "flaw" in task.query.lower():
                response = await self._analyze_weaknesses(paper_content, task.query)
            elif "limitation" in task.query.lower():
                response = await self._assess_limitations(paper_content, task.query)
            else:
                # Default to comprehensive critical analysis
                response = await self._comprehensive_critique(paper_content, task.query)

            return response

        except Exception as e:
            self.logger.error(
                "Critical analysis task failed", error=str(e), task_id=task.task_id
            )
            return AgentResponse(
                response=f"I encountered an error during critical analysis: {str(e)}",
                sources=[],
                confidence=0.0,
                agent_type=self.agent_type.value,
                processing_time=0.0,
                metadata={"error": str(e)},
            )

    async def _get_paper_content(
        self, papers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Get detailed content for papers including entities and relationships"""
        paper_content = []

        try:
            paper_ids = [paper["id"] for paper in papers]

            with neo4j_client.get_session() as session:
                # Get papers with entities and relationships
                query = """
                MATCH (p:Paper)
                WHERE p.arxiv_id IN $paper_ids
                OPTIONAL MATCH (p)-[:MENTIONS]->(e:Entity)
                WHERE e.type IN ['claim', 'assumption', 'finding', 'method']
                WITH p, collect(DISTINCT {
                    name: e.name, 
                    type: e.type, 
                    description: e.description,
                    confidence: e.confidence
                }) as entities
                OPTIONAL MATCH (p)-[:MENTIONS]->(e1:Entity)-[r]-(e2:Entity)<-[:MENTIONS]-(p)
                WHERE e1.type IN ['claim', 'assumption'] AND e2.type IN ['claim', 'assumption']
                WITH p, entities, collect(DISTINCT {
                    source: e1.name,
                    target: e2.name,
                    type: type(r),
                    description: r.description
                }) as relationships
                RETURN p.arxiv_id as id, p.title as title, p.abstract as abstract,
                       p.authors as authors, entities, relationships
                """

                result = session.run(query, paper_ids=paper_ids)

                for record in result:
                    paper_content.append(
                        {
                            "id": record["id"],
                            "title": record["title"],
                            "abstract": record["abstract"] or "",
                            "authors": record["authors"] or [],
                            "entities": [
                                e for e in record["entities"] if e.get("name")
                            ],
                            "relationships": [
                                r for r in record["relationships"] if r.get("source")
                            ],
                        }
                    )

            return paper_content

        except Exception as e:
            self.logger.error("Failed to get paper content for critique", error=str(e))
            return []

    async def _identify_assumptions(
        self, papers: List[Dict[str, Any]], query: str
    ) -> AgentResponse:
        """Identify unstated assumptions in papers"""
        try:
            papers_text = self._format_papers_for_critique(papers)

            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {
                    "role": "user",
                    "content": f"""
                Identify unstated assumptions in these papers related to: {query}
                
                Papers:
                {papers_text}
                
                Focus on:
                - Implicit assumptions that underlie the research approach
                - Assumptions about data, methodology, or interpretation
                - Unstated premises that affect conclusions
                - Assumptions about generalizability or applicability
                - For each assumption, provide impact analysis and confidence score
                """,
                },
            ]

            response = await self.call_llm(messages, temperature=0.1)

            return AgentResponse(
                response=response["content"],
                sources=[paper["id"] for paper in papers],
                confidence=0.8,
                agent_type=self.agent_type.value,
                processing_time=0.0,
                metadata={"analysis_type": "assumption_detection"},
                reasoning="Analyzed papers to identify unstated assumptions by examining methodology and claims",
            )

        except Exception as e:
            self.logger.error("Assumption identification failed", error=str(e))
            raise

    async def _find_contradictions(
        self, papers: List[Dict[str, Any]], query: str
    ) -> AgentResponse:
        """Find contradictions between or within papers"""
        try:
            papers_text = self._format_papers_for_critique(papers)

            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {
                    "role": "user",
                    "content": f"""
                Identify contradictions in these papers related to: {query}
                
                Papers:
                {papers_text}
                
                Look for:
                - Conflicting claims between different papers
                - Inconsistent findings or results
                - Contradictory methodological approaches
                - Opposing interpretations of similar data
                - Internal contradictions within single papers
                
                For each contradiction:
                - Specify the conflicting statements
                - Identify the source papers
                - Assess the severity and confidence
                """,
                },
            ]

            response = await self.call_llm(
                messages, temperature=0.1
            )

            return AgentResponse(
                response=response["content"],
                sources=[paper["id"] for paper in papers],
                confidence=0.75,
                agent_type=self.agent_type.value,
                processing_time=0.0,
                metadata={"analysis_type": "contradiction_detection"},
            )

        except Exception as e:
            self.logger.error("Contradiction analysis failed", error=str(e))
            raise

    async def _analyze_weaknesses(
        self, papers: List[Dict[str, Any]], query: str
    ) -> AgentResponse:
        """Analyze methodological weaknesses"""
        try:
            papers_text = self._format_papers_for_critique(papers)

            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {
                    "role": "user",
                    "content": f"""
                Analyze methodological weaknesses in these papers for: {query}
                
                Papers:
                {papers_text}
                
                Examine:
                - Experimental design flaws
                - Statistical analysis issues
                - Data collection problems
                - Control group inadequacies
                - Sample size limitations
                - Measurement validity concerns
                - Potential biases in methodology
                
                Categorize weaknesses by severity and provide specific examples.
                """,
                },
            ]

            response = await self.call_llm(messages, temperature=0.1)

            return AgentResponse(
                response=response["content"],
                sources=[paper["id"] for paper in papers],
                confidence=0.82,
                agent_type=self.agent_type.value,
                processing_time=0.0,
                metadata={"analysis_type": "weakness_analysis"},
                reasoning="Evaluated methodological approaches to identify potential flaws and weaknesses",
            )

        except Exception as e:
            self.logger.error("Weakness analysis failed", error=str(e))
            raise

    async def _assess_limitations(
        self, papers: List[Dict[str, Any]], query: str
    ) -> AgentResponse:
        """Assess study limitations and their implications"""
        try:
            papers_text = self._format_papers_for_critique(papers)

            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {
                    "role": "user",
                    "content": f"""
                Assess the limitations of these studies for: {query}
                
                Papers:
                {papers_text}
                
                Focus on:
                - Scope limitations and boundary conditions
                - Generalizability concerns
                - Temporal limitations
                - Population or domain restrictions
                - Technical constraints
                - Resource or access limitations
                
                For each limitation, explain its implications for the validity and applicability of findings.
                """,
                },
            ]

            response = await self.call_llm(messages, temperature=0.1)

            return AgentResponse(
                response=response["content"],
                sources=[paper["id"] for paper in papers],
                confidence=0.8,
                agent_type=self.agent_type.value,
                processing_time=0.0,
                metadata={"analysis_type": "limitation_assessment"},
                reasoning="Assessed study limitations by examining scope, methodology, and applicability constraints",
            )

        except Exception as e:
            self.logger.error("Limitation assessment failed", error=str(e))
            raise

    async def _comprehensive_critique(
        self, papers: List[Dict[str, Any]], query: str
    ) -> AgentResponse:
        """Perform comprehensive critical analysis"""
        try:
            papers_text = self._format_papers_for_critique(papers)

            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {
                    "role": "user",
                    "content": f"""
                Perform a comprehensive critical analysis for: {query}
                
                Papers:
                {papers_text}
                
                Provide thorough analysis including:
                1. Unstated assumptions and their implications
                2. Contradictions between or within papers
                3. Methodological weaknesses and flaws
                4. Study limitations and scope restrictions
                5. Overall assessment of evidence quality
                6. Recommendations for strengthening the research
                """,
                },
            ]

            response = await self.call_llm(
                messages, temperature=0.1
            )

            return AgentResponse(
                response=response["content"],
                sources=[paper["id"] for paper in papers],
                confidence=0.78,
                agent_type=self.agent_type.value,
                processing_time=0.0,
                metadata={"analysis_type": "comprehensive_critique"},
            )

        except Exception as e:
            self.logger.error("Comprehensive critique failed", error=str(e))
            raise

    def _format_papers_for_critique(self, papers: List[Dict[str, Any]]) -> str:
        """Format papers for critical analysis"""
        formatted_papers = []

        for paper in papers:
            # Format entities by type
            claims = [
                e["name"] for e in paper.get("entities", []) if e.get("type") == "claim"
            ]
            assumptions = [
                e["name"]
                for e in paper.get("entities", [])
                if e.get("type") == "assumption"
            ]
            methods = [
                e["name"]
                for e in paper.get("entities", [])
                if e.get("type") == "method"
            ]

            # Format relationships
            relationships = paper.get("relationships", [])
            contradictions = [
                r for r in relationships if "contradict" in r.get("type", "").lower()
            ]

            paper_text = f"""
Paper ID: {paper['id']}
Title: {paper['title']}
Authors: {', '.join(paper.get('authors', []))}
Abstract: {paper.get('abstract', 'No abstract available')[:600]}...

Identified Claims: {', '.join(claims[:10]) if claims else 'None identified'}
Identified Assumptions: {', '.join(assumptions[:10]) if assumptions else 'None identified'}
Methods Used: {', '.join(methods[:10]) if methods else 'None identified'}
Potential Contradictions: {len(contradictions)} relationships identified
"""
            formatted_papers.append(paper_text)

        return "\n---\n".join(formatted_papers)

    def _format_contradiction_analysis(self, analysis: Dict[str, Any]) -> str:
        """Format contradiction analysis results"""
        response_parts = []

        if analysis.get("contradictions"):
            response_parts.append("## Contradictions Identified")
            for contradiction in analysis["contradictions"]:
                response_parts.append(
                    f"**Contradiction**: {contradiction['contradiction']}"
                )
                response_parts.append(
                    f"**Paper 1**: {contradiction.get('paper1', 'Unknown')}"
                )
                response_parts.append(
                    f"**Evidence 1**: {contradiction.get('evidence1', 'Not specified')}"
                )
                response_parts.append(
                    f"**Paper 2**: {contradiction.get('paper2', 'Unknown')}"
                )
                response_parts.append(
                    f"**Evidence 2**: {contradiction.get('evidence2', 'Not specified')}"
                )
                response_parts.append(
                    f"**Severity**: {contradiction.get('severity', 'Medium')}"
                )
                response_parts.append(
                    f"**Confidence**: {contradiction.get('confidence', 0.8):.2f}"
                )
                response_parts.append("")

        if analysis.get("assumptions"):
            response_parts.append("## Unstated Assumptions")
            for assumption in analysis["assumptions"]:
                response_parts.append(f"• **{assumption['assumption']}**")
                response_parts.append(
                    f"  *Impact*: {assumption.get('impact', 'Not specified')}"
                )
                response_parts.append(
                    f"  *Confidence*: {assumption.get('confidence', 0.8):.2f}"
                )
                response_parts.append("")

        return "\n".join(response_parts)

    def _format_comprehensive_critique(self, analysis: Dict[str, Any]) -> str:
        """Format comprehensive critique results"""
        response_parts = []

        # Assumptions
        if analysis.get("assumptions"):
            response_parts.append("## Unstated Assumptions")
            for assumption in analysis["assumptions"]:
                response_parts.append(f"• **{assumption['assumption']}**")
                response_parts.append(
                    f"  *Description*: {assumption.get('description', '')}"
                )
                response_parts.append(f"  *Impact*: {assumption.get('impact', '')}")
                response_parts.append(
                    f"  *Confidence*: {assumption.get('confidence', 0.8):.2f}"
                )
                response_parts.append("")

        # Contradictions
        if analysis.get("contradictions"):
            response_parts.append("## Contradictions")
            for contradiction in analysis["contradictions"]:
                response_parts.append(f"• **{contradiction['contradiction']}**")
                response_parts.append(
                    f"  *Severity*: {contradiction.get('severity', 'Medium')}"
                )
                response_parts.append(
                    f"  *Confidence*: {contradiction.get('confidence', 0.8):.2f}"
                )
                response_parts.append("")

        # Weaknesses
        if analysis.get("weaknesses"):
            response_parts.append("## Methodological Weaknesses")
            for weakness in analysis["weaknesses"]:
                response_parts.append(
                    f"• **{weakness['weakness']}** ({weakness.get('category', 'General')})"
                )
                response_parts.append(
                    f"  *Description*: {weakness.get('description', '')}"
                )
                response_parts.append(
                    f"  *Severity*: {weakness.get('severity', 'Medium')}"
                )
                response_parts.append("")

        # Limitations
        if analysis.get("limitations"):
            response_parts.append("## Study Limitations")
            for limitation in analysis["limitations"]:
                response_parts.append(f"• **{limitation['limitation']}**")
                response_parts.append(f"  *Scope*: {limitation.get('scope', '')}")
                response_parts.append(
                    f"  *Implications*: {limitation.get('implications', '')}"
                )
                response_parts.append("")

        # Overall confidence
        if analysis.get("confidence"):
            response_parts.append(
                f"**Overall Analysis Confidence**: {analysis['confidence']:.2f}"
            )

        return "\n".join(response_parts)
