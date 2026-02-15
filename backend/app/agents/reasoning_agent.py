"""Multi-hop reasoning agent for complex research queries"""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import openai

from app.agents.base_agent import AgentResponse, AgentType, BaseAgent
from app.core.config import settings
from app.core.logging import get_logger
from app.database.neo4j_client import Neo4jClient
from app.services.pinecone_store import pinecone_store

logger = get_logger("reasoning_agent")


@dataclass
class ReasoningStep:
    """A single step in multi-hop reasoning"""

    step_number: int
    question: str
    method: str  # "graph", "vector", "llm"
    query: str
    results: List[Dict[str, Any]]
    answer: str
    confidence: float


class ReasoningAgent(BaseAgent):
    """Agent for multi-hop reasoning across research papers"""

    def __init__(self):
        super().__init__(AgentType.REASONING)
        self.neo4j_client = Neo4jClient()
        self.max_hops = 3
        self.max_results_per_hop = 10

    def get_system_prompt(self) -> str:
        """Get system prompt for reasoning agent"""
        return """You are a multi-hop reasoning agent specializing in research questions.
Your task is to break down complex questions into simpler sub-questions,
answer them step-by-step using graph traversal and vector search,
and then synthesize a comprehensive final answer.

Capabilities:
- Multi-hop reasoning across research papers
- Graph traversal to find relationships between entities
- Vector search for finding relevant papers
- Evidence accumulation across reasoning steps
- Confidence scoring based on evidence quality

Focus on accuracy and provide sources for all claims.
"""

    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return [
            "multi-hop reasoning",
            "graph traversal",
            "vector search",
            "relationship discovery",
            "evidence accumulation",
            "confidence scoring",
            "question decomposition",
        ]

    async def process_task(self, task) -> AgentResponse:
        """Process a reasoning task"""
        from app.agents.base_agent import AgentTask

        try:
            result = await self.answer_complex_query(
                query=task.query, context=task.context
            )

            sources = []
            if "sources" in result:
                sources = result["sources"]

            return AgentResponse(
                response=result.get("answer", ""),
                sources=[s.get("title", "") for s in sources] if sources else [],
                confidence=result.get("confidence", 0.0),
                agent_type="reasoning",
                processing_time=0.0,
            )
        except Exception as e:
            self.logger.error(f"Reasoning task failed: {str(e)}")
            raise

    async def answer_complex_query(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Answer a complex query using multi-hop reasoning

        Args:
            query: Complex question requiring multiple reasoning steps
            context: Optional context from previous queries

        Returns:
            Dictionary with answer and reasoning steps
        """
        self.logger.info(f"Starting multi-hop reasoning for: {query}")

        try:
            # Step 1: Decompose query into sub-questions
            sub_questions = await self._decompose_query(query)

            # Step 2: Execute each sub-question
            reasoning_steps = []
            accumulated_context = []

            for i, sub_q in enumerate(sub_questions, 1):
                step = await self._execute_reasoning_step(
                    step_number=i, question=sub_q, context=accumulated_context
                )
                reasoning_steps.append(step)
                accumulated_context.extend(step.results)

            # Step 3: Synthesize final answer
            final_answer = await self._synthesize_answer(
                query, reasoning_steps, accumulated_context
            )

            return {
                "query": query,
                "answer": final_answer["answer"],
                "confidence": final_answer["confidence"],
                "reasoning_steps": [
                    {
                        "step": s.step_number,
                        "question": s.question,
                        "method": s.method,
                        "answer": s.answer,
                        "evidence_count": len(s.results),
                    }
                    for s in reasoning_steps
                ],
                "sources": final_answer["sources"],
                "reasoning_path": [s.question for s in reasoning_steps],
            }

        except Exception as e:
            self.logger.error(f"Multi-hop reasoning failed: {str(e)}")
            raise

    async def _decompose_query(self, query: str) -> List[str]:
        """Decompose complex query into sub-questions"""

        prompt = f"""You are a research assistant helping to answer complex questions about academic papers.

Break down this complex question into 2-4 simpler sub-questions that can be answered step-by-step.

Complex Question: {query}

Requirements:
- Each sub-question should be specific and answerable
- Sub-questions should build on each other
- Keep questions focused on research papers, methods, datasets, or findings

Format your response as a numbered list:
1. [First sub-question]
2. [Second sub-question]
...

Sub-questions:"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7,
        )

        # Parse sub-questions
        content = response.choices[0].message.content.strip()
        sub_questions = []

        for line in content.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                # Remove numbering
                question = line.split(".", 1)[-1].strip()
                question = question.lstrip("- ")
                if question:
                    sub_questions.append(question)

        # Fallback if parsing fails
        if not sub_questions:
            sub_questions = [query]

        self.logger.info(f"Decomposed into {len(sub_questions)} sub-questions")
        return sub_questions[:4]  # Max 4 steps

    async def _execute_reasoning_step(
        self, step_number: int, question: str, context: List[Dict[str, Any]]
    ) -> ReasoningStep:
        """Execute a single reasoning step"""

        self.logger.info(f"Step {step_number}: {question}")

        # Determine best method for this question
        method = await self._select_method(question)

        # Execute query based on method
        if method == "graph":
            results = await self._graph_search(question, context)
        elif method == "vector":
            results = await self._vector_search(question, context)
        else:
            results = await self._llm_reasoning(question, context)

        # Generate answer for this step
        answer = await self._answer_sub_question(question, results, context)

        return ReasoningStep(
            step_number=step_number,
            question=question,
            method=method,
            query=question,
            results=results,
            answer=answer["text"],
            confidence=answer["confidence"],
        )

    async def _select_method(self, question: str) -> str:
        """Determine the best method to answer this sub-question"""

        # Simple heuristics for method selection
        question_lower = question.lower()

        # Graph search for relationship queries
        if any(
            word in question_lower
            for word in [
                "related",
                "connected",
                "uses",
                "implements",
                "extends",
                "relationship",
                "connection",
                "link",
            ]
        ):
            return "graph"

        # Vector search for similarity/finding queries
        if any(
            word in question_lower
            for word in ["similar", "like", "find", "papers about", "research on"]
        ):
            return "vector"

        # Default to graph for most queries
        return "graph"

    async def _graph_search(
        self, question: str, context: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Search using graph traversal"""

        # Extract entities from question
        entities = await self._extract_entities_from_text(question)

        if not entities:
            return []

        # Find paths between entities or related papers
        query = """
        MATCH (e:Entity)
        WHERE e.name IN $entityNames
        OPTIONAL MATCH (e)<-[:MENTIONS]-(p:Paper)
        WITH e, collect(DISTINCT p) as papers
        OPTIONAL MATCH (e)-[r]-(e2:Entity)
        WITH e, papers, collect(DISTINCT {
            entity: e2.name,
            relationship: type(r),
            type: e2.type
        }) as relationships
        RETURN e.name as entity,
               e.type as entityType,
               papers[..5] as papers,
               relationships[..10] as relationships
        LIMIT $limit
        """

        results = self.neo4j_client.execute_query(
            query, {"entityNames": entities, "limit": self.max_results_per_hop}
        )

        return results if results else []

    async def _vector_search(
        self, question: str, context: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Search using vector similarity"""

        try:
            results = pinecone_store.search(question, k=self.max_results_per_hop)
            return results
        except Exception as e:
            self.logger.error(f"Vector search failed: {str(e)}")
            return []

    async def _llm_reasoning(
        self, question: str, context: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Use LLM for reasoning when graph/vector search insufficient"""

        # Format context
        context_text = "\n".join(
            [
                f"- {item.get('text', item.get('title', str(item)))}"
                for item in context[:5]
            ]
        )

        prompt = f"""Based on the research context below, answer this question:

Question: {question}

Context:
{context_text}

Provide a concise, factual answer based on the context."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )

        answer_text = response.choices[0].message.content.strip()

        return [{"source": "llm_reasoning", "text": answer_text, "method": "synthesis"}]

    async def _extract_entities_from_text(self, text: str) -> List[str]:
        """Extract entity names from text using simple pattern matching"""

        # In a real implementation, this would use NER or entity linking
        # For now, we'll search for entities that exist in our graph

        query = """
        MATCH (e:Entity)
        WHERE toLower($text) CONTAINS toLower(e.name)
        RETURN e.name as name
        LIMIT 10
        """

        results = self.neo4j_client.execute_query(query, {"text": text})
        return [r["name"] for r in results] if results else []

    async def _answer_sub_question(
        self,
        question: str,
        results: List[Dict[str, Any]],
        context: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate answer for a sub-question"""

        if not results:
            return {
                "text": "Insufficient information to answer this question.",
                "confidence": 0.0,
            }

        # Format results as context
        results_text = self._format_results_as_text(results)

        prompt = f"""Answer this specific question based on the evidence:

Question: {question}

Evidence:
{results_text}

Provide a concise, factual answer (1-2 sentences)."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.5,
        )

        answer_text = response.choices[0].message.content.strip()

        # Estimate confidence based on amount of evidence
        confidence = min(0.9, 0.5 + (len(results) * 0.1))

        return {"text": answer_text, "confidence": confidence}

    def _format_results_as_text(self, results: List[Dict[str, Any]]) -> str:
        """Format results into readable text"""

        formatted = []
        for i, result in enumerate(results[:10], 1):
            if "entity" in result:
                # Graph result
                formatted.append(
                    f"{i}. Entity: {result['entity']} ({result.get('entityType', 'unknown')})"
                )
                if result.get("papers"):
                    papers = result["papers"][:2]
                    for p in papers:
                        formatted.append(f"   - Paper: {p.get('title', 'Unknown')}")

            elif "text" in result:
                # Vector result
                formatted.append(f"{i}. {result['text'][:200]}...")

        return "\n".join(formatted) if formatted else "No relevant results found."

    async def _synthesize_answer(
        self,
        original_query: str,
        reasoning_steps: List[ReasoningStep],
        all_evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Synthesize final answer from all reasoning steps"""

        # Format reasoning path
        reasoning_text = "\n".join(
            [
                f"Step {s.step_number}: {s.question}\nAnswer: {s.answer}\n"
                for s in reasoning_steps
            ]
        )

        prompt = f"""You are synthesizing a final answer to a complex research question.

Original Question: {original_query}

Reasoning Steps:
{reasoning_text}

Based on the step-by-step reasoning above, provide a comprehensive final answer to the original question.

Your answer should:
1. Directly address the original question
2. Integrate insights from all reasoning steps
3. Cite specific findings when possible
4. Be clear and concise (2-4 sentences)

Final Answer:"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.6,
        )

        final_answer = response.choices[0].message.content.strip()

        # Extract sources (papers mentioned)
        sources = []
        for evidence in all_evidence:
            if "papers" in evidence:
                for paper in evidence["papers"]:
                    if paper.get("arxiv_id"):
                        sources.append(
                            {
                                "arxiv_id": paper["arxiv_id"],
                                "title": paper.get("title", "Unknown"),
                            }
                        )

        # Calculate overall confidence
        avg_confidence = sum(s.confidence for s in reasoning_steps) / len(
            reasoning_steps
        )

        return {
            "answer": final_answer,
            "confidence": avg_confidence,
            "sources": sources[:10],  # Top 10 sources
        }


# Global reasoning agent instance
reasoning_agent = ReasoningAgent()


async def answer_complex_query(
    query: str, context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Answer a complex query using multi-hop reasoning"""
    return await reasoning_agent.answer_complex_query(query, context)
