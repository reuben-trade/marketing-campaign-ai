"""Tests for recommendation engine service."""

import pytest

from app.services.recommendation_engine import RecommendationEngine


class TestRecommendationEngine:
    """Tests for RecommendationEngine."""

    def test_extract_trends_empty_ads(self):
        """Test extracting trends from empty ads list."""
        engine = RecommendationEngine()
        trends = engine._extract_trends([])

        assert trends["total_ads"] == 0
        assert trends["avg_engagement"] == 0

    def test_extract_trends_with_ads(self):
        """Test extracting trends from ads."""
        engine = RecommendationEngine()
        ads = [
            {
                "likes": 100,
                "comments": 50,
                "shares": 25,
                "analysis": {
                    "visual_themes": ["Modern", "Clean"],
                    "ctas": ["Shop Now"],
                    "emotional_appeal": "Aspiration",
                },
            },
            {
                "likes": 200,
                "comments": 100,
                "shares": 50,
                "analysis": {
                    "visual_themes": ["Modern", "Bold"],
                    "ctas": ["Learn More"],
                    "emotional_appeal": "Curiosity",
                },
            },
        ]

        trends = engine._extract_trends(ads)

        assert trends["total_ads"] == 2
        assert trends["avg_engagement"] == 262.5
        assert "Modern" in trends["visual_themes"]

    def test_validate_recommendations_valid(self):
        """Test validating a valid recommendations structure."""
        engine = RecommendationEngine()
        recommendations = {
            "trend_analysis": {},
            "recommendations": [
                {
                    "concept": {"title": "Test"},
                    "priority": "high",
                    "ad_format": "video",
                }
            ],
        }

        errors = engine.validate_recommendations(recommendations)

        assert len(errors) == 0

    def test_validate_recommendations_missing_fields(self):
        """Test validating recommendations with missing fields."""
        engine = RecommendationEngine()
        recommendations = {}

        errors = engine.validate_recommendations(recommendations)

        assert len(errors) > 0
        assert any("recommendations" in e for e in errors)

    def test_validate_recommendations_empty_list(self):
        """Test validating recommendations with empty list."""
        engine = RecommendationEngine()
        recommendations = {
            "trend_analysis": {},
            "recommendations": [],
        }

        errors = engine.validate_recommendations(recommendations)

        assert any("No recommendations" in e for e in errors)

    def test_prepare_business_strategy_context(self):
        """Test preparing business strategy context."""
        engine = RecommendationEngine()
        strategy = {
            "business_name": "Test Company",
            "industry": "Technology",
        }

        context = engine._prepare_business_strategy_context(strategy)

        assert "Test Company" in context
        assert "Technology" in context

    def test_prepare_ads_analysis_context(self):
        """Test preparing ads analysis context."""
        engine = RecommendationEngine()
        ads = [
            {
                "id": "123",
                "competitor_name": "Competitor A",
                "creative_type": "image",
                "likes": 100,
                "comments": 50,
                "shares": 25,
                "analysis": {"summary": "Test summary"},
            }
        ]

        context = engine._prepare_ads_analysis_context(ads)

        assert "Competitor A" in context
        assert "image" in context
