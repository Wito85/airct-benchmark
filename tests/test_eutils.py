import json
from pathlib import Path

import pytest

from airct_benchmark.eutils import EutilsClient, TokenBucket, TransportError
from conftest import FakeSession, deterministic_count, esearch_json, FakeResponse

TERM = '"Diabetes Mellitus"[Mesh] AND "Humans"[Mesh] AND ("2015"[pdat])'


def make_client(tmp_path, session, clock, api_key="KEY", **kw):
    return EutilsClient(api_key=api_key, raw_dir=tmp_path / "raw", session=session, clock=clock, sleeper=clock.sleep, **kw)


def test_token_bucket_caps_rate(fake_clock):
    bucket = TokenBucket(10, clock=fake_clock, sleeper=fake_clock.sleep)
    start = fake_clock()
    for _ in range(30):
        bucket.acquire()
    elapsed = fake_clock() - start
    # 30 requests at 10 per second with a burst capacity of 10: at least 2 seconds
    assert elapsed >= 2.0 - 1e-9
    assert elapsed < 3.0


def test_rate_without_key_is_three_per_second(tmp_path, fake_clock):
    client = make_client(tmp_path, FakeSession(), fake_clock, api_key=None)
    assert client.bucket.rate == 3.0
    client2 = make_client(tmp_path, FakeSession(), fake_clock, api_key="K")
    assert client2.bucket.rate == 10.0


def test_esearch_count_parses_count_and_translation(tmp_path, fake_clock):
    session = FakeSession(count_overrides={TERM: 18723})
    client = make_client(tmp_path, session, fake_clock)
    res = client.esearch_count(TERM, "smoke")
    assert res.ok and res.count == 18723
    assert res.querytranslation == f"TRANSLATION({TERM})"
    assert res.http_status == 200 and res.attempt == 1
    method, url, params = session.calls[0]
    assert url.endswith("/esearch.fcgi")
    assert params["db"] == "pubmed" and params["retmode"] == "json" and params["retmax"] == 0
    assert params["tool"] == "airct_benchmark" and params["email"] == "witold.polanski@ukdd.de"
    assert params["api_key"] == "KEY"
    assert params["term"] == TERM


def test_raw_response_saved_without_api_key(tmp_path, fake_clock):
    client = make_client(tmp_path, FakeSession(), fake_clock, api_key="SUPERSECRET")
    res = client.esearch_count(TERM, "cell")
    raw = json.loads(Path(res.raw_path).read_text(encoding="utf-8"))
    assert "api_key" not in raw["params"]
    assert "SUPERSECRET" not in Path(res.raw_path).read_text(encoding="utf-8")
    assert raw["http_status"] == 200 and raw["attempt"] == 1 and raw["utc"].endswith("Z")
    assert raw["body"].startswith("{")


def test_retry_on_429_then_success_uses_backoff_one_second(tmp_path, fake_clock):
    session = FakeSession(status_script=[429, 200])
    client = make_client(tmp_path, session, fake_clock)
    t0 = fake_clock()
    res = client.esearch_count(TERM, "cell")
    assert res.ok and res.attempt == 2 and res.http_status == 200
    assert fake_clock() - t0 >= 1.0
    # both attempts stored
    assert len(list((tmp_path / "raw").glob("cell__a*.json"))) == 2


def test_retry_schedule_1_2_4_8_16_then_give_up_after_six_attempts(tmp_path, fake_clock):
    session = FakeSession(status_script=[500, 502, 503, 504, 429, 500, 200])
    client = make_client(tmp_path, session, fake_clock)
    t0 = fake_clock()
    res = client.esearch_count(TERM, "cell")
    assert not res.ok
    assert res.attempt == 6
    assert "failed after 6 attempts" in res.error
    waited = fake_clock() - t0
    assert waited >= 1 + 2 + 4 + 8 + 16
    assert waited < 1 + 2 + 4 + 8 + 16 + 32
    assert len(session.calls) == 6


def test_transport_exceptions_are_retried(tmp_path, fake_clock):
    session = FakeSession(raise_script=[ConnectionError("boom api_key=KEY")])
    client = make_client(tmp_path, session, fake_clock)
    res = client.esearch_count(TERM, "cell")
    assert res.ok and res.attempt == 2
    first_raw = sorted((tmp_path / "raw").glob("cell__a1__*.json"))[0].read_text(encoding="utf-8")
    assert "ConnectionError" in first_raw
    assert "api_key=KEY" not in first_raw


def test_non_retry_http_error_returns_error_result(tmp_path, fake_clock):
    session = FakeSession(status_script=[400])
    client = make_client(tmp_path, session, fake_clock)
    res = client.esearch_count(TERM, "cell")
    assert not res.ok
    assert res.http_status == 400


def test_pubmed_error_and_warning_lists_are_surfaced(tmp_path, fake_clock):
    class S(FakeSession):
        def _answer(self, method, url, params):
            body = esearch_json(0, params["term"], warninglist={"phrasesignored": [], "quotedphrasesnotfound": [], "outputmessages": ["No items found."]})
            return FakeResponse(200, body)

    client = make_client(tmp_path, S(), fake_clock)
    res = client.esearch_count('"Deep Learning"[Mesh] AND ("2015"[pdat])', "cell")
    assert res.ok and res.count == 0 and res.has_issues
    assert res.warninglist["outputmessages"] == ["No items found."]

    class E(FakeSession):
        def _answer(self, method, url, params):
            return FakeResponse(200, json.dumps({"esearchresult": {"ERROR": "Empty term and query_key - nothing todo"}}))

    res2 = make_client(tmp_path, E(), fake_clock).esearch_count("", "cell2")
    assert not res2.ok and "PubMed ERROR" in res2.error


def test_esearch_ids_small_list_pages_with_retmax_retstart(tmp_path, fake_clock):
    term = "SMALL"
    session = FakeSession(count_overrides={term: 250})
    client = make_client(tmp_path, session, fake_clock, esearch_page_size=100)
    ids, head, notes = client.esearch_ids(term, "L")
    assert ids == list(range(1, 251))
    assert head.count == 250 and notes == []
    pages = [c for c in session.calls if c[1].endswith("esearch.fcgi") and int(c[2].get("retmax", 0)) > 0]
    assert [int(c[2]["retstart"]) for c in pages] == [0, 100, 200]


def test_esearch_ids_large_list_uses_history_server(tmp_path, fake_clock):
    term = "LARGE"
    session = FakeSession(count_overrides={term: 25000})
    client = make_client(tmp_path, session, fake_clock, esearch_page_size=10000, history_threshold=10000)
    ids, head, notes = client.esearch_ids(term, "L")
    assert len(ids) == 25000 and ids[0] == 1 and ids[-1] == 25000
    uilist_calls = [c for c in session.calls if c[1].endswith("efetch.fcgi") and c[2].get("rettype") == "uilist"]
    assert [int(c[2]["retstart"]) for c in uilist_calls] == [0, 10000, 20000]
    assert all(c[2]["WebEnv"].startswith("WEBENV_") and c[2]["query_key"] == "1" for c in uilist_calls)
    assert head.webenv is not None
    plain_pages = [c for c in session.calls if c[1].endswith("esearch.fcgi") and int(c[2].get("retmax", 0)) > 0]
    assert plain_pages == []


def test_efetch_batches_of_200_and_method_by_url_length(tmp_path, fake_clock):
    session = FakeSession()
    client = make_client(tmp_path, session, fake_clock, efetch_batch_size=200, max_get_url_length=1500)
    pmids = list(range(30000000, 30000000 + 450))
    batches = client.efetch_xml(pmids, "O")
    assert [len(b.pmids) for b in batches] == [200, 200, 50]
    assert batches[0].method == "POST"   # 200 ids of eight digits exceed 1,500 characters
    assert batches[2].method == "GET"
    assert all(b.http_status == 200 for b in batches)
    assert "<PubmedArticleSet>" in batches[0].xml
    efetch_calls = [c for c in session.calls if c[1].endswith("efetch.fcgi")]
    assert efetch_calls[0][0] == "POST" and efetch_calls[2][0] == "GET"
    assert all(c[2]["retmode"] == "xml" and c[2]["db"] == "pubmed" for c in efetch_calls)


def test_efetch_raw_files_are_saved(tmp_path, fake_clock):
    client = make_client(tmp_path, FakeSession(), fake_clock)
    client.efetch_xml([1, 2, 3], "O")
    files = list((tmp_path / "raw").glob("O__batch0001__a1__*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["endpoint"] == "efetch" and "PubmedArticleSet" in payload["body"]


def test_transport_error_for_list_count_failure(tmp_path, fake_clock):
    session = FakeSession(status_script=[500] * 6)
    client = make_client(tmp_path, session, fake_clock)
    with pytest.raises(TransportError):
        client.esearch_ids("X", "L")
