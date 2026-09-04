# airct-benchmark

PubMed E-utilities pipeline of the study **Randomized trial share of medical artificial intelligence literature benchmarked against established clinical fields** (AI-RCT Benchmark).

* Preregistration: OSF https://osf.io/qkb9g/ (DOI 10.17605/OSF.IO/QKB9G), Preregistration v2.0 FINAL of 4 September 2026. The registration is binding; every query string in this repository is copied character for character from its item Q12.
* Code archive: Zenodo DOI 10.5281/zenodo.22299272 (first version published with tag v1.0 before the freeze run).
* License: MIT. Pipeline lead: Markus Georg Prem. Senior and corresponding author, guarantor: Witold Polanski (witold.polanski@ukdd.de). Department of Neurosurgery, Faculty of Medicine and University Hospital Carl Gustav Carus, Technische Universität Dresden.

The pipeline retrieves record counts (esearch, `retmax=0`) for a fixed catalogue of PubMed queries, twice in one session on the registered freeze date (Run A, then Run B), and retrieves PMID lists and efetch XML for the RCT-tagged and enriched untagged strata of AI and Stroke in 2024. Analysis is a separate step and is not part of this package.

## Repository layout

```
config/catalogue.yaml         verbatim query catalogue (Q12), request parameters (12.1, Q7), freeze rule,
                              smoke-test reference (Q18), sampling rules (Q13), identifier regexes (12.8)
airct_benchmark/
  catalogue.py                loads and validates the catalogue
  queries.py                  composes every count query (families A to K, M, N, Q, R, U, W, Y) and list
                              query (family L); checks string identity against the registration text
  eutils.py                   E-utilities client: rate limit, retry, raw response storage, esearch, efetch
  pubmed_xml.py               efetch XML parser (standard library)
  identifiers.py              trial registration identifiers (12.8, endpoint S8)
  sampling.py                 seeded validation and stratum sampling (Q13, Q14)
  manifest.py                 SHA-256 manifest (sha256sum format)
  run.py                      command-line entry point
tests/                        pytest suite, fully offline (PubMed is mocked)
docs/DATA_DICTIONARY.md       definition of every output column (Q10)
docs/CODE_REVIEW_v1.0.md      record of the pre-freeze code review (Step 3)
Preregistration_v2.0_FINAL_2026-09-04.md
                              copy of the registered text; the OSF registration is authoritative
CITATION.cff, requirements.txt, environment.yml, pyproject.toml
```

## Installation

Python 3.10 or newer. Dependencies beyond the standard library: `requests` and `pyyaml` (and `pytest` for the tests).

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

The registration fixes the freeze run for **Monday, 12 October 2026**. Before that date no query other than the smoke-test cell may be sent to PubMed (Q8, Q9). The `freeze` and `lists` modes therefore refuse to run before 12 October 2026 unless `--override-freeze-guard` is given; an override is written to the log and would have to be disclosed as prior knowledge.

## Commands

### Smoke test (the only online command allowed before the freeze date)

One cell: Diabetes Mellitus, family A (human-subject denominator), publication year 2015.

```bash
python -m airct_benchmark smoke --out out
```

The result is written to `out/smoke_<UTC>.json` together with the raw response and a log. The count is compared with the reference 18,723 from the syntax check of 4 September 2026 (Q18). PubMed is updated continuously, so a difference is expected, logged and not a failure. Other cells of the same field and year can be tested with `--family B --metric rct` (reference 1,405), `--family E --metric den` (18,647), `--family G --metric den` (24,838), `--family K --metric den` (13,614) or `--family R --metric S` (941); any other field or year is refused.

### Catalogue check against the registration (offline, Step 3 of the work plan)

```bash
python -m airct_benchmark check-catalogue --prereg Preregistration_v2.0_FINAL_2026-09-04.md --json out/check_catalogue.json
```

The registration text is included in the repository root as a copy of the registered Markdown file, so the check runs without external files; the version on OSF (https://osf.io/qkb9g/) is authoritative. Exit code 0: every catalogue component (field expressions, auxiliary expressions, panel headings, family templates, worked examples) is found character for character in the registration text. Exit code 1: found only after removing whitespace (happens with line-wrapped text exports; repeat with the Markdown file). Exit code 2: a character difference exists and must be resolved before the release is tagged.

### Freeze run (12 October 2026)

```bash
python -m airct_benchmark freeze --out out
```

Runs the complete count catalogue (2,034 queries) as Run A and immediately again as Run B, in one session. Output directory `out/freeze_<YYYYMMDD>/`:

* `counts_frozen_<YYYYMMDD>_runA.csv` and `counts_frozen_<YYYYMMDD>_runB.csv`: the frozen files. Comment header (`#` lines) with retrieval start and end in UTC, git commit, pipeline version, E-utilities base URL, catalogue SHA-256, registration DOI, Python version and request statistics, followed by the eleven columns of 12.10 (`run, family, field, year, metric, query, querytranslation, count, utc, http_status, attempt`). Run A is the analysis dataset; Run B serves the within-day volatility diagnostic (E11).
* `issues_<YYYYMMDD>_run<X>.jsonl`: one line per cell with a PubMed warning or error list or a failed request.
* `raw/run<X>/`: the complete JSON response of every request attempt, with UTC timestamp, HTTP status and attempt number.
* `catalogue_snapshot.yaml`, `queries.json`: the catalogue and the ordered query list as executed.
* `run_<UTC>.log`, `MANIFEST_SHA256.txt` (verify with `sha256sum -c MANIFEST_SHA256.txt` or `python -m airct_benchmark verify-manifest --dir out/freeze_<YYYYMMDD>`).

Exit code 3 signals that at least one cell failed after six attempts; the cell is present in the CSV with an empty count and the HTTP status of the last attempt, and it is listed in the issues file. Rerunning the session is a protocol decision, not something the pipeline does on its own.

A run restricted to some families (`--families A B`) or to Run A only (`--single-run`) is for testing and reproduction tooling; the registered freeze run uses neither option.

### Lists, sampling, XML and identifiers (after the freeze run, same session)

```bash
python -m airct_benchmark lists --out out
```

Output directory `out/lists_<YYYYMMDD>/`:

* `pmid_lists/pmids_<B|S|R>_<AI|STROKE>_2024.txt` and `lists_meta.json`: family L. Lists above 10,000 identifiers are retrieved through the history server (`usehistory=y`, `efetch rettype=uilist`).
* `samples/sample_<cell>.csv` and `sampling_report.json`: Q13 draws for V-AI, V-STROKE, U-AI, U-STROKE, R-AI, R-STROKE (seed 20260904; pilot of 20 first; census rule for V-cells with 200 records or fewer; replacements after Q14).
* `xml/`: family O, efetch XML in batches of 200 for every record of the family B lists and for the sampled U and R records; `efetch_report.json`.
* `identifiers/identifiers_2024.csv` and `identifiers_summary.json`: registration identifiers (12.8) from the complete B lists.
* `catalogue_snapshot.yaml`, `run_<UTC>.log`, `MANIFEST_SHA256.txt`.

`--no-efetch` stops after the lists and the sampling.

### Offline tools

```bash
python -m airct_benchmark ratingsheet --xml-dir out/lists_<YYYYMMDD>/xml/B_AI --pmids out/lists_<YYYYMMDD>/samples/sample_V-AI.csv --out out/rating_V-AI.csv
python -m airct_benchmark identifiers --xml-dir out/lists_<YYYYMMDD>/xml/B_STROKE --field STROKE --out out/identifiers_STROKE.csv
python -m airct_benchmark manifest --dir <directory>
python -m airct_benchmark verify-manifest --dir <directory>
```

Rating sheets contain PMID, year, journal, title and abstract only (no MeSH terms, no publication types), as required for blinded coding (Q24).

## Tests

```bash
python -m pytest
```

The suite (53 tests) runs without network access: PubMed responses are simulated. It checks the number of queries per family (2,034 in total), the six worked examples of 12.6, the year clause position, the COVID-19 window, the registration check itself (including detection of a single changed character), the rate limiter, the retry schedule, the absence of the API key from every output, list paging and the history server path, efetch batching, identifier extraction and normalization, the sampling rules, and every command-line mode end to end.

## Reproduction

The independent reproduction (Hachem, Buszello) consists of (1) `python -m pytest`, (2) `check-catalogue` against the registration Markdown file, (3) verifying the deposited manifest, and (4) recomputing the analysis dataset from the deposited raw responses: every count in `counts_frozen_<YYYYMMDD>_runA.csv` equals the `esearchresult.count` value in the raw file named in the same order under `raw/runA/`. Rerunning `freeze` after the freeze date reproduces the procedure but not the numbers, because PubMed is updated continuously (Q9).

## Implementation decisions documented for the statistical analysis plan

* **I1, sampling sequence.** The seeded sequence of a cell is one call `random.Random(20260904).sample(sorted_pmids, k=len(sorted_pmids))`. The pilot is its first 20 elements, the formal set the following 200 (or 50 for the R check), replacements after Q14 continue along the same sequence. Census V-cells (200 records or fewer) contain no additional pilot records; this is flagged in `sampling_report.json`.
* **I2, descriptors introduced after 2015.** Family H subfields and panel members are queried for every year 2015 to 2024; the registered reporting rules (report from the introduction year, trajectory exclusion) are applied in the analysis step and are stored as metadata in the catalogue.
* **Freeze guard.** See above. The smoke test is restricted to Diabetes Mellitus 2015 in code.
* **Failed cells.** A cell that fails after six attempts keeps its row (empty count, HTTP status and attempt of the last try). The frozen file is never edited by hand.

## Versioning

The version string in `airct_benchmark/__init__.py` is written into the header of every frozen file. It is `1.0.0.dev0` during development and is set to `1.0.0` with the git tag `v1.0`, which is archived on Zenodo before the freeze run.

## Authors

Markus Georg Prem (1; ORCID 0009-0005-9888-1380), Sven Richter (1, 2; ORCID 0000-0003-1648-5754), Clara Helene Buszello (1; ORCID 0009-0008-8230-1064), Sophia Willkommen (1; ORCID 0009-0003-8993-7720), Youssef Hachem (1), Nargiz Abdullayeva (1), Ilker Y. Eyüpoglu (1; ORCID 0000-0002-8185-7764) and Witold Polanski (1, 2; ORCID 0000-0002-6603-5375, corresponding author, witold.polanski@ukdd.de).

1. Department of Neurosurgery, Faculty of Medicine and University Hospital Carl Gustav Carus, Technische Universität Dresden, Dresden, Germany
2. Else Kröner Fresenius Center for Digital Health, Faculty of Medicine Carl Gustav Carus, Technische Universität Dresden, Dresden, Germany

Roles as registered: pipeline lead, Prem; validation raters, Polanski and Prem; second raters of the untagged strata, Richter and Willkommen; adjudication, Eyüpoglu; statistical analysis plan, Polanski; independent reproduction, Hachem and Buszello; guarantor, Polanski. Pre-freeze code review: see `docs/CODE_REVIEW_v1.0.md`.

## Citation

See `CITATION.cff`. Software archive: Zenodo DOI 10.5281/zenodo.22299272. Registration: OSF DOI 10.17605/OSF.IO/QKB9G.
