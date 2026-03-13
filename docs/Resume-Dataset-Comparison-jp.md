# Resume Dataset Comparison

## 概要
本ドキュメントは、[data](data) 配下の 1st〜5th データソースを比較し、各データの構造・用途・実装上の向き不向きを整理したものです。

分析用スクリプト:
- [script/for_1st/analyze_1st_resume_structure.py](script/for_1st/analyze_1st_resume_structure.py)
- [script/for_2nd/analyze_2nd_resume_sections.py](script/for_2nd/analyze_2nd_resume_sections.py)
- [script/for_3rd/analyze_3rd_resume_components.py](script/for_3rd/analyze_3rd_resume_components.py)
- [script/for_4th/analyze_4th_resume_structure.py](script/for_4th/analyze_4th_resume_structure.py)
- [script/for_5th/analyze_5th_resume_sections.py](script/for_5th/analyze_5th_resume_sections.py)

対応するレポート:
- [script/for_1st/analyze_1st_resume_structure_report.json](script/for_1st/analyze_1st_resume_structure_report.json)
- [script/for_2nd/analyze_2nd_resume_sections_report.json](script/for_2nd/analyze_2nd_resume_sections_report.json)
- [script/for_3rd/analyze_3rd_resume_components_report.json](script/for_3rd/analyze_3rd_resume_components_report.json)
- [script/for_4th/analyze_4th_resume_structure_report.json](script/for_4th/analyze_4th_resume_structure_report.json)
- [script/for_5th/analyze_5th_resume_sections_report.json](script/for_5th/analyze_5th_resume_sections_report.json)

## 比較表
| データ | 主ファイル | データ形式 | 件数 | summary | experience | skill | education | 特徴 | 向いている用途 |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| 1st | data/1st_data/Resume/Resume.csv | 半構造テキストCSV | 2484 | 見出しベースで高頻度 | 高頻度 | 高頻度 | 高頻度 | 全体として構造シグナルが強い | Resume parsing、RAG、検索 |
| 2nd | data/2nd_data/UpdatedResumeDataSet.csv | 半構造テキストCSV | 962 | 153 | 439 | 962 | 812 | skills が非常に強く、summary は弱め | Resume parsing、スキル抽出、補完型解析 |
| 3rd | data/3rd_data/*.csv | リレーショナル構造化CSV群 | 54933 people | 0 | 54933 | 54933 | 48075 | 既に person 単位で構造化済み | メタデータ検索、統合プロフィール生成 |
| 4th | data/4th_data/Resume.csv | 半構造テキストCSV + HTML | 2484 | 見出しベースで高頻度 | 高頻度 | 高頻度 | 高頻度 | 1st と同等 + HTML 付き | Resume parsing、HTML活用、RAG |
| 5th | data/5th_data/train_data.txt | 履歴書テキスト + エンティティ注釈 | 200 | 36 | 200 | 181 | 194 | NER用注釈がある | Resume parsing の学習・評価 |

## データソース別の説明

### 1st_data
対象: [data/1st_data/Resume/Resume.csv](data/1st_data/Resume/Resume.csv)

内容:
- `ID`
- `Resume_str`
- `Resume_html` はなし
- `Category`

分析結果の要点:
- 全 2484 件
- 3つ以上の見出しシグナルを持つ履歴書が 2481 件
- 日付レンジを持つ履歴書が 2422 件
- 平均構造スコアは 8.727

解釈:
- `Resume_str` は完全な自由文ではなく、見出し・日付・箇条書きがかなり残っている
- CSVベースの Resume parsing の一次ソースとしてかなり扱いやすい

おすすめ用途:
- セクション分割
- experience 抽出
- skill_tags 抽出
- RAG用チャンク生成

### 2nd_data
対象: [data/2nd_data/UpdatedResumeDataSet.csv](data/2nd_data/UpdatedResumeDataSet.csv)

内容:
- `Category`
- `Resume`

分析結果の要点:
- 全 962 件
- `summary` を持つと判定された履歴書は 153 件
- `experience` は 439 件
- `skill` は 962 件
- `education` は 812 件
- 4要素すべてを持つ履歴書は 86 件

解釈:
- skills と education は強い
- summary は弱い
- 1st より構造は不均一だが、スキル抽出には向いている

おすすめ用途:
- skill セクション抽出
- education 抽出
- 難例への LLM補完
- セクション存在判定の評価用

### 3rd_data
対象:
- [data/3rd_data/01_people.csv](data/3rd_data/01_people.csv)
- [data/3rd_data/02_abilities.csv](data/3rd_data/02_abilities.csv)
- [data/3rd_data/03_education.csv](data/3rd_data/03_education.csv)
- [data/3rd_data/04_experience.csv](data/3rd_data/04_experience.csv)
- [data/3rd_data/05_person_skills.csv](data/3rd_data/05_person_skills.csv)
- [data/3rd_data/06_skills.csv](data/3rd_data/06_skills.csv)

内容:
- person 単位に experience / education / skills が分割された構造化データ
- 履歴書本文そのものではなく、リレーショナルデータに近い

分析結果の要点:
- 全 54933 人
- `summary` 専用ソースは存在しない
- `experience` は 54933 人
- `skill` は 54933 人
- `education` は 48075 人
- experience の中央値は 4 件
- skill-like 情報の中央値は 47 件

解釈:
- 既に構造化済みなので、Resume parsing より統合・検索設計向き
- `summary` は別途生成する必要がある

おすすめ用途:
- metadata ベース検索
- candidate profile JSON の生成
- experience/skills の定量評価
- フィルタリング重視の検索基盤

### 4th_data
対象:
- [data/4th_data/Resume.csv](data/4th_data/Resume.csv)
- [data/4th_data/training_data.csv](data/4th_data/training_data.csv)

#### Resume.csv
内容:
- `ID`
- `Resume_str`
- `Resume_html`
- `Category`

分析結果の要点:
- 全 2484 件
- 1st とほぼ同等の構造シグナル
- `Resume_html` が全件に存在
- median HTML length は 15025.5

解釈:
- 1st と同じ履歴書集合系だが、HTMLが付いている分だけ情報量が多い
- レイアウトやセクション境界を補強したい場合に有利

おすすめ用途:
- Resume parsing
- HTML活用による構造補強
- テキスト抽出結果の検証
- RAG前処理

#### training_data.csv
内容:
- `company_name`
- `job_description`
- `position_title`
- `description_length`
- `model_response`

解釈:
- 履歴書データではなく、求人記述を構造化要件に変換するための教師データ / 評価データ
- 候補者側ではなく求人側のデータ

おすすめ用途:
- Job Parsing Agent
- required/preferred 抽出
- 求人要件の構造化

### 5th_data
対象:
- [data/5th_data/train_data.txt](data/5th_data/train_data.txt)
- 補助サンプル: [data/5th_data/Aline CV .txt](data/5th_data/Aline%20CV%20.txt)

内容:
- `train_data.txt` は `(resume_text, annotations)` のタプル集合
- `annotations` にエンティティラベルが付いている

分析結果の要点:
- 全 200 件
- `summary` は 36 件
- `experience` は 200 件
- `skill` は 181 件
- `education` は 194 件
- 4要素すべてを持つ履歴書は 30 件
- 上位エンティティは `Name`, `Designation`, `Location`, `Degree`, `Email Address`, `College Name`, `Companies worked at`, `Skills`

解釈:
- 半構造履歴書テキストに NER 注釈が付いたデータ
- Resume parsing の学習・評価に使いやすい

おすすめ用途:
- エンティティ抽出モデルの学習/評価
- parser の精度検証
- スキル・学歴・会社名抽出の評価セット

## 総合評価
### 履歴書本文の一次ソースとして有力
- 1st_data
- 4th_data

理由:
- 履歴書本文がまとまっている
- 見出し・日付・スキル記述が十分残っている
- 4th は HTML も併用できる

### 部分構造抽出の補助として有力
- 2nd_data
- 5th_data

理由:
- 2nd は skills / education が強い
- 5th は注釈付きなので parser 評価に使える

### メタデータ検索基盤として有力
- 3rd_data

理由:
- 既に person 単位の構造化データ
- experience / skills / education のフィルタリングに強い

## 実装に向けた推奨使い分け
- 候補者検索・RAG本体:
  - 1st_data または 4th_data
- HTMLや原文構造を活かしたい場合:
  - 4th_data
- Resume parser / NER の評価:
  - 5th_data
- 構造化プロフィールの検索・集計:
  - 3rd_data
- 補助的な section 抽出・多様性確認:
  - 2nd_data

## 結論
最も実装しやすい組み合わせは次の通りです。

- 主データ: 1st_data または 4th_data
- 評価/補助データ: 5th_data
- 構造化メタデータ補完: 3rd_data
- 補助比較用: 2nd_data

特に、初期実装では 4th_data を主ソースにし、必要に応じて 1st_data と互換扱いする方針が最も扱いやすいです。
