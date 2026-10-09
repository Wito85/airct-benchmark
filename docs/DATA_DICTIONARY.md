# Data dictionary (Q10)

Study-specific data dictionary of the AI-RCT Benchmark pipeline. Controlling documentation named in the registration: NCBI E-utilities documentation (NCBI Bookshelf NBK25499, NBK25500), NLM MeSH Browser (Descriptor Data 2026), PubMed publication-type definitions. Registration: https://osf.io/qkb9g/ (DOI 10.17605/OSF.IO/QKB9G). This version describes the outputs of pipeline v1.1.0, which implements Protocol Amendment v3.0 (`docs/AMENDMENT_v3_0.md`); everything registered in v2.0 is unchanged, and additions are marked "amendment".

Conventions. All timestamps are UTC in ISO 8601 with a trailing `Z` (`2026-10-12T08:15:03Z`). All CSV files are UTF-8, comma separated, RFC 4180 quoting, header row present, line terminator LF. Comment lines start with `#` and precede the header row. Empty cells mean "not available", never zero. Field keys are the registered keys of 12.3: `AI`, `STROKE`, `DM`, `MI`, `CVD`, `COVID`, `MOBAPP`, `CDSS`, `DXIMG`, `TELE`; subfield keys `SUB_ML`, `SUB_DL`, `SUB_NLP`, `SUB_NN`; panel member keys `DIS_<HEADING>` and `TECH_<DESCRIPTOR>` (upper case, spaces and punctuation replaced by underscores); amendment: GBD panel member keys `GBD_<CAUSE>` built in the same way from the GBD cause name, apostrophes dropped (for example `GBD_ISCHEMIC_HEART_DISEASE`, `GBD_HIV_AIDS`, `GBD_ALZHEIMERS_DISEASE_AND_OTHER_DEMENTIAS`). SHA-256 values of text files (catalogue, panel file, deposited GBD files) are computed on the UTF-8 content with LF line endings, so that they are the same on every platform; SHA-256 values in manifests and of the raw IHME files are computed on the file bytes.

## 1. Frozen count files: `counts_frozen_<YYYYMMDD>_run<A|B>.csv` (12.10)

Comment header, one `#` line each: `airct_benchmark frozen count file`, `run`, `retrieval_start_utc`, `retrieval_end_utc`, `git_commit` (suffix `(dirty working tree)` when uncommitted changes existed), `git_describe`, `source_sha256` (SHA-256 over the Python sources of the package `airct_benchmark/*.py`: for every file in the order of the file names, the file name, the length of the content and the content with LF line endings; it identifies the code also where no git checkout exists or the working tree holds uncommitted files, and it is recomputed from a release with `airct_benchmark.util.source_fingerprint`), `pipeline_version`, `eutils_base_url`, `catalogue_sha256` (SHA-256 of `config/catalogue.yaml` as executed), `gbd_panel_sha256` (SHA-256 of `config/gbd_panel.yaml` as executed, with its status), `registration`, `amendment`, `python`, `queries`, `columns`, `requests_sent`, `failed_cells`, `cells_with_pubmed_warnings_or_errors`.

One row per cell, in catalogue order. First the registered cells exactly as in v1.0 (families in the order A, B, C, D, E, F, G, H, I, J, K, M, N, Q, R, U, W, Y; within a family by field order of 12.5 and 12.6, then metric, then year), then the amendment cells (families in the order DB, DC, MD, ME, GA, GD, GE, DV, QV, WV, KV, JV, RS; within a family by field, metric, year). GBD panel members that coincide with a named field have no rows in families GA, GD and GE; their counts are the rows named in `shared_cells.json` (Section 4).

| Column | Type | Definition |
|---|---|---|
| `run` | text | Run label within the freeze session: `A` (analysis dataset) or `B` (within-day volatility diagnostic, E11). |
| `family` | text | Query family: a letter of 12.6 (A to K, M, N, Q, R, U, W, Y) or a two-letter code of Amendment v3.0, Section 4 (DB, DC, MD, ME, GA, GD, GE, DV, QV, WV, KV, JV, RS). L, LV and O are list and XML families and produce no count rows. P, S, T, V, X are unused letters of the registration. |
| `field` | text | Field key, subfield key, panel member key or GBD panel member key (see conventions). |
| `year` | integer | Publication year of the year clause `AND ("YYYY"[pdat])`, 2015 to 2024 (COVID-19: 2020 to 2024; families R and RS: 2024 only). |
| `metric` | text | Metric within the family. Registered: `den` (human-subject denominator), `rct` (`"Randomized Controlled Trial"[pt]`), `ct` (`"Clinical Trial"[pt]`), `overlap` (field AND AI, family D), `all` (no Humans restriction, family I), `medline` (`medline[sb]`, family I), `rct_noprot` (RCT NOT `"Clinical Trial Protocol"[pt]`, family J), `S` and `R` (enriched untagged stratum and remainder stratum, family R), `rev` and `prim` (review-type and primary-article counts, family Y). Amendment: see the table below. |

Amendment families and their metrics (templates in `config/catalogue.yaml`, section `amendment_families`; "AI" is `"Artificial Intelligence"[Mesh]`):

| Family | Fields | Metrics | Cell content |
|---|---|---|---|
| `DB` | nine comparators | `rct` | field AND AI, human-subject base, RCT-tagged (numerator of the within-field AI share; the denominator is family D `overlap`) |
| `DC` | nine comparators | `ct` | field AND AI, human-subject base, Clinical Trial publication type |
| `MD` | 21 disease-panel headings | `den`, `rct` | heading AND AI, human-subject base |
| `ME` | 21 disease-panel headings | `den`, `rct` | heading NOT AI, human-subject base |
| `GA` | GBD panel members | `den`, `rct` | GBD expression, human-subject base |
| `GD` | GBD panel members | `den`, `rct` | GBD expression AND AI, human-subject base |
| `GE` | GBD panel members | `den`, `rct` | GBD expression NOT AI, human-subject base |
| `DV` | STROKE | `ai_vocab_den`, `ai_vocab_rct`, `nonai_vocab_den`, `nonai_vocab_rct` | stroke with and without the vocabulary-stable AI definition (F_AI_VOCAB2015) |
| `DV` | STROKE | `ai_tiab_den`, `ai_tiab_rct`, `nonai_tiab_den`, `nonai_tiab_rct` | stroke, MEDLINE-indexed, with and without the AI text words |
| `QV` | STROKE | `ai_den`, `ai_rct`, `nonai_den`, `nonai_rct` | stroke with and without AI on the unrestricted base (no Humans clause) |
| `WV` | STROKE | `ai_norob_den`, `ai_norob_rct` | stroke AND (AI NOT Robotics), human-subject base |
| `KV` | STROKE | `ai_den`, `ai_rct`, `nonai_den`, `nonai_rct` | stroke with and without AI on the original-research base (X_NONRESEARCH removed) |
| `JV` | STROKE | `ai_rct_noprot`, `nonai_rct_noprot` | stroke with and without AI, RCT-tagged, protocols removed |
| `RS` | STROKE, 2024 | `S_ai`, `S_nonai` | enriched untagged stroke stratum with and without AI |

In families with `_den` and `_rct` pairs, and in families with `den` and `rct`, the RCT metric is the denominator string with `AND "Randomized Controlled Trial"[pt]` inserted before the year clause.

Remaining columns:

| Column | Type | Definition |
|---|---|---|
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

## 4. Query list, snapshots and shared cells: `queries.json`, `catalogue_snapshot.yaml`, `gbd_panel_snapshot.yaml`, `shared_cells.json`

`queries.json`: ordered list of objects with `query_id`, `family`, `field`, `year`, `metric`, `term`, identical to the rows of the frozen files. `catalogue_snapshot.yaml` and `gbd_panel_snapshot.yaml`: byte copies of `config/catalogue.yaml` and `config/gbd_panel.yaml` as executed. The header of the frozen files states their SHA-256 on the content with LF line endings (see conventions).

`shared_cells.json` (amendment, Section 5.2): one object per cell of a GBD panel member that coincides with a named field. Keys: `gbd_member` (for example `GBD_STROKE`), `family` (`GA`, `GD` or `GE`), `metric`, `year`, `query` (the composed string), `held_by_query_id`, `held_by_family`, `held_by_field`, `held_by_metric` (the row of the frozen file that holds the count: `GA/den` in `A/den`, `GA/rct` in `B/rct`, `GD/den` in `D/overlap`, `GD/rct` in `DB/rct`, `GE/den` in `E/den`, `GE/rct` in `E/rct`). The string of the GBD cell and the string of the holding cell are identical; the pipeline verifies this for every cell at every start, before any request. A member shared with a named field of a shorter year window (COVID-19, 2020 to 2024) has objects for the years of that window only; for earlier years it has no cell, neither requested nor shared.

## 5. Smoke test: `smoke_<UTC>.json`

Keys: `mode`, `utc`, `query_id`, `query`, `count`, `querytranslation`, `http_status`, `attempt`, `error`, `errorlist`, `warninglist`, `reference_count` (Q18 value of 4 September 2026), `reference_source`, `difference` (`count` minus `reference_count`; informational), `pipeline_version`, `git`, `source_sha256` (as in the header of the frozen files), `raw_path`.

## 6. PMID lists (families L and LV): `pmid_lists/pmids_<list>_2024.txt`, `lists_meta.json`, `partition_report.json`

Text files with one PMID per line, in ascending order, duplicates across pages removed (`retmax`/`retstart` paging, or the history server with `efetch rettype=uilist` above 10,000 identifiers). A list is written only when the number of identifiers retrieved equals the count of the same request; otherwise it is read again (up to three readings) and the run stops if they still differ.

Family L (registered), `<B|S|R>_<AI|STROKE>`: `B` RCT-tagged records (family B query), `S` enriched untagged stratum, `R` remainder stratum (family R queries).

Family LV (amendment), stroke only: `DB_STROKE` RCT-tagged stroke records with the AI heading (family DB query), `ERCT_STROKE` RCT-tagged stroke records without it (family E RCT query), `SAI_STROKE` and `SNONAI_STROKE` the enriched untagged stroke stratum with and without the AI heading (family RS queries).

`lists_meta.json` records the run (`utc_start`, `year`, `pipeline_version`, `git`, `source_sha256`, `catalogue_sha256`, `gbd_panel_sha256`, as in the header of the frozen files) and, under `lists`, per list: `query_id` (`L_<FIELD>_<cell>_2024` or `LV_<FIELD>_<cell>_2024`), `list_family`, `query`, `count` (esearch count), `retrieved` (identifiers received; equals `count`), `querytranslation`, `utc`, `http_status`, `attempt`, `notes` (for example an earlier reading that was incomplete).

`lists_failed.json` (only when a lists run stopped): `utc`, `reason`, `note`. A directory that holds this file contains no validation sample to be rated.

`partition_report.json`: for `B_STROKE` against `DB_STROKE` plus `ERCT_STROKE`, and for `S_STROKE` against `SAI_STROKE` plus `SNONAI_STROKE`: `whole_size`, `part_sizes`, `union_size`, `only_in_whole`, `only_in_parts`, `in_more_than_one_part` (PMID lists) and `consistent`. The lists are read one after another from a live database; a difference is reported and never corrected.

## 7. Samples (Q13, Q14): `samples/sample_<cell>.csv`, `sampling_report.json`

Cells of Amendment v3.0, Section 6.1 (the stroke cells of v2.0 are split by AI status): `V-AI` (source list `B_AI`), `V-STROKE-AI` (`DB_STROKE`), `V-STROKE-nonAI` (`ERCT_STROKE`), `U-AI` (`S_AI`), `U-STROKE-AI` (`SAI_STROKE`), `U-STROKE-nonAI` (`SNONAI_STROKE`), `R-AI` (`R_AI`), `R-STROKE` (`R_STROKE`). A V-cell or U-cell with 200 records or fewer is a census: every record is in the formal set, no pilot is drawn from the cell and there is no replacement queue. A larger cell is a seeded sample.

| Column | Definition |
|---|---|
| `cell` | Cell name. |
| `set` | `pilot` (20 records drawn first, codebook calibration only, not in the formal set; none in a census cell) or `formal` (validation set: all records of a census cell, otherwise 200; 50 for the R check). |
| `order` | Position within the set (1-based), following the seeded sequence (decision I1). |
| `pmid` | PubMed identifier. |

The sample files are written twice: after the draw, and again at the end of the run with the final sets, in which a replacement (Q14) stands in the place of the PMID it replaced. With `--no-efetch` they hold the draw as made (`xml_checked` false in the report).

`sampling_report.json`: `seed` (20260904), `rule`, `xml_checked`, `cells` (per cell: `cell`, `source_list`, `population_size`, `rule` (`census` or the seeded sample rule), `pilot`, `formal`, `reserve` (remaining seeded sequence, replacement queue), `replacements` (list of `{missing, replacement, set}` after Q14; `replacement` is null in a census cell or when the queue is exhausted), `notes`, `missing_after_replacement` (PMIDs of the final pilot and formal sets without XML after six attempts)), `census_lists_missing` (PMIDs of the complete B lists that efetch did not return in six attempts).

## 8. XML (family O): `xml/<key>/batch_<nnnn>.xml`, `efetch_report.json`

Complete efetch responses (`retmode=xml`, batches of 200) for `B_AI`, `B_STROKE` (every record) and for the cells `U-AI`, `U-STROKE-AI`, `U-STROKE-nonAI`, `R-AI`, `R-STROKE`. V-cells are subsets of the B lists and use the B XML (`V-AI` of `B_AI`; `V-STROKE-AI` and `V-STROKE-nonAI` of `B_STROKE`). A record of a split stroke list that is not in the XML of the complete list (it entered the database between the two list requests) is fetched under the split list, `xml/DB_STROKE/` or `xml/ERCT_STROKE/`. A batch file is written for every response that holds at least one requested record.

`efetch_report.json` per key (complete list, split list with extra records, or cell): `requested`, `returned`, `missing` (not returned in six attempts), `batches` (files written), `methods` (`GET`, `POST`), `attempts` (1 to 6); for V-cells `xml_source` (the directories that hold the XML of the cell) and, where records of the cell had to be requested for the cell itself, `fetched_directly` (their XML is in `xml/<cell>/`).

## 9. Registration identifiers (12.8, S8): `identifiers/identifiers_2024.csv`, `identifiers_summary.json`

| Column | Definition |
|---|---|
| `field` | `AI` or `STROKE` (record taken from the respective complete B list). A record that is in both lists has its rows under each field. |
| `pmid` | PubMed identifier. |
| `registry` | Registry class after normalization: `ClinicalTrials.gov`, `ISRCTN`, `EudraCT`, `DRKS`, `ACTRN`, `ChiCTR`, `UMIN`, `CTRI`, `NTR`, `NL`, `IRCT`, `JPRN`, `jRCT`, `PACTR`, or the DataBankName for other whitelisted trial registries. JPRN-prefixed UMIN and jRCT numbers are classified as UMIN and jRCT. |
| `identifier` | Normalized identifier (upper case, whitespace removed, separators unified) used for deduplication within field. |
| `source` | `databank` (DataBankList accession), `title` or `abstract` (regular-expression match). |
| `raw` | Text as found (`<DataBankName>:<AccessionNumber>` for databank entries). |

`identifiers_summary.json` per field: `records`, `records_with_identifier`, `records_without_identifier`, `distinct_identifiers`, `distinct_identifiers_by_registry`, `upper_bound_trials` (distinct identifiers plus records without identifier, 12.9), `note`. Amendment: under the key `subsets` the same summary for `DB_STROKE` and `ERCT_STROKE` (stroke records with and without the AI heading; identifiers taken from the same XML and split by the family LV lists). A trial registered in two registries counts twice (Q23); resolution is an analysis-step decision.

## 10. Rating sheet (Q24): `rating_<cell>.csv` produced by `ratingsheet`

One sheet per rater and cell. Columns `pmid`, `year`, `journal`, `title`, `abstract` are filled by the pipeline; MeSH terms and publication types are deliberately absent. `V1` to `V6`, `rater`, `comment` are filled by the rater. Codes of 12.7 (final definitions and examples fixed in the pilot):

| Variable | Applies to | Codes |
|---|---|---|
| `V1` Report type | all cells | `primary` (primary report of an RCT, main results), `secondary` (secondary analysis: post hoc, subgroup, long-term follow-up, economic or process evaluation, pooled analysis), `protocol` (protocol or design paper), `not_rct` (non-randomized, observational, review, commentary, other), `unclear` |
| `V2` Randomization unit | if V1 is `primary` or `secondary` | `individual`, `cluster`, `crossover` (crossover or within-subject), `other` |
| `V3` Role of AI | `V-AI`, `V-STROKE-AI`, `U-AI`, `U-STROKE-AI` (amendment, Section 6.2) | `ai_intervention` (AI system is the intervention or an integral component of the randomized comparison), `robotic_no_learning` (robotic or automated system without a learning or inference component; enters through the Robotics subtree, decision M10), `analytic_tool` (AI used as an analytic tool on trial data), `peripheral` (mentioned peripherally or used as an outcome or measurement instrument), `no_ai` (indexing error), `unclear` |
| `V4` Setting | if V3 is `ai_intervention` | `real_care` (real clinical care with patient-level or clinician-level outcomes), `simulated` (simulated or reader-study setting), `other` |
| `V5` Field relevance | all STROKE cells (amendment, Section 6.2) | `target` (stroke is the target condition or population), `peripheral`, `no_stroke` |
| `V6` Registration identifier seen | all cells | verbatim identifier(s) visible in title or abstract, separated by `;`, or empty |
| `rater` | | rater key: `WP` (Polanski) or `MP` (Prem) |
| `comment` | | free text, optional |

Full text is consulted when title and abstract do not allow coding; the rater records this in `comment`.

## 11. Validation dataset (merged, Step 5)

One row per record of the formal sets (pilot records are kept in a separate file). Columns: `cell`, `pmid`, `year`, `journal`, `title`, `abstract`, then for each variable `V1` to `V6` the columns `<V>_WP`, `<V>_MP` and `<V>_adj` (adjudicated value by Eyüpoglu where the raters disagree, otherwise the agreed value), `disagreement_<V>` (`1`/`0` for V1, V3, V5), `full_text_consulted_WP`, `full_text_consulted_MP`, `adjudication_note`. Kappa and percent agreement (Q24) are computed from the `_WP` and `_MP` columns of V1, V3 and V5 per cell.

## 12. Manifest and log

`MANIFEST_SHA256.txt`: `sha256sum` format (`<hex digest>  <relative path>`), one line per file of the output directory including the log; written as the last action of a run. `run_<UTC>.log`: complete run log, API key redacted.

## 13. Amendment syntax check: `syntax_check_<UTC>/` (amendment, Sections 1.4, 8.3 and 8.10)

Written by `syntax-check --send`, before the freeze run, publication year 2015 only.

`syntax_check_<UTC>.json`: `mode`, `rule`, `utc_start`, `utc_end`, `pipeline_version`, `git`, `source_sha256` (as in the header of the frozen files), `catalogue_sha256`, `gbd_panel_sha256`, `requests_sent`, `earlier_runs_in_the_output_directory`, `reason_for_repetition`, `results`, `identities`, `needs_review` (check ids), `identities_not_met` (names). Trial numerators within a field (families DB, DC, JV and every RCT metric) are not part of the check. Each object of `results`: `group` (`anchor`: registered smoke cell of Diabetes Mellitus 2015 disclosed in Q18; `composition`: new composition of Section 4; `gbd_descriptor`: GBD descriptor that is new relative to v2.0), `check_id` (`<family>/<metric>`, for descriptors `GA/den:<GBD key>`), `family`, `metric`, `field` (the field the request was composed for: `DM`, or the GBD key), `term` (the string sent), `note`, `catalogue_query_id` (id of the identical catalogue cell, or null: the stroke-only compositions are run with Diabetes Mellitus in place of Stroke and are no catalogue cells), `reference_count` (Q18 value of an anchor), `count`, `querytranslation`, `utc`, `http_status`, `attempt`, `error`, `pubmed_messages`, `valid_zero_no_items_found`, `pattern_notes` (departures of the query translation from the form recorded in Q18: number of terms per field tag, every MeSH heading under its own name, number of NOT operators, publication-date range; the grouping of operators is not parsed), `review_notes` (for example a descriptor introduced before 2015 without a record in 2015), `info_notes`, `raw_path`. Each object of `identities`: `name`, `type` (`equal` or `at_most`), `left`, `right` (check ids; a leading minus sign subtracts), `left_value`, `right_value`, `status`.

`syntax_check_<UTC>.csv`: `group`, `check_id`, `query`, `querytranslation`, `count`, `reference_count`, `utc`, `http_status`, `attempt`.

`q18_addendum_<UTC>.md`: the same content as text and table, written for Section 8.10 of the amendment (Q18 addendum). Raw responses, log, snapshots and manifest as in Sections 3, 4 and 12.

## 14. GBD panel files (amendment, Section 5)

`config/gbd_panel.yaml` (generated by `scripts/gbd_panel.py`): `status` (`final` or `provisional`), `provenance` (free text, provisional panels), `test_fixture` (true only in the synthetic panel of the test suite), `source` (`gbd_round`, `citation`, `quantity`, `selection_rule`, `mapping_table`, `mapping_table_sha256`, `ranking_sha256`, `raw_export_sha256`, `candidates_sha256`, `raters`; a final panel must state the raters and the three first hashes), `members`: `rank` (rank among all Level 3 causes by global DALY count 2023), `key`, `cause` (GBD cause name as exported), `expression` (the string used as {G}), `mesh_ui`, `date_introduced` (NLM MeSH, Date Introduced), `in_trajectory` (false when the descriptor was introduced after 2015: 2024 and pooled windows only, panel rule of Q13), `shared_with` (key of the named field whose cells hold the counts, or null), `scope_relation` (`exact`, `broader`, `narrower`, or `mixed` when over- and under-inclusion are both stated), `inclusion_note`.

`data/gbd/gbd2023_level3_ranking.csv`: one row per Level 3 cause of GBD 2023 in descending order of the global DALY count 2023: `rank`, `cause_id`, `cause_name`, `level1_group` (`NCD`, `CMNN`, `Injuries`), `panel_rule_result` (`kept for mapping` or `excluded`), `exclusion_reason` (rule a, b or c). DALY values are not part of this file.

`data/gbd/gbd_export_record.json`: `source`, `source_identifier`, `data_path`, `settings` (measure, metric, location, age, sex, year, cause), `stratum_as_named_in_the_export` (the names of measure, location, sex, age and metric as the export writes them, in the interface language of the tool), `stratum_identified_by`, `data_citation_delivered_with_the_download` (text of the citation file of the download, or empty), `permalink`, `exported_by`, `export_date`, `ranked_utc`, `raw_export` (`file_name`, `sha256`, `rows`), `cause_hierarchy` (`file_name`, `sha256`, `read_from`), `level3_causes_ranked` (number of ranked causes), `all_causes_check` (`done`, `level3_sum_over_all_causes`, `tolerance`: the DALY counts of the ranked causes must add up to the value of "All causes"), `export_aggregates_outside_hierarchy_ignored` (aggregates across causes, names beginning with "Total"), `export_causes_outside_hierarchy_not_ranked` (other causes of the export that the hierarchy file does not list; tolerated only when the completeness check was passed), `hierarchy_aggregates_not_ranked` (aggregates that the hierarchy file lists at Level 1 to 3), `causes_above_level_3_ranked_as_themselves` (a cause of Level 1 or 2 without causes below it; ranked with the Level 3 causes, as GBD reports it, and accepted only when rule (a), (b) or (c) excludes it), `names_spelled_differently_in_export_and_hierarchy`, `notes`, `ranking_with_values_kept_by_the_authors` (`file_name`, `sha256`), `ranking_public` (`file`, `sha256`), `hash_rule`, `note`. The raw export, the hierarchy file and the ranking with values are kept by the authors and are not redistributed.

`data/gbd/gbd_mesh_candidates.csv`: the proposals shown to the raters. `gbd_cause`, `role` (`proposed`, `registered` for a named field, `alternative`, `no single descriptor`), `expression`, `mesh_ui`, `date_introduced`, `tree_numbers`, `scope_relation`, `mesh_scope_note`, `narrower_descriptors`, `inclusion_note`, `alternatives`, `decision_needed`, `verified` (source and date of the MeSH facts), `shared_with`.

`data/gbd/gbd_panel_mesh_mapping.csv` (written by `reconcile`): one row per rated cause: `rank`, `cause_id`, `gbd_cause`, `level1_group`, `decision` (`mapped` or `excluded rule (d)`), `expression`, `mesh_ui`, `date_introduced`, `scope_relation`, `inclusion_note`, `choice_<rater 1>`, `choice_<rater 2>` (each rater's independent choice), `reconciliation` (`agreed independently` or `agreed after discussion`), `comment_<rater 1>`, `comment_<rater 2>`, `comment_consensus` (reason entered in the consensus sheet). The raters stand in the alphabetical order of their keys. The first 20 mapped causes in rank order are the panel.

`data/gbd/gbd_panel_amendment_table.md`: the panel table for Section 5 of the amendment, with the causes excluded above the last panel member, the hashes and the catalogue volume. `data/gbd/rating/gbd_mapping_rater_<key>.xlsx`: the rater sheets as filled in, one per rater: `rank`, `gbd_cause`, `proposed_expression`, `mesh_ui`, `mesh_browser_link`, `date_introduced`, `scope_relation`, `mesh_scope_note`, `narrower_descriptors`, `inclusion_note`, `alternatives` (pre-filled), and `DECISION` (`agree`, `use alternative`, `no single descriptor (rule d)`), `ALTERNATIVE_EXPRESSION`, `COMMENT` (filled in by the rater). `data/gbd/rating/gbd_mapping_consensus.xlsx` (only if the raters differed): the rows in question with both choices and comments and the agreed `DECISION`, `ALTERNATIVE_EXPRESSION`, `COMMENT`.
