"""Command-line entry point of the pipeline.

Online modes (send requests to PubMed):
  smoke            one cell: Diabetes Mellitus, family A, 2015; compared with the Q18 reference 18,723
  freeze           the complete count catalogue twice in one session (Run A, then Run B)
  lists            family L (PMID lists) and family O (efetch XML) for AI and STROKE 2024, with Q13 sampling

Offline modes (no network):
  check-catalogue  string identity of config/catalogue.yaml against the registration text (Step 3)
  identifiers      registration identifiers from saved efetch XML (12.8)
  ratingsheet      rating sheets (title, abstract, journal, year, PMID only) from saved XML (Q24)
  manifest         SHA-256 manifest of a directory; verify-manifest checks one

Rule of the registration (Q8, Q9, Other): before the freeze date, 12 October 2026, no query other
than the smoke-test cell may be sent to PubMed. ``freeze`` and ``lists`` therefore refuse to run
before that date unless --override-freeze-guard is given, and the override is written to the log.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import platform
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from . import __version__
from .catalogue import Catalogue, CatalogueError, DEFAULT_CATALOGUE_PATH, PACKAGE_ROOT, load_catalogue
from .eutils import EsearchCount, EutilsClient, TransportError
from .identifiers import IdentifierExtractor, summarize, write_identifiers_csv
from .manifest import verify_manifest, write_manifest
from .pubmed_xml import parse_pubmed_xml, returned_pmids
from .queries import (
    QuerySpec,
    build_count_queries,
    build_list_queries,
    check_against_preregistration,
    count_summary,
    load_prereg_text,
    smoke_query,
    smoke_reference_count,
)
from .sampling import CellSample, draw_all_cells, replace_missing, write_cell_csvs
from .util import Redactor, env_api_key, git_metadata, sha256_text, utc_compact_seconds, utc_date, utc_iso, utc_now, write_json

log = logging.getLogger("airct_benchmark.run")

CSV_COLUMNS = ["run", "family", "field", "year", "metric", "query", "querytranslation", "count", "utc", "http_status", "attempt"]


# ---------------------------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------------------------

def setup_logging(out_dir: Path, redactor: Redactor, verbose: bool = False) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / f"run_{utc_compact_seconds()}.log"
    root = logging.getLogger("airct_benchmark")
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    class RedactingFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.msg = redactor(record.getMessage())
            record.args = ()
            return True

    for handler in (logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler(sys.stdout)):
        handler.setFormatter(fmt)
        handler.addFilter(RedactingFilter())
        root.addHandler(handler)
    return log_path


def finish_with_manifest(out_dir: Path) -> Path:
    """Close the run log and write the manifest as the very last action, so that the log file
    itself is covered by the manifest with its final content."""
    root = logging.getLogger("airct_benchmark")
    for h in list(root.handlers):
        if isinstance(h, logging.FileHandler):
            h.flush()
            root.removeHandler(h)
            h.close()
    path = write_manifest(out_dir)
    print(f"manifest written: {path}")
    return path


def make_client(cat: Catalogue, raw_dir: Path, session=None, **overrides) -> EutilsClient:
    e = cat.eutils
    api_key = env_api_key(cat.api_key_env())
    if not api_key:
        log.warning("no API key in %s: rate limited to %s requests per second", cat.api_key_env(), e["requests_per_second_without_key"])
    kwargs: dict[str, Any] = dict(
        api_key=api_key,
        raw_dir=raw_dir,
        base_url=e["base_url"],
        db=e["db"],
        tool=e["tool"],
        email=e["email"],
        requests_per_second=e["requests_per_second_with_key"] if api_key else e["requests_per_second_without_key"],
        backoff_seconds=e["backoff_seconds"],
        max_attempts=e["max_attempts"],
        timeout=e["timeout_seconds"],
        efetch_batch_size=e["efetch_batch_size"],
        esearch_page_size=e["esearch_page_size"],
        history_threshold=e["history_threshold"],
        max_get_url_length=e["max_get_url_length"],
        session=session,
    )
    kwargs.update(overrides)
    return EutilsClient(**kwargs)


def freeze_guard(cat: Catalogue, override: bool, today: date | None = None) -> None:
    """Refuse full runs before the registered freeze date unless explicitly overridden."""
    freeze_date = date.fromisoformat(str(cat.freeze["date"]))
    today = today or utc_now().date()
    if today < freeze_date:
        if override:
            log.warning("FREEZE GUARD OVERRIDDEN: today %s is before the registered freeze date %s. "
                        "Any count viewed now is prior knowledge and must be disclosed.", today, freeze_date)
            return
        raise SystemExit(
            f"Refusing to query PubMed: today ({today}) is before the registered freeze date {freeze_date}. "
            "Before that date only the smoke-test cell (Diabetes Mellitus, 2015) may be run. "
            "Use --override-freeze-guard only with a documented reason."
        )


def header_lines(cat: Catalogue, run_label: str, start_utc: str, end_utc: str, n_queries: int, extra: dict | None = None) -> list[str]:
    git = git_metadata(PACKAGE_ROOT)
    lines = [
        "# airct_benchmark frozen count file",
        f"# run: {run_label}",
        f"# retrieval_start_utc: {start_utc}",
        f"# retrieval_end_utc: {end_utc}",
        f"# git_commit: {git['commit']}{' (dirty working tree)' if git['dirty'] else ''}",
        f"# git_describe: {git['describe']}",
        f"# pipeline_version: {__version__}",
        f"# eutils_base_url: {cat.eutils['base_url']}",
        f"# catalogue_sha256: {sha256_text(cat.text)}",
        f"# registration: {cat.registration['osf_registration']} (DOI {cat.registration['osf_doi']})",
        f"# python: {platform.python_version()} ({platform.platform()})",
        f"# queries: {n_queries}",
        "# columns: " + ",".join(CSV_COLUMNS),
    ]
    for k, v in (extra or {}).items():
        lines.append(f"# {k}: {v}")
    return lines


def write_counts_csv(path: Path, rows: list[dict], header: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        for line in header:
            fh.write(line + "\n")
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in CSV_COLUMNS})


def row_from_result(run_label: str, spec: QuerySpec, res: EsearchCount) -> dict:
    return {
        "run": run_label,
        "family": spec.family,
        "field": spec.field,
        "year": spec.year,
        "metric": spec.metric,
        "query": spec.term,
        "querytranslation": res.querytranslation,
        "count": "" if res.count is None else res.count,
        "utc": res.utc,
        "http_status": "" if res.http_status is None else res.http_status,
        "attempt": res.attempt,
    }


def issue_record(run_label: str, spec: QuerySpec, res: EsearchCount) -> dict | None:
    if not res.has_issues:
        return None
    return {
        "run": run_label,
        "query_id": spec.query_id,
        "query": spec.term,
        "count": res.count,
        "error": res.error,
        "errorlist": res.errorlist,
        "warninglist": res.warninglist,
        "http_status": res.http_status,
        "attempt": res.attempt,
        "utc": res.utc,
        "raw_path": res.raw_path,
    }


def execute_counts(
    client: EutilsClient,
    specs: Sequence[QuerySpec],
    run_label: str,
    partial_path: Path,
    issues_path: Path,
    progress_every: int = 100,
) -> tuple[list[dict], int, int]:
    """Run all count queries in order; stream rows to a partial CSV as a crash safety net.

    Returns (rows, number of failed cells, number of cells with PubMed warnings or error lists)."""
    rows: list[dict] = []
    failures = 0
    issues = 0
    partial_path.parent.mkdir(parents=True, exist_ok=True)
    with open(partial_path, "w", newline="", encoding="utf-8") as pfh, open(issues_path, "a", encoding="utf-8") as ifh:
        pw = csv.DictWriter(pfh, fieldnames=CSV_COLUMNS, lineterminator="\n")
        pw.writeheader()
        for i, spec in enumerate(specs, 1):
            res = client.esearch_count(spec.term, f"{run_label}__{spec.query_id}")
            row = row_from_result(run_label, spec, res)
            rows.append(row)
            pw.writerow(row)
            pfh.flush()
            if not res.ok:
                failures += 1
                log.error("run %s cell %s FAILED: %s", run_label, spec.query_id, res.error)
            issue = issue_record(run_label, spec, res)
            if issue:
                issues += 1
                ifh.write(json.dumps(issue, ensure_ascii=False) + "\n")
                ifh.flush()
                if res.ok:
                    log.warning("run %s cell %s: PubMed warning or error list: %s %s", run_label, spec.query_id, res.errorlist, res.warninglist)
            if i % progress_every == 0 or i == len(specs):
                log.info("run %s: %d/%d queries done", run_label, i, len(specs))
    return rows, failures, issues


# ---------------------------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------------------------

def mode_smoke(args: argparse.Namespace, cat: Catalogue, session=None) -> int:
    out_dir = Path(args.out)
    api_key = env_api_key(cat.api_key_env())
    setup_logging(out_dir, Redactor([api_key] if api_key else []), args.verbose)
    try:
        spec = smoke_query(cat, args.family, args.metric)
    except CatalogueError as exc:
        raise SystemExit(f"smoke test refused: {exc}. Only cells of the registered smoke field and year "
                         f"({cat.smoke_test['field']} {cat.smoke_test['year']}) may be run before the freeze date.") from exc
    reference = smoke_reference_count(cat, spec.family, spec.metric)
    log.info("smoke test cell %s", spec.query_id)
    log.info("query: %s", spec.term)
    client = make_client(cat, out_dir / "raw" / "smoke", session=session)
    res = client.esearch_count(spec.term, f"smoke__{spec.query_id}")
    result = {
        "mode": "smoke",
        "utc": res.utc,
        "query_id": spec.query_id,
        "query": spec.term,
        "count": res.count,
        "querytranslation": res.querytranslation,
        "http_status": res.http_status,
        "attempt": res.attempt,
        "error": res.error,
        "errorlist": res.errorlist,
        "warninglist": res.warninglist,
        "reference_count": reference,
        "reference_source": cat.smoke_test["reference_source"],
        "difference": (res.count - reference) if (res.ok and reference is not None) else None,
        "pipeline_version": __version__,
        "git": git_metadata(PACKAGE_ROOT),
        "raw_path": res.raw_path,
    }
    path = out_dir / f"smoke_{utc_compact_seconds()}.json"
    write_json(path, result)
    if not res.ok:
        log.error("smoke test FAILED: %s", res.error)
        return 2
    log.info("count=%s querytranslation=%s http=%s attempt=%s", res.count, res.querytranslation, res.http_status, res.attempt)
    if reference is not None:
        log.info("reference %s (%s): difference %+d (deviations are expected from live updates and are logged, not failures)",
                 reference, cat.smoke_test["reference_source"], res.count - reference)
    if res.has_issues:
        log.warning("PubMed reported errorlist=%s warninglist=%s", res.errorlist, res.warninglist)
    log.info("smoke result written to %s", path)
    return 0


def mode_freeze(args: argparse.Namespace, cat: Catalogue, session=None) -> int:
    start = utc_now()
    stamp = utc_date(start)
    out_dir = Path(args.out) / f"freeze_{stamp}"
    api_key = env_api_key(cat.api_key_env())
    setup_logging(out_dir, Redactor([api_key] if api_key else []), args.verbose)
    freeze_guard(cat, args.override_freeze_guard)
    specs = build_count_queries(cat, args.families)
    log.info("freeze run: %d count queries, families %s", len(specs), count_summary(specs))
    template = cat.freeze["csv_name_template"]
    written: list[Path] = []
    total_failures = 0
    run_labels = list(cat.freeze["runs"]) if not args.single_run else [cat.freeze["runs"][0]]
    for run_label in run_labels:
        client = make_client(cat, out_dir / "raw" / f"run{run_label}", session=session)
        run_start = utc_iso()
        log.info("run %s start %s", run_label, run_start)
        rows, failures, issues = execute_counts(
            client, specs, run_label,
            out_dir / f"counts_{stamp}_run{run_label}.partial.csv",
            out_dir / f"issues_{stamp}_run{run_label}.jsonl",
        )
        run_end = utc_iso()
        header = header_lines(cat, run_label, run_start, run_end, len(specs), {"requests_sent": client.request_count,
                                                                                "failed_cells": failures,
                                                                                "cells_with_pubmed_warnings_or_errors": issues})
        path = out_dir / template.format(date=stamp, run=run_label)
        write_counts_csv(path, rows, header)
        (out_dir / f"counts_{stamp}_run{run_label}.partial.csv").unlink(missing_ok=True)
        written.append(path)
        total_failures += failures
        log.info("run %s end %s: %d rows, %d failed cells, %d cells with warnings; written %s", run_label, run_end, len(rows), failures, issues, path.name)
    # catalogue snapshot and query list for the audit trail
    (out_dir / "catalogue_snapshot.yaml").write_text(cat.text, encoding="utf-8")
    write_json(out_dir / "queries.json", [s.as_dict() for s in specs])
    if len(written) == 2:
        _log_run_difference(written[0], written[1])
    log.info("freeze session finished: %d failed cells in total", total_failures)
    finish_with_manifest(out_dir)
    return 0 if total_failures == 0 else 3


def _log_run_difference(path_a: Path, path_b: Path) -> None:
    """Number of cells whose count differs between Run A and Run B (information only; E11 is Step 7)."""
    def load(p: Path) -> dict[tuple, str]:
        with open(p, encoding="utf-8") as fh:
            reader = csv.DictReader(line for line in fh if not line.startswith("#"))
            return {(r["family"], r["field"], r["year"], r["metric"]): r["count"] for r in reader}
    a, b = load(path_a), load(path_b)
    differing = sum(1 for k in a if a[k] != b.get(k))
    log.info("Run A versus Run B: %d of %d cells differ in count (E11 diagnostic is computed in the analysis step)", differing, len(a))


def mode_lists(args: argparse.Namespace, cat: Catalogue, session=None) -> int:
    start = utc_now()
    stamp = utc_date(start)
    out_dir = Path(args.out) / f"lists_{stamp}"
    api_key = env_api_key(cat.api_key_env())
    setup_logging(out_dir, Redactor([api_key] if api_key else []), args.verbose)
    freeze_guard(cat, args.override_freeze_guard)
    client = make_client(cat, out_dir / "raw", session=session)
    specs = build_list_queries(cat)
    lists_dir = out_dir / "pmid_lists"
    lists_dir.mkdir(parents=True, exist_ok=True)

    # ---- family L: PMID lists ----------------------------------------------------------------
    lists: dict[str, list[int]] = {}
    list_meta: dict[str, dict] = {}
    for spec in specs:
        key = f"{spec.metric}_{spec.field}"  # B_AI, S_AI, R_AI, ...
        log.info("list %s: %s", key, spec.term)
        try:
            pmids, head, notes = client.esearch_ids(spec.term, f"L__{spec.query_id}")
        except TransportError as exc:
            log.error("list %s failed: %s", key, exc)
            return 3
        lists[key] = pmids
        (lists_dir / f"pmids_{key}_{spec.year}.txt").write_text("\n".join(str(p) for p in pmids) + "\n", encoding="utf-8")
        list_meta[key] = {"query_id": spec.query_id, "query": spec.term, "count": head.count, "retrieved": len(pmids),
                          "querytranslation": head.querytranslation, "utc": head.utc, "http_status": head.http_status,
                          "attempt": head.attempt, "notes": notes}
        for n in notes:
            log.warning("list %s: %s", key, n)
        log.info("list %s: count %s, %d identifiers", key, head.count, len(pmids))
    write_json(lists_dir / "lists_meta.json", {"utc_start": utc_iso(start), "year": cat.lists["year"], "lists": list_meta})

    # ---- Q13 sampling -----------------------------------------------------------------------
    samples = draw_all_cells(lists, cat.sampling)
    sample_dir = out_dir / "samples"
    write_cell_csvs(samples, sample_dir)
    for s in samples:
        log.info("cell %s: population %d, pilot %d, formal %d, reserve %d, rule %s%s",
                 s.cell, s.population_size, len(s.pilot), len(s.formal), len(s.reserve), s.rule,
                 ("; " + "; ".join(s.notes)) if s.notes else "")

    if args.no_efetch:
        write_json(sample_dir / "sampling_report.json", _sampling_report(samples, {}))
        (out_dir / "catalogue_snapshot.yaml").write_text(cat.text, encoding="utf-8")
        log.info("lists mode finished without efetch (--no-efetch)")
        finish_with_manifest(out_dir)
        return 0

    # ---- family O: efetch XML --------------------------------------------------------------
    xml_dir = out_dir / "xml"
    fetched: dict[str, dict] = {}
    missing_report: dict[str, list[int]] = {}
    for fld in cat.field_group(cat.lists["fields"]):
        # every PMID of the family B list (S8 and V-cells)
        fetched[f"B_{fld}"] = _efetch_to_dir(client, lists[f"B_{fld}"], xml_dir / f"B_{fld}", f"O__B_{fld}")
        missing_report[f"B_{fld}"] = fetched[f"B_{fld}"]["missing"]
    for s in samples:
        key = s.cell
        fld = key.split("-", 1)[1]
        if s.source_list.startswith("B_"):
            # V-cells are subsets of the complete family B list, whose XML is already fetched.
            covered = _pmids_in_dir(xml_dir / f"B_{fld}")
            info = {"requested": len(s.requested), "returned": len([p for p in s.requested if p in covered]),
                    "missing": [p for p in s.requested if p not in covered], "batches": 0, "methods": [],
                    "xml_source": f"xml/B_{fld}"}
        else:
            info = _efetch_to_dir(client, s.requested, xml_dir / key, f"O__{key}")
        # Q14: replace unretrievable PMIDs by the next PMID of the seeded sequence, then fetch the replacements
        rounds = 0
        while info["missing"] and rounds < 10:
            added = replace_missing(s, info["missing"])
            rounds += 1
            if not added:
                break
            more = _efetch_to_dir(client, added, xml_dir / key, f"O__{key}__replacement{rounds}", start_index=info["batches"])
            info["batches"] += more["batches"]
            info["returned"] += more["returned"]
            info["missing"] = more["missing"]
        fetched[key] = info
        missing_report[key] = info["missing"]
    write_json(sample_dir / "sampling_report.json", _sampling_report(samples, missing_report))
    write_json(xml_dir / "efetch_report.json", fetched)

    # ---- 12.8 identifiers from the complete B lists ----------------------------------------
    ids_dir = out_dir / "identifiers"
    extractor = IdentifierExtractor(cat.identifiers["regex"], cat.identifiers["trial_registry_databanks"])
    all_ids, field_by_pmid, summaries = [], {}, {}
    for fld in cat.field_group(cat.lists["fields"]):
        records = _parse_dir(xml_dir / f"B_{fld}")
        ids = extractor.extract(records.values())
        all_ids.extend(ids)
        field_by_pmid.update({p: fld for p in records})
        summaries[fld] = summarize(fld, lists[f"B_{fld}"], ids)
    write_identifiers_csv(ids_dir / f"identifiers_{cat.lists['year']}.csv", field_by_pmid, all_ids)
    write_json(ids_dir / "identifiers_summary.json", summaries)
    for fld, summ in summaries.items():
        log.info("identifiers %s: %d records, %d with identifier, %d distinct identifiers", fld, summ["records"],
                 summ["records_with_identifier"], summ["distinct_identifiers"])

    (out_dir / "catalogue_snapshot.yaml").write_text(cat.text, encoding="utf-8")
    log.info("lists mode finished")
    finish_with_manifest(out_dir)
    return 0


def _efetch_to_dir(client: EutilsClient, pmids: list[int], target: Path, label: str, start_index: int = 0) -> dict:
    target.mkdir(parents=True, exist_ok=True)
    batches = client.efetch_xml(pmids, label)
    got: set[int] = set()
    for i, b in enumerate(batches, start_index + 1):
        (target / f"batch_{i:04d}.xml").write_text(b.xml, encoding="utf-8")
        got |= returned_pmids(b.xml)
    missing = sorted(set(pmids) - got)
    if missing:
        log.warning("%s: %d PMIDs not returned by efetch: %s", label, len(missing), missing[:20])
    return {"requested": len(pmids), "returned": len(got & set(pmids)), "missing": missing, "batches": len(batches),
            "methods": sorted({b.method for b in batches})}


def _pmids_in_dir(xml_dir: Path) -> set[int]:
    got: set[int] = set()
    for p in sorted(xml_dir.glob("*.xml")):
        got |= returned_pmids(p.read_text(encoding="utf-8"))
    return got


def _parse_dir(xml_dir: Path) -> dict[int, Any]:
    records: dict[int, Any] = {}
    for p in sorted(xml_dir.glob("*.xml")):
        for rec in parse_pubmed_xml(p.read_text(encoding="utf-8")):
            records[rec.pmid] = rec
    return records


def _sampling_report(samples: list[CellSample], missing: dict[str, list[int]]) -> dict:
    return {
        "seed": 20260904,
        "rule": "random.Random(20260904).sample on the ascending PMID list; pilot 20 drawn first (Q13); "
                "replacement by the next PMID of the seeded sequence (Q14); see sampling.py docstring, decision I1",
        "cells": [{**s.as_dict(), "missing_after_replacement": missing.get(s.cell, [])} for s in samples],
        "census_lists_missing": {k: v for k, v in missing.items() if k.startswith("B_")},
    }


def mode_check_catalogue(args: argparse.Namespace, cat: Catalogue) -> int:
    text = load_prereg_text(args.prereg)
    report = check_against_preregistration(cat, text)
    print(report.summary())
    strict_fail = report.failures(strict=True)
    lenient_fail = report.failures(strict=False)
    if lenient_fail:
        print("\nNOT FOUND even ignoring whitespace (character difference, must be resolved):")
        for item in lenient_fail:
            print(f"  [{item.kind}] {item.name}: {item.text}")
    elif strict_fail:
        print("\nFound only after removing whitespace (line wraps in the source text; verify against the Markdown file):")
        for item in strict_fail:
            print(f"  [{item.kind}] {item.name}")
    if args.json:
        write_json(args.json, {"summary": report.summary(), "strict_ok": report.strict_ok, "lenient_ok": report.lenient_ok,
                               "items": [asdict(i) for i in report.items]})
    if report.strict_ok:
        print("\nRESULT: strict string identity confirmed for every catalogue component.")
        return 0
    if report.lenient_ok:
        print("\nRESULT: identity confirmed up to whitespace only; run the check against the Markdown registration file for the strict result.")
        return 1
    print("\nRESULT: character differences found.")
    return 2


def mode_identifiers(args: argparse.Namespace, cat: Catalogue) -> int:
    extractor = IdentifierExtractor(cat.identifiers["regex"], cat.identifiers["trial_registry_databanks"])
    xml_dir = Path(args.xml_dir)
    records = _parse_dir(xml_dir)
    ids = extractor.extract(records.values())
    field_by_pmid = {p: args.field for p in records}
    out = Path(args.out)
    write_identifiers_csv(out, field_by_pmid, ids)
    summary = summarize(args.field, records.keys(), ids)
    write_json(out.with_suffix(".summary.json"), summary)
    print(json.dumps(summary, indent=2))
    return 0


def mode_ratingsheet(args: argparse.Namespace, cat: Catalogue) -> int:
    """Rating sheet for the validation substudy (Q24): title, abstract, journal, year and PMID only.
    MeSH terms and publication types are deliberately not written."""
    records = _parse_dir(Path(args.xml_dir))
    wanted = None
    if args.pmids:
        wanted = [int(line.split(",")[-1]) if "," in line else int(line) for line in Path(args.pmids).read_text().splitlines()
                  if line.strip() and not line.startswith("cell")]
    pmids = wanted if wanted is not None else sorted(records)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["pmid", "year", "journal", "title", "abstract", "V1", "V2", "V3", "V4", "V5", "V6", "rater", "comment"])
        for p in pmids:
            r = records.get(int(p))
            if r is None:
                w.writerow([p, "", "", "[XML not available]", "", "", "", "", "", "", "", "", ""])
                continue
            w.writerow([r.pmid, r.year, r.journal, r.title, r.abstract, "", "", "", "", "", "", "", ""])
    print(f"rating sheet with {len(pmids)} records written to {out}")
    return 0


def mode_manifest(args: argparse.Namespace) -> int:
    path = write_manifest(args.dir)
    print(f"manifest written: {path}")
    return 0


def mode_verify_manifest(args: argparse.Namespace) -> int:
    problems = verify_manifest(args.dir)
    if problems:
        print("\n".join(problems))
        return 2
    print("manifest verified: every listed file matches")
    return 0


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="airct_benchmark", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--catalogue", default=str(DEFAULT_CATALOGUE_PATH), help="path to config/catalogue.yaml")
    p.add_argument("--verbose", action="store_true")
    sub = p.add_subparsers(dest="mode", required=True)

    s = sub.add_parser("smoke", help="one cell: Diabetes Mellitus 2015 (family A by default)")
    s.add_argument("--out", default="out", help="output directory")
    s.add_argument("--family", default=None, help="family letter within Diabetes Mellitus 2015 (default A)")
    s.add_argument("--metric", default=None, help="metric within the family (default den)")

    f = sub.add_parser("freeze", help="complete catalogue, Run A then Run B")
    f.add_argument("--out", default="out")
    f.add_argument("--override-freeze-guard", action="store_true", help="run before the registered freeze date (logged)")
    f.add_argument("--single-run", action="store_true", help="Run A only (testing and reproduction tooling)")
    f.add_argument("--families", nargs="*", default=None, help="restrict to family letters (testing only)")

    l = sub.add_parser("lists", help="family L PMID lists, Q13 sampling, family O efetch XML, 12.8 identifiers")
    l.add_argument("--out", default="out")
    l.add_argument("--override-freeze-guard", action="store_true")
    l.add_argument("--no-efetch", action="store_true", help="lists and sampling only")

    c = sub.add_parser("check-catalogue", help="string identity against the registration text (offline)")
    c.add_argument("--prereg", required=True, help="Preregistration_v2.0_FINAL_2026-09-04.md (or a text export)")
    c.add_argument("--json", default=None, help="write the full report as JSON")

    i = sub.add_parser("identifiers", help="registration identifiers from saved efetch XML (offline)")
    i.add_argument("--xml-dir", required=True)
    i.add_argument("--field", required=True, help="field key written into the output (AI or STROKE)")
    i.add_argument("--out", required=True, help="output CSV")

    r = sub.add_parser("ratingsheet", help="rating sheet without MeSH terms and publication types (offline)")
    r.add_argument("--xml-dir", required=True)
    r.add_argument("--pmids", default=None, help="optional sample CSV or PMID list restricting the sheet")
    r.add_argument("--out", required=True)

    m = sub.add_parser("manifest", help="write MANIFEST_SHA256.txt for a directory (offline)")
    m.add_argument("--dir", required=True)
    v = sub.add_parser("verify-manifest", help="verify MANIFEST_SHA256.txt of a directory (offline)")
    v.add_argument("--dir", required=True)
    return p


def main(argv: Sequence[str] | None = None, session=None) -> int:
    args = build_parser().parse_args(argv)
    cat = load_catalogue(args.catalogue)
    if args.mode == "smoke":
        return mode_smoke(args, cat, session)
    if args.mode == "freeze":
        return mode_freeze(args, cat, session)
    if args.mode == "lists":
        return mode_lists(args, cat, session)
    if args.mode == "check-catalogue":
        return mode_check_catalogue(args, cat)
    if args.mode == "identifiers":
        return mode_identifiers(args, cat)
    if args.mode == "ratingsheet":
        return mode_ratingsheet(args, cat)
    if args.mode == "manifest":
        return mode_manifest(args)
    if args.mode == "verify-manifest":
        return mode_verify_manifest(args)
    raise SystemExit(f"unknown mode {args.mode}")


if __name__ == "__main__":
    sys.exit(main())
