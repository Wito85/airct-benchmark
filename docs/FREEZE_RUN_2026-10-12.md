# Freeze run record, 12 October 2026

Purpose. This file records the retrieval of the frozen dataset on the registered retrieval date (registration Q8 and Other; Amendment v3.0, Sections 7 and 8.15): the count runs (Run A and Run B), the lists run, the decisions taken on that day and the files deposited. Nothing in this file is a result of the study. Every number is taken from the run logs, the file headers or the reports named; fields in square brackets are completed by the person named. Times are UTC unless marked CEST.

## 1. Machine, code and people

* Pipeline lead at the keyboard: M. G. Prem (Windows 11, Python 3.13.3). Decisions: W. Polanski, guarantor, by message during the day. Reproductions on the same UTC day: Y. Hachem and C. H. Buszello (their own logs).
* Count runs: tag `v1.1.0`, commit `9e2a617bcaf844f4ff6aefdfc33803181a61e782`, source SHA-256 `0dd843f805e21965d81d7d89dab03a3a453d2d0397f53ceaffd2ee95afd6fa83`, catalogue SHA-256 `8677d96be620d527307ff29865e47a75cd97ef23c87f2b11eba649d7dd759f63`, GBD panel SHA-256 `b91fd005303816cc191301a73241b37b9db0850877742f947d51736476437f2c` (status final), checkout `airct-release`.
* Lists run: tag `v1.1.1`, commit `57e656525bf3972ffa6e30e0815e6522b837faf6`, source SHA-256 `1245b3a306c483b16f1fd9b1a7bd39c76a0dc4b21545b0f4c5ecc6e2d8aaa170`, same catalogue and panel hashes, checkout `airct-111` (docs/CODE_REVIEW_v1.1.1.md).
* API key: set in the environment variable for the count runs from 07:08 UTC and for the lists run [confirm from the first lines of the lists log, `api_key=present (not logged)`; Prem]; never written anywhere.

## 2. Count runs (freeze, families of the registration and of the amendment)

1. False start, 07:02:19 UTC. The command `freeze --out out` was started without the API key in the terminal window (warning `no API key in NCBI_API_KEY`), and the first request (cell `A__A_AI_den_2015`) could not reach `eutils.ncbi.nlm.nih.gov` (connect timeout of 60 seconds on attempts 1, 2 and 3, at 07:02:40, 07:03:02 and 07:03:25 UTC). On the instruction of the guarantor the run was aborted with Ctrl+C before any count had been retrieved, and its directory was kept as `out/freeze_20261012_fehlstart_0702Z` (deposited for documentation). Nothing from it is used.
2. Run A, 07:08:32 to 07:52:40 UTC: 4,326 cells (2,034 registered, 2,292 of the amendment), 5,691 requests sent (the difference to 4,326 are retries after HTTP 429 or transport errors, all logged), 1 failed cell, 186 cells with a PubMed warning or error entry (to be classified by SAP v2.0, Section 3.5; the expected entries are the valid zeros of descriptor cells before the introduction year).
3. Run B, 07:52:41 to 08:36:55 UTC, same session: 4,326 cells, 5,674 requests sent, 0 failed cells, 185 cells with warning or error entries.
4. `verify-manifest --dir out/freeze_20261012`: `manifest verified: every listed file matches` (08:48 UTC).
5. Run A versus Run B (compare_runs.py, 10:25 UTC, `d26_report_20261012.md` and `.csv`): 4,326 cells compared, 4,325 tier 1 (equal), 0 tier 2, 0 tier 3, 1 empty; largest absolute difference 0.
6. The empty cell: family `GE`, field `GBD_TUBERCULOSIS`, metric `den`, year 2017; no count in Run A after six attempts ([HTTP status and attempts from `issues_20261012_runA.jsonl`; Prem]), count 4,143 in Run B. Decision of the guarantor, 10:41 UTC (SAP v2.0, Section 3.4, rule 4, non-core cell): the Run B count is substituted in the analysis, the cell is flagged in every table that uses it and recorded as a deviation; the session is not repeated; the cell is excluded from E11; the frozen files are unchanged. The decision line is written into `d26_report_20261012.md`.

## 3. Lists run (families L and LV, sampling, XML, identifiers)

1. First attempt, version 1.1.0, 08:50:23 UTC. Lists B_AI (254), B_STROKE (661), S_AI (1,201) and S_STROKE (962) complete. List R_AI: count 30,447, 9,999 identifiers delivered, empty page from the history server at `retstart=9999` in three readings; run stopped by design at 08:50:31 UTC (exit code 3, `lists_failed.json`, manifest written); no sample drawn. Directory kept as `out/lists_20261012_versuch1` (deposited). Cause and decision: docs/CODE_REVIEW_v1.1.1.md.
2. Second attempt, version 1.1.1, 10:17:39 to 10:18:10 UTC, from the checkout of tag `v1.1.1`: all ten lists complete. R_AI: 30,447 identifiers read in 4 publication date ranges of 2024 (largest range 9,584; sum of the range counts 36,479; 6,032 identifiers that fell into two ranges counted once; 30,447 unique identifiers, equal to the count of the unchanged query). R_STROKE 9,088 (one page). DB_STROKE 30, ERCT_STROKE 631, SAI_STROKE 30, SNONAI_STROKE 932. Partition checks exact: B_STROKE 661 = 30 + 631; S_STROKE 962 = 30 + 932 (nothing only in the whole, nothing only in the parts, nothing in more than one part).
3. Cells drawn (seed 20260904; rule of Amendment v3.0, Section 6.1, and SAP decision I6): V-AI population 254 (pilot 20, formal 200, reserve 34); V-STROKE-AI 30, census; V-STROKE-nonAI 631 (20, 200, 411); U-AI 1,201 (20, 200, 981); U-STROKE-AI 30, census; U-STROKE-nonAI 932 (20, 200, 712); R-AI 30,447 (pilot 20, formal 50, reserve 30,377); R-STROKE 9,088 (20, 50, 9,018).
4. XML and registration identifiers (12.8): AI 254 records, 86 with an identifier, 88 distinct identifiers; STROKE 661 records, 293 with an identifier, 276 distinct; DB_STROKE 30 records, 11 with an identifier, 11 distinct; ERCT_STROKE 631 records, 282 with an identifier, 266 distinct. `lists mode finished`, exit code 0; `verify-manifest --dir out/lists_20261012`: every listed file matches.

## 4. Deposit (OSF project https://osf.io/ta7xw/, OSF Storage)

| File | Content | Uploaded (UTC) | Size |
|---|---|---|---|
| `freeze_20261012.zip` | `out/freeze_20261012` of `airct-release` (both count files, issues files, raw responses of every attempt, `shared_cells.json`, `queries.json`, snapshots, run log, manifest) | [ ] | [ ] |
| `freeze_20261012_fehlstart_0702Z.zip` | the aborted first start (log and raw attempts of one cell) | [ ] | [ ] |
| `lists_20261012_versuch1.zip` | the stopped first lists attempt (version 1.1.0) | [ ] | [ ] |
| `lists_20261012.zip` | `out/lists_20261012` of `airct-111` (version 1.1.1: PMID lists, `lists_meta.json`, `partition_report.json`, samples, `sampling_report.json`, XML, `efetch_report.json`, identifiers, log, manifest) | [ ] | [ ] |
| `d26_report_20261012.md`, `d26_report_20261012.csv` | Run A versus Run B with the decision line of the guarantor | [ ] | [ ] |

Before upload: the logs contain `api_key=present (not logged)` and nowhere the key; no IHME file is in the folders. [checked by; Prem]

## 5. Disclosures

* Values of 2024 strata seen on the freeze day by the pipeline lead and the guarantor in the logs, before any analysis: the list sizes B_AI 254, B_STROKE 661, S_AI 1,201, S_STROKE 962, R_AI 30,447, R_STROKE 9,088, DB_STROKE 30, ERCT_STROKE 631, SAI_STROKE 30, SNONAI_STROKE 932, the identifier counts of Section 3.4, and the Run B count 4,143 of the empty cell. These are sizes of registered strata and cells, not endpoints; the only decision taken on the day that touches the data (Section 2.6) follows a prespecified rule.
* The lists run used version 1.1.1 (code change on the freeze day, reviewed and tagged before the run; deviation from the retrieval mechanism named in the registration for lists above 10,000 identifiers, docs/CODE_REVIEW_v1.1.1.md).
* The analysis dataset for every count endpoint is Run A of 07:08 to 07:52 UTC; the sampling frames are the lists of 10:17 UTC of the same day.
