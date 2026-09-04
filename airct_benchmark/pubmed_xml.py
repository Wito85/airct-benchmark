"""Parse PubMed efetch XML (PubmedArticleSet) into plain records. Standard library only."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from typing import Iterable


@dataclass
class DataBankEntry:
    name: str
    accession: str


@dataclass
class PubmedRecord:
    pmid: int
    title: str = ""
    abstract: str = ""
    journal: str = ""
    journal_iso: str = ""
    year: str = ""
    publication_types: list[str] = field(default_factory=list)
    mesh_descriptors: list[str] = field(default_factory=list)
    databanks: list[DataBankEntry] = field(default_factory=list)
    doi: str = ""
    kind: str = "article"  # article | book

    def as_dict(self) -> dict:
        d = asdict(self)
        d["databanks"] = [asdict(x) for x in self.databanks]
        return d


def _text(elem: ET.Element | None) -> str:
    """All text of an element including inline markup (<i>, <sub>, ...), whitespace-normalized."""
    if elem is None:
        return ""
    return " ".join("".join(elem.itertext()).split())


def parse_pubmed_xml(xml_text: str) -> list[PubmedRecord]:
    """Parse one efetch response. Books (PubmedBookArticle) are returned with kind='book'."""
    root = ET.fromstring(xml_text)
    records: list[PubmedRecord] = []
    for art in root.findall("PubmedArticle"):
        mc = art.find("MedlineCitation")
        if mc is None:
            continue
        pmid_el = mc.find("PMID")
        if pmid_el is None or not (pmid_el.text or "").strip().isdigit():
            continue
        rec = PubmedRecord(pmid=int(pmid_el.text.strip()))
        article = mc.find("Article")
        if article is not None:
            rec.title = _text(article.find("ArticleTitle"))
            abstract = article.find("Abstract")
            if abstract is not None:
                parts = []
                for at in abstract.findall("AbstractText"):
                    label = at.get("Label")
                    txt = _text(at)
                    parts.append(f"{label}: {txt}" if label else txt)
                rec.abstract = " ".join(p for p in parts if p)
            journal = article.find("Journal")
            if journal is not None:
                rec.journal = _text(journal.find("Title"))
                rec.journal_iso = _text(journal.find("ISOAbbreviation"))
                pubdate = journal.find("JournalIssue/PubDate")
                if pubdate is not None:
                    year = _text(pubdate.find("Year"))
                    if not year:
                        medline_date = _text(pubdate.find("MedlineDate"))
                        year = medline_date[:4] if medline_date[:4].isdigit() else medline_date
                    rec.year = year
            if not rec.year:
                rec.year = _text(article.find("ArticleDate/Year"))
            rec.publication_types = [_text(pt) for pt in article.findall("PublicationTypeList/PublicationType")]
            for db in article.findall("DataBankList/DataBank"):
                name = _text(db.find("DataBankName"))
                for acc in db.findall("AccessionNumberList/AccessionNumber"):
                    rec.databanks.append(DataBankEntry(name, _text(acc)))
        rec.mesh_descriptors = [_text(mh.find("DescriptorName")) for mh in mc.findall("MeshHeadingList/MeshHeading")]
        for aid in art.findall("PubmedData/ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi":
                rec.doi = _text(aid)
        records.append(rec)
    for book in root.findall("PubmedBookArticle"):
        pmid_el = book.find("BookDocument/PMID")
        if pmid_el is not None and (pmid_el.text or "").strip().isdigit():
            rec = PubmedRecord(pmid=int(pmid_el.text.strip()), kind="book")
            rec.title = _text(book.find("BookDocument/ArticleTitle")) or _text(book.find("BookDocument/Book/BookTitle"))
            records.append(rec)
    return records


def returned_pmids(xml_text: str) -> set[int]:
    return {r.pmid for r in parse_pubmed_xml(xml_text)}


def parse_many(xml_texts: Iterable[str]) -> dict[int, PubmedRecord]:
    """Parse several efetch responses into a PMID-keyed dict (later duplicates win)."""
    out: dict[int, PubmedRecord] = {}
    for xml_text in xml_texts:
        for rec in parse_pubmed_xml(xml_text):
            out[rec.pmid] = rec
    return out
