# FR-08 Live Eval Report

- Generated at (UTC): 2026-03-17T19:04:52.775744+00:00
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
| `frontend_react_typescript` | 200 / 5 results | 200 / 5 results | - |
| `data_engineer_etl` | 200 / 1 results | 200 / 1 results | - |
| `machine_learning_engineer` | 200 / 0 results | 200 / 0 results | search returned no ranked results |
| `secretary_office_operations` | 200 / 5 results | 200 / 5 results | - |
| `bank_manager_financial_analysis` | 200 / 5 results | 200 / 5 results | - |
| `business_analyst_database_statistics` | 200 / 5 results | 200 / 5 results | - |
| `accountant_financial_reporting` | 200 / 5 results | 200 / 5 results | - |

## Retrieve Metric Summary

| Metric | Count | Avg | Median | Min | Max | Threshold | Below Threshold |
|---|---:|---:|---:|---:|---:|---:|---:|
| `contextual_precision` | 9 | 0.750 | 0.887 | 0.000 | 1.000 | 0.50 | 2 |
| `contextual_relevancy` | 9 | 0.570 | 0.604 | 0.100 | 0.911 | 0.50 | 3 |

## Retrieve Lowest Scoring Cases

### `contextual_precision`
- `data_engineer_etl` (aggregate retrieval context) score=0.000: The score is 0.00 because all nodes in the retrieval contexts are irrelevant, with the first node ranked highest despite not mentioning 'data engineer' or ETL pipelines, the second node mentioning only SQL but lacking Spark or ETL, and the third node focusing on unrelated IT management and network engineering roles. This ordering places irrelevant nodes above any relevant information, resulting in the lowest possible score.
- `frontend_react_typescript` (aggregate retrieval context) score=0.333: The score is 0.33 because the first two nodes in retrieval contexts are irrelevant, as they lack mention of React or TypeScript, which are key for the query. The relevant node appears only at rank 3, indicating that irrelevant nodes are ranked higher than the relevant one, lowering the score.
- `business_analyst_database_statistics` (aggregate retrieval context) score=0.700: The score is 0.70 because the first node in retrieval contexts is relevant and appropriately ranked at the top, reflecting strong alignment with the input query. However, the second node, which is irrelevant, is ranked higher than some relevant nodes, as it mentions 'database' and 'business process improvement' but lacks explicit 'business analyst' occupation and detailed analytical experience, which lowers the score. Additionally, other irrelevant nodes ranked above relevant ones focus on roles like 'data analyst' or sales rather than the specific business analyst skills sought, preventing a higher score.

### `contextual_relevancy`
- `data_engineer_etl` (aggregate retrieval context) score=0.100: The score is 0.10 because the reasons for irrelevancy highlight that the experience and education focus on IT management, network engineering, and system administration rather than data engineering or ETL pipelines, while the only relevant statement mentions SQL but lacks specific references to ETL pipelines, Spark, or analytics platforms.
- `backend_software_engineer` (aggregate retrieval context) score=0.394: The score is 0.39 because although the retrieval context includes relevant skills like 'Python' and 'SQL' and mentions 'software engineer' related roles, much of the content focuses on Drupal development and IT leadership roles unrelated to backend engineering with Python and API development, as highlighted by reasons such as 'The occupations listed do not include software engineer' and 'The qualifications focus on Drupal and related skills, not on Python or API development relevant to backend engineering.'
- `frontend_react_typescript` (aggregate retrieval context) score=0.486: The score is 0.49 because while the retrieval context includes relevant skills like JavaScript and CSS and mentions web developer occupations, it lacks specific references to React and TypeScript, which are key to the input query. Additionally, many reasons for irrelevancy highlight the focus on backend development and unrelated technologies, reducing overall relevance.

## Search Metric Summary

| Metric | Count | Avg | Median | Min | Max | Threshold | Below Threshold |
|---|---:|---:|---:|---:|---:|---:|---:|
| `answer_relevancy` | 9 | 0.922 | 1.000 | 0.750 | 1.000 | 0.50 | 0 |
| `bias` | 9 | 0.000 | 0.000 | 0.000 | 0.000 | 0.30 | 0 |
| `experience_fit` | 9 | 0.605 | 0.701 | 0.285 | 0.803 | 0.50 | 3 |
| `faithfulness` | 9 | 0.657 | 0.500 | 0.500 | 1.000 | 0.60 | 5 |
| `skill_coverage` | 9 | 0.654 | 0.695 | 0.332 | 0.818 | 0.50 | 2 |

## Search Lowest Scoring Cases

### `answer_relevancy`
- `business_analyst_database_statistics` (candidate_id=75c70480-357a-4360-a0e1-e2c2af96edfd) score=0.750: The score is 0.75 because the response mostly addresses the query about a business analyst with database and statistics skills for process improvement, but it includes an irrelevant statement about a management role that does not pertain to the requested skills or occupation, preventing a higher score.
- `data_analyst_reporting` (candidate_id=b7d802c5-fa90-4e68-b0df-a32062b52eae) score=0.750: The score is 0.75 because the response mostly addresses the query about a data analyst with skills in SQL and Python, but it includes a statement that does not relate directly to the skills or occupation, preventing a higher score.
- `bank_manager_financial_analysis` (candidate_id=eaa995fb-470b-45f5-aa5d-ad66750cdd61) score=0.800: The score is 0.80 because the response appropriately addresses the bank manager role with financial analysis and banking operations experience, but it includes irrelevant information about corporate banking experience, which was not mentioned in the input.

### `bias`
- `accountant_financial_reporting` (candidate_id=912312eb-2c44-4f70-bb7b-9fc963ac3aaa) score=0.000: The score is 0.00 because there are no reasons indicating any bias in the actual output, reflecting a completely unbiased response.
- `backend_software_engineer` (candidate_id=7d9be2eb-c0c2-4539-a62c-92cc2a930a09) score=0.000: The score is 0.00 because there are no reasons indicating any bias in the actual output, reflecting a completely unbiased response.
- `bank_manager_financial_analysis` (candidate_id=eaa995fb-470b-45f5-aa5d-ad66750cdd61) score=0.000: The score is 0.00 because there are no reasons indicating bias in the actual output, reflecting a completely unbiased response.

### `experience_fit`
- `data_engineer_etl` (candidate_id=bc2a2473-8b5f-4b44-b4f4-8bd81fc1fc81) score=0.285: The actual output identifies SQL and database migration skills but omits key required skills such as Spark and ETL pipeline development, which are central to the query and expected output. The retrieval context shows no evidence of Spark or explicit ETL pipeline experience, supporting the gaps noted in the actual output. However, the actual output fails to mention any data engineering occupation or relevant pipeline-building experience, which is a significant mismatch with the expected output. The response correctly flags missing skills but does not fully align with the expected candidate profile.
- `frontend_react_typescript` (candidate_id=7d9be2eb-c0c2-4539-a62c-92cc2a930a09) score=0.423: The actual output correctly identifies relevant skills like JavaScript and CSS and relevant occupations such as web developer and software developer, aligning partially with the expected output. However, it explicitly notes the absence of React and TypeScript experience, which are key to the query, indicating a gap. The retrieval context supports the presence of JavaScript and CSS skills but does not mention React or TypeScript, confirming the actual output's caution. The candidate's seniority and experience are accurately reflected without inflation. The main shortcoming is the omission of any positive evidence of TypeScript or React, which are critical for the query, leading to a moderate score.
- `backend_software_engineer` (candidate_id=7d9be2eb-c0c2-4539-a62c-92cc2a930a09) score=0.465: The actual output correctly identifies Python programming and software developer roles, aligning partially with the retrieval context and expected output. However, it omits mention of SQL skills and API or service development experience, which are key requirements. It also notes gaps in backend development beyond Drupal, reflecting some recency and seniority accurately but lacks explicit reference to the candidate's seniority level (Information Technology Specialist III). The absence of API development experience and limited backend skills are appropriately flagged, but the output does not fully capture the candidate's relevant qualifications or the full scope of the expected experience.

### `faithfulness`
- `accountant_financial_reporting` (candidate_id=912312eb-2c44-4f70-bb7b-9fc963ac3aaa) score=0.500: The score is 0.50 but there are no listed contradictions, indicating the actual output may partially align with the retrieval context yet lacks full faithfulness for reasons not specified here.
- `backend_software_engineer` (candidate_id=7d9be2eb-c0c2-4539-a62c-92cc2a930a09) score=0.500: The score is 0.50 because the actual output fails to acknowledge the individual's explicit backend development skills in Drupal, despite the context clearly stating five years of experience in both frontend and backend development and theming.
- `data_analyst_reporting` (candidate_id=b7d802c5-fa90-4e68-b0df-a32062b52eae) score=0.500: The score is 0.50 because there are no listed contradictions, suggesting partial faithfulness, but the score indicates some discrepancies not detailed here.

### `skill_coverage`
- `data_engineer_etl` (candidate_id=bc2a2473-8b5f-4b44-b4f4-8bd81fc1fc81) score=0.332: The actual output mentions SQL explicitly, which aligns with one must-have skill, but omits Spark entirely and only generically references 'database migration' without confirming ETL or analytics platform experience. It acknowledges gaps in ETL pipeline development and analytics platforms, showing some honesty about skill gaps. However, the transferable skills cited (SQL, database migration) are only partially supported by the retrieval context, which lacks clear evidence of Spark or ETL pipeline work. The response lacks specific evidence of building or operating data pipelines and does not fully meet the expected output requirements.
- `data_analyst_reporting` (candidate_id=b7d802c5-fa90-4e68-b0df-a32062b52eae) score=0.455: The actual output mentions SQL and related skills like business intelligence and database management systems, which aligns partially with the expected SQL skill. However, it omits explicit mention of Python and report-building or dashboard experience, which are key must-have skills in the expected output. The transferable skills cited (SQL, business intelligence) are supported by the retrieval context, lending credibility. The output fails to acknowledge any significant skill gaps despite missing important skills like Python and explicit report/dashboard experience, and it contains generic praise ('very strong fit') without detailed justification. These shortcomings reduce alignment with the evaluation criteria.
- `backend_software_engineer` (candidate_id=7d9be2eb-c0c2-4539-a62c-92cc2a930a09) score=0.638: The actual output explicitly mentions Python skills and software developer roles, aligning with the expected requirement for Python and software engineering experience. It also honestly acknowledges the lack of explicit API development experience and limited backend skills beyond Drupal, addressing skill gaps. However, it omits mention of SQL skills, which are a must-have according to the expected output, and does not provide evidence of API or service development from the retrieval context. The response is specific and grounded in the context but incomplete regarding all required skills.
