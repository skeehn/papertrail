"""Trend analysis service for detecting research trends over time"""

import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.database.hydradb_store import hydradb_store

logger = get_logger("trend_analyzer")


class TrendAnalyzer:
    """Service for analyzing trends in research topics over time"""

    def __init__(self):
        self.logger = logger

    async def _aggregate(self) -> Dict[str, Any]:
        """Fetch sources once and build paper/entity maps for aggregation.

        papers: paper_id -> {title, year}
        entity_mentions: entity_name -> list of (paper_id, year)
        """
        try:
            sources = await hydradb_store.list_sources(limit=1000)
        except Exception as e:
            self.logger.warning("Source listing failed", error=str(e))
            sources = []

        papers: Dict[str, Dict[str, Any]] = {}
        entity_mentions: Dict[str, List[Tuple[str, Optional[str]]]] = defaultdict(list)
        current_year = str(datetime.now().year)

        for source in sources:
            attrs = source.get("attributes") or {}
            kind = attrs.get("source", "arxiv")
            if kind == "entity":
                name = attrs.get("entity_name", "")
                pid = attrs.get("paper_id", "")
                if name:
                    entity_mentions[name].append((pid, None))
            else:
                pid = attrs.get("arxiv_id") or attrs.get("paper_id")
                if not pid:
                    continue
                papers[pid] = {
                    "title": attrs.get("title") or source.get("title", ""),
                    "year": attrs.get("year") or current_year,
                }

        resolved: Dict[str, List[Tuple[str, str]]] = {}
        for name, mentions in entity_mentions.items():
            resolved[name] = [
                (pid, papers.get(pid, {}).get("year", current_year)) for pid, _ in mentions
            ]
        return {"papers": papers, "entity_mentions": resolved}

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
        """Yearly paper-mention counts for one entity, from HydraDB sources."""

        agg = await self._aggregate()
        mentions = agg["entity_mentions"].get(entity_name, [])
        this_year = int(datetime.now().year)
        cutoff = this_year - max(1, time_window_years) + 1

        per_year: Dict[str, List[str]] = defaultdict(list)
        for pid, year in mentions:
            if not pid:
                continue
            y = int(year) if (year or "").isdigit() else this_year
            if y < cutoff:
                continue
            per_year[str(y)].append(pid)

        if not per_year:
            return {
                "entity": entity_name,
                "trend": "no_data",
                "yearly_counts": [],
                "growth_rate": 0,
                "status": "No data available",
            }

        sorted_years = sorted(per_year)
        example_papers = contextually = [
            agg["papers"].get(pid, {}).get("title", pid)
            for pid in per_year[sorted_years[-1]]
        ]
        yearly = [(y, len(per_year[y])) for y in sorted_years]
        growth_rate = self._calculate_growth_rate(yearly)
        trend_direction = self._determine_trend(yearly)

        return {
            "entity": entity_name,
            "trend": trend_direction,
            "yearly_counts": [
                {
                    "year": y,
                    "count": count,
                    "example_papers": example_papers[:3],
                }
                for y, count in yearly
            ],
            "growth_rate": growth_rate,
            "total_mentions": sum(count for _, count in yearly),
            "time_span": f"{sorted_years[0]} - {sorted_years[-1]}",
        }

    async def _analyze_all_entities(
        self, time_window_years: int, min_mentions: int
    ) -> Dict[str, Any]:
        """Entity trends aggregated in-memory from HydraDB sources."""

        agg = await self._aggregate()
        this_year = int(datetime.now().year)
        cutoff = this_year - max(1, time_window_years) + 1

        trends = []
        for entity_name, mentions in agg["entity_mentions"].items():
            per_year: Dict[str, int] = defaultdict(int)
            for pid, year in mentions:
                if not pid:
                    continue
                y = int(year) if (year or "").isdigit() else this_year
                if y >= cutoff:
                    per_year[str(y)] += 1
            if sum(per_year.values()) < min_mentions:
                continue

            sorted_years = sorted(per_year)
            yearly_data = [(y, per_year[y]) for y in sorted_years]
            trends.append(
                {
                    "entity": entity_name,
                    "type": "entity",
                    "trend": self._determine_trend(yearly_data),
                    "growth_rate": self._calculate_growth_rate(yearly_data),
                    "total_mentions": sum(count for _, count in yearly_data),
                    "yearly_data": [
                        {"year": y, "count": per_year[y]} for y in sorted_years
                    ],
                }
            )

        rising = [t for t in trends if t["trend"] == "rising"]
        declining = [t for t in trends if t["trend"] == "declining"]

        return {
            "summary": {
                "total_entities": len(trends),
                "rising": len(rising),
                "declining": len(declining),
                "stable": sum(1 for t in trends if t["trend"] == "stable"),
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

        n = len(counts)
        x = list(range(n))
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(counts)

        numerator = sum((x[i] - x_mean) * (counts[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        if slope > y_mean * 0.1:
            return "rising"
        elif slope < -y_mean * 0.1:
            return "declining"
        else:
            return "stable"

    async def detect_emerging_topics(
        self, lookback_months: int = 12, min_growth_rate: float = 50.0
    ) -> List[Dict[str, Any]]:
        """Detect topics whose recent mentions outpace their historical ones."""

        agg = await self._aggregate()
        this_year = int(datetime.now().year)
        cutoff_year = this_year - max(1, lookback_months // 12)

        emerging = []
        for entity_name, mentions in agg["entity_mentions"].items():
            recent = sum(1 for pid, year in mentions if (year or "0").isdigit() and int(year) > cutoff_year)
            older = len(mentions) - recent
            if recent == 0 or older == 0 or older == 0:
                continue
            growth = (recent - older) / older * 100
            if growth < min_growth_rate:
                continue
            emerging.append(
                {
                    "entity": entity_name,
                    "type": "entity",
                    "recent_mentions": recent,
                    "historical_mentions": older,
                    "growth_rate": round(growth, 2),
                    "status": "emerging",
                }
            )

        emerging.sort(key=lambda e: e["growth_rate"], reverse=True)
        self.logger.info(f"Found {len(emerging)} emerging topics")
        return emerging[:20]



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
        """Count entity mentions in the most recent papers."""

        agg = await self._aggregate()
        this_year = str(datetime.now().year)
        recent_tag = str(this_year)

        counts: List[Tuple[str, int, List[str]]] = []
        for entity_name, mentions in agg["entity_mentions"].items():
            recent_papers = [pid for pid, year in mentions if year == recent_tag]
            if not recent_papers:
                continue
            examples = [
                agg["papers"].get(pid, {}).get("title", pid) for pid in recent_papers[:3]
            ]
            counts.append((entity_name, len(recent_papers), examples))

        counts.sort(key=lambda t: t[1], reverse=True)
        return [
            {
                "entity": entity,
                "type": "entity",
                "recent_mentions": count,
                "example_papers": examples,
                "status": "trending",
            }
            for entity, count, examples in counts[:top_n]
        ]


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
