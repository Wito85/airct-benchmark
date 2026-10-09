# Code review record for release v1.1.0

Purpose. Protocol Amendment v3.0 adds query families, a GBD panel and split validation cells before any freeze run. As for v1.0, the pipeline that produces the frozen dataset is reviewed, tagged and archived before any result is known. This file records that review. Nothing in this file is a result of the study. Fields in square brackets are completed by the person named.

## What changed relative to v1.0

* `config/catalogue.yaml`: the registered catalogue of tag v1.0 is the unchanged beginning of the file (first 20,150 characters, SHA-256 `f58bbbe612bab8fff2649aacff5b3b8ae85fc0c2b1803658bb187ac17982d394`, pinned in `airct_benchmark/catalogue.py`). The addendum of Amendment v3.0 follows it: families DB, DC, MD, ME, GA, GD, GE, DV, QV, WV, KV, JV, RS, list family LV, the eight validation cells, the syntax-check plan.
* `config/gbd_panel.yaml` (new, generated): the GBD panel.
* `airct_benchmark/`: `catalogue.py` and `queries.py` extended (addendum, panel, identity check against the amendment, syntax-check plan); `gbd.py` new (rules of the GBD panel shared by the loader, the catalogue check and the script); `run.py` extended (mode `syntax-check`, lists and cells of the amendment, shared cells, panel guards, six attempts per record, refusal of incomplete lists); `sampling.py` extended (`draw_cells`); `util.py` extended (`source_fingerprint`). `eutils.py`, `identifiers.py`, `pubmed_xml.py` and `manifest.py` are unchanged.
* `scripts/gbd_panel.py` (new): ranking of the GBD export, rater sheets, reconciliation, panel build.
* Tests: 53 in v1.0, 163 in v1.1.0.

## Development record (7 and 8 October 2026)

The extension was drafted with Anthropic's Claude under the supervision of the guarantor. The following was observed in the development environment and is to be repeated by the guarantor and the reviewers on their own machines; it is not a substitute for their checks. State of 8 October 2026 with the final GBD panel: source SHA-256 `0dd843f805e21965d81d7d89dab03a3a453d2d0397f53ceaffd2ee95afd6fa83`, catalogue SHA-256 `8677d96be620d527307ff29865e47a75cd97ef23c87f2b11eba649d7dd759f63`, GBD panel SHA-256 `b91fd005303816cc191301a73241b37b9db0850877742f947d51736476437f2c`.

| Check | Result |
|---|---|
| Offline test suite, `python -m pytest` | 163 passed (Linux; Python 3.10.20, 3.11.17, 3.13.16 and 3.14.6). With Windows line endings for every text file written (simulated, Python 3.10.20 and 3.13.16): 163 passed after the correction of 9 October 2026 below |
| Registered query list against tag v1.0 (checkout of commit `b68eb65`): 2,034 count queries and 6 list queries, same ids, same strings, same order | SHA-256 of the lists identical (`6c3f367f...9882` and `b37945a8...f8de`, full values in `tests/test_queries.py`) |
| `check-catalogue`, registered part against `Preregistration_v2.0_FINAL_2026-09-04.md` | 93 checks, 93 strict matches |
| `check-catalogue`, addendum and final panel against a test copy of the amendment draft of 30 September 2026 into which the generated table of the panel was pasted after paragraph 5.6 | 98 checks, 98 strict matches, exit code 0: 72 on Section 4 (auxiliary expression, set of families, 20 templates in 13 rows, 13 notes on RCT variants, 14 derived RCT variants, 5 worked examples, 5 generated strings equal to the examples) and 26 on the GBD panel (status, size, not the test panel, 20 rows, the table as a whole, the deposited files, the generated text of Section 5.7 as one block). Four copies of the text with one changed line around the table (a hash, the rater keys, an excluded cause, the catalogue volume) each end with exit code 2. The check is repeated with the amendment text as submitted (release checklist, steps 4 and 7). |
| Catalogue volume with the final panel (Stroke and Diabetes Mellitus are shared members) | 2,292 additional count requests, 4,326 per run |
| Syntax-check plan with the final panel, `syntax-check --dry-run` | 33 requests (4 anchors, 11 compositions, 18 descriptors), every one of publication year 2015, none with the Stroke heading, none a trial numerator within a field |
| Panel rebuilt from the deposited mapping table in a fresh copy, `python scripts/gbd_panel.py build --status final` | `config/gbd_panel.yaml` and `data/gbd/gbd_panel_amendment_table.md` identical to the files written by `reconcile` (same SHA-256) |
| Requests sent to PubMed (E-utilities) during development | none. `syntax-check` without `--send` prints the plan and sends nothing (tried with the final panel). The MeSH records for the candidates table were read from the NLM MeSH servers (id.nlm.nih.gov and meshb.nlm.nih.gov) on 7 and 8 October 2026. |

Changes of 8 October 2026, after the first handover of this version (source SHA-256 of that handover: `8964d295abaab656cd5ceb1d501b28e61e8505a8a51b30b29d4bc69e58f7f244`):

1. `airct_benchmark/catalogue.py` and the addendum of `config/catalogue.yaml`: COVID-19 is treated like Stroke and Diabetes Mellitus when it is a member of the GBD panel (decision of the guarantor of 8 October 2026). A member that coincides with a named field of a shorter year window shares the cells of that window, has no cell for earlier years and cannot be part of the trajectory. The rule is not applied by the final panel, in which COVID-19 (rank 26) is not a member.
2. `scripts/gbd_panel.py`: the export is read by the ids of the GBD Results Tool, so that an export made with a translated interface is ranked like an English one; cause names are taken from the hierarchy file; aggregates across causes whose names begin with "Total" are never ranked; the citation text of the download is recorded (`--citation-file`); the messages for an export with a wrong setting name that setting. `data/gbd/gbd_mesh_candidates.csv`: three rows added for causes of the real ranking that had no row (COVID-19, gynecological diseases, oral disorders). Tests: 161 instead of 157.
4. `airct_benchmark/gbd.py` and `airct_benchmark/queries.py`: `check-catalogue` has one more check of a final panel (kind `gbd_panel_block`). The generated text of Section 5.7 (`data/gbd/gbd_panel_amendment_table.md`) must stand in the amendment as one unchanged block. The deposited text is tested first: it must state the SHA-256 values of the current panel file, mapping table, ranking and raw export, the raters of the panel file, the date, person, permalink and hierarchy hash of the export record, the table rows of the panel file and the catalogue volume computed from the catalogue. Before this change only the 20 rows of the table were compared, so that a changed hash, rater key, excluded cause or volume figure in the amendment passed. Limits that remain: the list of causes that are not in the panel is not composed anew by the check, which is why `build --status final` is run before it (release checklist, step 4); text added on the same line before the first or after the last line of the block is not noticed.
5. `airct_benchmark/run.py`: `syntax-check` sends with `--send` only; without it the plan is printed and nothing is sent, and abbreviated options are not accepted. Before this change the command sent its requests whenever `--dry-run` was left out, and with a final panel nothing else stood in the way of an unintended run.
6. `config/gbd_panel.yaml`, `data/gbd/`: final panel from the export of 8 October 2026 and the two rater sheets (record in `docs/GBD_PANEL_EXPORT_PROTOCOL.md`, Section 8). The commands `rank`, `sheets` and `reconcile` were run by Claude in a cloud session on the files provided by the guarantor, because no Python installation was available at his workstation; the reviewers repeat them (Section 8 of that file).

Correction of 9 October 2026, during the review. On the Windows machine of the first reviewer (C. H. Buszello, Python 3.13) one test failed: `tests/test_run.py::test_check_catalogue_confirms_a_final_panel_with_its_files_and_its_amendment` (1 failed, 162 passed). The fault was in the test, not in the pipeline. Before the test rewrites its temporary amendment file with Windows line endings, it asserted that the file had Unix line endings. That holds on Linux and macOS only, because Python on Windows writes text files with Windows line endings. The test now normalises the file first and tries both kinds of line endings on every platform. Five lines of `tests/test_run.py` changed. No file of `airct_benchmark/`, `scripts/`, `config/` or `data/` changed, so that the source SHA-256, the catalogue SHA-256 and the GBD panel SHA-256 are those stated above. The failure was reproduced in the development environment by running the suite with Windows line endings for every text file written (1 failed and 162 passed before the correction, 163 passed after it). The commands of the reviewers that write or compare files (`reconcile`, `rank`, `check-catalogue`) were run in the same way and gave byte-identical files and the same hashes. The development environment has no Windows machine; the result on Windows is the one the reviewers record below: with the corrected file the suite passed on the machine where the fault had been found (163 passed, Python 3.13.3, 9 October 2026). The test had been written on 8 October 2026 after the automated readings and had been run on Linux only.

Automated second reading of 8 October 2026. The state with the final panel was read by a separate instance of Claude that had not written the code. It recomputed the ranking and the panel from the two raw files with its own code (no difference in any of the 176 ranks, in the panel or in a hash) and ran the commands of the reviewers. Its findings led to changes 4 and 5 above and to corrections of this file, of the README and of the export protocol. Changes 4 and 5 were then read by a further instance, which tried 47 altered copies of the amendment and of the generated text; its findings were worked in (the tests of the deposited text against the current files, the message that shows the place of the first difference, no abbreviated options). The last form of these two changes was not read again by a separate reviewer. The human reviewers are asked to read them in particular: `amendment_block`, `_first_difference` and `amendment_block_check` in `airct_benchmark/gbd.py`, the item `gbd_panel_block` in `airct_benchmark/queries.py`, and the options of `syntax-check` in `airct_benchmark/run.py` (`mode_syntax_check`, `build_parser`, `main`).

Automated second reading of 7 October 2026. Before the first handover, the pipeline and the GBD tooling were each read by a separate automated reviewer (instances of Claude that had not written the code and were asked to find faults). Their findings were resolved before the handover. The changes that matter for the protocol:

1. Syntax check. The first draft of the plan contained trial numerators within Diabetes Mellitus 2015 (families DB, DC and JV and the RCT metrics of the other families). Sections 1.4 and 8.2 of the amendment state that no within-field RCT count is viewed before the freeze run. These requests were removed; the loader now refuses a plan that names one, and the command checks every request against the rule (publication year 2015 only, no Stroke heading in any spelling) before anything is sent. No such request was ever sent.
2. Catalogue check. The first draft searched the amendment for each template as a substring. A truncated template, two exchanged templates or an additional family would have passed. The check now compares Section 4 row by row and the panel table row by row.
3. Registered part of the catalogue. Its SHA-256 was read from the file itself. It is now a constant of the code; the file is read with a loader that refuses a repeated key, and every registered section is compared with the registered text after loading.
4. Lists. Q14 is implemented literally: a record counts as unretrievable only after six attempts. A PMID list whose length differs from its count is read again and never sampled; a failure of the service stops the run instead of drawing replacements.
5. GBD panel. A panel with status `final` can only be built from a mapping table written by `reconcile`, together with the ranking and the export record; `check-catalogue` verifies the panel file against these files. The synthetic panel of the test suite is marked and refused by every online mode. A named field cannot enter the panel under another spelling.
6. Hashes of deposited text files are computed on the content with LF line endings, so that Windows and Linux give the same value. A run names the SHA-256 of the package sources (`source_sha256`) next to the git commit, so that it stays identifiable where no git checkout exists.

## Release checklist (in this order)

1. GBD panel final: `python scripts/gbd_panel.py reconcile` ended with exit code 0 and has written `data/gbd/gbd_panel_mesh_mapping.csv`, `config/gbd_panel.yaml` (status `final`) and `data/gbd/gbd_panel_amendment_table.md`. Done on 8 October 2026 with the sheets of W. Polanski and I. Y. Eyüpoglu (30 of 30 rows agreed, 20 members, ranks 1 to 23). Repeated by C. H. Buszello on 9 October 2026 with `python scripts/gbd_panel.py reconcile`, which reads the two deposited sheets and builds the panel again: GBD panel SHA-256 `b91fd005303816cc191301a73241b37b9db0850877742f947d51736476437f2c` as printed by `check-catalogue`, unchanged.
2. The table is pasted unchanged into Section 5 of the amendment. The amendment text is copied to `docs/AMENDMENT_v3_0.md`.
3. `python -m pytest`: all tests pass. [number, Python version]
4. `python scripts/gbd_panel.py build --status final` (writes the panel file and the text of Section 5.7 again from the mapping table; nothing may change), then `python -m airct_benchmark check-catalogue --json out/check_catalogue_v1_1.json`: 93 of 93 and 98 of 98 checks, exit code 0. [date, name, source SHA-256 as printed]
5. The state of step 4 is committed (or uploaded) to the branch; from here on the code is not changed. `python -m airct_benchmark syntax-check --dry-run` (sends nothing): the plan is read by a second person: every request ends with `("2015"[pdat])`, none contains `"Stroke"[Mesh]`, and none contains `AND "Randomized Controlled Trial"[pt]` or `AND "Clinical Trial"[pt]` (a trial numerator; the clause `NOT "Randomized Controlled Trial"[pt]` of the untagged strata is not one). [name]
6. `python -m airct_benchmark syntax-check --send --out out`: run once. Exit code [0 or 4]. The file `q18_addendum_<UTC>.md` is pasted into Section 8.10 of the amendment; a result that needed review is described there. A repetition needs `--repeat "<reason>"` and is disclosed. [date, UTC time, name]
7. The amendment as submitted to OSF is copied to `docs/AMENDMENT_v3_0.md` again (it now contains the Q18 addendum), and step 4 is repeated: exit code 0, same source SHA-256.
8. No provisional file is left in `data/gbd/` (the placeholder `gbd_panel_mesh_mapping_PROVISIONAL.csv` was removed on 8 October 2026, when the final panel was written). No file with DALY values and no raw IHME file is in the repository folder (`data/gbd/` holds the ranking without values only). `CITATION.cff`: `date-released` set. Section "Repository state reviewed" below completed.
9. Tag `v1.1.0`, archive on Zenodo, DOI entered in `CITATION.cff` and README on the main branch.
10. Smoke test with the tagged version: `python -m airct_benchmark smoke --out out`. [count, difference to 18,723, UTC time]

## Repository state reviewed

* Repository: https://github.com/Wito85/airct-benchmark, branch `release-1.1.0`
* Commit reviewed: [hash]; source SHA-256: [from the first line printed by `check-catalogue`]
* Catalogue SHA-256: [from the header of `check_catalogue_v1_1.json`]; GBD panel SHA-256: [same file]
* Amendment text used for the identity check: `docs/AMENDMENT_v3_0.md`, SHA-256 [hash], identical to the file submitted with the OSF update of [date]

## Checks by the guarantor (Witold Polanski, [date])

| Check | Command | Result |
|---|---|---|
| Offline test suite | `python -m pytest` | [n passed, Python version] |
| String identity, registration and amendment | `python -m airct_benchmark check-catalogue --json out/check_catalogue_v1_1.json` | [checks, strict matches, exit code] |
| Syntax check plan | `python -m airct_benchmark syntax-check --dry-run` | [number of requests; 2015 only; no Stroke expression; no trial numerator] |
| Syntax check | `python -m airct_benchmark syntax-check --send --out out` | [UTC time, exit code, requests, review notes] |
| Smoke test | `python -m airct_benchmark smoke --out out` | [count, reference 18,723, difference] |

## Independent confirmation (second and third reader)

| Reviewer | Date | `python -m pytest` | `check-catalogue` exit code | Source SHA-256 (first 12 characters) | Python version | Remarks |
|---|---|---|---|---|---|---|
| Clara Helene Buszello | 9 October 2026 | 163 passed (with `tests/test_run.py` as corrected on 9 October 2026; 1 failed and 162 passed before the correction) | 0: 93 of 93 and 98 of 98 checks strict, last line `RESULT: strict string identity confirmed`, against the test copy of the amendment draft with Section 5.7 | `0dd843f805e2` | 3.13.3 (Windows) | No git checkout (git commit unknown); catalogue SHA-256 `8677d96be620...` and GBD panel SHA-256 `b91fd0053038...` as printed. `syntax-check --dry-run`: 33 requests, identical line for line to the plan of the development environment. `reconcile` repeated with the two sheets as received, and `rank` repeated in a copy of the folder with her export of 8 October 2026: `check-catalogue` unchanged after each (same panel SHA-256, strict). |
| Youssef Hachem | 9 October 2026 | 163 passed | 0: 93 of 93 and 98 of 98 checks strict | `0dd843f805e2` | 3.13.3 | Package of 9 October 2026 (Korrektur1), the review steps of the guide on his own machine, in parallel to the first reviewer; result identical to hers, as reported to the guarantor on 9 October 2026. He read the plan of `syntax-check --dry-run` (33 requests). |

The guarantor read this record on 9 October 2026 and raised no objection. After the two reviews, the personal file properties of the two rater sheets (author, last saved by, folder path) were removed from the deposited copies by decision of the guarantor; the cells are unchanged, and `reconcile` gives byte-identical results (`docs/GBD_PANEL_EXPORT_PROTOCOL.md`, Section 8). No file of `airct_benchmark/`, `scripts/`, `config/` or `tests/` changed after the reviews.

## Review statements (to be confirmed by the reviewers)

1. The registered part of `config/catalogue.yaml` is the catalogue of tag v1.0; the first 2,034 requests of a run are the registered queries in the order of v1.0.
2. No string of the addendum deviates from Section 4 of the amendment, and the panel of `config/gbd_panel.yaml` is the panel listed in Section 5 and is supported by the deposited mapping table, ranking and export record (strict check, exit code 0).
3. `freeze` and `lists` refuse to run before the freeze date unless overridden; `freeze`, `lists` and `syntax-check` refuse a provisional panel and the synthetic panel of the test suite.
4. `syntax-check` sends only requests of publication year 2015, none with the Stroke expression and none that is a trial numerator within a field; the counts it viewed are those listed in the Q18 addendum.
5. Implementation decisions I3 to I8 (README) are documented for the statistical analysis plan v2.0; none changes an estimand of the amendment.

## Decision

Tag `v1.1.0` (package version 1.1.0) approved for archiving on Zenodo before the freeze run.
Guarantor: [name, date].
