# airct-benchmark

Randomized trial share of medical artificial intelligence literature benchmarked against established clinical fields: a preregistered, reproducible bibliometric meta-research study of PubMed record counts, publication years 2015 to 2024.

The study compares the proportion of human-subject PubMed records carrying the Randomized Controlled Trial publication type between the literature indexed under "Artificial Intelligence"[Mesh] and established clinical fields (primary comparator: Stroke), with a single confirmatory contrast for 2024, a 2015 to 2024 trend, technology and young-field comparators, a validation of the RCT tag in both directions, a trial-level count by registration identifiers, and reference distributions across all major disease categories and a panel of health-technology fields.

## Status

Preregistration on OSF in preparation (September 2026). The retrieval pipeline follows the registration. The frozen dataset is retrieved on 12 October 2026 (Run A for analysis, Run B for within-day volatility), independently reproduced on the same day, and deposited on OSF.

## Planned contents

- `pipeline/`: PubMed E-utilities retrieval (esearch counts with `retmax=0`, efetch XML), rate limiting, retry with backoff, archiving of every raw response
- `config/`: the query catalogue, verbatim from the preregistration
- `analysis/`: statistical analysis in Python (seed 20260904), producing every table and figure from the frozen files
- `docs/`: preregistration, change log, pre-registration syntax-check log
- `prereg_syntax_check.py`: query-syntax check run before registration (publication year 2015 only, new expressions only)

## Links

- OSF project: to be added
- OSF registration: to be added
- Zenodo archive: to be added

## Team

Prem, Richter, Buszello, Willkommen, Hachem, Abullayeva, Eyüpoglu, Polanski (senior and corresponding author, witold.polanski@ukdd.de). Department of Neurosurgery, Universitätsklinikum Carl Gustav Carus, TU Dresden.

## License

Code: MIT License. Documents and data: CC-BY 4.0.
