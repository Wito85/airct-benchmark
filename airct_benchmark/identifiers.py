"""Trial registration identifiers (12.8, endpoint S8).

From the efetch XML of every RCT-tagged AI and Stroke record of 2024 (family O):
(a) accession numbers listed in DataBankList under a trial-registry DataBankName, and
(b) registration identifiers matched in title and abstract by regular expressions for
ClinicalTrials.gov (NCT + eight digits), ISRCTN, EudraCT, DRKS, ACTRN, ChiCTR, UMIN, CTRI,
NTR and its successor NL, IRCT, JPRN and jRCT, and PACTR.

Identifiers are normalized (case, whitespace, separators) and deduplicated within field.
The regular expressions live in config/catalogue.yaml (identifiers.regex) and are fixed with the
tagged release before the freeze run; they are implementation detail and do not alter the estimand.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from .pubmed_xml import PubmedRecord

# Registry names as used in this package. DataBankName values used by NLM map onto them.
DATABANK_TO_REGISTRY = {
    "clinicaltrials.gov": "ClinicalTrials.gov",
    "isrctn": "ISRCTN",
    "eudract": "EudraCT",
    "drks": "DRKS",
    "anzctr": "ACTRN",
    "chictr": "ChiCTR",
    "umin-ctr": "UMIN",
    "umin": "UMIN",
    "ctri": "CTRI",
    "ntr": "NTR",
    "irct": "IRCT",
    "jprn": "JPRN",
    "pactr": "PACTR",
}


@dataclass(frozen=True)
class Identifier:
    pmid: int
    registry: str
    identifier: str      # normalized form used for deduplication
    source: str          # databank | title | abstract
    raw: str             # text as found

    def as_dict(self) -> dict:
        return asdict(self)


class IdentifierExtractor:
    def __init__(self, regex: dict[str, str], trial_registry_databanks: Iterable[str]):
        self.patterns = {name: re.compile(pattern, re.IGNORECASE) for name, pattern in regex.items()}
        self.trial_databanks = {d.lower() for d in trial_registry_databanks}

    # ---- normalization --------------------------------------------------------------------
    @staticmethod
    def normalize(registry: str, groups: tuple[str, ...] | str) -> tuple[str, str]:
        """Canonical (registry, identifier) for a regex match. Returns the possibly re-classified registry."""
        if isinstance(groups, str):
            groups = (groups,)
        g = ["".join(x.split()).upper() if x else "" for x in groups]
        if registry == "ClinicalTrials.gov":
            return registry, f"NCT{g[0]}"
        if registry == "ISRCTN":
            return registry, f"ISRCTN{g[0]}"
        if registry == "EudraCT":
            return registry, g[0]
        if registry == "DRKS":
            return registry, f"DRKS{g[0]}"
        if registry == "ACTRN":
            return registry, f"ACTRN{g[0]}"
        if registry == "ChiCTR":
            body = g[0].replace("--", "-")
            return registry, f"CHICTR-{body}" if "-" in body else f"CHICTR{body}"
        if registry == "UMIN":
            return registry, f"UMIN{g[0]}"
        if registry == "CTRI":
            return registry, f"CTRI/{g[0]}/{g[1]}/{g[2]}"
        if registry == "NTR":
            return registry, f"NTR{g[0]}"
        if registry == "NL":
            body = g[0].replace("-", "")
            return registry, f"NL-{body}" if body.startswith("OMON") else f"NL{body}"
        if registry == "IRCT":
            return registry, f"IRCT{g[0]}N{g[1]}"
        if registry == "JPRN":
            # JPRN prefixes the identifier of an underlying Japanese registry: reclassify so that
            # "JPRN-UMIN000012345" and "UMIN000012345" count as the same trial.
            inner = g[0]
            m = re.fullmatch(r"UMIN(\d{9})", inner)
            if m:
                return "UMIN", f"UMIN{m.group(1)}"
            m = re.fullmatch(r"JRCT([SC]?\d{9,10})", inner)
            if m:
                return "jRCT", f"JRCT{m.group(1)}"
            return registry, f"JPRN-{inner}"
        if registry == "jRCT":
            return registry, f"JRCT{g[0]}"
        if registry == "PACTR":
            return registry, f"PACTR{g[0]}"
        return registry, "".join(g)

    def normalize_databank(self, name: str, accession: str) -> tuple[str, str] | None:
        """Normalize a DataBankList entry, or None when the data bank is not a trial registry."""
        if name.lower() not in self.trial_databanks:
            return None
        acc = accession.strip()
        # Try the registry regexes first so that databank and text identifiers share one canonical form.
        for registry, pattern in self.patterns.items():
            m = pattern.search(acc)
            if m and m.group(0).strip().upper().replace(" ", "") == "".join(acc.split()).upper():
                return self.normalize(registry, m.groups())
        registry = DATABANK_TO_REGISTRY.get(name.lower(), name)
        return registry, "".join(acc.split()).upper()

    # ---- extraction -----------------------------------------------------------------------
    def from_text(self, pmid: int, text: str, source: str) -> list[Identifier]:
        found: list[Identifier] = []
        for registry, pattern in self.patterns.items():
            for m in pattern.finditer(text or ""):
                reg, ident = self.normalize(registry, m.groups())
                found.append(Identifier(pmid, reg, ident, source, m.group(0)))
        return found

    def from_record(self, rec: PubmedRecord) -> list[Identifier]:
        found: list[Identifier] = []
        for db in rec.databanks:
            norm = self.normalize_databank(db.name, db.accession)
            if norm:
                found.append(Identifier(rec.pmid, norm[0], norm[1], "databank", f"{db.name}:{db.accession}"))
        found.extend(self.from_text(rec.pmid, rec.title, "title"))
        found.extend(self.from_text(rec.pmid, rec.abstract, "abstract"))
        return _drop_nested(found)

    def extract(self, records: Iterable[PubmedRecord]) -> list[Identifier]:
        out: list[Identifier] = []
        for rec in records:
            out.extend(self.from_record(rec))
        return out


def _drop_nested(found: list[Identifier]) -> list[Identifier]:
    """Remove text hits that are substrings of another hit of the same record and source
    (e.g. the UMIN number inside 'JPRN-UMIN000012345' when both already normalize to the same id)."""
    keep: list[Identifier] = []
    for ident in found:
        nested = any(
            other is not ident and other.source == ident.source and other.raw != ident.raw and ident.raw in other.raw
            for other in found
        )
        if not nested:
            keep.append(ident)
    return keep


# ---------------------------------------------------------------------------------------------
# Deduplication and summaries
# ---------------------------------------------------------------------------------------------

def distinct_identifiers(identifiers: Iterable[Identifier]) -> set[str]:
    """Distinct normalized identifiers (within one field)."""
    return {i.identifier for i in identifiers}


def per_record(identifiers: Iterable[Identifier]) -> dict[int, set[str]]:
    out: dict[int, set[str]] = {}
    for i in identifiers:
        out.setdefault(i.pmid, set()).add(i.identifier)
    return out


def summarize(field: str, pmids: Iterable[int], identifiers: list[Identifier]) -> dict:
    """Descriptive pipeline summary for one field (analysis proper is Step 7, endpoint S8)."""
    pmids = sorted(set(int(p) for p in pmids))
    by_rec = per_record(identifiers)
    with_id = [p for p in pmids if p in by_rec]
    distinct = distinct_identifiers(identifiers)
    by_registry: dict[str, int] = {}
    for ident in {(i.registry, i.identifier) for i in identifiers}:
        by_registry[ident[0]] = by_registry.get(ident[0], 0) + 1
    return {
        "field": field,
        "records": len(pmids),
        "records_with_identifier": len(with_id),
        "records_without_identifier": len(pmids) - len(with_id),
        "distinct_identifiers": len(distinct),
        "distinct_identifiers_by_registry": dict(sorted(by_registry.items())),
        "upper_bound_trials": len(distinct) + (len(pmids) - len(with_id)),
        "note": "Distinct normalized identifiers; the same trial registered in two registries counts twice (Q23). Upper bound treats each record without identifier as its own trial (12.9).",
    }


def write_identifiers_csv(path: Path | str, field_by_pmid: dict[int, str], identifiers: list[Identifier]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["field", "pmid", "registry", "identifier", "source", "raw"])
        for i in sorted(identifiers, key=lambda x: (field_by_pmid.get(x.pmid, ""), x.pmid, x.registry, x.identifier, x.source)):
            w.writerow([field_by_pmid.get(i.pmid, ""), i.pmid, i.registry, i.identifier, i.source, i.raw])
