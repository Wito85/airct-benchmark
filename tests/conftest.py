"""Offline test infrastructure. No test in this suite opens a network connection: the E-utilities
session is replaced by FakeSession, time by FakeClock, and sleeping by a recorder."""

from __future__ import annotations

import hashlib
import json
import re
import socket
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from airct_benchmark.catalogue import load_catalogue  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
# Synthetic GBD panel (status final, marked test_fixture) and the amendment excerpt that lists it.
# The test suite never depends on the state of config/gbd_panel.yaml, which is provisional until
# the export and the reconciliation of Amendment v3.0, Section 5, are done.
FIXTURE_PANEL = FIXTURES / "gbd_panel_fixture.yaml"
FIXTURE_AMENDMENT = FIXTURES / "amendment_v3_0_excerpt.md"


def cli(argv, session=None):
    """Run the command line with the synthetic GBD panel of the test suite."""
    from airct_benchmark.run import main

    return main(["--gbd-panel", str(FIXTURE_PANEL), *argv], session=session)


def realistic_translation(term: str) -> str:
    """A query translation of the form PubMed returns (pattern recorded in Q18): MeSH tags as
    [MeSH Terms] or [MeSH Terms:noexp], publication types as [Publication Type], text words as
    [Title/Abstract] or [Title], medline[sb] as the MEDLINE filter, the year clause as a date range."""
    t = re.sub(r'"([^"]+)"\[Mesh:NoExp\]', lambda m: f'"{m.group(1).lower()}"[MeSH Terms:noexp]', term)
    t = re.sub(r'"([^"]+)"\[Mesh\]', lambda m: f'"{m.group(1).lower()}"[MeSH Terms]', t)
    t = re.sub(r'"([^"]+)"\[pt\]', lambda m: f'"{m.group(1).lower()}"[Publication Type]', t)
    t = re.sub(r'\b([A-Za-z-]+)\[pt\]', lambda m: f'"{m.group(1).lower()}"[Publication Type]', t)
    t = re.sub(r'"([^"]+)"\[tiab\]', lambda m: f'"{m.group(1).lower()}"[Title/Abstract]', t)
    t = re.sub(r'\b([A-Za-z]+)\[tiab\]', lambda m: f'"{m.group(1).lower()}"[Title/Abstract]', t)
    t = re.sub(r'\b([A-Za-z]+)\[ti\]', lambda m: f'"{m.group(1).lower()}"[Title]', t)
    t = t.replace("medline[sb]", '"medline"[Filter]')
    t = re.sub(r'\("(\d{4})"\[pdat\]\)', lambda m: f'{m.group(1)}/01/01:{m.group(1)}/12/31[Date - Publication]', t)
    return t


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Safety net for the whole suite: no test may open a network connection. If a guard of the
    pipeline ever failed inside a test that runs without a fake session, the request would stop
    here instead of reaching PubMed."""
    def refuse(*args, **kwargs):
        raise AssertionError("a test tried to open a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


class FakeResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text)


def deterministic_count(term: str) -> int:
    """A stable pseudo count per query string (never used as a real number anywhere)."""
    return int(hashlib.sha256(term.encode()).hexdigest()[:6], 16) % 50000


def esearch_json(count: int, term: str, *, idlist=None, webenv=None, querykey=None, errorlist=None, warninglist=None,
                 translation: str | None = None) -> str:
    res = {
        "count": str(count),
        "retmax": str(len(idlist or [])),
        "retstart": "0",
        "idlist": [str(i) for i in (idlist or [])],
        "translationset": [],
        "querytranslation": translation if translation is not None else f"TRANSLATION({term})",
    }
    if webenv:
        res["webenv"] = webenv
        res["querykey"] = querykey or "1"
    if errorlist:
        res["errorlist"] = errorlist
    if warninglist:
        res["warninglist"] = warninglist
    return json.dumps({"header": {"type": "esearch", "version": "0.3"}, "esearchresult": res})


def pubmed_article_xml(pmid: int, *, title: str = "", abstract: str = "", databanks=None, year: str = "2024",
                       journal: str = "Journal of Tests", pubtypes=("Journal Article", "Randomized Controlled Trial"),
                       mesh=("Humans", "Artificial Intelligence")) -> str:
    dbs = ""
    if databanks:
        items = "".join(
            f"<DataBank><DataBankName>{name}</DataBankName><AccessionNumberList>"
            + "".join(f"<AccessionNumber>{a}</AccessionNumber>" for a in accs)
            + "</AccessionNumberList></DataBank>"
            for name, accs in databanks
        )
        dbs = f"<DataBankList CompleteYN=\"Y\">{items}</DataBankList>"
    pts = "".join(f'<PublicationType UI="D0">{p}</PublicationType>' for p in pubtypes)
    mh = "".join(f'<MeshHeading><DescriptorName UI="D0" MajorTopicYN="N">{m}</DescriptorName></MeshHeading>' for m in mesh)
    return f"""<PubmedArticle><MedlineCitation Status="MEDLINE" Owner="NLM"><PMID Version="1">{pmid}</PMID>
<Article PubModel="Print"><Journal><ISOAbbreviation>J Tests</ISOAbbreviation><Title>{journal}</Title>
<JournalIssue CitedMedium="Internet"><PubDate><Year>{year}</Year></PubDate></JournalIssue></Journal>
<ArticleTitle>{title or f"Synthetic record {pmid}"}</ArticleTitle>
<Abstract><AbstractText Label="BACKGROUND">{abstract or f"Abstract of record {pmid}."}</AbstractText></Abstract>
{dbs}<PublicationTypeList>{pts}</PublicationTypeList></Article><MeshHeadingList>{mh}</MeshHeadingList></MedlineCitation>
<PubmedData><ArticleIdList><ArticleId IdType="doi">10.1000/test.{pmid}</ArticleId></ArticleIdList></PubmedData></PubmedArticle>"""


def pubmed_set_xml(articles: list[str]) -> str:
    return '<?xml version="1.0" ?><!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2024//EN" "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_240101.dtd">\n<PubmedArticleSet>' + "".join(articles) + "</PubmedArticleSet>"


class FakeSession:
    """Answers esearch and efetch like PubMed would, deterministically and offline.

    * count queries: count = deterministic_count(term), or an override per term
    * list queries: PMIDs 1..count, or the explicit PMID list of ids_overrides for that term
      (pages honour retstart and retmax)
    * efetch uilist: PMIDs from the 'history' of the last usehistory query
    * efetch xml: one synthetic PubmedArticle per requested PMID (missing_pmids are omitted)
    * scripted statuses: a queue of HTTP status codes returned before the normal answer
    * translate: optional function term -> querytranslation (default: TRANSLATION(term))
    * warnings_by_term: optional warninglist per term (for example "No items found.")
    * hook: optional function (endpoint, params, call number) -> FakeResponse or None; a response it
      returns replaces the normal answer (truncated pages, empty or broken efetch bodies, ...)
    """

    def __init__(self, count_overrides: dict[str, int] | None = None, status_script: list[int] | None = None,
                 missing_pmids: set[int] | None = None, xml_by_pmid: dict[int, str] | None = None,
                 raise_script: list[Exception] | None = None, ids_overrides: dict[str, list[int]] | None = None,
                 translate=None, warnings_by_term: dict[str, dict] | None = None, hook=None):
        self.hook = hook
        self.count_overrides = count_overrides or {}
        self.ids_overrides = {k: list(v) for k, v in (ids_overrides or {}).items()}
        self.status_script = list(status_script or [])
        self.raise_script = list(raise_script or [])
        self.missing_pmids = set(missing_pmids or [])
        self.xml_by_pmid = xml_by_pmid or {}
        self.translate = translate
        self.warnings_by_term = warnings_by_term or {}
        self.calls: list[tuple[str, str, dict]] = []
        self.history: dict[str, str] = {}

    def _count(self, term: str) -> int:
        if term in self.ids_overrides:
            return len(self.ids_overrides[term])
        return self.count_overrides.get(term, deterministic_count(term))

    def _ids(self, term: str, retstart: int, retmax: int) -> list[int]:
        if term in self.ids_overrides:
            return self.ids_overrides[term][retstart : retstart + retmax]
        return list(range(retstart + 1, min(self._count(term), retstart + retmax) + 1))

    def _answer(self, method: str, url: str, params: dict) -> FakeResponse:
        self.calls.append((method, url, dict(params)))
        if self.raise_script:
            raise self.raise_script.pop(0)
        if self.status_script:
            status = self.status_script.pop(0)
            if status != 200:
                return FakeResponse(status, f"<html>error {status}</html>")
        endpoint = urlparse(url).path.rsplit("/", 1)[-1]
        if self.hook is not None:
            special = self.hook(endpoint, params, len(self.calls))
            if special is not None:
                return special
        if endpoint == "esearch.fcgi":
            term = params["term"]
            count = self._count(term)
            retmax = int(params.get("retmax", 0))
            retstart = int(params.get("retstart", 0))
            idlist = self._ids(term, retstart, retmax) if retmax else []
            webenv = None
            if params.get("usehistory") == "y":
                webenv = f"WEBENV_{hashlib.md5(term.encode()).hexdigest()[:8]}"
                self.history[webenv] = term
            return FakeResponse(200, esearch_json(count, term, idlist=idlist, webenv=webenv, querykey="1",
                                                  translation=self.translate(term) if self.translate else None,
                                                  warninglist=self.warnings_by_term.get(term)))
        if endpoint == "efetch.fcgi":
            if params.get("rettype") == "uilist":
                term = self.history[params["WebEnv"]]
                retstart, retmax = int(params.get("retstart", 0)), int(params.get("retmax", 10000))
                ids = self._ids(term, retstart, retmax)
                return FakeResponse(200, "\n".join(str(i) for i in ids) + "\n")
            pmids = [int(x) for x in params["id"].split(",")]
            arts = [self.xml_by_pmid.get(p) or pubmed_article_xml(p) for p in pmids if p not in self.missing_pmids]
            return FakeResponse(200, pubmed_set_xml(arts))
        raise AssertionError(f"unexpected endpoint {endpoint}")

    def get(self, url, params=None, timeout=None):
        return self._answer("GET", url, params or {})

    def post(self, url, data=None, timeout=None):
        return self._answer("POST", url, data or {})


class FakeClock:
    def __init__(self, start: float = 1000.0):
        self.t = start

    def __call__(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


@pytest.fixture
def catalogue():
    """The repository catalogue with the synthetic GBD panel of the test suite."""
    return load_catalogue(gbd_panel_path=FIXTURE_PANEL)


@pytest.fixture
def fake_clock():
    return FakeClock()


@pytest.fixture
def api_key_env(monkeypatch):
    monkeypatch.setenv("NCBI_API_KEY", "SECRETKEY1234567890")
    return "SECRETKEY1234567890"
