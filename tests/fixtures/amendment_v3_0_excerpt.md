<!-- TEST FIXTURE of the pipeline test suite. Section 4 below is Protocol Amendment v3.0 as drafted on
30 September 2026, verbatim. The panel table at the end is the table that scripts/gbd_panel.py generates for
the synthetic panel of the test suite (tests/fixtures/gbd_panel_fixture.yaml). This file is not the amendment:
the release check runs against docs/AMENDMENT_v3_0.md, the amendment as submitted with the OSF update. -->

## 4. Change 3: query catalogue extension (addition to Q12.6)

Composition rule of Q12.2 unchanged: character-level concatenation, left-to-right Boolean evaluation, parentheses exactly as shown, year clause always last, "Humans"[Mesh] and the year as separate clauses. {F} is a field expression of Q12.3; {HEADING} one of the 21 panel headings of Q12.5; {G} one of the 20 GBD descriptors of Section 5; AI denotes "Artificial Intelligence"[Mesh]; AI_TIAB_TERMS denotes ("artificial intelligence"[tiab] OR "machine learning"[tiab] OR "deep learning"[tiab] OR "neural network"[tiab] OR "neural networks"[tiab]); (...) the year clause ("YYYY"[pdat]). "The same with RCT" means the identical string with AND "Randomized Controlled Trial"[pt] inserted before the year clause. Windows: 2015 to 2024 for all fields except COVID (2020 to 2024).

| Family | Use | Template | Fields |
|--------|-----|----------|--------|
| DB | overlap RCT numerators (P, S2, E16) | {F} AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND (...) | nine comparators |
| DC | overlap Clinical Trial numerators (S4) | {F} AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND "Clinical Trial"[pt] AND (...) | nine comparators |
| MD | panel overlap (S9, S11) | {HEADING} AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND (...); the same with RCT | 21 headings |
| ME | panel disjoint sets (S9) | ({HEADING} NOT "Artificial Intelligence"[Mesh]) AND "Humans"[Mesh] AND (...); the same with RCT | 21 headings |
| GA | GBD denominators and RCT numerators (S10) | {G} AND "Humans"[Mesh] AND (...); the same with RCT | 20 GBD descriptors |
| GD | GBD overlap (S10, S11) | {G} AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND (...); the same with RCT | 20 GBD descriptors |
| GE | GBD disjoint sets (S10) | ({G} NOT "Artificial Intelligence"[Mesh]) AND "Humans"[Mesh] AND (...); the same with RCT | 20 GBD descriptors |
| DV | STROKE within-field on alternative AI definitions (E1, E2, D19) | "Stroke"[Mesh] AND {F_AI_VOCAB2015} AND "Humans"[Mesh] AND (...); ("Stroke"[Mesh] NOT {F_AI_VOCAB2015}) AND "Humans"[Mesh] AND (...); "Stroke"[Mesh] AND medline[sb] AND {AI_TIAB_TERMS} AND "Humans"[Mesh] AND (...); ("Stroke"[Mesh] AND medline[sb] NOT {AI_TIAB_TERMS}) AND "Humans"[Mesh] AND (...); each the same with RCT | STROKE |
| QV | STROKE within-field on the unrestricted base (E10) | "Stroke"[Mesh] AND "Artificial Intelligence"[Mesh] AND (...); ("Stroke"[Mesh] NOT "Artificial Intelligence"[Mesh]) AND (...); each the same with RCT | STROKE |
| WV | STROKE within-field, Robotics-excluded AI subset (E13) | "Stroke"[Mesh] AND ("Artificial Intelligence"[Mesh] NOT "Robotics"[Mesh]) AND "Humans"[Mesh] AND (...); the same with RCT | STROKE |
| KV | STROKE within-field on the original-research base (E5) | "Stroke"[Mesh] AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] NOT (Review[pt] OR Editorial[pt] OR Letter[pt] OR Comment[pt] OR News[pt]) AND (...); ("Stroke"[Mesh] NOT "Artificial Intelligence"[Mesh]) AND "Humans"[Mesh] NOT (Review[pt] OR Editorial[pt] OR Letter[pt] OR Comment[pt] OR News[pt]) AND (...); each the same with RCT inserted before the year clause | STROKE |
| JV | STROKE within-field, protocol-excluded numerators (E6) | "Stroke"[Mesh] AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] NOT "Clinical Trial Protocol"[pt] AND (...); ("Stroke"[Mesh] NOT "Artificial Intelligence"[Mesh]) AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] NOT "Clinical Trial Protocol"[pt] AND (...) | STROKE |
| RS | strata within STROKE by AI status (S7, D22), 2024 only, counts and PMID lists | S_STROKE_AI: "Stroke"[Mesh] AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND medline[sb] AND (randomized[tiab] OR randomised[tiab] OR randomly[tiab] OR placebo[tiab] OR trial[ti]) NOT "Randomized Controlled Trial"[pt] AND (...); S_STROKE_nonAI: ("Stroke"[Mesh] NOT "Artificial Intelligence"[Mesh]) AND "Humans"[Mesh] AND medline[sb] AND (randomized[tiab] OR randomised[tiab] OR randomly[tiab] OR placebo[tiab] OR trial[ti]) NOT "Randomized Controlled Trial"[pt] AND (...) | STROKE, 2024 |
| LV | PMID lists (validation cells of D22, S8) | the family DB string for STROKE and the family E RCT string for STROKE, 2024; the two family RS strings; esearch with retmax and retstart, or usehistory=y above 10,000 | STROKE, 2024 |

Worked verbatim examples (STROKE, 2024):
- Family DB: "Stroke"[Mesh] AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2024"[pdat])
- Family E, RCT (registered): ("Stroke"[Mesh] NOT "Artificial Intelligence"[Mesh]) AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2024"[pdat])
- Family D (registered): "Stroke"[Mesh] AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND ("2024"[pdat])
- Family MD, heading Neoplasms: "Neoplasms"[Mesh] AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND ("2024"[pdat])
- Family GE, RCT, descriptor Diabetes Mellitus: ("Diabetes Mellitus"[Mesh] NOT "Artificial Intelligence"[Mesh]) AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2024"[pdat])

Approximate additional volume: DB and DC about 170 requests; MD and ME 840; GA, GD and GE up to 1,200 (cells identical to registered strings are reused, not re-queried); DV 80; QV 40; WV 20; KV 40; JV 20; RS 2; total about 2,400 additional count requests, so about 4,600 per run, completed within about ten minutes at 10 requests per second. Family letters remain distinct from endpoint labels; two-letter codes are used for all new families.

Derived variables (addition to Q12.9): for a field F and year y, within-field share of the AI subset p_AI = DB / D (for panels MD-RCT / MD; for GBD GD-RCT / GD), within-field share of the complement p_nonAI = E-RCT / E (ME-RCT / ME; GE-RCT / GE), PR_within = p_AI / p_nonAI, absolute difference (p_AI minus p_nonAI) in percentage points, AI penetration D / A (MD / M; GD / GA), and the consistency residuals of E16.

---

## 5. GBD panel (table of the synthetic test panel)

5.7 GBD panel (final).
The 20 GBD 2023 Level 3 causes of the panel in rank order of global DALY counts 2023, selected by the rule of 5.2 and mapped by the rule of 5.3 by WP and IE. The query expression is used verbatim as {G} in families GA, GD and GE. Members that coincide with a named field share its registered cells and are not queried again. Descriptors introduced after 2015 enter 2024 and the pooled windows only (panel rule of Q13). Scope relation: exact, broader or narrower than the GBD cause, or mixed where over- and under-inclusion are both stated.

| Rank 2023 | GBD Level 3 cause | Query expression (verbatim) | MeSH UI | Introduced | Scope relation | Stated over- or under-inclusion | Cells |
|---|---|---|---|---|---|---|---|
| 1 | Ischemic heart disease | "Myocardial Ischemia"[Mesh] | D017202 | 1993 | exact | Contains the named field Myocardial Infarction (MI), which stays a separate comparator. | queried |
| 2 | Neonatal disorders | "Infant, Newborn, Diseases"[Mesh] | D007232 | 1966 | broader | Narrowest heading that contains preterm-birth complications, birth asphyxia, neonatal sepsis and neonatal jaundice. Over-inclusion: hereditary conditions filed under this heading, above all Cystic Fibrosis (tree number C16.614.213), also Ichthyosis and Severe Combined Immunodeficiency. | queried |
| 3 | Stroke | "Stroke"[Mesh] | D020521 | 2000 | exact | Named field STROKE; cells are shared with the registered families, not queried again. | shared with STROKE |
| 4 | Lower respiratory infections | ("Pneumonia"[Mesh] NOT "COVID-19"[Mesh]) | D011014 NOT D000086382 | 1963 | narrower | COVID-19 (D000086382, introduced 2021, applied back to 2020) is a child of Pneumonia, Viral. The exploded Pneumonia heading therefore contains the COVID-19 literature from 2020 on, although GBD counts COVID-19 as a separate cause and COVID is a named field of this study. Removing it keeps the series comparable before and after 2020. Under-inclusion: bronchiolitis and acute bronchitis are not covered. Records on other pneumonia that also carry the COVID-19 heading are lost. | queried |
| 5 | Diabetes mellitus | "Diabetes Mellitus"[Mesh] | D003920 | 1966 | exact | Named field DM; cells are shared with the registered families, not queried again. | shared with DM |
| 7 | Chronic obstructive pulmonary disease | "Pulmonary Disease, Chronic Obstructive"[Mesh] | D029424 | 2002 | exact |  | queried |
| 9 | Low back pain | "Low Back Pain"[Mesh] | D017116 | 1993 | exact |  | queried |
| 10 | Diarrheal diseases | "Diarrhea"[Mesh] | D003967 | 1966 | mixed | Symptom heading. Over-inclusion: non-infectious diarrhoea (for example drug-induced). Under-inclusion: records indexed only under a pathogen-specific heading (for example cholera or rotavirus infections). | queried |
| 11 | Depressive disorders | "Depressive Disorder"[Mesh] | D003866 | 1981 | exact | Under-inclusion: records indexed only under the separate heading Depression (symptom or behaviour) are not included (MeSH annotation: do not confuse with DEPRESSION). | queried |
| 12 | Anxiety disorders | "Anxiety Disorders"[Mesh] | D001008 | 1981 | exact |  | queried |
| 13 | Congenital birth defects | "Congenital Abnormalities"[Mesh] | D000013 | 2008 | exact | History note 2008 (1963): the heading was named Abnormalities until 2007; it exists for the whole study window. | queried |
| 14 | Age-related and other hearing loss | "Hearing Loss"[Mesh] | D034381 | 2003 | broader | Over-inclusion: hearing loss of every cause, including causes that GBD assigns elsewhere. | queried |
| 15 | Malaria | "Malaria"[Mesh] | D008288 | 1960 | exact |  | queried |
| 16 | Tracheal, bronchus, and lung cancer | "Lung Neoplasms"[Mesh] | D008175 | 1966 | mixed | Under-inclusion: tracheal neoplasms are not covered. Over-inclusion: malignant mesothelioma (a separate GBD cause) and pulmonary nodules are filed under this heading. | queried |
| 17 | Chronic kidney disease | "Renal Insufficiency, Chronic"[Mesh] | D051436 | 2006 | exact |  | queried |
| 18 | Headache disorders | "Headache Disorders"[Mesh] | D020773 | 2000 | broader | Over-inclusion: secondary headache disorders. Under-inclusion: records indexed only under the symptom heading Headache. | queried |
| 20 | HIV/AIDS | "HIV Infections"[Mesh] | D015658 | 1990 | exact |  | queried |
| 21 | Tuberculosis | "Tuberculosis"[Mesh] | D014376 | 1960 | exact | Includes latent tuberculosis. | queried |
| 22 | Cirrhosis and other chronic liver diseases | "Liver Cirrhosis"[Mesh] | D008103 | 1960 | narrower | Core entity of the cause. Under-inclusion: chronic liver disease without cirrhosis (for example fatty liver disease, chronic hepatitis, alcoholic liver disease other than cirrhosis). | queried |
| 23 | Synthetic cause (test fixture) | "Synthetic Heading After 2015"[Mesh] | D999999 | 2019 | exact | Synthetic row of the test suite: a descriptor introduced after 2015. | queried; 2024 and pooled windows only |

Causes ranked above the last panel member that are not in the panel: not stated (no ranking file).

Catalogue volume with this panel: 2,292 additional count requests, 4,326 per run.
