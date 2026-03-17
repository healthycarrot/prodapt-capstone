from __future__ import annotations

import unittest

from app.domain import EducationFilter, ExperienceFilter, QueryUnderstandingOutput, SearchQueryInput
from app.services.input_guardrail import InputGuardrailService


class InputGuardrailServiceTests(unittest.TestCase):
    def test_allows_valid_query_with_role_hint(self) -> None:
        service = InputGuardrailService(min_query_length=20)
        search_input = SearchQueryInput(query_text="Hiring backend engineer with Python and API experience")

        result = service.evaluate(search_input, understood=None)

        self.assertFalse(result.retry_required)
        self.assertEqual(result.conflict_fields, [])

    def test_rejects_too_short_query(self) -> None:
        service = InputGuardrailService(min_query_length=20)
        search_input = SearchQueryInput(query_text="backend engineer")

        result = service.evaluate(search_input, understood=None)

        self.assertTrue(result.retry_required)
        self.assertIn("query_text", result.conflict_fields)
        self.assertIn("too short", result.conflict_reason)

    def test_rejects_json_payload(self) -> None:
        service = InputGuardrailService(min_query_length=1)
        search_input = SearchQueryInput(query_text='{"role":"backend engineer","skill":"python"}')

        result = service.evaluate(search_input, understood=None)

        self.assertTrue(result.retry_required)
        self.assertIn("natural-language", result.conflict_reason)

    def test_rejects_personal_contact_information(self) -> None:
        service = InputGuardrailService(min_query_length=1)
        search_input = SearchQueryInput(
            query_text="Backend engineer role. Contact me at test.user@example.com"
        )

        result = service.evaluate(search_input, understood=None)

        self.assertTrue(result.retry_required)
        self.assertIn("personal contact information", result.conflict_reason)

    def test_allows_query_when_skill_or_occupation_info_is_missing_by_default(self) -> None:
        service = InputGuardrailService(min_query_length=20)
        search_input = SearchQueryInput(query_text="We are hiring immediately for our growing team")

        result = service.evaluate(search_input, understood=None)

        self.assertFalse(result.retry_required)
        self.assertEqual(result.conflict_fields, [])

    def test_rejects_when_skill_or_occupation_info_is_missing_if_enabled(self) -> None:
        service = InputGuardrailService(min_query_length=20, require_skill_or_occupation=True)
        search_input = SearchQueryInput(query_text="We are hiring immediately for our growing team")

        result = service.evaluate(search_input, understood=None)

        self.assertTrue(result.retry_required)
        self.assertIn("skill_terms", result.conflict_fields)
        self.assertIn("occupation_terms", result.conflict_fields)

    def test_generates_non_blocking_warnings_for_missing_optional_hints(self) -> None:
        service = InputGuardrailService(min_query_length=1)
        search_input = SearchQueryInput(
            query_text="Hiring backend engineer with Python",
            requested_occupation_terms=["backend engineer"],
        )
        understood = QueryUnderstandingOutput(
            original_query=search_input.query_text,
            skill_terms=["python"],
            occupation_terms=["backend engineer"],
            industry_terms=[],
            experience=ExperienceFilter(),
            education=EducationFilter(),
        )

        result = service.evaluate(search_input, understood=understood)

        self.assertFalse(result.retry_required)
        codes = {item.code for item in result.warnings}
        self.assertEqual(
            codes,
            {"missing_experience_hint", "missing_education_hint", "missing_industry_hint"},
        )


if __name__ == "__main__":
    unittest.main()
