# ESCO Schema Analysis

- data_dir: C:\Users\Administrator\Desktop\prodapt-capstone\data\ESCO
- total_csv_files: 19

## Logical groups
- Core concepts: occupations_en.csv, skills_en.csv
- Taxonomy groups: ISCOGroups_en.csv, skillGroups_en.csv
- Relation edges: broaderRelationsOccPillar_en.csv, broaderRelationsSkillPillar_en.csv, occupationSkillRelations_en.csv, skillSkillRelations_en.csv
- Hierarchy views: skillsHierarchy_en.csv
- Theme collections: digCompSkillsCollection_en.csv, digitalSkillsCollection_en.csv, greenShareOcc_en.csv, greenSkillsCollection_en.csv, languageSkillsCollection_en.csv, researchOccupationsCollection_en.csv, researchSkillsCollection_en.csv, transversalSkillsCollection_en.csv
- Concept schemes: conceptSchemes_en.csv
- Data dictionary: dictionary_en.csv

## Recommended logical schema
### concept_master
- occupations_en.csv
- skills_en.csv
- ISCOGroups_en.csv
- skillGroups_en.csv
### relation_edges
- occupationSkillRelations_en.csv
- skillSkillRelations_en.csv
- broaderRelationsOccPillar_en.csv
- broaderRelationsSkillPillar_en.csv
### hierarchy_views
- skillsHierarchy_en.csv
### theme_collections
- digCompSkillsCollection_en.csv
- digitalSkillsCollection_en.csv
- greenSkillsCollection_en.csv
- languageSkillsCollection_en.csv
- researchOccupationsCollection_en.csv
- researchSkillsCollection_en.csv
- transversalSkillsCollection_en.csv

## Relationship hints
- occupations_en.conceptUri -> occupationSkillRelations_en.occupationUri: Occupation concept joins to occupation-skill relation edges.
- skills_en.conceptUri -> occupationSkillRelations_en.skillUri: Skill concept joins to occupation-skill relation edges.
- skills_en.conceptUri -> skillSkillRelations_en.originalSkillUri / relatedSkillUri: Skill-to-skill graph edges for related, optional, or knowledge links.
- occupations_en.iscoGroup -> ISCOGroups_en.code: Occupation rows reference an ISCO classification code.
- broaderRelationsOccPillar_en.conceptUri -> broaderRelationsOccPillar_en.broaderUri: Occupation-side broader/narrower hierarchy edges.
- broaderRelationsSkillPillar_en.conceptUri -> broaderRelationsSkillPillar_en.broaderUri: Skill-side broader/narrower hierarchy edges.
- skillsHierarchy_en.Level N URI -> skills_en.conceptUri / skillGroups_en.conceptUri: Readable multi-level hierarchy projection for skills and skill groups.

## File schema details

### broaderRelationsOccPillar_en.csv
- role: relation
- rows: 3648
- columns: 6
- description: Edge table connecting concepts to broader concepts or related concepts.
- primary_key_candidates: conceptUri
- uri_columns: conceptUri, broaderUri
- label_columns: conceptLabel, broaderLabel

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| conceptType | 100.0% | ISCOGroup / Occupation | No direct related property exists |
| conceptUri | 100.0% | http://data.europa.eu/esco/isco/C01 / http://data.europa.eu/esco/isco/C011 / http://data.europa.eu/esco/isco/C0110 | No direct related property exists |
| conceptLabel | 100.0% | Commissioned armed forces officers / Non-commissioned armed forces officers / Armed forces occupations, other ranks | The preferred lexical label for a resource, in a given language. |
| broaderType | 100.0% | ISCOGroup / Occupation | No direct related property exists |
| broaderUri | 100.0% | http://data.europa.eu/esco/isco/C0 / http://data.europa.eu/esco/isco/C01 / http://data.europa.eu/esco/isco/C011 | No direct related property exists |
| broaderLabel | 100.0% | Armed forces occupations / Commissioned armed forces officers / Non-commissioned armed forces officers | The preferred lexical label for a resource, in a given language. |

### broaderRelationsSkillPillar_en.csv
- role: relation
- rows: 20819
- columns: 6
- description: Edge table connecting concepts to broader concepts or related concepts.
- primary_key_candidates: conceptUri
- uri_columns: conceptUri, broaderUri
- label_columns: conceptLabel, broaderLabel

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| conceptType | 100.0% | SkillGroup / KnowledgeSkillCompetence | No direct related property exists |
| conceptUri | 100.0% | http://data.europa.eu/esco/isced-f/00 / http://data.europa.eu/esco/isced-f/000 / http://data.europa.eu/esco/isced-f/0000 | No direct related property exists |
| conceptLabel | 100.0% | generic programmes and qualifications / generic programmes and qualifications not further defined / basic programmes and qualifications | The preferred lexical label for a resource, in a given language. |
| broaderType | 100.0% | SkillGroup / KnowledgeSkillCompetence | No direct related property exists |
| broaderUri | 100.0% | http://data.europa.eu/esco/skill/c46fcb45-5c14-4ffa-abed-5a43f104bb22 / http://data.europa.eu/esco/isced-f/00 / http://data.europa.eu/esco/isced-f/000 | No direct related property exists |
| broaderLabel | 100.0% | knowledge / generic programmes and qualifications / generic programmes and qualifications not further defined | The preferred lexical label for a resource, in a given language. |

### conceptSchemes_en.csv
- role: scheme
- rows: 20
- columns: 7
- description: Concept scheme metadata and top-level concept membership.
- primary_key_candidates: conceptSchemeUri
- uri_columns: conceptSchemeUri
- label_columns: preferredLabel

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| conceptType | 100.0% | ConceptScheme | No direct related property exists |
| conceptSchemeUri | 100.0% | http://data.europa.eu/esco/concept-scheme/6c930acd-c104-4ece-acf7-f44fd7333036 / http://data.europa.eu/esco/concept-scheme/8ae4b9f3-507e-4057-a145-2f96f0132613 / http://data.europa.eu/esco/concept-scheme/digcomp | No direct related property exists |
| preferredLabel | 100.0% | Digital / Research occupations / DigComp | The preferred lexical label for a resource, in a given language. |
| title | 15.0% | ESCO relationship types / ESCO Skill Pillar concept (sub-) Types / ESCO Skill Pillar concept reusability levels | A name given to the resource. |
| status | 70.0% | released | ISO status - on ThesaurusConcept - on ThesaurusTerm |
| description | 20.0% | A taxonomy of the different label roles in ESCO / A taxonomy of the occupations in ESCO / A taxonomy of the skills and competences in ESCO | An account of the resource. |
| hasTopConcept | 100.0% | http://data.europa.eu/esco/skill/6c80d53c-d8c9-41fe-998f-091fca208834, http://data.europa.eu/esco/skill/3be6b84a-fa78-42b9-a8df-150cdb40b9d7, http://data.europa / http://data.europa.eu/esco/occupation/d7d986e1-7333-431b-9719-0c5c6939e360, http://data.europa.eu/esco/occupation/b2cede50-82bb-4684-9f11-1930e12ad672, http://d / http://data.europa.eu/esco/skill/21d2f96d-35f7-4e3f-9745-c533d2dd6e97, http://data.europa.eu/esco/skill/426ceaba-6867-481c-bb6b-aee3933da7d2, http://data.europa | Relates, by convention, a concept scheme to a concept which is topmost in the broader/narrower concept hierarchies for that scheme, providing an entry point to these hierarchies. |

### dictionary_en.csv
- role: data_dictionary
- rows: 160
- columns: 4
- description: Field-level glossary for the ESCO CSV export.
- label_columns: filename

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| filename | 100.0% | occupations / skills / ISCOGroups |  |
| data header | 100.0% | conceptType / conceptUri / iscoGroup |  |
| property | 70.6% | http://www.w3.org/2004/02/skos/core#notation / http://www.w3.org/2004/02/skos/core#prefLabel / http://www.w3.org/2004/02/skos/core#altLabel |  |
| description | 100.0% | No direct related property exists / A notation, also known as classification code, is a string of characters such as "T58.5" or "303.4833" used to uniquely identify a concept within the scope of a / The preferred lexical label for a resource, in a given language. |  |

### digCompSkillsCollection_en.csv
- role: collection
- rows: 25
- columns: 10
- description: Thematic subset of ESCO concepts for a domain-specific use case.
- primary_key_candidates: conceptUri
- uri_columns: conceptUri, broaderConceptUri
- label_columns: preferredLabel, altLabels

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| conceptType | 100.0% | KnowledgeSkillCompetence | No direct related property exists |
| conceptUri | 100.0% | http://data.europa.eu/esco/skill/14832d87-2f2f-4895-b290-e4760ebae42a / http://data.europa.eu/esco/skill/16a00c69-9c74-4c37-96d7-6301d285e5ce / http://data.europa.eu/esco/skill/1a4cc54f-1e53-442b-a6d2-1682dc8ef8f9 | No direct related property exists |
| preferredLabel | 100.0% | solve technical problems / use e-services / creatively use digital technologies | The preferred lexical label for a resource, in a given language. |
| status | 100.0% | released | ISO status - on ThesaurusConcept - on ThesaurusTerm |
| skillType | 80.0% | skill/competence / knowledge | Type of competence (a tagging concept) |
| reuseLevel | 80.0% | cross-sector / occupation-specific | Reuseability level of a skill |
| altLabels | 92.0% | resolve technical issues | diagnose technical problems / use online payment solutions | make use of e-services | use electronic services | engage in citizenship through digital technologies | able to use e-services |  / use digital technologies for cognitive tasks | use digital technologies for process innovation | use digital technologies for product innovation | use digital t | An alternative lexical label for a resource. |
| description | 100.0% | Identify technical problems when operating devices and using digital environments, and solve them (from trouble-shooting to solving more complex problems). / Participate in society through the use of public and private digital services. Seek opportunities for self-empowerment and for participatory citizenship through / Use digital tools and technologies to create knowledge and to innovate processes and products. Engage individually and collectively in cognitive processing to u | An account of the resource. |
| broaderConceptUri | 100.0% | http://data.europa.eu/esco/skill/7e5147d1-60b1-4a68-804b-1f5cb0396b91 | http://data.europa.eu/esco/skill/a628d2d1-f40a-4c37-a357-2801726f2996 | http://data.euro / http://data.europa.eu/esco/skill/574257ea-7b64-4100-b7b6-e27c233fe143 | http://data.europa.eu/esco/skill/98fb499f-9155-412d-a8a0-95ba97126fec / http://data.europa.eu/esco/skill/7e5147d1-60b1-4a68-804b-1f5cb0396b91 | http://data.europa.eu/esco/skill/98fb499f-9155-412d-a8a0-95ba97126fec | No direct related property exists |
| broaderConceptPT | 100.0% | problem-solving with digital tools | identify problems | resolving computer problems / digital communication and collaboration | using digital tools for collaboration and productivity / problem-solving with digital tools | using digital tools for collaboration and productivity | The preferred lexical label for a resource, in a given language. |

### digitalSkillsCollection_en.csv
- role: collection
- rows: 1284
- columns: 10
- description: Thematic subset of ESCO concepts for a domain-specific use case.
- primary_key_candidates: conceptUri
- uri_columns: conceptUri, broaderConceptUri
- label_columns: preferredLabel, altLabels

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| conceptType | 100.0% | KnowledgeSkillCompetence | No direct related property exists |
| conceptUri | 100.0% | http://data.europa.eu/esco/skill/000f1d3d-220f-4789-9c0a-cc742521fb02 / http://data.europa.eu/esco/skill/00c04e40-35ea-4ed1-824c-82f936c8f876 / http://data.europa.eu/esco/skill/013441c1-1f13-47e9-80c4-9a53e8e1bc05 | No direct related property exists |
| preferredLabel | 100.0% | Haskell / incremental development / KDevelop | The preferred lexical label for a resource, in a given language. |
| status | 100.0% | released | ISO status - on ThesaurusConcept - on ThesaurusTerm |
| skillType | 100.0% | knowledge / skill/competence | Type of competence (a tagging concept) |
| reuseLevel | 100.0% | sector-specific / cross-sector / occupation-specific | Reuseability level of a skill |
| altLabels | 99.1% | Haskell techniques / gradual development / kdevplatform | KDevelop platform | An alternative lexical label for a resource. |
| description | 100.0% | The techniques and principles of software development, such as analysis, algorithms, coding, testing and compiling of programming paradigms in Haskell. / The incremental development model is a methodology to design software systems and applications. / The computer program KDevelop is a suite of software development tools for writing programs, such as compiler, debugger, code editor, code highlights, packaged  | An account of the resource. |
| broaderConceptUri | 100.0% | http://data.europa.eu/esco/skill/21d2f96d-35f7-4e3f-9745-c533d2dd6e97 | http://data.europa.eu/esco/isced-f/0613 / http://data.europa.eu/esco/skill/bec4359e-cb92-468f-a997-8fb28e32fba9 | http://data.europa.eu/esco/isced-f/0613 / http://data.europa.eu/esco/skill/925463a7-d51f-4d5b-9f79-4d28cf30acde | http://data.europa.eu/esco/isced-f/0612 | No direct related property exists |
| broaderConceptPT | 100.0% | computer programming | software and applications development and analysis / ICT project management methodologies | software and applications development and analysis / integrated development environment software | database and network design and administration | The preferred lexical label for a resource, in a given language. |

### greenShareOcc_en.csv
- role: collection
- rows: 3590
- columns: 5
- description: Thematic subset of ESCO concepts for a domain-specific use case.
- primary_key_candidates: conceptUri
- uri_columns: conceptUri
- label_columns: preferredLabel

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| conceptType | 100.0% | ISCO level 3 / ISCO level 4 / Occupation |  |
| conceptUri | 100.0% | http://data.europa.eu/esco/isco/C011 / http://data.europa.eu/esco/isco/C0110 / http://data.europa.eu/esco/occupation/f2cc5978-e45c-4f28-b859-7f89221b0505 |  |
| code | 100.0% | 011 / 0110 / 0110.1 |  |
| preferredLabel | 100.0% | Commissioned armed forces officers / air force officer / armed forces officer |  |
| greenShare | 100.0% | 0.00575396825396825 / 0.0 / 0.0333333333333333 |  |

### greenSkillsCollection_en.csv
- role: collection
- rows: 629
- columns: 10
- description: Thematic subset of ESCO concepts for a domain-specific use case.
- primary_key_candidates: conceptUri
- uri_columns: conceptUri, broaderConceptUri
- label_columns: preferredLabel, altLabels

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| conceptType | 100.0% | KnowledgeSkillCompetence | No direct related property exists |
| conceptUri | 100.0% | http://data.europa.eu/esco/skill/001d46db-035e-4b92-83a3-ed8771e0c123 / http://data.europa.eu/esco/skill/0037c821-2898-4919-b96e-7ed1cd89554c / http://data.europa.eu/esco/skill/00735755-adc6-4ea0-b034-b8caff339c9f | No direct related property exists |
| preferredLabel | 100.0% | train staff to reduce food waste / develop energy saving concepts / install heat pump | The preferred lexical label for a resource, in a given language. |
| status | 100.0% | released | ISO status - on ThesaurusConcept - on ThesaurusTerm |
| skillType | 100.0% | skill/competence / knowledge | Type of competence (a tagging concept) |
| reuseLevel | 100.0% | sector-specific / cross-sector / transversal | Reuseability level of a skill |
| altLabels | 99.8% | teach students food waste reduction practices | educate staff on food waste reduction | educate workers on food recycling methods | inform staff on food waste r / develop concepts for energy saving | create energy saving concepts | energy saving concepts creating | creating energy saving concepts | creating concepts for e / installation of heat pumps | commissioning heat pumps | heat pump installing | heat pump commissioning | installation of heat pump | commissioning heat pump | c | An alternative lexical label for a resource. |
| description | 100.0% | Establish new trainings and staff development provisions to support staff knowledge in food waste prevention and food recycling practices. Ensure that staff und / Use current research results and collaborate with experts to optimise or develop concepts, equipment, and production processes which require a lesser amount of  / Install heat pumps, which use the physical properties of substances called refrigerants to extract heat from an environment and release it to a warmer environme | An account of the resource. |
| broaderConceptUri | 100.0% | http://data.europa.eu/esco/skill/6c4fa8c8-e9e1-49b5-897f-6b61fe649488 / http://data.europa.eu/esco/skill/c2a0c52c-0b4b-4180-a918-92650ea3b458 | http://data.europa.eu/esco/skill/c23e0a2f-f04b-45bc-b0dd-20571f6b502c / http://data.europa.eu/esco/skill/b85caa4a-f04b-4331-80df-11404fd71225 | No direct related property exists |
| broaderConceptPT | 100.0% | training on operational procedures / think innovatively | developing operational policies and procedures / installing heating, ventilation and air conditioning equipment | The preferred lexical label for a resource, in a given language. |

### ISCOGroups_en.csv
- role: taxonomy_group
- rows: 619
- columns: 8
- description: Taxonomy grouping table used as parent categories or classification levels.
- primary_key_candidates: conceptUri
- uri_columns: conceptUri
- label_columns: preferredLabel, altLabels

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| conceptType | 100.0% | ISCOGroup | No direct related property exists |
| conceptUri | 100.0% | http://data.europa.eu/esco/isco/C0 / http://data.europa.eu/esco/isco/C01 / http://data.europa.eu/esco/isco/C011 | No direct related property exists |
| code | 100.0% | 0 / 01 / 011 | A notation, also known as classification code, is a string of characters such as "T58.5" or "303.4833" used to uniquely identify a concept within the scope of a given concept scheme. |
| preferredLabel | 100.0% | Armed forces occupations / Commissioned armed forces officers / Non-commissioned armed forces officers | The preferred lexical label for a resource, in a given language. |
| status | 100.0% | released | ISO status - on ThesaurusConcept - on ThesaurusTerm |
| altLabels | 0.0% |  | An alternative lexical label for a resource. |
| inScheme | 100.0% | http://data.europa.eu/esco/concept-scheme/occupations, http://data.europa.eu/esco/concept-scheme/isco | Relates a resource (for example a concept) to a concept scheme in which it is included. |
| description | 100.0% | Armed forces occupations include all jobs held by members of the armed forces. Members of the armed forces are those personnel who are currently serving in the  / Commissioned armed forces officers provide leadership and management to organizational units in the armed forces and/or perform similar tasks to those performed / Commissioned armed forces officers provide leadership and management to organizational units in the armed forces and/or perform similar tasks to those performed | An account of the resource. |

### languageSkillsCollection_en.csv
- role: collection
- rows: 359
- columns: 10
- description: Thematic subset of ESCO concepts for a domain-specific use case.
- primary_key_candidates: conceptUri
- uri_columns: conceptUri, broaderConceptUri
- label_columns: preferredLabel, altLabels

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| conceptType | 100.0% | KnowledgeSkillCompetence | No direct related property exists |
| conceptUri | 100.0% | http://data.europa.eu/esco/skill/01f10952-cb59-4347-9aee-d4fbc51c870a / http://data.europa.eu/esco/skill/021c8a09-6b8d-4708-a5dd-17677e846640 / http://data.europa.eu/esco/skill/02d68c2b-1722-4440-8e25-376650e123c8 | No direct related property exists |
| skillType | 100.0% | skill/competence / knowledge | Type of competence (a tagging concept) |
| reuseLevel | 100.0% | transversal / cross-sector | Reuseability level of a skill |
| preferredLabel | 100.0% | write Hungarian / understand spoken Luxembourgish / understand written Korean | The preferred lexical label for a resource, in a given language. |
| status | 100.0% | released | ISO status - on ThesaurusConcept - on ThesaurusTerm |
| altLabels | 99.4% | correspond in written Hungarian | show competency in written Hungarian / understand Luxembourgish speech | interpret spoken Luxembourgish | comprehend spoken Luxembourgish | make sense of spoken Luxembourgish | listen to Luxembourgis / read Korean | comprehend written Korean | make sense of written Korean | interpret written Korean | understand Korean writing | An alternative lexical label for a resource. |
| description | 100.0% | Compose written texts in Hungarian. / Comprehend orally expressed Luxembourgish. / Read and comprehend written texts in Korean. | An account of the resource. |
| broaderConceptUri | 100.0% | http://data.europa.eu/esco/skill/ddd3596a-43f3-402e-960a-5f79362a8609 / http://data.europa.eu/esco/skill/7d16f1e4-1003-4f1f-9595-5cafb25a67df / http://data.europa.eu/esco/skill/f9bc2890-d1f2-4a83-bd7b-b150a7679c79 | No direct related property exists |
| broaderConceptPT | 100.0% | Hungarian / Luxembourgish / Korean | The preferred lexical label for a resource, in a given language. |

### occupations_en.csv
- role: core_concept
- rows: 3043
- columns: 15
- description: Primary concept table containing normalized occupation or skill records.
- primary_key_candidates: conceptUri
- uri_columns: conceptUri
- label_columns: preferredLabel, altLabels, hiddenLabels

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| conceptType | 100.0% | Occupation | No direct related property exists |
| conceptUri | 100.0% | http://data.europa.eu/esco/occupation/00030d09-2b3a-4efd-87cc-c4ea39d27c34 / http://data.europa.eu/esco/occupation/000e93a3-d956-4e45-aacb-f12c83fedf84 / http://data.europa.eu/esco/occupation/0019b951-c699-4191-8208-9822882d150c | No direct related property exists |
| iscoGroup | 100.0% | 2654 / 8121 / 7543 | A notation, also known as classification code, is a string of characters such as "T58.5" or "303.4833" used to uniquely identify a concept within the scope of a given concept scheme. |
| preferredLabel | 100.0% | technical director / metal drawing machine operator / precision device inspector | The preferred lexical label for a resource, in a given language. |
| altLabels | 100.0% | director of technical arts technical supervisor head of technical technical and operations director technical manager head of technical department / wire drawer forming machine operative draw machine operator metal drawing machine technician draw machine operative metal drawing machine operative wiredrawing  / precision device quality control supervisor precision device quality assurance supervisor precision instrument quality control inspector precision instrument in | An alternative lexical label for a resource. |
| hiddenLabels | 0.3% | sexual health consultant youth policy manager youth operator eurodesk mobility advisor youth animator youth technician youth Information researcher youth profes / azure cloud architect / project assistant | A lexical label for a resource that should be hidden when generating visual displays of the resource, but should still be accessible to free text search operations. |
| status | 100.0% | released | ISO status - on ThesaurusConcept - on ThesaurusTerm |
| modifiedDate | 100.0% | 2024-01-25T11:28:50.295Z / 2024-01-23T10:09:32.099Z / 2024-01-25T15:00:12.188Z | Date on which the resource was changed. |
| regulatedProfessionNote | 100.0% | http://data.europa.eu/esco/regulated-professions/unregulated / http://data.europa.eu/esco/regulated-professions/regulated | The subject occupation is regulated according the description in the note.  The note typically contains a hyperlink. |
| scopeNote | 10.2% | Excludes people performing analysis of blood samples, cell cultures, or review blood samples. Excludes people performing assignment of blood groups, interpretat / Includes people performing activities at the point of sale. / Includes <a resource="http://data.europa.eu/esco/occupation/1009be17-7efd-45f1-a033-566bf179c588" typeOf="http://data.europa.eu/esco/model#Occupation" href="htt | A note that helps to clarify the meaning and/or the use of a concept. |
| definition | 0.3% | Excludes choreologist. / Credit intermediaries are natural or legal persons who offer credit agreements to consumers. They act on behalf of creditors to conclude agreements with consume / A financial planner or personal financial planner helps others with their financial issues and planning such as retirement, investments and insurance. They deve | A statement or formal explanation of the meaning of a concept. |
| inScheme | 100.0% | http://data.europa.eu/esco/concept-scheme/member-occupations, http://data.europa.eu/esco/concept-scheme/occupations / http://data.europa.eu/esco/concept-scheme/member-occupations, http://data.europa.eu/esco/concept-scheme/8ae4b9f3-507e-4057-a145-2f96f0132613, http://data.europa | Relates a resource (for example a concept) to a concept scheme in which it is included. |
| description | 100.0% | Technical directors realise the artistic visions of the creators within technical constraints. They coordinate the operations of various production units, such  / Metal drawing machine operators set up and operate drawing machines for ferrous and non-ferrous metal products, designed to provide wires, bars, pipes, hollow p / Precision device inspectors make sure precision devices, such as micrometers and gauges, operate according to design specifications. They may adjust the precisi | An account of the resource. |
| code | 100.0% | 2654.1.7 / 8121.4 / 7543.10.3 | A notation, also known as classification code, is a string of characters such as "T58.5" or "303.4833" used to uniquely identify a concept within the scope of a given concept scheme. |
| naceCode | 100.0% | http://data.europa.eu/ux2/nace2.1/9031 / http://data.europa.eu/ux2/nace2.1/242 / http://data.europa.eu/ux2/nace2.1/2651 | A tagging concept using the NACE codes to specify the industry sector of the tagged subject. |

### occupationSkillRelations_en.csv
- role: relation
- rows: 126051
- columns: 6
- description: Edge table connecting concepts to broader concepts or related concepts.
- primary_key_candidates: occupationUri, skillUri
- uri_columns: occupationUri, skillUri
- label_columns: occupationLabel, skillLabel

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| occupationUri | 100.0% | http://data.europa.eu/esco/occupation/00030d09-2b3a-4efd-87cc-c4ea39d27c34 / http://data.europa.eu/esco/occupation/000e93a3-d956-4e45-aacb-f12c83fedf84 / http://data.europa.eu/esco/occupation/0019b951-c699-4191-8208-9822882d150c | No direct related property exists |
| occupationLabel | 100.0% | technical director / metal drawing machine operator / precision device inspector | The preferred lexical label for a resource, in a given language. |
| relationType | 100.0% | essential / optional | The ESCO skill or competence that is relevant (but optional) for the subject occuption. | The ESCO skill or competence that is essential for the subject occupation or skill. |
| skillType | 100.0% | knowledge / skill/competence | Type of competence (a tagging concept) |
| skillUri | 100.0% | http://data.europa.eu/esco/skill/fed5b267-73fa-461d-9f69-827c78beb39d / http://data.europa.eu/esco/skill/05bc7677-5a64-4e0c-ade3-0140348d4125 / http://data.europa.eu/esco/skill/271a36a0-bc7a-43a9-ad29-0a3f3cac4e57 | No direct related property exists |
| skillLabel | 100.0% | theatre techniques / organise rehearsals / write risk assessment on performing arts production | The preferred lexical label for a resource, in a given language. |

### researchOccupationsCollection_en.csv
- role: collection
- rows: 122
- columns: 8
- description: Thematic subset of ESCO concepts for a domain-specific use case.
- primary_key_candidates: conceptUri
- uri_columns: conceptUri, broaderConceptUri
- label_columns: preferredLabel, altLabels

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| conceptType | 100.0% | Occupation | No direct related property exists |
| conceptUri | 100.0% | http://data.europa.eu/esco/occupation/01ffb917-98dc-48c1-91ad-93c4104e791d / http://data.europa.eu/esco/occupation/0611f232-b30e-46c7-9c26-2d59b1448e79 / http://data.europa.eu/esco/occupation/0959cd1d-f6c8-4362-939a-ad7d5f75d659 | No direct related property exists |
| preferredLabel | 100.0% | biomedical engineer / criminologist / economics lecturer | The preferred lexical label for a resource, in a given language. |
| status | 100.0% | released | ISO status - on ThesaurusConcept - on ThesaurusTerm |
| altLabels | 100.0% | biomedical technology engineering specialist | biomedical technology engineering consultant | BME consultant | BME specialist | BME expert | biomedical technolo / criminology scientist | criminology research scientist | criminology studies scientist | criminology studies research scientist | criminology researcher | crimi / economics professor | university lecturer in economics | lecturer in economics | senior lecturer in economics | lecturer of economics | university economics lec | An alternative lexical label for a resource. |
| description | 100.0% | Biomedical engineers combine knowledge of engineering principles and biological findings for the development of medical treatments, medicaments, and general hea / Criminologists study conditions pertaining to humans such as the social and psychological aspects that could lead them to commit criminal acts. They observe and / Economics lecturers are subject professors, assistant professors, teachers, lectures, assistant lecturers, mentors who instruct students in their own specialise | An account of the resource. |
| broaderConceptUri | 100.0% | http://data.europa.eu/esco/occupation/f9433fdb-dde1-46cf-9e91-b49d243946a7 / http://data.europa.eu/esco/isco/C2632 / http://data.europa.eu/esco/occupation/684fd8d5-9b40-4b02-a680-438f0082d923 | No direct related property exists |
| broaderConceptPT | 100.0% | bioengineer / Sociologists, anthropologists and related professionals / higher education lecturer | The preferred lexical label for a resource, in a given language. |

### researchSkillsCollection_en.csv
- role: collection
- rows: 40
- columns: 10
- description: Thematic subset of ESCO concepts for a domain-specific use case.
- primary_key_candidates: conceptUri
- uri_columns: conceptUri, broaderConceptUri
- label_columns: preferredLabel, altLabels

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| conceptType | 100.0% | KnowledgeSkillCompetence | No direct related property exists |
| conceptUri | 100.0% | http://data.europa.eu/esco/skill/00b9a3aa-7070-4bb5-8020-f228a97cf42f / http://data.europa.eu/esco/skill/08b04e53-ed25-41a2-9f90-0b9cd939ba3d / http://data.europa.eu/esco/skill/20a8fe89-d4eb-4698-8521-8881c13377e0 | No direct related property exists |
| preferredLabel | 100.0% | draft scientific or academic papers and technical documentation / manage research data / interact professionally in research and professional environments | The preferred lexical label for a resource, in a given language. |
| status | 100.0% | released | ISO status - on ThesaurusConcept - on ThesaurusTerm |
| skillType | 100.0% | skill/competence | Type of competence (a tagging concept) |
| reuseLevel | 100.0% | cross-sector / sector-specific / transversal | Reuseability level of a skill |
| altLabels | 100.0% | create technical documentation | create technical documentation and academic writings | write technical documentation | write scientific and academic papers / oversee scientific data | handle research data | administer research data / give feedback in a professional setting | interact appropriately in research and professional spheres | receive feedback in a professional setting | interact co | An alternative lexical label for a resource. |
| description | 100.0% | Draft and edit scientific, academic or technical texts on different subjects. / Produce and analyse scientific data originating from qualitative and quantitative research methods. Store and maintain the data in research databases. Support t / Show consideration to others as well as collegiality. Listen, give and receive feedback and respond perceptively to others, also involving staff supervision and | An account of the resource. |
| broaderConceptUri | 100.0% | http://data.europa.eu/esco/skill/6e62e776-fbfa-486c-a6df-58cd239c86fe / http://data.europa.eu/esco/skill/32c017fd-28ab-4051-bf68-74de952c2f77 / http://data.europa.eu/esco/skill/91b0b918-942e-4661-b88c-70b9396529e5 | No direct related property exists |
| broaderConceptPT | 100.0% | technical or academic writing / managing information / working with others | The preferred lexical label for a resource, in a given language. |

### skillGroups_en.csv
- role: taxonomy_group
- rows: 640
- columns: 11
- description: Taxonomy grouping table used as parent categories or classification levels.
- primary_key_candidates: conceptUri
- uri_columns: conceptUri
- label_columns: preferredLabel, altLabels, hiddenLabels

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| conceptType | 100.0% | SkillGroup | No direct related property exists |
| conceptUri | 100.0% | http://data.europa.eu/esco/isced-f/00 / http://data.europa.eu/esco/isced-f/000 / http://data.europa.eu/esco/isced-f/0000 | No direct related property exists |
| preferredLabel | 100.0% | generic programmes and qualifications / generic programmes and qualifications not further defined / basic programmes and qualifications | The preferred lexical label for a resource, in a given language. |
| altLabels | 17.5% | self-discipline self-management self-control self-regulation professional attitude / installing and maintaining mechanical equipment / working with others acting with others to achieve aims | An alternative lexical label for a resource. |
| hiddenLabels | 2.7% | professional orientation and perfection demonstrate self-management professional way of working self-discipline self-conquest / good sense of pressure and touch good sense of taste speed good sense of touch athletic performance climb good sense of hearing reaction time dynamic flexibilit / solution-oriented approach solution and process-oriented thinking | A lexical label for a resource that should be hidden when generating visual displays of the resource, but should still be accessible to free text search operations. |
| status | 100.0% | released | ISO status - on ThesaurusConcept - on ThesaurusTerm |
| modifiedDate | 53.0% | 2023-07-13T15:16:44.968Z / 2023-07-04T13:43:35.384Z / 2024-07-03T13:25:01.639Z | Date on which the resource was changed. |
| scopeNote | 50.6% | Examples: - escort students on a field trip - supervise special visitors Excludes: - assist clients with special needs. / Examples: - Follow trends in sporting equipment - Keep up to date with diagnostic innovations - Monitor legislation developments - Monitor technology trends. / Excludes: - Installing, maintaining and repairing mechatronic or robotic equipment and components. | A note that helps to clarify the meaning and/or the use of a concept. |
| inScheme | 100.0% | http://data.europa.eu/esco/concept-scheme/skills http://data.europa.eu/esco/concept-scheme/skills-hierarchy http://data.europa.eu/esco/concept-scheme/isced-f / http://data.europa.eu/esco/concept-scheme/skills http://data.europa.eu/esco/concept-scheme/skills-hierarchy / http://data.europa.eu/esco/concept-scheme/skills http://data.europa.eu/esco/concept-scheme/skills-hierarchy http://data.europa.eu/esco/concept-scheme/skill-tran | Relates a resource (for example a concept) to a concept scheme in which it is included. |
| description | 79.2% | Generic programmes and qualifications are those providing fundamental and personal skills education which cover a broad range of subjects and do not emphasise o / Basic programmes and qualifications are designed to provide participants with fundamental skills in reading, writing and arithmetic along with an elementary und / Literacy and numeracy are programmes or qualifications arranged mainly for adults, designed to teach fundamental skills in reading, writing and arithmetic. The  | An account of the resource. |
| code | 100.0% | 00 / 000 / 0000 | A notation, also known as classification code, is a string of characters such as "T58.5" or "303.4833" used to uniquely identify a concept within the scope of a given concept scheme. |

### skills_en.csv
- role: core_concept
- rows: 13960
- columns: 13
- description: Primary concept table containing normalized occupation or skill records.
- primary_key_candidates: conceptUri
- uri_columns: conceptUri
- label_columns: preferredLabel, altLabels, hiddenLabels

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| conceptType | 100.0% | KnowledgeSkillCompetence | No direct related property exists |
| conceptUri | 100.0% | http://data.europa.eu/esco/skill/0005c151-5b5a-4a66-8aac-60e734beb1ab / http://data.europa.eu/esco/skill/00064735-8fad-454b-90c7-ed858cc993f2 / http://data.europa.eu/esco/skill/000709ed-2be5-4193-b056-45a97698d828 | No direct related property exists |
| skillType | 100.0% | skill/competence / knowledge | Type of competence (a tagging concept) |
| reuseLevel | 100.0% | sector-specific / occupation-specific / cross-sector | Reuseability level of a skill |
| preferredLabel | 100.0% | manage musical staff / supervise correctional procedures / apply anti-oppressive practices | The preferred lexical label for a resource, in a given language. |
| altLabels | 99.9% | manage music staff coordinate duties of musical staff direct musical staff manage staff of music / manage prison procedures monitor correctional procedures oversee prison procedures oversee correctional procedures manage correctional procedures monitor prison / make use of anti-oppressive practices use anti-oppressive practices apply non-oppressive practices apply anti-oppresive practice identify oppression in societie | An alternative lexical label for a resource. |
| hiddenLabels | 1.1% | active participation activity initiative great initiative self starter / KDevelop 4.7.0 KDevelop 4.6.0 KDevelop 5.0.0 KDevelop 4.0.0 / think about biodiversity eat bio aim for a vegan diet | A lexical label for a resource that should be hidden when generating visual displays of the resource, but should still be accessible to free text search operations. |
| status | 100.0% | released | ISO status - on ThesaurusConcept - on ThesaurusTerm |
| modifiedDate | 100.0% | 2023-11-30T15:53:37.136Z / 2023-11-30T15:04:00.689Z / 2023-11-28T10:45:53.54Z | Date on which the resource was changed. |
| scopeNote | 1.7% | It includes building stone, sand, bricks, clay and gravel. / It includes safe working considerations, animal assessment and handling. Principles and aims of first aid treatment, common conditions and injuries, and appropr / Excludes <a resource="http://data.europa.eu/esco/skill/699e7c26-6502-4e78-a823-3656ff5a5b8b" typeOf="http://data.europa.eu/esco/model#Skill" href="http://data.e | A note that helps to clarify the meaning and/or the use of a concept. |
| definition | 0.0% | Bilingual examination of target language content against source language content for its suitability for the agreed purpose (ISO 17100). / Monolingual examination of target language content for its suitability for the agreed purpose (ISO 17100). | A statement or formal explanation of the meaning of a concept. |
| inScheme | 100.0% | http://data.europa.eu/esco/concept-scheme/skills, http://data.europa.eu/esco/concept-scheme/member-skills / http://data.europa.eu/esco/concept-scheme/skills, http://data.europa.eu/esco/concept-scheme/member-skills, http://data.europa.eu/esco/concept-scheme/6c930acd-c1 / http://data.europa.eu/esco/concept-scheme/skills, http://data.europa.eu/esco/concept-scheme/member-skills, http://data.europa.eu/esco/concept-scheme/skill-trans | Relates a resource (for example a concept) to a concept scheme in which it is included. |
| description | 100.0% | Assign and manage staff tasks in areas such as scoring, arranging, copying music and vocal coaching. / Supervise the operations of a correctional facility or other correctional procedures, ensuring that they are compliant with legal regulations, and ensure that t / Identify oppression in societies, economies, cultures, and groups, acting as a professional in an non-oppressive way, enabling service users to take action to i | An account of the resource. |

### skillsHierarchy_en.csv
- role: hierarchy
- rows: 640
- columns: 14
- description: Precomputed hierarchy view for navigating multi-level skill groups.
- uri_columns: Level 0 URI, Level 1 URI, Level 2 URI, Level 3 URI

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| Level 0 URI | 100.0% | http://data.europa.eu/esco/skill/e35a5936-091d-4e87-bafe-f264e55bd656 / http://data.europa.eu/esco/skill/335228d2-297d-4e0e-a6ee-bc6a8dc110d9 / http://data.europa.eu/esco/skill/04a13491-b58c-4d33-8b59-8fad0d55fe9e | No direct related property exists |
| Level 0 preferred term | 100.0% | language skills and knowledge / skills / transversal skills and competences | The preferred lexical label for a resource, in a given language. |
| Level 1 URI | 99.4% | http://data.europa.eu/esco/skill/43f425aa-f45d-4bb4-a200-6f82fa211b66 / http://data.europa.eu/esco/skill/e434e71a-f068-44ed-8059-d1af9eb592d7 / http://data.europa.eu/esco/skill/03e0b95b-67d1-457a-b3f7-06c407cf6bec | No direct related property exists |
| Level 1 preferred term | 99.4% | languages / classical languages / handling and moving | The preferred lexical label for a resource, in a given language. |
| Level 2 URI | 95.0% | http://data.europa.eu/esco/skill/15dfca7a-5dde-4199-bad3-c00600387258 / http://data.europa.eu/esco/skill/1cc5ff0b-afaa-4993-9de7-ab0d77b6cca2 / http://data.europa.eu/esco/skill/1d9e5893-d6b2-47b1-80ba-5f1cdcbf5e9a | No direct related property exists |
| Level 2 preferred term | 95.0% | handling and disposing of waste and hazardous materials / moving and lifting / making moulds, casts, models and patterns | The preferred lexical label for a resource, in a given language. |
| Level 3 URI | 70.6% | http://data.europa.eu/esco/skill/61d1dab2-6007-4b7c-9380-cd88207fa30f / http://data.europa.eu/esco/skill/8bde58aa-9d5b-422b-801c-ff9186dd648e / http://data.europa.eu/esco/skill/f8c676de-c871-424f-9a65-77059d07910a | No direct related property exists |
| Level 3 preferred term | 70.6% | disposing of non-hazardous waste or debris / handling and disposing of hazardous materials / handling and disposing of waste and hazardous materials | The preferred lexical label for a resource, in a given language. |
| Description | 79.2% | Ability to communicate through reading, writing, speaking and listening in the mother tongue and/or in a foreign language. / All dead languages, no longer actively used, originating from various periods in history, such as Latin from Antiquity, Middle English from the Middle Ages, Cla / Sorting, arranging, moving, transforming, fabricating and cleaning goods and materials by hand or using handheld tools and equipment. Tending plants, crops and  | An account of the resource. |
| Scope note | 50.6% | Excludes: - all languages that are actively used as a mother tongue or lingua franca Latin, Sanskrit, Ancient Greek. / Excludes: - Specific skills involving interaction with people. / Examples: - Handle fish harvesting waste - Collect domestic waste. | A note that helps to clarify the meaning and/or the use of a concept. |
| Level 0 code | 100.0% | L / S / T | A notation, also known as classification code, is a string of characters such as "T58.5" or "303.4833" used to uniquely identify a concept within the scope of a given concept scheme. |
| Level 1 code | 99.4% | L1 / L2 / S6 | A notation, also known as classification code, is a string of characters such as "T58.5" or "303.4833" used to uniquely identify a concept within the scope of a given concept scheme. |
| Level 2 code | 95.0% | S6.13 / S6.2 / S6.6 | A notation, also known as classification code, is a string of characters such as "T58.5" or "303.4833" used to uniquely identify a concept within the scope of a given concept scheme. |
| Level 3 code | 70.6% | S6.13.2 / S6.13.1 / S6.13.0 | A notation, also known as classification code, is a string of characters such as "T58.5" or "303.4833" used to uniquely identify a concept within the scope of a given concept scheme. |

### skillSkillRelations_en.csv
- role: relation
- rows: 5818
- columns: 5
- description: Edge table connecting concepts to broader concepts or related concepts.
- uri_columns: originalSkillUri, relatedSkillUri

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| originalSkillUri | 100.0% | http://data.europa.eu/esco/skill/00064735-8fad-454b-90c7-ed858cc993f2 / http://data.europa.eu/esco/skill/000bb1e4-89f0-4b86-be05-05ece3641724 / http://data.europa.eu/esco/skill/0023e7a5-43da-4b68-bee3-726ef21f986d | No direct related property exists |
| originalSkillType | 100.0% | skill/competence / knowledge | Type of competence (a tagging concept) |
| relationType | 100.0% | optional / essential | The ESCO skill or competence that is relevant (but optional) for the subject occuption. | The ESCO skill or competence that is essential for the subject occupation or skill. |
| relatedSkillType | 100.0% | knowledge / skill/competence | Type of competence (a tagging concept) |
| relatedSkillUri | 100.0% | http://data.europa.eu/esco/skill/d4a0744a-508b-4a5e-97a5-ad1fc7f55e6e / http://data.europa.eu/esco/skill/b70ab677-5781-40b5-9198-d98f4a34310f / http://data.europa.eu/esco/skill/5753e2ca-8934-45d3-8e52-3877d373239d | No direct related property exists |

### transversalSkillsCollection_en.csv
- role: collection
- rows: 95
- columns: 10
- description: Thematic subset of ESCO concepts for a domain-specific use case.
- primary_key_candidates: conceptUri
- uri_columns: conceptUri, broaderConceptUri
- label_columns: preferredLabel, altLabels

| column | fill_ratio | sample_values | description |
|---|---:|---|---|
| conceptType | 100.0% | KnowledgeSkillCompetence | No direct related property exists |
| conceptUri | 100.0% | http://data.europa.eu/esco/skill/001115fb-569f-4ee6-8381-c6807ef2527f / http://data.europa.eu/esco/skill/0171653e-c8e9-4c24-bb86-a4b6fe038f25 / http://data.europa.eu/esco/skill/045f71e6-0699-4169-8a54-9c6b96f3174d | No direct related property exists |
| skillType | 100.0% | skill/competence | Type of competence (a tagging concept) |
| reuseLevel | 100.0% | transversal / cross-sector | Reuseability level of a skill |
| preferredLabel | 100.0% | show initiative / adopt ways to foster biodiversity and animal welfare / advise others | The preferred lexical label for a resource, in a given language. |
| status | 100.0% | released | ISO status - on ThesaurusConcept - on ThesaurusTerm |
| altLabels | 100.0% | initiate action | be a driving force | give impetus | take the initiative | show sense of initiative | show active initiative | demonstrate sense of initiative / concretely support biodiversity and animal welfare | implement environmental choices in your own eating habit | adopt a sustainable eating habit | take sustaina / mentor others | mentor individuals | counsel others | counselling | offer suggestions to others | guide others | make recommendations to others | give advice |  | An alternative lexical label for a resource. |
| description | 100.0% | Be proactive and take the first step in an action without waiting for what others say or do. / Engage in behaviours that help maintaining stable ecosystems and combatting mass extinction, for example by making conscious dietary choices that support organi / Offer suggestions about the best course of action. | An account of the resource. |
| broaderConceptUri | 100.0% | http://data.europa.eu/esco/skill/91860993-1a8b-4473-91f3-600aa1924bd0 / http://data.europa.eu/esco/skill/80cf002a-6586-4db7-9c9a-88325a9a5e1b / http://data.europa.eu/esco/skill/82463bb1-85d1-4e99-a4ce-08508fc3b2a3 | No direct related property exists |
| broaderConceptPT | 100.0% | taking a proactive approach / applying environmental skills and competences / supporting others | The preferred lexical label for a resource, in a given language. |
