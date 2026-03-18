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

Hello everyone, and thank you for joining. Today I'd like to introduce our AI-Powered Candidate Matching System. The goal is to help recruiters screen resumes faster, more consistently, and with better quality.

**日本語訳**

皆さま、こんにちは。本日は、私たちの AI-Powered Candidate Matching System をご紹介します。このシステムの目的は、履歴書スクリーニングの速度、一貫性、品質を改善し、採用担当者がより効果的に適切な人材を見つけられるようにすることです。

---

## Page 2. The Core Problem

**Target time:** 0:40

**English**

The issue is not just that recruiters have too many resumes to read. The bigger challenge is that hiring teams need to make decisions quickly, but screening is still manual, inconsistent, and often based on simple keyword matching. So this is not only a search problem. It's really a hiring decision problem.

**日本語訳**

中心的な課題は、単に採用担当者が読むべき履歴書の数が多すぎることではありません。より本質的な問題は、採用チームが素早く判断しなければならない一方で、そのプロセスが依然として手作業中心で、一貫性に欠け、単純なキーワードマッチに依存しがちなことです。つまりこれは、採用のスピード、一貫性、品質を同時にどう改善するかという意思決定品質の問題です。

---

## Page 3. Design Thinking

**Target time:** 0:40

**English**

Our goal is not to automate hiring in a simple way. What we want is to support recruiters. If we can clearly show why a candidate is recommended, recruiters can decide faster and in a more consistent way. To do that, the system needs to understand hiring needs, find related and transferable skills, explain the scores, and read resumes in different formats in one consistent way.

**日本語訳**

私たちの目標は、採用判断を単純に自動化することではありません。採用担当者の判断を支援するシステムを作ることが目的です。なぜその候補者が選ばれているのかを可視化することで、採用担当者意思決定コストを下げることができます。また担当者ごとに属人化していた判断を標準化することもできます。
そのためには、採用要件の意味理解、関連スキルや転用可能スキルの認識、スコアだけでなく説明の提示、そして形式の異なる履歴書を統一的に解釈する仕組みが必要です。

---

## Page 4. Key Features

**Target time:** 0:40

**English**

From the user side, the system has four main features. First, recruiters can search in natural language. Second, they can add hard filters for structured needs. Third, the system scores candidates by skills, experience, career growth, and soft skills. And finally, users can check both the explanation and the original resume evidence.

**日本語訳**

ユーザー視点では、このシステムには4つの主要な機能があります。1つ目は、自然言語で候補者検索ができることです。2つ目は、構造化された条件に対してハードフィルターを適用できることです。3つ目は、スキル、経験、キャリア成長、ソフトスキルといった複数の観点で候補者を評価できることです。最後に、推薦理由の説明と元の履歴書根拠の両方を確認できます。

---

## Page 5. Product Demo

**Target time:** 5:00

**English**

Now let me show you the demo.

First, I'll enter a search query in natural language. For example, I can type this requirement: "We are looking for a senior data engineering professional who can serve as a technical lead. Strong machine learning and data analysis skills are essential, and expertise in Python would be highly desirable."

This search takes about one minute, so while it is running, let me show you another result.
The query is:
We are looking for a senior frontend engineering professional who can serve as a technical lead.

We can also add filters. When we type two or more characters, the system calls the API and gets options. This is for metadata filtering, so we designed it this way to match the metadata in the vector database.

If we look at the result, this is what we get. Each card shows a summary of the recommendation, matched skills, transferable skills, and matched experience. It also shows missing skills or experience, so the user can make a clearer decision.

We also show the scores behind the ranking.
This main score is an integrated score. It combines the retrieval score and the agent score.
We can also check the breakdown and the reason for each score. For the agents, we can see the score for skill match, experience match, career progression, and soft skills.

If we click View Detail, we can also check the structured resume and the raw data. That helps recruiters make decisions with more confidence.

Now the first result is ready, so let's look at that one too. In the previous example, I used explicit filters, but in this one, the filtering comes from the natural-language query. If the backend finds clear skill requirements in the query, it extracts them and uses them for filtering. Here again, we can check the recommendation summary, matched skills and experience, and the score breakdown.

**日本語訳**
これからデモを始めます
まずは、自然言語で検索クエリを入力します。例えば、「We are looking for a senior data engineering professional who can serve as a technical lead. Strong machine learning and data analysis skills are essential, and expertise in Python would be highly desirable.」といった要件をそのまま書いてみます。

この実行結果は1分ほどかかるので、先にほかの実行結果を紹介します。
クエリはこれです。
We are looking for a senior frontend engineering professional who can serve as a technical lead. 

フィルタをかけることができ、２文字以上入力するとAPIで候補を取得してきます。これはメタデータフィルタリングのための機能なので、VectorDBのメタデータと整合をとるためにこのような実装にしています。

結果を見てみるとこのようになっています。まずカードには推薦理由のサマリと何のスキルがマッチしたのか、マッチしていないが転用可能なスキルは何か、どの経験がマッチしたのかを表示しています。また逆にマッチしていないスキルや経験を表示してユーザーの判断を明確にします。

さらにランク付けの根拠となるスコアも表示しています
メインのスコアがこれであり、このスコアはRetrievalの一致度のスコアとAgentによる採点のスコアを統合したものになります。
それぞれの内訳と判断理由も確認することができ、Agentについては
スキルマッチ、経験マッチ、キャリア成長、ソフトスキルの観点でどのように採点されたのかを確認できます。

さらにView detailを押すと、構造化した元の履歴書と生データも確認することができ、採用担当者も安心して判断できるようになっています。

結果がでているようですね。先ほどのクエリの結果も見てみましょう。先ほどは明示的にフィルタをかけていましたが、こちらは自然言語のほうでフィルタをかけています。バックエンドでクエリを分析して明確にスキルを指定している場合は、そのスキルを抽出してフィルタリングにかけるようにしています。こちらも同様に、推薦理由のサマリとマッチしたスキルや経験、スコアの内訳を確認することができます。
---

## Page 6. Enterprise Architecture

**Target time:** 0:35

**English**

We designed this system with a microservice mindset. The frontend mainly calls `/search`, but the backend also has separate functions such as retrieval, candidate detail, resume access, and suggestion APIs. We keep `/retrieve` separate on purpose. That way, if we change the agent layer or the vector database later, the switching cost stays low. MongoDB stores raw and normalized candidate data. Milvus is used for semantic search. The data pipeline prepares the data, and the evaluation module checks quality. The main point here is modularity and future extensibility. Also, the system can be divided into three main parts: Data Pipeline, Retrieval, and Agent-based Scoring. Let me walk through them next.

**日本語訳**

アーキテクチャの観点では、このシステムをマイクロサービス思考で設計しました。フロントエンドは主に `/search` フローを呼び出しますが、バックエンドには retrieval、candidate detail、resume access、suggestion API など、切り離し可能な機能も用意しています。
特に/retrieveの機能は意図的に切り離し可能にしており、将来エージェント層やベクトルデータベースを入れ替える場合のスイッチングコストを下げています。
MongoDB は生データと正規化済み候補者データを保持し、Milvus はセマンティック検索を担い、データパイプラインが検索可能な形に前処理し、評価モジュールが品質を測定します。ここでの重要なメッセージは、モジュール性と将来拡張性です。

またこのシステムのメインの機能は論理的に３つに分解でき、それはDataPipeline、Retrieval、Agent-based Scoring という３つの機能です。これからそれぞれの機能について説明します。

---

## Page 7. System Thinking: Data Challenges

**Target time:** 0:35

**English**

This use case is difficult because the data comes from many sources, and most of it is unstructured. If we split long resumes only by token length, retrieval quality gets worse. And if we send full documents to an LLM at runtime, context size, latency, and cost all go up. That's why we focused on the preprocessing pipeline.

**日本語訳**

このユースケースが難しいのは、データが複数ソースから来ており、その大半が非構造データだからです。長い履歴書を単純にトークン長で分割すると検索品質が下がりますし、実行時に文書全体を LLM に渡すと、コンテキストサイズ、レイテンシ、コストがすべて増加します。だからこそ、私たちは設計の中心を前処理パイプラインに置くことにしました。

---

## Page 8. Pipeline Stage 1: Structuring

**Target time:** 0:35

**English**

The first pipeline stage is structuring. For HTML resumes, we parse sections directly by using tags. For non-HTML formats, we can use NLP-based title extraction or LLM-based parsing. We also extract key fields such as skill and occupation into structured data, so later retrieval and filtering can use cleaner signals instead of only raw text.

**日本語訳**

パイプラインの第1段階は structuring です。HTML の履歴書については、タグを使ってセクションを直接パースします。HTML 以外の形式では、NLP による見出し抽出や LLM を使ったパースを利用できます。さらに、skill や occupation のような重要フィールドを構造化要素として抽出することで、後続の検索やフィルタリングが生テキストだけでなく、よりクリーンなシグナルを使って動けるようにしています。

---

## Page 9. Pipeline Stage 2: Normalisation

**Target time:** 0:35

**English**

The second stage is normalization. We had multiple datasets with similar information, but the wording and format were different. So instead of making many dataset-to-dataset mapping rules, we normalized candidate data to the ESCO taxonomy for skills, competencies, qualifications, and occupations. This reduces ambiguity in retrieval, gives us a reliable external standard, and makes the system easier to extend. A recent paper on matching resumes to ESCO occupations also supports this idea.

**日本語訳**

第2段階は normalization です。今回扱った複数のデータセットは、含んでいる情報は似ていても、表現や記述方法が異なっていました。そこで、データセット同士を個別に対応付けるルールを作るのではなく、候補者データ全体を ESCO のスキル、能力、資格、職業のタクソノミーに正規化しました。これにより検索時の曖昧さが減り、信頼できる外部標準を使え、将来的な拡張性も高まります。履歴書を ESCO 職種にマッチングする最近の論文も、この方向性を裏付けています。

---

## Page 10. Retrieval Design

**Target time:** 0:40

**English**

The retrieval workflow has four stages. First, we set hard filters from user-selected conditions or from conditions extracted from natural language and normalized into ESCO. At this step, we use few-shot prompting so the system can extract ESCO-like skills more easily. Second, we run hybrid search, which means vector search and keyword search in parallel. Third, we calculate a fusion score to combine those search results. And finally, we use a cross-encoder to rerank the top candidates and improve relevance.

**日本語訳**

retrieval ワークフローは4段階で構成されています。まず、ユーザーが明示的に選んだ条件、あるいは自然言語から抽出して ESCO に正規化した条件をもとにハードフィルターを定義します。このさいにFew-shot promptingでESCOっぽいSkillを抽出しやすいようにしています。次に、ベクトル検索とキーワード検索を並列で実行するハイブリッド検索を行います。3つ目に、それらの検索経路を統合する fusion score を計算します。最後に、cross-encoder を使って上位候補を再ランキングし、関連性をさらに高めます。

---

## Page 11. Agent-Based Scoring

**Target time:** 0:45

**English**

Retrieval gives us a good shortlist, but the final recommendation quality comes from agent-based scoring. We implemented five agents: skill match, experience match, education match, career progression, and soft skill. These agents run independently and in parallel. Then an orchestrator combines their outputs into one final score and explanation. The orchestrator can also skip agents that are not needed, for example when education is not important for the query.

**日本語訳**

retrieval は強い候補者のショートリストを作ってくれますが、最終的な推薦品質を高めるのは agent-based scoring です。私たちは、skill match、experience match、education match、career progression、soft skill の5つの専門エージェントを実装しました。これらのエージェントは独立して並列実行され、オーケストレーターがその出力を集約して最終スコアと説明を作ります。また、education がクエリに関係ない場合のように、不要なエージェントをスキップすることもできます。

---

## Page 12. Business Value & ROI

**Target time:** 0:30

**English**

From a business view, the value shows up in three areas. First, operational efficiency: recruiters spend less time on manual screening. Second, hiring quality: the system can find strong candidates even when the exact keywords do not match. Third, consistency: the reason behind each recommendation becomes more standard and less dependent on each reviewer.

**日本語訳**

ビジネスの観点では、この価値は3つの領域に表れます。1つ目は業務効率で、採用担当者が手作業のスクリーニングに費やす時間を減らせます。2つ目は採用品質で、完全一致のキーワードがなくても有力候補を見つけられます。3つ目は一貫性で、推薦理由が標準化され、個々の担当者の癖に左右されにくくなります。

---

## Page 13. Measuring Success: KPIs

**Target time:** 0:35

**English**

To measure success, we should not look only at retrieval relevance. We also need business KPIs such as average review time, hiring lead time, interview pass-through rate, top-rank conversion rate, rediscovery of overlooked candidates, and agreement among recruiters. In other words, this system should be evaluated not only by search quality, but also by business impact.

**日本語訳**

成功を測るためには、単に retrieval relevance だけを見ていてはいけません。平均レビュー時間、採用までのリードタイム、面接通過率、上位候補の面接化率、見落とし候補の再発見率、採用担当者間の評価一致率といったビジネス KPI も必要です。つまり、このシステムは検索品質だけでなく、ビジネスインパクトでも評価されるべきです。

---

## Page 14. Future Extensibility

**Target time:** 0:20

**English**

Looking ahead, we see four extension areas: stronger CI/CD, larger batch evaluation, tuning agent scoring weights based on evaluation results, and validation across multiple data sources. The architecture was designed so that we can add these improvements step by step without a full redesign.

**日本語訳**

今後の拡張としては、CI/CD の強化、より大規模なバッチ評価、評価結果に基づくエージェント重みの調整、そして複数データソースでの検証の4つを想定しています。このアーキテクチャは、こうした改善を全面的な作り直しではなく、段階的に追加できるように設計しています。

---

## Page 15. GitHub URL

**Target time:** 0:10

**English**

This page shows the repository. If you'd like to review the implementation after the session, the full code and related documents are available here.

**日本語訳**

このページはリポジトリへの案内です。発表後に実装を確認したい場合は、コードと関連ドキュメントをこちらから参照できます。

---

## Page 16. Trade-off Decisions

**Target time:** 0:35

**Note:** 時間が足りない場合は補足スライドとして扱えます。

**English**

As a final technical note, we separated the roles of MongoDB and Milvus. MongoDB is the system of record for raw resumes, normalized profiles, explanation evidence, and candidate detail APIs. Milvus is the retrieval engine for scalable semantic search. We chose this design because a general-purpose database alone is weak against wording differences and long resume meaning, while a vector database alone is not a good operational store. By separating them, we get better extensibility now and lower switching cost in the future.

**日本語訳**

最後に技術的な補足として、私たちは MongoDB と Milvus の役割を分離しました。MongoDB は、生の履歴書、正規化済みプロフィール、説明根拠、候補者詳細 API のための system of record として使っています。Milvus は、スケーラブルなセマンティック検索のための retrieval engine として使っています。この構成を選んだ理由は、汎用データベースだけでは表現ゆれや長文履歴書の意味理解に弱く、逆にベクトル DB だけでは運用上のデータ保管基盤としては十分でないからです。両者を分離することで、現在の拡張性と将来の切り替えコストの低さを両立できます。
