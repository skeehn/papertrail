from typing import Dict, List, Optional

from app.core.logging import get_logger
from app.database import get_paper_by_id

logger = get_logger("contradiction_detector")


class ContradictionDetector:
    """Detects contradictions between research papers"""

    @staticmethod
    def extract_claims(text: str) -> List[Dict[str, any]]:
        """Extract claims from paper text"""
        claims = []

        # Simple claim extraction patterns
        # Pattern: "We show/demonstrate/find/reveal that..."
        import re

        claim_patterns = [
            r"(?:We|This study|Our results)\s+(?:show|demonstrate|find|reveal|indicate|suggest|conclude)\s+that\s+([^.!?]+[.!?])",
            r"(?:The|Our)\s+(?:findings|results|analysis)\s+(?:suggest|indicate|reveal)\s+that\s+([^.!?]+[.!?])",
            r"(?:It is)\s+(?:evident|clear|shown|demonstrated)\s+that\s+([^.!?]+[.!?])",
        ]

        for pattern in claim_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for claim in matches:
                claims.append(
                    {
                        "text": claim.strip(),
                        "confidence": 0.7,  # Base confidence
                    }
                )

        return claims

    @staticmethod
    def compare_claims(
        claim1: Dict[str, any], claim2: Dict[str, any]
    ) -> Dict[str, any]:
        """Compare two claims for contradictions"""
        comparison = {
            "claim1": claim1["text"],
            "claim2": claim2["text"],
            "contradiction_score": 0.0,
            "contradiction_type": None,
            "details": [],
        }

        # Simple keyword-based contradiction detection
        negations = [
            "not",
            "no",
            "never",
            "cannot",
            "impossible",
            "unlikely",
            "fails",
            "does not",
        ]

        claim1_lower = claim1["text"].lower()
        claim2_lower = claim2["text"].lower()

        def _norm(s: str) -> str:
            return " ".join(s.split())

        claim1_lower = _norm(claim1_lower)
        claim2_lower = _norm(claim2_lower)

        # Check for direct contradictions
        for neg in negations:
            if neg in claim1_lower and neg not in claim2_lower:
                # Potential contradiction if claims are similar
                if _norm(claim1_lower.replace(neg, "")) == claim2_lower:
                    comparison["contradiction_score"] = 0.8
                    comparison["contradiction_type"] = "direct_negation"
                    comparison["details"].append(
                        f"Claim 1 uses '{neg}' while Claim 2 makes the same assertion"
                    )
                    break
            elif neg in claim2_lower and neg not in claim1_lower:
                if _norm(claim2_lower.replace(neg, "")) == claim1_lower:
                    comparison["contradiction_score"] = 0.8
                    comparison["contradiction_type"] = "direct_negation"
                    comparison["details"].append(
                        f"Claim 2 uses '{neg}' while Claim 1 makes the same assertion"
                    )
                    break

        # Check for opposite claims (e.g., "X increases Y" vs "X decreases Y")
        opposites = [
            ("increases", "decreases"),
            ("improves", "worsens"),
            ("better", "worse"),
            ("higher", "lower"),
            ("more", "less"),
            ("significant", "insignificant"),
        ]

        for opp1, opp2 in opposites:
            if opp1 in claim1_lower and opp2 in claim2_lower:
                # Check if they're talking about similar subjects (simplified check)
                subjects = set()
                for word in claim1_lower.split():
                    if word in ["performance", "accuracy", "efficiency", "quality"]:
                        subjects.add(word)

                if subjects:
                    comparison["contradiction_score"] = max(
                        comparison["contradiction_score"], 0.6
                    )
                    comparison["contradiction_type"] = "opposite_assertions"
                    comparison["details"].append(
                        f"Claims use opposite terms: '{opp1}' vs '{opp2}'"
                    )
                    break
            elif opp2 in claim1_lower and opp1 in claim2_lower:
                subjects = set()
                for word in claim2_lower.split():
                    if word in ["performance", "accuracy", "efficiency", "quality"]:
                        subjects.add(word)

                if subjects:
                    comparison["contradiction_score"] = max(
                        comparison["contradiction_score"], 0.6
                    )
                    comparison["contradiction_type"] = "opposite_assertions"
                    comparison["details"].append(
                        f"Claims use opposite terms: '{opp2}' vs '{opp1}'"
                    )
                    break

        return comparison

    @staticmethod
    def detect_contradictions(paper_ids: List[str]) -> Dict[str, any]:
        """Detect contradictions across multiple papers"""
        result = {
            "contradictions": [],
            "metrics": {
                "total_papers_analyzed": len(paper_ids),
                "total_contradictions": 0,
                "high_confidence_contradictions": 0,
                "by_type": {},
            },
        }

        # Extract claims from all papers
        all_claims: List[tuple] = []
        for paper_id in paper_ids:
            try:
                paper = get_paper_by_id(paper_id)
                if paper:
                    text = paper.get("abstract", "") + " " + paper.get("text", "")
                    claims = ContradictionDetector.extract_claims(text)
                    for claim in claims:
                        all_claims.append((paper_id, claim))
            except Exception as e:
                logger.warning(f"Failed to extract claims from {paper_id}: {e}")
                continue

        # Compare all claims against each other
        compared_pairs = set()
        for i, (paper_id1, claim1) in enumerate(all_claims):
            for j, (paper_id2, claim2) in enumerate(all_claims):
                if i >= j:
                    continue  # Skip comparing same claim or already compared pairs

                # Skip comparing claims from same paper
                if paper_id1 == paper_id2:
                    continue

                pair_key = (paper_id1, paper_id2)
                if pair_key in compared_pairs:
                    continue
                compared_pairs.add(pair_key)

                comparison = ContradictionDetector.compare_claims(claim1, claim2)

                if comparison["contradiction_score"] > 0.5:
                    result["contradictions"].append(
                        {
                            "paper1_id": paper_id1,
                            "paper2_id": paper_id2,
                            "claim1": claim1["text"],
                            "claim2": claim2["text"],
                            "score": comparison["contradiction_score"],
                            "type": comparison["contradiction_type"],
                            "details": comparison["details"],
                        }
                    )

                    # Update metrics
                    result["metrics"]["total_contradictions"] += 1
                    if comparison["contradiction_score"] > 0.7:
                        result["metrics"]["high_confidence_contradictions"] += 1

                    # Track by type
                    ctype = comparison["contradiction_type"] or "unknown"
                    result["metrics"]["by_type"][ctype] = (
                        result["metrics"]["by_type"].get(ctype, 0) + 1
                    )

        # Sort contradictions by score (highest first)
        result["contradictions"].sort(key=lambda x: x["score"], reverse=True)

        return result

    @staticmethod
    def group_contradictions(
        contradictions: List[Dict[str, any]],
    ) -> List[Dict[str, any]]:
        """Group related contradictions together"""
        groups = []
        used_indices = set()

        for i, contradiction in enumerate(contradictions):
            if i in used_indices:
                continue

            group = [contradiction]
            used_indices.add(i)

            # Find related contradictions
            for j, other_contradiction in enumerate(contradictions):
                if j <= i or j in used_indices:
                    continue

                # Group if they share papers or similar claims
                if (
                    contradiction["paper1_id"] == other_contradiction["paper1_id"]
                    or contradiction["paper1_id"] == other_contradiction["paper2_id"]
                    or contradiction["paper2_id"] == other_contradiction["paper1_id"]
                    or contradiction["paper2_id"] == other_contradiction["paper2_id"]
                ):

                    group.append(other_contradiction)
                    used_indices.add(j)

            if len(group) > 1:
                groups.append(
                    {
                        "contradictions": group,
                        "count": len(group),
                        "paper_pairs": list(
                            set([(c["paper1_id"], c["paper2_id"]) for c in group])
                        ),
                    }
                )

        return groups

    @staticmethod
    def get_contradiction_summary(paper_id: str) -> Dict[str, any]:
        """Get contradiction summary for a specific paper"""
        summary = {
            "paper_id": paper_id,
            "contradicts_with": [],
            "contradicted_by": [],
            "total_contradictions": 0,
            "types": {},
        }

        try:
            from app.database import helix_store

            # Query Neo4j for contradictions involving this paper
            query = """
            MATCH (p1:Paper {arxiv_id: $paper_id})-[r1:MENTIONS]-(c1)
            MATCH (p2:Paper)-[r2:MENTIONS]-(c2)
            WHERE c1.name = c2.name
            AND (p1.arxiv_id = p2.arxiv_id OR p1.arxiv_id = $paper_id)
            RETURN p2.arxiv_id as other_paper_id, c1.name as conflicting_claim
            """

            result = None  # Use helix_store.list_papers()

            for record in result:
                other_paper = record["other_paper_id"]
                claim = record["conflicting_claim"]

                summary["total_contradictions"] += 1

                if other_paper == paper_id:
                    summary["contradicts_with"].append(
                        {
                            "claim": claim,
                        }
                    )
                else:
                    summary["contradicted_by"].append(
                        {
                            "paper_id": other_paper,
                            "claim": claim,
                        }
                    )

        except Exception as e:
            logger.error(f"Failed to get contradiction summary for {paper_id}: {e}")

        return summary
