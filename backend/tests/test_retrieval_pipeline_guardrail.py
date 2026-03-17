from __future__ import annotations

import unittest

from app.domain import QueryUnderstandingOutput, RetrievalPipelineOutput, SearchQueryInput
from app.services.input_guardrail import InputGuardrailService
from app.services.response_builder import ResponseBuilderService
from app.services.retrieval_pipeline import RetrievalPipelineService


class _StubQueryUnderstandingService:
    def __init__(self, output: QueryUnderstandingOutput) -> None:
        self.output = output
        self.calls = 0

    def extract(self, search_input: SearchQueryInput) -> QueryUnderstandingOutput:
        self.calls += 1
        return self.output


class _FailIfCalled:
    def normalize(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("normalize should not be called in guardrail early-return path")

    def check(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("check should not be called in guardrail early-return path")

    def compile(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("compile should not be called in guardrail early-return path")

    def build(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("build should not be called in guardrail early-return path")

    def search(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("search should not be called in guardrail early-return path")

    def fuse(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("fuse should not be called in guardrail early-return path")

    def rerank(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("rerank should not be called in guardrail early-return path")


class RetrievalPipelineGuardrailTests(unittest.TestCase):
    def test_pre_guardrail_blocks_before_query_understanding(self) -> None:
        query_understanding = _StubQueryUnderstandingService(
            output=QueryUnderstandingOutput(original_query="short")
        )
        fail = _FailIfCalled()
        pipeline = RetrievalPipelineService(
            input_guardrail=InputGuardrailService(min_query_length=20, require_skill_or_occupation=True),
            query_understanding=query_understanding,
            query_normalizer=fail,  # type: ignore[arg-type]
            conflict_checker=fail,  # type: ignore[arg-type]
            hard_filter_compiler=fail,  # type: ignore[arg-type]
            query_builder=fail,  # type: ignore[arg-type]
            vector_search=fail,  # type: ignore[arg-type]
            keyword_search=fail,  # type: ignore[arg-type]
            fusion=fail,  # type: ignore[arg-type]
            cross_encoder=fail,  # type: ignore[arg-type]
            rerank=fail,  # type: ignore[arg-type]
            response_builder=ResponseBuilderService(),
        )

        output = pipeline.run(SearchQueryInput(query_text="backend engineer"))

        self.assertIsInstance(output, RetrievalPipelineOutput)
        self.assertTrue(output.retry_required)
        self.assertIn("query_text", output.conflict_fields)
        self.assertEqual(query_understanding.calls, 0)

    def test_post_guardrail_blocks_after_query_understanding(self) -> None:
        query_understanding = _StubQueryUnderstandingService(
            output=QueryUnderstandingOutput(
                original_query="Hiring backend engineer quickly for expansion across business teams",
                skill_terms=[],
                occupation_terms=[],
                industry_terms=[],
            )
        )
        fail = _FailIfCalled()
        pipeline = RetrievalPipelineService(
            input_guardrail=InputGuardrailService(min_query_length=20, require_skill_or_occupation=True),
            query_understanding=query_understanding,
            query_normalizer=fail,  # type: ignore[arg-type]
            conflict_checker=fail,  # type: ignore[arg-type]
            hard_filter_compiler=fail,  # type: ignore[arg-type]
            query_builder=fail,  # type: ignore[arg-type]
            vector_search=fail,  # type: ignore[arg-type]
            keyword_search=fail,  # type: ignore[arg-type]
            fusion=fail,  # type: ignore[arg-type]
            cross_encoder=fail,  # type: ignore[arg-type]
            rerank=fail,  # type: ignore[arg-type]
            response_builder=ResponseBuilderService(),
        )

        output = pipeline.run(
            SearchQueryInput(query_text="Hiring backend engineer quickly for expansion across business teams")
        )

        self.assertTrue(output.retry_required)
        self.assertIn("skill_terms", output.conflict_fields)
        self.assertIn("occupation_terms", output.conflict_fields)
        self.assertEqual(query_understanding.calls, 1)


if __name__ == "__main__":
    unittest.main()
