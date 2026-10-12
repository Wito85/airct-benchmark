# Code review record for release v1.1.1 (freeze day, 12 October 2026)

Purpose. Version 1.1.1 changes one thing: how a PMID list above 10,000 identifiers is read from PubMed. The change was made on the freeze day after the registered mechanism failed on the live service, so that the lists run (families L and LV, the sampling frames of the validation) could be completed on the registered retrieval date. The count cells of the freeze run (Run A and Run B of 12 October 2026) were retrieved with version 1.1.0 and are not touched. This file records the finding, the change, the review and the rerun. Nothing in this file is a result of the study. Fields in square brackets are completed by the person named.

## Finding (12 October 2026, 08:50 UTC)

The freeze run of version 1.1.0 (tag `v1.1.0`, commit `9e2a617bcaf844f4ff6aefdfc33803181a61e782`) had ended with exit code 0 and a verified manifest. The lists run started at 08:50:23 UTC. The four lists B_AI (254), B_STROKE (661), S_AI (1,201) and S_STROKE (962) were read completely. For list R_AI (the AI remainder stratum of 2024: human-subject records with the AI heading, MEDLINE subset, no RCT publication type, none of the trial words) PubMed reported a count of 30,447 and delivered 9,999 identifiers; the next page of the identifier list (history server, `efetch rettype=uilist`, `retstart=9999`) came back empty, in three readings. The pipeline refused to draw a sample from an incomplete list (decision I8), wrote `lists_failed.json`, closed the run with the manifest and exit code 3. The directory of this first attempt is kept as `out/lists_20261012_versuch1` and is deposited with the freeze files.

Cause. PubMed returns at most the first 10,000 identifiers of a result set. This holds for `esearch` with `retstart` and `retmax` and, as observed, for the history server as well. The registration (Q7, 12.1) names the history server for lists above 10,000 identifiers; that mechanism had never been exercised on a list of that size, because the syntax checks and the smoke test are count requests and version 1.0 never ran the lists mode on the live service. The offline test double of version 1.1.0 answered history requests of any length, so the test suite could not show the limit.

Decision of the guarantor (W. Polanski, 12 October 2026, 08:55 UTC, option A of three). The lists are read on the registered retrieval date with a corrected version 1.1.1 rather than on a later day (two retrieval dates in one dataset) or from the truncated list (no sampling frame). The change is reviewed by the two reviewers before the tag, tagged as `v1.1.1`, archived on Zenodo, and disclosed as a deviation: the retrieval mechanism named in the registration is replaced because the service does not provide it; the set that is read is the same set, defined by the same unchanged query string.

## The change (decision I9 of the README)

* `airct_benchmark/eutils.py`: `esearch_ids` reads a list above `history_threshold` (10,000, unchanged in `config/catalogue.yaml`) in publication date ranges of its year instead of from the history server. The year is halved into ranges until every range holds at most 9,999 identifiers (`LIST_SERVICE_LIMIT`); each range is one `esearch` request whose term is the registered query string, unchanged, with the range appended: `(<query>) AND (YYYY/MM/DD:YYYY/MM/DD[pdat])`. A single publication day above the limit (dates without month or day are indexed on the first day of the year or month) is halved further by create date (`[crdt]`); a single day on both axes above the limit stops the run. The list is accepted only when the sum of the range counts and the number of unique identifiers both equal the count of the unchanged query; otherwise the existing rule applies (three readings, then the run stops). Every range request is saved and logged like any other request; the notes in `lists_meta.json` record the number of ranges, the largest range and the sum of the range counts. The year is taken from the list specification (`run.py`) or, failing that, from the `("YYYY"[pdat])` clause of the term. The history server is no longer used.
* `airct_benchmark/run.py`: `_read_list` passes the year of the list.
* `airct_benchmark/__init__.py`: version `1.1.1`.
* `tests/conftest.py`: the offline test double answers date range terms (the identifiers of the base term whose synthetic publication or create day falls into the range) and imitates the service limit (`list_limit`), so that the limit is now part of the suite.
* `tests/test_eutils.py`: the test of the history server is replaced by five tests of the date range reading (ranges with the unchanged string inside, the year from the caller or the term, a publication day above the limit split by create date, ranges that do not add up, a day that cannot be read completely). The suite has 167 tests (166 passed, 1 skipped after the freeze date).
* `README.md` (lists section, decision I9, versioning) and `CITATION.cff` (version, `date-released: 2026-10-12`).
* Not changed: `config/catalogue.yaml` (catalogue SHA-256 `8677d96be620d527307ff29865e47a75cd97ef23c87f2b11eba649d7dd759f63`), `config/gbd_panel.yaml` (GBD panel SHA-256 `b91fd005303816cc191301a73241b37b9db0850877742f947d51736476437f2c`), every query string, the sampling (`sampling.py`), the XML and identifier steps, the freeze mode. Source SHA-256 of version 1.1.1 as prepared: `1245b3a306c483b16f1fd9b1a7bd39c76a0dc4b21545b0f4c5ecc6e2d8aaa170` (the same value must be printed by `check-catalogue` on the tagged commit).

Prepared in the development environment (Anthropic's Claude under the supervision of the guarantor) on 12 October 2026 between 08:57 and 09:15 UTC from a clone of `main` (commit `67a26af`); `python -m pytest`: 166 passed, 1 skipped (Python 3.13.16); `check-catalogue`: 93 of 93 and 98 of 98 strict matches, exit code 0, catalogue and panel hashes as above.

## Review (expedited, before the tag)

Each reviewer, on a fresh clone of branch `release-1.1.1`:

| Reviewer | Date, UTC | `python -m pytest` | `check-catalogue` (exit code, source SHA-256 first 12 characters, catalogue and panel hashes unchanged) | Diff read (`eutils.py`, `run.py`, `conftest.py`, `test_eutils.py`) | Python version |
|---|---|---|---|---|---|
| Clara Helene Buszello | [ ] | [166 passed, 1 skipped] | [0; 1245b3a306c4; yes] | [yes] | [ ] |
| Youssef Hachem | [ ] | [166 passed, 1 skipped] | [0; 1245b3a306c4; yes] | [yes] | [ ] |

Review statements (to be confirmed by the reviewers):

1. The registered query string of every list is contained unchanged in every range request; only a date range is appended.
2. No count query of the freeze run is affected; `config/catalogue.yaml` and `config/gbd_panel.yaml` are byte-identical to version 1.1.0 (same hashes).
3. A list is accepted only when the range counts add up to the count of the unchanged query and the unique identifiers equal that count; otherwise the run stops after three readings, as in version 1.1.0.
4. The sampling, the XML retrieval and the identifier extraction are unchanged.

## Release

Merge of `release-1.1.1` into `main` (pull request, merge commit): [hash, UTC; Polanski]. Tag `v1.1.1` on commit [hash; Polanski]. GitHub release "v1.1.1: PMID lists above the service limit read in date ranges". Zenodo: the GitHub integration creates the version record in the series 10.5281/zenodo.23280130; version DOI [10.5281/zenodo.23314880; Polanski]. `check-catalogue` on the tagged commit: [source SHA-256 as printed; Prem].

## Rerun of the lists (same retrieval date)

Command: `python -m airct_benchmark lists --out out` from a fresh clone of tag `v1.1.1`, with the API key in the environment, after the directory of the first attempt was renamed to `out/lists_20261012_versuch1`.
Start and end (UTC, `lists_meta.json` and the run log): [ ] to [ ]. Exit code: [0 | 3]. Lists read in date ranges (from the notes of `lists_meta.json`): [R_AI: n ranges, largest; R_STROKE: ...; LV lists: ...]. Readings repeated: [none | list]. `verify-manifest --dir out/lists_20261012`: [ ]. Deposited in the OSF project with `freeze_20261012.zip`: `lists_20261012.zip` and `lists_20261012_versuch1.zip`.

## Deviation statement (for the deviation log of the registration and the manuscript)

The registration (Q7, 12.1) states that PMID lists above 10,000 identifiers are retrieved through the history server (`usehistory=y`, `efetch rettype=uilist`). On the retrieval date, 12 October 2026, PubMed delivered no more than the first 10,000 identifiers of such a list through this mechanism. The lists above 10,000 identifiers were therefore read with pipeline version 1.1.1 in publication date ranges of the year 2024, each range below the limit and each defined by the registered query string with a date range appended, and accepted only after the range counts and the unique identifiers were shown to add up to the count of the unchanged query. The sets read are the sets defined by the registered strings; the count cells of the freeze run are unaffected (version 1.1.0). The first attempt of the lists run (version 1.1.0, 08:50 UTC, stopped at list R_AI) is deposited unchanged. In the course of the first attempt the pipeline lead and the guarantor saw the sizes of the four complete lists and the count of R_AI (B_AI 254, B_STROKE 661, S_AI 1,201, S_STROKE 962, R_AI 30,447); these are 2024 values of the registered strata and are disclosed here; the decision on the Run A versus Run B comparison (D26) follows the prespecified tiers and does not depend on them.

## Decision

Tag `v1.1.1` (package version 1.1.1) approved for the lists run of 12 October 2026 and for archiving on Zenodo.
Guarantor: [Witold Polanski, date and UTC time].
