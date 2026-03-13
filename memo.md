# data
## 構造
- summary: sectionで抽出
- skill: sectionで抽出, bullet pointで抽出
- experience: sectionで抽出, subsectionで抽出
- education: sectionで抽出


## metadata候補
### まず採用
- resume_id:CSVの ID
- category:CSVの Category
- source:今回は基本 csv
- parser_version:自前で付与
- chunk_index:分割時に自前で付与
- section:summary, skills, experience, education, projects, certifications など
- start_date
- end_date
- is_current

### 前処理で採用有望
- title: experienceの職歴ブロック先頭から抽出
- company: title直後やCompany Nameパターンから抽出
- skill_tags: skills section + 本文 + bullet pointから抽出

### LLM補完で追加候補
- seniority: junior / mid / senior / lead / manager
- normalized_title: titleの表記ゆれ統一
- role_family: software / data / network / teaching / finance など
- normalized_company: 会社名の表記ゆれ統一

### RAG向け優先セット
- resume_id
- category
- source
- parser_version
- section
- chunk_index
- title
- company
- start_date
- end_date
- is_current
- skill_tags


# 各機能の検討
## Career Progression Analysis

## Technical Evaluation Agent
experienceの文章からスキルを抽出することについての論文。
few-shotが有効で、スキル抽出の精度が上がることが示されている。
https://aclanthology.org/2024.nlp4hr-1.3.pdf?utm_source=chatgpt.com

LLMを含めた3つの手法でスキル抽出を行い、そのハイブリッドなアプローチが高い精度を示すことを示した論文。
https://aclanthology.org/2025.genaik-1.15.pdf?utm_source=chatgpt.com

この論文は履歴書全体からESCOの職種へのマッチングを行う手法を提案している。
https://arxiv.org/html/2503.02056v1


# Document breakdown
- それぞれのdocumentからskillとoccupation(category)、experience、educationを抽出して、構造化されたデータにする。
- skillとoccupationはESCOの分類体系を使う。