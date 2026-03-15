# Resume Dataset Comparison

## æ¦‚è¦
æœ¬ãƒ‰ã‚­ãƒ¥ãƒ¡ãƒ³ãƒˆã¯ã€[data](../../data) é…ä¸‹ã® 1stã€œ5th ãƒ‡ãƒ¼ã‚¿ã‚½ãƒ¼ã‚¹ã‚’æ¯”è¼ƒã—ã€å„ãƒ‡ãƒ¼ã‚¿ã®æ§‹é€ ãƒ»ç”¨é€”ãƒ»å®Ÿè£…ä¸Šã®å‘ãä¸å‘ãã‚’æ•´ç†ã—ãŸã‚‚ã®ã§ã™ã€‚

åˆ†æžç”¨ã‚¹ã‚¯ãƒªãƒ—ãƒˆ:
- [script/for_1st/analyze_1st_resume_structure.py](../../script/for_1st/analyze_1st_resume_structure.py)
- [script/for_2nd/analyze_2nd_resume_sections.py](../../script/for_2nd/analyze_2nd_resume_sections.py)
- [script/for_3rd/analyze_3rd_resume_components.py](../../script/for_3rd/analyze_3rd_resume_components.py)
- [script/for_4th/analyze_4th_resume_structure.py](../../script/for_4th/analyze_4th_resume_structure.py)
- [script/for_5th/analyze_5th_resume_sections.py](../../script/for_5th/analyze_5th_resume_sections.py)

å¯¾å¿œã™ã‚‹ãƒ¬ãƒãƒ¼ãƒˆ:
- [script/for_1st/analyze_1st_resume_structure_report.json](../../script/for_1st/analyze_1st_resume_structure_report.json)
- [script/for_2nd/analyze_2nd_resume_sections_report.json](../../script/for_2nd/analyze_2nd_resume_sections_report.json)
- [script/for_3rd/analyze_3rd_resume_components_report.json](../../script/for_3rd/analyze_3rd_resume_components_report.json)
- [script/for_4th/analyze_4th_resume_structure_report.json](../../script/for_4th/analyze_4th_resume_structure_report.json)
- [script/for_5th/analyze_5th_resume_sections_report.json](../../script/for_5th/analyze_5th_resume_sections_report.json)

## æ¯”è¼ƒè¡¨
| ãƒ‡ãƒ¼ã‚¿ | ä¸»ãƒ•ã‚¡ã‚¤ãƒ« | ãƒ‡ãƒ¼ã‚¿å½¢å¼ | ä»¶æ•° | summary | experience | skill | education | ç‰¹å¾´ | å‘ã„ã¦ã„ã‚‹ç”¨é€” |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| 1st | data/1st_data/Resume/Resume.csv | åŠæ§‹é€ ãƒ†ã‚­ã‚¹ãƒˆCSV | 2484 | è¦‹å‡ºã—ãƒ™ãƒ¼ã‚¹ã§é«˜é »åº¦ | é«˜é »åº¦ | é«˜é »åº¦ | é«˜é »åº¦ | å…¨ä½“ã¨ã—ã¦æ§‹é€ ã‚·ã‚°ãƒŠãƒ«ãŒå¼·ã„ | Resume parsingã€RAGã€æ¤œç´¢ |
| 2nd | data/2nd_data/UpdatedResumeDataSet.csv | åŠæ§‹é€ ãƒ†ã‚­ã‚¹ãƒˆCSV | 962 | 153 | 439 | 962 | 812 | skills ãŒéžå¸¸ã«å¼·ãã€summary ã¯å¼±ã‚ | Resume parsingã€ã‚¹ã‚­ãƒ«æŠ½å‡ºã€è£œå®Œåž‹è§£æž |
| 3rd | data/3rd_data/*.csv | ãƒªãƒ¬ãƒ¼ã‚·ãƒ§ãƒŠãƒ«æ§‹é€ åŒ–CSVç¾¤ | 54933 people | 0 | 54933 | 54933 | 48075 | æ—¢ã« person å˜ä½ã§æ§‹é€ åŒ–æ¸ˆã¿ | ãƒ¡ã‚¿ãƒ‡ãƒ¼ã‚¿æ¤œç´¢ã€çµ±åˆãƒ—ãƒ­ãƒ•ã‚£ãƒ¼ãƒ«ç”Ÿæˆ |
| 4th | data/4th_data/Resume.csv | åŠæ§‹é€ ãƒ†ã‚­ã‚¹ãƒˆCSV + HTML | 2484 | è¦‹å‡ºã—ãƒ™ãƒ¼ã‚¹ã§é«˜é »åº¦ | é«˜é »åº¦ | é«˜é »åº¦ | é«˜é »åº¦ | 1st ã¨åŒç­‰ + HTML ä»˜ã | Resume parsingã€HTMLæ´»ç”¨ã€RAG |
| 5th | data/5th_data/train_data.txt | å±¥æ­´æ›¸ãƒ†ã‚­ã‚¹ãƒˆ + ã‚¨ãƒ³ãƒ†ã‚£ãƒ†ã‚£æ³¨é‡ˆ | 200 | 36 | 200 | 181 | 194 | NERç”¨æ³¨é‡ˆãŒã‚ã‚‹ | Resume parsing ã®å­¦ç¿’ãƒ»è©•ä¾¡ |

## ãƒ‡ãƒ¼ã‚¿ã‚½ãƒ¼ã‚¹åˆ¥ã®èª¬æ˜Ž

### 1st_data
å¯¾è±¡: [data/1st_data/Resume/Resume.csv](../../data/1st_data/Resume/Resume.csv)

å†…å®¹:
- `ID`
- `Resume_str`
- `Resume_html` ã¯ãªã—
- `Category`

åˆ†æžçµæžœã®è¦ç‚¹:
- å…¨ 2484 ä»¶
- 3ã¤ä»¥ä¸Šã®è¦‹å‡ºã—ã‚·ã‚°ãƒŠãƒ«ã‚’æŒã¤å±¥æ­´æ›¸ãŒ 2481 ä»¶
- æ—¥ä»˜ãƒ¬ãƒ³ã‚¸ã‚’æŒã¤å±¥æ­´æ›¸ãŒ 2422 ä»¶
- å¹³å‡æ§‹é€ ã‚¹ã‚³ã‚¢ã¯ 8.727

è§£é‡ˆ:
- `Resume_str` ã¯å®Œå…¨ãªè‡ªç”±æ–‡ã§ã¯ãªãã€è¦‹å‡ºã—ãƒ»æ—¥ä»˜ãƒ»ç®‡æ¡æ›¸ããŒã‹ãªã‚Šæ®‹ã£ã¦ã„ã‚‹
- CSVãƒ™ãƒ¼ã‚¹ã® Resume parsing ã®ä¸€æ¬¡ã‚½ãƒ¼ã‚¹ã¨ã—ã¦ã‹ãªã‚Šæ‰±ã„ã‚„ã™ã„

ãŠã™ã™ã‚ç”¨é€”:
- ã‚»ã‚¯ã‚·ãƒ§ãƒ³åˆ†å‰²
- experience æŠ½å‡º
- skill_tags æŠ½å‡º
- RAGç”¨ãƒãƒ£ãƒ³ã‚¯ç”Ÿæˆ

### 2nd_data
å¯¾è±¡: [data/2nd_data/UpdatedResumeDataSet.csv](../../data/2nd_data/UpdatedResumeDataSet.csv)

å†…å®¹:
- `Category`
- `Resume`

åˆ†æžçµæžœã®è¦ç‚¹:
- å…¨ 962 ä»¶
- `summary` ã‚’æŒã¤ã¨åˆ¤å®šã•ã‚ŒãŸå±¥æ­´æ›¸ã¯ 153 ä»¶
- `experience` ã¯ 439 ä»¶
- `skill` ã¯ 962 ä»¶
- `education` ã¯ 812 ä»¶
- 4è¦ç´ ã™ã¹ã¦ã‚’æŒã¤å±¥æ­´æ›¸ã¯ 86 ä»¶

è§£é‡ˆ:
- skills ã¨ education ã¯å¼·ã„
- summary ã¯å¼±ã„
- 1st ã‚ˆã‚Šæ§‹é€ ã¯ä¸å‡ä¸€ã ãŒã€ã‚¹ã‚­ãƒ«æŠ½å‡ºã«ã¯å‘ã„ã¦ã„ã‚‹

ãŠã™ã™ã‚ç”¨é€”:
- skill ã‚»ã‚¯ã‚·ãƒ§ãƒ³æŠ½å‡º
- education æŠ½å‡º
- é›£ä¾‹ã¸ã® LLMè£œå®Œ
- ã‚»ã‚¯ã‚·ãƒ§ãƒ³å­˜åœ¨åˆ¤å®šã®è©•ä¾¡ç”¨

### 3rd_data
å¯¾è±¡:
- [data/3rd_data/01_people.csv](../../data/3rd_data/01_people.csv)
- [data/3rd_data/02_abilities.csv](../../data/3rd_data/02_abilities.csv)
- [data/3rd_data/03_education.csv](../../data/3rd_data/03_education.csv)
- [data/3rd_data/04_experience.csv](../../data/3rd_data/04_experience.csv)
- [data/3rd_data/05_person_skills.csv](../../data/3rd_data/05_person_skills.csv)
- [data/3rd_data/06_skills.csv](../../data/3rd_data/06_skills.csv)

å†…å®¹:
- person å˜ä½ã« experience / education / skills ãŒåˆ†å‰²ã•ã‚ŒãŸæ§‹é€ åŒ–ãƒ‡ãƒ¼ã‚¿
- å±¥æ­´æ›¸æœ¬æ–‡ãã®ã‚‚ã®ã§ã¯ãªãã€ãƒªãƒ¬ãƒ¼ã‚·ãƒ§ãƒŠãƒ«ãƒ‡ãƒ¼ã‚¿ã«è¿‘ã„

åˆ†æžçµæžœã®è¦ç‚¹:
- å…¨ 54933 äºº
- `summary` å°‚ç”¨ã‚½ãƒ¼ã‚¹ã¯å­˜åœ¨ã—ãªã„
- `experience` ã¯ 54933 äºº
- `skill` ã¯ 54933 äºº
- `education` ã¯ 48075 äºº
- experience ã®ä¸­å¤®å€¤ã¯ 4 ä»¶
- skill-like æƒ…å ±ã®ä¸­å¤®å€¤ã¯ 47 ä»¶

è§£é‡ˆ:
- æ—¢ã«æ§‹é€ åŒ–æ¸ˆã¿ãªã®ã§ã€Resume parsing ã‚ˆã‚Šçµ±åˆãƒ»æ¤œç´¢è¨­è¨ˆå‘ã
- `summary` ã¯åˆ¥é€”ç”Ÿæˆã™ã‚‹å¿…è¦ãŒã‚ã‚‹

ãŠã™ã™ã‚ç”¨é€”:
- metadata ãƒ™ãƒ¼ã‚¹æ¤œç´¢
- candidate profile JSON ã®ç”Ÿæˆ
- experience/skills ã®å®šé‡è©•ä¾¡
- ãƒ•ã‚£ãƒ«ã‚¿ãƒªãƒ³ã‚°é‡è¦–ã®æ¤œç´¢åŸºç›¤

### 4th_data
å¯¾è±¡:
- [data/4th_data/Resume.csv](../../data/4th_data/Resume.csv)
- [data/4th_data/training_data.csv](../../data/4th_data/training_data.csv)

#### Resume.csv
å†…å®¹:
- `ID`
- `Resume_str`
- `Resume_html`
- `Category`

åˆ†æžçµæžœã®è¦ç‚¹:
- å…¨ 2484 ä»¶
- 1st ã¨ã»ã¼åŒç­‰ã®æ§‹é€ ã‚·ã‚°ãƒŠãƒ«
- `Resume_html` ãŒå…¨ä»¶ã«å­˜åœ¨
- median HTML length ã¯ 15025.5

è§£é‡ˆ:
- 1st ã¨åŒã˜å±¥æ­´æ›¸é›†åˆç³»ã ãŒã€HTMLãŒä»˜ã„ã¦ã„ã‚‹åˆ†ã ã‘æƒ…å ±é‡ãŒå¤šã„
- ãƒ¬ã‚¤ã‚¢ã‚¦ãƒˆã‚„ã‚»ã‚¯ã‚·ãƒ§ãƒ³å¢ƒç•Œã‚’è£œå¼·ã—ãŸã„å ´åˆã«æœ‰åˆ©

ãŠã™ã™ã‚ç”¨é€”:
- Resume parsing
- HTMLæ´»ç”¨ã«ã‚ˆã‚‹æ§‹é€ è£œå¼·
- ãƒ†ã‚­ã‚¹ãƒˆæŠ½å‡ºçµæžœã®æ¤œè¨¼
- RAGå‰å‡¦ç†

#### training_data.csv
å†…å®¹:
- `company_name`
- `job_description`
- `position_title`
- `description_length`
- `model_response`

è§£é‡ˆ:
- å±¥æ­´æ›¸ãƒ‡ãƒ¼ã‚¿ã§ã¯ãªãã€æ±‚äººè¨˜è¿°ã‚’æ§‹é€ åŒ–è¦ä»¶ã«å¤‰æ›ã™ã‚‹ãŸã‚ã®æ•™å¸«ãƒ‡ãƒ¼ã‚¿ / è©•ä¾¡ãƒ‡ãƒ¼ã‚¿
- å€™è£œè€…å´ã§ã¯ãªãæ±‚äººå´ã®ãƒ‡ãƒ¼ã‚¿

ãŠã™ã™ã‚ç”¨é€”:
- Job Parsing Agent
- required/preferred æŠ½å‡º
- æ±‚äººè¦ä»¶ã®æ§‹é€ åŒ–

### 5th_data
å¯¾è±¡:
- [data/5th_data/train_data.txt](../../data/5th_data/train_data.txt)
- è£œåŠ©ã‚µãƒ³ãƒ—ãƒ«: [data/5th_data/Aline CV .txt](../../data/5th_data/Aline%20CV%20.txt)

å†…å®¹:
- `train_data.txt` ã¯ `(resume_text, annotations)` ã®ã‚¿ãƒ—ãƒ«é›†åˆ
- `annotations` ã«ã‚¨ãƒ³ãƒ†ã‚£ãƒ†ã‚£ãƒ©ãƒ™ãƒ«ãŒä»˜ã„ã¦ã„ã‚‹

åˆ†æžçµæžœã®è¦ç‚¹:
- å…¨ 200 ä»¶
- `summary` ã¯ 36 ä»¶
- `experience` ã¯ 200 ä»¶
- `skill` ã¯ 181 ä»¶
- `education` ã¯ 194 ä»¶
- 4è¦ç´ ã™ã¹ã¦ã‚’æŒã¤å±¥æ­´æ›¸ã¯ 30 ä»¶
- ä¸Šä½ã‚¨ãƒ³ãƒ†ã‚£ãƒ†ã‚£ã¯ `Name`, `Designation`, `Location`, `Degree`, `Email Address`, `College Name`, `Companies worked at`, `Skills`

è§£é‡ˆ:
- åŠæ§‹é€ å±¥æ­´æ›¸ãƒ†ã‚­ã‚¹ãƒˆã« NER æ³¨é‡ˆãŒä»˜ã„ãŸãƒ‡ãƒ¼ã‚¿
- Resume parsing ã®å­¦ç¿’ãƒ»è©•ä¾¡ã«ä½¿ã„ã‚„ã™ã„

ãŠã™ã™ã‚ç”¨é€”:
- ã‚¨ãƒ³ãƒ†ã‚£ãƒ†ã‚£æŠ½å‡ºãƒ¢ãƒ‡ãƒ«ã®å­¦ç¿’/è©•ä¾¡
- parser ã®ç²¾åº¦æ¤œè¨¼
- ã‚¹ã‚­ãƒ«ãƒ»å­¦æ­´ãƒ»ä¼šç¤¾åæŠ½å‡ºã®è©•ä¾¡ã‚»ãƒƒãƒˆ

## ç·åˆè©•ä¾¡
### å±¥æ­´æ›¸æœ¬æ–‡ã®ä¸€æ¬¡ã‚½ãƒ¼ã‚¹ã¨ã—ã¦æœ‰åŠ›
- 1st_data
- 4th_data

ç†ç”±:
- å±¥æ­´æ›¸æœ¬æ–‡ãŒã¾ã¨ã¾ã£ã¦ã„ã‚‹
- è¦‹å‡ºã—ãƒ»æ—¥ä»˜ãƒ»ã‚¹ã‚­ãƒ«è¨˜è¿°ãŒååˆ†æ®‹ã£ã¦ã„ã‚‹
- 4th ã¯ HTML ã‚‚ä½µç”¨ã§ãã‚‹

### éƒ¨åˆ†æ§‹é€ æŠ½å‡ºã®è£œåŠ©ã¨ã—ã¦æœ‰åŠ›
- 2nd_data
- 5th_data

ç†ç”±:
- 2nd ã¯ skills / education ãŒå¼·ã„
- 5th ã¯æ³¨é‡ˆä»˜ããªã®ã§ parser è©•ä¾¡ã«ä½¿ãˆã‚‹

### ãƒ¡ã‚¿ãƒ‡ãƒ¼ã‚¿æ¤œç´¢åŸºç›¤ã¨ã—ã¦æœ‰åŠ›
- 3rd_data

ç†ç”±:
- æ—¢ã« person å˜ä½ã®æ§‹é€ åŒ–ãƒ‡ãƒ¼ã‚¿
- experience / skills / education ã®ãƒ•ã‚£ãƒ«ã‚¿ãƒªãƒ³ã‚°ã«å¼·ã„

## å®Ÿè£…ã«å‘ã‘ãŸæŽ¨å¥¨ä½¿ã„åˆ†ã‘
- å€™è£œè€…æ¤œç´¢ãƒ»RAGæœ¬ä½“:
  - 1st_data ã¾ãŸã¯ 4th_data
- HTMLã‚„åŽŸæ–‡æ§‹é€ ã‚’æ´»ã‹ã—ãŸã„å ´åˆ:
  - 4th_data
- Resume parser / NER ã®è©•ä¾¡:
  - 5th_data
- æ§‹é€ åŒ–ãƒ—ãƒ­ãƒ•ã‚£ãƒ¼ãƒ«ã®æ¤œç´¢ãƒ»é›†è¨ˆ:
  - 3rd_data
- è£œåŠ©çš„ãª section æŠ½å‡ºãƒ»å¤šæ§˜æ€§ç¢ºèª:
  - 2nd_data

## çµè«–
æœ€ã‚‚å®Ÿè£…ã—ã‚„ã™ã„çµ„ã¿åˆã‚ã›ã¯æ¬¡ã®é€šã‚Šã§ã™ã€‚

- ä¸»ãƒ‡ãƒ¼ã‚¿: 1st_data ã¾ãŸã¯ 4th_data
- è©•ä¾¡/è£œåŠ©ãƒ‡ãƒ¼ã‚¿: 5th_data
- æ§‹é€ åŒ–ãƒ¡ã‚¿ãƒ‡ãƒ¼ã‚¿è£œå®Œ: 3rd_data
- è£œåŠ©æ¯”è¼ƒç”¨: 2nd_data

ç‰¹ã«ã€åˆæœŸå®Ÿè£…ã§ã¯ 4th_data ã‚’ä¸»ã‚½ãƒ¼ã‚¹ã«ã—ã€å¿…è¦ã«å¿œã˜ã¦ 1st_data ã¨äº’æ›æ‰±ã„ã™ã‚‹æ–¹é‡ãŒæœ€ã‚‚æ‰±ã„ã‚„ã™ã„ã§ã™ã€‚

