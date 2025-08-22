import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.base_agent import (AgentResponse, AgentTask, AgentType,
                                   BaseAgent)
from app.database.neo4j_client import neo4j_client


class SynthesizerAgent(BaseAgent):
    """Agent specialized in paper summarization and claim extraction"""

    def __init__(self):
        super().__init__(AgentType.SYNTHESIZER)

        # Synthesizer-specific configuration
        self.max_papers_per_synthesis = 10
        self.min_confidence_threshold = 0.6

        # Function schemas for structured outputs
        self.synthesis_function = {
            "name": "synthesize_papers",
            "description": "Create a structured synthesis of research papers",
            "parameters": {
                "type": "object",
                "properties": {
                    "synthesis": {
                        "type": "object",
                        "properties": {
                            "main_themes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Primary themes across the papers",
                            },
                            "key_claims": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "claim": {"type": "string"},
                                        "evidence": {"type": "string"},
                                        "confidence": {"type": "number"},
                                        "sources": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                },
                                "description": "Key claims made across papers",
                            },
                            "methodologies": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "method": {"type": "string"},
                                        "description": {"type": "string"},
                                        "papers": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                },
                                "description": "Research methodologies used",
                            },
                            "findings": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "finding": {"type": "string"},
                                        "significance": {"type": "string"},
                                        "supporting_papers": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                },
                                "description": "Key findings and results",
                            },
                            "summary": {
                                "type": "string",
                                "description": "Overall synthesis summary",
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Confidence in the synthesis",
                            },
                        },
                    }
                },
            },
        }

    def get_system_prompt(self) -> str:
        """Get the system prompt for the Synthesizer agent"""
        return """You are the Synthesizer Agent, an expert research analyst specializing in academic paper synthesis and claim extraction.

Your primary responsibilities:
1. Analyze and synthesize multiple research papers to identify common themes and patterns
2. Extract key claims and arguments from papers with supporting evidence
3. Identify research methodologies and their applications across papers
4. Summarize findings and their significance in the research domain
5. Create comprehensive overviews that help researchers understand the landscape

When synthesizing papers:
- Focus on academic rigor and evidence-based conclusions
- Identify both consensus and divergent viewpoints
- Highlight methodological approaches and their effectiveness
- Extract quantifiable results and qualitative insights
- Maintain objectivity while noting the strength of evidence
- Connect findings across papers to reveal broader patterns

Always provide confidence scores for your claims and cite specific papers as sources.
Be thorough but concise, prioritizing the most significant insights."""

    def get_capabilities(self) -> List[str]:
        """Get the capabilities of the Synthesizer agent"""
        return [
            "paper_summarization",
            "claim_extraction",
            "theme_identification",
            "methodology_analysis",
            "finding_synthesis",
            "evidence_evaluation",
            "multi_paper_analysis",
            "research_landscape_overview",
        ]

    async def process_task(self, task: AgentTask) -> AgentResponse:
        """Process a synthesis task"""
        try:
            # Get relevant papers for the query
            papers = await self.get_relevant_papers(
                task.query, task.paper_ids, limit=self.max_papers_per_synthesis
            )

            if not papers:
                return AgentResponse(
                    response="I couldn't find any relevant papers for your query. Please try a different search term or specify paper IDs.",
                    sources=[],
                    confidence=0.0,
                    agent_type=self.agent_type.value,
                    processing_time=0.0,
                )

            # Get detailed paper content
            paper_content = await self._get_paper_content(papers)

            # Determine synthesis type based on query
            if "summarize" in task.query.lower() or "overview" in task.query.lower():
                response = await self._synthesize_papers(paper_content, task.query)
            elif "claim" in task.query.lower() or "finding" in task.query.lower():
                response = await self._extract_claims(paper_content, task.query)
            elif "method" in task.query.lower() or "approach" in task.query.lower():
                response = await self._analyze_methodologies(paper_content, task.query)
            else:
                # Default to comprehensive synthesis
                response = await self._comprehensive_synthesis(
                    paper_content, task.query
                )

            return response

        except Exception as e:
            self.logger.error(
                "Synthesis task failed", error=str(e), task_id=task.task_id
            )
            return AgentResponse(
                response=f"I encountered an error while synthesizing the papers: {str(e)}",
                sources=[],
                confidence=0.0,
                agent_type=self.agent_type.value,
                processing_time=0.0,
                metadata={"error": str(e)},
            )

    async def _get_paper_content(
        self, papers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Get detailed content for papers"""
        paper_content = []

        try:
            paper_ids = [paper["id"] for paper in papers]

            with neo4j_client.get_session() as session:
                # Get paper details including entities
                query = """
                MATCH (p:Paper)
                WHERE p.arxiv_id IN $paper_ids
                OPTIONAL MATCH (p)-[:MENTIONS]->(e:Entity)
                WITH p, collect({
                    name: e.name, 
                    type: e.type, 
                    description: e.description,
                    confidence: e.confidence
                }) as entities
                RETURN p.arxiv_id as id, p.title as title, p.abstract as abstract,
                       p.authors as authors, entities
                """

                result = session.run(query, paper_ids=paper_ids)

                for record in result:
                    paper_content.append(
                        {
                            "id": record["id"],
                            "title": record["title"],
                            "abstract": record["abstract"] or "",
                            "authors": record["authors"] or [],
                            "entities": [e for e in record["entities"] if e["name"]],
                        }
                    )

            return paper_content

        except Exception as e:
            self.logger.error("Failed to get paper content", error=str(e))
            return []

    async def _synthesize_papers(
        self, papers: List[Dict[str, Any]], query: str
    ) -> AgentResponse:
        """Create a synthesis of multiple papers"""
        try:
            # Prepare paper information for LLM
            papers_text = self._format_papers_for_llm(papers)

            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {
                    "role": "user",
                    "content": f"""
                Please synthesize the following research papers to answer: {query}
                
                Papers to synthesize:
                {papers_text}
                
                Provide a comprehensive synthesis that includes:
                1. Main themes across the papers
                2. Key claims with evidence and confidence levels
                3. Research methodologies employed
                4. Important findings and their significance
                5. Overall summary with confidence assessment
                """,
                },
            ]

            response = await self.call_llm(
                messages, functions=[self.synthesis_function]
            )

            if response["type"] == "function_call":
                synthesis_data = json.loads(response["arguments"])
                synthesis = synthesis_data["synthesis"]

                # Format response
                formatted_response = self._format_synthesis_response(synthesis)

                return AgentResponse(
                    response=formatted_response,
                    sources=[paper["id"] for paper in papers],
                    confidence=synthesis.get("confidence", 0.8),
                    agent_type=self.agent_type.value,
                    processing_time=0.0,
                    metadata={
                        "synthesis_type": "comprehensive",
                        "paper_count": len(papers),
                        "themes": synthesis.get("main_themes", []),
                        "claim_count": len(synthesis.get("key_claims", [])),
                    },
                    reasoning="Synthesized information from multiple papers using theme analysis and claim extraction",
                )

            else:
                # Fallback to text response
                return AgentResponse(
                    response=response["content"],
                    sources=[paper["id"] for paper in papers],
                    confidence=0.7,
                    agent_type=self.agent_type.value,
                    processing_time=0.0,
                )

        except Exception as e:
            self.logger.error("Synthesis failed", error=str(e))
            raise

    async def _extract_claims(
        self, papers: List[Dict[str, Any]], query: str
    ) -> AgentResponse:
        """Extract specific claims from papers"""
        try:
            papers_text = self._format_papers_for_llm(papers)

            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {
                    "role": "user",
                    "content": f"""
                Extract key claims related to: {query}
                
                Papers:
                {papers_text}
                
                Focus on:
                - Explicit claims made by the authors
                - Supporting evidence for each claim
                - Confidence level based on evidence strength
                - Source papers for each claim
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
                metadata={"analysis_type": "claim_extraction"},
                reasoning="Extracted claims by analyzing paper content and identifying evidence-backed statements",
            )

        except Exception as e:
            self.logger.error("Claim extraction failed", error=str(e))
            raise

    async def _analyze_methodologies(
        self, papers: List[Dict[str, Any]], query: str
    ) -> AgentResponse:
        """Analyze research methodologies across papers"""
        try:
            papers_text = self._format_papers_for_llm(papers)

            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {
                    "role": "user",
                    "content": f"""
                Analyze the research methodologies in these papers related to: {query}
                
                Papers:
                {papers_text}
                
                Focus on:
                - Research methods and approaches used
                - Experimental designs and setups
                - Data collection and analysis techniques
                - Evaluation metrics and validation approaches
                - Comparative analysis of methodological effectiveness
                """,
                },
            ]

            response = await self.call_llm(messages, temperature=0.1)

            return AgentResponse(
                response=response["content"],
                sources=[paper["id"] for paper in papers],
                confidence=0.85,
                agent_type=self.agent_type.value,
                processing_time=0.0,
                metadata={"analysis_type": "methodology_analysis"},
                reasoning="Analyzed methodological approaches by examining research design and experimental procedures",
            )

        except Exception as e:
            self.logger.error("Methodology analysis failed", error=str(e))
            raise

    async def _comprehensive_synthesis(
        self, papers: List[Dict[str, Any]], query: str
    ) -> AgentResponse:
        """Perform comprehensive synthesis covering all aspects"""
        try:
            papers_text = self._format_papers_for_llm(papers)

            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {
                    "role": "user",
                    "content": f"""
                Provide a comprehensive analysis and synthesis for: {query}
                
                Papers:
                {papers_text}
                
                Include:
                1. Research landscape overview
                2. Key themes and patterns
                3. Important claims and findings
                4. Methodological approaches
                5. Gaps and future directions
                6. Confidence assessment
                """,
                },
            ]

            response = await self.call_llm(
                messages, functions=[self.synthesis_function], temperature=0.1
            )

            if response["type"] == "function_call":
                synthesis_data = json.loads(response["arguments"])
                synthesis = synthesis_data["synthesis"]
                formatted_response = self._format_synthesis_response(synthesis)

                return AgentResponse(
                    response=formatted_response,
                    sources=[paper["id"] for paper in papers],
                    confidence=synthesis.get("confidence", 0.8),
                    agent_type=self.agent_type.value,
                    processing_time=0.0,
                    metadata={
                        "synthesis_type": "comprehensive",
                        "paper_count": len(papers),
                        "themes": synthesis.get("main_themes", []),
                    },
                    reasoning="Comprehensive synthesis covering themes, claims, methods, and findings",
                )
            else:
                return AgentResponse(
                    response=response["content"],
                    sources=[paper["id"] for paper in papers],
                    confidence=0.75,
                    agent_type=self.agent_type.value,
                    processing_time=0.0,
                    metadata={"synthesis_type": "comprehensive"},
                )

        except Exception as e:
            self.logger.error("Comprehensive synthesis failed", error=str(e))
            raise

    def _format_papers_for_llm(self, papers: List[Dict[str, Any]]) -> str:
        """Format papers for LLM input"""
        formatted_papers = []

        for paper in papers:
            entities_text = ", ".join(
                [
                    f"{e['name']} ({e['type']})"
                    for e in paper.get("entities", [])
                    if e.get("confidence", 0) > self.min_confidence_threshold
                ][:20]
            )  # Limit entities to avoid token overflow

            paper_text = f"""
Paper ID: {paper['id']}
Title: {paper['title']}
Authors: {', '.join(paper.get('authors', []))}
Abstract: {paper.get('abstract', 'No abstract available')[:500]}...
Key Entities: {entities_text}
"""
            formatted_papers.append(paper_text)

        return "\n---\n".join(formatted_papers)

    def _format_synthesis_response(self, synthesis: Dict[str, Any]) -> str:
        """Format synthesis data into readable response"""
        response_parts = []

        # Main themes
        if synthesis.get("main_themes"):
            response_parts.append("## Main Themes")
            for theme in synthesis["main_themes"]:
                response_parts.append(f"• {theme}")
            response_parts.append("")

        # Key claims
        if synthesis.get("key_claims"):
            response_parts.append("## Key Claims")
            for claim in synthesis["key_claims"]:
                response_parts.append(f"**Claim**: {claim['claim']}")
                response_parts.append(f"**Evidence**: {claim['evidence']}")
                response_parts.append(
                    f"**Confidence**: {claim.get('confidence', 0.8):.2f}"
                )
                response_parts.append(
                    f"**Sources**: {', '.join(claim.get('sources', []))}"
                )
                response_parts.append("")

        # Methodologies
        if synthesis.get("methodologies"):
            response_parts.append("## Research Methodologies")
            for method in synthesis["methodologies"]:
                response_parts.append(
                    f"**{method['method']}**: {method['description']}"
                )
                response_parts.append(
                    f"*Used in*: {', '.join(method.get('papers', []))}"
                )
                response_parts.append("")

        # Findings
        if synthesis.get("findings"):
            response_parts.append("## Key Findings")
            for finding in synthesis["findings"]:
                response_parts.append(f"• **{finding['finding']}**")
                response_parts.append(f"  *Significance*: {finding['significance']}")
                response_parts.append(
                    f"  *Sources*: {', '.join(finding.get('supporting_papers', []))}"
                )
                response_parts.append("")

        # Summary
        if synthesis.get("summary"):
            response_parts.append("## Summary")
            response_parts.append(synthesis["summary"])
            response_parts.append("")

        # Confidence
        if synthesis.get("confidence"):
            response_parts.append(
                f"**Overall Confidence**: {synthesis['confidence']:.2f}"
            )

        return "\n".join(response_parts)
