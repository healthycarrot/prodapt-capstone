# Issue #13 Plan Review (Post Full Run)

Reviewed after:
- Issue #10 full run (`balanced + medium`, 2484 docs)
- Issue #11/#12 readiness analysis

## Conclusion
- The current Issue #13 scope is directionally correct.
- No major rewrite is required for ranking metrics themselves.
- A few additions are recommended so evaluation reflects operational reality.

## Observed Baseline
- status distribution:
  - success: 2027 (81.6%)
  - partial: 427 (17.19%)
  - failed: 30 (1.21%)
- graph rerank:
  - applied: 1181 (47.54%)
  - rank changed: 590 (23.75%)
- llm handoff cohorts:
  - rerank trigger: 26 (1.05%)
  - extraction trigger: 781 (31.44%)
- weak-label pilot metrics (from current normalized output):
  - weak P@1: 0.1884
  - weak P@5: 0.1175
  - weak MRR@10: 0.2291
  - weak MAP@10: 0.2268
  - weak coverage@10: 0.3003

## Recommended Adjustments To Issue #13
1. Keep existing ranking metrics:
   - P@1, P@5, MRR@10, MAP@K, coverage@10
2. Add segmentation outputs:
   - metrics by `normalization_status` (success / partial / failed)
   - metrics by `llm_handoff` cohorts (rerank/extraction trigger)
3. Keep weak-label mode as supplementary:
   - do not use weak-only score as final gate
   - emit warning when weak coverage@10 is below threshold (e.g. 0.40)
4. Add integrity block to the evaluation report:
   - duplicate upsert keys count
   - missing candidate_id count
5. Acceptance criteria update:
   - 50-doc smoke output + full-run summary output
   - Gold and Weak mode execution both required
   - JSON + Markdown + A/B diff table output
