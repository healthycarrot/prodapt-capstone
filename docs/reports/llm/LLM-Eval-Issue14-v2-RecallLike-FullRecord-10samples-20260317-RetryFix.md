# LLM Recall-like Evaluation (Full normalized_candidates Record, RetryFix)

- Generated at (UTC): 2026-03-16T16:15:20.817853
- Model: gpt-4.1-mini
- Sample size: 10
- Recall-like Hit@3: 1.0
- Recall-like Hit@10: 1.0
- Recall-like Hit@20: 1.0
- Retry policy: max_3_json_retries

## Items
- ID=22323967 cat=HR status=success h3=True h10=True h20=True reason=トップ1の職業候補は「human resources officer」であり、候補者の職務経歴（HR Specialist, US HR Operationsなど）とスキル（human resources department processes、manage human resources、hire human resourcesなど）が一致しているため、hit_at_3はtrue。トップ10およびトップ20にも関連職業（human resources assistant、recruitment consultant、labour relations officer、talent acquisition managerなど）が含まれており、全ての範囲でヒットしている。
- ID=37058472 cat=DESIGNER status=success h3=True h10=True h20=True reason=トップ1の職業候補は「project manager」であり、記録の職歴に「Project Manager」が含まれているためhit_at_3はtrue。さらに、関連する職業候補として「furniture designer」「interior designer」などのデザイナー関連職も上位20位以内に存在し、職務内容やスキルもデザイン関連で一致しているため、hit_at_10およびhit_at_20もtrueと判断した。
- ID=33241454 cat=INFORMATION-TECHNOLOGY status=success h3=True h10=True h20=True reason=トップ1の職業候補は「IT auditor」であり、候補者の職務経験やスキル（情報技術監督、技術者経験、Cisco、トラブルシュートなど）と関連性が高い。トップ3以内に関連職業（ICT consultant、Information Technology Technician）が含まれており、トップ10およびトップ20にも関連職業が存在するため、hit_at_3、hit_at_10、hit_at_20すべてtrueと判断した。
- ID=37292350 cat=AGRICULTURE status=success h3=True h10=True h20=True reason=トップ1の職業候補は「agriculture, forestry and fishery vocational teacher」であり、記録の職歴に複数の「Agriculture Teacher」としての経験が詳細に記載されているため、トップ1は正確かつ関連性が高い。トップ3以内に関連職業が存在し、トップ10およびトップ20にも含まれているため、hit_at_3、hit_at_10、hit_at_20すべてtrueと判断。
- ID=77576845 cat=BUSINESS-DEVELOPMENT status=success h3=True h10=True h20=True reason=トップ1の職業候補は「commercial director」であり、元の職務タイトル「DIRECTOR OF BUSINESS DEVELOPMENT」と高い関連性があるためhit_at_3はtrue。トップ10およびトップ20にも関連職業が含まれているため、それらもtrueと判断。
- ID=17926546 cat=ENGINEERING status=success h3=True h10=True h20=True reason=トップ1の職業候補は「electrical mechanic」であり、候補者の職歴に「Electrical Technician and Mechanist」が含まれているため、トップ3以内に正しい関連職業が存在する。したがって、hit_at_3、hit_at_10、hit_at_20はすべてtrueと判断される。
- ID=43752620 cat=ENGINEERING status=success h3=True h10=True h20=True reason=トップ1の職業候補は「industrial machinery mechanic」であり、関連性が高い。職歴やスキル情報からエンジニアリング分野での経験が豊富であり、機械工学インターンやエンジニアリングインターンの経験が含まれているため、hit_at_3、hit_at_10、hit_at_20すべてでヒットと判断した。
- ID=98379112 cat=BUSINESS-DEVELOPMENT status=partial h3=True h10=True h20=True reason=トップ3の候補に関連する職業（bank manager, business analyst, business consultant, economic development coordinator）が含まれており、レコードの内容と一致しているため、hit_at_3、hit_at_10、hit_at_20すべてtrueと判断した。
- ID=30757456 cat=FITNESS status=partial h3=True h10=True h20=True reason=候補の上位に関連する職業（スポーツ施設マネージャーなど）が含まれており、職務内容やスキルがフィットネス分野のディレクターやパフォーマンスコーチに一致しているため、hit_at_3、hit_at_10、hit_at_20すべてtrueと判断しました。
- ID=37201447 cat=AGRICULTURE status=partial h3=True h10=True h20=True reason=トップ1の職業候補は「zoo educator」となっているが、実際の職歴は主に「Agriculture Teacher」や「Adult Education Instructor」であり、ESCOの職業候補に「agriculture, forestry and fishery vocational teacher」（3位）や「politics lecturer」（2位）が含まれているため、関連性が高い。したがって、トップ3以内に関連職業が存在し、hit_at_3、hit_at_10、hit_at_20すべてtrueと判断した。
