from airct_benchmark.identifiers import (
    IdentifierExtractor,
    distinct_identifiers,
    summarize,
    write_identifiers_csv,
)
from airct_benchmark.pubmed_xml import parse_pubmed_xml, parse_many, returned_pmids
from conftest import pubmed_article_xml, pubmed_set_xml


def make_extractor(catalogue) -> IdentifierExtractor:
    ids = catalogue.raw["identifiers"]
    return IdentifierExtractor(ids["regex"], ids["trial_registry_databanks"])


def test_databank_and_text_identifiers_are_normalized_and_deduplicated(catalogue):
    ex = make_extractor(catalogue)
    xml = pubmed_set_xml([
        pubmed_article_xml(
            101,
            title="A randomized trial of an AI triage tool (NCT01234567)",
            abstract="Registered at ClinicalTrials.gov, nct 01234567, and ISRCTN 12345678.",
            databanks=[("ClinicalTrials.gov", ["NCT01234567"]), ("GENBANK", ["AB123456"])],
        ),
    ])
    recs = parse_pubmed_xml(xml)
    found = ex.extract(recs)
    assert {i.identifier for i in found} == {"NCT01234567", "ISRCTN12345678"}
    sources = {(i.source, i.identifier) for i in found}
    assert ("databank", "NCT01234567") in sources
    assert ("title", "NCT01234567") in sources
    assert ("abstract", "NCT01234567") in sources
    assert ("abstract", "ISRCTN12345678") in sources
    assert all(i.registry != "GENBANK" for i in found)
    assert distinct_identifiers(found) == {"NCT01234567", "ISRCTN12345678"}


def test_every_registered_registry_pattern_matches_a_synthetic_example(catalogue):
    ex = make_extractor(catalogue)
    text = (
        "NCT12345678; ISRCTN87654321; EudraCT 2019-001234-56; DRKS00012345; ACTRN12619000123456; "
        "ChiCTR2000034567; ChiCTR-IOR-17012345; UMIN000012345; CTRI/2020/05/025123; NTR7890; "
        "NL8123; NL-OMON45678; IRCT20200101045678N1; JPRN-jRCTs031200123; PACTR202001234567890; "
        "jRCT1030200456"
    )
    found = ex.from_text(1, text, "abstract")
    got = {(i.registry, i.identifier) for i in found}
    expected = {
        ("ClinicalTrials.gov", "NCT12345678"),
        ("ISRCTN", "ISRCTN87654321"),
        ("EudraCT", "2019-001234-56"),
        ("DRKS", "DRKS00012345"),
        ("ACTRN", "ACTRN12619000123456"),
        ("ChiCTR", "CHICTR2000034567"),
        ("ChiCTR", "CHICTR-IOR-17012345"),
        ("UMIN", "UMIN000012345"),
        ("CTRI", "CTRI/2020/05/025123"),
        ("NTR", "NTR7890"),
        ("NL", "NL8123"),
        ("NL", "NL-OMON45678"),
        ("IRCT", "IRCT20200101045678N1"),
        ("jRCT", "JRCTS031200123"),
        ("PACTR", "PACTR202001234567890"),
        ("jRCT", "JRCT1030200456"),
    }
    assert expected <= got, expected - got


def test_jprn_prefixed_umin_is_reclassified_and_counted_once(catalogue):
    ex = make_extractor(catalogue)
    rec = parse_pubmed_xml(pubmed_set_xml([pubmed_article_xml(
        202, abstract="Registered as JPRN-UMIN000012345 (UMIN-CTR).",
        databanks=[("UMIN-CTR", ["UMIN000012345"])])]))[0]
    found = ex.from_record(rec)
    assert {i.identifier for i in found} == {"UMIN000012345"}
    assert {i.registry for i in found} == {"UMIN"}
    # the nested plain UMIN hit inside the JPRN string is not reported twice for the abstract
    abstract_hits = [i for i in found if i.source == "abstract"]
    assert len(abstract_hits) == 1
    assert abstract_hits[0].raw == "JPRN-UMIN000012345"


def test_case_and_whitespace_variants_normalize_to_one_identifier(catalogue):
    ex = make_extractor(catalogue)
    variants = ["NCT04567890", "nct04567890", "NCT 04567890", "NCT-04567890"]
    idents = {ex.from_text(1, v, "title")[0].identifier for v in variants}
    assert idents == {"NCT04567890"}
    d = ex.normalize_databank("ClinicalTrials.gov", " nct04567890 ")
    assert d == ("ClinicalTrials.gov", "NCT04567890")
    assert ex.normalize_databank("GENBANK", "NCT04567890") is None
    assert ex.normalize_databank("ISRCTN", "isrctn 99999999") == ("ISRCTN", "ISRCTN99999999")


def test_negative_cases_do_not_match(catalogue):
    ex = make_extractor(catalogue)
    text = (
        "NCT0123456 has only seven digits and NCT012345678 has nine. "
        "The compound TNCT01234567X is not an identifier. "
        "Grant number R01-2019-001234 and DOI 10.1000/2020-123456-789 are not EudraCT numbers. "
        "ISRCTN with no number, DRKS 1234, and UMIN 12345 are incomplete."
    )
    assert ex.from_text(1, text, "abstract") == []


def test_word_boundary_does_not_swallow_neighbouring_digits(catalogue):
    ex = make_extractor(catalogue)
    found = ex.from_text(1, "Trial NCT01234567.", "abstract")
    assert [i.identifier for i in found] == ["NCT01234567"]
    found2 = ex.from_text(1, "(ClinicalTrials.gov: NCT01234567; ISRCTN12345678).", "abstract")
    assert {i.identifier for i in found2} == {"NCT01234567", "ISRCTN12345678"}


def test_summary_and_csv(tmp_path, catalogue):
    ex = make_extractor(catalogue)
    xml = pubmed_set_xml([
        pubmed_article_xml(1, abstract="NCT00000001."),
        pubmed_article_xml(2, abstract="NCT00000001 (secondary publication)."),
        pubmed_article_xml(3, abstract="No registration reported."),
        pubmed_article_xml(4, abstract="ISRCTN00000004 and NCT00000004 (dual registration)."),
    ])
    recs = parse_pubmed_xml(xml)
    found = ex.extract(recs)
    s = summarize("AI", [r.pmid for r in recs], found)
    assert s["records"] == 4
    assert s["records_with_identifier"] == 3
    assert s["records_without_identifier"] == 1
    assert s["distinct_identifiers"] == 3
    assert s["distinct_identifiers_by_registry"] == {"ClinicalTrials.gov": 2, "ISRCTN": 1}
    assert s["upper_bound_trials"] == 4
    path = tmp_path / "ids.csv"
    write_identifiers_csv(path, {r.pmid: "AI" for r in recs}, found)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "field,pmid,registry,identifier,source,raw"
    assert len(lines) == 1 + len(found)


def test_pubmed_xml_parser_handles_inline_markup_books_and_missing_records():
    xml = pubmed_set_xml([
        pubmed_article_xml(11, title="Deep <i>learning</i> for <sub>2</sub> tasks", year="2024"),
    ]).replace("</PubmedArticleSet>", (
        '<PubmedBookArticle><BookDocument><PMID Version="1">12</PMID>'
        '<Book><BookTitle>Handbook</BookTitle></Book><ArticleTitle>Chapter one</ArticleTitle>'
        '</BookDocument></PubmedBookArticle></PubmedArticleSet>'
    ))
    recs = parse_pubmed_xml(xml)
    assert [r.pmid for r in recs] == [11, 12]
    assert recs[0].title == "Deep learning for 2 tasks"
    assert recs[0].abstract.startswith("BACKGROUND:")
    assert "Randomized Controlled Trial" in recs[0].publication_types
    assert recs[0].mesh_descriptors == ["Humans", "Artificial Intelligence"]
    assert recs[0].doi == "10.1000/test.11" and recs[0].year == "2024"
    assert recs[1].kind == "book" and recs[1].title == "Chapter one"
    assert returned_pmids(xml) == {11, 12}
    merged = parse_many([xml, pubmed_set_xml([pubmed_article_xml(13)])])
    assert set(merged) == {11, 12, 13}
