"""Offline test infrastructure. No test in this suite opens a network connection: the E-utilities
session is replaced by FakeSession, time by FakeClock, and sleeping by a recorder."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from airct_benchmark.catalogue import load_catalogue  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text)


def deterministic_count(term: str) -> int:
    """A stable pseudo count per query string (never used as a real number anywhere)."""
    return int(hashlib.sha256(term.encode()).hexdigest()[:6], 16) % 50000


def esearch_json(count: int, term: str, *, idlist=None, webenv=None, querykey=None, errorlist=None, warninglist=None) -> str:
    res = {
        "count": str(count),
        "retmax": str(len(idlist or [])),
        "retstart": "0",
        "idlist": [str(i) for i in (idlist or [])],
        "translationset": [],
        "querytranslation": f"TRANSLATION({term})",
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
    * list queries: PMIDs 1..count (pages honour retstart and retmax)
    * efetch uilist: PMIDs from the 'history' of the last usehistory query
    * efetch xml: one synthetic PubmedArticle per requested PMID (missing_pmids are omitted)
    * scripted statuses: a queue of HTTP status codes returned before the normal answer
    """

    def __init__(self, count_overrides: dict[str, int] | None = None, status_script: list[int] | None = None,
                 missing_pmids: set[int] | None = None, xml_by_pmid: dict[int, str] | None = None,
                 raise_script: list[Exception] | None = None):
        self.count_overrides = count_overrides or {}
        self.status_script = list(status_script or [])
        self.raise_script = list(raise_script or [])
        self.missing_pmids = set(missing_pmids or [])
        self.xml_by_pmid = xml_by_pmid or {}
        self.calls: list[tuple[str, str, dict]] = []
        self.history: dict[str, str] = {}

    def _count(self, term: str) -> int:
        return self.count_overrides.get(term, deterministic_count(term))

    def _answer(self, method: str, url: str, params: dict) -> FakeResponse:
        self.calls.append((method, url, dict(params)))
        if self.raise_script:
            raise self.raise_script.pop(0)
        if self.status_script:
            status = self.status_script.pop(0)
            if status != 200:
                return FakeResponse(status, f"<html>error {status}</html>")
        endpoint = urlparse(url).path.rsplit("/", 1)[-1]
        if endpoint == "esearch.fcgi":
            term = params["term"]
            count = self._count(term)
            retmax = int(params.get("retmax", 0))
            retstart = int(params.get("retstart", 0))
            idlist = list(range(retstart + 1, min(count, retstart + retmax) + 1)) if retmax else []
            webenv = None
            if params.get("usehistory") == "y":
                webenv = f"WEBENV_{hashlib.md5(term.encode()).hexdigest()[:8]}"
                self.history[webenv] = term
            return FakeResponse(200, esearch_json(count, term, idlist=idlist, webenv=webenv, querykey="1"))
        if endpoint == "efetch.fcgi":
            if params.get("rettype") == "uilist":
                term = self.history[params["WebEnv"]]
                count = self._count(term)
                retstart, retmax = int(params.get("retstart", 0)), int(params.get("retmax", 10000))
                ids = range(retstart + 1, min(count, retstart + retmax) + 1)
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
    return load_catalogue()


@pytest.fixture
def fake_clock():
    return FakeClock()


@pytest.fixture
def api_key_env(monkeypatch):
    monkeypatch.setenv("NCBI_API_KEY", "SECRETKEY1234567890")
    return "SECRETKEY1234567890"
