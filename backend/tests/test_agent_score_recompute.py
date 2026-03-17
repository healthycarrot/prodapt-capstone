from __future__ import annotations

import unittest

from app.services.agent_scoring.agents.common import (
    recompute_career_score,
    recompute_education_score,
    recompute_experience_score,
    recompute_skill_score,
    recompute_soft_skill_score,
)


class AgentScoreRecomputeTests(unittest.TestCase):
    def test_skill_score_recomputed_from_breakdown_and_weights(self) -> None:
        score = recompute_skill_score(
            match_score=0.8,
            skill_depth_score=0.6,
            management_score=0.4,
            match_weight=0.5,
            depth_weight=0.25,
            management_weight=0.25,
        )
        self.assertAlmostEqual(score, 0.65, places=6)

    def test_experience_score_uses_recency_as_linear_bonus(self) -> None:
        no_bonus = recompute_experience_score(
            industry_match_score=0.5,
            experience_level_match_score=0.5,
            recency_score=0.0,
            industry_weight=0.5,
            level_weight=0.5,
        )
        max_bonus = recompute_experience_score(
            industry_match_score=0.5,
            experience_level_match_score=0.5,
            recency_score=1.0,
            industry_weight=0.5,
            level_weight=0.5,
        )
        self.assertAlmostEqual(no_bonus, 0.5, places=6)
        self.assertAlmostEqual(max_bonus, 0.6, places=6)

    def test_education_score_is_education_match_score(self) -> None:
        score = recompute_education_score(education_match_score=0.73)
        self.assertAlmostEqual(score, 0.73, places=6)

    def test_career_score_is_average_of_two_dimensions(self) -> None:
        score = recompute_career_score(vertical_growth_score=0.8, scope_expansion_score=0.4)
        self.assertAlmostEqual(score, 0.6, places=6)

    def test_soft_skill_score_is_average_of_three_dimensions(self) -> None:
        score = recompute_soft_skill_score(
            communication_score=0.9,
            teamwork_score=0.6,
            adaptability_score=0.3,
        )
        self.assertAlmostEqual(score, 0.6, places=6)


if __name__ == "__main__":
    unittest.main()
