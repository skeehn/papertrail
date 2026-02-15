from collections import Counter
from typing import Dict, List, Optional

from app.core.logging import get_logger
from app.database import list_papers

logger = get_logger("recommender")


class Recommender:
    """Recommends papers based on current library"""

    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from paper text"""
        import re

        # Get significant words (4+ characters, not common stop words)
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "but",
            "by",
            "for",
            "if",
            "in",
            "into",
            "is",
            "it",
            "no",
            "not",
            "of",
            "on",
            "or",
            "such",
            "that",
            "their",
            "then",
            "there",
            "these",
            "this",
            "to",
            "was",
            "will",
            "with",
            "have",
            "this",
            "that",
        }

        # Extract keywords using regex
        words = re.findall(r"\b[A-Za-z]{4,}\b", text.lower())
        keywords = [w for w in words if w not in stop_words]

        return Counter(keywords).most_common(max_keywords)

    @staticmethod
    def calculate_paper_similarity(
        paper1: Dict[str, any], paper2: Dict[str, any]
    ) -> float:
        """Calculate similarity score between two papers"""
        similarity = 0.0

        # Compare titles
        title1 = paper1.get("title", "").lower()
        title2 = paper2.get("title", "").lower()
        title_words1 = set(title1.split())
        title_words2 = set(title2.split())

        if title_words1 and title_words2:
            title_intersection = title_words1 & title_words2
            title_union = title_words1 | title_words2
            title_jaccard = (
                len(title_intersection) / len(title_union) if title_union else 0
            )
            similarity += title_jaccard * 0.4

        # Compare authors
        authors1 = [a.lower() for a in paper1.get("authors", [])]
        authors2 = [a.lower() for a in paper2.get("authors", [])]
        if authors1 and authors2:
            author_intersection = set(authors1) & set(authors2)
            if author_intersection:
                similarity += min(len(author_intersection), 3) * 0.3

        # Compare abstracts (keyword overlap)
        abstract1 = paper1.get("abstract", "")
        abstract2 = paper2.get("abstract", "")

        if abstract1 and abstract2:
            keywords1 = set([k[0] for k in Recommender.extract_keywords(abstract1)])
            keywords2 = set([k[0] for k in Recommender.extract_keywords(abstract2)])

            if keywords1 and keywords2:
                keyword_intersection = keywords1 & keywords2
                keyword_union = keywords1 | keywords2
                keyword_jaccard = (
                    len(keyword_intersection) / len(keyword_union)
                    if keyword_union
                    else 0
                )
                similarity += keyword_jaccard * 0.3

        return min(similarity, 1.0)

    @staticmethod
    def recommend_papers(paper_ids: List[str], limit: int = 10) -> List[Dict[str, any]]:
        """Recommend papers based on current library"""
        try:
            # Get current papers
            current_papers = list_papers(limit=100)

            if not current_papers or len(current_papers) == 0:
                return []

            # Build paper ID map
            current_paper_map = {p.get("id", ""): p for p in current_papers}
            current_ids = set(current_paper_map.keys())

            # Get all other papers
            all_papers = list_papers(limit=500)
            other_papers = [p for p in all_papers if p.get("id", "") not in current_ids]

            if not other_papers:
                return []

            # Calculate similarity scores
            scored_papers = []

            for current_paper in current_papers:
                for other_paper in other_papers:
                    similarity = Recommender.calculate_paper_similarity(
                        current_paper, other_paper
                    )

                    if similarity > 0.1:  # Minimum similarity threshold
                        scored_papers.append(
                            {
                                "paper": other_paper,
                                "based_on": current_paper.get("id", ""),
                                "similarity": similarity,
                                "reason": Recommender._get_similarity_reason(
                                    similarity
                                ),
                            }
                        )

            # Sort by similarity and get top recommendations
            scored_papers.sort(key=lambda x: x["similarity"], reverse=True)

            # Deduplicate by paper ID, keeping highest similarity
            seen_papers = set()
            unique_recommendations = []

            for rec in scored_papers:
                paper_id = rec["paper"].get("id", "")
                if paper_id not in seen_papers:
                    seen_papers.add(paper_id)
                    unique_recommendations.append(rec)

                    if len(unique_recommendations) >= limit:
                        break

            return unique_recommendations[:limit]

        except Exception as e:
            logger.error(f"Failed to recommend papers: {e}")
            return []

    @staticmethod
    def _get_similarity_reason(similarity: float) -> str:
        """Get human-readable reason for similarity"""
        if similarity >= 0.7:
            return "Very similar - same research area"
        elif similarity >= 0.5:
            return "Similar - related research"
        elif similarity >= 0.3:
            return "Moderately related"
        else:
            return "Potentially relevant"

    @staticmethod
    def recommend_for_question(
        question: str, paper_ids: Optional[List[str]] = None, limit: int = 5
    ) -> List[Dict[str, any]]:
        """Recommend papers based on a research question"""
        try:
            # Extract keywords from question
            question_keywords = [
                k[0] for k in Recommender.extract_keywords(question, max_keywords=5)
            ]

            if not question_keywords:
                return []

            # Get papers
            if paper_ids:
                # Use specific papers as context
                papers = []
                for pid in paper_ids:
                    from app.database import get_paper_by_id

                    paper = get_paper_by_id(pid)
                    if paper:
                        papers.append(paper)
            else:
                # Use all papers
                papers = list_papers(limit=200)

            if not papers:
                return []

            # Score papers based on keyword matches
            scored_papers = []

            for paper in papers:
                title = paper.get("title", "").lower()
                abstract = paper.get("abstract", "")
                full_text = f"{title} {abstract}"

                # Calculate keyword overlap
                matched_keywords = 0
                for keyword in question_keywords:
                    if keyword in full_text:
                        matched_keywords += 1

                if matched_keywords > 0:
                    score = matched_keywords / len(question_keywords)
                    scored_papers.append(
                        {
                            "paper": paper,
                            "score": score,
                            "matched_keywords": matched_keywords,
                            "reason": f"Matches {matched_keywords} of {len(question_keywords)} question keywords",
                        }
                    )

            # Sort by score
            scored_papers.sort(key=lambda x: x["score"], reverse=True)

            return scored_papers[:limit]

        except Exception as e:
            logger.error(f"Failed to recommend papers for question: {e}")
            return []

    @staticmethod
    def get_trending_topics(limit: int = 10) -> List[Dict[str, any]]:
        """Get trending topics from paper library"""
        try:
            papers = list_papers(limit=500)

            if not papers:
                return []

            # Extract topics from all papers
            all_topics = []
            for paper in papers:
                abstract = paper.get("abstract", "")
                text = paper.get("text", "")
                keywords = Recommender.extract_keywords(
                    f"{abstract} {text}", max_keywords=5
                )

                for keyword, count in keywords:
                    all_topics.append(
                        {
                            "topic": keyword,
                            "count": count,
                            "paper_id": paper.get("id", ""),
                        }
                    )

            # Aggregate by topic
            topic_counts = Counter()
            for item in all_topics:
                topic_counts[item["topic"]] += 1

            # Get top topics
            trending = topic_counts.most_common(limit)

            return [
                {
                    "topic": topic,
                    "count": count,
                    "papers": [
                        item["paper_id"]
                        for item in all_topics
                        if item["topic"] == topic
                    ],
                }
                for topic, count in trending
            ]

        except Exception as e:
            logger.error(f"Failed to get trending topics: {e}")
            return []
