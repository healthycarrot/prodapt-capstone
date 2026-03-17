# FR-08 Live Eval Report

- Generated at (UTC): 2026-03-17T16:13:06.072043+00:00
- Model: gpt-4.1-mini
- Case limit: 10
- Retrieval top-k: 5
- Search result top-n: 1

## Selected Cases
- `frontend_web_developer`
- `backend_software_engineer`
- `data_analyst_reporting`
- `frontend_react_typescript`
- `data_engineer_etl`
- `machine_learning_engineer`
- `secretary_office_operations`
- `bank_manager_financial_analysis`
- `business_analyst_database_statistics`
- `accountant_financial_reporting`

## Execution Overview

| Case | /retrieve | /search | Notes |
|---|---:|---:|---|
| `frontend_web_developer` | 200 / 5 results | 200 / 5 results | - |
| `backend_software_engineer` | 200 / 5 results | 200 / 5 results | - |
| `data_analyst_reporting` | 200 / 5 results | 200 / 5 results | - |
| `frontend_react_typescript` | 422 / 0 results | 422 / 0 results | retrieve: invalid ESCO labels: skill_terms=['React']; occupation_terms=['frontend developer']; search: invalid ESCO labels: skill_terms=['React']; occupation_terms=['frontend developer'] |
| `data_engineer_etl` | 200 / 1 results | 200 / 1 results | - |
| `machine_learning_engineer` | 200 / 0 results | 200 / 0 results | search returned no ranked results |
| `secretary_office_operations` | 200 / 5 results | 200 / 5 results | - |
| `bank_manager_financial_analysis` | 200 / 5 results | 200 / 5 results | - |
| `business_analyst_database_statistics` | 200 / 5 results | 200 / 5 results | - |
| `accountant_financial_reporting` | 200 / 5 results | 200 / 5 results | - |

## Retrieve Metric Summary

| Metric | Count | Avg | Median | Min | Max | Threshold | Below Threshold |
|---|---:|---:|---:|---:|---:|---:|---:|
| `contextual_precision` | 8 | 0.826 | 0.958 | 0.000 | 1.000 | 0.50 | 1 |
| `contextual_relevancy` | 8 | 0.628 | 0.664 | 0.200 | 0.915 | 0.50 | 2 |

## Retrieve Lowest Scoring Cases

### `contextual_precision`
- `data_engineer_etl` (aggregate retrieval context) score=0.000: The score is 0.00 because the first node in retrieval contexts is irrelevant, as it only mentions 'SQL' but lacks explicit references to 'data engineer', 'ETL pipelines', or 'analytics platforms'. Since there are no relevant nodes ranked higher, the score cannot be higher.
- `backend_software_engineer` (aggregate retrieval context) score=0.806: The score is 0.81 because the first node in retrieval contexts is relevant and appropriately ranked at the top, as it mentions 'Python (computer programming)' and 'SQL' skills along with backend development and API experience. However, the second node, which is irrelevant due to its focus on cloud infrastructure and lack of backend or API development, is ranked too high at position 2, lowering the score. The relevant nodes at ranks 3 and 4 correctly follow, but the presence of an irrelevant node at rank 2 prevents a perfect score.
- `frontend_web_developer` (aggregate retrieval context) score=0.887: The score is 0.89 because most nodes in retrieval contexts that mention 'web developer' and skills like 'JavaScript' and 'CSS' relevant to frontend interactive web applications are ranked higher, such as the first, second, fourth, and fifth nodes. However, the third node, which focuses on Drupal development and backend site building rather than frontend interactive web applications, is ranked third, slightly lowering the score since an irrelevant node appears relatively high in the ranking.

### `contextual_relevancy`
- `data_engineer_etl` (aggregate retrieval context) score=0.200: The score is 0.20 because the reasons for irrelevancy highlight that the retrieval context lacks mention of 'data engineer' and key skills like ETL pipelines, Spark, and analytics platforms, which are central to the input query. Although the relevant statement includes 'SQL', it does not cover the other critical skills or occupation terms, making the overall context largely irrelevant.
- `backend_software_engineer` (aggregate retrieval context) score=0.424: The score is 0.42 because although the retrieval context includes relevant skills such as 'Python' and 'SQL' and mentions 'software engineer' in the resume excerpt, the reasons for irrelevancy highlight that the experience focuses mainly on front-end development and .NET technologies rather than backend engineering or API development with Python, which is the core of the input query.
- `secretary_office_operations` (aggregate retrieval context) score=0.604: The score is 0.60 because while many statements such as 'Education: Bachelor of Science | Business Administration' and 'Experience: Street Team Member' are irrelevant to secretary duties, relevant statements like 'Occupations: administrative assistant, secretary' and detailed 'Experience: ADMINISTRATIVE ASSISTANT' roles demonstrate coordination of office tasks and support daily administration, aligning with the input query.

## Search Metric Summary

| Metric | Count | Avg | Median | Min | Max | Threshold | Below Threshold |
|---|---:|---:|---:|---:|---:|---:|---:|
| `answer_relevancy` | 8 | 0.773 | 0.757 | 0.571 | 1.000 | 0.50 | 0 |
| `bias` | 8 | 0.000 | 0.000 | 0.000 | 0.000 | 0.30 | 0 |
| `experience_fit` | 8 | 0.779 | 0.859 | 0.413 | 0.898 | 0.50 | 1 |
| `faithfulness` | 8 | 0.710 | 0.817 | 0.250 | 1.000 | 0.60 | 2 |
| `skill_coverage` | 8 | 0.699 | 0.764 | 0.310 | 0.818 | 0.50 | 1 |

## Search Lowest Scoring Cases

### `answer_relevancy`
- `accountant_financial_reporting` (candidate_id=912312eb-2c44-4f70-bb7b-9fc963ac3aaa) score=0.571: The score is 0.57 because the response partially addresses the query by mentioning finance-related roles, but it includes irrelevant details about ongoing roles, management skills, and general leadership that do not specifically pertain to accounting or financial statement reporting experience.
- `backend_software_engineer` (candidate_id=7d9be2eb-c0c2-4539-a62c-92cc2a930a09) score=0.600: The score is 0.60 because the response includes relevant technical skills like Python and API development, but it also contains several irrelevant statements about leadership and soft skills that do not directly address the technical query, preventing a higher score.
- `data_engineer_etl` (candidate_id=bc2a2473-8b5f-4b44-b4f4-8bd81fc1fc81) score=0.667: The score is 0.67 because the response includes relevant technical skills related to data engineering for ETL pipelines and analytics platforms, such as Spark, ETL, and SQL. However, it also contains irrelevant information about IT management, teaching, and communication skills, which lowers the relevancy score.

### `bias`
- `accountant_financial_reporting` (candidate_id=912312eb-2c44-4f70-bb7b-9fc963ac3aaa) score=0.000: The score is 0.00 because there are no reasons indicating any bias in the actual output, reflecting a completely unbiased response.
- `backend_software_engineer` (candidate_id=7d9be2eb-c0c2-4539-a62c-92cc2a930a09) score=0.000: The score is 0.00 because there are no reasons indicating any bias in the actual output, reflecting a completely unbiased response.
- `bank_manager_financial_analysis` (candidate_id=eaa995fb-470b-45f5-aa5d-ad66750cdd61) score=0.000: The score is 0.00 because there are no reasons indicating any bias in the actual output, reflecting a completely unbiased response.

### `experience_fit`
- `data_engineer_etl` (candidate_id=bc2a2473-8b5f-4b44-b4f4-8bd81fc1fc81) score=0.413: The actual output correctly identifies the candidate's skills in SQL and management experience but fails to confirm ETL pipeline or analytics platform experience, which aligns with the retrieval context showing no explicit ETL or Spark skills. However, the output does not fully acknowledge the absence of Spark or direct data engineering experience as emphasized in the expected output, and it somewhat inflates seniority by highlighting strong management experience without clear relevance to the data engineer role. The retrieval context supports the candidate's IT management and SQL skills but lacks evidence for ETL or analytics platform expertise, which the actual output only partially addresses.
- `backend_software_engineer` (candidate_id=7d9be2eb-c0c2-4539-a62c-92cc2a930a09) score=0.622: The actual output correctly identifies the candidate's Python skill and backend experience in Drupal development, aligning with the retrieval context. However, it notes the absence of explicit API development experience, which is a key job requirement, showing appropriate caution. Leadership and seniority claims are moderate and supported by the lead developer role. The output misses mentioning SQL skills explicitly, which are part of the required skill terms, and does not fully address the software engineer occupation term, focusing more on Drupal developer roles. Overall, the response is mostly accurate but omits some important skill matches and occupation alignment.
- `business_analyst_database_statistics` (candidate_id=75c70480-357a-4360-a0e1-e2c2af96edfd) score=0.788: The actual output accurately identifies strong alignment with the business analyst occupation and relevant database and statistics skills, supported by the retrieval context showing extensive experience since 2014. The mention of progressive roles and leadership in multi-regional projects reflects appropriate seniority without inflation. However, the omission of explicit process improvement experience, a key aspect in the expected output, results in a minor deduction.

### `faithfulness`
- `data_analyst_reporting` (candidate_id=b7d802c5-fa90-4e68-b0df-a32062b52eae) score=0.250: The score is 0.25 despite no listed contradictions, indicating the actual output likely contains inaccuracies or omissions not explicitly detailed here, leading to low faithfulness to the retrieval context.
- `accountant_financial_reporting` (candidate_id=912312eb-2c44-4f70-bb7b-9fc963ac3aaa) score=0.333: The score is 0.33 because the actual output incorrectly implies the individual's current role is ongoing and includes a recency score, which the context does not support.
- `backend_software_engineer` (candidate_id=7d9be2eb-c0c2-4539-a62c-92cc2a930a09) score=0.800: The score is 0.80 because there are no contradictions, indicating the actual output is largely faithful to the retrieval context, though there may be minor areas for improvement.

### `skill_coverage`
- `data_engineer_etl` (candidate_id=bc2a2473-8b5f-4b44-b4f4-8bd81fc1fc81) score=0.310: The actual output mentions SQL explicitly but omits Spark and ETL skills, which are must-have according to the expected output. It acknowledges the lack of ETL pipeline and analytics platform experience, showing honesty about skill gaps. However, transferable skills like database migration and server management are claimed but only partially supported by the retrieval context, which lacks direct references to ETL or Spark. The response includes some relevant details but misses key required skills and does not fully align with the expected data engineering focus.
- `backend_software_engineer` (candidate_id=7d9be2eb-c0c2-4539-a62c-92cc2a930a09) score=0.618: The actual output correctly identifies Python and backend experience, referencing Drupal development and leadership roles, which aligns with the retrieval context. However, it fails to explicitly mention SQL and does not confirm API or service development experience, which are must-have skills in the expected output. The output honestly acknowledges the lack of explicit API development evidence, avoiding unsupported claims. The mention of leadership and communication skills is supported by the context, but the omission of SQL and API skills reduces alignment.
- `secretary_office_operations` (candidate_id=d0e33ecc-43d8-45a6-8363-f8c5313e4de3) score=0.708: The actual output explicitly mentions strong coordination and administrative support experience aligned with the secretary role, fulfilling the must-have skills of office task coordination and daily administration. However, it does not explicitly mention the critical transferable skills of 'use microsoft office' and 'use word processing software' despite these being present in the retrieval context. The output avoids generic praise and demonstrates relevant experience but misses explicitly acknowledging these key software skills, which are essential per the expected output.
