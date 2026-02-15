"""Tests for insights API endpoints"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestComplexReasoning:
    """Test complex reasoning endpoint"""

    @patch("app.api.v1.endpoints.insights.answer_complex_query")
    def test_complex_reasoning_success(self, mock_answer):
        """Test successful complex reasoning query"""
        mock_answer.return_value = {
            "answer": "Test answer",
            "reasoning_steps": [],
            "sources": [],
            "confidence": 0.9,
        }

        response = client.post(
            "/api/v1/insights/reasoning",
            json={
                "query": "What methods from NLP are used in computer vision?",
                "context": None,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data or "response" in data


class TestTrendAnalysis:
    """Test trend analysis endpoints"""

    @patch("app.api.v1.endpoints.insights.analyze_trends")
    def test_analyze_trends(self, mock_analyze):
        """Test trend analysis"""
        mock_analyze.return_value = {
            "entity_name": "Transformer",
            "trend_data": [],
            "growth_rate": 50.0,
            "summary": {},
        }

        response = client.post(
            "/api/v1/insights/trends/analyze",
            json={
                "entity_name": "Transformer",
                "time_window_years": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "entity_name" in data or "trend_data" in data

    @patch("app.api.v1.endpoints.insights.find_emerging_topics")
    def test_get_emerging_topics(self, mock_find):
        """Test getting emerging topics"""
        mock_find.return_value = [
            {
                "entity_name": "Topic 1",
                "growth_rate": 75.0,
                "mention_count": 100,
            }
        ]

        response = client.get("/api/v1/insights/trends/emerging?lookback_months=12")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @patch("app.api.v1.endpoints.insights.get_trending")
    def test_get_trending_topics(self, mock_get):
        """Test getting trending topics"""
        mock_get.return_value = [
            {
                "entity_name": "Trending Topic",
                "mention_count": 200,
            }
        ]

        response = client.get("/api/v1/insights/trends/trending?recent_months=6")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @patch("app.api.v1.endpoints.insights.compare_entity_trends")
    def test_compare_trends(self, mock_compare):
        """Test comparing trends"""
        mock_compare.return_value = {
            "entities": ["Entity1", "Entity2"],
            "comparison": {},
        }

        response = client.post(
            "/api/v1/insights/trends/compare",
            json={
                "entity_names": ["BERT", "GPT-3"],
                "time_window_years": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "entities" in data or "comparison" in data


class TestResearchSummary:
    """Test research summary endpoint"""

    @patch("app.api.v1.endpoints.insights.get_trending")
    @patch("app.api.v1.endpoints.insights.find_emerging_topics")
    @patch("app.api.v1.endpoints.insights.analyze_trends")
    def test_get_research_summary(self, mock_analyze, mock_emerging, mock_trending):
        """Test getting research landscape summary"""
        mock_trending.return_value = []
        mock_emerging.return_value = []
        mock_analyze.return_value = {"summary": {}}

        response = client.get("/api/v1/insights/summary")

        assert response.status_code == 200
        data = response.json()
        assert "trending_now" in data or "emerging_topics" in data
