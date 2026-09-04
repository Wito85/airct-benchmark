# Preregistration v2.0

## Randomized trial share of medical artificial intelligence literature benchmarked against established clinical fields

**OSF template:** Preregistration for Studies with Existing Data (Secondary Data Preregistration; van den Akker O, Weston S, Campbell L, et al. Preregistration of secondary data analysis: a template and tutorial. Meta-Psychology 2021;5:2625, DOI 10.15626/MP.2020.2625). Items Q1 to Q25, Statement of Integrity, and an "Other" block for availability, timeline, reporting and governance. Each Q block is pasted into the matching OSF field; the Metadata block is filled in the OSF submission form.

**Version and provenance:** v2.0, prepared 4 September 2026 by W. Polanski with AI assistance (see Other, AI use). Merges Study Concept v1.1 (4 September 2026; decisions D1 to D20) and the merge decisions M1 to M10 of the project status file into the draft of 3 September 2026. Field expressions, the RCT numerator and the review and primary-article expressions are character-identical to the draft; the prior-knowledge disclosure in Q18 is carried over verbatim.

**Registration status:** registered on 4 September 2026 (the OSF registration timestamp is authoritative). The definitive data retrieval (freeze run) takes place strictly after the OSF registration timestamp, on Monday 12 October 2026.

**Conventions:** Year ranges are written "2015 to 2024". "Record" means a PubMed record. Endpoint labels P, S1 to S9 and E1 to E15 are used throughout this document and in every table and figure of the manuscript. F* denotes a field expression combined with the check tag "Humans"[Mesh].

---

### METADATA (common OSF block)

**Title:** Randomized trial share of medical artificial intelligence literature benchmarked against established clinical fields

**Description:** Cross-sectional bibliometric meta-research study of PubMed record counts retrieved through NCBI E-utilities. Among human-subject records published 2015 to 2024, the study compares the share of records carrying the Randomized Controlled Trial publication type in the literature indexed under Artificial Intelligence with that of stroke (primary comparator), diabetes mellitus, myocardial infarction and cardiovascular diseases, with two young-field controls (COVID-19, mobile applications), with two technology comparators matched on function and task (clinical decision support systems, diagnostic imaging) and one exploratory technology comparator (telemedicine), and positions AI within complete reference distributions of 21 disease categories and 9 health-technology fields. A validation substudy and an enriched-stratum study estimate the precision and the sensitivity of the RCT tag in AI and stroke, yielding tag-corrected and validation-adjusted estimates; trial registration identifiers deduplicate the numerator to the trial level. One confirmatory contrast (AI versus stroke, 2024, prevalence ratio with 95% confidence interval), verbatim query strings, a single retrieval date, a frozen dataset, and independent same-day reproduction.

**Contributors:** Markus Georg Prem; Sven Richter; Clara Helene Buszello; Sophia Willkommen; Youssef Hachem; Nargiz Abdullayeva; Ilker Y. Eyüpoglu; Witold Polanski.

**License:** CC-BY 4.0 (preregistration, documents and data); the code is released under the MIT License.

**Subjects and tags:** meta-research; bibliometrics; artificial intelligence; evidence-based medicine; PubMed; randomized controlled trials; publication types.

---

### SECTION 1: STUDY INFORMATION

**Q1. Title.**
Randomized trial share of medical artificial intelligence literature benchmarked against established clinical fields.

The working title meets the format of the primary target journal (up to 15 words, no punctuation). The manuscript title may be shortened within the same constraint; the registered title identifies the study.

**Q2. Authors.**
In final byline order: (1) Markus Georg Prem (first author; pipeline lead; validation rater; manuscript first draft with Polanski), ORCID 0009-0005-9888-1380; (2) Sven Richter (second rater for the U-cells, see Q24), ORCID 0000-0003-1648-5754; (3) Clara Helene Buszello (independent reproduction), ORCID 0009-0008-8230-1064; (4) Sophia Willkommen (second rater for the U-cells), ORCID 0009-0003-8993-7720; (5) Youssef Hachem (independent reproduction), ORCID to be linked in the OSF contributor profile; (6) Nargiz Abdullayeva, ORCID to be linked in the OSF contributor profile; (7) Ilker Y. Eyüpoglu (adjudicator of all validation cells), ORCID 0000-0002-8185-7764; (8) PD Dr. med. habil. Witold Polanski (senior author, corresponding author, guarantor; statistical analysis plan; validation rater), ORCID 0000-0002-6603-5375. Affiliation of all authors: Department of Neurosurgery, Faculty of Medicine and University Hospital Carl Gustav Carus, Technische Universität Dresden, Dresden, Germany. CRediT roles are listed under Other. This preregistration concerns a secondary analysis of existing PubMed metadata; prior contact of the authors with the data source is disclosed in Q17 and Q18.

**Q3. Research questions.**
- RQ1 (primary, confirmatory). Among PubMed records on human subjects published in 2024, is the proportion of records carrying the Randomized Controlled Trial publication type lower in records indexed under Artificial Intelligence than in records indexed under Stroke?
- RQ2 (key secondary). Has the AI versus Stroke gap narrowed or widened between 2015 and 2024, and is any change driven by the numerator (RCT-tagged records) or by the denominator (all records)?
- RQ3 (secondary). How does the AI RCT share compare with the disease comparators Diabetes Mellitus, Myocardial Infarction and Cardiovascular Diseases?
- RQ4 (secondary). How does the AI RCT share compare with the function-matched and task-matched technology fields Decision Support Systems, Clinical and Diagnostic Imaging?
- RQ5 (secondary). Does the deficit persist when the outcome is any clinical trial publication type rather than the RCT type alone?
- RQ6 (secondary, validation-based). What fraction of RCT-tagged AI records report a genuine RCT, a primary rather than a secondary analysis, and an AI system as the intervention under randomized comparison, and how does the adjusted AI share compare with Stroke?
- RQ7 (secondary, young fields). How does the AI RCT share compare with two young fields of different kind, the disease field COVID-19 and the technology field Mobile Applications?
- RQ8 (secondary, tag-corrected). Does the AI versus Stroke contrast persist after correcting the RCT count in each field for false-positive tags and for untagged RCT reports?
- RQ9 (secondary, trial-level). How many distinct registered trials underlie the RCT-tagged records in AI and Stroke, and does the contrast persist at the trial level?
- RQ10 (secondary, reference distributions). Where does AI rank among all major disease categories and among a predefined panel of health-technology fields?
- RQ11 (exploratory). Are the results robust to the definition of the AI denominator (unrestricted record base, vocabulary-stable descriptor set, text words, original-research records, disease-related subset, exclusion of the Robotics subtree), to overlap between fields, to exclusion of protocol records, to the indexing era, and to within-day database volatility; and how does the composition of each field's literature (review-to-primary-article ratio) develop over time?

**Q4. Hypotheses.**
Statistical framework: frequentist estimation with 95% confidence intervals and exactly one confirmatory test (decision D8). All research questions other than RQ1 are answered by estimation and are labelled secondary or exploratory in every table and every sentence; no hypothesis is attached to them and no significance language is used for them.

- H1 (primary, confirmatory, directional). Among human-subject PubMed records published in 2024, the prevalence ratio PR = p(AI, 2024) / p(Stroke, 2024) of the RCT share is below 1, where p is the proportion of records of a field that carry the Randomized Controlled Trial publication type. Rationale: systematic and scoping reviews of AI trials report that randomized trials form a very small fraction of the AI literature (Lam et al., J Med Internet Res 2022;24:e37188; npj Digital Medicine 2026, DOI 10.1038/s41746-026-02698-z; Lancet Digital Health 2024, PIIS2589-7500(24)00047-5), whereas stroke is an established interventional field with a mature randomized-trial infrastructure in acute therapy, secondary prevention and rehabilitation.

Note on confirmatory value. Aggregate counts for AI and Stroke on the unrestricted record base were inspected during study conception (Q18). The direction of H1 is therefore expected; the informative quantities are the magnitude of the prevalence ratio on the human-subject record base, its trajectory 2015 to 2024, and the corrected, adjusted and trial-level versions of the contrast. The former secondary hypothesis of the draft (AI versus COVID-19) is answered by estimation as endpoint S6 and is no longer formulated as a hypothesis.

---

### SECTION 2: DATA DESCRIPTION

**Q5. Dataset.**
The data source is PubMed (National Library of Medicine), accessed programmatically through NCBI E-utilities: esearch (db=pubmed) for record counts and PMID lists, and efetch (db=pubmed, retmode=xml) for the XML of the records that enter the validation and trial-level components. The dataset of this study is created by the authors' pipeline on a single retrieval date and frozen. It consists of aggregate counts per field, metric and publication year (main analyses), PMID lists for the validation strata, and efetch XML for all RCT-tagged AI and Stroke records of 2024 and for the sampled records of the enriched and remainder strata. The unit of analysis is the PubMed record; main outcomes are shares of records within a field-year; the trial level is reached for the numerator through registration-identifier deduplication (endpoint S8). The record base of all main analyses is human-subject records, defined by the check tag "Humans"[Mesh] (decision D12); the unrestricted base is run as a sensitivity analysis (E10). The study window is publication years 2015 to 2024. The year 2025 is excluded because indexing of 2025 records is incomplete at the retrieval date (decision D13), and the completeness of 2024 is quantified (E7). Live PubMed continues to change; the frozen files, not live PubMed, are the analysis dataset. The anchor pull of 23 August 2026 is not part of the dataset and is disclosed as prior knowledge (Q18).

**Q6. Openness of data.**
PubMed is public and free. There is no access barrier, no registration wall for searching and no licensing restriction on record counts or on the MEDLINE citation XML returned by efetch. An NCBI API key is used only to raise the request-rate ceiling from 3 to 10 requests per second; it is not required to obtain the data and does not change the returned counts or records. The frozen dataset, the raw responses, the code and the validation data are posted openly (Q7, Other).

**Q7. Access to data.**
Counts are obtained from `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi` with `db=pubmed`, `retmode=json`, `retmax=0`, `term` set to each verbatim query of Q12, `tool=airct_benchmark`, `email=witold.polanski@ukdd.de`, and `api_key` read from the environment variable `NCBI_API_KEY` (never stored in code, configuration, logs or repository). The parameter `retmax=0` returns the record count together with PubMed's query translation and any error or warning lists, without an identifier list; the alternative `rettype=count` returns the count alone and is therefore not used, so that the query translation can be stored as an audit field for every query. PMID lists (family L of Q12) use esearch with `retmax` and `retstart`, or `usehistory=y` with retrieval from the history server when a list exceeds 10,000 identifiers. Record XML is obtained from `efetch.fcgi` with `db=pubmed`, `retmode=xml`, in batches of 200 PMIDs, as GET or POST depending on identifier list length. The pipeline, the frozen files, all raw JSON and XML responses and the validation data are deposited in a public GitHub repository (release tagged before the freeze run), on OSF on the day of the freeze run, and archived on Zenodo (repository https://github.com/Wito85/airct-benchmark; Zenodo DOI 10.5281/zenodo.22299272, reserved on 4 September 2026; the first version is published at release v1.0 before the freeze run and the submission version as a further version of the same record). Any reader can re-run every query; live counts will differ from the frozen values because PubMed is continuously updated.

**Q8. Date(s) data were accessed.**
- 23 August 2026: anchor pull on the unrestricted record base by W. Polanski and Prem; cells and counts are disclosed verbatim in Q18.
- 3 September 2026: one structure check of publication-type behaviour (Q18).
- 4 September 2026: pre-registration query-syntax checks, restricted by rule to publication year 2015 and to the expressions that are new relative to the draft of 3 September 2026 (Q18 lists the checked expressions; the complete log is deposited on OSF). No 2024 count and no Stroke count was viewed; the only AI counts viewed were the 2015 counts of the three new AI denominator definitions (vocabulary-stable, text-word, Robotics-excluded) and of four subfield descriptors.
- Monday 12 October 2026 (fixed): definitive retrieval (freeze run, Run A followed by Run B in the same session), strictly after the OSF registration timestamp; the exact UTC start and end are written into the file headers and the OSF log. Independent reproduction by Hachem and Buszello takes place on the same UTC calendar day (Other).

All statistical analyses use Run A of the freeze run. Neither the anchor pull nor the syntax checks enter any analysis.

**Q9. Data collection.**
Collection is fully automated by a single Python package whose configuration file holds the query catalogue of Q12 verbatim. For every cell (field, metric, publication year) one esearch request is issued with the year restricted through `[pdat]`. A token-bucket rate limiter caps requests at 10 per second. HTTP 429 and 5xx responses are retried with exponential backoff (1, 2, 4, 8, 16, 32 seconds; at most six attempts) and full logging. The raw JSON or XML of every response is saved with a UTC timestamp. For every count query the following audit fields are stored: full query string, PubMed `querytranslation` as returned, count, UTC timestamp, HTTP status, attempt number, and run label. A smoke-test mode runs one cell. The freeze mode runs the complete catalogue twice in the same session (Run A, then Run B; decision D18) and writes `counts_frozen_YYYYMMDD_runA.csv` and `counts_frozen_YYYYMMDD_runB.csv` with commented headers (retrieval start and end in UTC, git commit hash, pipeline version, E-utilities base URL). Run A is the analysis dataset; Run B serves only the within-day volatility diagnostic (E11). A SHA-256 manifest covers all files. The repository contains a README with exact run instructions and no API key. Because the source is a bibliographic index rather than a sample of participants, representativeness concerns are about indexing behaviour; the principal known artefacts (the 2022 transition of NLM to automated indexing, indexing lag, vocabulary evolution) are handled by design (Q14, Q24). The freeze run takes place strictly after the OSF registration timestamp; before registration, query checks are limited by rule to publication year 2015 and to new expressions (Q8, Q18).

**Q10. Data codebook.**
Controlling documentation: (a) the NCBI E-utilities documentation (NCBI Bookshelf NBK25499 for parameters, NBK25500 for the quick start); (b) the NLM MeSH Browser, Descriptor Data 2026, for every descriptor used, including tree positions and introduction years (facts fixed on 4 September 2026 and stated in Q12 and Q13); (c) the PubMed publication-type definitions. A study-specific data dictionary defining every column of the frozen files (run label, query family, field key, publication year, metric, query string, query translation, count, UTC timestamp, HTTP status, attempt) and every column of the validation dataset (V1 to V6 per rater, adjudicated value) is deposited with the data. The verbatim query catalogue in Q12 and the validation codebook in Q12 and Q24 are self-contained.

---

### SECTION 3: VARIABLES

**Q11. Manipulated variables.**
Not applicable. This is an observational bibliometric study. Field and publication year are naturally occurring grouping variables, not manipulations.

**Q12. Measured variables.**

*12.1 Fixed request parameters.* esearch with `db=pubmed`, `retmode=json`, `retmax=0`, `tool=airct_benchmark`, `email=witold.polanski@ukdd.de`, `api_key` from `NCBI_API_KEY`. Year clause appended to every count query: `AND ("YYYY"[pdat])`, YYYY from 2015 to 2024 (COVID-19: 2020 to 2024). efetch with `db=pubmed`, `retmode=xml`, batches of 200 PMIDs.

*12.2 Composition rule.* Every query is the character-level concatenation of the components shown in the templates of 12.6, joined by ` AND ` or ` NOT ` exactly as shown, with the year clause always last. PubMed evaluates Boolean operators from left to right; parentheses are used exactly where the templates show them and nowhere else. The pipeline configuration holds the templates verbatim, and the code review before the freeze run (Other, timeline) confirms string identity between configuration and this registration. Field expressions, the RCT numerator and the review and primary-article expressions are character-identical to the draft of 3 September 2026 (decision M9); `"Humans"[Mesh]` and the year are appended as separate clauses.

*12.3 Field expressions.*

| Key | Role | MeSH expression (exploded, verbatim) | Text-word expression for E2 and E7 (verbatim) |
|---|---|---|---|
| AI | exposure field | `"Artificial Intelligence"[Mesh]` | `("artificial intelligence"[tiab] OR "machine learning"[tiab] OR "deep learning"[tiab] OR "neural network"[tiab] OR "neural networks"[tiab])` |
| STROKE | primary comparator | `"Stroke"[Mesh]` | `"stroke"[tiab]` |
| DM | secondary disease comparator | `"Diabetes Mellitus"[Mesh]` | `("diabetes"[tiab] OR "diabetes mellitus"[tiab])` |
| MI | secondary disease comparator, narrow cardiovascular sensitivity | `"Myocardial Infarction"[Mesh]` | `("myocardial infarction"[tiab] OR "heart attack"[tiab])` |
| CVD | breadth supplement only, not interpreted as like-for-like | `"Cardiovascular Diseases"[Mesh]` | `"cardiovascular disease"[tiab]` |
| COVID | young-field control, disease-based, 2020 to 2024 | `"COVID-19"[Mesh]` | `("COVID-19"[tiab] OR "SARS-CoV-2"[tiab])` |
| MOBAPP | young-field control, technology-based, 2015 to 2024 (descriptor introduced 2014) | `"Mobile Applications"[Mesh]` | none |
| CDSS | technology comparator, function-matched | `"Decision Support Systems, Clinical"[Mesh]` | none |
| DXIMG | technology comparator, task-matched | `"Diagnostic Imaging"[Mesh]` | none |
| TELE | exploratory technology comparator | `"Telemedicine"[Mesh]` | none |

The text-word expression for AI extends the three-term draft string by `"neural network"[tiab] OR "neural networks"[tiab]` (Study Concept v1.1), because these terms carried a large part of the AI literature before the Machine Learning descriptor existed and keep the coverage of the definition more stable across the study window. It is stated in advance that the two terms also match records on biological neural networks, so the text-word denominator over-includes non-AI records. For this reason E2 serves the replication of the trend under the agreement rule (decision D19), E1b is read for step changes rather than for its level, and neither is used as a level estimate of the AI RCT share. Text-word definitions are always combined with `medline[sb]` so that numerator and denominator share one indexed base (decision D20).

Comparator justification (decision D7). Stroke was fixed a priori as the primary comparator before any technology comparator was considered, because it is a mature clinical field with an active randomized-trial culture in acute therapy, secondary prevention and rehabilitation, and lies within the author team's domain expertise. Diabetes Mellitus is a chronic disease with large pharmacological and behavioural trial output. Myocardial Infarction is an acute cardiovascular field with an established trial culture and narrower than Cardiovascular Diseases, which is a heterogeneous umbrella term reported for completeness only. COVID-19 is a disease field created in 2020 that generated randomized evidence quickly; the limits of the analogy (pandemic funding, therapeutic urgency) are stated in the manuscript. Mobile Applications is a digital, largely interventional technology field whose descriptor was introduced shortly before the study window, so that its entire growth phase is observable and field age is controlled without the pandemic confounder. Decision Support Systems, Clinical is the pre-AI generation of computerized decision support with an established RCT tradition; Diagnostic Imaging tests whether a diagnostic orientation alone explains a low RCT share; Telemedicine is a digital-health delivery field with an established RCT tradition.

*12.4 Auxiliary expressions.*

```
H_HUM          = "Humans"[Mesh]
YEAR           = ("YYYY"[pdat])
N_RCT          = "Randomized Controlled Trial"[pt]
N_CT           = "Clinical Trial"[pt]
N_PROT         = "Clinical Trial Protocol"[pt]
N_REV          = (Review[pt] OR "Systematic Review"[pt] OR Meta-Analysis[pt])
N_PRIM         = "Journal Article"[pt] NOT (Review[pt] OR "Systematic Review"[pt] OR Meta-Analysis[pt] OR Editorial[pt] OR Comment[pt] OR Letter[pt])
T_RCT          = (randomized[tiab] OR randomised[tiab] OR randomly[tiab] OR placebo[tiab] OR trial[ti])
X_NONRESEARCH  = (Review[pt] OR Editorial[pt] OR Letter[pt] OR Comment[pt] OR News[pt])
MEDLINE        = medline[sb]
F_AI_VOCAB2015 = ("Artificial Intelligence"[Mesh:NoExp] OR "Expert Systems"[Mesh:NoExp] OR "Fuzzy Logic"[Mesh:NoExp] OR "Knowledge Bases"[Mesh:NoExp] OR "Natural Language Processing"[Mesh:NoExp] OR "Neural Networks, Computer"[Mesh:NoExp] OR "Robotics"[Mesh:NoExp])
F_AI_TIAB      = ("artificial intelligence"[tiab] OR "machine learning"[tiab] OR "deep learning"[tiab] OR "neural network"[tiab] OR "neural networks"[tiab]) AND medline[sb]
F_AI_NOROB     = ("Artificial Intelligence"[Mesh] NOT "Robotics"[Mesh])
SUB_ML         = "Machine Learning"[Mesh]
SUB_DL         = "Deep Learning"[Mesh]
SUB_NLP        = "Natural Language Processing"[Mesh]
SUB_NN         = "Neural Networks, Computer"[Mesh]
```

F_AI_VOCAB2015 contains every descriptor of the Artificial Intelligence subtree that existed in MeSH 2015, each without explosion, so that descriptors introduced later (for example Machine Learning, 2016; Computer Heuristics, 2016) cannot inflate the AI denominator over time (E1). Residual assumption: the tree position of these descriptors has not changed since 2015. F_AI_NOROB removes the Robotics subtree, which is a child of Artificial Intelligence in the MeSH tree (L01.224.050.375.630) and brings rehabilitation and autonomous robotics records into the exploded AI set, whereas "Robotic Surgical Procedures" lies in other trees (E04, J01) and is not affected (E13, decision M10).

*12.5 Reference panels (positioning only, decision D16).*

Disease-category panel (21 members). Rule: all top-level headings of the MeSH Diseases tree C01 to C26 in the 2026 edition, each as `"..."[Mesh]` (exploded), plus `"Mental Disorders"[Mesh]` from the F tree; excluded by rule: Disorders of Environmental Origin, Animal Diseases, and Pathological Conditions, Signs and Symptoms (C21 to C23). Fixed list: `"Infections"[Mesh]`; `"Neoplasms"[Mesh]`; `"Musculoskeletal Diseases"[Mesh]`; `"Digestive System Diseases"[Mesh]`; `"Stomatognathic Diseases"[Mesh]`; `"Respiratory Tract Diseases"[Mesh]`; `"Otorhinolaryngologic Diseases"[Mesh]`; `"Nervous System Diseases"[Mesh]`; `"Eye Diseases"[Mesh]`; `"Urogenital Diseases"[Mesh]`; `"Cardiovascular Diseases"[Mesh]`; `"Hemic and Lymphatic Diseases"[Mesh]`; `"Congenital, Hereditary, and Neonatal Diseases and Abnormalities"[Mesh]`; `"Skin and Connective Tissue Diseases"[Mesh]`; `"Nutritional and Metabolic Diseases"[Mesh]`; `"Endocrine System Diseases"[Mesh]`; `"Immune System Diseases"[Mesh]`; `"Occupational Diseases"[Mesh]`; `"Chemically-Induced Disorders"[Mesh]`; `"Wounds and Injuries"[Mesh]`; `"Mental Disorders"[Mesh]`.

Technology panel (9 members), predefined list: `"Diagnostic Imaging"[Mesh]`; `"Telemedicine"[Mesh]`; `"Decision Support Systems, Clinical"[Mesh]`; `"Biomarkers"[Mesh]`; `"Robotic Surgical Procedures"[Mesh]`; `"Electronic Health Records"[Mesh]`; `"Mobile Applications"[Mesh]`; `"Wearable Electronic Devices"[Mesh]`; `"Point-of-Care Testing"[Mesh]`.

`CLIN_ANY` is the disjunction of all 21 disease-panel headings in the order listed, `("Infections"[Mesh] OR "Neoplasms"[Mesh] OR ... OR "Mental Disorders"[Mesh])`, written out in full in the pipeline configuration. Panel headings are exploded with the MeSH tree current at retrieval. Biomarkers enters only as a panel member; there is no named Biomarkers contrast (decision D1).

*12.6 Query families.* `{F}` denotes a MeSH field expression of 12.3, `{F_TIAB}` its text-word expression, `(...)` the year clause `("YYYY"[pdat])`. Every template is combined with every year of the field's window.

| Family | Use | Template | Fields |
|---|---|---|---|
| A | denominators | `{F} AND "Humans"[Mesh] AND (...)` | ten named fields |
| B | RCT numerators | `{F} AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND (...)` | ten named fields |
| C | Clinical Trial numerators (S4) | `{F} AND "Humans"[Mesh] AND "Clinical Trial"[pt] AND (...)` | ten named fields |
| D | overlap with AI (E3) | `{F} AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND (...)` | nine comparators |
| E | disjoint sets (E3) | `({F} NOT "Artificial Intelligence"[Mesh]) AND "Humans"[Mesh] AND (...)`; the same with `AND "Randomized Controlled Trial"[pt]` inserted before the year clause; the same with `AND "Clinical Trial"[pt]` | nine comparators |
| F | vocabulary-stable AI (E1) | `{F_AI_VOCAB2015} AND "Humans"[Mesh] AND (...)`; the same with `AND "Randomized Controlled Trial"[pt]` | AI |
| G | text-word definitions (E2) | `{F_TIAB} AND medline[sb] AND "Humans"[Mesh] AND (...)`; the same with `AND "Randomized Controlled Trial"[pt]` | AI, STROKE, DM, MI, CVD, COVID |
| H | subfields (E4) | `{SUB} AND "Humans"[Mesh] AND (...)`; the same with `AND "Randomized Controlled Trial"[pt]` | SUB_ML, SUB_DL, SUB_NLP, SUB_NN |
| I | indexing completeness (E7) | `{F_TIAB} AND (...)` and `{F_TIAB} AND medline[sb] AND (...)`; no Humans clause by design | AI, STROKE |
| J | protocol-excluded numerators (E6) | `{F} AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] NOT "Clinical Trial Protocol"[pt] AND (...)` | ten named fields |
| K | original-research base (E5) | `{F} AND "Humans"[Mesh] NOT (Review[pt] OR Editorial[pt] OR Letter[pt] OR Comment[pt] OR News[pt]) AND (...)`; the same with `AND "Randomized Controlled Trial"[pt]` inserted before the year clause | ten named fields |
| L | PMID lists (S5, S7, S8, R-check) | the family B strings for AI and STROKE and the family R strings (S_f, R_f); esearch with `retmax` and `retstart`, or `usehistory=y` with retrieval from the history server when a list exceeds 10,000 | AI, STROKE, 2024 |
| M | disease panel (S9, E12) | `{HEADING} AND "Humans"[Mesh] AND (...)`; the same with `AND "Randomized Controlled Trial"[pt]` | 21 headings |
| N | technology panel (S9) | `{DESCRIPTOR} AND "Humans"[Mesh] AND (...)`; the same with `AND "Randomized Controlled Trial"[pt]` | 9 descriptors |
| O | efetch XML (S5, S7, S8) | efetch of every PMID in the family B lists for AI and STROKE and of the sampled PMIDs of S_f and R_f | AI, STROKE, 2024 |
| Q | unrestricted record base (E10) | `{F} AND (...)`; `{F} AND "Randomized Controlled Trial"[pt] AND (...)` | AI, STROKE |
| R | strata (S7) | S_f: `{F} AND "Humans"[Mesh] AND medline[sb] AND (randomized[tiab] OR randomised[tiab] OR randomly[tiab] OR placebo[tiab] OR trial[ti]) NOT "Randomized Controlled Trial"[pt] AND (...)`; R_f: `{F} AND "Humans"[Mesh] AND medline[sb] NOT "Randomized Controlled Trial"[pt] NOT (randomized[tiab] OR randomised[tiab] OR randomly[tiab] OR placebo[tiab] OR trial[ti]) AND (...)` | AI, STROKE, 2024 |
| U | disease-related AI subset (E12) | `"Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND {CLIN_ANY} AND (...)`; the same with `AND "Randomized Controlled Trial"[pt]` | AI |
| W | Robotics-excluded AI (E13) | `("Artificial Intelligence"[Mesh] NOT "Robotics"[Mesh]) AND "Humans"[Mesh] AND (...)`; the same with `AND "Randomized Controlled Trial"[pt]` | AI |
| Y | review and primary-article counts (E14) | `{F} AND "Humans"[Mesh] AND (Review[pt] OR "Systematic Review"[pt] OR Meta-Analysis[pt]) AND (...)`; `{F} AND "Humans"[Mesh] AND "Journal Article"[pt] NOT (Review[pt] OR "Systematic Review"[pt] OR Meta-Analysis[pt] OR Editorial[pt] OR Comment[pt] OR Letter[pt]) AND (...)` | ten named fields |

Family letters P, S, T, V and X are not used, to avoid confusion with endpoint labels, stratum names, validation cells and X_NONRESEARCH. Approximate volume: about 2,200 count requests plus efetch batches, completed within about an hour at 10 requests per second.

Worked verbatim examples (AI, 2024):
- Family A: `"Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND ("2024"[pdat])`
- Family B: `"Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2024"[pdat])`
- Family G: `("artificial intelligence"[tiab] OR "machine learning"[tiab] OR "deep learning"[tiab] OR "neural network"[tiab] OR "neural networks"[tiab]) AND medline[sb] AND "Humans"[Mesh] AND ("2024"[pdat])`
- Family Q (identical to the worked example of the draft): `"Artificial Intelligence"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2024"[pdat])`
- Family R, S_AI: `"Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND medline[sb] AND (randomized[tiab] OR randomised[tiab] OR randomly[tiab] OR placebo[tiab] OR trial[ti]) NOT "Randomized Controlled Trial"[pt] AND ("2024"[pdat])`
- Family W: `("Artificial Intelligence"[Mesh] NOT "Robotics"[Mesh]) AND "Humans"[Mesh] AND ("2024"[pdat])`

*12.7 Validation variables (codebook; definitions and examples finalized in the pilot, Q24).* Coded per record from title, abstract, journal, year and PMID, with full text consulted when title and abstract do not allow coding:
- V1 Report type: primary report of an RCT (main results) / secondary analysis of an RCT (post hoc, subgroup, long-term follow-up, economic or process evaluation, pooled analysis) / protocol or design paper / not an RCT (non-randomized, observational, review, commentary, other) / unclear.
- V2 Randomization unit (if V1 is primary or secondary): individual / cluster / crossover or within-subject / other.
- V3 Role of AI (AI cells only): AI system is the intervention or an integral component of the intervention under randomized comparison / a robotic or automated system without a learning or inference component is the intervention (record enters the AI set through the Robotics subtree; decision M10) / AI used as an analytic tool on trial data / AI mentioned peripherally or used as an outcome or measurement instrument / no AI content (indexing error) / unclear.
- V4 Setting (if V3 is AI intervention): real clinical care with patient-level or clinician-level outcomes / simulated or reader-study setting / other.
- V5 Field relevance (Stroke cells only): stroke is the target condition or population / stroke is peripheral / no stroke content.
- V6 Registration identifier seen (all cells): any trial registration identifier visible in title or abstract, recorded verbatim; used to check the automated extraction of 12.8.

*12.8 Trial-level variables (S8).* From the efetch XML of every RCT-tagged AI and Stroke record of 2024 (family O): accession numbers in DataBankList, and registration identifiers matched in title and abstract by regular expressions for ClinicalTrials.gov (NCT followed by eight digits), ISRCTN, EudraCT, DRKS, ACTRN, ChiCTR, UMIN, CTRI, NTR and its successor NL, IRCT, JPRN and jRCT, and PACTR. Identifiers are normalized (case, whitespace, separators) and deduplicated within field. The exact regular expressions are fixed in the pipeline configuration of the tagged release before the freeze run and deposited with the code; they are implementation detail and do not alter the estimand.

*12.9 Derived variables and estimands.* For field f and year y: RCT share p_fy = y_fy / n_fy (family B over family A) and Clinical Trial share c_fy / n_fy (family C over family A); prevalence ratio PR = p_AI / p_comparator with the fold difference 1/PR and the absolute difference in percentage points; overlap proportion (family D over family A) and disjoint-set shares (family E); corrected count C_f = a_f x pi_true,f + size(S_f) x pi_missed,f with p_corr,f = C_f / n_f and PR_corr (S7); adjusted shares p_adj and PR_adj (S5, Q19); distinct registered trials T_f, identifier coverage, records-per-trial ratio a_f / T_f, trial density T_f / n_f per 1,000 records and its upper bound (S8); annual multiplicative change of the PR and compound annual growth rates of numerator and denominator (S1); rank of AI within each panel and number of panel members whose confidence interval lies entirely above the AI interval (S9); vocabulary-stability ratio n(family A, AI) / n(family G, AI) per year (E1b); MEDLINE completeness indicator, family I with `medline[sb]` over family I without it, per year (E7); Run B minus Run A per cell (E11); proportion of AI records carrying the Robotics subtree, 1 minus n(family W) / n(family A, AI) (E13); review-to-primary-article ratio, first over second family Y count (E14).

*12.10 Audit fields per count query.* Full query string, PubMed `querytranslation` as returned, count, UTC timestamp, HTTP status, attempt number, run label (A or B).

**Q13. Inclusion and exclusion criteria.**

Count cells (main analyses). A record enters the denominator of field f and year y if it carries the field's MeSH descriptor (exploded), the check tag `"Humans"[Mesh]` and the publication year y in `[pdat]`. It enters the RCT numerator if it additionally carries `"Randomized Controlled Trial"[pt]` (PubMed explodes the publication-type hierarchy, so pragmatic and equivalence trials are included), and the Clinical Trial numerator if it carries `"Clinical Trial"[pt]`. No language restriction and no record-type restriction apply in the main analyses; the original-research restriction (E5) and the protocol exclusion (E6) are exploratory. Text-word definitions (E2, E7) additionally require `medline[sb]`. Every cell is a census of matching records, not a sample. Years: 2015 to 2024 for all fields except COVID-19 (2020 to 2024); the primary year is 2024; 2025 and later years are excluded (decision D13). Subfields (E4) are reported from the descriptor's introduction year onward (Machine Learning 2016; Deep Learning 2019, with previous indexing under Artificial Intelligence 2001 to 2018; Natural Language Processing and Neural Networks, Computer existed before 2015). Panel rule: a panel member whose descriptor was introduced after 2015 (Point-of-Care Testing, 2016; Wearable Electronic Devices, 2018) enters the 2024 rank only and not the rank trajectory; Mobile Applications (2014) enters both. Introduction years were read from the field Date Introduced of the NLM MeSH Browser (Descriptor Data 2026) by W. Polanski on 4 September 2026 (Point-of-Care Testing D000067716: 2016/01/01; Deep Learning D000077321: 2019/01/01; Wearable Electronic Devices D000076251: 2018; Mobile Applications D063731: 2014; Machine Learning D000069550: 2016). The pre-registration syntax check found non-zero 2015 counts for both later descriptors (Q18), which reflects records with publication year 2015 indexed after the descriptor was established and confirms that pre-introduction years are incompletely covered. Overlap between fields is not removed in the main analyses (a record can belong to several fields); overlaps and disjoint sets are reported (E3).

Validation and stratum records (S5, S7, R-check). Frozen PMID lists from Run A, publication year 2024, seed 20260904:
- V-AI: all records of `F*_AI AND N_RCT` if 200 or fewer, otherwise a simple random sample of 200.
- V-STROKE: the same rule for `F*_STROKE AND N_RCT`.
- U-AI and U-STROKE: simple random samples of 200 from the enriched untagged strata S_AI and S_STROKE (family R).
- R-check: 50 records each from the remainder strata R_AI and R_STROKE (plausibility check only).
- Pilot: 20 additional records per cell, drawn first, used only to calibrate the codebook and not counted in the formal set.
Sampling by Python `random.Random(20260904).sample` on the PMID list sorted ascending. Trial-level component (S8): all RCT-tagged AI and Stroke records of 2024, no sampling.

**Q14. Missing data.**
Counts: none by construction; every cell is a complete count at the retrieval date, and a valid zero count is a genuine zero, not missing (zero counts inside a prevalence ratio are handled by the Haldane correction, Q23). Indexing lag: 2025 is excluded (decision D13), and the completeness of the primary year 2024 is quantified as the proportion of text-word AI and stroke records that have completed MEDLINE indexing (E7); no incomplete year is presented and no imputation is performed. Validation: a record that cannot be coded after full-text retrieval is coded "unclear" and reported; kappa is computed including "unclear". A PMID whose XML cannot be retrieved after six attempts is recorded as missing and reported; for sampled cells it is replaced by the next PMID in the seeded sampling sequence. Trial level: records without any registration identifier are not missing but a reported category (coverage), and an upper bound treats each such record as its own trial (S8).

**Q15. Outliers.**
No outlier removal. Every cell is a complete count, so extreme values are features of the literature. The influence of single field-years on the trend model is examined descriptively by refitting S1 with year as a factor and with a natural cubic spline (Q19), and the within-day stability of every cell is quantified by the double run (E11). No data point is deleted.

**Q16. Sampling weights.**
Not applicable. Counts are unweighted censuses of matching records. In the trend models the logarithm of the field-year denominator enters as the offset (exposure); this is a model offset, not a sampling weight. In the bootstrap for S5 and S7 the validation proportions are combined with the observed stratum sizes by construction (Q19); this is a correction, not a weighting scheme.

---

### SECTION 4: KNOWLEDGE OF DATA

**Q17. Previous work.**
No author has published a prior peer-reviewed study using a frozen PubMed count dataset of this kind; the dataset is generated de novo by the authors' pipeline on 12 October 2026. Prior contact with the data source: (a) an anchor pull on 23 August 2026 on the unrestricted record base, executed and inspected by W. Polanski and Prem, to scope feasibility and stabilize the query strings (cells and counts in Q18); (b) one structure check on 3 September 2026 (Q18); (c) pre-registration query-syntax checks limited to publication year 2015 and to new expressions (Q8, Q18). Richter, Buszello, Willkommen, Hachem and Abdullayeva have seen summary anchor figures during team meetings; Ilker Y. Eyüpoglu is the validation adjudicator and has seen the same summary figures. All eight authors reviewed this preregistration, including the disclosures of Q17 and Q18, and approved it at a team meeting on 4 September 2026. General domain familiarity with the medical-AI evidence-gap literature (Lam et al. 2022; npj Digital Medicine 2026; Lancet Digital Health 2024) is shared across the team and informs the direction of H1.

**Q18. Prior knowledge (pilot-data disclosure and bias mitigation).**

Anchor pull, 23 August 2026, unrestricted record base (no `"Humans"[Mesh]` clause), disclosed verbatim from the draft of 3 September 2026:
- AI all-time: 298,542 records; AI reviews all-time: 30,065; AI primary all-time: 257,518.
- AI 2021: 24,936 total; 2,579 reviews; 223 RCTs (0.89 percent RCT share).
- AI 2024: 38,034 total; 4,307 reviews; 254 RCTs (0.67 percent RCT share); retrospective[tiab] 2,109 vs prospective[tiab] 1,054.
- Stroke 2021: 13,023 total; 2,116 reviews; 588 RCTs (4.52 percent).
- Stroke 2024: 11,693 total; 1,995 reviews; 661 RCTs (5.65 percent).
- Diabetes 2021 total: 26,810. Cardiovascular Diseases all-time: 2,966,478.

These pilot values indicate that the primary contrast is likely to fall in the hypothesized direction (anchor prevalence ratio approximately 0.12 on the unrestricted base).

Structure check, 3 September 2026: `"Artificial Intelligence"[Mesh] AND "Systematic Review"[pt] NOT Review[pt]` without year restriction returned zero records, confirming that the Systematic Review publication type is nested under Review in PubMed.

Decisions taken without data contact: the restriction of the main analyses to human-subject records (decision D12) and the exclusion of 2025 (decision D13) were taken on 4 September 2026 without viewing any Humans-restricted count and without viewing any 2025 count.

Cells never inspected before registration: no count for Myocardial Infarction, COVID-19, Mobile Applications, Decision Support Systems, Clinical, Diagnostic Imaging, Telemedicine, any panel member other than the all-time Cardiovascular Diseases count above, the Clinical Trial numerator, the protocol-excluded numerator, the enriched or remainder strata, the original-research base, the disjoint sets, any overlap, any Humans-restricted definition of AI or Stroke, any 2024 count other than those listed above, and no validation or trial-level outcome; the only exceptions are the 2015 syntax-check counts listed next.

Pre-registration syntax checks, 4 September 2026, 07:26:24 to 07:26:41 UTC, under rule 10.2 of the study concept: esearch with `retmax=0`, publication year 2015 only, one query per new expression, 51 queries in total, run with the script `prereg_syntax_check.py` (version 1.0, API key present). The log `prereg_syntax_check_20260904T072624Z.log` and the raw responses `prereg_syntax_check_20260904T072624Z.jsonl` are deposited as project files with this registration. Combinations involving a named field were run with Diabetes Mellitus wherever the field itself was not the object of the check, so that no Stroke count and no AI count beyond the 2015 counts of F_AI_VOCAB2015, F_AI_TIAB, F_AI_NOROB and the four subfield descriptors were viewed. Checked expressions: `"Humans"[Mesh]`; the family A, B, E, G, J, K and R compositions with Diabetes Mellitus; `"Clinical Trial"[pt]`; `"Clinical Trial Protocol"[pt]`; T_RCT; X_NONRESEARCH; `medline[sb]`; F_AI_VOCAB2015; F_AI_TIAB; F_AI_NOROB; the four subfield descriptors; CLIN_ANY; all 21 disease-panel headings and all 9 technology-panel descriptors. Results: all 51 requests returned HTTP 200 at the first attempt; PubMed reported no error-list entry (no unknown descriptor, no unknown field) and one warning, "No items found", for `"Deep Learning"[Mesh]` in 2015, which is the expected consequence of the descriptor's establishment in 2019. Every querytranslation matched the intended semantics: each MeSH descriptor resolved as [MeSH Terms] or [MeSH Terms:noexp], each publication type as [Publication Type], `trial[ti]` as [Title], `medline[sb]` as the MEDLINE status filter, and the NOT clauses of the stratum and exclusion expressions were grouped left to right as intended. Consistency check: for Diabetes Mellitus 2015 the enriched untagged stratum (941), the remainder stratum (16,377) and the RCT-tagged records (1,405) sum exactly to the human-subject denominator (18,723), so the three strata partition the field, and the human-subject records of 2015 are entirely MEDLINE-indexed. No query string was changed in response to the check. Counts viewed (publication year 2015; human-subject base unless marked "all records"): Humans check tag alone (all records) 760,055; DM denominator (family A) 18,723; DM RCT numerator (family B) 1,405; Clinical Trial publication type (all records) 41,162; Clinical Trial Protocol publication type (all records) 20; T_RCT (all records) 64,724; X_NONRESEARCH (all records) 240,372; DM text words AND medline[sb] (family G) 24,838; DM enriched untagged stratum S 941; DM remainder stratum R 16,377; DM protocol-excluded RCT numerator (family J) 1,405; DM NOT AI (family E) 18,647; DM original-research base (family K) 13,614; F_AI_VOCAB2015 2,728; F_AI_TIAB 2,236; F_AI_NOROB 3,232; Machine Learning 1,477; Deep Learning 0; Natural Language Processing 260; Neural Networks, Computer 718; CLIN_ANY 518,620; Infections 76,454; Neoplasms 140,191; Musculoskeletal Diseases 37,553; Digestive System Diseases 62,594; Stomatognathic Diseases 16,660; Respiratory Tract Diseases 46,801; Otorhinolaryngologic Diseases 12,630; Nervous System Diseases 92,935; Eye Diseases 18,718; Urogenital Diseases 74,656; Cardiovascular Diseases 89,503; Hemic and Lymphatic Diseases 30,473; Congenital, Hereditary, and Neonatal Diseases and Abnormalities 39,667; Skin and Connective Tissue Diseases 48,247; Nutritional and Metabolic Diseases 51,788; Endocrine System Diseases 37,208; Immune System Diseases 50,168; Occupational Diseases 3,118; Chemically-Induced Disorders 16,064; Wounds and Injuries 31,084; Mental Disorders 55,778; Diagnostic Imaging 100,676; Telemedicine 2,154; Decision Support Systems, Clinical 619; Biomarkers 40,672; Robotic Surgical Procedures 1,363; Electronic Health Records 2,291; Mobile Applications 852; Wearable Electronic Devices 363; Point-of-Care Testing 266. The overlap Diabetes Mellitus AND Artificial Intelligence (human-subject base, 2015) is derivable from these counts as 76 records. The 2015 counts of Point-of-Care Testing (266) and Wearable Electronic Devices (363), both descriptors established after 2015, motivate the panel rule stated in Q13.

Bias mitigation: (1) all query strings, endpoints, models and inference criteria are fully prespecified here, and the freeze run takes place strictly after the registration timestamp; (2) exactly one confirmatory contrast is declared (P); every other endpoint is labelled secondary or exploratory and reported with estimation language only; (3) no data-dependent model selection is permitted: the trend model is quasi-Poisson by prespecification and the negative binomial is a fixed sensitivity analysis, not a switch; (4) the main record base (human-subject records) has never been viewed for any field; (5) the frozen dataset, raw responses, code and validation data are posted openly and reproduced independently on the same day; (6) because the anchor pull is not an independent hold-out sample, the authors do not claim novelty of direction and frame the contribution as reproducible quantification and benchmarking (magnitude, trajectory, tag-corrected, adjusted and trial-level versions of the contrast, and the rank of AI within complete reference distributions). No author has knowledge that would invalidate the confirmatory test in the sense of Wagenmakers et al. (2012), because the frozen human-subject counts, confidence intervals and trend estimates are not known before the freeze run.

---

### SECTION 5: ANALYSES

**Q19. Statistical model.**

*19.1 Endpoint hierarchy.* One confirmatory endpoint; all other endpoints are estimation with 95% confidence intervals and are labelled as below in every table and every sentence (decision D8). The label E8 is not used, because the former exploratory tag-sensitivity check has become the mandatory endpoint S7.

| Label | Endpoint | Status |
|---|---|---|
| P | prevalence ratio of the RCT share, AI vs STROKE, 2024, human-subject record base, two-sided 95% CI | primary, confirmatory |
| S1 | annual multiplicative change of the AI vs STROKE prevalence ratio, 2015 to 2024, 95% CI; yearly prevalence ratios; growth decomposition | key secondary |
| S2 | prevalence ratio of the RCT share, AI vs DM, MI and CVD, 2024, 95% CI; yearly ratios descriptively | secondary |
| S3 | prevalence ratio of the RCT share, AI vs CDSS and AI vs DXIMG, 2024, 95% CI; trends 2015 to 2024 | secondary |
| S4 | prevalence ratio of the Clinical Trial share, AI vs STROKE, 2024, 95% CI; other comparators descriptively | secondary |
| S5 | validation-based: precision of the RCT tag, primary-report fraction, AI-as-intervention fraction, adjusted AI share and adjusted prevalence ratio vs STROKE, 2024, bootstrap 95% CI | secondary |
| S6 | young-field controls: RCT share of COVID (2020 to 2024) and MOBAPP (2015 to 2024) and prevalence ratio AI vs each per year | secondary |
| S7 | tag-corrected prevalence ratio AI vs STROKE, 2024, correcting for false-positive and for untagged RCT records in each field, bootstrap 95% CI | secondary |
| S8 | trial level: distinct registered trials per 1,000 records, records-per-trial ratio, trial-level prevalence ratio with 95% CI, identifier coverage per field, AI and STROKE 2024 | secondary |
| S9 | reference distributions: RCT share with 95% CI for every panel member, 2024; rank of AI in the disease panel and in the technology panel; number of members whose CI lies entirely above the AI CI; rank trajectory 2015 to 2024 | secondary, descriptive |
| E1 | vocabulary-stable AI denominator (P and S1 recomputed); E1b vocabulary-stability diagnostic | exploratory |
| E2 | text-word definitions on the MEDLINE-indexed base: P and S1 with the text-word AI denominator against the MeSH Stroke field; fully text-word contrast and text-word shares of the five disease comparators descriptively | exploratory |
| E3 | disjoint-set comparators and overlap counts | exploratory |
| E4 | AI subfields Machine Learning, Deep Learning, Natural Language Processing, Neural Networks Computer | exploratory |
| E5 | original-research denominators (P and S2 recomputed) | exploratory |
| E6 | protocol-excluded RCT numerator (P and S2 recomputed) | exploratory |
| E7 | indexing completeness and MEDLINE coverage indicator per year | exploratory, descriptive |
| E9 | TELE as additional technology comparator, as in S3 | exploratory |
| E10 | P and S1 on the unrestricted record base | exploratory, sensitivity |
| E11 | within-day database volatility, Run A vs Run B per cell | exploratory, descriptive |
| E12 | disease-related clinical AI subset (AI AND CLIN_ANY), P recomputed | exploratory |
| E13 | Robotics-excluded AI denominator and numerator (P and S1 recomputed); yearly Robotics share of AI records | exploratory, sensitivity |
| E14 | review-to-primary-article ratio per named field and year | exploratory, descriptive |
| E15 | S1 refit on the human-indexed era 2015 to 2021 | exploratory, sensitivity |

*19.2 Primary analysis (P).* Prevalence ratio PR = (a / n_AI) / (b / n_STROKE) for 2024 on the human-subject record base, where a and b are the RCT-tagged counts (family B) and n the denominators (family A). Two-sided 95% CI by the Katz log method, SE(log PR) = sqrt(1/a - 1/n_AI + 1/b - 1/n_STROKE). A Wald p-value on the log scale is reported once, in the primary table. The manuscript reports the PR, the fold difference 1/PR and the absolute difference in percentage points with a Newcombe hybrid-score 95% CI. If either numerator is below 10, a Koopman score interval is added. Should the PR be at or above 1, this is reported as such; no post hoc redefinition.

*19.3 Key secondary analysis (S1).* Poisson generalized linear model with log link on the 20 field-year cells 2015 to 2024 of AI and STROKE: response y_fy, offset log n_fy, terms field, (year - 2015) and field x (year - 2015), STROKE as reference. Standard errors use the quasi-Poisson dispersion; a negative binomial model with the same mean structure is the fixed sensitivity analysis. The exponentiated field-by-year interaction coefficient is the annual multiplicative change of the AI versus STROKE prevalence ratio (below 1: gap widening; above 1: gap narrowing), with 95% CI. Nonlinearity check (exploratory): year as a factor, and a natural cubic spline with 3 knots. Yearly Katz prevalence ratios with CIs are plotted. Growth decomposition: compound annual growth rates 2015 to 2024 of RCT-tagged records and of all records, for AI and for STROKE. S1 is replicated on the vocabulary-stable (E1) and text-word (E2) AI denominators; a trend conclusion is stated only if the three definitions agree in direction (decision D19).

*19.4 Other secondary contrasts (S2, S3, S4, S6).* Katz prevalence ratios with 95% CIs for 2024. Trends for S3 and S6 as in 19.3 with the respective comparator in place of STROKE (COVID-19 window 2020 to 2024); yearly ratios descriptively for S2 and S4.

*19.5 Validation-adjusted (S5) and tag-corrected (S7) estimates.* Validation estimands from the adjudicated codes (Q24): pi_true,f, the proportion of tagged records (V-cells) with V1 in {primary, secondary}; pi_primary,f, the proportion with V1 = primary; pi_intervention (AI), the proportion of true RCT reports in V-AI with V3 = AI intervention (the robotic-system category does not count and is reported separately); pi_field (Stroke), the proportion of true RCT reports in V-STROKE with V5 = target condition; pi_missed,f, the proportion of U-cell records with V1 in {primary, secondary}; pi_missed_primary,f analogously for V1 = primary. S5: p_adj(AI) = p_crude(AI) x pi_true(AI) x pi_intervention(AI); p_adj(STROKE) = p_crude(STROKE) x pi_true(STROKE) x pi_field(STROKE); PR_adj = p_adj(AI) / p_adj(STROKE). S7: C_f = a_f x pi_true,f + size(S_f) x pi_missed,f; p_corr,f = C_f / n_f; PR_corr = p_corr(AI) / p_corr(STROKE). 95% CIs by parametric bootstrap with 10,000 draws and seed 20260904: each validation proportion is drawn from Beta(k + 0.5, m - k + 0.5) (Jeffreys) with k successes among m coded records; each tagged count a_f is drawn from a Poisson distribution with mean equal to the observed count; stratum sizes and denominators are fixed at their observed values; percentile intervals. Stated assumption: RCT reports outside the tagged set and outside S_f are negligible; the number of RCT reports found among the 50 R-check records per field is reported (expected zero) and not used for correction. Sensitivity variant: the corrected numerator restricted to primary reports (pi_primary, pi_missed_primary). Inter-rater agreement: unweighted Cohen's kappa with asymptotic 95% CI (statsmodels, cohens_kappa) and raw percent agreement for V1, V3 and V5, reported per cell.

*19.6 Trial-level estimates (S8).* T_f distinct identifiers per field. Trial density T_f / n_f per 1,000 records with an exact Poisson 95% CI; trial-level prevalence ratio (T_AI / n_AI) / (T_STROKE / n_STROKE) with a Katz-type CI treating T as counts (approximation stated); identifier coverage (proportion of RCT-tagged records with at least one identifier) with Wilson 95% CI; records-per-trial ratio a_f / T_f among records with identifiers, descriptively; upper bound counting each record without identifier as its own trial; agreement between the V6 codes and the automated extraction on the validation sample.

*19.7 Reference distributions (S9).* RCT share with Wilson 95% CI for every panel member in 2024. Rank of AI within each panel (1 = lowest share); number of panel members whose CI lies entirely above the AI CI; rank trajectory 2015 to 2024 as a line plot, excluding members introduced after 2015 (Q13). No formal tests.

*19.8 Exploratory analyses and diagnostics (E1 to E15).* E1, E2, E5, E6, E10, E12 and E13: the endpoints named in 19.1 are recomputed with the alternative denominator or numerator definition and reported next to the main result. E1b: yearly ratio of the MeSH-defined to the text-word-defined AI denominator; a step change coinciding with a descriptor introduction year or with the 2022 switch to automated indexing is reported as evidence of a vocabulary artefact and discussed against the trend replications. E3: overlap proportions and prevalence ratios on the disjoint sets. E4: shares per subfield-year from the introduction year onward. E7: proportion of text-word records with completed MEDLINE indexing per year, for AI and for stroke; the 2024 value documents the completeness of the primary year. E9: TELE as in S3. E11: Run A versus Run B, absolute and relative difference per cell, maximum reported. E13 additionally: yearly proportion of AI records carrying the Robotics subtree. E14: review-to-primary-article ratio per field-year, descriptively, plotted. E15: the S1 model refit on 2015 to 2021, compared descriptively with the full-window estimate.

*19.9 Software and reproducibility.* Python 3 with pandas, numpy, scipy and statsmodels; versions pinned in requirements.txt and environment.yml; all random procedures use seed 20260904; every table and figure is produced from the frozen files without manual steps; two authors regenerate all outputs from the frozen files and confirm bit-identical results (Other).

*19.10 Statistical analysis plan.* A full SAP that elaborates but does not alter the analyses specified here is written by W. Polanski and deposited on OSF before the freeze run. Any element of the SAP that differs from this registration is labelled as a deviation and justified.

**Q20. Effect size.**
The confirmatory effect size is the 2024 AI versus Stroke prevalence ratio of the RCT share on the human-subject record base, reported with its fold difference 1/PR and the absolute difference in percentage points. Secondary effect sizes: prevalence ratios for every other contrast; the annual multiplicative change of the AI versus Stroke prevalence ratio; the validation-adjusted and tag-corrected prevalence ratios; the trial-level prevalence ratio; the rank of AI within each panel. The smallest effect of interest for H1 is any prevalence ratio below 1 whose two-sided 95% CI excludes 1; the magnitude expected from the anchor pull on the unrestricted base is disclosed in Q18 and is far from 1.

**Q21. Power / precision.**
Every count cell is a complete count, so inference for P, S1 to S4, S6, S8 and S9 is precision-based: the denominators are large and the CI width is reported for every estimate. The precision-limited components are the validation cells: n = 200 per cell yields a two-sided 95% Wilson interval with a half-width of at most about 6.9 percentage points for each validation proportion; the uncertainty of these proportions is propagated into S5 and S7 by the bootstrap of 19.5, and the width of the resulting intervals is reported. Kappa is reported with its CI. No conventional a priori power analysis applies to a census.

**Q22. Inference criteria.**
H1 is supported if the upper limit of the two-sided 95% CI for the 2024 AI versus Stroke prevalence ratio lies below 1; otherwise H1 is reported as not supported, without redefinition. The single Wald p-value is reported once and interpreted at the two-sided 5% level. No multiplicity adjustment is applied because there is exactly one confirmatory test; all other endpoints are estimation with unadjusted 95% CIs, labelled secondary or exploratory in every table and sentence, without significance language (decision D8). For S1 a direction of change of the gap is stated only if the estimates on the three AI denominator definitions (main, E1, E2) agree in direction (decision D19); otherwise the trend is reported as inconclusive with respect to vocabulary. For S9 the position of AI is reported as a rank and as the number of members whose CI lies entirely above the AI CI; no test.

**Q23. Assumptions.**
(1) Katz and Wilson intervals assume moderately large counts; a Koopman score interval is added to P if either numerator is below 10; zero cells receive the Haldane correction (0.5 added to all four cells of the affected prevalence ratio) and are flagged. (2) The trend model uses the quasi-Poisson dispersion for all standard errors by prespecification; the negative binomial is a fixed sensitivity analysis, not a data-dependent switch; the dispersion statistic is reported. Nonlinearity is checked by the year-as-factor and spline models of 19.3. The confirmatory contrast does not depend on any regression model; a convergence failure of the GLM would be reported and the yearly Katz prevalence ratios would stand as the descriptive trend. (3) The tag correction assumes that RCT reports lacking randomization vocabulary in title or abstract are negligible; the R-check reports evidence on this assumption. (4) The trial-level interval treats distinct identifiers as counts; the approximation and the identifier coverage are reported. (5) Field definitions are proxies; conclusions are stated only where the four denominator definitions (exploded MeSH, Humans-restricted MeSH, vocabulary-stable MeSH, text words) agree in direction. (6) Kappa is computed including the "unclear" category; the validation values entering the analysis are the adjudicated values.

**Q24. Sensitivity / robustness.**

Prespecified sensitivity analyses: (1) vocabulary-stable AI denominator, E1, with the diagnostic E1b; (2) text-word definitions for AI and the five disease comparators on the MEDLINE-indexed base, E2; (3) disjoint-set comparators and overlap counts, E3; (4) original-research denominators, E5; (5) protocol-excluded numerator, E6; (6) unrestricted record base for P and S1, E10; (7) Robotics-excluded AI denominator and numerator, E13; (8) human-indexed-era refit of S1, E15; (9) the tag correction S7 and the validation adjustment S5 are mandatory corrections rather than sensitivity analyses. Diagnostics: E7 (indexing completeness), E11 (within-day volatility), E1b (vocabulary stability).

The 2022 transition of NLM to fully automated MeSH indexing can shift publication-type and MeSH assignment over time. It is addressed by the validation of the RCT tag in both directions and in both fields (S5, S7), by the vocabulary-stability diagnostic E1b, by the replication of the trend on three denominator definitions with the agreement rule D19, and by the era refit E15. It cannot be eliminated and is discussed in the limitations.

Validation substudy (procedure). Cells and sampling as in Q13; publication year 2024; frozen PMID lists from Run A. Materials: efetch XML for each sampled PMID; the rating sheet shows title, abstract, journal, year and PMID only, with MeSH terms and publication types removed; full text is consulted when title and abstract do not allow coding. Pilot: 20 records per cell, rated jointly to calibrate the codebook of 12.7, not counted in the formal set. Formal rating: independent, blinded rating of the V-cells and the R-check by W. Polanski and Prem; the U-cells are rated by the second rater pair Richter and Willkommen under the same procedure (confirmed at the team meeting on 4 September 2026). Adjudication of all disagreements in all cells by Ilker Y. Eyüpoglu; adjudicated values enter the analysis. Agreement: unweighted Cohen's kappa with 95% CI and raw percent agreement for V1, V3 and V5, per cell. Procedural rule kept from the draft: if kappa for V1 in any cell is below 0.61, a full-text adjudication layer is added for that cell (both raters re-code every record of the cell on the full text before adjudication) and both kappa values are reported. V6 codes are compared with the automated identifier extraction of 12.8 and the agreement is reported.

**Q25. Exploratory analyses.**
All analyses labelled E1 to E15 in Q19 are exploratory and are reported under an explicit "Exploratory" heading: E1 vocabulary-stable AI denominator; E1b vocabulary-stability diagnostic; E2 text-word definitions; E3 disjoint sets and overlaps; E4 AI subfields (Machine Learning, Deep Learning, Natural Language Processing, Neural Networks Computer); E5 original-research denominators; E6 protocol-excluded numerator; E7 indexing completeness and MEDLINE coverage; E9 Telemedicine as additional technology comparator; E10 unrestricted record base; E11 within-day volatility; E12 disease-related clinical AI subset; E13 Robotics-excluded AI; E14 review-to-primary-article ratio; E15 human-indexed-era refit. The retrospective-versus-prospective title-and-abstract proxy and the joinpoint regression of the draft are not carried into this registration (decision M3). Any analysis not specified in Q19 to Q24 that is added during the study is reported as exploratory and labelled as a deviation from this registration.

---

### STATEMENT OF INTEGRITY
The authors of this preregistration state that they filled out this preregistration to the best of their knowledge and that no other preregistration exists pertaining to the same hypotheses and dataset. All prior contact with the data source is disclosed in Q17 and Q18, including the anchor pull of 23 August 2026, the structure check of 3 September 2026 and the pre-registration syntax checks of 4 September 2026.

---

### OTHER

**Data and code availability.** The public GitHub repository https://github.com/Wito85/airct-benchmark (MIT License) contains the pipeline, the configuration file with the verbatim query catalogue, requirements.txt, environment.yml and a README with exact run instructions; the release is tagged before the freeze run and archived on Zenodo under DOI 10.5281/zenodo.22299272 (reserved on 4 September 2026; first version published at release v1.0, submission version as a further version of the same record). On 12 October 2026 the frozen count files (Run A and Run B), all raw JSON and XML responses, the SHA-256 manifest and the tagged code release are deposited on OSF. The validation dataset (rater codes, adjudicated codes, agreement tables) and the trial-identifier table are deposited on OSF when the validation is complete. The SAP is deposited on OSF before the freeze run. From the day of the freeze, every number in the manuscript traces to these files. A medRxiv preprint is posted at submission.

**Timing and freeze rule.** The freeze run takes place strictly after the OSF registration timestamp. Run A is the analysis dataset; Run B serves E11 only. Independent reproduction: Hachem and Buszello each run the tagged release from a clean environment on the same UTC calendar day, compare every cell with Run A and record discrepancies in a reproduction log on OSF; both also regenerate all tables and figures from the frozen files and confirm bit-identical output.

**Timeline.** Registration on 4 September 2026. Pipeline v1, code review and smoke test (string identity against this registration, explosion behaviour of `"Clinical Trial"[pt]`, `medline[sb]` semantics, identifier regular-expression tests, git tag v1.0) before the freeze run. SAP deposited before the freeze run. Freeze run Monday 12 October 2026 with same-day reproduction. Validation (pilot, formal rating, R-check, adjudication, agreement statistics, identifier extraction), SAP-conform analysis, figures and tables, manuscript, checklists, submission.

**Target journals and reporting.** Primary target npj Digital Medicine, Article format (unstructured abstract up to 150 words; title up to 15 words without punctuation; order Introduction, Results, Discussion, Methods; Data availability, Code availability, Author contributions and Competing interests mandatory; about 60 references; AI use disclosed in Methods; Nature Portfolio Reporting Summary and Editorial Policy Checklist at revision). Second choice Journal of Clinical Epidemiology; third choice JAMA Network Open. Reporting follows BIBLIO (Montazeri et al., Syst Rev 2023;12:239) as the primary checklist and STROBE for cross-sectional studies as the secondary checklist.

**AI use.** Anthropic's Claude was used, under the supervision and verification of the authors, for drafting protocol text, code scaffolding and language editing. No analysis result is generated by AI without reproduction by the authors from the frozen data. This is disclosed in the Methods section of the manuscript.

**Conflicts of interest.** The authors declare no financial conflicts of interest; confirmed by all authors at the team meeting on 4 September 2026.

**Governance of the statistical analysis plan.** The SAP is written by the senior author without an external biostatistician. Mitigations: (1) the analyses are fully specified in this registration before any data are retrieved, and the SAP cannot alter them without a labelled deviation; (2) documented independent reproduction of the pipeline and of all results by two co-authors (Hachem, Buszello) on separate machines, with a reproduction log on OSF; (3) a courtesy review of the SAP by an institutional statistician without authorship, requested before the freeze run and acknowledged if performed.

**Author contributions (CRediT).** All eight authors meet the four ICMJE criteria (substantial contribution; drafting or critical revision; final approval; accountability). The roles were confirmed by all authors at the team meeting on 4 September 2026.

| # | Author | CRediT roles |
|---|---|---|
| 1 | Prem (first) | Data curation (lead); Software (lead, pipeline); Formal analysis (supporting); Investigation; Validation (rater); Writing (original draft, with Polanski) |
| 2 | Richter | Investigation (literature curation); Validation (rater, U-cells); Writing (review and editing) |
| 3 | Buszello | Software (code review); Validation (independent reproduction); Writing (review and editing) |
| 4 | Willkommen | Visualization (figure and table quality control); Validation (rater, U-cells); Writing (review and editing) |
| 5 | Hachem | Validation (independent reproduction of results); Software (supporting); Writing (review and editing) |
| 6 | Abdullayeva | Investigation (reference management, query verification); Project administration (supporting); Writing (review and editing) |
| 7 | Eyüpoglu (adjudicator) | Validation (adjudication); Supervision (clinical face validity of comparator fields); Methodology (supporting); Writing (review and editing) |
| 8 | Polanski (senior, corresponding, guarantor) | Conceptualization (lead); Methodology; Formal analysis (SAP); Validation (rater); Supervision; Project administration; Writing (original draft with Prem; review and editing) |

**Limitations acknowledged a priori.** (1) Any operational definition of a field is a proxy; it is triangulated across four definitions and conclusions are stated only where they agree in direction. (2) The tag correction assumes that RCT reports without randomization vocabulary in title or abstract are negligible; a plausibility check is reported, the assumption is not fully testable. (3) The trial level is reached only for records that report a registration identifier; coverage is reported per field and an upper bound is given; denominators remain records. (4) No perfect young-field analogue exists; two complementary controls of different kind are used. (5) The dataset is a snapshot of one continuously changing database; within-day volatility is quantified, and results apply to MEDLINE-indexed literature. (6) Publication-type and check-tag assignment by NLM is not observable; it is characterized empirically in both directions and in both fields, not eliminated.

**Reference documents.** Study Concept v1.1 (4 September 2026) and the project status file are the source of the design decisions D1 to D20 and M1 to M10 and are deposited on OSF together with this registration.
