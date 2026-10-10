import csv
import json
from datetime import date
from pathlib import Path

import pytest
import yaml

from airct_benchmark import __version__
from airct_benchmark import run as run_mod
from airct_benchmark.manifest import verify_manifest
from airct_benchmark.queries import build_count_queries, build_list_specs, build_syntax_check_plan, shared_cells, smoke_query
from airct_benchmark.run import CSV_COLUMNS, PACKAGE_DIR, freeze_guard, header_lines, main, translation_pattern_notes
from airct_benchmark.sampling import seeded_sequence
from airct_benchmark.util import source_fingerprint
from conftest import (FIXTURE_AMENDMENT, FIXTURE_PANEL, FIXTURES, FakeClock, FakeResponse, FakeSession, cli, pubmed_article_xml,
                      pubmed_set_xml, realistic_translation)
from gbd_helpers import final_panel

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
    rc = cli(["smoke", "--out", str(tmp_path)], session=session)
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
    rc = cli(["smoke", "--out", str(tmp_path)], session=session)
    assert rc == 0
    result = json.loads(next(tmp_path.glob("smoke_*.json")).read_text(encoding="utf-8"))
    assert result["difference"] == 77
    log_text = next(tmp_path.glob("run_*.log")).read_text(encoding="utf-8")
    assert "difference +77" in log_text


def test_smoke_other_metric_and_failure_exit_code(tmp_path, fast_client, catalogue):
    b = smoke_query(catalogue, "B", "rct")
    session = FakeSession(count_overrides={b.term: 1405})
    rc = cli(["smoke", "--out", str(tmp_path), "--family", "B", "--metric", "rct"], session=session)
    assert rc == 0
    result = json.loads(next(tmp_path.glob("smoke_*.json")).read_text(encoding="utf-8"))
    assert result["reference_count"] == 1405 and result["difference"] == 0
    failing = FakeSession(status_script=[500] * 6)
    rc = cli(["smoke", "--out", str(tmp_path / "fail")], session=failing)
    assert rc == 2


def test_smoke_refuses_cells_outside_diabetes_2015(tmp_path, fast_client):
    with pytest.raises(SystemExit):
        cli(["smoke", "--out", str(tmp_path), "--family", "R"], session=FakeSession())


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
        cli(["freeze", "--out", str(tmp_path), "--families", "A"], session=session)
    with pytest.raises(SystemExit):
        cli(["lists", "--out", str(tmp_path)], session=session)
    assert session.calls == []


# ---- freeze ---------------------------------------------------------------------------------

def test_freeze_writes_run_a_and_run_b_with_header_and_manifest(tmp_path, fast_client, api_key_env, catalogue):
    session = FakeSession()
    rc = cli(["freeze", "--out", str(tmp_path), "--override-freeze-guard", "--families", "A", "B"], session=session)
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
    assert any(h == f"# gbd_panel_sha256: {catalogue.gbd_sha256()} (status final)" for h in header)
    assert any(h == "# amendment: v3.0 (docs/AMENDMENT_v3_0.md)" for h in header)
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
    assert (out / "gbd_panel_snapshot.yaml").read_text(encoding="utf-8") == FIXTURE_PANEL.read_text(encoding="utf-8")
    assert json.loads((out / "shared_cells.json").read_text(encoding="utf-8")) == shared_cells(catalogue)
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
    rc = cli(["freeze", "--out", str(tmp_path), "--override-freeze-guard", "--single-run", "--families", "R"], session=session)
    assert rc == 3
    out = next(tmp_path.glob("freeze_*"))
    header, rows = read_counts_csv(next(out.glob("counts_frozen_*_runA.csv")))
    assert len(rows) == 4
    failed = [r for r in rows if r["count"] == ""]
    assert len(failed) == 1 and failed[0]["http_status"] == "500" and failed[0]["attempt"] == "6"
    assert any(h == "# failed_cells: 1" for h in header)
    issues = [json.loads(l) for l in next(out.glob("issues_*_runA.jsonl")).read_text(encoding="utf-8").splitlines()]
    assert len(issues) == 1 and issues[0]["query_id"] == failed[0]["family"] + "_" + failed[0]["field"] + "_" + failed[0]["metric"] + "_" + failed[0]["year"]
    assert not list(out.glob("*.partial.csv"))
    assert not list(out.glob("*runB.csv"))


# ---- freeze with the amendment families ----------------------------------------------------------

def test_freeze_runs_amendment_families_after_the_registered_ones(tmp_path, fast_client, catalogue):
    session = FakeSession()
    rc = cli(["freeze", "--out", str(tmp_path), "--override-freeze-guard", "--single-run", "--families", "GA", "DB", "A"], session=session)
    assert rc == 0
    out = next(tmp_path.glob("freeze_*"))
    header, rows = read_counts_csv(next(out.glob("counts_frozen_*_runA.csv")))
    assert len(rows) == 95 + 85 + 360
    assert [f for f in dict.fromkeys(r["family"] for r in rows)] == ["A", "DB", "GA"]      # registered first, then amendment order
    specs = {s.query_id: s for s in build_count_queries(catalogue, ["A", "DB", "GA"])}
    for row in rows:
        assert row["query"] == specs[f"{row['family']}_{row['field']}_{row['metric']}_{row['year']}"].term
    fields = {r["field"] for r in rows if r["family"] == "GA"}
    assert len(fields) == 18 and "GBD_STROKE" not in fields and "GBD_LOWER_RESPIRATORY_INFECTIONS" in fields
    cells = json.loads((out / "shared_cells.json").read_text(encoding="utf-8"))
    assert len(cells) == 120 and {c["gbd_member"] for c in cells} == {"GBD_STROKE", "GBD_DIABETES_MELLITUS"}
    assert (out / "gbd_panel_snapshot.yaml").read_bytes() == FIXTURE_PANEL.read_bytes()      # byte copies of the files as executed
    assert (out / "catalogue_snapshot.yaml").read_bytes() == catalogue.path.read_bytes()
    assert verify_manifest(out) == []


def test_full_catalogue_is_4326_requests_per_run(tmp_path, fast_client, catalogue):
    session = FakeSession()
    rc = cli(["freeze", "--out", str(tmp_path), "--override-freeze-guard", "--single-run"], session=session)
    assert rc == 0
    out = next(tmp_path.glob("freeze_*"))
    header, rows = read_counts_csv(next(out.glob("counts_frozen_*_runA.csv")))
    assert len(rows) == 4326 and len(session.calls) == 4326
    assert any(h == "# queries: 4326" for h in header)
    assert [r["family"] for r in rows[:2034]] == [s.family for s in build_count_queries(catalogue)[:2034]]
    assert rows[2034]["family"] == "DB" and rows[-1]["family"] == "RS"
    assert len({(r["family"], r["field"], r["metric"], r["year"]) for r in rows}) == 4326


def test_a_run_never_writes_into_a_directory_of_an_earlier_run(tmp_path, fast_client):
    """A second freeze or lists run on the same day would mix raw responses, XML and issue lines of two sessions."""
    session = FakeSession()
    assert cli(["freeze", "--out", str(tmp_path), "--override-freeze-guard", "--single-run", "--families", "R"], session=session) == 0
    n = len(session.calls)
    with pytest.raises(SystemExit) as exc:
        cli(["freeze", "--out", str(tmp_path), "--override-freeze-guard", "--single-run", "--families", "R"], session=session)
    assert "exists and is not empty" in str(exc.value) and len(session.calls) == n
    assert cli(["lists", "--out", str(tmp_path), "--override-freeze-guard", "--no-efetch"], session=session) == 0
    n = len(session.calls)
    with pytest.raises(SystemExit) as exc:
        cli(["lists", "--out", str(tmp_path), "--override-freeze-guard", "--no-efetch"], session=session)
    assert "exists and is not empty" in str(exc.value) and len(session.calls) == n


def provisional_panel(tmp_path: Path) -> Path:
    path = tmp_path / "gbd_panel_provisional.yaml"
    path.write_text(FIXTURE_PANEL.read_text(encoding="utf-8").replace("status: final", "status: provisional"), encoding="utf-8")
    return path


def test_online_modes_refuse_a_provisional_gbd_panel(tmp_path, fast_client):
    prov = str(provisional_panel(tmp_path))
    session = FakeSession()
    out = tmp_path / "out"
    for argv in (["freeze", "--out", str(out), "--override-freeze-guard"],
                 ["freeze", "--out", str(out), "--override-freeze-guard", "--families", "GE"],
                 ["lists", "--out", str(out), "--override-freeze-guard"],
                 ["syntax-check", "--send", "--out", str(out)]):
        with pytest.raises(SystemExit) as exc:
            main(["--gbd-panel", prov, *argv], session=session)
        assert "status 'provisional'" in str(exc.value)
    assert session.calls == [] and not out.exists()             # refused before anything was written or sent
    # families that do not involve the GBD panel can still be exercised (testing only)
    assert main(["--gbd-panel", prov, "freeze", "--out", str(out), "--override-freeze-guard", "--single-run", "--families", "A"],
                session=session) == 0


def test_synthetic_test_panel_can_never_be_sent_to_pubmed(tmp_path, monkeypatch):
    """Without an injected session the client would talk to PubMed: the test panel is refused first, in
    every online mode and with every option. Should the guard ever fail, no client can be created here."""
    def no_client(*args, **kwargs):
        raise AssertionError("a client for PubMed was about to be created")

    monkeypatch.setattr(run_mod, "make_client", no_client)
    out = tmp_path / "out"
    for argv in (["freeze", "--out", str(out), "--override-freeze-guard"],
                 ["freeze", "--out", str(out), "--override-freeze-guard", "--families", "R"],
                 ["freeze", "--out", str(out), "--override-freeze-guard", "--families", "GA", "--single-run"],
                 ["lists", "--out", str(out), "--override-freeze-guard"],
                 ["lists", "--out", str(out), "--override-freeze-guard", "--no-efetch"],
                 ["syntax-check", "--send", "--out", str(out)],
                 ["smoke", "--out", str(out)]):
        with pytest.raises(SystemExit) as exc:
            main(["--gbd-panel", str(FIXTURE_PANEL), *argv])
        assert "synthetic GBD panel of the test suite" in str(exc.value)
    assert not out.exists()
    # offline modes stay available with the test panel
    assert main(["--gbd-panel", str(FIXTURE_PANEL), "syntax-check", "--dry-run"]) == 0


def test_a_refused_catalogue_ends_with_exit_code_2(tmp_path, capsys, catalogue):
    bad = tmp_path / "catalogue.yaml"
    bad.write_text(catalogue.text.replace('"Stroke"[Mesh]', '"Stroke"[Majr]', 1), encoding="utf-8")
    for argv in (["check-catalogue"], ["syntax-check", "--dry-run"], ["smoke", "--out", str(tmp_path / "o")]):
        with pytest.raises(SystemExit) as exc:
            main(["--catalogue", str(bad), "--gbd-panel", str(FIXTURE_PANEL), *argv], session=FakeSession())
        assert exc.value.code == 2
    assert "catalogue refused: the registered part of config/catalogue.yaml" in capsys.readouterr().err


# ---- lists ----------------------------------------------------------------------------------

def list_terms(catalogue) -> dict[str, str]:
    return {x.key: x.spec.term for x in build_list_specs(catalogue)}


def split_lists(catalogue) -> dict[str, list[int]]:
    """RCT-tagged STROKE records 1..1200: 1..30 also indexed under AI, 31..1200 not. The enriched
    untagged stratum 1..3000 is split at 150."""
    term = list_terms(catalogue)
    return {
        term["B_AI"]: list(range(1, 151)),
        term["B_STROKE"]: list(range(1, 1201)),
        term["S_AI"]: list(range(1, 3001)),
        term["S_STROKE"]: list(range(1, 3001)),
        term["DB_STROKE"]: list(range(1, 31)),
        term["ERCT_STROKE"]: list(range(31, 1201)),
        term["SAI_STROKE"]: list(range(1, 151)),
        term["SNONAI_STROKE"]: list(range(151, 3001)),
    }


def r_counts(catalogue) -> dict[str, int]:
    term = list_terms(catalogue)
    return {term["R_AI"]: 25000, term["R_STROKE"]: 12000}


def test_lists_mode_end_to_end_with_split_cells_replacement_and_identifiers(tmp_path, fast_client, catalogue):
    term = list_terms(catalogue)
    ids = split_lists(catalogue)
    ids[term["DB_STROKE"]] = list(range(1, 31)) + [5000]      # entered the live database after the complete list was read
    seq_u_ai = seeded_sequence(range(1, 3001))
    drawn_elsewhere = (set(seeded_sequence(range(151, 3001))[:220]) | set(seeded_sequence(range(31, 1201))[:220])
                       | set(seeded_sequence(range(1, 25001))[:70]) | set(seeded_sequence(range(1, 12001))[:70]))
    # Q14: a PMID of the U-AI formal set that occurs in no other draw and in no complete list
    missing_sampled = next(p for p in seq_u_ai[20:220] if p > 1200 and p not in drawn_elsewhere)
    # a PMID of two census cells (V-AI, U-STROKE-AI) that is in no sampled draw: it cannot be replaced
    missing_census = next(p for p in range(31, 151) if p not in drawn_elsewhere and p not in seq_u_ai[:220])
    xml_by_pmid = {
        5: pubmed_article_xml(5, abstract="Registered at NCT00000005.", databanks=[("ClinicalTrials.gov", ["NCT00000005"])]),
        6: pubmed_article_xml(6, abstract="Secondary analysis of NCT00000005."),
        7: pubmed_article_xml(7, abstract="ISRCTN00000007 and ChiCTR2000000007."),
        5000: pubmed_article_xml(5000, abstract="Registered as DRKS00005000."),
    }
    session = FakeSession(count_overrides=r_counts(catalogue), ids_overrides=ids, missing_pmids={missing_sampled, missing_census}, xml_by_pmid=xml_by_pmid)
    rc = cli(["lists", "--out", str(tmp_path), "--override-freeze-guard"], session=session)
    assert rc == 0
    out = next(tmp_path.glob("lists_*"))

    # families L and LV: ten lists
    assert sorted(p.name for p in (out / "pmid_lists").glob("pmids_*.txt")) == sorted(
        f"pmids_{k}_2024.txt" for k in ["B_AI", "B_STROKE", "S_AI", "S_STROKE", "R_AI", "R_STROKE", "DB_STROKE", "ERCT_STROKE", "SAI_STROKE", "SNONAI_STROKE"])
    assert (out / "pmid_lists" / "pmids_B_AI_2024.txt").read_text().split() == [str(i) for i in range(1, 151)]
    assert (out / "pmid_lists" / "pmids_DB_STROKE_2024.txt").read_text().split() == [str(i) for i in range(1, 31)] + ["5000"]
    assert len((out / "pmid_lists" / "pmids_R_AI_2024.txt").read_text().split()) == 25000
    meta = json.loads((out / "pmid_lists" / "lists_meta.json").read_text())
    assert meta["lists"]["R_AI"]["count"] == 25000 and meta["lists"]["R_AI"]["retrieved"] == 25000
    assert meta["source_sha256"] == source_fingerprint(PACKAGE_DIR) and meta["pipeline_version"] == __version__
    assert meta["gbd_panel_sha256"] == catalogue.gbd_sha256() and set(meta["git"]) == {"commit", "dirty", "describe"}
    assert meta["lists"]["B_AI"]["query"] == term["B_AI"] and meta["lists"]["B_AI"]["list_family"] == "L"
    assert meta["lists"]["ERCT_STROKE"]["list_family"] == "LV" and meta["lists"]["ERCT_STROKE"]["query_id"] == "LV_STROKE_ERCT_2024"

    # PMID-level comparison of the complete lists with their split lists: reported, never corrected
    parts = {x["whole"]: x for x in json.loads((out / "pmid_lists" / "partition_report.json").read_text())["partitions"]}
    assert parts["B_STROKE"]["parts"] == ["DB_STROKE", "ERCT_STROKE"]
    assert parts["B_STROKE"]["whole_size"] == 1200 and parts["B_STROKE"]["union_size"] == 1201
    assert parts["B_STROKE"]["only_in_parts"] == [5000] and parts["B_STROKE"]["only_in_whole"] == []
    assert parts["B_STROKE"]["in_more_than_one_part"] == [] and parts["B_STROKE"]["consistent"] is False
    assert parts["S_STROKE"]["consistent"] is True and parts["S_STROKE"]["part_sizes"] == {"SAI_STROKE": 150, "SNONAI_STROKE": 2850}

    # validation cells of Amendment v3.0, Section 6.1
    report = json.loads((out / "samples" / "sampling_report.json").read_text())
    assert report["seed"] == 20260904 and report["xml_checked"] is True
    cells = {c["cell"]: c for c in report["cells"]}
    assert list(cells) == ["V-AI", "V-STROKE-AI", "V-STROKE-nonAI", "U-AI", "U-STROKE-AI", "U-STROKE-nonAI", "R-AI", "R-STROKE"]
    assert sorted(p.name for p in (out / "samples").glob("sample_*.csv")) == sorted(f"sample_{c}.csv" for c in cells)
    for name, size in (("V-AI", 150), ("V-STROKE-AI", 31), ("U-STROKE-AI", 150)):          # 200 records or fewer: rated completely
        assert cells[name]["rule"] == "census" and cells[name]["pilot"] == [] and len(cells[name]["formal"]) == size, name
        assert cells[name]["reserve"] == []
    for name, source, population in (("V-STROKE-nonAI", "ERCT_STROKE", 1170), ("U-AI", "S_AI", 3000), ("U-STROKE-nonAI", "SNONAI_STROKE", 2850)):
        assert cells[name]["source_list"] == source and cells[name]["population_size"] == population
        assert len(cells[name]["pilot"]) == 20 and len(cells[name]["formal"]) == 200, name
    assert len(cells["R-AI"]["formal"]) == 50 and len(cells["R-STROKE"]["formal"]) == 50 and len(cells["R-AI"]["pilot"]) == 20
    assert cells["V-STROKE-nonAI"]["pilot"] == seeded_sequence(range(31, 1201))[:20]

    # Q14: the PMID of a sampled cell that efetch does not return in six attempts is replaced along the seeded sequence ...
    u_ai = cells["U-AI"]
    assert u_ai["replacements"] == [{"missing": missing_sampled, "replacement": seq_u_ai[220], "set": "formal"}]
    assert missing_sampled not in u_ai["formal"] and seq_u_ai[220] in u_ai["formal"] and u_ai["missing_after_replacement"] == []
    # ... and the sample file that the raters receive holds the replacement, not the PMID that was replaced
    csv_pmids = [int(l.split(",")[3]) for l in (out / "samples" / "sample_U-AI.csv").read_text().splitlines()[1:]]
    assert csv_pmids == u_ai["pilot"] + u_ai["formal"] and missing_sampled not in csv_pmids and seq_u_ai[220] in csv_pmids
    asked = [c for c in session.calls if c[1].endswith("efetch.fcgi") and c[2].get("retmode") == "xml" and str(missing_sampled) in c[2]["id"].split(",")]
    assert len(asked) == 6                                             # six attempts before the record counts as unretrievable
    # a census cell has no replacement queue: the PMID is recorded as missing
    for name in ("V-AI", "U-STROKE-AI"):
        assert cells[name]["replacements"] == [{"missing": missing_census, "replacement": None, "set": "formal"}], name
        assert cells[name]["missing_after_replacement"] == [missing_census]
    assert report["census_lists_missing"] == {"B_AI": [missing_census], "B_STROKE": [missing_census]}

    # family O: the XML of the complete RCT-tagged lists is reused for the V-cells; a record that is only in a
    # split list is fetched under that list
    efetch = json.loads((out / "xml" / "efetch_report.json").read_text())
    assert efetch["B_AI"]["requested"] == 150 and efetch["B_AI"]["returned"] == 149 and efetch["B_AI"]["missing"] == [missing_census]
    assert efetch["B_AI"]["attempts"] == 6 and efetch["B_STROKE"]["batches"] == 6 and efetch["B_STROKE"]["returned"] == 1199
    assert efetch["DB_STROKE"]["requested"] == 1 and efetch["DB_STROKE"]["missing"] == [] and "not in the XML of B_STROKE" in efetch["DB_STROKE"]["note"]
    assert efetch["ERCT_STROKE"]["missing"] == [missing_census]
    assert efetch["V-STROKE-nonAI"] == {"batches": 0, "methods": [], "attempts": 0, "xml_source": "xml/B_STROKE and xml/ERCT_STROKE",
                                        "requested": 220, "returned": 220, "missing": []}
    assert efetch["V-STROKE-AI"]["xml_source"] == "xml/B_STROKE and xml/DB_STROKE" and "fetched_directly" not in efetch["V-STROKE-AI"]
    assert efetch["V-STROKE-AI"]["returned"] == 31 and efetch["V-STROKE-AI"]["missing"] == []
    assert efetch["V-AI"]["fetched_directly"] == [missing_census] and efetch["V-AI"]["missing"] == [missing_census]
    assert efetch["U-AI"]["returned"] == 220 and efetch["U-STROKE-AI"]["returned"] == 149
    assert len(list((out / "xml" / "B_AI").glob("batch_*.xml"))) == 1
    assert not (out / "xml" / "V-STROKE-nonAI").exists() and not (out / "xml" / "S_STROKE").exists()

    # 12.8 identifiers from the complete B lists, and split by AI status within STROKE (S8)
    summary = json.loads((out / "identifiers" / "identifiers_summary.json").read_text())
    assert summary["AI"]["records"] == 150
    assert summary["AI"]["records_with_identifier"] == 3
    assert summary["AI"]["distinct_identifiers"] == 3            # NCT00000005 (twice), ISRCTN00000007, CHICTR2000000007
    assert summary["AI"]["distinct_identifiers_by_registry"] == {"ChiCTR": 1, "ClinicalTrials.gov": 1, "ISRCTN": 1}
    assert summary["STROKE"]["records_with_identifier"] == 3      # PMIDs 5, 6, 7 are synthetic in both lists
    assert set(summary["subsets"]) == {"DB_STROKE", "ERCT_STROKE"}
    # the record that is only in the split list counts in its denominator AND its identifier is read
    assert summary["subsets"]["DB_STROKE"]["records"] == 31 and summary["subsets"]["DB_STROKE"]["records_with_identifier"] == 4
    assert summary["subsets"]["DB_STROKE"]["distinct_identifiers_by_registry"] == {"ChiCTR": 1, "ClinicalTrials.gov": 1, "DRKS": 1, "ISRCTN": 1}
    assert summary["subsets"]["ERCT_STROKE"]["records"] == 1170 and summary["subsets"]["ERCT_STROKE"]["distinct_identifiers"] == 0
    # a record of both complete lists is written under both fields
    rows = list(csv.DictReader((out / "identifiers" / "identifiers_2024.csv").open(encoding="utf-8")))
    assert list(rows[0]) == ["field", "pmid", "registry", "identifier", "source", "raw"]
    assert sorted({(r["field"], r["pmid"]) for r in rows}) == [("AI", "5"), ("AI", "6"), ("AI", "7"), ("STROKE", "5"), ("STROKE", "6"), ("STROKE", "7")]
    assert (out / "MANIFEST_SHA256.txt").exists() and verify_manifest(out) == []

    # rating sheet of a split cell from two XML directories: no MeSH terms, no publication types
    sheet = tmp_path / "sheet.csv"
    rc = cli(["ratingsheet", "--xml-dir", str(out / "xml" / "B_STROKE"), str(out / "xml" / "DB_STROKE"),
              "--pmids", str(out / "samples" / "sample_V-STROKE-AI.csv"), "--out", str(sheet)])
    assert rc == 0
    rows = list(csv.DictReader(sheet.open(encoding="utf-8")))
    assert len(rows) == 31 and {int(r["pmid"]) for r in rows} == set(range(1, 31)) | {5000}
    assert all(r["title"] != "[XML not available]" for r in rows)
    assert list(rows[0].keys()) == ["pmid", "year", "journal", "title", "abstract", "V1", "V2", "V3", "V4", "V5", "V6", "rater", "comment"]
    assert "Randomized Controlled Trial" not in sheet.read_text(encoding="utf-8")
    assert "Artificial Intelligence" not in sheet.read_text(encoding="utf-8")
    # the sheet of a sampled cell lists the replacement and has XML for every row
    rc = cli(["ratingsheet", "--xml-dir", str(out / "xml" / "U-AI"), "--pmids", str(out / "samples" / "sample_U-AI.csv"), "--out", str(sheet)])
    rows = list(csv.DictReader(sheet.open(encoding="utf-8")))
    assert rc == 0 and len(rows) == 220 and all(r["title"] != "[XML not available]" for r in rows)

    # identifiers mode on the saved XML; a directory that does not exist is an error, not an empty result
    ids_out = tmp_path / "ids.csv"
    rc = cli(["identifiers", "--xml-dir", str(out / "xml" / "B_AI"), "--field", "AI", "--out", str(ids_out)])
    assert rc == 0
    assert json.loads(ids_out.with_suffix(".summary.json").read_text())["distinct_identifiers"] == 3
    with pytest.raises(SystemExit):
        cli(["identifiers", "--xml-dir", str(out / "xml" / "nothing_here"), "--field", "AI", "--out", str(ids_out)])
    with pytest.raises(SystemExit):
        cli(["ratingsheet", "--xml-dir", str(out / "xml" / "nothing_here"), "--out", str(sheet)])


def test_lists_no_efetch(tmp_path, fast_client, catalogue):
    session = FakeSession()
    rc = cli(["lists", "--out", str(tmp_path), "--override-freeze-guard", "--no-efetch"], session=session)
    assert rc == 0
    out = next(tmp_path.glob("lists_*"))
    assert len(list((out / "pmid_lists").glob("pmids_*.txt"))) == 10
    assert len(list((out / "samples").glob("sample_*.csv"))) == 8
    assert (out / "pmid_lists" / "partition_report.json").exists()
    assert json.loads((out / "samples" / "sampling_report.json").read_text())["xml_checked"] is False
    assert not (out / "xml").exists()
    assert all(not c[1].endswith("efetch.fcgi") or c[2].get("rettype") == "uilist" for c in session.calls)


def efetch_xml_call(endpoint: str, params: dict) -> bool:
    return endpoint == "efetch.fcgi" and params.get("retmode") == "xml"


def test_one_empty_or_broken_efetch_response_is_asked_again_and_replaces_nothing(tmp_path, fast_client, catalogue):
    """A response that is empty, an error page or not XML is not evidence that 200 records cannot be
    retrieved: the records are requested again (Q14 speaks of six attempts), and nothing is replaced."""
    state = {"n": 0}

    def hook(endpoint, params, n):
        if efetch_xml_call(endpoint, params):
            state["n"] += 1
            if state["n"] == 1:
                return FakeResponse(200, pubmed_set_xml([]))                      # well formed, but empty
            if state["n"] == 3:
                return FakeResponse(200, "<html><body>Service unavailable</body>")  # HTTP 200, not XML
            if state["n"] == 5:
                return FakeResponse(400, "<eFetchResult><ERROR>bad request</ERROR></eFetchResult>")
        return None

    session = FakeSession(count_overrides=r_counts(catalogue), ids_overrides=split_lists(catalogue), hook=hook)
    assert cli(["lists", "--out", str(tmp_path), "--override-freeze-guard"], session=session) == 0
    out = next(tmp_path.glob("lists_*"))
    report = json.loads((out / "samples" / "sampling_report.json").read_text())
    assert all(c["replacements"] == [] and c["missing_after_replacement"] == [] for c in report["cells"])
    assert report["census_lists_missing"] == {"B_AI": [], "B_STROKE": []}
    efetch = json.loads((out / "xml" / "efetch_report.json").read_text())
    assert efetch["B_AI"]["attempts"] == 2 and efetch["B_AI"]["returned"] == 150
    assert efetch["B_STROKE"]["returned"] == 1200 and efetch["B_STROKE"]["attempts"] == 2
    cells = {c["cell"]: c for c in report["cells"]}
    assert cells["U-AI"]["pilot"] == seeded_sequence(range(1, 3001))[:20]          # the registered draw survived untouched
    assert cells["U-AI"]["formal"] == seeded_sequence(range(1, 3001))[20:220]


def test_a_service_failure_stops_the_lists_run_instead_of_drawing_replacements(tmp_path, fast_client, catalogue):
    def hook(endpoint, params, n):
        if efetch_xml_call(endpoint, params) and len(params["id"].split(",")) > 100:
            return FakeResponse(200, pubmed_set_xml([]))          # every large batch comes back empty, again and again
        return None

    session = FakeSession(count_overrides=r_counts(catalogue), ids_overrides=split_lists(catalogue), hook=hook)
    assert cli(["lists", "--out", str(tmp_path), "--override-freeze-guard"], session=session) == 3
    out = next(tmp_path.glob("lists_*"))
    failed = json.loads((out / "lists_failed.json").read_text())
    assert "150 of 150 records were not returned by efetch after 6 attempts" in failed["reason"]
    assert "no replacement is drawn" in failed["reason"]
    assert not (out / "samples" / "sampling_report.json").exists() and not (out / "identifiers").exists()
    assert verify_manifest(out) == []


def test_an_incomplete_pmid_list_is_read_again_and_never_sampled(tmp_path, fast_client, catalogue):
    term = list_terms(catalogue)
    state = {"truncated": 0}

    def truncate_once(endpoint, params, n):
        # the first page request of the ERCT_STROKE list returns an empty page, once
        if endpoint == "esearch.fcgi" and params.get("term") == term["ERCT_STROKE"] and int(params.get("retmax", 0)) > 0 and state["truncated"] == 0:
            state["truncated"] += 1
            return FakeResponse(200, json.dumps({"esearchresult": {"count": "1170", "idlist": [], "querytranslation": "x"}}))
        return None

    session = FakeSession(count_overrides=r_counts(catalogue), ids_overrides=split_lists(catalogue), hook=truncate_once)
    assert cli(["lists", "--out", str(tmp_path / "a"), "--override-freeze-guard", "--no-efetch"], session=session) == 0
    out = next((tmp_path / "a").glob("lists_*"))
    meta = json.loads((out / "pmid_lists" / "lists_meta.json").read_text())["lists"]["ERCT_STROKE"]
    assert meta["count"] == meta["retrieved"] == 1170 and any(n.startswith("reading 1: count 1170, 0 identifiers retrieved") for n in meta["notes"])
    report = json.loads((out / "samples" / "sampling_report.json").read_text())
    assert {c["cell"]: c["population_size"] for c in report["cells"]}["V-STROKE-nonAI"] == 1170

    def always_short(endpoint, params, n):
        if endpoint == "esearch.fcgi" and params.get("term") == term["ERCT_STROKE"] and int(params.get("retmax", 0)) > 0:
            return FakeResponse(200, json.dumps({"esearchresult": {"count": "1170", "idlist": [str(i) for i in range(31, 1031)], "querytranslation": "x"}}))
        return None

    session = FakeSession(count_overrides=r_counts(catalogue), ids_overrides=split_lists(catalogue), hook=always_short)
    assert cli(["lists", "--out", str(tmp_path / "b"), "--override-freeze-guard", "--no-efetch"], session=session) == 3
    out = next((tmp_path / "b").glob("lists_*"))
    assert "No sample is drawn from an incomplete list" in json.loads((out / "lists_failed.json").read_text())["reason"]
    assert not (out / "samples").exists()


# ---- offline modes --------------------------------------------------------------------------

def test_check_catalogue_confirms_a_final_panel_with_its_files_and_its_amendment(tmp_path, capsys):
    made = final_panel(tmp_path)                       # a final panel from a synthetic export, with mapping, ranking and record
    prereg = str(FIXTURES / "preregistration_q12_excerpt.md")
    base = ["--gbd-panel", str(made["panel"]), "check-catalogue", "--prereg", prereg, "--amendment", str(made["amendment"])]
    capsys.readouterr()
    rc = main(base + ["--json", str(tmp_path / "r.json")])
    assert rc == 0, capsys.readouterr().out
    report = json.loads((tmp_path / "r.json").read_text())
    assert report["strict_ok"] and report["lenient_ok"] and report["exit_code"] == 0
    assert report["registration"]["strict_ok"] and report["amendment"]["strict_ok"] and report["amendment"]["checked"]
    assert report["gbd_panel_status"] == "final"
    assert sum(i["source"] == "registration" for i in report["items"]) == 93
    kinds = [i["kind"] for i in report["items"] if i["source"] == "amendment"]
    assert len(kinds) == 98 and kinds.count("gbd_panel_real") == 1 and kinds.count("gbd_panel_files") == 1
    assert kinds.count("gbd_panel_block") == 1
    printed = capsys.readouterr().out
    assert "strict string identity confirmed" in printed
    # the record of the check names the code it was made with, also where no git checkout exists
    assert report["source_sha256"] == source_fingerprint(PACKAGE_DIR) and report["pipeline_version"] == __version__
    assert f"source SHA-256 {report['source_sha256']}" in printed and f"Catalogue SHA-256 {report['catalogue_sha256']}" in printed

    # registration text as distributed (PDF text with line wraps): identity up to whitespace
    assert main(["--gbd-panel", str(made["panel"]), "check-catalogue", "--prereg", str(FIXTURES / "preregistration_v2_0_pdf_text_p3-6.txt"),
                 "--amendment", str(made["amendment"])]) == 1
    # one character changed in the registration text
    mutated = tmp_path / "mutated.md"
    mutated.write_text((FIXTURES / "preregistration_q12_excerpt.md").read_text(encoding="utf-8").replace("medline[sb]", "MEDLINE[sb]"), encoding="utf-8")
    capsys.readouterr()
    assert main(["--gbd-panel", str(made["panel"]), "check-catalogue", "--prereg", str(mutated), "--amendment", str(made["amendment"])]) == 2
    assert "12.4 MEDLINE" in capsys.readouterr().out

    # the deposited files no longer support the panel: each of these ends with exit code 2
    def refused_after(edit, expected: str) -> None:
        saved = {k: made[k].read_bytes() for k in ("mapping", "ranking", "record", "panel", "amendment", "table")}
        edit()
        capsys.readouterr()
        try:
            rc = main(base)
        except SystemExit as exc:                           # the loader may refuse the panel file before the check runs
            rc = exc.code
        out = capsys.readouterr()
        assert rc == 2 and expected in out.out + out.err, (expected, out.out[-600:], out.err[-300:])
        for k, data in saved.items():
            made[k].write_bytes(data)

    text = lambda k: made[k].read_text(encoding="utf-8")   # noqa: E731
    refused_after(lambda: made["mapping"].write_text(text("mapping").replace("agreed independently", "agreed after discussion", 1), encoding="utf-8"),
                  "the mapping table has another SHA-256 than the panel file states")
    refused_after(lambda: made["ranking"].write_text(text("ranking").replace("Road injuries,Injuries,excluded,rule (a): Level 1 group Injuries", "Road injuries,Injuries,kept for mapping,"), encoding="utf-8"),
                  "the ranking has another SHA-256 than the panel file states")
    refused_after(lambda: made["record"].unlink(), "export record not found")
    refused_after(lambda: made["panel"].write_text(text("panel").replace("  - rank: 23\n", "  - rank: 24\n"), encoding="utf-8"),
                  "the members of the panel file are not the first 20 mapped causes of the mapping table")
    refused_after(lambda: made["panel"].write_text(text("panel").replace("in_trajectory: true", "in_trajectory: false", 1), encoding="utf-8"),
                  "the members of the panel file are not the first 20 mapped causes")
    refused_after(lambda: made["amendment"].write_text(text("amendment").replace("| 15 | Malaria |", "| 16 | Malaria |"), encoding="utf-8"),
                  "Section 5 panel row 13: GBD_MALARIA")

    # the text around the table: Section 5.7 must stand in the amendment as one unchanged block that names the current files
    raw_sha = json.loads(text("record"))["raw_export"]["sha256"]
    assert raw_sha in text("table") and raw_sha in text("amendment")
    refused_after(lambda: made["amendment"].write_text(text("amendment").replace(raw_sha, "0" * 64), encoding="utf-8"),
                  "SHA-256 of the raw export 0000000000")              # the message shows the place in the amendment
    refused_after(lambda: made["amendment"].write_text(text("amendment").replace("Catalogue volume with this panel:", "Catalogue volume:"), encoding="utf-8"),
                  "of the generated text, at character 17: there the generated text reads")
    refused_after(lambda: made["amendment"].write_text(text("amendment").replace("Road injuries (rank", "Falls (rank", 1), encoding="utf-8"),
                  "[gbd_panel_block] Section 5.7 stands in the amendment as generated")
    # the deposited text itself is tested first: it must have been written for the files as they are now
    refused_after(lambda: made["table"].write_text(text("table").replace(raw_sha, "0" * 64), encoding="utf-8"),
                  "does not state the SHA-256 of the current panel file, mapping table, ranking and raw export")
    refused_after(lambda: made["table"].unlink(), "data/gbd/gbd_panel_amendment_table.md not found")
    record = json.loads(text("record"))
    refused_after(lambda: made["record"].write_text(json.dumps(dict(record, exported_by="Somebody Else"), indent=2), encoding="utf-8"),
                  "does not state the export date, person, permalink and hierarchy hash of data/gbd/gbd_export_record.json")

    def same_edit_in_both(old: str, new: str) -> None:                 # a hand edit of the deposited text, pasted into the amendment
        assert old in text("table") and old in text("amendment")
        made["table"].write_text(text("table").replace(old, new), encoding="utf-8")
        made["amendment"].write_text(text("amendment").replace(old, new), encoding="utf-8")

    volume = next(line for line in text("table").split("\n") if line.startswith("Catalogue volume with this panel:"))
    refused_after(lambda: same_edit_in_both(volume, "Catalogue volume with this panel: 1 additional count requests, 2 per run."),
                  "does not hold the table of the panel file and the catalogue volume as they are now")
    refused_after(lambda: same_edit_in_both("| 15 | Malaria |", "| 15 | Malaria and others |"),
                  "does not hold the table of the panel file and the catalogue volume as they are now")
    raters = yaml.safe_load(text("panel"))["source"]["raters"]
    refused_after(lambda: same_edit_in_both(f"by the rule of 5.3 by {raters}.", "by the rule of 5.3 by XX and YY."),
                  f"does not name the raters of the panel file ({raters})")
    # whitespace only: a blank line added inside the block gives exit code 1; the line endings of the file are no difference
    saved = made["amendment"].read_bytes()
    made["amendment"].write_text(text("amendment").replace("\n\nCatalogue volume with this panel:", "\n\n\nCatalogue volume with this panel:"), encoding="utf-8")
    assert main(base) == 1
    unix = saved.replace(b"\r\n", b"\n")                     # Python on Windows wrote the file with \r\n, elsewhere with \n
    assert b"\r" not in unix
    for line_ending in (b"\r\n", b"\n"):
        made["amendment"].write_bytes(unix.replace(b"\n", line_ending))
        assert main(base) == 0
    made["amendment"].write_bytes(saved)
    assert main(base) == 0                                   # everything restored


def test_check_catalogue_refuses_the_test_panel_a_missing_text_and_a_provisional_panel(tmp_path, capsys):
    prereg = str(FIXTURES / "preregistration_q12_excerpt.md")
    # the synthetic panel of the test suite is never confirmed
    rc = cli(["check-catalogue", "--prereg", prereg, "--amendment", str(FIXTURE_AMENDMENT)])
    assert rc == 2
    assert "GBD panel is not the synthetic panel of the test suite" in capsys.readouterr().out
    # the amendment text is missing
    rc = cli(["check-catalogue", "--prereg", prereg, "--amendment", str(tmp_path / "no_such_file.md"), "--json", str(tmp_path / "r.json")])
    assert rc == 2
    out = capsys.readouterr().out
    assert "file not found" in out and "the release must not be tagged" in out
    report = json.loads((tmp_path / "r.json").read_text())
    assert report["registration"]["strict_ok"] and not report["amendment"]["checked"] and not report["strict_ok"]
    # one character changed in a template of the amendment text
    mutated = tmp_path / "amendment_mutated.md"
    mutated.write_text(FIXTURE_AMENDMENT.read_text(encoding="utf-8").replace('{G} AND "Humans"[Mesh] AND (...)', '{G} AND "Human"[Mesh] AND (...)'), encoding="utf-8")
    rc = cli(["check-catalogue", "--prereg", prereg, "--amendment", str(mutated)])
    assert rc == 2
    assert "Section 4 family GA den" in capsys.readouterr().out
    # a provisional panel can be loaded, but it never passes the release check
    rc = main(["--gbd-panel", str(provisional_panel(tmp_path)), "check-catalogue", "--prereg", prereg, "--amendment", str(FIXTURE_AMENDMENT)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "GBD panel status is final (found: provisional)" in out and "has status 'provisional'" in out


def test_manifest_and_verify_manifest(tmp_path, capsys):
    d = tmp_path / "data"
    d.mkdir()
    (d / "a.csv").write_text("1,2,3\n")
    (d / "sub").mkdir()
    (d / "sub" / "b.json").write_text("{}")
    assert cli(["manifest", "--dir", str(d)]) == 0
    manifest = (d / "MANIFEST_SHA256.txt").read_text().splitlines()
    assert len(manifest) == 2 and all(len(l.split("  ")[0]) == 64 for l in manifest)
    assert cli(["verify-manifest", "--dir", str(d)]) == 0
    (d / "a.csv").write_text("1,2,4\n")
    assert cli(["verify-manifest", "--dir", str(d)]) == 2
    assert "a.csv" in capsys.readouterr().out


# ---- syntax check of the amendment (publication year 2015 only) --------------------------------------

CONSISTENT_COUNTS = {
    # registered smoke cells of Diabetes Mellitus 2015 with their Q18 values
    "A/den": 18723, "E/den": 18647, "K/den": 13614, "R/S": 941,
    # invented values for the new compositions, chosen so that every identity of the plan holds
    "DV/ai_vocab_den": 60, "DV/nonai_vocab_den": 18663, "DV/ai_tiab_den": 40, "DV/nonai_tiab_den": 18683,
    "QV/ai_den": 80, "QV/nonai_den": 20000, "WV/ai_norob_den": 60, "KV/ai_den": 50, "KV/nonai_den": 13564,
    "RS/S_ai": 5, "RS/S_nonai": 936,
}
NO_ITEMS = {"phrasesignored": [], "quotedphrasesnotfound": [], "outputmessages": ["No items found."]}
LATE = "GA/den:GBD_SYNTHETIC_CAUSE_TEST_FIXTURE"
N_REQUESTS = 4 + 11 + 18


def syntax_session(catalogue, counts: dict | None = None, **kw) -> FakeSession:
    plan = build_syntax_check_plan(catalogue)
    by_id = {**CONSISTENT_COUNTS, **{it.check_id: 1000 + i for i, it in enumerate(plan) if it.group == "gbd_descriptor"}, LATE: 0}
    by_id.update(counts or {})
    term = {it.check_id: it.term for it in plan}
    assert set(by_id) == set(term)
    warnings = {term[k]: NO_ITEMS for k, v in by_id.items() if v == 0}
    kw.setdefault("translate", realistic_translation)
    return FakeSession(count_overrides={term[k]: v for k, v in by_id.items()}, warnings_by_term=warnings, **kw)


def syntax_outputs(tmp_path: Path) -> tuple[Path, dict, str]:
    out = next(tmp_path.glob("syntax_check_*"))
    result = json.loads(next(out.glob("syntax_check_*.json")).read_text(encoding="utf-8"))
    addendum = next(out.glob("q18_addendum_*.md")).read_text(encoding="utf-8")
    return out, result, addendum


def test_syntax_check_dry_run_prints_the_plan_and_sends_nothing(tmp_path, capsys):
    session = FakeSession()
    assert cli(["syntax-check", "--dry-run", "--out", str(tmp_path)], session=session) == 0
    out = capsys.readouterr().out
    assert f"{N_REQUESTS} requests, publication year 2015 only. Nothing is sent in a dry run." in out
    assert "DV/ai_vocab_den" in out and "GA/den:GBD_MALARIA" in out and "stroke" not in out.lower()
    assert "DB/rct" not in out and "JV/" not in out and ' AND "Randomized Controlled Trial"[pt]' not in out
    assert session.calls == [] and list(tmp_path.iterdir()) == []
    # a provisional panel can be inspected in a dry run, with a note
    assert main(["--gbd-panel", str(provisional_panel(tmp_path)), "syntax-check", "--dry-run"], session=session) == 0
    assert "the descriptor requests below are not final" in capsys.readouterr().out
    assert session.calls == []


def test_syntax_check_without_send_prints_the_plan_and_sends_nothing(tmp_path, capsys, monkeypatch):
    # A forgotten option must never view a count: the requests are sent with --send only.
    monkeypatch.chdir(tmp_path)                       # the default output directory is ./out: it must not appear either
    session = FakeSession()
    for argv in (["syntax-check"], ["syntax-check", "--out", str(tmp_path)], ["syntax-check", "--out", str(tmp_path), "--repeat", "x"],
                 ["syntax-check", "--send", "--dry-run", "--out", str(tmp_path)]):
        assert cli(argv, session=session) == 0
        out = capsys.readouterr().out
        assert f"{N_REQUESTS} requests, publication year 2015 only." in out and "GA/den:GBD_MALARIA" in out
        assert ("Nothing was sent: without --send" in out) == ("--dry-run" not in argv)
        assert session.calls == [] and list(tmp_path.iterdir()) == []
    # without --send the command is not an online mode: no session, no key, the test panel, and still nothing is sent
    assert cli(["syntax-check"]) == 0
    assert "Nothing was sent" in capsys.readouterr().out
    # no abbreviated option is read as --send (or as anything else)
    for abbreviated in ("--s", "--se", "--sen", "--d", "--dry"):
        with pytest.raises(SystemExit) as exc:
            cli(["syntax-check", abbreviated], session=session)
        assert exc.value.code == 2
    assert session.calls == [] and list(tmp_path.iterdir()) == []


def test_syntax_check_clean_run_writes_the_q18_addendum(tmp_path, fast_client, api_key_env, catalogue):
    session = syntax_session(catalogue)
    rc = cli(["syntax-check", "--send", "--out", str(tmp_path)], session=session)
    assert rc == 0
    # exactly one request per plan item; every request is a count request of publication year 2015, without Stroke
    # and without a trial numerator within a field
    assert len(session.calls) == N_REQUESTS
    for _, url, params in session.calls:
        assert url.endswith("esearch.fcgi") and params["retmax"] == 0
        assert params["term"].endswith('AND ("2015"[pdat])') and params["term"].count("[pdat]") == 1
        assert "stroke" not in params["term"].lower()
        assert ' AND "Randomized Controlled Trial"[pt]' not in params["term"] and ' AND "Clinical Trial"[pt]' not in params["term"]
    assert [c[2]["term"] for c in session.calls] == [it.term for it in build_syntax_check_plan(catalogue)]

    out, result, addendum = syntax_outputs(tmp_path)
    assert result["requests_sent"] == N_REQUESTS and result["needs_review"] == [] and result["identities_not_met"] == []
    assert len(result["identities"]) == 8 and all(i["status"] == "met" for i in result["identities"])
    by_id = {r["check_id"]: r for r in result["results"]}
    assert by_id["A/den"]["count"] == 18723 and by_id["A/den"]["reference_count"] == 18723
    assert by_id["KV/ai_den"]["catalogue_query_id"] is None and by_id["KV/ai_den"]["pattern_notes"] == []
    assert by_id[LATE]["count"] == 0 and by_id[LATE]["valid_zero_no_items_found"] is True
    assert by_id[LATE]["info_notes"] and not by_id[LATE]["review_notes"]

    # the addendum states what was sent and what came back
    assert "### Q18 addendum: syntax check of the new expressions of Amendment v3.0" in addendum
    assert f"publication year 2015 only, {N_REQUESTS} requests in total" in addendum
    assert "No request contained the Stroke descriptor or a publication year other than 2015." in addendum
    assert f"catalogue SHA-256 {result['catalogue_sha256']}, GBD panel SHA-256 {catalogue.gbd_sha256()}" in addendum
    assert result["source_sha256"] == source_fingerprint(PACKAGE_DIR)
    assert f"source SHA-256 {result['source_sha256']}; catalogue SHA-256" in addendum
    assert '| 1 | anchor | A/den | `"Diabetes Mellitus"[Mesh] AND "Humans"[Mesh] AND ("2015"[pdat])` | 18,723 | 18,723 | 200 | 1 |' in addendum
    assert "| composition | DV/ai_vocab_den |" in addendum and "| gbd_descriptor | GA/den:GBD_MALARIA |" in addendum
    assert "vocabulary-stable AI partition of the field: DV/ai_vocab_den + DV/nonai_vocab_den = 18723; A/den = 18723; equality: met." in addendum
    assert "A/den + -E/den = 76; QV/ai_den = 80; left side at most right side: met." in addendum
    assert "No request failed and PubMed reported no error-list entry." in addendum
    assert "the expected result for a descriptor introduced after 2015" in addendum
    assert "stroke\"[mesh]" not in addendum.lower() and "NOT MET" not in addendum

    table = list(csv.DictReader(next(out.glob("syntax_check_*.csv")).open(encoding="utf-8")))
    assert len(table) == N_REQUESTS and table[0]["query"] == SMOKE_TERM and table[0]["count"] == "18723"
    assert (out / "gbd_panel_snapshot.yaml").exists() and (out / "catalogue_snapshot.yaml").exists()
    assert len(list((out / "raw").glob("*.json"))) == N_REQUESTS
    assert verify_manifest(out) == []
    assert files_containing(out, api_key_env) == []


def test_syntax_check_asks_for_review_when_an_identity_fails_or_a_translation_departs(tmp_path, fast_client, catalogue):
    # an identity that must hold by construction does not hold
    session = syntax_session(catalogue, {"DV/ai_vocab_den": 61})
    assert cli(["syntax-check", "--send", "--out", str(tmp_path / "a")], session=session) == 4
    _, result, addendum = syntax_outputs(tmp_path / "a")
    assert result["identities_not_met"] == ["vocabulary-stable AI partition of the field"]
    assert "DV/ai_vocab_den + DV/nonai_vocab_den = 18724; A/den = 18723; equality: NOT MET." in addendum

    # PubMed maps a heading to another descriptor (an entry term), puts one into All Fields, and reports a phrase it did not find
    plan = {it.check_id: it for it in build_syntax_check_plan(catalogue)}
    mapped, untagged = plan["GA/den:GBD_MALARIA"].term, plan["GA/den:GBD_HIV_AIDS"].term

    def translate(term: str) -> str:
        t = realistic_translation(term)
        if term == mapped:
            return t.replace('"malaria"[MeSH Terms]', '"plasmodium infections"[MeSH Terms]')
        return t.replace('"hiv infections"[MeSH Terms]', '"hiv infections"[All Fields]') if term == untagged else t

    session = syntax_session(catalogue, translate=translate)
    session.warnings_by_term[plan["GA/den:GBD_TUBERCULOSIS"].term] = {"phrasesignored": [], "quotedphrasesnotfound": ['"Tuberculosis"[Mesh]'], "outputmessages": []}
    assert cli(["syntax-check", "--send", "--out", str(tmp_path / "b")], session=session) == 4
    _, result, addendum = syntax_outputs(tmp_path / "b")
    assert result["needs_review"] == ["GA/den:GBD_MALARIA", "GA/den:GBD_HIV_AIDS", "GA/den:GBD_TUBERCULOSIS"]
    by_id = {r["check_id"]: r for r in result["results"]}
    assert by_id["GA/den:GBD_MALARIA"]["pattern_notes"] == ['the heading "Malaria" does not stand in the translation under this name']
    assert by_id["GA/den:GBD_HIV_AIDS"]["pattern_notes"] == ["[MeSH Terms]: 2 expected from the query, 1 in the translation",
                                                             'the heading "HIV Infections" does not stand in the translation under this name']
    assert "quotedphrasesnotfound" in addendum and '"plasmodium infections"[MeSH Terms]' in addendum
    assert "No request failed and PubMed reported no error-list entry." not in addendum

    # a descriptor recorded as introduced before 2015 returns no record: the heading is probably wrong
    session = syntax_session(catalogue, {"GA/den:GBD_MALARIA": 0})
    assert cli(["syntax-check", "--send", "--out", str(tmp_path / "c")], session=session) == 4
    _, result, addendum = syntax_outputs(tmp_path / "c")
    assert result["needs_review"] == ["GA/den:GBD_MALARIA"]
    assert "although the descriptor is recorded as introduced in or before 2015" in addendum


def test_syntax_check_reports_failed_requests(tmp_path, fast_client, catalogue):
    session = syntax_session(catalogue, status_script=[200] + [500] * 6)
    assert cli(["syntax-check", "--send", "--out", str(tmp_path)], session=session) == 2
    _, result, addendum = syntax_outputs(tmp_path)
    failed = [r for r in result["results"] if r["error"]]
    assert [r["check_id"] for r in failed] == ["E/den"] and failed[0]["count"] is None and failed[0]["attempt"] == 6
    assert any(i["status"].startswith("not evaluated") for i in result["identities"])
    assert "E/den: request failed" in addendum


def test_translation_pattern_notes():
    term = '"Malaria"[Mesh] AND "Humans"[Mesh] AND ("2015"[pdat])'
    good = '"malaria"[MeSH Terms] AND "humans"[MeSH Terms] AND 2015/01/01:2015/12/31[Date - Publication]'
    assert translation_pattern_notes(term, good, 2015) == []
    assert translation_pattern_notes(term, good.replace("2015/12/31", "2016/12/31"), 2015) == [
        "publication-date range 2015/01/01:2015/12/31[Date - Publication] not found exactly once"]
    assert translation_pattern_notes(term, "", 2015)[0].startswith("[MeSH Terms]: 2 expected")
    noexp = '"Robotics"[Mesh:NoExp] AND medline[sb] AND trial[ti] AND "x y"[tiab] AND Review[pt] AND ("2015"[pdat])'
    assert translation_pattern_notes(noexp, realistic_translation(noexp), 2015) == []
    # a NOT that PubMed dropped or doubled, and a heading under another name, are reported
    lri = '("Pneumonia"[Mesh] NOT "COVID-19"[Mesh]) AND "Humans"[Mesh] AND ("2015"[pdat])'
    assert translation_pattern_notes(lri, realistic_translation(lri), 2015) == []
    assert "NOT operators: 1 in the query, 0 in the translation" in translation_pattern_notes(lri, realistic_translation(lri).replace(" NOT ", " AND "), 2015)
    assert translation_pattern_notes(lri, realistic_translation(lri).replace('"covid-19"', '"sars-cov-2 infection"'), 2015) == [
        'the heading "COVID-19" does not stand in the translation under this name']


def test_syntax_check_is_run_once_and_a_repetition_states_its_reason(tmp_path, fast_client, catalogue):
    assert cli(["syntax-check", "--send", "--out", str(tmp_path)], session=syntax_session(catalogue)) == 0
    first = next(tmp_path.glob("syntax_check_*")).name
    session = syntax_session(catalogue)
    with pytest.raises(SystemExit) as exc:
        cli(["syntax-check", "--send", "--out", str(tmp_path)], session=session)
    assert "Refusing to run the syntax check again" in str(exc.value) and first in str(exc.value)
    assert session.calls == []
    assert cli(["syntax-check", "--dry-run", "--out", str(tmp_path)], session=session) == 0          # a dry run views nothing
    fast_client.sleep(2)                                           # the second run starts later (directory names carry the second)
    import time
    time.sleep(1.1)
    assert cli(["syntax-check", "--send", "--out", str(tmp_path), "--repeat", "the first run was made before the panel was final"], session=session) == 0
    runs = sorted(p for p in tmp_path.glob("syntax_check_*"))
    assert len(runs) == 2
    result = json.loads(next(runs[1].glob("syntax_check_*.json")).read_text(encoding="utf-8"))
    addendum = next(runs[1].glob("q18_addendum_*.md")).read_text(encoding="utf-8")
    assert result["earlier_runs_in_the_output_directory"] == [first]
    assert "Repeated run." in addendum and first in addendum and "before the panel was final" in addendum


def test_source_fingerprint_identifies_the_code_on_every_platform(tmp_path):
    """Without a git checkout (a folder downloaded as an archive) a run is identified by the SHA-256 of the
    package sources. Line endings must not change it; any change of the code must."""
    import shutil

    reference = source_fingerprint(PACKAGE_DIR)
    assert len(reference) == 64 and reference == source_fingerprint(PACKAGE_DIR)

    windows = tmp_path / "windows"
    windows.mkdir()
    for path in PACKAGE_DIR.glob("*.py"):
        (windows / path.name).write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    assert source_fingerprint(windows) == reference

    changed = tmp_path / "changed"
    shutil.copytree(windows, changed)
    with open(changed / "util.py", "ab") as fh:
        fh.write(b"# one more line\r\n")
    assert source_fingerprint(changed) != reference

    renamed = tmp_path / "renamed"
    shutil.copytree(windows, renamed)
    (renamed / "util.py").rename(renamed / "util2.py")
    assert source_fingerprint(renamed) != reference


def test_frozen_header_names_the_source_fingerprint(catalogue):
    line = f"# source_sha256: {source_fingerprint(PACKAGE_DIR)} (airct_benchmark/*.py, LF line endings)"
    header = header_lines(catalogue, "A", "2026-10-12T08:00:00Z", "2026-10-12T08:10:00Z", 1)
    assert header.count(line) == 1
    assert header.index(line) == [i for i, h in enumerate(header) if h.startswith("# git_describe: ")][0] + 1


def test_check_catalogue_still_passes_when_the_q18_addendum_is_pasted_into_the_amendment(tmp_path, fast_client, catalogue, capsys):
    """Release path: the syntax check writes the Q18 addendum, it is pasted into Section 8.10 of the amendment,
    and the amendment as submitted is checked again. The table of the addendum has eight cells per row, like the
    panel table; it must be read neither as a panel row nor as a family row of Section 4."""
    made = final_panel(tmp_path / "repo")
    assert cli(["syntax-check", "--send", "--out", str(tmp_path / "syntax")], session=syntax_session(catalogue)) == 0
    _, _, addendum = syntax_outputs(tmp_path / "syntax")
    assert addendum.count("\n| ") > N_REQUESTS                      # the table of the addendum is there
    with open(made["amendment"], "a", encoding="utf-8") as fh:
        fh.write("\n## 8. Transparency\n\n### 8.10 Addendum to Q18\n\n" + addendum)
    capsys.readouterr()
    rc = main(["--gbd-panel", str(made["panel"]), "check-catalogue", "--prereg", str(FIXTURES / "preregistration_q12_excerpt.md"),
               "--amendment", str(made["amendment"])])
    assert rc == 0, capsys.readouterr().out[-1500:]


def test_a_console_that_cannot_show_a_character_does_not_stop_the_command(tmp_path, monkeypatch):
    """Windows: output that is redirected to a file, or a console with a legacy code page, cannot encode every
    character (a cause name, a line of the amendment). The command must report its result instead of ending
    with an encoding error: the entry point switches both streams to replacing such a character."""
    import io
    import sys

    raw_out, raw_err = io.BytesIO(), io.BytesIO()
    out = io.TextIOWrapper(raw_out, encoding="cp1252", errors="strict", newline="\n")
    err = io.TextIOWrapper(raw_err, encoding="cp1252", errors="strict", newline="\n")
    with pytest.raises(UnicodeEncodeError):
        out.write("rank \u2264 20")                       # what would happen without the precaution
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    assert cli(["syntax-check", "--dry-run", "--out", str(tmp_path)]) == 0
    assert out.errors == "replace" and err.errors == "replace"
    print("rank \u2264 20, cause \u2192 descriptor")
    out.flush()
    printed = raw_out.getvalue().decode("cp1252")
    assert "rank ? 20, cause ? descriptor" in printed and f"{N_REQUESTS} requests, publication year 2015 only" in printed
