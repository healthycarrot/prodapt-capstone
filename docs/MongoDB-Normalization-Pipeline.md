# MongoDB Normalization Pipeline (1st_data -> normalized_candidates)

## æ–¹é‡
- ESCO ã¯ raw æ§‹é€ ã®ã¾ã¾ MongoDB ã«æ ¼ç´ã—ã¦å‚ç…§ã™ã‚‹ã€‚
- 1st_data (`Resume.csv`) ã‚’å…¥åŠ›ã¨ã—ã¦æ­£è¦åŒ–ã—ã€`normalized_candidates` ã«ä¿å­˜ã™ã‚‹ã€‚
- åˆæœŸãƒžãƒƒãƒãƒ³ã‚°ã¯ `exact + alt_label + fuzzy(>=0.85)`ã€‚
- å°†æ¥ LLM ã‚’è¿½åŠ ã§ãã‚‹ã‚ˆã†ã€matcher ã‚’ãƒ¢ã‚¸ãƒ¥ãƒ¼ãƒ«åŒ–ã™ã‚‹ã€‚
- è·ç¨®å€™è£œã¯ ESCO occupation-skill relation ã§å†ãƒ©ãƒ³ã‚­ãƒ³ã‚°ã™ã‚‹ï¼ˆgraph rerankï¼‰ã€‚
- æ›–æ˜§ã‚±ãƒ¼ã‚¹ã®ã¿ LLM rerank ã‚’ç™ºç«ã—ã€çµæžœã¯ãƒ¡ãƒ¢ãƒªã‚­ãƒ£ãƒƒã‚·ãƒ¥ã™ã‚‹ã€‚
- ä»»æ„ã§ Top-N ã®ã¿ embedding rerank ã‚’é©ç”¨ã™ã‚‹ã€‚

## ã‚³ãƒ¬ã‚¯ã‚·ãƒ§ãƒ³

### Raw å‚ç…§ã‚³ãƒ¬ã‚¯ã‚·ãƒ§ãƒ³ (ESCO)
- `raw_esco_occupations`
- `raw_esco_skills`
- `raw_esco_isco_groups`
- `raw_esco_skill_groups`
- `raw_esco_broader_relations_occ`
- `raw_esco_broader_relations_skill`
- `raw_esco_occupation_skill_relations`

### å…¥åŠ›ã‚³ãƒ¬ã‚¯ã‚·ãƒ§ãƒ³
- `source_1st_resumes`

### æ­£è¦åŒ–å‡ºåŠ›ã‚³ãƒ¬ã‚¯ã‚·ãƒ§ãƒ³
- `normalized_candidates`

## å®Ÿè£…ãƒ•ã‚¡ã‚¤ãƒ«
- CSVå–è¾¼: [script/pipeline_mongo/ingest_csv_to_mongo.py](script/pipeline_mongo/ingest_csv_to_mongo.py)
- æ­£è¦åŒ–: [script/pipeline_mongo/normalize_1st_to_mongo.py](script/pipeline_mongo/normalize_1st_to_mongo.py)
- è©•ä¾¡ãƒ©ãƒ³ãƒŠãƒ¼: [script/pipeline_mongo/evaluate_normalization.py](script/pipeline_mongo/evaluate_normalization.py)

## å¿…è¦ãƒ‘ãƒƒã‚±ãƒ¼ã‚¸
- `pymongo`
- `rapidfuzz`
- `openai`
- `python-dotenv`

## å®Ÿè¡Œæ‰‹é †

1. CSV ã‚’ MongoDB ã«ãƒ­ãƒ¼ãƒ‰
- ESCO raw CSV
- 1st_data `Resume.csv`

2. æ­£è¦åŒ–ãƒ‘ã‚¤ãƒ—ãƒ©ã‚¤ãƒ³å®Ÿè¡Œ
- `source_1st_resumes` ã‚’èª­ã¿å–ã‚Š
- occupation/skill ã‚’ ESCO å‚ç…§ã§å€™è£œåŒ–
- occupation ã‚’ ESCO relation + optional embedding/LLM ã§å†ãƒ©ãƒ³ã‚­ãƒ³ã‚°
- `normalized_candidates` ã¸ upsert

### æŽ¨å¥¨å®Ÿè¡Œä¾‹ï¼ˆgraph + LLM + embeddingï¼‰
- `python .\normalize_1st_to_mongo.py --db-name prodapt_capstone --limit 0 --ranking-profile balanced --threshold-strictness medium --embedding-mode auto --metrics-out .\script\pipeline_mongo\metrics_issue10_full_balanced_medium.json`

### ä¸»ãªè¿½åŠ ãƒ•ãƒ©ã‚°
- `--graph-essential-weight`
- `--graph-optional-weight`
- `--graph-max-boost`
- `--embedding-mode` (`auto` / `off`)
- `--embedding-model`
- `--embedding-occ-top-k`
- `--embedding-skill-top-k`
- `--embedding-min-confidence`
- `--milvus-occ-collection`
- `--milvus-skill-collection`

## æ­£è¦åŒ–ãƒ«ãƒ¼ãƒ« (ç¢ºå®š)
- `candidate_id`: UUID v4
- `source_dataset`: `1st_data`
- `source_record_id`: 1st ã® `ID`
- fuzzy é–¾å€¤: `0.85`
- rank: `confidence` é™é †
- is_primary: `rank = 1`
- å†å®Ÿè¡Œ: upsertï¼ˆæ—¢å­˜å€™è£œ/å­é…åˆ—å·®ã—æ›¿ãˆï¼‰
- occupationå€™è£œã« `graph_support`ï¼ˆessential/optional hitï¼‰ã‚’ä»˜ä¸Ž

## ãƒ¢ã‚¸ãƒ¥ãƒ¼ãƒ«æ§‹æˆ (å°†æ¥LLMå¯¾å¿œ)
- `ExactMatcher`
- `AltLabelMatcher`
- `FuzzyMatcher`
- å°†æ¥è¿½åŠ : `LLMMatcher`

`normalize_1st_to_mongo.py` ã¯ matcher ã‚¤ãƒ³ã‚¿ãƒ¼ãƒ•ã‚§ãƒ¼ã‚¹çµŒç”±ã§å‘¼ã¶ãŸã‚ã€LLM matcher ã‚’è¿½åŠ ã—ã¦ã‚‚æ—¢å­˜å‡¦ç†ã«æœ€å°å¤‰æ›´ã§å¯¾å¿œã§ãã‚‹ã€‚

## è©•ä¾¡ãƒ©ãƒ³ãƒŠãƒ¼

### å®Ÿè¡Œ
- `python .\script\pipeline_mongo\evaluate_normalization.py --db-name prodapt_capstone --mode weak --limit 50 --k 10 --output-json .\script\pipeline_mongo\eval_issue13_smoke50.json --output-md .\docs\Eval-Normalization-Issue13-Smoke50.md`
- `python .\script\pipeline_mongo\evaluate_normalization.py --db-name prodapt_capstone --mode gold --gold-file .\gold_labels.csv --k 10 --output-json .\script\pipeline_mongo\eval_issue13_gold.json --output-md .\docs\Eval-Normalization-Issue13-Gold.md`
- `python .\script\pipeline_mongo\evaluate_normalization.py --db-name prodapt_capstone --mode weak --k 10 --baseline-json .\script\pipeline_mongo\eval_issue13_before.json --output-json .\script\pipeline_mongo\eval_issue13_after.json --output-md .\docs\Eval-Normalization-Issue13-Diff.md`

### æŒ‡æ¨™
- `P@5`
- `MRR@10`
- `MAP@K`
- `coverage@10`

### å‚™è€ƒ
- `--mode auto` ã§ã¯ `--gold-file` æŒ‡å®šæ™‚ã« Goldï¼ŒæœªæŒ‡å®šæ™‚ã« Weak
- Weak ã¯ category-anchor overlap ã«åŸºã¥ãè£œåŠ©è©•ä¾¡
- `--baseline-json` ãŒã‚ã‚‹ã¨ A/B å·®åˆ†è¡¨ã‚’ Markdown ã«å‡ºåŠ›

## Issue #11/#12 Handoff (from full run)
- Full run command:
  - `python .\normalize_1st_to_mongo.py --db-name prodapt_capstone --ranking-profile balanced --threshold-strictness medium --limit 0 --metrics-out .\metrics_issue10_full_balanced_medium.json`
- Full run size:
  - `processed_docs`: 2484
- Status distribution:
  - `success`: 2027
  - `partial`: 427
  - `failed`: 30
- Graph rerank effect:
  - applied docs: 1181
  - rank changed docs: 590

### Issue #11 connection fields
- `normalized_candidates.llm_handoff.rerank_trigger`
- `normalized_candidates.llm_handoff.extraction_trigger`
- `normalized_candidates.matching_debug.llm_handoff`

`llm_handoff` is generated from rule output and can be used to gate LLM calls to a controlled cohort.

### Issue #12 integrity checks
- Upsert key: `source_dataset + source_record_id`
- Duplicate key count should remain `0`
- `candidate_id` should be present for all normalized documents

### Review artifacts
- `script/pipeline_mongo/metrics_issue10_full_balanced_medium.json`
- `script/pipeline_mongo/issue11_12_readiness_report.json`
- `docs/Issue11-12-Review.md`

