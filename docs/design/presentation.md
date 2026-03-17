# Gamma AI Prompt

以下の内容をもとに、**採用候補者マッチングAIシステム**に関するプレゼン資料を作成してください。  
**対象 audience は技術者とビジネス関係者の両方**です。  
全体として、**「課題設定 → 設計思想 → システム構成 → 技術的工夫 → 価値」** が自然につながる構成にしてください。  
デザインは**モダンでプロフェッショナル、AI/データプロダクトらしい雰囲気**にしてください。  
文章は長くしすぎず、**1スライドあたり3〜5点程度の要点**で簡潔にまとめてください。  
適切な箇所では、**アーキテクチャ図、検索フロー図、スコアリング構成図、ROI/KPI整理図**をいれるのでそこは空欄にしておいてください。

---

## Slide 1. Title
**AI-Powered Candidate Matching System**  
Improving speed, consistency, and quality in resume screening

---

## Slide 2. Problem Solving
この課題の中心問題は、**大量の応募者の中から求人要件に本当に合う候補者を、効率的かつ一貫して見つけにくいこと**です。

以下の観点で整理してください。

- **Speed**
  - Resume screening is still heavily manual
  - Reviewing large volumes of resumes takes significant time

- **Consistency**
  - Evaluation criteria vary across recruiters and hiring managers
  - Human judgment tends to be inconsistent

- **Quality**
  - Keyword matching is weak against wording variation
  - Related skills and transferable capabilities are difficult to capture
  - Candidate data exists in multiple formats and is hard to interpret consistently

最後に、これは単なる検索精度の問題ではなく、  
**hiring decision quality, speed, and consistency を改善する問題**であることを強調してください。

---

## Slide 3. Design Thinking
このシステムの目的は、単に候補者をスコアリングすることではありません。  
重要なのは、**採用担当者が「なぜこの候補者が合うのか」を理解しやすい形で支援すること**です。

以下の設計思想を整理してください。

- Natural language hiring requirements can be interpreted semantically
- Candidates should be matched not only by exact overlap, but also by related and transferable skills
- The system should provide explanations, not just scores
- Profiles in different formats should be interpreted in a unified way

このスライドでは、  
**“decision support for recruiters”** という観点を強調してください。

---

## Slide 4. Key Features
以下の機能をわかりやすく整理してください。

- Natural language search for candidate retrieval
- Hard filters for structured requirements
- Multi-dimensional scoring based on:
  - skills
  - experience
  - career progression
  - soft skills
- Natural language explanations for each score
- Access to both summarized candidate profiles and original resumes

---

## Slide 5. Demo
A simple product demo slide.  
以下を短く表現してください。

- Enter hiring requirements in natural language
- Apply optional hard filters
- Retrieve and rank matched candidates
- Review score explanations and source resume evidence

見た目重視で、UIモック風にしてください。

---

## Slide 6. Enterprise Architecture
**Architecture & Design | Enterprise Architecture**

以下の構成要素を含むアーキテクチャ図を作成してください。

- Frontend
- Backend API
- MongoDB
- Milvus
- Data Pipeline
- Evaluation Module

また、以下の意図を説明してください。

- The architecture is designed with microservice thinking in mind
- Currently the frontend mainly calls the `/search` endpoint
- The `/retrieve` capability is intentionally separable
- This reduces switching cost if the agent layer or vector database is replaced in the future

このスライドでは、**modularity and future extensibility** を強調してください。

---

## Slide 7. Trade-off Decisions
**Architecture & Design | Trade-off Decisions**

このユースケースの技術的なネックは、**長文ドキュメントをどう扱うか**です。  
その観点で、Milvus を採用した理由を整理してください。

含めたい論点:
- Handling long-form resume data efficiently
- Need for scalable vector retrieval
- High availability and reliability as a distributed vector database
- Suitability for semantic search at scale

必要であれば、  
**why vector DB is necessary for this use case** も補足してください。

---

## Slide 8. System Thinking: Data Challenges
**Architecture & Design | System Thinking**

このユースケースの特徴として、以下を整理してください。

- Multiple data sources with different formats
- Most of the data is unstructured

その結果として予想される課題:

- Simple token-length chunking leads to poor retrieval quality
- Passing whole documents into LLMs increases context size
- Larger context leads to higher latency and cost

最後に、  
**therefore the core design focus is the preprocessing pipeline**  
という流れにつなげてください。

---

## Slide 9. Pipeline Design: Structuring
データ前処理パイプラインのうち、まず **Structuring** を説明してください。

含めたい内容:

- HTML resumes are parsed using tags
- Non-HTML data may require NLP-based title extraction or LLM-based parsing
- Key fields such as Skill and Occupation are extracted as structured elements for downstream RAG

このスライドでは、  
**raw resume data → structured candidate profile** の流れを図で見せてください。

---

## Slide 10. Pipeline Design: Normalization
次に **Normalization** を説明してください。

背景:
- Multiple datasets are provided
- They contain similar information, but differ in wording and representation
- Skill names and occupation titles vary significantly across datasets

方針:
- Normalize all candidate information into a common standard
- Use the **ESCO dataset** as the shared taxonomy for skills, competencies, qualifications, and occupations

この判断理由も含めてください。

- ESCO reduces ambiguity during retrieval
- ESCO is credible and used in research
- A common external standard is more extensible than dataset-to-dataset rule mapping

補足として、この論文に触れてください。  
It proposes matching resumes to ESCO occupations:  
https://arxiv.org/html/2503.02056v1

---

## Slide 11. Normalization Methods
正規化のために使っている手法を整理してください。

- Keyword matching
- Cosine similarity matching
  - Embed ESCO skill and occupation descriptions
  - Compare them with extracted resume skills and career history
- LLM-based matching

また、これによる効果をまとめてください。

- Lower ambiguity in retrieval
- Better long-term extensibility
- Token savings through preprocessing
- Faster runtime processing
- Better RAG quality

---

## Slide 12. Retrieval Design
**Architecture & Design | AI Workflow Design**

検索・絞り込みの流れを整理してください。

- Two hard-filter specification methods:
  - explicit user-selected filters
  - extracting constraints from natural language and normalizing them into ESCO
- Filtering targets:
  - skill, occupation, industry: filterable in both Vector DB and MongoDB
  - education, experience, location: filterable in Vector DB

加えて、以下も含めてください。

- Hybrid search: vector search + keyword search
- Fusion score calculation
- Cross-encoder reranking

このスライドは、**retrieval pipeline diagram** を含めてください。

---

## Slide 13. Agent-based Scoring
以下の Agent を実装していることを説明してください。

- Skill Match Agent
- Experience Match Agent
- Education Match Agent
- Career Progression Match Agent
- Soft Skill Match Agent

構成:
- Each agent runs independently and in parallel
- Each agent produces its own score
- An Orchestrator Agent aggregates and summarizes the results
- The Orchestrator can skip unnecessary agents depending on the query
  - for example, it may skip Education Match Agent when education is irrelevant

このスライドでは、**A2A-style orchestration** を図で見せてください。

---

## Slide 14. ROI Framing
ビジネス価値を次の3つの観点で整理してください。

- **Operational Efficiency**
  - Reduce resume screening time
  - Lower reviewer workload

- **Hiring Quality**
  - Discover strong candidates beyond keyword overlap
  - Surface candidates with transferable skills

- **Consistency**
  - Reduce evaluator variance
  - Standardize reasoning behind hiring recommendations

---

## Slide 15. KPI
測定しやすい KPI を整理してください。

- Average review time per application
- Interview pass-through rate
- Offer acceptance rate
- Hiring lead time
- Interview conversion rate of top-ranked candidates
- Rediscovery rate of overlooked candidates
- Inter-rater agreement among recruiters

最後に、  
**the system should be evaluated not only by retrieval relevance, but also by business impact**  
というメッセージで締めてください。

---

## Additional Instructions for Gamma
- Use a clean and modern enterprise presentation style
- Keep text concise and visual
- Use icons, process diagrams, and architecture diagrams where helpful
- Emphasize explainability, modularity, and business value
- Avoid overly academic wording
- Make the slides suitable for a technical demo / solution presentation