"""Command-line entry point of the pipeline.

Online modes (send requests to PubMed):
  smoke            one cell: Diabetes Mellitus, family A, 2015; compared with the Q18 reference 18,723
  syntax-check     Amendment v3.0: the new expressions, publication year 2015 only, Diabetes Mellitus
                   in place of Stroke; writes the Q18 addendum (run once, before the OSF update).
                   Sends with --send only; without it the plan is printed and nothing is sent
  freeze           the complete count catalogue twice in one session (Run A, then Run B)
  lists            families L and LV (PMID lists) and family O (efetch XML) for 2024, with the
                   validation sampling of Amendment v3.0 (Section 6.1)

Offline modes (no network):
  check-catalogue  string identity of config/catalogue.yaml against the registration text and
                   against Amendment v3.0 (code review before the release is tagged)
  identifiers      registration identifiers from saved efetch XML (12.8)
  ratingsheet      rating sheets (title, abstract, journal, year, PMID only) from saved XML (Q24)
  manifest         SHA-256 manifest of a directory; verify-manifest checks one

Rule of the registration (Q8, Q9, Other) and of Amendment v3.0 (Sections 1.4 and 8.3): before the
freeze date no query may be sent to PubMed other than the smoke-test cell and the syntax check of
new expressions, both restricted to publication year 2015. ``freeze`` and ``lists`` therefore
refuse to run before that date unless --override-freeze-guard is given, and the override is
written to the log. ``freeze``, ``lists`` and ``syntax-check --send`` also refuse to run while the
GBD panel file is provisional.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import platform
import shutil
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from . import __version__
from .catalogue import Catalogue, CatalogueError, DEFAULT_CATALOGUE_PATH, GBD_FAMILIES, PACKAGE_ROOT, load_catalogue, mesh_headings
from .eutils import EsearchCount, EutilsClient, TransportError
from .identifiers import IdentifierExtractor, summarize, write_identifiers_csv
from .manifest import verify_manifest, write_manifest
from .pubmed_xml import parse_pubmed_xml, returned_pmids
from .queries import (
    CheckReport,
    QuerySpec,
    SyntaxCheckItem,
    build_count_queries,
    build_list_specs,
    build_syntax_check_plan,
    check_against_amendment,
    check_against_preregistration,
    count_summary,
    load_prereg_text,
    shared_cells,
    smoke_query,
    smoke_reference_count,
    syntax_check_violation,
)
from .sampling import CellSample, draw_cells, replace_missing, write_cell_csvs
from .util import (Redactor, env_api_key, git_metadata, safe_filename, sha256_text, source_fingerprint, utc_compact_seconds, utc_date,
                   utc_iso, utc_now, write_json)

log = logging.getLogger("airct_benchmark.run")
PACKAGE_DIR = Path(__file__).resolve().parent      # the Python sources that source_fingerprint() identifies

CSV_COLUMNS = ["run", "family", "field", "year", "metric", "query", "querytranslation", "count", "utc", "http_status", "attempt"]
ONLINE_MODES = ("smoke", "syntax-check", "freeze", "lists")


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
            "Before that date only the smoke-test cell (Diabetes Mellitus, 2015) and the syntax check of "
            "Amendment v3.0 (publication year 2015 only) may be run. "
            "Use --override-freeze-guard only with a documented reason."
        )


def refuse_existing_output(out_dir: Path, what: str) -> None:
    """A run never writes into a directory that already holds files: a second run on the same day
    would mix raw responses, XML and issue lines of two sessions. Whether a session is repeated is
    a protocol decision; the earlier directory is kept and renamed by the person who decides."""
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"Refusing to run {what}: the output directory {out_dir} exists and is not empty. Keep it, rename it "
                         "(for example by adding _first_attempt) or choose another --out, and document why the run is repeated.")


def snapshot(source: Path | None, text: str, target: Path) -> None:
    """Copy a configuration file into the output directory byte for byte (the text is written only
    when the catalogue was not loaded from a file)."""
    if source is not None and Path(source).is_file():
        shutil.copyfile(source, target)
    else:
        target.write_text(text, encoding="utf-8")


def require_final_gbd_panel(cat: Catalogue, what: str, session=None) -> None:
    """Refuse an online mode while the GBD panel file is provisional, and refuse the synthetic
    panel of the test suite unless the E-utilities session is injected (offline tests).

    There is no override: the panel is fixed by the export and the reconciled mapping of
    Amendment v3.0, Section 5, and is written by scripts/gbd_panel.py with status 'final'."""
    if not cat.gbd_is_final:
        raise SystemExit(
            f"Refusing to run {what}: the GBD panel file {cat.gbd_path} has status '{cat.gbd_status}'. "
            "Generate the final panel with scripts/gbd_panel.py (export, two rater sheets, reconciliation) first."
        )
    if cat.gbd_is_test_fixture and session is None:
        raise SystemExit(
            f"Refusing to run {what}: {cat.gbd_path} is the synthetic GBD panel of the test suite and must never be sent to PubMed."
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
        f"# source_sha256: {source_fingerprint(PACKAGE_DIR)} (airct_benchmark/*.py, LF line endings)",
        f"# pipeline_version: {__version__}",
        f"# eutils_base_url: {cat.eutils['base_url']}",
        f"# catalogue_sha256: {sha256_text(cat.text)}",
        f"# gbd_panel_sha256: {cat.gbd_sha256()} (status {cat.gbd_status})",
        f"# registration: {cat.registration['osf_registration']} (DOI {cat.registration['osf_doi']})",
        f"# amendment: v{cat.amendment['version']} ({cat.amendment['document']})",
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
        "source_sha256": source_fingerprint(PACKAGE_DIR),
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
    # every refusal comes before the output directory is created
    freeze_guard(cat, args.override_freeze_guard)
    try:
        specs = build_count_queries(cat, args.families)
        shared = shared_cells(cat)      # proves, before the first request, that every shared cell is held by an identical query
    except CatalogueError as exc:
        raise SystemExit(f"freeze refused: {exc}") from exc
    if any(s.family in GBD_FAMILIES for s in specs) or not args.families:
        require_final_gbd_panel(cat, "the freeze run", session)
    refuse_existing_output(out_dir, "the freeze run")
    api_key = env_api_key(cat.api_key_env())
    setup_logging(out_dir, Redactor([api_key] if api_key else []), args.verbose)
    freeze_guard(cat, args.override_freeze_guard)      # again, so that an override is written into the run log
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
    # catalogue snapshot, GBD panel snapshot, query list and shared-cell map for the audit trail
    snapshot(cat.path, cat.text, out_dir / "catalogue_snapshot.yaml")
    snapshot(cat.gbd_path, cat.gbd_text, out_dir / "gbd_panel_snapshot.yaml")
    write_json(out_dir / "queries.json", [s.as_dict() for s in specs])
    write_json(out_dir / "shared_cells.json", shared)
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


class ListsFailure(RuntimeError):
    """The lists run cannot go on without risking a wrong sampling frame or wrong replacements."""


LIST_READINGS = 3              # a PMID list whose length differs from its count is read again, up to three readings
MASS_FAILURE_MIN = 5           # more unretrievable records than this in one efetch call ...
MASS_FAILURE_SHARE = 0.05      # ... and more than this share of the call: an infrastructure failure, not Q14


def _read_list(client: EutilsClient, ls) -> tuple[list[int], EsearchCount, list[str]]:
    """One complete PMID list. A list is a sampling frame: it is accepted only when the number of
    identifiers retrieved equals the count PubMed reported for the same request."""
    notes: list[str] = []
    for reading in range(1, LIST_READINGS + 1):
        label = f"{ls.list_family}__{ls.spec.query_id}" + ("" if reading == 1 else f"__reading{reading}")
        pmids, head, reading_notes = client.esearch_ids(ls.spec.term, label, year=int(ls.spec.year))
        if head.count == len(pmids):
            return pmids, head, notes + reading_notes
        note = f"reading {reading}: count {head.count}, {len(pmids)} identifiers retrieved ({'; '.join(reading_notes)})"
        notes.append(note)
        log.warning("list %s incomplete, %s; the list is read again", ls.key, note)
    raise ListsFailure(f"list {ls.key}: count and number of identifiers retrieved differ in {LIST_READINGS} readings "
                       f"({' | '.join(notes)}). No sample is drawn from an incomplete list.")


def mode_lists(args: argparse.Namespace, cat: Catalogue, session=None) -> int:
    start = utc_now()
    stamp = utc_date(start)
    out_dir = Path(args.out) / f"lists_{stamp}"
    # every refusal comes before the output directory is created
    freeze_guard(cat, args.override_freeze_guard)
    require_final_gbd_panel(cat, "the lists run", session)   # the lists belong to the freeze session of the released catalogue
    refuse_existing_output(out_dir, "the lists run")
    api_key = env_api_key(cat.api_key_env())
    setup_logging(out_dir, Redactor([api_key] if api_key else []), args.verbose)
    freeze_guard(cat, args.override_freeze_guard)      # again, so that an override is written into the run log
    client = make_client(cat, out_dir / "raw", session=session)
    try:
        return _lists_run(args, cat, client, out_dir, start)
    except (TransportError, ListsFailure) as exc:
        log.error("lists run STOPPED: %s", exc)
        write_json(out_dir / "lists_failed.json", {"utc": utc_iso(), "reason": str(exc),
                                                   "note": "The run stopped before it was complete. Nothing in this directory is a "
                                                           "validation sample to be rated. Repeating the run is a protocol decision."})
        finish_with_manifest(out_dir)
        return 3


def _lists_run(args: argparse.Namespace, cat: Catalogue, client: EutilsClient, out_dir: Path, start) -> int:
    list_specs = build_list_specs(cat)
    year = int(cat.amendment_lists["year"])
    lists_dir = out_dir / "pmid_lists"
    lists_dir.mkdir(parents=True, exist_ok=True)

    # ---- families L and LV: PMID lists --------------------------------------------------------
    lists: dict[str, list[int]] = {}
    list_meta: dict[str, dict] = {}
    for ls in list_specs:
        spec, key = ls.spec, ls.key   # B_AI, S_AI, R_AI, ..., DB_STROKE, ERCT_STROKE, SAI_STROKE, SNONAI_STROKE
        log.info("list %s (family %s): %s", key, ls.list_family, spec.term)
        pmids, head, notes = _read_list(client, ls)
        lists[key] = pmids
        (lists_dir / f"pmids_{key}_{spec.year}.txt").write_text("\n".join(str(p) for p in pmids) + "\n", encoding="utf-8")
        list_meta[key] = {"query_id": spec.query_id, "list_family": ls.list_family, "query": spec.term, "count": head.count,
                          "retrieved": len(pmids), "querytranslation": head.querytranslation, "utc": head.utc,
                          "http_status": head.http_status, "attempt": head.attempt, "notes": notes}
        for n in notes:
            log.warning("list %s: %s", key, n)
        log.info("list %s: count %s, %d identifiers", key, head.count, len(pmids))
    write_json(lists_dir / "lists_meta.json", {
        "utc_start": utc_iso(start), "year": year, "pipeline_version": __version__, "git": git_metadata(PACKAGE_ROOT),
        "source_sha256": source_fingerprint(PACKAGE_DIR), "catalogue_sha256": sha256_text(cat.text),
        "gbd_panel_sha256": cat.gbd_sha256(), "lists": list_meta})

    # ---- PMID-level consistency of the split lists (information only, never corrected) ---------
    partition_cfg = cat.amendment_lists.get("partitions", [])
    partitions = _partition_report(lists, partition_cfg)
    write_json(lists_dir / "partition_report.json", partitions)
    for part in partitions["partitions"]:
        log.info("partition %s = %s: whole %d, union of parts %d, only in whole %d, only in parts %d, in more than one part %d%s",
                 part["whole"], " + ".join(part["parts"]), part["whole_size"], part["union_size"], len(part["only_in_whole"]),
                 len(part["only_in_parts"]), len(part["in_more_than_one_part"]),
                 "" if part["consistent"] else " (difference reported; lists are retrieved one after another from a live database)")

    # ---- validation sampling (Q13; Amendment v3.0, Section 6.1) -------------------------------
    samples = draw_cells(lists, cat.amendment_sampling)
    cell_cfg = {c["cell"]: c for c in cat.amendment_sampling["cells"]}
    sample_dir = out_dir / "samples"
    write_cell_csvs(samples, sample_dir)      # the draw as made; written again below once replacements (Q14) are known
    for s in samples:
        log.info("cell %s: population %d, pilot %d, formal %d, reserve %d, rule %s%s",
                 s.cell, s.population_size, len(s.pilot), len(s.formal), len(s.reserve), s.rule,
                 ("; " + "; ".join(s.notes)) if s.notes else "")

    complete_keys = [ls.key for ls in list_specs if ls.efetch == "all"]
    if args.no_efetch:
        write_json(sample_dir / "sampling_report.json", _sampling_report(samples, {}, {}, xml_checked=False))
        snapshot(cat.path, cat.text, out_dir / "catalogue_snapshot.yaml")
        log.info("lists mode finished without efetch (--no-efetch): the samples are the draw as made, not checked against the XML")
        finish_with_manifest(out_dir)
        return 0

    # ---- family O: efetch XML --------------------------------------------------------------
    xml_dir = out_dir / "xml"
    fetched: dict[str, dict] = {}
    have: dict[str, set[int]] = {}             # PMIDs whose XML is on disk, per directory key
    list_missing: dict[str, list[int]] = {}
    for key in complete_keys:
        # every PMID of the complete RCT-tagged lists (S8 and the V-cells)
        fetched[key] = _efetch_to_dir(client, lists[key], xml_dir / key, f"O__{key}")
        have[key] = set(lists[key]) - set(fetched[key]["missing"])
        list_missing[key] = fetched[key]["missing"]
    # A record of a split list that is not in the XML of its complete list (it entered the database
    # between the two list requests, or efetch did not return it) is fetched under the split list.
    for part in partition_cfg:
        if part["whole"] not in have:
            continue
        for sub in part["parts"]:
            extra = [p for p in lists[sub] if p not in have[part["whole"]]]
            if extra:
                info = _efetch_to_dir(client, extra, xml_dir / sub, f"O__{sub}")
                fetched[sub] = {**info, "note": f"records of {sub} that are not in the XML of {part['whole']}"}
                have[sub] = set(extra) - set(info["missing"])

    cell_missing: dict[str, list[int]] = {}
    for s in samples:
        key, cfg = s.cell, cell_cfg[s.cell]
        xml_from = cfg.get("xml_from")
        available: set[int] = set()
        if xml_from:
            # V-cells are subsets of a complete family B list, whose XML is already on disk.
            available |= have.get(xml_from, set()) | have.get(cfg["list"], set())
        info: dict[str, Any] = {"batches": 0, "methods": [], "attempts": 0}
        if xml_from:
            info["xml_source"] = f"xml/{xml_from}" + (f" and xml/{cfg['list']}" if cfg["list"] in have and cfg["list"] != xml_from else "")
        directly: list[int] = []
        need = [p for p in s.requested if p not in available]
        rounds = 0
        while need:
            got = _efetch_to_dir(client, need, xml_dir / key, f"O__{key}" + (f"__replacement{rounds}" if rounds else ""), start_index=info["batches"])
            directly += need
            info["batches"] += got["batches"]
            info["methods"] = sorted(set(info["methods"]) | set(got["methods"]))
            info["attempts"] = max(info["attempts"], got["attempts"])
            available |= set(need) - set(got["missing"])
            if not got["missing"]:
                break
            # Q14: a PMID whose XML cannot be retrieved after six attempts is replaced by the next PMID of the
            # seeded sequence (sampled cells); a census cell has no replacement queue and records it as missing.
            added = replace_missing(s, got["missing"])
            rounds += 1
            need = [p for p in added if p not in available]
            if rounds > 200:
                raise ListsFailure(f"cell {key}: more than 200 rounds of replacement; the run is stopped")
        final = s.requested
        missing = sorted(p for p in final if p not in available)
        info.update({"requested": len(final), "returned": len(final) - len(missing), "missing": missing})
        if xml_from and directly:
            info["fetched_directly"] = directly
        fetched[key] = info
        cell_missing[key] = missing
    write_cell_csvs(samples, sample_dir)       # final sets: replacements are in, replaced PMIDs are out
    write_json(sample_dir / "sampling_report.json", _sampling_report(samples, cell_missing, list_missing, xml_checked=True))
    write_json(xml_dir / "efetch_report.json", fetched)

    # ---- 12.8 identifiers from the complete RCT-tagged lists -------------------------------
    ids_dir = out_dir / "identifiers"
    extractor = IdentifierExtractor(cat.identifiers["regex"], cat.identifiers["trial_registry_databanks"])
    field_of = {ls.key: ls.spec.field for ls in list_specs}
    id_rows: list[tuple[str, Any]] = []
    summaries: dict[str, dict] = {}
    records_of: dict[str, dict[int, Any]] = {}
    for key in complete_keys:
        fld, members = field_of[key], set(lists[key])
        records_of[key] = {p: rec for p, rec in _parse_dir(xml_dir / key).items() if p in members}
        ids = extractor.extract(records_of[key].values())
        id_rows += [(fld, i) for i in ids]          # a record of both lists is written once per field
        summaries[fld] = summarize(fld, lists[key], ids)
    # Amendment v3.0, S8 within STROKE: the same identifiers, split by the family LV lists
    subsets: dict[str, dict] = {}
    for part in partition_cfg:
        if part["whole"] not in records_of:
            continue
        for sub in part["parts"]:
            members = set(lists[sub])
            records = {p: rec for p, rec in records_of[part["whole"]].items() if p in members}
            records.update({p: rec for p, rec in _parse_dir(xml_dir / sub).items() if p in members})
            subsets[sub] = summarize(sub, members, extractor.extract(records.values()))
    _write_identifier_rows(ids_dir / f"identifiers_{year}.csv", id_rows)
    write_json(ids_dir / "identifiers_summary.json", {**summaries, "subsets": subsets})
    for fld, summ in {**summaries, **subsets}.items():
        log.info("identifiers %s: %d records, %d with identifier, %d distinct identifiers", fld, summ["records"],
                 summ["records_with_identifier"], summ["distinct_identifiers"])

    snapshot(cat.path, cat.text, out_dir / "catalogue_snapshot.yaml")
    n_missing = sum(len(v) for v in cell_missing.values())
    if n_missing or any(list_missing.values()):
        log.warning("lists mode finished: XML missing after six attempts for %d record(s) of the cells and %d record(s) of the "
                    "complete lists; see sampling_report.json (Q14: reported)", n_missing, sum(len(v) for v in list_missing.values()))
    else:
        log.info("lists mode finished")
    finish_with_manifest(out_dir)
    return 0


def _write_identifier_rows(path: Path, rows: list[tuple[str, Any]]) -> None:
    """identifiers_<year>.csv: one row per (field, record, identifier, source). A record that is in
    the complete lists of two fields has its rows under each of them."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["field", "pmid", "registry", "identifier", "source", "raw"])
        for fld, i in sorted(rows, key=lambda x: (x[0], x[1].pmid, x[1].registry, x[1].identifier, x[1].source)):
            w.writerow([fld, i.pmid, i.registry, i.identifier, i.source, i.raw])


def _partition_report(lists: dict[str, list[int]], partitions: list[dict]) -> dict:
    """Compare each complete list with the union of its split lists at the PMID level."""
    out = []
    for part in partitions:
        whole = set(lists[part["whole"]])
        parts = [set(lists[k]) for k in part["parts"]]
        union = set().union(*parts) if parts else set()
        seen: set[int] = set()
        multiple: set[int] = set()
        for ps in parts:
            multiple |= seen & ps
            seen |= ps
        only_whole, only_parts = sorted(whole - union), sorted(union - whole)
        out.append({
            "whole": part["whole"], "parts": list(part["parts"]), "whole_size": len(whole),
            "part_sizes": {k: len(set(lists[k])) for k in part["parts"]}, "union_size": len(union),
            "only_in_whole": only_whole, "only_in_parts": only_parts, "in_more_than_one_part": sorted(multiple),
            "consistent": not only_whole and not only_parts and not multiple,
        })
    return {"note": "PMID-level comparison of a complete list with the union of its split lists (families L and LV). "
                    "The lists are retrieved one after another from a live database; a difference is reported, never corrected.",
            "partitions": out}


def _returned_by(batch) -> set[int]:
    """PMIDs of the requested records that one efetch response holds. A response that is not
    HTTP 200 or not well-formed XML holds none: its records are requested again."""
    if batch.http_status != 200:
        return set()
    try:
        return returned_pmids(batch.xml) & set(batch.pmids)
    except ET.ParseError:
        return set()


def _efetch_to_dir(client: EutilsClient, pmids: list[int], target: Path, label: str, start_index: int = 0) -> dict:
    """efetch XML for ``pmids`` into ``target``.

    Q14: a PMID counts as unretrievable only after six attempts. A record that a response does not
    hold (the response may be empty, truncated or an error page with HTTP 200) is therefore
    requested again with the registered waiting times, up to six attempts in total. If, after
    that, more than a handful of records of one call are still missing, the cause is the service,
    not the records: the run stops instead of drawing replacements for all of them."""
    wanted = list(dict.fromkeys(int(p) for p in pmids))
    got: set[int] = set()
    saved, attempts, methods = 0, 0, set()
    pending = list(wanted)
    while pending and attempts < client.max_attempts:
        attempts += 1
        batches = client.efetch_xml(pending, label if attempts == 1 else f"{label}__attempt{attempts}")
        for b in batches:
            methods.add(b.method)
            returned = _returned_by(b)
            if returned:
                saved += 1
                target.mkdir(parents=True, exist_ok=True)
                (target / f"batch_{start_index + saved:04d}.xml").write_text(b.xml, encoding="utf-8")
                got |= returned
        pending = [p for p in pending if p not in got]
        if pending and attempts < client.max_attempts:
            wait = client.backoff[min(attempts - 1, len(client.backoff) - 1)]
            log.warning("%s: %d of %d records not returned (attempt %d of %d); requested again in %.0f s: %s",
                        label, len(pending), len(wanted), attempts, client.max_attempts, wait, pending[:20])
            client._sleep(wait)
    missing = sorted(pending)
    if len(missing) > max(MASS_FAILURE_MIN, MASS_FAILURE_SHARE * len(wanted)):
        raise ListsFailure(f"{label}: {len(missing)} of {len(wanted)} records were not returned by efetch after {attempts} attempts. "
                           "This is a failure of the service or the connection, not of single records; no replacement is drawn.")
    if missing:
        log.warning("%s: %d PMIDs not returned by efetch after %d attempts (Q14): %s", label, len(missing), attempts, missing[:20])
    return {"requested": len(wanted), "returned": len(got), "missing": missing, "batches": saved, "methods": sorted(methods),
            "attempts": attempts}


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


def _sampling_report(samples: list[CellSample], cell_missing: dict[str, list[int]], list_missing: dict[str, list[int]],
                     xml_checked: bool) -> dict:
    return {
        "seed": 20260904,
        "rule": "random.Random(20260904).sample on the ascending PMID list; pilot 20 drawn first (Q13); "
                "a cell with 200 records or fewer is rated completely (census, no pilot, no replacement queue); "
                "a PMID whose XML cannot be retrieved after six attempts is replaced by the next PMID of the seeded "
                "sequence (Q14); cells of Amendment v3.0, Section 6.1; see sampling.py docstring, decision I1",
        "xml_checked": xml_checked,
        "cells": [{**s.as_dict(), "missing_after_replacement": cell_missing.get(s.cell, [])} for s in samples],
        "census_lists_missing": {k: v for k, v in list_missing.items()},
    }


def _print_check(title: str, report: CheckReport) -> int:
    """Print one identity report and return its exit code (0 strict, 1 whitespace only, 2 differences)."""
    print(f"{title}: {report.summary()}")
    strict_fail = report.failures(strict=True)
    lenient_fail = report.failures(strict=False)
    if lenient_fail:
        print("\nNOT FOUND even ignoring whitespace (character difference, must be resolved):")
        for item in lenient_fail:
            print(f"  [{item.kind}] {item.name}: {item.text}")
    elif strict_fail:
        print("\nFound only after removing whitespace (line wraps in the source text; verify against the Markdown file):")
        for item in strict_fail:
            print(f"  [{item.kind}] {item.name}" + (f": {item.text}" if item.kind == "gbd_panel_block" else ""))
    if report.strict_ok:
        return 0
    return 1 if report.lenient_ok else 2


def mode_check_catalogue(args: argparse.Namespace, cat: Catalogue) -> int:
    """String identity of the catalogue: registered part against the registration text (93 checks,
    unchanged from tag v1.0), addendum against Amendment v3.0 (templates, worked examples, GBD panel)."""
    prereg_path = Path(args.prereg) if args.prereg else PACKAGE_ROOT / cat.registration["document"]
    amendment_path = Path(args.amendment) if args.amendment else PACKAGE_ROOT / cat.amendment["document"]

    git = git_metadata(PACKAGE_ROOT)
    print(f"Pipeline version {__version__}; git commit {git['commit']}{' (uncommitted changes)' if git['dirty'] else ''}; "
          f"source SHA-256 {source_fingerprint(PACKAGE_DIR)}")
    print(f"Catalogue SHA-256 {sha256_text(cat.text)}; GBD panel SHA-256 {cat.gbd_sha256()} (status {cat.gbd_status})\n")
    report_reg = check_against_preregistration(cat, load_prereg_text(prereg_path))
    rc_reg = _print_check(f"Registration v2.0 ({prereg_path.name})", report_reg)

    report_am: CheckReport | None = None
    print()
    if not amendment_path.is_file():
        print(f"Amendment v3.0: file not found: {amendment_path}")
        print("  The addendum of the catalogue cannot be confirmed without the amendment text. Copy the amendment as "
              "submitted with the OSF update to that path, or name it with --amendment.")
        rc_am = 2
    else:
        report_am = check_against_amendment(cat, load_prereg_text(amendment_path), allow_test_fixture=False)
        rc_am = _print_check(f"Amendment v3.0 ({amendment_path.name})", report_am)
        if not cat.gbd_is_final:
            print(f"\n  The GBD panel file {cat.gbd_path} has status '{cat.gbd_status}'. A release needs the final panel "
                  "(scripts/gbd_panel.py) and an amendment text that lists it (Section 5).")

    rc = max(rc_reg, rc_am)
    if args.json:
        items = [{"source": "registration", **asdict(i)} for i in report_reg.items]
        items += [{"source": "amendment", **asdict(i)} for i in (report_am.items if report_am else [])]
        write_json(args.json, {
            "summary": f"registration: {report_reg.summary()}; amendment: {report_am.summary() if report_am else 'not checked'}",
            "strict_ok": rc == 0,
            "lenient_ok": rc <= 1,
            "exit_code": rc,
            "registration": {"path": str(prereg_path), "summary": report_reg.summary(), "strict_ok": report_reg.strict_ok,
                             "lenient_ok": report_reg.lenient_ok},
            "amendment": {"path": str(amendment_path), "checked": report_am is not None,
                          "summary": report_am.summary() if report_am else None,
                          "strict_ok": report_am.strict_ok if report_am else False,
                          "lenient_ok": report_am.lenient_ok if report_am else False},
            "pipeline_version": __version__,
            "git": git_metadata(PACKAGE_ROOT),
            "source_sha256": source_fingerprint(PACKAGE_DIR),
            "catalogue_sha256": sha256_text(cat.text),
            "gbd_panel_sha256": cat.gbd_sha256(),
            "gbd_panel_status": cat.gbd_status,
            "items": items,
        })
    if rc == 0:
        print("\nRESULT: strict string identity confirmed for every catalogue component (registration v2.0 and Amendment v3.0).")
    elif rc == 1:
        print("\nRESULT: identity confirmed up to whitespace only; run the check against the Markdown files for the strict result.")
    else:
        print("\nRESULT: character differences found or a source text is missing; the release must not be tagged.")
    return rc


# ---------------------------------------------------------------------------------------------
# Amendment syntax check (publication year 2015 only)
# ---------------------------------------------------------------------------------------------

def translation_pattern_notes(term: str, translation: str, year: int) -> list[str]:
    """Compare PubMed's query translation with the form recorded in Q18. Checked, and nothing more:

    * the number of terms per field tag: every [Mesh] as [MeSH Terms] ([Mesh:NoExp] as
      [MeSH Terms:noexp]), [pt] as [Publication Type], [tiab] as [Title/Abstract], [ti] as [Title],
      medline[sb] as the MEDLINE filter;
    * every MeSH heading of the query stands in the translation under its own name (PubMed maps
      another name of a descriptor, an entry term, to the descriptor: the translation then shows a
      different heading, which is reported);
    * the number of NOT operators is unchanged;
    * the year clause became the publication-date range of that year, once.
    The grouping of the Boolean operators is not parsed. Returns one note per departure."""
    t = (translation or "").lower()
    notes: list[str] = []
    expected = [
        ("[MeSH Terms]", term.count("[Mesh]"), t.count("[mesh terms]")),
        ("[MeSH Terms:noexp]", term.count("[Mesh:NoExp]"), t.count("[mesh terms:noexp]")),
        ("[Publication Type]", term.count("[pt]"), t.count("[publication type]")),
        ("[Title/Abstract]", term.count("[tiab]"), t.count("[title/abstract]")),
        ("[Title]", term.count("[ti]"), t.count("[title]")),
    ]
    for label, want, got in expected:
        if want != got:
            notes.append(f"{label}: {want} expected from the query, {got} in the translation")
    for heading in dict.fromkeys(mesh_headings(term)):
        if f'"{heading.lower()}"[mesh terms' not in t:
            notes.append(f'the heading "{heading}" does not stand in the translation under this name')
    if term.count(" NOT ") != (translation or "").count(" NOT "):
        notes.append(f"NOT operators: {term.count(' NOT ')} in the query, {(translation or '').count(' NOT ')} in the translation")
    n_sb = term.count("medline[sb]")
    n_filter = sum(t.count(x) for x in ('medline"[filter]', "medline[filter]", 'medline"[sb]', "medline[sb]", 'medline"[subset]', "medline[subset]"))
    if n_sb != n_filter:
        notes.append(f"medline[sb]: {n_sb} expected from the query, {n_filter} MEDLINE filter terms in the translation")
    date_range = f"{year}/01/01:{year}/12/31[date - publication]"
    if t.count(date_range) != 1:
        notes.append(f"publication-date range {year}/01/01:{year}/12/31[Date - Publication] not found exactly once")
    return notes


def _count_notes(cat: Catalogue, item: SyntaxCheckItem, count: int | None, zero_no_items: bool) -> tuple[list[str], list[str]]:
    """Notes on a returned count: (notes that need a human look, notes that are information only).

    A GBD descriptor recorded as introduced in or before 2015 must have records in 2015; a count of
    zero then points to a wrong heading and is flagged. For a descriptor introduced after 2015 a
    zero is the expected result (as for "Deep Learning"[Mesh] in Q18), and records in 2015 are
    retrospective indexing, which the panel rule of Q13 handles. A zero in one of the small
    Diabetes Mellitus compositions is a result, not an error, and is stated as such."""
    review: list[str] = []
    info: list[str] = []
    if count is None:
        return review, info
    if item.group == "gbd_descriptor":
        member = cat.gbd_member(item.field)
        if count == 0 and member.in_trajectory:
            review.append(f"no record in {cat.amendment_syntax_check['year']} although the descriptor is recorded as introduced in or "
                          "before 2015; check the heading in the MeSH Browser")
        elif count == 0:
            info.append("no record in 2015, the expected result for a descriptor introduced after 2015 (panel rule of Q13)")
        elif not member.in_trajectory:
            info.append("records in 2015 although the descriptor was introduced after 2015 (retrospective indexing; the panel rule "
                        "of Q13 applies: 2024 and pooled windows only)")
    elif count == 0 and zero_no_items:
        info.append("count 0 with the PubMed message 'No items found'; a result, not a syntax error")
    return review, info


def _evaluate_identities(identities: list[dict], counts: dict[str, int | None]) -> list[dict]:
    def total(terms: list[str]) -> int | None:
        acc = 0
        for term in terms:
            sign, key = (-1, term[1:]) if str(term).startswith("-") else (1, str(term))
            if counts.get(key) is None:
                return None
            acc += sign * int(counts[key])
        return acc

    out = []
    for ident in identities:
        left, right = total(list(ident["left"])), total(list(ident["right"]))
        if left is None or right is None:
            status = "not evaluated (a count is missing)"
        elif ident["type"] == "equal":
            status = "met" if left == right else "NOT MET"
        else:
            status = "met" if left <= right else "NOT MET"
        out.append({"name": ident["name"], "type": ident["type"], "left": list(ident["left"]), "right": list(ident["right"]),
                    "left_value": left, "right_value": right, "status": status})
    return out


def _q18_addendum_markdown(cat: Catalogue, results: list[dict], identities: list[dict], start_utc: str, end_utc: str) -> str:
    """The verbatim record of the syntax check, written so that it can be pasted into Section 8.10
    (Q18 addendum) of Amendment v3.0. It states what was sent and what came back, nothing else."""
    git = git_metadata(PACKAGE_ROOT)
    year = int(cat.amendment_syntax_check["year"])
    n = {g: sum(1 for r in results if r["group"] == g) for g in ("anchor", "composition", "gbd_descriptor")}
    lines = [
        "### Q18 addendum: syntax check of the new expressions of Amendment v3.0",
        "",
        f"Run from {start_utc} to {end_utc} with `python -m airct_benchmark syntax-check --send` (pipeline version {__version__}, "
        f"git commit {git['commit']}, git describe {git['describe']}{', with uncommitted changes' if git['dirty'] else ''}; "
        f"source SHA-256 {source_fingerprint(PACKAGE_DIR)}; "
        f"catalogue SHA-256 {sha256_text(cat.text)}, GBD panel SHA-256 {cat.gbd_sha256()}), "
        f"under the rule of Q8 and Q18: esearch with "
        f"`retmax=0`, publication year {year} only, {len(results)} requests in total. {n['anchor']} requests re-read registered "
        f"smoke cells of Diabetes Mellitus {year} that were disclosed in Q18 of v2.0 (reference values in the table); "
        f"{n['composition']} requests checked the new compositions of Section 4, each run with Diabetes Mellitus in place of "
        f"Stroke, so that no Stroke count was viewed; {n['gbd_descriptor']} requests checked the GBD descriptors that are new "
        f"relative to v2.0 (family GA, human-subject denominator). No request contained the Stroke descriptor or a publication "
        f"year other than {year}. The log, the raw responses and a SHA-256 manifest are deposited with this update.",
        "",
        "| # | Group | Check | Query (verbatim) | Count | Q18 reference | HTTP | Attempt |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(results, 1):
        count = "" if r["count"] is None else f"{r['count']:,}"
        ref = "" if r["reference_count"] is None else f"{r['reference_count']:,}"
        http = "" if r["http_status"] is None else str(r["http_status"])
        lines.append(f"| {i} | {r['group']} | {r['check_id']} | `{r['term']}` | {count} | {ref} | {http} | {r['attempt']} |")
    lines += ["", "Identities and bounds evaluated on these counts:", ""]
    for ident in identities:
        lines.append(f"- {ident['name']}: {' + '.join(ident['left'])} = {ident['left_value']}; "
                     f"{' + '.join(ident['right'])} = {ident['right_value']}; "
                     f"{'equality' if ident['type'] == 'equal' else 'left side at most right side'}: {ident['status']}.")
    issues = [r for r in results if r["pubmed_messages"] or r["pattern_notes"] or r["error"] or r["review_notes"] or r["info_notes"]]
    lines += ["", "PubMed messages and query-translation pattern:", ""]
    flagged = [r for r in results if r["error"] or r["pattern_notes"] or r["review_notes"]
               or (r["pubmed_messages"] and not r["valid_zero_no_items_found"])]
    if not flagged:
        lines.append("- No request failed and PubMed reported no error-list entry. In every query translation that was compared "
                     "(requests with a count of zero and the message 'No items found' are not compared), the terms carried the "
                     "field tags recorded in Q18 (MeSH descriptors as [MeSH Terms] or [MeSH Terms:noexp], publication types as "
                     "[Publication Type], text words as [Title/Abstract] or [Title], medline[sb] as the MEDLINE filter), every "
                     "MeSH heading stood under its own name, the number of NOT operators was unchanged, and the year clause "
                     "was the publication-date range of the year. The grouping of the operators was not parsed by the script; "
                     "the translations are deposited verbatim.")
    for r in issues:
        parts = []
        if r["error"]:
            parts.append(f"request failed: {r['error']}")
        if r["pubmed_messages"]:
            parts.append(f"PubMed messages: {json.dumps(r['pubmed_messages'], ensure_ascii=False)}")
        if r["pattern_notes"]:
            parts.append("translation pattern: " + "; ".join(r["pattern_notes"]) + f"; translation as returned: `{r['querytranslation']}`")
        parts += r["review_notes"] + r["info_notes"]
        lines.append(f"- {r['check_id']}: " + "; ".join(parts) + ".")
    lines.append("")
    return "\n".join(lines)


def mode_syntax_check(args: argparse.Namespace, cat: Catalogue, session=None) -> int:
    """Amendment v3.0, Sections 1.4 and 8.3: one request per new expression, publication year 2015 only."""
    try:
        plan: list[SyntaxCheckItem] = build_syntax_check_plan(cat)
    except CatalogueError as exc:
        raise SystemExit(f"syntax check refused: {exc}") from exc
    year = int(cat.amendment_syntax_check["year"])

    if args.dry_run or not args.send:
        print(f"Syntax check plan: {len(plan)} requests, publication year {year} only." + (" Nothing is sent in a dry run." if args.dry_run else ""))
        if not cat.gbd_is_final:
            print(f"NOTE: the GBD panel file has status '{cat.gbd_status}'; the descriptor requests below are not final.")
        for i, it in enumerate(plan, 1):
            print(f"{i:>3}  {it.group:<15} {it.check_id:<46} {it.term}")
        if not args.dry_run:
            # Forgetting an option must never send anything: the check views counts and is run once.
            print("\nNothing was sent: without --send this command prints the plan only. The syntax check views counts, is run once "
                  "from the committed state and is disclosed in the Q18 addendum (Amendment v3.0, Section 1.4). To run it, give the "
                  "same command with --send.")
        return 0

    require_final_gbd_panel(cat, "the syntax check", session)
    for it in plan:      # the whole plan is checked before the output directory is created and before anything is sent
        violation = syntax_check_violation(cat, it.term)
        if violation:
            raise SystemExit(f"syntax check refused: request {it.check_id} {violation} (rule of Q8 and Q18)")
    # Every run of this mode views counts, and every run is disclosed. A second run needs a stated reason.
    earlier = sorted(p.name for p in Path(args.out).glob("syntax_check_*") if p.is_dir())
    if earlier and not (args.repeat or "").strip():
        raise SystemExit(f"Refusing to run the syntax check again: {Path(args.out)} already holds {earlier}. Every run views counts "
                         "and has to be disclosed in the Q18 addendum. If the check must be repeated, give the reason: "
                         "--repeat \"<reason>\"; it is written into the addendum of the new run.")
    start = utc_now()
    out_dir = Path(args.out) / f"syntax_check_{utc_compact_seconds(start)}"
    api_key = env_api_key(cat.api_key_env())
    setup_logging(out_dir, Redactor([api_key] if api_key else []), args.verbose)
    log.info("amendment syntax check: %d requests, publication year %d only (rule of Q8 and Q18)", len(plan), year)
    client = make_client(cat, out_dir / "raw", session=session)
    results: list[dict] = []
    failed = 0
    for it in plan:
        # Hard rule, checked again immediately before sending: publication year 2015 only, no Stroke heading.
        violation = syntax_check_violation(cat, it.term)
        if violation:
            raise SystemExit(f"syntax check refused: request {it.check_id} {violation} (rule of Q8 and Q18)")
        res = client.esearch_count(it.term, f"syntax__{safe_filename(it.check_id)}")
        messages = {}
        if any(res.errorlist.values()):
            messages["errorlist"] = res.errorlist
        if any(res.warninglist.values()):
            messages["warninglist"] = res.warninglist
        no_items_only = (set(messages) == {"warninglist"}
                         and not any(v for k, v in res.warninglist.items() if k != "outputmessages")
                         and all("no items found" in str(m).lower() for m in res.warninglist.get("outputmessages", [])))
        zero_no_items = bool(res.ok and res.count == 0 and no_items_only)
        notes = translation_pattern_notes(it.term, res.querytranslation, year) if res.ok and not zero_no_items else []
        review_notes, info_notes = _count_notes(cat, it, res.count if res.ok else None, zero_no_items)
        if not res.ok:
            failed += 1
            log.error("%s FAILED: %s", it.check_id, res.error)
        else:
            log.info("%s: count=%s http=%s attempt=%s", it.check_id, res.count, res.http_status, res.attempt)
        results.append({**it.as_dict(), "count": res.count, "querytranslation": res.querytranslation, "utc": res.utc,
                        "http_status": res.http_status, "attempt": res.attempt, "error": res.error,
                        "pubmed_messages": messages, "valid_zero_no_items_found": zero_no_items,
                        "pattern_notes": notes, "review_notes": review_notes, "info_notes": info_notes, "raw_path": res.raw_path})
    end = utc_now()

    counts = {r["check_id"]: r["count"] for r in results}
    identities = _evaluate_identities(cat.amendment_syntax_check.get("identities", []), counts)
    review = [r["check_id"] for r in results
              if r["error"] or r["pattern_notes"] or r["review_notes"] or (r["pubmed_messages"] and not r["valid_zero_no_items_found"])]
    not_met = [i["name"] for i in identities if i["status"] != "met"]
    for ident in identities:
        (log.info if ident["status"] == "met" else log.warning)("identity %s: left %s, right %s: %s", ident["name"],
                                                                 ident["left_value"], ident["right_value"], ident["status"])
    for r in results:
        if r["reference_count"] is not None and r["count"] is not None and r["count"] != r["reference_count"]:
            log.info("%s: count %s differs from the Q18 reference %s by %+d (live database; logged, not a failure)",
                     r["check_id"], r["count"], r["reference_count"], r["count"] - r["reference_count"])

    stamp = utc_compact_seconds(start)
    write_json(out_dir / f"syntax_check_{stamp}.json", {
        "mode": "syntax-check", "rule": "Amendment v3.0, Sections 1.4 and 8.3; registration Q8 and Q18: publication year 2015 only",
        "utc_start": utc_iso(start), "utc_end": utc_iso(end), "pipeline_version": __version__, "git": git_metadata(PACKAGE_ROOT),
        "source_sha256": source_fingerprint(PACKAGE_DIR),
        "catalogue_sha256": sha256_text(cat.text), "gbd_panel_sha256": cat.gbd_sha256(), "requests_sent": client.request_count,
        "earlier_runs_in_the_output_directory": earlier, "reason_for_repetition": (args.repeat or "").strip() if earlier else "",
        "results": results, "identities": identities, "needs_review": review, "identities_not_met": not_met,
    })
    with open(out_dir / f"syntax_check_{stamp}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["group", "check_id", "query", "querytranslation", "count", "reference_count", "utc", "http_status", "attempt"])
        for r in results:
            w.writerow([r["group"], r["check_id"], r["term"], r["querytranslation"], "" if r["count"] is None else r["count"],
                        "" if r["reference_count"] is None else r["reference_count"], r["utc"],
                        "" if r["http_status"] is None else r["http_status"], r["attempt"]])
    md_path = out_dir / f"q18_addendum_{stamp}.md"
    addendum = _q18_addendum_markdown(cat, results, identities, utc_iso(start), utc_iso(end))
    if earlier:
        addendum += (f"\nRepeated run. Earlier runs of the syntax check on this computer: {', '.join(earlier)}; their records are "
                     f"deposited as well. Reason for the repetition, as stated by the person who ran it: {args.repeat.strip()}\n")
        log.warning("repeated syntax check; earlier runs: %s; stated reason: %s", earlier, args.repeat.strip())
    md_path.write_text(addendum, encoding="utf-8")
    snapshot(cat.path, cat.text, out_dir / "catalogue_snapshot.yaml")
    snapshot(cat.gbd_path, cat.gbd_text, out_dir / "gbd_panel_snapshot.yaml")

    if failed:
        log.error("syntax check finished: %d of %d requests FAILED; repeat the check after the cause is known", failed, len(plan))
        rc = 2
    elif review or not_met:
        log.warning("syntax check finished: REVIEW NEEDED before the OSF update (requests: %s; identities: %s)", review, not_met)
        rc = 4
    else:
        log.info("syntax check finished: %d requests, no failed request, no PubMed error or unexpected warning, "
                 "every translation as expected, every identity met", len(plan))
        rc = 0
    log.info("Q18 addendum written to %s", md_path)
    finish_with_manifest(out_dir)
    return rc


def mode_identifiers(args: argparse.Namespace, cat: Catalogue) -> int:
    extractor = IdentifierExtractor(cat.identifiers["regex"], cat.identifiers["trial_registry_databanks"])
    xml_dir = Path(args.xml_dir)
    if not xml_dir.is_dir():
        raise SystemExit(f"identifiers: directory not found: {xml_dir}")
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
    records: dict[int, Any] = {}
    for d in ([args.xml_dir] if isinstance(args.xml_dir, str) else args.xml_dir):
        if not Path(d).is_dir():
            raise SystemExit(f"ratingsheet: directory not found: {d}")
        records.update(_parse_dir(Path(d)))
    wanted = None
    if args.pmids:
        wanted = [int(line.split(",")[-1]) if "," in line else int(line) for line in Path(args.pmids).read_text(encoding="utf-8-sig").splitlines()
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
    p.add_argument("--gbd-panel", default=None, help="path to the GBD panel file (default: config/gbd_panel.yaml next to the catalogue)")
    p.add_argument("--verbose", action="store_true")
    sub = p.add_subparsers(dest="mode", required=True)

    s = sub.add_parser("smoke", help="one cell: Diabetes Mellitus 2015 (family A by default)")
    s.add_argument("--out", default="out", help="output directory")
    s.add_argument("--family", default=None, help="family letter within Diabetes Mellitus 2015 (default A)")
    s.add_argument("--metric", default=None, help="metric within the family (default den)")

    # No abbreviated options here: --s or --se must not be read as --send.
    y = sub.add_parser("syntax-check", allow_abbrev=False,
                       help="Amendment v3.0: new expressions, publication year 2015 only; with --send writes the Q18 addendum")
    y.add_argument("--out", default="out", help="output directory")
    y.add_argument("--dry-run", action="store_true", help="print the requests without sending anything")
    y.add_argument("--send", action="store_true",
                   help="send the requests; the check views counts and is run once. Without this option the plan is printed and nothing is sent")
    y.add_argument("--repeat", default=None, metavar="REASON",
                   help="run again although the output directory holds an earlier syntax check; the reason is disclosed")

    f = sub.add_parser("freeze", help="complete catalogue, Run A then Run B")
    f.add_argument("--out", default="out")
    f.add_argument("--override-freeze-guard", action="store_true", help="run before the registered freeze date (logged)")
    f.add_argument("--single-run", action="store_true", help="Run A only (testing and reproduction tooling)")
    f.add_argument("--families", nargs="*", default=None, help="restrict to family codes (testing only)")

    l = sub.add_parser("lists", help="family L and LV PMID lists, validation sampling, family O efetch XML, 12.8 identifiers")
    l.add_argument("--out", default="out")
    l.add_argument("--override-freeze-guard", action="store_true")
    l.add_argument("--no-efetch", action="store_true", help="lists and sampling only")

    c = sub.add_parser("check-catalogue", help="string identity against the registration text and Amendment v3.0 (offline)")
    c.add_argument("--prereg", default=None, help="registration text (default: Preregistration_v2.0_FINAL_2026-09-04.md in the repository)")
    c.add_argument("--amendment", default=None, help="amendment text (default: docs/AMENDMENT_v3_0.md in the repository)")
    c.add_argument("--json", default=None, help="write the full report as JSON")

    i = sub.add_parser("identifiers", help="registration identifiers from saved efetch XML (offline)")
    i.add_argument("--xml-dir", required=True)
    i.add_argument("--field", required=True, help="field key written into the output (AI or STROKE)")
    i.add_argument("--out", required=True, help="output CSV")

    r = sub.add_parser("ratingsheet", help="rating sheet without MeSH terms and publication types (offline)")
    r.add_argument("--xml-dir", required=True, nargs="+", help="one or more directories with efetch XML")
    r.add_argument("--pmids", default=None, help="optional sample CSV or PMID list restricting the sheet")
    r.add_argument("--out", required=True)

    m = sub.add_parser("manifest", help="write MANIFEST_SHA256.txt for a directory (offline)")
    m.add_argument("--dir", required=True)
    v = sub.add_parser("verify-manifest", help="verify MANIFEST_SHA256.txt of a directory (offline)")
    v.add_argument("--dir", required=True)
    return p


def main(argv: Sequence[str] | None = None, session=None) -> int:
    for stream in (sys.stdout, sys.stderr):      # a console that cannot show a character must not stop a run
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    args = build_parser().parse_args(argv)
    try:
        cat = load_catalogue(args.catalogue, args.gbd_panel)
        shared_cells(cat)      # every shared GBD cell must be held by an identical query, in every mode
    except CatalogueError as exc:
        print(f"catalogue refused: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    online = args.mode in ONLINE_MODES and not getattr(args, "dry_run", False)
    if args.mode == "syntax-check" and not args.send:
        online = False                                       # prints the plan only
    if online and cat.gbd_is_test_fixture and session is None:
        # The synthetic panel of the test suite is never sent to PubMed, whatever the mode and its options.
        raise SystemExit(f"Refusing to run {args.mode}: {cat.gbd_path} is the synthetic GBD panel of the test suite and must "
                         "never be sent to PubMed.")
    if args.mode == "smoke":
        return mode_smoke(args, cat, session)
    if args.mode == "syntax-check":
        return mode_syntax_check(args, cat, session)
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
