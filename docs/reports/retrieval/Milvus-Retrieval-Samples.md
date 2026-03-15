# Milvus Retrieval Check (1st_data Representative Samples)

- Generated at (UTC): 2026-03-15T02:56:20.717391
- Sample size: 10
- Top-K: 5
- Embedding model: text-embedding-3-small
- Occ collection: occupation_collection
- Skill collection: skill_collection

## Summary
- Occ top1 category-anchor hit: 8 / 10
- Skill top1 query-token overlap hit: 7 / 10

## Per Sample

### ID=10176815 / category=AVIATION
- Occupation query: `AVIATION`
- Skill query: `Proficient with maintenance tracking software`
- Heuristic: occ_anchor_hit=True, skill_query_overlap=False

Occupation Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | aviation inspector | 0.529046 | 0.529046 |
| 2 | avionics inspector | 0.514619 | 0.514619 |
| 3 | aircraft maintenance engineer | 0.498751 | 0.498751 |
| 4 | aviation safety officer | 0.496018 | 0.496018 |
| 5 | aviation data communications manager | 0.495817 | 0.495817 |

Skill Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | maintain inventory of rail track parts | 0.528742 | 0.528742 |
| 2 | maintain inventory of tools | 0.526421 | 0.526421 |
| 3 | use computerised maintenance management systems | 0.526178 | 0.526178 |
| 4 | maintain records of maintenance interventions | 0.524020 | 0.524020 |
| 5 | maintain inventory of pesticides | 0.523864 | 0.523864 |

### ID=10041713 / category=CONSTRUCTION
- Occupation query: `CONSTRUCTION`
- Skill query: `Energy Management Professional Certified by Schneider University.`
- Heuristic: occ_anchor_hit=True, skill_query_overlap=True

Occupation Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | construction general contractor | 0.474407 | 0.474407 |
| 2 | construction manager | 0.449771 | 0.449771 |
| 3 | construction general supervisor | 0.442202 | 0.442202 |
| 4 | building construction worker | 0.434108 | 0.434108 |
| 5 | construction quality inspector | 0.433524 | 0.433524 |

Skill Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | energy efficiency | 0.453625 | 0.453625 |
| 2 | energy conservation | 0.443939 | 0.443939 |
| 3 | carry out energy management of facilities | 0.416929 | 0.416929 |
| 4 | smart grids systems | 0.412729 | 0.412729 |
| 5 | design passive energy measures | 0.409637 | 0.409637 |

### ID=10030015 / category=ENGINEERING
- Occupation query: `ENGINEERING`
- Skill query: `DasyLab`
- Heuristic: occ_anchor_hit=False, skill_query_overlap=False

Occupation Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | equipment engineer | 0.527851 | 0.527851 |
| 2 | construction engineer | 0.523447 | 0.523447 |
| 3 | contract engineer | 0.520627 | 0.520627 |
| 4 | military engineer | 0.519582 | 0.519582 |
| 5 | civil engineering technician | 0.516646 | 0.516646 |

Skill Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | LAMS | 0.367809 | 0.367809 |
| 2 | automated analysers in the medical laboratory | 0.354273 | 0.354273 |
| 3 | Brightspace (learning management systems) | 0.353884 | 0.353884 |
| 4 | laboratory equipment | 0.340958 | 0.340958 |
| 5 | check the received biological samples | 0.328984 | 0.328984 |

### ID=10504237 / category=TEACHER
- Occupation query: `TEACHER`
- Skill query: `Anatomy`
- Heuristic: occ_anchor_hit=True, skill_query_overlap=True

Occupation Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | drama teacher | 0.501579 | 0.501579 |
| 2 | secondary school teacher | 0.488013 | 0.488013 |
| 3 | drama teacher secondary school | 0.486087 | 0.486087 |
| 4 | language school teacher | 0.483211 | 0.483211 |
| 5 | teacher of talented and gifted students | 0.482430 | 0.482430 |

Skill Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | human anatomy | 0.563476 | 0.563476 |
| 2 | pathological anatomy | 0.518051 | 0.518051 |
| 3 | horse anatomy | 0.514003 | 0.514003 |
| 4 | histology | 0.504665 | 0.504665 |
| 5 | anatomy of animals | 0.497413 | 0.497413 |

### ID=10005171 / category=DIGITAL-MEDIA
- Occupation query: `DIGITAL-MEDIA`
- Skill query: `radio and television interviews featuring Chattanooga State administrators`
- Heuristic: occ_anchor_hit=True, skill_query_overlap=True

Occupation Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | digital media designer | 0.511475 | 0.511475 |
| 2 | media integration operator | 0.442636 | 0.442636 |
| 3 | digital artist | 0.436440 | 0.436440 |
| 4 | digital marketing manager | 0.433229 | 0.433229 |
| 5 | advertising media planner | 0.396075 | 0.396075 |

Skill Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | give interviews to media | 0.333589 | 0.333589 |
| 2 | present during live broadcasts | 0.277643 | 0.277643 |
| 3 | organise press conferences | 0.273861 | 0.273861 |
| 4 | operate radio equipment | 0.261579 | 0.261579 |
| 5 | interview techniques | 0.260443 | 0.260443 |

### ID=10070224 / category=PUBLIC-RELATIONS
- Occupation query: `PUBLIC-RELATIONS`
- Skill query: `Microsoft Office Suite: Word`
- Heuristic: occ_anchor_hit=True, skill_query_overlap=True

Occupation Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | public relations manager | 0.530518 | 0.530518 |
| 2 | public relations officer | 0.512696 | 0.512696 |
| 3 | spokesperson | 0.491099 | 0.491099 |
| 4 | public affairs consultant | 0.461925 | 0.461925 |
| 5 | communication manager | 0.377817 | 0.377817 |

Skill Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | use word processing software | 0.540683 | 0.540683 |
| 2 | use microsoft office | 0.512855 | 0.512855 |
| 3 | Microsoft Access | 0.422890 | 0.422890 |
| 4 | use presentation software | 0.413069 | 0.413069 |
| 5 | apply desktop publishing techniques | 0.405797 | 0.405797 |

### ID=10062724 / category=HEALTHCARE
- Occupation query: `HEALTHCARE`
- Skill query: `design`
- Heuristic: occ_anchor_hit=True, skill_query_overlap=True

Occupation Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | healthcare assistant | 0.441855 | 0.441855 |
| 2 | healthcare inspector | 0.434803 | 0.434803 |
| 3 | healthcare consultant | 0.433607 | 0.433607 |
| 4 | healthcare institution manager | 0.421748 | 0.421748 |
| 5 | public health policy officer | 0.382367 | 0.382367 |

Skill Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | design user interface | 0.472413 | 0.472413 |
| 2 | select design elements | 0.465204 | 0.465204 |
| 3 | develop design plans | 0.461338 | 0.461338 |
| 4 | design principles | 0.460482 | 0.460482 |
| 5 | design process | 0.450291 | 0.450291 |

### ID=10549585 / category=FINANCE
- Occupation query: `FINANCE`
- Skill query: `Skills Experience Total Years Last Used`
- Heuristic: occ_anchor_hit=True, skill_query_overlap=True

Occupation Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | financial manager | 0.450558 | 0.450558 |
| 2 | public finance accountant | 0.432097 | 0.432097 |
| 3 | financial broker | 0.418468 | 0.418468 |
| 4 | financial planner | 0.416746 | 0.416746 |
| 5 | financial controller | 0.414563 | 0.414563 |

Skill Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | use experience map | 0.440260 | 0.440260 |
| 2 | last types | 0.419782 | 0.419782 |
| 3 | use tools for construction and repair | 0.417952 | 0.417952 |
| 4 | use authentic crafting techniques | 0.406531 | 0.406531 |
| 5 | age furniture artificially | 0.397902 | 0.397902 |

### ID=10554236 / category=ACCOUNTANT
- Occupation query: `ACCOUNTANT`
- Skill query: `Certified Defense Financial Manager`
- Heuristic: occ_anchor_hit=True, skill_query_overlap=False

Occupation Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | accountant | 0.611652 | 0.611652 |
| 2 | bookkeeper | 0.587359 | 0.587359 |
| 3 | accounting assistant | 0.567562 | 0.567562 |
| 4 | financial auditor | 0.558525 | 0.558525 |
| 5 | accounting analyst | 0.557364 | 0.557364 |

Skill Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | apply certification and payment procedures | 0.410387 | 0.410387 |
| 2 | manage cash desk | 0.406382 | 0.406382 |
| 3 | financial management | 0.373889 | 0.373889 |
| 4 | manage financial and material resources | 0.368454 | 0.368454 |
| 5 | control financial resources | 0.364037 | 0.364037 |

### ID=10953078 / category=AGRICULTURE
- Occupation query: `AGRICULTURE`
- Skill query: `balance`
- Heuristic: occ_anchor_hit=False, skill_query_overlap=True

Occupation Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | agricultural engineer | 0.490751 | 0.490751 |
| 2 | agricultural scientist | 0.479283 | 0.479283 |
| 3 | agronomist | 0.470415 | 0.470415 |
| 4 | agricultural policy officer | 0.460292 | 0.460292 |
| 5 | crop production worker | 0.458714 | 0.458714 |

Skill Top-K

| rank | label | score | confidence |
|---:|---|---:|---:|
| 1 | balance tyres | 0.433732 | 0.433732 |
| 2 | perform balance sheet operations | 0.410270 | 0.410270 |
| 3 | balance transportation cargo | 0.391213 | 0.391213 |
| 4 | balance participants' personal needs with group needs | 0.373756 | 0.373756 |
| 5 | harmonise body movements | 0.369783 | 0.369783 |
