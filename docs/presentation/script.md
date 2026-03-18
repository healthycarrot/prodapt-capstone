# Presentation Script

15分発表を前提に、`5分デモ + 約8分15秒の本編 + 約1分45秒のバッファ` で話せる分量にしています。  
PDFは16ページあるため、`Page 16` は時間が厳しい場合の補足スライドとして扱えるようにしています。  
なお、原稿は**現在のPDFのページ順**に合わせています。

## Overall Timing

- Page 1-4: 約2分20秒
- Page 5 Demo: 約5分
- Page 6-14: 約5分10秒
- Page 15: 約10秒
- Page 16: 約35秒
- Buffer: 約1分45秒

---

## Page 1. Title

**Target time:** 0:20

**English**

Good afternoon, everyone. Today I would like to introduce our AI-Powered Candidate Matching System. The goal of this system is to improve the speed, consistency, and quality of resume screening, and to help recruiters find the right talent more effectively.

**日本語訳**

皆さま、こんにちは。本日は、私たちの AI-Powered Candidate Matching System をご紹介します。このシステムの目的は、履歴書スクリーニングの速度、一貫性、品質を改善し、採用担当者がより効果的に適切な人材を見つけられるようにすることです。

---

## Page 2. The Core Problem

**Target time:** 0:40

**English**

The core problem is not simply that recruiters have too many resumes to read. The deeper issue is that hiring teams need to make decisions quickly, but the process is still manual, inconsistent, and often dependent on simple keyword matching. So this is really a decision-quality problem: how do we improve hiring speed, consistency, and quality at the same time?

**日本語訳**

中心的な課題は、単に採用担当者が読むべき履歴書の数が多すぎることではありません。より本質的な問題は、採用チームが素早く判断しなければならない一方で、そのプロセスが依然として手作業中心で、一貫性に欠け、単純なキーワードマッチに依存しがちなことです。つまりこれは、採用のスピード、一貫性、品質を同時にどう改善するかという意思決定品質の問題です。

---

## Page 3. Design Thinking

**Target time:** 0:40

**English**

Our goal is not to automate hiring decisions in a simplistic way. The purpose is to build a system that supports recruiter judgement. By making it visible why a candidate is being recommended, we can reduce the decision-making cost for recruiters and standardize evaluations that would otherwise depend too much on each individual reviewer. To achieve that, the system needs semantic understanding of hiring requirements, recognition of related and transferable skills, explanations rather than just scores, and a unified way to interpret resumes in different formats.

**日本語訳**

私たちの目標は、採用判断を単純に自動化することではありません。採用担当者の判断を支援するシステムを作ることが目的です。なぜその候補者が選ばれているのかを可視化することで、採用担当者意思決定コストを下げることができます。また担当者ごとに属人化していた判断を標準化することもできます。
そのためには、採用要件の意味理解、関連スキルや転用可能スキルの認識、スコアだけでなく説明の提示、そして形式の異なる履歴書を統一的に解釈する仕組みが必要です。

---

## Page 4. Key Features

**Target time:** 0:40

**English**

From the user perspective, the system provides four main capabilities. First, recruiters can search candidates in natural language. Second, they can apply hard filters for structured requirements. Third, candidates are evaluated with multi-dimensional scoring across skills, experience, career progression, and soft skills. Finally, users can inspect both the explanations and the original resume evidence behind the recommendation.

**日本語訳**

ユーザー視点では、このシステムには4つの主要な機能があります。1つ目は、自然言語で候補者検索ができることです。2つ目は、構造化された条件に対してハードフィルターを適用できることです。3つ目は、スキル、経験、キャリア成長、ソフトスキルといった複数の観点で候補者を評価できることです。最後に、推薦理由の説明と元の履歴書根拠の両方を確認できます。

---

## Page 5. Product Demo

**Target time:** 5:00
**English**

**日本語訳**
これからデモを始めます
### Step1
まずは、自然言語で検索クエリを入力します。例えば、「We are looking for a senior data engineering professional who can serve as a technical lead. Strong machine learning and data analysis skills are essential, and expertise in Python would be highly desirable.」といった要件をそのまま書いてみます。

この実行結果は1分ほどかかるので、先にほかの実行結果を紹介します。
クエリはこれです。
We are looking for a senior frontend engineering professional who can serve as a technical lead. 

フィルタをかけることができ、２文字以上入力するとAPIで候補を取得してきます。これはメタデータフィルタリングのための機能なので、VectorDBのメタデータと整合をとるためにこのような実装にしています。

結果を見てみるとこのようになっています。まずカードには推薦理由のサマリと何のスキルがマッチしたのか、マッチしていないが転用可能なスキルは何か、どの経験がマッチしたのかを表示しています。また逆にマッチしていないスキルや経験を表示してユーザーの判断を明確にします。

さらにランク付けの根拠となるスコアも表示しています


---

## Page 6. Enterprise Architecture

**Target time:** 0:35

**English**

From an architecture perspective, we designed this system with microservice thinking in mind. The frontend mainly calls the `/search` flow, while the backend also exposes separable capabilities such as retrieval, candidate detail, resume access, and suggestion APIs. MongoDB stores raw and normalized candidate data, Milvus handles semantic retrieval, the data pipeline prepares the search-ready representation, and the evaluation module measures quality. The key design message here is modularity and future extensibility.

**日本語訳**

アーキテクチャの観点では、このシステムをマイクロサービス思考で設計しました。フロントエンドは主に `/search` フローを呼び出しますが、バックエンドには retrieval、candidate detail、resume access、suggestion API など、切り離し可能な機能も用意しています。MongoDB は生データと正規化済み候補者データを保持し、Milvus はセマンティック検索を担い、データパイプラインが検索可能な形に前処理し、評価モジュールが品質を測定します。ここでの重要なメッセージは、モジュール性と将来拡張性です。

---

## Page 7. System Thinking: Data Challenges

**Target time:** 0:35

**English**

This use case is challenging because the data comes from multiple sources and most of it is unstructured. If we simply chunk long resumes by token length, retrieval quality drops. If we send full documents to an LLM at runtime, context size, latency, and cost all increase. That is why we decided that the real design focus should be the preprocessing pipeline.

**日本語訳**

このユースケースが難しいのは、データが複数ソースから来ており、その大半が非構造データだからです。長い履歴書を単純にトークン長で分割すると検索品質が下がりますし、実行時に文書全体を LLM に渡すと、コンテキストサイズ、レイテンシ、コストがすべて増加します。だからこそ、私たちは設計の中心を前処理パイプラインに置くことにしました。

---

## Page 8. Pipeline Stage 1: Structuring

**Target time:** 0:35

**English**

The first pipeline stage is structuring. For HTML resumes, we parse sections directly using tags. For non-HTML formats, we can rely on NLP-based title extraction or LLM-assisted parsing. We also extract key fields such as skill and occupation into structured elements, so downstream retrieval and filtering can work on cleaner signals instead of raw text alone.

**日本語訳**

パイプラインの第1段階は structuring です。HTML の履歴書については、タグを使ってセクションを直接パースします。HTML 以外の形式では、NLP による見出し抽出や LLM を使ったパースを利用できます。さらに、skill や occupation のような重要フィールドを構造化要素として抽出することで、後続の検索やフィルタリングが生テキストだけでなく、よりクリーンなシグナルを使って動けるようにしています。

---

## Page 9. Pipeline Stage 2: Normalisation

**Target time:** 0:35

**English**

The second stage is normalization. We had multiple datasets that contained similar information, but their wording and representation were different. So instead of building dataset-to-dataset mapping rules, we normalized candidate data to the ESCO taxonomy for skills, competencies, qualifications, and occupations. This reduces ambiguity during retrieval, gives us a credible external standard, and makes the system more extensible. A recent paper on matching resumes to ESCO occupations also supports this direction.

**日本語訳**

第2段階は normalization です。今回扱った複数のデータセットは、含んでいる情報は似ていても、表現や記述方法が異なっていました。そこで、データセット同士を個別に対応付けるルールを作るのではなく、候補者データ全体を ESCO のスキル、能力、資格、職業のタクソノミーに正規化しました。これにより検索時の曖昧さが減り、信頼できる外部標準を使え、将来的な拡張性も高まります。履歴書を ESCO 職種にマッチングする最近の論文も、この方向性を裏付けています。

---

## Page 10. Retrieval Design

**Target time:** 0:40

**English**

After preprocessing, the retrieval workflow has four stages. First, we define hard filters either from explicit user selections or by extracting constraints from natural language and normalizing them into ESCO. Second, we run hybrid search, meaning vector search and keyword search in parallel. Third, we calculate a fusion score to merge those search paths. Finally, we use a cross-encoder to rerank the top candidates for higher relevance.

**日本語訳**

前処理の後、retrieval ワークフローは4段階で構成されています。まず、ユーザーが明示的に選んだ条件、あるいは自然言語から抽出して ESCO に正規化した条件をもとにハードフィルターを定義します。次に、ベクトル検索とキーワード検索を並列で実行するハイブリッド検索を行います。3つ目に、それらの検索経路を統合する fusion score を計算します。最後に、cross-encoder を使って上位候補を再ランキングし、関連性をさらに高めます。

---

## Page 11. Agent-Based Scoring

**Target time:** 0:45

**English**

Retrieval gives us a strong shortlist, but the final recommendation quality comes from agent-based scoring. We implemented five specialist agents: skill match, experience match, education match, career progression, and soft skill. These agents run independently and in parallel, and an orchestrator aggregates their outputs into a final score and explanation. The orchestrator can also skip unnecessary agents, for example when education is not relevant to the query.

**日本語訳**

retrieval は強い候補者のショートリストを作ってくれますが、最終的な推薦品質を高めるのは agent-based scoring です。私たちは、skill match、experience match、education match、career progression、soft skill の5つの専門エージェントを実装しました。これらのエージェントは独立して並列実行され、オーケストレーターがその出力を集約して最終スコアと説明を作ります。また、education がクエリに関係ない場合のように、不要なエージェントをスキップすることもできます。

---

## Page 12. Business Value & ROI

**Target time:** 0:30

**English**

From a business perspective, the value appears in three areas. First, operational efficiency: recruiters spend less time on manual screening. Second, hiring quality: the system can surface strong candidates even when they do not match the exact keywords. Third, consistency: the reasoning behind recommendations becomes more standardized and less dependent on individual reviewer habits.

**日本語訳**

ビジネスの観点では、この価値は3つの領域に表れます。1つ目は業務効率で、採用担当者が手作業のスクリーニングに費やす時間を減らせます。2つ目は採用品質で、完全一致のキーワードがなくても有力候補を見つけられます。3つ目は一貫性で、推薦理由が標準化され、個々の担当者の癖に左右されにくくなります。

---

## Page 13. Measuring Success: KPIs

**Target time:** 0:35

**English**

To measure success, we should not stop at retrieval relevance alone. We also need business KPIs such as average review time, hiring lead time, interview pass-through rate, top-rank conversion rate, rediscovery of overlooked candidates, and agreement among recruiters. In other words, this system should be evaluated not only by search quality, but also by business impact.

**日本語訳**

成功を測るためには、単に retrieval relevance だけを見ていてはいけません。平均レビュー時間、採用までのリードタイム、面接通過率、上位候補の面接化率、見落とし候補の再発見率、採用担当者間の評価一致率といったビジネス KPI も必要です。つまり、このシステムは検索品質だけでなく、ビジネスインパクトでも評価されるべきです。

---

## Page 14. Future Extensibility

**Target time:** 0:20

**English**

Looking ahead, we see four extension areas: stronger CI/CD, larger batch evaluation, tuning agent scoring weights based on evaluation results, and validating the system across multiple data sources. The architecture was designed so that these improvements can be added incrementally rather than requiring a full redesign.

**日本語訳**

今後の拡張としては、CI/CD の強化、より大規模なバッチ評価、評価結果に基づくエージェント重みの調整、そして複数データソースでの検証の4つを想定しています。このアーキテクチャは、こうした改善を全面的な作り直しではなく、段階的に追加できるように設計しています。

---

## Page 15. GitHub URL

**Target time:** 0:10

**English**

This page simply points to the repository. If you would like to review the implementation after the session, the full code and related documents are available here.

**日本語訳**

このページはリポジトリへの案内です。発表後に実装を確認したい場合は、コードと関連ドキュメントをこちらから参照できます。

---

## Page 16. Trade-off Decisions

**Target time:** 0:35

**Note:** 時間が足りない場合は補足スライドとして扱えます。

**English**

As a final technical note, we separated responsibilities between MongoDB and Milvus. MongoDB serves as the system of record for raw resumes, normalized profiles, explanation evidence, and candidate detail APIs. Milvus serves as the retrieval engine for scalable semantic search. We chose this split because a general-purpose database alone is weak against wording variation and long-form resume semantics, while a vector database alone is not ideal as the operational store. Separating them gives us better extensibility now and lower switching cost in the future.

**日本語訳**

最後に技術的な補足として、私たちは MongoDB と Milvus の役割を分離しました。MongoDB は、生の履歴書、正規化済みプロフィール、説明根拠、候補者詳細 API のための system of record として使っています。Milvus は、スケーラブルなセマンティック検索のための retrieval engine として使っています。この構成を選んだ理由は、汎用データベースだけでは表現ゆれや長文履歴書の意味理解に弱く、逆にベクトル DB だけでは運用上のデータ保管基盤としては十分でないからです。両者を分離することで、現在の拡張性と将来の切り替えコストの低さを両立できます。
