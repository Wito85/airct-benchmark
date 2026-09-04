# Excerpt of Preregistration v2.0 (4 September 2026), Q12.3 to Q12.6

This excerpt reproduces the registered strings of Q12 with every expression on a single line. It was
transcribed from the registered document (OSF https://osf.io/qkb9g/) for the offline test of the
string-identity checker. The authoritative strict check of Step 3 runs against the registered
Markdown file Preregistration_v2.0_FINAL_2026-09-04.md.

12.1 Fixed request parameters. esearch with db=pubmed, retmode=json, retmax=0, tool=airct_benchmark, email=witold.polanski@ukdd.de, api_key from NCBI_API_KEY. Year clause appended to every count query: AND ("YYYY"[pdat]), YYYY from 2015 to 2024 (COVID-19: 2020 to 2024). efetch with db=pubmed, retmode=xml, batches of 200 PMIDs.

12.3 Field expressions.

| Key | Role | MeSH expression (exploded, verbatim) | Text-word expression for E2 and E7 (verbatim) |
|---|---|---|---|
| AI | exposure field | "Artificial Intelligence"[Mesh] | ("artificial intelligence"[tiab] OR "machine learning"[tiab] OR "deep learning"[tiab] OR "neural network"[tiab] OR "neural networks"[tiab]) |
| STROKE | primary comparator | "Stroke"[Mesh] | "stroke"[tiab] |
| DM | secondary disease comparator | "Diabetes Mellitus"[Mesh] | ("diabetes"[tiab] OR "diabetes mellitus"[tiab]) |
| MI | secondary disease comparator, narrow cardiovascular sensitivity | "Myocardial Infarction"[Mesh] | ("myocardial infarction"[tiab] OR "heart attack"[tiab]) |
| CVD | breadth supplement only, not interpreted as like-for-like | "Cardiovascular Diseases"[Mesh] | "cardiovascular disease"[tiab] |
| COVID | young-field control, disease-based, 2020 to 2024 | "COVID-19"[Mesh] | ("COVID-19"[tiab] OR "SARS-CoV-2"[tiab]) |
| MOBAPP | young-field control, technology-based, 2015 to 2024 (descriptor introduced 2014) | "Mobile Applications"[Mesh] | none |
| CDSS | technology comparator, function-matched | "Decision Support Systems, Clinical"[Mesh] | none |
| DXIMG | technology comparator, task-matched | "Diagnostic Imaging"[Mesh] | none |
| TELE | exploratory technology comparator | "Telemedicine"[Mesh] | none |

12.4 Auxiliary expressions.

H_HUM = "Humans"[Mesh]
YEAR = ("YYYY"[pdat])
N_RCT = "Randomized Controlled Trial"[pt]
N_CT = "Clinical Trial"[pt]
N_PROT = "Clinical Trial Protocol"[pt]
N_REV = (Review[pt] OR "Systematic Review"[pt] OR Meta-Analysis[pt])
N_PRIM = "Journal Article"[pt] NOT (Review[pt] OR "Systematic Review"[pt] OR Meta-Analysis[pt] OR Editorial[pt] OR Comment[pt] OR Letter[pt])
T_RCT = (randomized[tiab] OR randomised[tiab] OR randomly[tiab] OR placebo[tiab] OR trial[ti])
X_NONRESEARCH = (Review[pt] OR Editorial[pt] OR Letter[pt] OR Comment[pt] OR News[pt])
MEDLINE = medline[sb]
F_AI_VOCAB2015 = ("Artificial Intelligence"[Mesh:NoExp] OR "Expert Systems"[Mesh:NoExp] OR "Fuzzy Logic"[Mesh:NoExp] OR "Knowledge Bases"[Mesh:NoExp] OR "Natural Language Processing"[Mesh:NoExp] OR "Neural Networks, Computer"[Mesh:NoExp] OR "Robotics"[Mesh:NoExp])
F_AI_TIAB = ("artificial intelligence"[tiab] OR "machine learning"[tiab] OR "deep learning"[tiab] OR "neural network"[tiab] OR "neural networks"[tiab]) AND medline[sb]
F_AI_NOROB = ("Artificial Intelligence"[Mesh] NOT "Robotics"[Mesh])
SUB_ML = "Machine Learning"[Mesh]
SUB_DL = "Deep Learning"[Mesh]
SUB_NLP = "Natural Language Processing"[Mesh]
SUB_NN = "Neural Networks, Computer"[Mesh]

12.5 Reference panels (positioning only, decision D16).

Disease-category panel (21 members). Fixed list: "Infections"[Mesh]; "Neoplasms"[Mesh]; "Musculoskeletal Diseases"[Mesh]; "Digestive System Diseases"[Mesh]; "Stomatognathic Diseases"[Mesh]; "Respiratory Tract Diseases"[Mesh]; "Otorhinolaryngologic Diseases"[Mesh]; "Nervous System Diseases"[Mesh]; "Eye Diseases"[Mesh]; "Urogenital Diseases"[Mesh]; "Cardiovascular Diseases"[Mesh]; "Hemic and Lymphatic Diseases"[Mesh]; "Congenital, Hereditary, and Neonatal Diseases and Abnormalities"[Mesh]; "Skin and Connective Tissue Diseases"[Mesh]; "Nutritional and Metabolic Diseases"[Mesh]; "Endocrine System Diseases"[Mesh]; "Immune System Diseases"[Mesh]; "Occupational Diseases"[Mesh]; "Chemically-Induced Disorders"[Mesh]; "Wounds and Injuries"[Mesh]; "Mental Disorders"[Mesh].

Technology panel (9 members), predefined list: "Diagnostic Imaging"[Mesh]; "Telemedicine"[Mesh]; "Decision Support Systems, Clinical"[Mesh]; "Biomarkers"[Mesh]; "Robotic Surgical Procedures"[Mesh]; "Electronic Health Records"[Mesh]; "Mobile Applications"[Mesh]; "Wearable Electronic Devices"[Mesh]; "Point-of-Care Testing"[Mesh].

CLIN_ANY is the disjunction of all 21 disease-panel headings in the order listed, ("Infections"[Mesh] OR "Neoplasms"[Mesh] OR ... OR "Mental Disorders"[Mesh]), written out in full in the pipeline configuration.

12.6 Query families. {F} denotes a MeSH field expression of 12.3, {F_TIAB} its text-word expression, (...) the year clause ("YYYY"[pdat]). Every template is combined with every year of the field's window.

| Family | Use | Template | Fields |
|---|---|---|---|
| A | denominators | {F} AND "Humans"[Mesh] AND (...) | ten named fields |
| B | RCT numerators | {F} AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND (...) | ten named fields |
| C | Clinical Trial numerators (S4) | {F} AND "Humans"[Mesh] AND "Clinical Trial"[pt] AND (...) | ten named fields |
| D | overlap with AI (E3) | {F} AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND (...) | nine comparators |
| E | disjoint sets (E3) | ({F} NOT "Artificial Intelligence"[Mesh]) AND "Humans"[Mesh] AND (...); the same with AND "Randomized Controlled Trial"[pt] inserted before the year clause; the same with AND "Clinical Trial"[pt] | nine comparators |
| F | vocabulary-stable AI (E1) | {F_AI_VOCAB2015} AND "Humans"[Mesh] AND (...); the same with AND "Randomized Controlled Trial"[pt] | AI |
| G | text-word definitions (E2) | {F_TIAB} AND medline[sb] AND "Humans"[Mesh] AND (...); the same with AND "Randomized Controlled Trial"[pt] | AI, STROKE, DM, MI, CVD, COVID |
| H | subfields (E4) | {SUB} AND "Humans"[Mesh] AND (...); the same with AND "Randomized Controlled Trial"[pt] | SUB_ML, SUB_DL, SUB_NLP, SUB_NN |
| I | indexing completeness (E7) | {F_TIAB} AND (...) and {F_TIAB} AND medline[sb] AND (...); no Humans clause by design | AI, STROKE |
| J | protocol-excluded numerators (E6) | {F} AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] NOT "Clinical Trial Protocol"[pt] AND (...) | ten named fields |
| K | original-research base (E5) | {F} AND "Humans"[Mesh] NOT (Review[pt] OR Editorial[pt] OR Letter[pt] OR Comment[pt] OR News[pt]) AND (...); the same with AND "Randomized Controlled Trial"[pt] inserted before the year clause | ten named fields |
| L | PMID lists (S5, S7, S8, R-check) | the family B strings for AI and STROKE and the family R strings (S_f, R_f); esearch with retmax and retstart, or usehistory=y with retrieval from the history server when a list exceeds 10,000 | AI, STROKE, 2024 |
| M | disease panel (S9, E12) | {HEADING} AND "Humans"[Mesh] AND (...); the same with AND "Randomized Controlled Trial"[pt] | 21 headings |
| N | technology panel (S9) | {DESCRIPTOR} AND "Humans"[Mesh] AND (...); the same with AND "Randomized Controlled Trial"[pt] | 9 descriptors |
| O | efetch XML (S5, S7, S8) | efetch of every PMID in the family B lists for AI and STROKE and of the sampled PMIDs of S_f and R_f | AI, STROKE, 2024 |
| Q | unrestricted record base (E10) | {F} AND (...); {F} AND "Randomized Controlled Trial"[pt] AND (...) | AI, STROKE |
| R | strata (S7) | S_f: {F} AND "Humans"[Mesh] AND medline[sb] AND (randomized[tiab] OR randomised[tiab] OR randomly[tiab] OR placebo[tiab] OR trial[ti]) NOT "Randomized Controlled Trial"[pt] AND (...); R_f: {F} AND "Humans"[Mesh] AND medline[sb] NOT "Randomized Controlled Trial"[pt] NOT (randomized[tiab] OR randomised[tiab] OR randomly[tiab] OR placebo[tiab] OR trial[ti]) AND (...) | AI, STROKE, 2024 |
| U | disease-related AI subset (E12) | "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND {CLIN_ANY} AND (...); the same with AND "Randomized Controlled Trial"[pt] | AI |
| W | Robotics-excluded AI (E13) | ("Artificial Intelligence"[Mesh] NOT "Robotics"[Mesh]) AND "Humans"[Mesh] AND (...); the same with AND "Randomized Controlled Trial"[pt] | AI |
| Y | review and primary-article counts (E14) | {F} AND "Humans"[Mesh] AND (Review[pt] OR "Systematic Review"[pt] OR Meta-Analysis[pt]) AND (...); {F} AND "Humans"[Mesh] AND "Journal Article"[pt] NOT (Review[pt] OR "Systematic Review"[pt] OR Meta-Analysis[pt] OR Editorial[pt] OR Comment[pt] OR Letter[pt]) AND (...) | ten named fields |

Family letters P, S, T, V and X are not used.

Worked verbatim examples (AI, 2024):
- Family A: "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND ("2024"[pdat])
- Family B: "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2024"[pdat])
- Family G: ("artificial intelligence"[tiab] OR "machine learning"[tiab] OR "deep learning"[tiab] OR "neural network"[tiab] OR "neural networks"[tiab]) AND medline[sb] AND "Humans"[Mesh] AND ("2024"[pdat])
- Family Q (identical to the worked example of the draft): "Artificial Intelligence"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2024"[pdat])
- Family R, S_AI: "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND medline[sb] AND (randomized[tiab] OR randomised[tiab] OR randomly[tiab] OR placebo[tiab] OR trial[ti]) NOT "Randomized Controlled Trial"[pt] AND ("2024"[pdat])
- Family W: ("Artificial Intelligence"[Mesh] NOT "Robotics"[Mesh]) AND "Humans"[Mesh] AND ("2024"[pdat])
