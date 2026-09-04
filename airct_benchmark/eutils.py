"""NCBI E-utilities client for the AI-RCT Benchmark (Q7, Q9, 12.1).

* esearch with db=pubmed, retmode=json, retmax=0, tool=airct_benchmark, email=witold.polanski@ukdd.de
  and api_key from the environment variable NCBI_API_KEY (never logged, never stored).
* Token bucket: 10 requests per second with a key, 3 without.
* HTTP 429 and 5xx (and transport errors) are retried with backoff 1, 2, 4, 8, 16, 32 seconds,
  at most six attempts in total.
* The raw body of every response (every attempt) is saved as a file with a UTC timestamp.
* PMID lists: esearch with retmax and retstart up to 10,000 identifiers, otherwise usehistory=y and
  retrieval of the identifier list from the history server (efetch rettype=uilist).
* efetch retmode=xml in batches of 200 PMIDs, GET or POST depending on the URL length.

The network layer is injectable (``session``) so that the test suite runs fully offline.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol
from urllib.parse import urlencode

from .util import Redactor, safe_filename, utc_compact, utc_iso, utc_now

log = logging.getLogger("airct_benchmark.eutils")

DEFAULT_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
RETRY_STATUSES = {429} | set(range(500, 600))


class TransportError(RuntimeError):
    """A request failed after the maximum number of attempts.

    Carries the audit fields of the last attempt (HTTP status, attempt number, UTC time, raw file)
    so that a failed cell is still fully documented in the frozen CSV."""

    def __init__(self, message: str, *, http_status: int | None = None, attempt: int = 0, utc: str = "", raw_path: str = ""):
        super().__init__(message)
        self.http_status = http_status
        self.attempt = attempt
        self.utc = utc
        self.raw_path = raw_path


class Response(Protocol):
    status_code: int
    text: str


class Session(Protocol):
    """Minimal subset of requests.Session used by the client (duck-typed for tests)."""

    def get(self, url: str, params: dict | None = None, timeout: float | None = None) -> Response: ...

    def post(self, url: str, data: dict | None = None, timeout: float | None = None) -> Response: ...


class TokenBucket:
    """Classic token bucket: ``rate`` tokens per second, capacity ``rate`` (bursts of one second)."""

    def __init__(self, rate: float, clock: Callable[[], float] = time.monotonic, sleeper: Callable[[float], None] = time.sleep):
        if rate <= 0:
            raise ValueError("rate must be positive")
        self.rate = float(rate)
        self.capacity = float(rate)
        self._tokens = float(rate)
        self._clock = clock
        self._sleep = sleeper
        self._last = clock()

    def _refill(self) -> None:
        now = self._clock()
        self._tokens = min(self.capacity, self._tokens + (now - self._last) * self.rate)
        self._last = now

    def acquire(self) -> float:
        """Block until a token is available; return the seconds waited."""
        waited = 0.0
        self._refill()
        if self._tokens < 1.0:
            need = (1.0 - self._tokens) / self.rate
            self._sleep(need)
            waited = need
            self._refill()
            # The requested wait has elapsed; guard against clock granularity and rounding.
            self._tokens = max(self._tokens, 1.0)
        self._tokens -= 1.0
        return waited


@dataclass
class RawRecord:
    """What is stored on disk for every response (api_key removed)."""

    utc: str
    endpoint: str
    method: str
    params: dict
    http_status: int | None
    attempt: int
    label: str
    body: str | None
    error: str | None = None


@dataclass
class EsearchCount:
    count: int | None
    querytranslation: str
    http_status: int | None
    attempt: int
    utc: str
    raw_path: str
    error: str | None = None
    errorlist: dict = field(default_factory=dict)
    warninglist: dict = field(default_factory=dict)
    webenv: str | None = None
    querykey: str | None = None

    @property
    def ok(self) -> bool:
        return self.count is not None and self.error is None

    @property
    def has_issues(self) -> bool:
        return bool(self.error) or any(self.errorlist.values()) or any(self.warninglist.values())


@dataclass
class RequestResult:
    http_status: int
    body: str
    attempt: int
    utc: str
    raw_path: Path
    method: str


@dataclass
class EfetchBatch:
    pmids: list[int]
    xml: str
    http_status: int
    attempt: int
    utc: str
    raw_path: str
    method: str


class EutilsClient:
    """Thin, auditable client. One instance per run label so that raw files are grouped."""

    def __init__(
        self,
        *,
        api_key: str | None,
        raw_dir: Path | str,
        base_url: str = DEFAULT_BASE_URL,
        db: str = "pubmed",
        tool: str = "airct_benchmark",
        email: str = "witold.polanski@ukdd.de",
        requests_per_second: float | None = None,
        backoff_seconds: Iterable[float] = (1, 2, 4, 8, 16, 32),
        max_attempts: int = 6,
        timeout: float = 60.0,
        efetch_batch_size: int = 200,
        esearch_page_size: int = 10000,
        history_threshold: int = 10000,
        max_get_url_length: int = 1500,
        session: Session | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        now: Callable[[], Any] = utc_now,
    ):
        self.api_key = api_key
        self.redact = Redactor([api_key] if api_key else [])
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url if base_url.endswith("/") else base_url + "/"
        self.db = db
        self.tool = tool
        self.email = email
        rate = requests_per_second if requests_per_second else (10.0 if api_key else 3.0)
        self.bucket = TokenBucket(rate, clock=clock, sleeper=sleeper)
        self.backoff = [float(b) for b in backoff_seconds]
        self.max_attempts = int(max_attempts)
        self.timeout = timeout
        self.efetch_batch_size = int(efetch_batch_size)
        self.esearch_page_size = int(esearch_page_size)
        self.history_threshold = int(history_threshold)
        self.max_get_url_length = int(max_get_url_length)
        self._sleep = sleeper
        self._now = now
        if session is None:
            import requests  # imported lazily so that the tests never need the network

            session = requests.Session()
        self.session = session
        self.request_count = 0

    # ---- low level ------------------------------------------------------------------------
    def _base_params(self) -> dict:
        p = {"db": self.db, "tool": self.tool, "email": self.email}
        if self.api_key:
            p["api_key"] = self.api_key
        return p

    def _url(self, endpoint: str) -> str:
        return f"{self.base_url}{endpoint}.fcgi"

    def _save_raw(self, record: RawRecord, label: str, attempt: int, suffix: str) -> Path:
        stamp = utc_compact(self._now())
        name = f"{safe_filename(label)}__a{attempt}__{stamp}.{suffix}"
        path = self.raw_dir / name
        payload = {
            "utc": record.utc,
            "endpoint": record.endpoint,
            "method": record.method,
            "params": record.params,
            "http_status": record.http_status,
            "attempt": record.attempt,
            "label": record.label,
            "error": record.error,
            "body": record.body,
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
        return path

    def request(self, endpoint: str, params: dict, label: str, *, force_post: bool = False) -> RequestResult:
        """Send one request with rate limiting and retry.

        Every attempt's response body is saved with a UTC timestamp. Returns the final successful
        attempt; raises TransportError after max_attempts."""
        full = {**self._base_params(), **params}
        public = self.redact.params(full)
        url = self._url(endpoint)
        method = "POST" if force_post or len(url + "?" + urlencode(full)) > self.max_get_url_length else "GET"
        last_exc: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            self.bucket.acquire()
            utc = utc_iso(self._now())
            status: int | None = None
            body: str | None = None
            error: str | None = None
            try:
                self.request_count += 1
                if method == "GET":
                    resp = self.session.get(url, params=full, timeout=self.timeout)
                else:
                    resp = self.session.post(url, data=full, timeout=self.timeout)
                status, body = int(resp.status_code), resp.text
            except Exception as exc:  # transport error (timeout, connection reset, DNS)
                error = f"{type(exc).__name__}: {self.redact(exc)}"
                last_exc = exc
            raw_path = self._save_raw(RawRecord(utc, endpoint, method, public, status, attempt, label, body, error), label, attempt, "json")
            if error is None and status is not None and status not in RETRY_STATUSES:
                if attempt > 1:
                    log.info("%s succeeded on attempt %d (HTTP %d)", label, attempt, status)
                return RequestResult(status, body or "", attempt, utc, raw_path, method)
            reason = error or f"HTTP {status}"
            if attempt < self.max_attempts:
                wait = self.backoff[min(attempt - 1, len(self.backoff) - 1)]
                log.warning("%s attempt %d failed (%s); retrying in %.0f s", label, attempt, self.redact(reason), wait)
                self._sleep(wait)
            else:
                log.error("%s failed after %d attempts (%s)", label, attempt, self.redact(reason))
                raise TransportError(f"{label}: failed after {attempt} attempts ({self.redact(reason)})",
                                     http_status=status, attempt=attempt, utc=utc, raw_path=str(raw_path)) from last_exc
        raise TransportError(f"{label}: no attempts made")  # pragma: no cover

    # ---- esearch --------------------------------------------------------------------------
    def esearch_count(self, term: str, label: str, *, usehistory: bool = False) -> EsearchCount:
        """One count query (retmax=0). Never raises for PubMed-level errors; they are returned in .error."""
        params = {"term": term, "retmode": "json", "retmax": 0}
        if usehistory:
            params["usehistory"] = "y"
        try:
            r = self.request("esearch", params, label)
        except TransportError as exc:
            return EsearchCount(None, "", exc.http_status, exc.attempt or self.max_attempts, exc.utc or utc_iso(self._now()),
                                exc.raw_path, error=str(exc))
        return self._parse_esearch(r.body, r.http_status, r.attempt, r.utc, r.raw_path)

    @staticmethod
    def _parse_esearch(body: str, status: int, attempt: int, utc: str, raw_path: Path) -> EsearchCount:
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            return EsearchCount(None, "", status, attempt, utc, str(raw_path), error=f"invalid JSON: {exc}")
        res = data.get("esearchresult")
        if not isinstance(res, dict):
            return EsearchCount(None, "", status, attempt, utc, str(raw_path), error="no esearchresult in response")
        if "ERROR" in res:
            return EsearchCount(None, res.get("querytranslation", ""), status, attempt, utc, str(raw_path), error=f"PubMed ERROR: {res['ERROR']}")
        try:
            count = int(res["count"])
        except (KeyError, TypeError, ValueError):
            return EsearchCount(None, res.get("querytranslation", ""), status, attempt, utc, str(raw_path), error="no count in response")
        return EsearchCount(
            count=count,
            querytranslation=res.get("querytranslation", ""),
            http_status=status,
            attempt=attempt,
            utc=utc,
            raw_path=str(raw_path),
            errorlist=res.get("errorlist") or {},
            warninglist=res.get("warninglist") or {},
            webenv=res.get("webenv"),
            querykey=res.get("querykey"),
        )

    def esearch_ids(self, term: str, label: str) -> tuple[list[int], EsearchCount, list[str]]:
        """Complete PMID list for a query (family L).

        Up to history_threshold identifiers: esearch pages with retmax and retstart. Above it: the
        count request carries usehistory=y and the identifiers are read from the history server
        with efetch rettype=uilist in pages of esearch_page_size. Returns (sorted unique PMIDs,
        the count result, list of notes such as count mismatches)."""
        notes: list[str] = []
        head = self.esearch_count(term, f"{label}__count", usehistory=True)
        if not head.ok:
            raise TransportError(f"{label}: count request failed ({head.error})")
        count = head.count or 0
        ids: list[int] = []
        if count <= self.history_threshold:
            retstart = 0
            while retstart < count:
                params = {"term": term, "retmode": "json", "retmax": self.esearch_page_size, "retstart": retstart}
                r = self.request("esearch", params, f"{label}__page{retstart}")
                data = json.loads(r.body)["esearchresult"]
                page = [int(x) for x in data.get("idlist", [])]
                if not page:
                    notes.append(f"empty page at retstart={retstart}")
                    break
                ids.extend(page)
                retstart += len(page)
        else:
            if not head.webenv or not head.querykey:
                raise TransportError(f"{label}: history server keys missing for a list of {count} identifiers")
            retstart = 0
            while retstart < count:
                params = {"query_key": head.querykey, "WebEnv": head.webenv, "rettype": "uilist", "retmode": "text",
                          "retstart": retstart, "retmax": self.esearch_page_size}
                r = self.request("efetch", params, f"{label}__uilist{retstart}")
                page = [int(line) for line in r.body.split() if line.strip().isdigit()]
                if not page:
                    notes.append(f"empty uilist page at retstart={retstart}")
                    break
                ids.extend(page)
                retstart += len(page)
        unique = sorted(set(ids))
        if len(unique) != count:
            notes.append(f"count {count} differs from {len(unique)} unique identifiers retrieved (live database movement)")
        if len(unique) != len(ids):
            notes.append(f"{len(ids) - len(unique)} duplicate identifiers across pages removed")
        return unique, head, notes

    # ---- efetch ---------------------------------------------------------------------------
    def efetch_xml(self, pmids: Iterable[int], label: str) -> list[EfetchBatch]:
        """efetch retmode=xml in batches of efetch_batch_size. GET or POST depends on URL length."""
        pmids = [int(p) for p in pmids]
        batches: list[EfetchBatch] = []
        for i in range(0, len(pmids), self.efetch_batch_size):
            chunk = pmids[i : i + self.efetch_batch_size]
            params = {"id": ",".join(str(p) for p in chunk), "retmode": "xml"}
            batch_label = f"{label}__batch{i // self.efetch_batch_size + 1:04d}"
            r = self.request("efetch", params, batch_label)
            batches.append(EfetchBatch(chunk, r.body, r.http_status, r.attempt, r.utc, str(r.raw_path), r.method))
        return batches
