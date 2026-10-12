"""NCBI E-utilities client for the AI-RCT Benchmark (Q7, Q9, 12.1).

* esearch with db=pubmed, retmode=json, retmax=0, tool=airct_benchmark, email=witold.polanski@ukdd.de
  and api_key from the environment variable NCBI_API_KEY (never logged, never stored).
* Token bucket: 10 requests per second with a key, 3 without.
* HTTP 429 and 5xx (and transport errors) are retried with backoff 1, 2, 4, 8, 16, 32 seconds,
  at most six attempts in total.
* The raw body of every response (every attempt) is saved as a file with a UTC timestamp.
* PMID lists: esearch with retmax and retstart up to 10,000 identifiers. Above that size PubMed
  delivers no more than the first 10,000 identifiers of a query, also from the history server
  (observed on 12 October 2026, version 1.1.1): the list is then read in publication date ranges
  of its year, each range below the limit, with the registered query string unchanged inside every
  range request; the sum of the range counts must equal the count of the unchanged query.
* efetch retmode=xml in batches of 200 PMIDs, GET or POST depending on the URL length.

The network layer is injectable (``session``) so that the test suite runs fully offline.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol
from urllib.parse import urlencode

from .util import Redactor, safe_filename, utc_compact, utc_iso, utc_now

log = logging.getLogger("airct_benchmark.eutils")

DEFAULT_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# PubMed returns at most the first 10,000 identifiers of a result set, from esearch and from the
# history server alike (efetch rettype=uilist returned 9,999 identifiers and then an empty page on
# 12 October 2026). A list above this size is read in date ranges whose counts stay below the limit.
LIST_SERVICE_LIMIT = 9999
PARTITION_FIELD = "pdat"            # publication date: the field that defines the year of every list
FALLBACK_FIELD = "crdt"             # create date: second axis when one publication day exceeds the limit
FALLBACK_RANGE = (date(1990, 1, 1), date(2035, 12, 31))
_YEAR_IN_TERM = re.compile(r'\("(\d{4})"\[pdat\]\)')


def partition_term(term: str, start: date, end: date, field_name: str = PARTITION_FIELD) -> str:
    """The registered query string, unchanged, restricted to a date range (both days inclusive)."""
    return f"({term}) AND ({start:%Y/%m/%d}:{end:%Y/%m/%d}[{field_name}])"


def year_from_term(term: str) -> int | None:
    """The publication year clause ("YYYY"[pdat]) of a registered query string, if it has one."""
    m = _YEAR_IN_TERM.search(term)
    return int(m.group(1)) if m else None
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

    def esearch_ids(self, term: str, label: str, *, year: int | None = None) -> tuple[list[int], EsearchCount, list[str]]:
        """Complete PMID list for a query (families L and LV).

        Up to history_threshold identifiers: esearch pages with retmax and retstart. Above it the
        service delivers no more than the first 10,000 identifiers of a result set (also from the
        history server), so the list is read in publication date ranges of its year, each range
        with a count of at most LIST_SERVICE_LIMIT identifiers (halved until it is), with the
        registered query string unchanged inside every range request. Returns (sorted unique
        PMIDs, the count result of the unchanged query, list of notes such as count mismatches).
        The caller accepts the list only when the number of identifiers equals the count."""
        notes: list[str] = []
        head = self.esearch_count(term, f"{label}__count")
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
            year = year if year is not None else year_from_term(term)
            if year is None:
                raise TransportError(f"{label}: {count} identifiers exceed the service limit of {LIST_SERVICE_LIMIT} "
                                     f"per request set and the query names no publication year to read it in date ranges")
            ids, part_notes = self._ids_in_date_ranges(term, label, int(year), count)
            notes.extend(part_notes)
        unique = sorted(set(ids))
        if len(unique) != count:
            notes.append(f"count {count} differs from {len(unique)} unique identifiers retrieved (live database movement)")
        if len(unique) != len(ids):
            notes.append(f"{len(ids) - len(unique)} duplicate identifiers across pages removed")
        return unique, head, notes

    def _ids_in_date_ranges(self, term: str, label: str, year: int, count: int) -> tuple[list[int], list[str]]:
        """Read a list above the service limit in publication date ranges of its year.

        The year is halved into date ranges until every range holds at most LIST_SERVICE_LIMIT
        identifiers; each range is one esearch request whose term is the unchanged query string
        with the range appended (partition_term). A single publication day above the limit (dates
        without month or day are indexed on the first day) is halved further by create date.
        Every request is recorded like any other (raw response, log). Returns the identifiers in
        reading order and notes: the number of ranges, the largest range, and every range whose
        identifiers do not match its count, and the sum of the range counts if it differs from the
        count of the unchanged query (the caller then reads the list again)."""
        notes: list[str] = []
        ids: list[int] = []
        leaves: list[tuple[str, int, int]] = []    # (range label, count, identifiers retrieved)
        pending: list[tuple[date, date, tuple[date, date] | None]] = [(date(year, 1, 1), date(year, 12, 31), None)]
        while pending:
            start, end, fallback = pending.pop(0)
            if fallback is None:
                t = partition_term(term, start, end)
                tag = f"{PARTITION_FIELD}{start:%Y%m%d}_{end:%Y%m%d}"
            else:
                fs, fe = fallback
                t = partition_term(partition_term(term, start, end), fs, fe, FALLBACK_FIELD)
                tag = f"{PARTITION_FIELD}{start:%Y%m%d}_{end:%Y%m%d}__{FALLBACK_FIELD}{fs:%Y%m%d}_{fe:%Y%m%d}"
            params = {"term": t, "retmode": "json", "retmax": self.esearch_page_size, "retstart": 0}
            r = self.request("esearch", params, f"{label}__{tag}")
            data = json.loads(r.body)["esearchresult"]
            try:
                c = int(data["count"])
            except (KeyError, TypeError, ValueError):
                raise TransportError(f"{label}: no count in the response for the range {tag}")
            if c > LIST_SERVICE_LIMIT:
                if fallback is None:
                    if start < end:
                        mid = start + (end - start) // 2
                        pending.insert(0, (mid + timedelta(days=1), end, None))
                        pending.insert(0, (start, mid, None))
                        continue
                    pending.insert(0, (start, end, FALLBACK_RANGE))
                    continue
                fs, fe = fallback
                if fs < fe:
                    mid = fs + (fe - fs) // 2
                    pending.insert(0, (start, end, (mid + timedelta(days=1), fe)))
                    pending.insert(0, (start, end, (fs, mid)))
                    continue
                raise TransportError(f"{label}: {c} identifiers on the publication day {start:%Y/%m/%d} and the create day "
                                     f"{fs:%Y/%m/%d} exceed the service limit of {LIST_SERVICE_LIMIT}; the list cannot be read completely")
            page = [int(x) for x in data.get("idlist", [])]
            if len(page) != c:
                notes.append(f"range {tag}: count {c} but {len(page)} identifiers in the response")
            ids.extend(page)
            leaves.append((tag, c, len(page)))
        total = sum(c for _, c, _ in leaves)
        largest = max((c for _, c, _ in leaves), default=0)
        notes.append(f"{count} identifiers exceed the service limit of {LIST_SERVICE_LIMIT} per request set: read in "
                     f"{len(leaves)} date ranges of {year} (largest range {largest} identifiers; sum of range counts {total})")
        if total != count:
            notes.append(f"sum of range counts {total} differs from the count {count} of the unchanged query")
        return ids, notes

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
