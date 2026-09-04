# Code review record for release v1.0

Purpose. The registration (Q9) requires that the pipeline is reviewed and tagged before the freeze run of
12 October 2026, so that the code that produces the frozen dataset exists, archived and citable, before any
result is known. This file records that review. Nothing in this file is a result of the study.

## Repository state reviewed

* Repository: https://github.com/Wito85/airct-benchmark, branch `main`
* Commit reviewed: `27b3e0f` (Pipeline v1, Step 2: catalogue, E-utilities client, run modes, tests, data dictionary)
* Catalogue file: `config/catalogue.yaml`, SHA-256 recorded in the header of every frozen file at run time
* Registration text used for the string identity check: `Preregistration_v2.0_FINAL_2026-09-04.md`
  (OSF https://osf.io/qkb9g/, DOI 10.17605/OSF.IO/QKB9G)

## Checks by the guarantor (Witold Polanski, 4 September 2026)

| Check | Command | Result |
|---|---|---|
| Offline test suite | `python -m pytest` | 53 passed (Python 3.14.3) |
| String identity catalogue versus registration | `python -m airct_benchmark check-catalogue --prereg Preregistration_v2.0_FINAL_2026-09-04.md --json out/check_catalogue.json` | 93 checks: 93 strict matches (63 components, 18 family templates, 6 worked examples, 6 generated-equals-example), exit code 0 |
| Smoke test, the only permitted online cell | `python -m airct_benchmark smoke --out out` | `A_DM_den_2015`, 2026-09-04T11:58:24Z, count 18,723, reference (Q18, 07:26 UTC) 18,723, difference 0, HTTP 200, attempt 1, no PubMed warnings; querytranslation `"Diabetes Mellitus"[MeSH Terms] AND "Humans"[MeSH Terms] AND 2015/01/01:2015/12/31[Date - Publication]` |

The files `check_catalogue.json` and `smoke_20260904T115824Z.json` are kept with the project records (not in the repository, because `out/` is ignored by git).

## Independent confirmation (second and third reader)

| Reviewer | Date | `python -m pytest` | `check-catalogue` exit code | Python version | Remarks |
|---|---|---|---|---|---|
| Youssef Hachem | 2026-09-04 | 53 passed | 0 | 3.14.3 | confirmed by e-mail of 2026-09-04, commit cc4038b |
| Clara Helene Buszello | 2026-09-04 | 53 passed | 0 | 3.14.3 | confirmed by e-mail of 2026-09-04, commit cc4038b |

Each reviewer confirms by completing the row above in a commit of their own (or by e-mail to the guarantor,
who then completes the row and names the e-mail date in Remarks).

## Review statements

1. No query string in `config/catalogue.yaml` deviates from item Q12 of the registration (strict check, exit code 0).
2. The API key is read from the environment only and is redacted from raw responses and logs (tests `test_eutils`, `test_run`).
3. `freeze` and `lists` refuse to run before 12 October 2026 unless explicitly overridden, and an override is logged (test `test_run`).
4. The smoke test is restricted in code to Diabetes Mellitus 2015.
5. Implementation decisions I1 (sampling sequence) and I2 (descriptor introduction years) are documented in README and code and are to be confirmed in the statistical analysis plan; neither changes a registered estimand.

## Decision

Tag `v1.0` (package version 1.0.0) approved for archiving on Zenodo (DOI 10.5281/zenodo.22299272) before the freeze run.
Guarantor: Witold Polanski, 4 September 2026.
