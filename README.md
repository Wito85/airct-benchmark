# airct-benchmark

PubMed E-utilities pipeline of the study **Randomized trial share of medical artificial intelligence literature benchmarked against established clinical fields** (AI-RCT Benchmark).

* Preregistration: OSF https://osf.io/qkb9g/ (DOI 10.17605/OSF.IO/QKB9G), Preregistration v2.0 FINAL of 4 September 2026. The registration is binding; every query string in this repository is copied character for character from its item Q12.
* Protocol Amendment v3.0 (pre-data): census framework without significance tests, within-field primary contrast (stroke records with versus without the Artificial Intelligence heading, 2024), new query families and a panel of 20 high-burden diseases (GBD 2023). It is submitted as an update of the OSF registration before the freeze run; its text as submitted is `docs/AMENDMENT_v3_0.md`. Pipeline version 1.1.0 implements it. The registered catalogue of tag v1.0 is kept unchanged, character for character, and the amendment only adds to it.
* Code archive: Zenodo DOI 10.5281/zenodo.22299272 (first version published with tag v1.0 before the freeze run).
* License: MIT. Pipeline lead: Markus Georg Prem. Senior and corresponding author, guarantor: Witold Polanski (witold.polanski@ukdd.de). Department of Neurosurgery, Faculty of Medicine and University Hospital Carl Gustav Carus, Technische Universität Dresden.

The pipeline retrieves record counts (esearch, `retmax=0`) for a fixed catalogue of PubMed queries, twice in one session on the registered freeze date (Run A, then Run B), and retrieves PMID lists and efetch XML for the RCT-tagged and enriched untagged strata of AI and Stroke in 2024, the Stroke strata split by AI status. Analysis is a separate step and is not part of this package.

## Repository layout

```
config/catalogue.yaml         verbatim query catalogue. First part: the registered catalogue of tag v1.0
                              (Q12, request parameters, freeze rule, smoke-test reference, sampling rules,
                              identifier regexes), unchanged. Second part: the addendum of Amendment v3.0
                              (new families, PMID lists, validation cells, syntax-check plan)
config/gbd_panel.yaml         the GBD panel (Amendment v3.0, Section 5); generated, never edited by hand
airct_benchmark/
  catalogue.py                loads and validates the catalogue and the panel file
  queries.py                  composes every count query (registered families A to K, M, N, Q, R, U, W, Y;
                              amendment families DB, DC, MD, ME, GA, GD, GE, DV, QV, WV, KV, JV, RS) and
                              list query (families L and LV); checks string identity against the
                              registration text and against the amendment text
  eutils.py                   E-utilities client: rate limit, retry, raw response storage, esearch, efetch
  pubmed_xml.py               efetch XML parser (standard library)
  identifiers.py              trial registration identifiers (12.8, endpoint S8)
  sampling.py                 seeded validation and stratum sampling (Q13, Q14; cells of Amendment v3.0)
  manifest.py                 SHA-256 manifest (sha256sum format)
  gbd.py                      rules of the GBD panel shared by the loader, the catalogue check and the script
  run.py                      command-line entry point
scripts/gbd_panel.py          GBD panel tooling: ranking of the export, rater sheets, reconciliation, build
data/gbd/                     candidates table, deposited ranking (ranks only), export record with hashes,
                              mapping table, table for the amendment
tests/                        pytest suite, fully offline (PubMed is mocked)
docs/AMENDMENT_v3_0.md        Protocol Amendment v3.0 as submitted with the OSF update
docs/GBD_PANEL_EXPORT_PROTOCOL.md
                              export settings and procedure of the GBD panel
docs/DATA_DICTIONARY.md       definition of every output column (Q10)
docs/CODE_REVIEW_v1.0.md      record of the pre-freeze code review of release v1.0
docs/CODE_REVIEW_v1.1.md      record of the pre-freeze code review of release v1.1.0
Preregistration_v2.0_FINAL_2026-09-04.md
                              copy of the registered text; the OSF registration is authoritative
CITATION.cff, requirements.txt, environment.yml, pyproject.toml
```

## Installation

Python 3.10 or newer. Dependencies beyond the standard library: `requests` and `pyyaml` (and `pytest` for the tests; `openpyxl` for the rater sheets of `scripts/gbd_panel.py`).

```bash
git clone https://github.com/Wito85/airct-benchmark.git
cd airct-benchmark
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

or with conda:

```bash
conda env create -f environment.yml
conda activate airct-benchmark
```

All commands below are run from the repository root. `python -m airct_benchmark` and `python -m airct_benchmark.run` are equivalent.

## API key

The NCBI API key is read from the environment variable `NCBI_API_KEY` only. It is never written to any output, log or raw file (the client redacts it), and it must never be committed. Without a key the client limits itself to 3 requests per second, with a key to 10 per second (Q7).

```bash
export NCBI_API_KEY=...        # Windows PowerShell: $env:NCBI_API_KEY="..."
```

## Rule before the freeze date

The registration fixes the freeze run for **Monday, 12 October 2026**. Before that date no query may be sent to PubMed other than the smoke-test cell and the syntax check of the new expressions of Amendment v3.0, both restricted to publication year 2015 (Q8, Q9, Q18; amendment, Sections 1.4 and 8.3). The `freeze` and `lists` modes therefore refuse to run before 12 October 2026 unless `--override-freeze-guard` is given; an override is written to the log and would have to be disclosed as prior knowledge. If the OSF update is not approved in time, the amendment moves the freeze run to Monday, 26 October 2026; the guard date in the catalogue is a lower bound and stays as registered.

`freeze`, `lists` and `syntax-check` also refuse to run while `config/gbd_panel.yaml` has the status `provisional`. There is no override for this: the panel is fixed by the export and the reconciled mapping (see "GBD panel" below).

## Commands

### Smoke test (the only online command allowed before the freeze date)

One cell: Diabetes Mellitus, family A (human-subject denominator), publication year 2015.

```bash
python -m airct_benchmark smoke --out out
```

The result is written to `out/smoke_<UTC>.json` together with the raw response and a log. The count is compared with the reference 18,723 from the syntax check of 4 September 2026 (Q18). PubMed is updated continuously, so a difference is expected, logged and not a failure. Other cells of the same field and year can be tested with `--family B --metric rct` (reference 1,405), `--family E --metric den` (18,647), `--family G --metric den` (24,838), `--family K --metric den` (13,614) or `--family R --metric S` (941); any other field or year is refused.

### Syntax check of the amendment (online, publication year 2015 only, before the OSF update)

```bash
python -m airct_benchmark syntax-check --dry-run      # prints the requests, sends nothing
python -m airct_benchmark syntax-check --send --out out
```

The requests are sent with `--send` only. Without it the command prints the plan and sends nothing, so that a forgotten option cannot view a count. Options of this command cannot be abbreviated.

One request per new expression of Amendment v3.0, under the rule of Q8 and Q18: publication year 2015 only; every composition that names Stroke is run with Diabetes Mellitus, the registered smoke field, in its place, so that no Stroke count is viewed; one request per GBD descriptor that is new relative to v2.0. Four registered smoke cells of Diabetes Mellitus 2015, disclosed in Q18, are read again on the same day, because the database is live and the partition identities need values of the same day (for example: the two halves of a split cell add up to the registered cell). With two shared panel members this is 33 requests: 4 anchors, 11 compositions, 18 descriptors.

Not run before the freeze run: every composition that is a trial numerator within a field, that is families DB, DC and JV and the RCT metrics of the other families. Sections 1.4 and 8.2 of the amendment state that no within-field RCT count is viewed before the freeze run. These templates add a registered publication-type clause, verified on 4 September 2026 (Q18), to compositions that are checked here or registered.

The rule is enforced in code, not read from a file: a request must end with the single year clause of 2015, must not contain the Stroke heading in any spelling (PubMed ignores case and blanks), and the plan in the catalogue addendum (`amendment_syntax_check`) is refused by the loader if it names a trial numerator or an anchor without a Q18 value.

Output directory `out/syntax_check_<UTC>/`: `syntax_check_<UTC>.json` and `.csv` (every query, query translation and count), `q18_addendum_<UTC>.md` (the verbatim record for Section 8.10 of the amendment, to be pasted into the OSF update), raw responses, log, copies of catalogue and panel, manifest. Exit code 0: no failed request, no PubMed error or unexpected warning, every identity met, and in every query translation the field tags, the MeSH headings and the number of NOT operators as expected. Exit code 4: a human has to look at the listed requests or identities before the OSF update; this is not a failure of the run. Exit code 2: at least one request failed.

Every run with `--send` views counts and is disclosed. A second run into the same output directory is refused unless its reason is given with `--repeat "<reason>"`; the reason is written into the addendum. Commit the code before the run, so that the addendum names a commit.

### Catalogue check against the registration and the amendment (offline, code review)

```bash
python -m airct_benchmark check-catalogue --json out/check_catalogue.json
```

Two identity checks.

(1) The registered part of the catalogue against the registration text (`Preregistration_v2.0_FINAL_2026-09-04.md`, a copy of the registered Markdown file; the version on OSF is authoritative): 93 checks, unchanged from tag v1.0.

(2) The addendum and the GBD panel against the amendment text (`docs/AMENDMENT_v3_0.md`). Section 4 is compared family by family: the table must hold exactly one row per family of the addendum and no row of another family; the templates of a row (split at "; ", with (...) for the year clause) must be the templates of the catalogue for that family, all of them, in the same order, and nothing else; the note "the same with RCT" must stand in a row exactly when the catalogue holds RCT variants, and every variant must be derived by the stated rule. A template that is only part of a longer string, two exchanged templates or a family on one side only are differences. The auxiliary expression and the five worked examples are compared as strings. Section 5: the panel must be final, have 20 members, and its table must stand in the amendment exactly as generated (the same complete rows in the same order, and no other row); the panel file must agree with the deposited mapping table, ranking and export record (hashes, ranks, members); and the generated text of Section 5.7 (`data/gbd/gbd_panel_amendment_table.md`, without its comment line) must stand in the amendment as one unchanged block, which covers the lines around the table (raters, causes not in the panel, export, hashes, catalogue volume). The deposited text is tested first: it must state the SHA-256 values of the current files, the raters of the panel file, the particulars of the export record, the table rows of the panel file and the catalogue volume as they are now. Where the block differs, the message names the line and character of the first difference and shows both sides. The list of causes that are not in the panel is not composed anew by the check; run `python scripts/gbd_panel.py build --status final` before it, which writes the text again. The synthetic panel of the test suite is never confirmed. With a final panel this is 98 checks.

Not covered, because the amendment states them in prose: the PMID lists, the validation cells and the syntax-check plan of the addendum. They are covered by the test suite. Other files can be named with `--prereg` and `--amendment`. The command prints, and writes to the JSON file, the pipeline version, the git commit, the SHA-256 of the package sources and the SHA-256 of catalogue and panel, so that the review record names exactly what was checked. The Section 4 table and the panel table of the amendment must keep their table form.

Exit code 0: every component agrees with its source text. Exit code 1: the registration strings were found only after removing whitespace (happens with line-wrapped text exports; repeat with the Markdown file). Exit code 2: a difference exists, the panel is provisional or not supported by its files, a source text is missing, or the catalogue itself was refused; the release must not be tagged. Until the amendment text is copied to `docs/`, the command ends with exit code 2.

In addition, the loader refuses to run in every mode unless the registered part of `config/catalogue.yaml` is the catalogue of tag v1.0 (first 20,150 characters, SHA-256 pinned in `airct_benchmark/catalogue.py`), no key occurs twice in the file, and nothing after the registered part changes a registered section.

### Freeze run (12 October 2026)

```bash
python -m airct_benchmark freeze --out out
```

Runs the complete count catalogue as Run A and immediately again as Run B, in one session: first the 2,034 registered queries in the order of tag v1.0, then the families of Amendment v3.0 in the order of its Section 4. With two panel members shared with named fields (Stroke, Diabetes Mellitus) the amendment adds 2,292 requests, 4,326 per run; the number for the final panel is printed by `scripts/gbd_panel.py build` and stands in the header of every frozen file. Output directory `out/freeze_<YYYYMMDD>/`:

* `counts_frozen_<YYYYMMDD>_runA.csv` and `counts_frozen_<YYYYMMDD>_runB.csv`: the frozen files. Comment header (`#` lines) with retrieval start and end in UTC, git commit, SHA-256 of the package sources, pipeline version, E-utilities base URL, catalogue SHA-256, GBD panel SHA-256, registration DOI, amendment version, Python version and request statistics, followed by the eleven columns of 12.10 (`run, family, field, year, metric, query, querytranslation, count, utc, http_status, attempt`). Run A is the analysis dataset; Run B serves the within-day volatility diagnostic (E11).
* `issues_<YYYYMMDD>_run<X>.jsonl`: one line per cell with a PubMed warning or error list or a failed request.
* `raw/run<X>/`: the complete JSON response of every request attempt, with UTC timestamp, HTTP status and attempt number.
* `catalogue_snapshot.yaml`, `gbd_panel_snapshot.yaml`, `queries.json`: the catalogue, the panel and the ordered query list as executed.
* `shared_cells.json`: for every GBD panel member that coincides with a named field, the registered cell (or family DB cell) that holds each of its counts. These cells are not requested a second time (amendment, Section 5.2); the composed strings are proven identical before the run starts.
* `run_<UTC>.log`, `MANIFEST_SHA256.txt` (verify with `sha256sum -c MANIFEST_SHA256.txt` or `python -m airct_benchmark verify-manifest --dir out/freeze_<YYYYMMDD>`).

Exit code 3 signals that at least one cell failed after six attempts; the cell is present in the CSV with an empty count and the HTTP status of the last attempt, and it is listed in the issues file. Rerunning the session is a protocol decision, not something the pipeline does on its own: `freeze` and `lists` refuse to write into an output directory of an earlier run, which is kept and renamed by the person who decides.

A run restricted to some families (`--families A B DB`) or to Run A only (`--single-run`) is for testing and reproduction tooling; the registered freeze run uses neither option.

### Lists, sampling, XML and identifiers (after the freeze run, same session)

```bash
python -m airct_benchmark lists --out out
```

Output directory `out/lists_<YYYYMMDD>/`:

* `pmid_lists/pmids_<list>_2024.txt` and `lists_meta.json`: family L (registered: `B`, `S`, `R` for `AI` and `STROKE`) and family LV (amendment: `DB_STROKE`, the RCT-tagged stroke records with the AI heading; `ERCT_STROKE`, those without; `SAI_STROKE` and `SNONAI_STROKE`, the enriched untagged stroke stratum split in the same way). Lists above 10,000 identifiers are retrieved through the history server (`usehistory=y`, `efetch rettype=uilist`).
* `pmid_lists/partition_report.json`: PMID-level comparison of each complete stroke list with the union of its two split lists. The lists are read one after another from a live database, so a difference is reported and never corrected.
* `samples/sample_<cell>.csv` and `sampling_report.json`: draws for the eight cells of Amendment v3.0, Section 6.1: V-AI, V-STROKE-AI, V-STROKE-nonAI, U-AI, U-STROKE-AI, U-STROKE-nonAI, R-AI, R-STROKE (seed 20260904; a V-cell or U-cell with 200 records or fewer is rated completely, without pilot and without replacement queue; a larger cell is a sample of 200 with a pilot of 20 drawn first; R check 50; replacements after Q14).
* `xml/`: family O, efetch XML in batches of 200 for every record of the family B lists and for the sampled U and R records; the V-cells use the XML of the complete family B list; a record that is in a split stroke list but not in the XML of the complete list is fetched under the split list (`xml/DB_STROKE`, `xml/ERCT_STROKE`); `efetch_report.json`.
* `identifiers/identifiers_2024.csv` and `identifiers_summary.json`: registration identifiers (12.8) from the complete B lists, with a summary per field and, under `subsets`, per split stroke list (S8 within stroke).
* `catalogue_snapshot.yaml`, `run_<UTC>.log`, `MANIFEST_SHA256.txt`.

`--no-efetch` stops after the lists and the sampling.

Safeguards of the lists run. A PMID list is a sampling frame: it is accepted only when the number of identifiers retrieved equals the count of the same request; otherwise it is read again, up to three readings, and then the run stops. A record counts as unretrievable only after six attempts (Q14): a record that an efetch response does not hold (the response may be empty, truncated or an error page) is requested again with the registered waiting times. Only then is it replaced by the next PMID of the seeded sequence (sampled cells) or recorded as missing (census cells), and the sample files are written with the final sets. If more than five records and more than five percent of one request are still missing after six attempts, the cause is the service: the run stops without drawing replacements. A stopped run ends with exit code 3 and `lists_failed.json`; nothing in its directory is a sample to be rated.

### Offline tools

```bash
python -m airct_benchmark ratingsheet --xml-dir out/lists_<YYYYMMDD>/xml/B_AI --pmids out/lists_<YYYYMMDD>/samples/sample_V-AI.csv --out out/rating_V-AI.csv
python -m airct_benchmark ratingsheet --xml-dir out/lists_<YYYYMMDD>/xml/B_STROKE out/lists_<YYYYMMDD>/xml/DB_STROKE --pmids out/lists_<YYYYMMDD>/samples/sample_V-STROKE-AI.csv --out out/rating_V-STROKE-AI.csv
python -m airct_benchmark identifiers --xml-dir out/lists_<YYYYMMDD>/xml/B_STROKE --field STROKE --out out/identifiers_STROKE.csv
python -m airct_benchmark manifest --dir <directory>
python -m airct_benchmark verify-manifest --dir <directory>
```

Rating sheets contain PMID, year, journal, title and abstract only (no MeSH terms, no publication types), as required for blinded coding (Q24). `--xml-dir` takes several directories: for a V-cell, name every directory that `efetch_report.json` lists for it (`xml_source`, and the directory of the cell itself if records were fetched directly); a directory that does not exist is an error.

## GBD panel (Amendment v3.0, Section 5)

The panel is the first 20 Level 3 causes of the Global Burden of Disease Study 2023, ranked by global DALY counts of 2023, after the exclusion rules of Section 5.2, each mapped to one MeSH expression. It is produced by three commands and never typed by hand. Settings and procedure: `docs/GBD_PANEL_EXPORT_PROTOCOL.md`. The panel of this repository is final since 8 October 2026 (20 members, ranks 1 to 23 of the ranking); Sections 7 and 8 of that file record the decisions taken at mapping and who did what.

```bash
python scripts/gbd_panel.py rank --export <Results Tool CSV> --hierarchy <GBD 2023 cause hierarchy file> --author "<name>" --export-date <YYYY-MM-DD> --permalink "<permalink>"
python scripts/gbd_panel.py sheets
python scripts/gbd_panel.py reconcile
```

1. `rank` keeps the Level 3 causes of the stratum DALYs, Number, Global, All ages, Both, 2023 (identified by the ids of the Results Tool, so that an export made with another interface language is read as well; cause names are those of the hierarchy file), ranks them and applies rules (a) Injuries, (b) pandemic-related outcome categories and (c) residual causes whose name begins with "Other". It stops, without writing a ranking, if the export is not the untouched download, if a Level 3 cause of the hierarchy is missing, if a cause identifier carries different names in an English export and in the hierarchy, if the Level 1 group of a cause cannot be read, or if the ranked causes do not add up to "All causes" (tolerance 0.5 percent). The names of an export in another language cannot be compared with the hierarchy file; such an export is read by its identifiers alone, the number of differing names is noted in the export record, and the names are compared outside the script (`docs/GBD_PANEL_EXPORT_PROTOCOL.md`, Section 8). This sum is the completeness check; where it was passed, a cause of the export that the hierarchy file does not list is reported and recorded, and where the export has no row "All causes", it stops the run. It writes the deposited ranking without values (`data/gbd/gbd2023_level3_ranking.csv`) and the export record with SHA-256 hashes (`data/gbd/gbd_export_record.json`).
2. `sheets` writes one sheet per rater into `data/gbd/rating/` for the first 30 causes that passed rules (a) to (c), pre-filled from `data/gbd/gbd_mesh_candidates.csv` (proposed expression, MeSH unique identifier, link to the MeSH Browser, date introduced, scope note, narrower descriptors, stated over- or under-inclusion, alternatives; compiled from the NLM MeSH records). Each rater checks every proposal in the MeSH Browser and decides alone: agree, use an alternative, or no single descriptor (rule d). Existing sheets are never overwritten.
3. `reconcile` reads the two sheets of `data/gbd/rating/`. It first checks them against the ranking (same causes, same ranks, none skipped) and against the candidates table (the pre-filled cells are unchanged), and refuses a row that is empty or contradicts itself. If the raters differ, it writes `gbd_mapping_consensus.xlsx` with only the rows in question and ends with exit code 1; the raters enter the agreed decisions there and the same command is run again. When no disagreement is left, it writes the mapping table (`data/gbd/gbd_panel_mesh_mapping.csv`, with both independent choices and how they were reconciled), the panel (`config/gbd_panel.yaml`, status `final`, checked by the pipeline's own loader before it replaces the earlier file) and `data/gbd/gbd_panel_amendment_table.md`, the table that is pasted unchanged into Section 5 of the amendment. `check-catalogue` later confirms that the amendment lists exactly this panel and that the panel agrees with the deposited files.

`build --status final` rebuilds panel and table from a reconciled mapping table and gives the same files as the last `reconcile`. Without `--status final` it writes a provisional panel, with which no online mode runs. A final panel cannot be built from a table that `reconcile` did not write.

| Command | Options |
|---|---|
| `rank` | `--export`, `--hierarchy`, `--author`, `--export-date`, `--permalink` (all required); `--citation-file` (the citation text delivered with the download, recorded word for word on one line); `--local-dir` (folder for the ranking with values; default: the folder of the raw export); `--show` |
| `sheets` | `--raters WP IE`; `--n 30` (causes per sheet); `--out-dir`; `--carry-from <folder>` (copy the decisions of earlier sheets into larger ones); `--force` |
| `reconcile` | `--sheets <file> <file>`; `--consensus <file>`; `--candidates`; `--ranking`; `--mapping` |
| `build` | `--mapping`; `--status provisional` or `final`; `--provenance` |

Exit codes of the script: 0 done; 1 the raters disagree and have to decide; 2 stopped, with a message that begins with "STOPPED:" and says what to do.

The raw export, the hierarchy file and the ranking with DALY values are IHME data. They are kept by the authors outside the repository and are not redistributed (IHME Free-of-Charge Non-commercial User Agreement); the ranking with values is written next to the raw export. Source: Institute for Health Metrics and Evaluation. Used with permission. All rights reserved. Hashes of deposited text files are computed on the content with LF line endings, so that they do not depend on the platform.

A member whose expression equals a named field (Stroke, Diabetes Mellitus, COVID-19) shares the cells of that field, COVID-19 for its registered year window 2020 to 2024; a named field cannot enter the panel under another spelling or name. A member may be written as one descriptor with another removed, `("<Heading>"[Mesh] NOT "<Heading>"[Mesh])`, the form registered for F_AI_NOROB, where the mapping rule of the amendment says so. No other form is accepted.

## Tests

```bash
python -m pytest
```

The suite (163 tests) runs without network access: PubMed responses are simulated, and a safety net of the suite refuses every network connection. It runs with a synthetic GBD panel (`tests/fixtures/gbd_panel_fixture.yaml`, marked as a test fixture and refused by every online mode) and does not depend on the state of `config/gbd_panel.yaml`. `openpyxl` is required.

Registered part, as in v1.0: the number of queries per family (2,034 in total), the six worked examples of 12.6, the year clause position, the COVID-19 window, the registration check itself (including detection of a single changed character), the rate limiter, the retry schedule, the absence of the API key from every output, list paging and the history server path, efetch batching, identifier extraction and normalization, the sampling rules, and every command-line mode end to end.

Added with v1.1.0: the registered query list is byte-identical to the list of tag v1.0 and comes first (SHA-256 of the list); every amendment family, character for character; the five worked examples of Section 4; partition by construction (field with AI plus field without AI equals the registered cell); shared cells of panel members; the amendment check, row by row, including cases that a search for substrings would miss (a truncated template, exchanged templates, an added or missing family, a changed panel row); refusal of any edit of the registered part of the catalogue, of a repeated key, and of any addendum template that is not built from registered components; validation of the panel file, including a named field under another spelling or name; the syntax check (2015 only, no Stroke heading, no trial numerator, identities, query translation, Q18 addendum, single run, nothing sent without `--send`); the generated text of Section 5.7 as one unchanged block of the amendment; the split lists with their PMID-level comparison, the eight validation cells, incomplete lists, empty or broken efetch responses, replacement after six attempts, a service failure; and the GBD tooling from a synthetic export to the final panel, with the input errors it has to stop on.

## Reproduction

The independent reproduction (Hachem, Buszello) consists of (1) `python -m pytest`, (2) `check-catalogue` against the registration Markdown file and the amendment, (3) verifying the deposited manifest, and (4) recomputing the analysis dataset from the deposited raw responses: every count in `counts_frozen_<YYYYMMDD>_runA.csv` equals the `esearchresult.count` value in the raw file named in the same order under `raw/runA/`. Rerunning `freeze` after the freeze date reproduces the procedure but not the numbers, because PubMed is updated continuously (Q9).

## Implementation decisions documented for the statistical analysis plan

* **I1, sampling sequence.** The seeded sequence of a cell is one call `random.Random(20260904).sample(sorted_pmids, k=len(sorted_pmids))`. The pilot is its first 20 elements, the formal set the following 200 (or 50 for the R check), replacements after Q14 continue along the same sequence. Census V-cells (200 records or fewer) contain no additional pilot records; this is flagged in `sampling_report.json`.
* **I2, descriptors introduced after 2015.** Family H subfields and panel members are queried for every year 2015 to 2024; the registered reporting rules (report from the introduction year, trajectory exclusion) are applied in the analysis step and are stored as metadata in the catalogue.
* **Freeze guard.** See above. The smoke test is restricted to Diabetes Mellitus 2015 in code.
* **Failed cells.** A cell that fails after six attempts keeps its row (empty count, HTTP status and attempt of the last try). The frozen file is never edited by hand.
* **I3, registered catalogue and addendum.** `config/catalogue.yaml` begins with the catalogue of tag v1.0, unchanged; the loader verifies its SHA-256 on every start. Everything of Amendment v3.0 follows it under keys that begin with `amendment`. An addendum template may contain only registered components, placeholders, AND, NOT and parentheses; each "the same with RCT" variant is written out and verified against the rule.
* **I4, query order.** The first 2,034 requests of a run are the registered catalogue in the order of tag v1.0; the amendment families follow in the order of Section 4. Within a family: field, metric, year.
* **I5, shared cells.** A GBD member that coincides with a named field is not requested again; `shared_cells.json` names the cell that holds each count, and the identity of the two strings is proven at every start. A member shared with a named field of a shorter year window (COVID-19, 2020 to 2024) shares the cells of that window and has no cell for earlier years; it is no part of the trajectory (Section 5.2 of the amendment, decision of 8 October 2026). The Cardiovascular Diseases heading of families MD and ME repeats cells of families D, DB and E (40 strings); as in v1.0 for families M and N, such repeats are requested and kept as within-run stability observations.
* **I6, census rule for validation cells.** Every V-cell and U-cell with 200 records or fewer is rated completely (no pilot from that cell, no replacement queue); a larger cell is a seeded sample of 200 with a pilot of 20 drawn first. This is the rule of the statistical analysis plan (decision I1) applied uniformly to the split cells; decision D23 of the amendment uses the same distinction. Open for the statistical analysis plan v2.0: a cell of 201 to 219 records cannot give a pilot of 20 and a formal set of 200; as in v1.0 the pilot is drawn first and the formal set holds the remaining 181 to 199 records, which is flagged in `sampling_report.json`.
* **I7, syntax check.** Compositions that name Stroke are checked with Diabetes Mellitus 2015 in its place, as in the registered check of 4 September 2026; trial numerators within a field are not run; the counts viewed are listed in the Q18 addendum written by the command.
* **I8, unretrievable records and incomplete lists.** Q14 is implemented literally: a PMID is replaced or recorded as missing only after six attempts. Two safeguards go beyond the text of Q14 and are documented for the statistical analysis plan: a PMID list whose length differs from its count is read again and never sampled, and a lists run stops when more than five records and more than five percent of one efetch request stay missing after six attempts.

## Versioning

The version string in `airct_benchmark/__init__.py` is written into the header of every frozen file together with the git commit. Version `1.0.0` is the git tag `v1.0`, archived on Zenodo on 4 September 2026. Version `1.1.0` implements Amendment v3.0; it is tagged `v1.1.0` and archived on Zenodo before the freeze run, after the OSF update, with the final GBD panel and the amendment text in `docs/`. Runs made before the tag (the syntax check) are identified by their git commit and by `source_sha256`, the SHA-256 over the Python sources of the package (file names and contents with LF line endings). This value is written by every online mode and by `check-catalogue`; it identifies the code also when a run is made from a folder without a git checkout or with uncommitted files, and anyone can recompute it from the release.

## Authors

Markus Georg Prem (1; ORCID 0009-0005-9888-1380), Sven Richter (1, 2; ORCID 0000-0003-1648-5754), Clara Helene Buszello (1; ORCID 0009-0008-8230-1064), Sophia Willkommen (1; ORCID 0009-0003-8993-7720), Youssef Hachem (1), Nargiz Abdullayeva (1), Ilker Y. Eyüpoglu (1; ORCID 0000-0002-8185-7764) and Witold Polanski (1, 2; ORCID 0000-0002-6603-5375, corresponding author, witold.polanski@ukdd.de).

1. Department of Neurosurgery, Faculty of Medicine and University Hospital Carl Gustav Carus, Technische Universität Dresden, Dresden, Germany
2. Else Kröner Fresenius Center for Digital Health, Faculty of Medicine Carl Gustav Carus, Technische Universität Dresden, Dresden, Germany

Roles as registered: pipeline lead, Prem; validation raters, Polanski and Prem; second raters of the untagged strata, Richter and Willkommen; adjudication, Eyüpoglu; statistical analysis plan, Polanski; independent reproduction, Hachem and Buszello; guarantor, Polanski. Pre-freeze code review: see `docs/CODE_REVIEW_v1.0.md` and `docs/CODE_REVIEW_v1.1.md`. GBD panel mapping: Polanski and Eyüpoglu.

## Citation
Version 1.1.0 (tag v1.1.0, commit 9e2a617bcaf844f4ff6aefdfc33803181a61e782, released 10 October 2026) is archived on Zenodo under DOI 10.5281/zenodo.23280203; the concept DOI 10.5281/zenodo.23280130 resolves to the latest version from 1.1.0 onwards. Version 1.0 is archived under DOI 10.5281/zenodo.22299272.
See `CITATION.cff`. Software archive: Zenodo DOI 10.5281/zenodo.22299272. Registration: OSF DOI 10.17605/OSF.IO/QKB9G.
