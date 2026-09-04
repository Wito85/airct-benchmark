# Data dictionary (Q10)

Study-specific data dictionary of the AI-RCT Benchmark pipeline. Controlling documentation named in the registration: NCBI E-utilities documentation (NCBI Bookshelf NBK25499, NBK25500), NLM MeSH Browser (Descriptor Data 2026), PubMed publication-type definitions. Registration: https://osf.io/qkb9g/ (DOI 10.17605/OSF.IO/QKB9G).

Conventions. All timestamps are UTC in ISO 8601 with a trailing `Z` (`2026-10-12T08:15:03Z`). All CSV files are UTF-8, comma separated, RFC 4180 quoting, header row present, line terminator LF. Comment lines start with `#` and precede the header row. Empty cells mean "not available", never zero. Field keys are the registered keys of 12.3: `AI`, `STROKE`, `DM`, `MI`, `CVD`, `COVID`, `MOBAPP`, `CDSS`, `DXIMG`, `TELE`; subfield keys `SUB_ML`, `SUB_DL`, `SUB_NLP`, `SUB_NN`; panel member keys `DIS_<HEADING>` and `TECH_<DESCRIPTOR>` (upper case, spaces and punctuation replaced by underscores).

## 1. Frozen count files: `counts_frozen_<YYYYMMDD>_run<A|B>.csv` (12.10)

Comment header, one `#` line each: `airct_benchmark frozen count file`, `run`, `retrieval_start_utc`, `retrieval_end_utc`, `git_commit` (suffix `(dirty working tree)` when uncommitted changes existed), `git_describe`, `pipeline_version`, `eutils_base_url`, `catalogue_sha256` (SHA-256 of `config/catalogue.yaml` as executed), `registration`, `python`, `queries`, `columns`, `requests_sent`, `failed_cells`, `cells_with_pubmed_warnings_or_errors`.

One row per registered cell, in catalogue order (families in the order A, B, C, D, E, F, G, H, I, J, K, M, N, Q, R, U, W, Y; within a family by field order of 12.5 and 12.6, then metric, then year).

| Column | Type | Definition |
|---|---|---|
| `run` | text | Run label within the freeze session: `A` (analysis dataset) or `B` (within-day volatility diagnostic, E11). |
| `family` | text | Query family letter of 12.6 (A to K, M, N, Q, R, U, W, Y). L and O are list and XML families and produce no count rows. P, S, T, V, X are unused letters of the registration. |
| `field` | text | Field key, subfield key or panel member key (see conventions). |
| `year` | integer | Publication year of the year clause `AND ("YYYY"[pdat])`, 2015 to 2024 (COVID-19: 2020 to 2024; family R: 2024 only). |
| `metric` | text | Metric within the family: `den` (human-subject denominator), `rct` (`"Randomized Controlled Trial"[pt]`), `ct` (`"Clinical Trial"[pt]`), `overlap` (field AND AI, family D), `all` (no Humans restriction, family I), `medline` (`medline[sb]`, family I), `rct_noprot` (RCT NOT `"Clinical Trial Protocol"[pt]`, family J), `S` and `R` (enriched untagged stratum and remainder stratum, family R), `rev` and `prim` (review-type and primary-article counts, family Y). |
| `query` | text | The complete esearch `term` sent to PubMed, composed character for character from the templates of Q12 (12.2). |
| `querytranslation` | text | PubMed's `esearchresult.querytranslation` for that request, verbatim (audit field, decision T1). |
| `count` | integer or empty | `esearchresult.count` of the successful request. Empty when the cell failed after six attempts or PubMed returned an error (see `issues` file). |
| `utc` | text | Time of the request attempt whose response is recorded, UTC. |
| `http_status` | integer or empty | HTTP status of that attempt (200 for a success; the last attempt's status for a failed cell; empty when no HTTP response was received, for example a timeout on every attempt). |
| `attempt` | integer | Attempt number of the recorded response (1 to 6). Values above 1 indicate that HTTP 429, 5xx or a transport error occurred before. |

## 2. Issues file: `issues_<YYYYMMDD>_run<A|B>.jsonl`

One JSON object per line for every cell with a PubMed `errorlist` or `warninglist` (for example `quotedphrasesnotfound`, `phrasesignored`, `outputmessages`), a PubMed `ERROR`, or a failed request. Keys: `run`, `query_id` (`<family>_<field>_<metric>_<year>`), `query`, `count`, `error`, `errorlist`, `warninglist`, `http_status`, `attempt`, `utc`, `raw_path`. A warning does not invalidate a count; the analysis step decides case by case and reports it.

## 3. Raw responses: `raw/run<A|B>/<label>__a<attempt>__<UTC>.json`

One file per request attempt (counts) or per efetch batch. Keys: `utc`, `endpoint` (`esearch` or `efetch`), `method` (`GET` or `POST`), `params` (all request parameters, `api_key` removed), `http_status`, `attempt`, `label`, `error` (transport error text, or null), `body` (the complete response text as received, or null when no response was received). The count in a frozen row is `esearchresult.count` of the body of the file whose label is `<run>__<query_id>` and whose attempt equals the row's `attempt`.

## 4. Query list and catalogue snapshot: `queries.json`, `catalogue_snapshot.yaml`

`queries.json`: ordered list of objects with `query_id`, `family`, `field`, `year`, `metric`, `term`, identical to the rows of the frozen files. `catalogue_snapshot.yaml`: byte copy of `config/catalogue.yaml` as executed (its SHA-256 is in the CSV header).

## 5. Smoke test: `smoke_<UTC>.json`

Keys: `mode`, `utc`, `query_id`, `query`, `count`, `querytranslation`, `http_status`, `attempt`, `error`, `errorlist`, `warninglist`, `reference_count` (Q18 value of 4 September 2026), `reference_source`, `difference` (`count` minus `reference_count`; informational), `pipeline_version`, `git`, `raw_path`.

## 6. PMID lists (family L): `pmid_lists/pmids_<B|S|R>_<AI|STROKE>_2024.txt`, `lists_meta.json`

Text files with one PMID per line in the order returned by PubMed (`retmax`/`retstart` paging, or the history server with `efetch rettype=uilist` above 10,000 identifiers). `B`: RCT-tagged records (family B query), `S`: enriched untagged stratum, `R`: remainder stratum (family R queries). `lists_meta.json` records per list: `query_id`, `query`, `count` (esearch count), `retrieved` (identifiers received; equals `count` unless noted), `querytranslation`, `utc`, `http_status`, `attempt`, `notes`.

## 7. Samples (Q13, Q14): `samples/sample_<cell>.csv`, `sampling_report.json`

Cells: `V-AI`, `V-STROKE` (source lists `B_AI`, `B_STROKE`), `U-AI`, `U-STROKE` (source `S_*`), `R-AI`, `R-STROKE` (source `R_*`).

| Column | Definition |
|---|---|
| `cell` | Cell name. |
| `set` | `pilot` (20 records drawn first, codebook calibration only, not in the formal set) or `formal` (validation set: all records of a census V-cell, otherwise 200; 50 for the R check). |
| `order` | Position within the set (1-based), following the seeded sequence (decision I1). |
| `pmid` | PubMed identifier. |

`sampling_report.json`: `seed` (20260904), `rule`, `cells` (per cell: `cell`, `source_list`, `population_size`, `rule` (`census` or the seeded sample rule), `pilot`, `formal`, `reserve` (remaining seeded sequence, replacement queue), `replacements` (list of `{missing, replacement, set}` after Q14), `notes`, `missing_after_replacement`), `census_lists_missing` (PMIDs of the complete B lists that efetch did not return).

## 8. XML (family O): `xml/<key>/batch_<nnnn>.xml`, `efetch_report.json`

Complete efetch responses (`retmode=xml`, batches of 200) for `B_AI`, `B_STROKE` (every record) and for the sampled cells `U-AI`, `U-STROKE`, `R-AI`, `R-STROKE`. V-cells are subsets of the B lists and use the B XML. `efetch_report.json` per key: `requested`, `returned`, `missing`, `batches`, `methods` (`GET`, `POST`), for V-cells additionally `xml_source`.

## 9. Registration identifiers (12.8, S8): `identifiers/identifiers_2024.csv`, `identifiers_summary.json`

| Column | Definition |
|---|---|
| `field` | `AI` or `STROKE` (record taken from the respective complete B list). |
| `pmid` | PubMed identifier. |
| `registry` | Registry class after normalization: `ClinicalTrials.gov`, `ISRCTN`, `EudraCT`, `DRKS`, `ACTRN`, `ChiCTR`, `UMIN`, `CTRI`, `NTR`, `NL`, `IRCT`, `JPRN`, `jRCT`, `PACTR`, or the DataBankName for other whitelisted trial registries. JPRN-prefixed UMIN and jRCT numbers are classified as UMIN and jRCT. |
| `identifier` | Normalized identifier (upper case, whitespace removed, separators unified) used for deduplication within field. |
| `source` | `databank` (DataBankList accession), `title` or `abstract` (regular-expression match). |
| `raw` | Text as found (`<DataBankName>:<AccessionNumber>` for databank entries). |

`identifiers_summary.json` per field: `records`, `records_with_identifier`, `records_without_identifier`, `distinct_identifiers`, `distinct_identifiers_by_registry`, `upper_bound_trials` (distinct identifiers plus records without identifier, 12.9), `note`. A trial registered in two registries counts twice (Q23); resolution is an analysis-step decision.

## 10. Rating sheet (Q24): `rating_<cell>.csv` produced by `ratingsheet`

One sheet per rater and cell. Columns `pmid`, `year`, `journal`, `title`, `abstract` are filled by the pipeline; MeSH terms and publication types are deliberately absent. `V1` to `V6`, `rater`, `comment` are filled by the rater. Codes of 12.7 (final definitions and examples fixed in the pilot):

| Variable | Applies to | Codes |
|---|---|---|
| `V1` Report type | all cells | `primary` (primary report of an RCT, main results), `secondary` (secondary analysis: post hoc, subgroup, long-term follow-up, economic or process evaluation, pooled analysis), `protocol` (protocol or design paper), `not_rct` (non-randomized, observational, review, commentary, other), `unclear` |
| `V2` Randomization unit | if V1 is `primary` or `secondary` | `individual`, `cluster`, `crossover` (crossover or within-subject), `other` |
| `V3` Role of AI | AI cells only | `ai_intervention` (AI system is the intervention or an integral component of the randomized comparison), `robotic_no_learning` (robotic or automated system without a learning or inference component; enters through the Robotics subtree, decision M10), `analytic_tool` (AI used as an analytic tool on trial data), `peripheral` (mentioned peripherally or used as an outcome or measurement instrument), `no_ai` (indexing error), `unclear` |
| `V4` Setting | if V3 is `ai_intervention` | `real_care` (real clinical care with patient-level or clinician-level outcomes), `simulated` (simulated or reader-study setting), `other` |
| `V5` Field relevance | Stroke cells only | `target` (stroke is the target condition or population), `peripheral`, `no_stroke` |
| `V6` Registration identifier seen | all cells | verbatim identifier(s) visible in title or abstract, separated by `;`, or empty |
| `rater` | | rater key: `WP` (Polanski) or `MP` (Prem) |
| `comment` | | free text, optional |

Full text is consulted when title and abstract do not allow coding; the rater records this in `comment`.

## 11. Validation dataset (merged, Step 5)

One row per record of the formal sets (pilot records are kept in a separate file). Columns: `cell`, `pmid`, `year`, `journal`, `title`, `abstract`, then for each variable `V1` to `V6` the columns `<V>_WP`, `<V>_MP` and `<V>_adj` (adjudicated value by Eyüpoglu where the raters disagree, otherwise the agreed value), `disagreement_<V>` (`1`/`0` for V1, V3, V5), `full_text_consulted_WP`, `full_text_consulted_MP`, `adjudication_note`. Kappa and percent agreement (Q24) are computed from the `_WP` and `_MP` columns of V1, V3 and V5 per cell.

## 12. Manifest and log

`MANIFEST_SHA256.txt`: `sha256sum` format (`<hex digest>  <relative path>`), one line per file of the output directory including the log; written as the last action of a run. `run_<UTC>.log`: complete run log, API key redacted.
