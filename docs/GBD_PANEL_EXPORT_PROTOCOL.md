# GBD panel: export and mapping protocol (Amendment v3.0, Section 5, decision D24)

Status: procedure of pipeline v1.1.0, executed on 8 October 2026 (export by C. H. Buszello, rating by W. Polanski and I. Y. Eyüpoglu; record in Section 8). This file replaces the draft of 22 September 2026, which was written before the export could be made. Nothing in this file is a result of the study.

## 1. Source and quantity

Global Burden of Disease Study 2023 (GBD 2023): GBD 2023 Disease and Injury and Risk Factor Collaborators, Lancet 2025;406(10513):1873 to 1922, DOI 10.1016/S0140-6736(25)01637-X. Quantity: cause hierarchy Level 3, DALYs as counts (metric Number), all ages, both sexes, location Global, year 2023.

The amendment names two equivalent data paths. This protocol uses the GBD Results Tool, because its CSV is machine readable and carries the cause identifiers: https://vizhub.healthdata.org/gbd-results/ (free IHME account).

## 2. Export

Settings of the Results Tool, exactly:

| Setting | Value |
|---|---|
| GBD Estimate | Cause of death or injury |
| Measure | DALYs (Disability-Adjusted Life Years) |
| Metric | Number |
| Cause | all causes (every level; the script keeps Level 3) |
| Location | Global |
| Age | All ages |
| Sex | Both |
| Year | 2023 |

In the field Cause every entry of the list is selected; the default of the tool is the single entry "All causes", and an export made with it holds one row and cannot be ranked. Download as CSV with names and identifiers (option "Both"). The Results Tool delivers a ZIP archive; the CSV inside is unpacked and not opened in a spreadsheet program. The interface language of the tool does not matter: the script identifies the stratum and the causes by their ids (measure 2, location 1, sex 3, age 22, metric 1, population group 1) and takes the cause names from the hierarchy file. The citation text that comes with the download is passed with `--citation-file` and recorded word for word on one line. Record the permalink of the query, the date and the person. Second file: the GBD 2023 cause hierarchy (worksheet "Cause Hierarchy" of the workbook IHME_GBD_2023_HIERARCHIES; columns Cause ID, Cause Name, Parent ID, Level), downloaded from the record of the GBD 2023 cause, REI and location hierarchies in the Global Health Data Exchange (GHDx, https://ghdx.healthdata.org/) [exact title and address of the record: to be entered by the person who downloaded the file]. The Level 1 group of a cause (non-communicable; communicable, maternal, neonatal and nutritional; injuries) is read from this file and never assigned by hand.

Both files are kept unchanged, under their original names, in a folder outside the repository.

## 3. Ranking and exclusion rules (a) to (c)

```bash
python scripts/gbd_panel.py rank --export <export.csv> --hierarchy <hierarchy.xlsx> --author "<name>" --export-date <YYYY-MM-DD> --permalink "<permalink>"
```

The script keeps the rows of the stratum of Section 1, keeps the Level 3 causes, sorts them by the DALY count in descending order and applies the rules of Amendment v3.0, Section 5.2, in this order: (a) Level 1 group Injuries; (b) pandemic-related outcome categories (cause name contains "pandemic-related"); (c) residual causes (cause name begins with "Other"). Should the hierarchy hold a cause of Level 1 or 2 without causes below it, it is ranked with the Level 3 causes as itself, as GBD reports it, and marked; the script accepts this only when one of the rules (a) to (c) excludes that cause, and stops otherwise, because the amendment does not say how such a cause would be treated.

The script stops, without writing a ranking, in each of these cases: the file is the ZIP archive or was saved again by a spreadsheet program (semicolons, decimal commas); the export holds risk-factor columns; no row matches the stratum; a Level 3 cause of the hierarchy is missing from the export; a cause identifier carries different names in an English export and in the hierarchy (a different spelling of the same name is noted; the names of an export in another language cannot be compared, so that such an export is read by its identifiers alone, the number of differing names is written to the export record, and the names are compared outside the script, see Section 8); a cause occurs twice; a value is not a finite, non-negative number; the Level 1 group of a cause cannot be read from the hierarchy; two causes among the first 60 have the same value; the DALY counts of the ranked causes do not add up to the value of "All causes" (tolerance 0.5 percent).

The comparison with "All causes" is the completeness check: the ranked causes partition all causes, so a missing cause, a cause counted twice or a hierarchy of another GBD round shows in the sum. Where it was passed, the following cannot change the order of the leading causes and are reported and written to the export record instead of stopping the run: a cause of the export that the hierarchy file does not list, and an aggregate that the hierarchy file lists among the causes. Where the export holds no row for "All causes", each of them stops the run. Aggregates across causes that the Results Tool offers under names beginning with "Total" are no part of the partition; they are never ranked and are listed in the export record.

Output: `data/gbd/gbd2023_level3_ranking.csv` (rank, cause identifier, cause, Level 1 group, rule result; no DALY values), `data/gbd/gbd_export_record.json` (settings, permalink, person, date, SHA-256 of the raw export, of the hierarchy file and of both rankings, result of the completeness check) and, next to the raw export and therefore outside the repository, `gbd2023_level3_dalys_global_2023.csv` (the ranking with values).

## 4. Mapping to MeSH, rule (d)

```bash
python scripts/gbd_panel.py sheets
```

One sheet per rater (W. Polanski, key WP; I. Y. Eyüpoglu, key IE) in `data/gbd/rating/` for the first 30 causes that passed rules (a) to (c): 20 for the panel and 10 in reserve. Each row is pre-filled from `data/gbd/gbd_mesh_candidates.csv` with a proposed expression and the facts of the descriptor: MeSH unique identifier, link to the MeSH Browser, date introduced, scope note, narrower descriptors, the stated over- or under-inclusion relative to the GBD cause, and alternatives. The candidates table was compiled on 7 and 8 October 2026 from the NLM MeSH records (MeSH RDF, id.nlm.nih.gov, and MeSH Browser, meshb.nlm.nih.gov, Descriptor Data 2026) with the assistance of Anthropic's Claude; it is a proposal, not a decision. A cause without a row in the candidates table is shown without a proposal and is looked up by the raters.

Each rater works alone, checks every proposal in the MeSH Browser against the mapping rule of Section 5.3 and records one decision per row in the three yellow columns: `agree`, `use alternative` (with the expression) or `no single descriptor (rule d)`. Nothing else in the sheet is changed. Stroke, Diabetes mellitus and COVID-19 are named fields; their expression is fixed by Section 5.2.

```bash
python scripts/gbd_panel.py reconcile
```

The script reads the two sheets of `data/gbd/rating/` and checks, before anything else, that they list the same causes, that causes and ranks are those of the ranking with none skipped, that the pre-filled cells still equal the candidates table, and that every row holds a decision that can be read without guessing. If the raters differ, it writes `data/gbd/rating/gbd_mapping_consensus.xlsx` with only the rows in question and the two independent choices, and ends with exit code 1; nothing else is written. The raters resolve each row by discussion (Section 5.3), enter the agreed decision and its reason in the consensus sheet, and run the same command again. The rater sheets themselves are not changed after the comparison, so that the independent choices stay on record.

When no disagreement is left, the script writes `data/gbd/gbd_panel_mesh_mapping.csv` with both independent choices, the agreed expression, whether agreement was reached independently or after discussion, and the comments. A cause without a single descriptor drops out under rule (d) and the next cause moves up. The first 20 mapped causes in rank order are the panel. If fewer than 20 of the rated causes are mapped, the script says how to write larger sheets that keep the decisions already made (`sheets --n 40 --out-dir <new folder> --carry-from <old folder>`).

An agreed expression that is not in the candidates table needs one row there (role `alternative`: cause, expression, MeSH unique identifier, date introduced as YYYY-MM-DD, scope relation, inclusion note, all taken from the MeSH Browser), added with a text editor before the command is repeated. Both raters then see the same facts that enter the panel.

Form of an expression: one exploded descriptor, `"<Heading>"[Mesh]`. Where the mapping rule requires it, one descriptor with another removed, `("<Heading>"[Mesh] NOT "<Heading>"[Mesh])`, the form registered for F_AI_NOROB. A cause that coincides with a named field (Stroke, Diabetes Mellitus, COVID-19) keeps the expression of the named field and shares its cells; COVID-19, whose registered year window is 2020 to 2024, shares the cells of that window and has no cell for earlier years.

## 5. Build and checks

`reconcile` builds the panel: it writes `config/gbd_panel.yaml` (status `final`) to a temporary name, lets the pipeline's own loader validate it, moves it into place and writes `data/gbd/gbd_panel_amendment_table.md`. That table is pasted unchanged into Section 5 of the amendment. `python -m airct_benchmark check-catalogue` then confirms that the amendment lists exactly the panel of the file, row by row, that the panel file agrees with the deposited mapping table, ranking and export record (hashes, ranks, members), and that the generated text stands in the amendment as one unchanged block that was written for the files as they are now (the first line of the file, a comment, may be left out). `python scripts/gbd_panel.py build --status final` is run before this check, so that the text compared is the generated one. Every descriptor that is new relative to v2.0 is checked by `python -m airct_benchmark syntax-check --send` on publication year 2015 only; the counts viewed are listed in the Q18 addendum.

`python scripts/gbd_panel.py build --status final` rebuilds the same panel file and table from the mapping table; it serves the reproduction. A panel with status `final` cannot be built from a mapping table that `reconcile` did not write.

Exit codes of the script: 0 done; 1 the raters disagree and have to decide; 2 stopped, with a message that begins with "STOPPED:" and says what to do. No step repairs an input by itself.

## 6. What is deposited and what is not

Deposited in the repository, on Zenodo and on OSF: the ranking without values, the export record with all hashes, the candidates table, the two rater sheets (and the consensus sheet, where one was written), the mapping table, the panel file and the table of the amendment. Not deposited and not passed on outside the group of authors: the raw export, the hierarchy file and the ranking with DALY values. They are IHME data (IHME Free-of-Charge Non-commercial User Agreement), kept by the authors for verification on request, and identified by their SHA-256 hashes. Source: Institute for Health Metrics and Evaluation. Used with permission. All rights reserved.

Hashes: raw IHME files, SHA-256 of the file bytes; text files written by the script, SHA-256 of the UTF-8 content with LF line endings, so that the value does not depend on the platform.

## 7. Decisions taken at mapping

The decisions of this section are taken from `data/gbd/gbd_panel_mesh_mapping.csv`, the alternatives that were not chosen from `data/gbd/gbd_mesh_candidates.csv`. The two raters chose the same expression in each of the 30 rated rows, so that no row went to discussion.

Lower respiratory infections (rank 4): `("Pneumonia"[Mesh] NOT "COVID-19"[Mesh])`, scope relation narrower. COVID-19 is filed under Pneumonia, Viral, in the MeSH tree, so that the exploded Pneumonia heading contains the COVID-19 literature from 2020 on, although GBD counts COVID-19 as a separate cause and COVID-19 is a named field of this study. Not chosen: the plain heading `"Pneumonia"[Mesh]`, the broader heading `"Respiratory Tract Infections"[Mesh]`, which contains other GBD causes, and exclusion under rule (d). This is the only member whose expression has the form of one descriptor with another removed.

Cirrhosis and other chronic liver diseases (rank 22): `"Liver Cirrhosis"[Mesh]`, scope relation narrower, with the under-inclusion stated in the panel table. Not chosen: `"Liver Diseases"[Mesh]`, which contains other GBD causes in full (liver cancer, hepatitis).

Members whose expression is not an exact match, each with the over- or under-inclusion stated in the panel table: neonatal disorders (broader), lower respiratory infections (narrower), diarrheal diseases (mixed), age-related and other hearing loss (broader), tracheal, bronchus, and lung cancer (mixed), headache disorders (broader), cirrhosis and other chronic liver diseases (narrower).

Rule (d): both raters recorded "no single descriptor" for hypertensive heart disease (rank 29), for which the sheet held no proposal. The cause lies below the last panel member (rank 23). No cause ranked above the last panel member was excluded under rule (d): the first 20 causes that passed rules (a) to (c) are the panel.

COVID-19 (rank 26) lies below the last panel member and is not in the panel. The rule for a member that coincides with a named field of a shorter year window (Section 4, last paragraph) was therefore not applied.

## 8. Execution record (8 October 2026)

Export. Made by Clara Helene Buszello on 8 October 2026 with the German interface of the GBD Results Tool, permalink https://vizhub.healthdata.org/gbd-results/result/cba5012c3acc5245d5e8c6d034403867, file `IHME-GBD_2023_DATA-cba5012c-1.csv`: 760 rows, that is 380 causes of every level with the metrics Number and Rate; the script reads the metric Number (id 1). Hierarchy file: `IHME_GBD_2023_HIERARCHIES_Y2025M10D23.XLSX`, worksheet "Cause Hierarchy". Three earlier exports of 7 and 8 October 2026 were not used: the first held the single row "All causes", the second the measure Deaths, the third the measure DALYs with the cause list of the Deaths query, in which 36 Level 3 causes without deaths were missing. The script stops on each of them and writes no ranking.

Ranking. `rank`, 8 October 2026, 06:53 UTC: 176 Level 3 causes ranked; the completeness check was passed (ratio 1.0000 of the ranked causes to "All causes"); 18 causes excluded under rule (a), none under rule (b), 15 under rule (c); 143 causes kept for mapping. No cause name of the GBD 2023 hierarchy contains "pandemic-related", so rule (b) excludes nothing in this round. Five aggregates of the hierarchy file whose names begin with "Total" were not ranked (listed in the export record). Because the export is in German, the script could not compare its cause names with the hierarchy file (349 names differ by language). The German names of the causes of ranks 1 to 45 and of all 33 excluded causes were therefore read against the names of the hierarchy file on 8 October 2026, by Claude in the session that ran the commands and again by a separate instance of Claude that reviewed the package; each pair names the same cause. The rank order was in addition recomputed from the two raw files, twice, with code that is independent of `scripts/gbd_panel.py`, with the same result for all 176 causes. A reviewer who reads German can repeat the comparison with the columns cause_id and cause_name of the export and the deposited ranking.

Rating. `sheets`, 8 October 2026, 06:54 UTC: 30 causes (ranks 1 to 35 of the ranking). W. Polanski (WP) and I. Y. Eyüpoglu (IE) each went through all 30 rows alone and recorded one decision per row, WP at his workstation, IE at his own computer (Section 5.3 of the amendment). The completed sheets were saved for the deposit under the user account of the guarantor on 8 October 2026. Two versions of each sheet were handed over that day, saved at 06:58 and 07:00 UTC and again at 07:28 UTC; no cell differs between them, and the deposited sheets are the later versions. The sheets as received named the account of the guarantor as the one that saved the file, held the e-mail address of the rater in the author field, and held the path of the folder from which they had been opened. These three items (author, last saved by, folder path) were removed from the deposited copies on 9 October 2026 by decision of the guarantor, because they are personal data and an internal network path. Anthropic's Claude removed them from the property parts of the files; no cell and no other part of the files was changed, the times of creation and of the last save are still in the file properties, and `reconcile` gives the same mapping table, panel file and table from the deposited copies as from the files as received. The files as received are kept by the authors. Both raters accepted the proposed expression in 29 rows and recorded rule (d) in one row (Section 7). Neither rater chose an alternative or entered a comment. The proposals had been compiled with the assistance of Anthropic's Claude (Section 4); the decisions are those of the raters.

Reconciliation. `reconcile`, 8 October 2026: 30 of 30 rows agreed without discussion; no consensus sheet was written. SHA-256 of the two rater sheets as deposited (file bytes): `gbd_mapping_rater_WP.xlsx` 49084eefbab57de661a2f13939da472724db8a236595c1f856d8844c7b04d44e, `gbd_mapping_rater_IE.xlsx` 84a5b30f502e583e21a778ccd2fb18f37167e946f0b27a985d10336c60f40be4; as received from the raters: ab7271de83501ea5337d3641dc8429c88037ca9777462254f475f2d1bc5431c0 (WP) and a18227641d41ae6ce628be9edac5d2f216d16aff903bed626b4f29b703483e4a (IE). The hashes of the mapping table, the ranking, the raw files and the panel file are stated in the table of the amendment (Section 5.7) and in `data/gbd/gbd_export_record.json`.

Who ran the commands. No Python installation was available at the workstation of the guarantor. The commands `rank`, `sheets` and `reconcile` were therefore run by Anthropic's Claude in a cloud session on the files that the guarantor provided (the export, the hierarchy file, the citation text and the two completed sheets). The steps are deterministic. They are repeated by the reviewers on their own machines: `rank` with the two IHME files and the arguments of the export record gives the deposited ranking (the export record then differs in the time of the run only), `reconcile` with the deposited sheets gives the deposited mapping table, panel file and table, and `build --status final` gives the panel file and table from the mapping table alone. `python -m airct_benchmark check-catalogue` then ends with exit code 0 and prints the SHA-256 of the panel file that the table of the amendment states. Repeated by C. H. Buszello on 9 October 2026 on a Windows machine (Python 3.13.3): `reconcile` with the sheets as received (the file properties were removed after her run) and, in a copy of the folder, `rank` with her export of 8 October 2026, the hierarchy file and the citation text. After each of the two, `check-catalogue` confirmed strict identity and printed the SHA-256 of the panel file stated in the amendment (b91fd005303816cc191301a73241b37b9db0850877742f947d51736476437f2c). The check passes only if the ranking, the mapping table and the raw export are the ones whose hashes the panel file states.
