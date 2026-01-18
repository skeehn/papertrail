"""Trend analysis service for detecting research trends over time"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from app.core.config import settings
from app.core.logging import get_logger
from app.database.neo4j_client import Neo4jClient

logger = get_logger("trend_analyzer")


class TrendAnalyzer:
    """Service for analyzing trends in research topics over time"""

    def __init__(self):
        self.logger = logger
        self.neo4j_client = Neo4jClient()

    async def analyze_entity_trends(
        self,
        entity_name: Optional[str] = None,
        time_window_years: int = 5,
        min_mentions: int = 3,
    ) -> Dict[str, Any]:
        """
        Analyze how entity mentions change over time

        Args:
            entity_name: Specific entity to analyze (None for all)
            time_window_years: Years to look back
            min_mentions: Minimum mentions to include

        Returns:
            Dictionary with trend data
        """
        self.logger.info(f"Analyzing trends for: {entity_name or 'all entities'}")

        if entity_name:
            trends = await self._analyze_single_entity(entity_name, time_window_years)
        else:
            trends = await self._analyze_all_entities(time_window_years, min_mentions)

        return trends

    async def _analyze_single_entity(
        self, entity_name: str, time_window_years: int
    ) -> Dict[str, Any]:
        """Analyze trends for a specific entity"""

        query = """
        MATCH (p:Paper)-[:MENTIONS]->(e:Entity {name: $entityName})
        WHERE p.published_date IS NOT NULL
        WITH p, e,
             datetime(p.published_date) as pubDate,
             date.truncate('year', datetime(p.published_date)) as year
        WHERE pubDate > datetime() - duration({years: $timeWindow})
        WITH year, count(p) as mentionCount, collect(p.title)[..5] as examplePapers
        RETURN toString(year.year) as year, mentionCount, examplePapers
        ORDER BY year ASC
        """

        results = self.neo4j_client.execute_query(
            query, {"entityName": entity_name, "timeWindow": time_window_years}
        )

        if not results:
            return {
                "entity": entity_name,
                "trend": "no_data",
                "yearly_counts": [],
                "growth_rate": 0,
                "status": "No data available",
            }

        # Calculate growth metrics
        yearly_data = [(r["year"], r["mentionCount"]) for r in results]
        growth_rate = self._calculate_growth_rate(yearly_data)
        trend_direction = self._determine_trend(yearly_data)

        return {
            "entity": entity_name,
            "trend": trend_direction,
            "yearly_counts": [
                {
                    "year": r["year"],
                    "count": r["mentionCount"],
                    "example_papers": r.get("examplePapers", [])[:3],
                }
                for r in results
            ],
            "growth_rate": growth_rate,
            "total_mentions": sum(r["mentionCount"] for r in results),
            "time_span": f"{results[0]['year']} - {results[-1]['year']}",
        }

    async def _analyze_all_entities(
        self, time_window_years: int, min_mentions: int
    ) -> Dict[str, Any]:
        """Analyze trends for all entities"""

        query = """
        MATCH (p:Paper)-[:MENTIONS]->(e:Entity)
        WHERE p.published_date IS NOT NULL
        WITH e, p,
             datetime(p.published_date) as pubDate,
             date.truncate('year', datetime(p.published_date)) as year
        WHERE pubDate > datetime() - duration({years: $timeWindow})
        WITH e, year, count(p) as yearCount
        WITH e,
             collect({year: toString(year.year), count: yearCount}) as yearlyData,
             sum(yearCount) as totalMentions
        WHERE totalMentions >= $minMentions
        RETURN e.name as entity,
               e.type as entityType,
               yearlyData,
               totalMentions
        ORDER BY totalMentions DESC
        LIMIT 50
        """

        results = self.neo4j_client.execute_query(
            query, {"timeWindow": time_window_years, "minMentions": min_mentions}
        )

        trends = []
        for record in results:
            yearly_data = [(d["year"], d["count"]) for d in record["yearlyData"]]
            growth_rate = self._calculate_growth_rate(yearly_data)
            trend_direction = self._determine_trend(yearly_data)

            trends.append(
                {
                    "entity": record["entity"],
                    "type": record["entityType"],
                    "trend": trend_direction,
                    "growth_rate": growth_rate,
                    "total_mentions": record["totalMentions"],
                    "yearly_data": record["yearlyData"],
                }
            )

        # Categorize trends
        rising = [t for t in trends if t["trend"] == "rising"]
        declining = [t for t in trends if t["trend"] == "declining"]
        stable = [t for t in trends if t["trend"] == "stable"]

        return {
            "summary": {
                "total_entities": len(trends),
                "rising": len(rising),
                "declining": len(declining),
                "stable": len(stable),
            },
            "top_rising": sorted(rising, key=lambda x: x["growth_rate"], reverse=True)[
                :10
            ],
            "top_declining": sorted(declining, key=lambda x: x["growth_rate"])[:10],
            "most_mentioned": sorted(
                trends, key=lambda x: x["total_mentions"], reverse=True
            )[:20],
        }

    def _calculate_growth_rate(self, yearly_data: List[Tuple[str, int]]) -> float:
        """Calculate average year-over-year growth rate"""

        if len(yearly_data) < 2:
            return 0.0

        counts = [count for _, count in yearly_data]

        # Calculate year-over-year changes
        yoy_changes = []
        for i in range(1, len(counts)):
            if counts[i - 1] > 0:
                change = ((counts[i] - counts[i - 1]) / counts[i - 1]) * 100
                yoy_changes.append(change)

        return round(statistics.mean(yoy_changes), 2) if yoy_changes else 0.0

    def _determine_trend(self, yearly_data: List[Tuple[str, int]]) -> str:
        """Determine if trend is rising, declining, or stable"""

        if len(yearly_data) < 2:
            return "stable"

        counts = [count for _, count in yearly_data]

        # Simple linear regression
        n = len(counts)
        x = list(range(n))
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(counts)

        numerator = sum((x[i] - x_mean) * (counts[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        # Classify based on slope
        if slope > y_mean * 0.1:  # More than 10% of mean
            return "rising"
        elif slope < -y_mean * 0.1:
            return "declining"
        else:
            return "stable"

    async def detect_emerging_topics(
        self, lookback_months: int = 12, min_growth_rate: float = 50.0
    ) -> List[Dict[str, Any]]:
        """
        Detect emerging research topics

        Args:
            lookback_months: Months to look back for comparison
            min_growth_rate: Minimum growth rate to consider emerging

        Returns:
            List of emerging topics
        """

        query = """
        MATCH (p:Paper)-[:MENTIONS]->(e:Entity)
        WHERE p.published_date IS NOT NULL
        WITH e,
             datetime(p.published_date) as pubDate,
             datetime() - duration({months: $lookback}) as cutoffDate
        WITH e,
             sum(CASE WHEN pubDate > cutoffDate THEN 1 ELSE 0 END) as recentCount,
             sum(CASE WHEN pubDate <= cutoffDate THEN 1 ELSE 0 END) as olderCount
        WHERE recentCount > 0 AND olderCount > 0
        WITH e, recentCount, olderCount,
             ((toFloat(recentCount) - olderCount) / olderCount * 100) as growthRate
        WHERE growthRate >= $minGrowth
        RETURN e.name as entity,
               e.type as entityType,
               recentCount,
               olderCount,
               growthRate
        ORDER BY growthRate DESC
        LIMIT 20
        """

        results = self.neo4j_client.execute_query(
            query, {"lookback": lookback_months, "minGrowth": min_growth_rate}
        )

        emerging = []
        for record in results:
            emerging.append(
                {
                    "entity": record["entity"],
                    "type": record["entityType"],
                    "recent_mentions": record["recentCount"],
                    "historical_mentions": record["olderCount"],
                    "growth_rate": round(record["growthRate"], 2),
                    "status": "emerging",
                }
            )

        self.logger.info(f"Found {len(emerging)} emerging topics")
        return emerging

    async def compare_trends(
        self, entity_names: List[str], time_window_years: int = 5
    ) -> Dict[str, Any]:
        """
        Compare trends across multiple entities

        Args:
            entity_names: List of entity names to compare
            time_window_years: Years to analyze

        Returns:
            Comparison data
        """

        comparisons = []

        for entity_name in entity_names:
            trend_data = await self._analyze_single_entity(
                entity_name, time_window_years
            )
            comparisons.append(trend_data)

        # Find common years
        all_years = set()
        for comp in comparisons:
            for yc in comp.get("yearly_counts", []):
                all_years.add(yc["year"])

        common_years = sorted(all_years)

        # Create comparison matrix
        comparison_matrix = {}
        for year in common_years:
            comparison_matrix[year] = {}
            for comp in comparisons:
                entity = comp["entity"]
                yearly_counts = {
                    yc["year"]: yc["count"] for yc in comp.get("yearly_counts", [])
                }
                comparison_matrix[year][entity] = yearly_counts.get(year, 0)

        return {
            "entities": entity_names,
            "time_span": (
                f"{common_years[0]} - {common_years[-1]}" if common_years else "N/A"
            ),
            "individual_trends": comparisons,
            "comparison_matrix": comparison_matrix,
            "winner": (
                max(comparisons, key=lambda x: x.get("total_mentions", 0))["entity"]
                if comparisons
                else None
            ),
        }

    async def get_trending_now(
        self, recent_months: int = 6, top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get currently trending entities

        Args:
            recent_months: Definition of "now"
            top_n: Number of top trends to return

        Returns:
            List of trending entities
        """

        query = """
        MATCH (p:Paper)-[:MENTIONS]->(e:Entity)
        WHERE p.published_date IS NOT NULL
          AND datetime(p.published_date) > datetime() - duration({months: $recentMonths})
        WITH e, count(p) as mentionCount, collect(p.title)[..3] as examplePapers
        RETURN e.name as entity,
               e.type as entityType,
               mentionCount,
               examplePapers
        ORDER BY mentionCount DESC
        LIMIT $topN
        """

        results = self.neo4j_client.execute_query(
            query, {"recentMonths": recent_months, "topN": top_n}
        )

        trending = []
        for record in results:
            trending.append(
                {
                    "entity": record["entity"],
                    "type": record["entityType"],
                    "recent_mentions": record["mentionCount"],
                    "example_papers": record["examplePapers"],
                    "status": "trending",
                }
            )

        return trending


# Global trend analyzer instance
trend_analyzer = TrendAnalyzer()


async def analyze_trends(
    entity_name: Optional[str] = None, time_window_years: int = 5
) -> Dict[str, Any]:
    """Analyze trends for entity or all entities"""
    return await trend_analyzer.analyze_entity_trends(entity_name, time_window_years)


async def find_emerging_topics(
    lookback_months: int = 12, min_growth_rate: float = 50.0
) -> List[Dict[str, Any]]:
    """Find emerging research topics"""
    return await trend_analyzer.detect_emerging_topics(lookback_months, min_growth_rate)


async def get_trending(recent_months: int = 6, top_n: int = 10) -> List[Dict[str, Any]]:
    """Get currently trending topics"""
    return await trend_analyzer.get_trending_now(recent_months, top_n)


async def compare_entity_trends(
    entity_names: List[str], time_window_years: int = 5
) -> Dict[str, Any]:
    """Compare trends across entities"""
    return await trend_analyzer.compare_trends(entity_names, time_window_years)
