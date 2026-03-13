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

## 正規化パイプライン後のKey fields
- occupation/category
	- ESCO基準で正規化
	- 階層構造を保持
	- 複数候補を保持
	- raw文字列も保持
	- confidenceも保持
- skills
	- ESCO基準で正規化
	- 階層構造を保持
	- 複数候補を保持
	- raw文字列も保持
	- confidenceも保持
- experience[]
	- title
	- company
	- start_date
	- end_date
	- is_current
	- location
	- duration_months
	- raw_title
	- normalized_occupation_candidates
- current_location
- education[]
	- institution
	- degree
	- field_of_study
	- start_date
	- end_date
	- graduation_year
	- location
- resume_text


## JSON Schema
```json
{
	"type": "object",
	"required": [
		"occupation_category",
		"skills",
		"experience",
		"current_location",
		"education",
		"resume_text"
	],
	"properties": {
		"occupation_category": {
			"type": "array",
			"items": { "$ref": "#/$defs/esco_candidate" }
		},
		"skills": {
			"type": "array",
			"items": { "$ref": "#/$defs/esco_candidate" }
		},
		"experience": {
			"type": "array",
			"items": { "$ref": "#/$defs/experience_item" }
		},
		"current_location": { "type": ["string", "null"] },
		"education": {
			"type": "array",
			"items": { "$ref": "#/$defs/education_item" }
		},
		"resume_text": { "type": "string" },
		"source": { "type": ["string", "null"] },
		"extraction_confidence": { "type": ["number", "null"] }
	},
	"$defs": {
		"esco_candidate": {
			"type": "object",
			"required": ["raw_text", "confidence"],
			"properties": {
				"esco_id": { "type": ["string", "null"] },
				"preferred_label": { "type": ["string", "null"] },
				"raw_text": { "type": "string" },
				"confidence": { "type": "number" },
				"hierarchy": {
					"type": "array",
					"items": {
						"type": "object",
						"properties": {
							"id": { "type": "string" },
							"label": { "type": "string" }
						}
					}
				}
			}
		},
		"experience_item": {
			"type": "object",
			"properties": {
				"title": { "type": ["string", "null"] },
				"company": { "type": ["string", "null"] },
				"start_date": { "type": ["string", "null"] },
				"end_date": { "type": ["string", "null"] },
				"is_current": { "type": "boolean" },
				"location": { "type": ["string", "null"] },
				"duration_months": { "type": ["integer", "null"] },
				"raw_title": { "type": ["string", "null"] },
				"normalized_occupation_candidates": {
					"type": "array",
					"items": { "$ref": "#/$defs/esco_candidate" }
				}
			}
		},
		"education_item": {
			"type": "object",
			"properties": {
				"institution": { "type": ["string", "null"] },
				"degree": { "type": ["string", "null"] },
				"field_of_study": { "type": ["string", "null"] },
				"start_date": { "type": ["string", "null"] },
				"end_date": { "type": ["string", "null"] },
				"graduation_year": { "type": ["integer", "string", "null"] },
				"location": { "type": ["string", "null"] }
			}
		}
	}
}
```

## ESCO参照DB方針（確定）
- ESCOはまず生データ構造のまま参照DBとして利用する（raw層）。
- 1st〜5thデータを正規化する際、occupation/skillはESCOへ寄せて正規化する。
- 生データ層では物理FKは必須にせず、URI/codeを論理キーとしてJOINする。
	- occupation_uri -> occupations.concept_uri
	- skill_uri -> skills.concept_uri
	- occupations.isco_group -> isco_groups.code
- 整合性はETL検証で担保する（unresolved join, duplicate, invalid keyを記録）。
- 正規化後の格納DBは別スキーマとして設計・保存する。
- 初期段階では生データ構造を崩さず進め、性能課題が出たら検索用ビュー/派生テーブルを追加する。