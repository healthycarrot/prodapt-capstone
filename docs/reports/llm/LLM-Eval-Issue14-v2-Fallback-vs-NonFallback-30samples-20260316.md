# LLM Evaluation: Fallback vs NonFallback (Issue14 v2, 30 samples)

- Generated at (UTC): 2026-03-16T04:05:20.129749
- Model: gpt-4.1-mini
- Collection: normalized_candidates
- Sample: fallback 15 / nonfallback 15

## Summary
- Fallback avg overall: 70.07 (Top1 72.67, Top10 66.67)
- NonFallback avg overall: 86.33 (Top1 88.33, Top10 83.33)
- Delta (NonFallback - Fallback): overall 16.26, Top1 15.66, Top10 16.66
- Fallback verdicts: {'good': 6, 'mixed': 5, 'poor': 4}
- NonFallback verdicts: {'good': 12, 'mixed': 3}

## Items (first 10)
- cohort=fallback ID=22496394 cat=DESIGNER top1='drafter' overall=83 verdict=good reason=CADデザイナーに近い職種多数で実務候補含むためフィルター有用。
- cohort=fallback ID=28035460 cat=INFORMATION-TECHNOLOGY top1='cyber incident responder' overall=73 verdict=mixed reason=ITスペシャリストに近いが候補少なく実務幅は限定的。
- cohort=fallback ID=15941675 cat=ENGINEERING top1='manufacturing engineer' overall=68 verdict=mixed reason=エンジニア系だが職種多様で絞り込みにやや難あり。
- cohort=fallback ID=23139819 cat=ACCOUNTANT top1='accountant' overall=93 verdict=good reason=会計士がトップで類似職種もあり実務候補として十分。
- cohort=fallback ID=23944036 cat=HEALTHCARE top1='market research analyst' overall=55 verdict=poor reason=トップ職種が市場調査分析で医療分析職と乖離。候補少なく実務活用困難。
- cohort=fallback ID=92524964 cat=FINANCE top1='accountant' overall=88 verdict=good reason=財務管理職中心で類似職種もあり実務候補として有用。
- cohort=fallback ID=16244633 cat=ARTS top1='office manager' overall=35 verdict=poor reason=営業・事務混在で職種乖離大。実務候補として不適。
- cohort=fallback ID=15433732 cat=CONSULTANT top1='commercial director' overall=78 verdict=mixed reason=マーケ系中心で類似職種多いが一部乖離あり。フィルター活用は限定的。
- cohort=fallback ID=17412079 cat=HR top1='talent acquisition manager' overall=83 verdict=good reason=HR関連職種が上位に揃い実務候補として有用。
- cohort=fallback ID=37735467 cat=SALES top1='sales account manager' overall=45 verdict=poor reason=営業職だが候補が少なく職種乖離もあり実務活用困難。
