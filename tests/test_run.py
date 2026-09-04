import csv
import json
from datetime import date
from pathlib import Path

import pytest

from airct_benchmark import run as run_mod
from airct_benchmark.manifest import verify_manifest
from airct_benchmark.queries import build_count_queries, smoke_query
from airct_benchmark.run import CSV_COLUMNS, freeze_guard, main
from airct_benchmark.sampling import seeded_sequence
from conftest import FIXTURES, FakeClock, FakeSession, pubmed_article_xml

SMOKE_TERM = '"Diabetes Mellitus"[Mesh] AND "Humans"[Mesh] AND ("2015"[pdat])'


@pytest.fixture
def fast_client(monkeypatch):
    """Route every client created by run.py through a fake clock so no test sleeps for real."""
    clock = FakeClock()
    original = run_mod.make_client

    def patched(cat, raw_dir, session=None, **overrides):
        overrides.setdefault("clock", clock)
        overrides.setdefault("sleeper", clock.sleep)
        return original(cat, raw_dir, session=session, **overrides)

    monkeypatch.setattr(run_mod, "make_client", patched)
    return clock


def read_counts_csv(path: Path) -> tuple[list[str], list[dict]]:
    header, body = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        (header if line.startswith("#") else body).append(line)
    rows = list(csv.DictReader(body))
    return header, rows


def files_containing(root: Path, needle: str) -> list[Path]:
    hits = []
    for p in root.rglob("*"):
        if p.is_file() and needle in p.read_text(encoding="utf-8", errors="ignore"):
            hits.append(p)
    return hits


# ---- smoke ----------------------------------------------------------------------------------

def test_smoke_reproduces_reference_and_logs_difference(tmp_path, fast_client, api_key_env):
    session = FakeSession(count_overrides={SMOKE_TERM: 18723})
    rc = main(["smoke", "--out", str(tmp_path)], session=session)
    assert rc == 0
    result = json.loads(next(tmp_path.glob("smoke_*.json")).read_text(encoding="utf-8"))
    assert result["query"] == SMOKE_TERM and result["query_id"] == "A_DM_den_2015"
    assert result["count"] == 18723 and result["reference_count"] == 18723 and result["difference"] == 0
    assert result["http_status"] == 200 and result["attempt"] == 1
    # exactly one request went out, with retmax=0 and the mandated tool and email
    assert len(session.calls) == 1
    params = session.calls[0][2]
    assert params["retmax"] == 0 and params["tool"] == "airct_benchmark" and params["email"] == "witold.polanski@ukdd.de"
    assert files_containing(tmp_path, api_key_env) == []


def test_smoke_deviation_is_logged_not_failed(tmp_path, fast_client):
    session = FakeSession(count_overrides={SMOKE_TERM: 18800})
    rc = main(["smoke", "--out", str(tmp_path)], session=session)
    assert rc == 0
    result = json.loads(next(tmp_path.glob("smoke_*.json")).read_text(encoding="utf-8"))
    assert result["difference"] == 77
    log_text = next(tmp_path.glob("run_*.log")).read_text(encoding="utf-8")
    assert "difference +77" in log_text


def test_smoke_other_metric_and_failure_exit_code(tmp_path, fast_client, catalogue):
    b = smoke_query(catalogue, "B", "rct")
    session = FakeSession(count_overrides={b.term: 1405})
    rc = main(["smoke", "--out", str(tmp_path), "--family", "B", "--metric", "rct"], session=session)
    assert rc == 0
    result = json.loads(next(tmp_path.glob("smoke_*.json")).read_text(encoding="utf-8"))
    assert result["reference_count"] == 1405 and result["difference"] == 0
    failing = FakeSession(status_script=[500] * 6)
    rc = main(["smoke", "--out", str(tmp_path / "fail")], session=failing)
    assert rc == 2


def test_smoke_refuses_cells_outside_diabetes_2015(tmp_path, fast_client):
    with pytest.raises(SystemExit):
        main(["smoke", "--out", str(tmp_path), "--family", "R"], session=FakeSession())


# ---- freeze guard ---------------------------------------------------------------------------

def test_freeze_guard_dates(catalogue, caplog):
    with pytest.raises(SystemExit):
        freeze_guard(catalogue, False, today=date(2026, 9, 4))
    with pytest.raises(SystemExit):
        freeze_guard(catalogue, False, today=date(2026, 10, 11))
    freeze_guard(catalogue, False, today=date(2026, 10, 12))   # freeze date itself is allowed
    with caplog.at_level("WARNING", logger="airct_benchmark"):
        freeze_guard(catalogue, True, today=date(2026, 9, 4))
    assert "FREEZE GUARD OVERRIDDEN" in caplog.text


def test_freeze_and_lists_refuse_before_freeze_date_without_override(tmp_path, fast_client):
    if date.today() >= date(2026, 10, 12):
        pytest.skip("freeze date reached; guard no longer applies")
    session = FakeSession()
    with pytest.raises(SystemExit):
        main(["freeze", "--out", str(tmp_path), "--families", "A"], session=session)
    with pytest.raises(SystemExit):
        main(["lists", "--out", str(tmp_path)], session=session)
    assert session.calls == []


# ---- freeze ---------------------------------------------------------------------------------

def test_freeze_writes_run_a_and_run_b_with_header_and_manifest(tmp_path, fast_client, api_key_env, catalogue):
    session = FakeSession()
    rc = main(["freeze", "--out", str(tmp_path), "--override-freeze-guard", "--families", "A", "B"], session=session)
    assert rc == 0
    out = next(tmp_path.glob("freeze_*"))
    stamp = out.name.split("_", 1)[1]
    csv_a, csv_b = out / f"counts_frozen_{stamp}_runA.csv", out / f"counts_frozen_{stamp}_runB.csv"
    assert csv_a.exists() and csv_b.exists()
    assert not list(out.glob("*.partial.csv"))

    header, rows = read_counts_csv(csv_a)
    assert header[0] == "# airct_benchmark frozen count file"
    assert any(h.startswith("# retrieval_start_utc: ") for h in header)
    assert any(h.startswith("# retrieval_end_utc: ") for h in header)
    assert any(h.startswith("# git_commit: ") for h in header)
    assert any(h.startswith("# pipeline_version: ") for h in header)
    assert any(h == "# eutils_base_url: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/" for h in header)
    assert any(h.startswith("# registration: https://osf.io/qkb9g/") for h in header)
    assert any(h == "# queries: 190" for h in header)
    assert rows and list(rows[0].keys()) == CSV_COLUMNS
    assert len(rows) == 190

    specs = {s.query_id: s for s in build_count_queries(catalogue, ["A", "B"])}
    for row in rows:
        spec = specs[f"{row['family']}_{row['field']}_{row['metric']}_{row['year']}"]
        assert row["query"] == spec.term
        assert row["querytranslation"] == f"TRANSLATION({spec.term})"
        assert row["run"] == "A" and row["http_status"] == "200" and row["attempt"] == "1"
        assert row["count"].isdigit() and row["utc"].endswith("Z")
    _, rows_b = read_counts_csv(csv_b)
    assert [r["query"] for r in rows_b] == [r["query"] for r in rows]
    assert all(r["run"] == "B" for r in rows_b)

    # audit trail: raw response per request, catalogue snapshot, query list, manifest
    assert len(list((out / "raw" / "runA").glob("*.json"))) == 190
    assert len(list((out / "raw" / "runB").glob("*.json"))) == 190
    assert (out / "catalogue_snapshot.yaml").read_text(encoding="utf-8") == catalogue.text
    assert len(json.loads((out / "queries.json").read_text(encoding="utf-8"))) == 190
    assert (out / "MANIFEST_SHA256.txt").exists()
    assert verify_manifest(out) == []
    assert len(session.calls) == 380
    # the API key appears nowhere in the output tree (raw files, CSV, logs, manifest)
    assert files_containing(out, api_key_env) == []
    log_text = next(out.glob("run_*.log")).read_text(encoding="utf-8")
    assert "Run A versus Run B: 0 of 190 cells differ" in log_text


def test_freeze_records_failed_cells_and_pubmed_warnings(tmp_path, fast_client, catalogue):
    # the third request fails six times (one cell lost), everything else succeeds
    session = FakeSession(status_script=[200, 200] + [500] * 6)
    rc = main(["freeze", "--out", str(tmp_path), "--override-freeze-guard", "--single-run", "--families", "R"], session=session)
    assert rc == 3
    out = next(tmp_path.glob("freeze_*"))
    header, rows = read_counts_csv(next(out.glob("counts_frozen_*_runA.csv")))
    assert len(rows) == 4
    failed = [r for r in rows if r["count"] == ""]
    assert len(failed) == 1 and failed[0]["http_status"] == "500" and failed[0]["attempt"] == "6"
    assert any(h == "# failed_cells: 1" for h in header)
    issues = [json.loads(l) for l in next(out.glob("issues_*_runA.jsonl")).read_text(encoding="utf-8").splitlines()]
    assert len(issues) == 1 and issues[0]["query_id"] == failed[0]["family"] + "_" + failed[0]["field"] + "_" + failed[0]["metric"] + "_" + failed[0]["year"]
    assert not (out / "counts_frozen_" ).exists()
    assert not list(out.glob("*runB.csv"))


# ---- lists ----------------------------------------------------------------------------------

def test_lists_mode_end_to_end_with_sampling_replacement_and_identifiers(tmp_path, fast_client, catalogue):
    lists_specs = {s.query_id: s.term for s in __import__("airct_benchmark.queries", fromlist=["x"]).build_list_queries(catalogue)}
    sizes = {"L_AI_B_2024": 150, "L_STROKE_B_2024": 1200, "L_AI_S_2024": 3000, "L_STROKE_S_2024": 3000,
             "L_AI_R_2024": 25000, "L_STROKE_R_2024": 12000}
    overrides = {lists_specs[k]: v for k, v in sizes.items()}
    # a PMID of the U-AI formal set that is in no B list (so the replacement path is exercised cleanly)
    seq_u = seeded_sequence(range(1, 3001))
    missing_pmid = next(p for p in seq_u[20:220] if p > 1200)
    xml_by_pmid = {
        5: pubmed_article_xml(5, abstract="Registered at NCT00000005.", databanks=[("ClinicalTrials.gov", ["NCT00000005"])]),
        6: pubmed_article_xml(6, abstract="Secondary analysis of NCT00000005."),
        7: pubmed_article_xml(7, abstract="ISRCTN00000007 and ChiCTR2000000007."),
    }
    session = FakeSession(count_overrides=overrides, missing_pmids={missing_pmid}, xml_by_pmid=xml_by_pmid)
    rc = main(["lists", "--out", str(tmp_path), "--override-freeze-guard"], session=session)
    assert rc == 0
    out = next(tmp_path.glob("lists_*"))

    # family L
    assert (out / "pmid_lists" / "pmids_B_AI_2024.txt").read_text().split() == [str(i) for i in range(1, 151)]
    assert len((out / "pmid_lists" / "pmids_R_AI_2024.txt").read_text().split()) == 25000
    meta = json.loads((out / "pmid_lists" / "lists_meta.json").read_text())
    assert meta["lists"]["R_AI"]["count"] == 25000 and meta["lists"]["R_AI"]["retrieved"] == 25000
    assert meta["lists"]["B_AI"]["query"] == lists_specs["L_AI_B_2024"]

    # Q13 sampling
    v_ai = (out / "samples" / "sample_V-AI.csv").read_text().splitlines()
    assert len(v_ai) == 1 + 150 and all(l.split(",")[1] == "formal" for l in v_ai[1:])
    v_stroke = (out / "samples" / "sample_V-STROKE.csv").read_text().splitlines()
    assert len(v_stroke) == 1 + 20 + 200
    report = json.loads((out / "samples" / "sampling_report.json").read_text())
    assert report["seed"] == 20260904
    cells = {c["cell"]: c for c in report["cells"]}
    assert cells["V-AI"]["rule"] == "census"
    assert len(cells["U-STROKE"]["formal"]) == 200 and len(cells["R-STROKE"]["formal"]) == 50

    # Q14 replacement of the unretrievable PMID along the seeded sequence
    u_ai = cells["U-AI"]
    assert u_ai["replacements"] == [{"missing": missing_pmid, "replacement": seq_u[220], "set": "formal"}]
    assert missing_pmid not in u_ai["formal"] and seq_u[220] in u_ai["formal"]
    assert u_ai["missing_after_replacement"] == []
    efetch = json.loads((out / "xml" / "efetch_report.json").read_text())
    assert efetch["B_AI"]["requested"] == 150 and efetch["B_AI"]["returned"] == 150 and efetch["B_AI"]["missing"] == []
    assert efetch["B_STROKE"]["batches"] == 6
    assert efetch["U-AI"]["returned"] == 220
    assert len(list((out / "xml" / "B_AI").glob("batch_*.xml"))) == 1

    # 12.8 identifiers from the complete B lists
    summary = json.loads((out / "identifiers" / "identifiers_summary.json").read_text())
    assert summary["AI"]["records"] == 150
    assert summary["AI"]["records_with_identifier"] == 3
    assert summary["AI"]["distinct_identifiers"] == 3            # NCT00000005 (twice), ISRCTN00000007, CHICTR2000000007
    assert summary["AI"]["distinct_identifiers_by_registry"] == {"ChiCTR": 1, "ClinicalTrials.gov": 1, "ISRCTN": 1}
    assert summary["STROKE"]["records_with_identifier"] == 3      # PMIDs 5, 6, 7 are synthetic in both lists
    ids_csv = (out / "identifiers" / "identifiers_2024.csv").read_text().splitlines()
    assert ids_csv[0] == "field,pmid,registry,identifier,source,raw"
    assert (out / "MANIFEST_SHA256.txt").exists() and verify_manifest(out) == []

    # rating sheet from the fetched XML: no MeSH terms, no publication types
    sheet = tmp_path / "sheet.csv"
    rc = main(["ratingsheet", "--xml-dir", str(out / "xml" / "B_AI"), "--pmids", str(out / "samples" / "sample_V-AI.csv"), "--out", str(sheet)])
    assert rc == 0
    rows = list(csv.DictReader(sheet.open(encoding="utf-8")))
    assert len(rows) == 150
    assert list(rows[0].keys()) == ["pmid", "year", "journal", "title", "abstract", "V1", "V2", "V3", "V4", "V5", "V6", "rater", "comment"]
    assert "Randomized Controlled Trial" not in sheet.read_text(encoding="utf-8")
    assert "Artificial Intelligence" not in sheet.read_text(encoding="utf-8")

    # identifiers mode on the saved XML
    ids_out = tmp_path / "ids.csv"
    rc = main(["identifiers", "--xml-dir", str(out / "xml" / "B_AI"), "--field", "AI", "--out", str(ids_out)])
    assert rc == 0
    assert json.loads(ids_out.with_suffix(".summary.json").read_text())["distinct_identifiers"] == 3


def test_lists_no_efetch(tmp_path, fast_client, catalogue):
    session = FakeSession()
    rc = main(["lists", "--out", str(tmp_path), "--override-freeze-guard", "--no-efetch"], session=session)
    assert rc == 0
    out = next(tmp_path.glob("lists_*"))
    assert len(list((out / "pmid_lists").glob("pmids_*.txt"))) == 6
    assert len(list((out / "samples").glob("sample_*.csv"))) == 6
    assert not (out / "xml").exists()
    assert all(not c[1].endswith("efetch.fcgi") or c[2].get("rettype") == "uilist" for c in session.calls)


# ---- offline modes --------------------------------------------------------------------------

def test_check_catalogue_mode_exit_codes(tmp_path, capsys):
    rc = main(["check-catalogue", "--prereg", str(FIXTURES / "preregistration_q12_excerpt.md"), "--json", str(tmp_path / "r.json")])
    assert rc == 0
    report = json.loads((tmp_path / "r.json").read_text())
    assert report["strict_ok"] and report["lenient_ok"]
    assert "strict string identity confirmed" in capsys.readouterr().out
    rc = main(["check-catalogue", "--prereg", str(FIXTURES / "preregistration_v2_0_pdf_text_p3-6.txt")])
    assert rc == 1
    mutated = tmp_path / "mutated.md"
    mutated.write_text((FIXTURES / "preregistration_q12_excerpt.md").read_text(encoding="utf-8").replace("medline[sb]", "MEDLINE[sb]"), encoding="utf-8")
    rc = main(["check-catalogue", "--prereg", str(mutated)])
    assert rc == 2
    assert "12.4 MEDLINE" in capsys.readouterr().out


def test_manifest_and_verify_manifest(tmp_path, capsys):
    d = tmp_path / "data"
    d.mkdir()
    (d / "a.csv").write_text("1,2,3\n")
    (d / "sub").mkdir()
    (d / "sub" / "b.json").write_text("{}")
    assert main(["manifest", "--dir", str(d)]) == 0
    manifest = (d / "MANIFEST_SHA256.txt").read_text().splitlines()
    assert len(manifest) == 2 and all(len(l.split("  ")[0]) == 64 for l in manifest)
    assert main(["verify-manifest", "--dir", str(d)]) == 0
    (d / "a.csv").write_text("1,2,4\n")
    assert main(["verify-manifest", "--dir", str(d)]) == 2
    assert "a.csv" in capsys.readouterr().out
