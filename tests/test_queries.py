import re

import pytest

from airct_benchmark.catalogue import CatalogueError, USED_FAMILY_LETTERS, load_catalogue
from airct_benchmark.queries import (
    WORKED_EXAMPLES,
    build_count_queries,
    build_list_queries,
    check_against_preregistration,
    count_summary,
    duplicate_terms,
    smoke_query,
    smoke_reference_count,
    year_from_term,
)
from conftest import FIXTURES

EXPECTED_PER_FAMILY = {
    "A": 95, "B": 95, "C": 95, "D": 85, "E": 255, "F": 20, "G": 110, "H": 80, "I": 40,
    "J": 95, "K": 190, "M": 420, "N": 180, "Q": 40, "R": 4, "U": 20, "W": 20, "Y": 190,
}


def test_catalogue_loads_and_families_match_registration(catalogue):
    assert sorted(catalogue.families) == sorted(USED_FAMILY_LETTERS)
    for letter in "PSTVXLO":
        assert letter not in catalogue.families
    assert len(catalogue.panel("disease")) == 21
    assert len(catalogue.panel("technology")) == 9
    assert catalogue.years_for_field("COVID") == list(range(2020, 2025))
    assert catalogue.years_for_field("AI") == list(range(2015, 2025))


def test_query_counts_per_family(catalogue):
    specs = build_count_queries(catalogue)
    summary = count_summary(specs)
    for fam, n in EXPECTED_PER_FAMILY.items():
        assert summary[fam] == n, fam
    assert summary["total"] == 2034
    assert len({s.query_id for s in specs}) == 2034


def test_worked_examples_reproduced_character_for_character(catalogue):
    specs = {(s.family, s.metric): s for s in build_count_queries(catalogue) if s.field == "AI" and s.year == 2024}
    for key, example in WORKED_EXAMPLES.items():
        assert specs[key].term == example, key


def test_every_query_ends_with_its_year_clause_and_has_no_double_spaces(catalogue):
    for s in build_count_queries(catalogue):
        assert s.term.endswith(f'AND ("{s.year}"[pdat])')
        assert year_from_term(s.term) == s.year
        assert "  " not in s.term
        assert "{" not in s.term and "}" not in s.term
        assert s.term.count("(") == s.term.count(")")


def test_covid_window_and_family_r_primary_year(catalogue):
    specs = build_count_queries(catalogue)
    covid_years = sorted({s.year for s in specs if s.field == "COVID"})
    assert covid_years == list(range(2020, 2025))
    r_years = {s.year for s in specs if s.family == "R"}
    assert r_years == {2024}
    assert {s.field for s in specs if s.family == "R"} == {"AI", "STROKE"}


def test_family_specific_composition(catalogue):
    by_id = {s.query_id: s.term for s in build_count_queries(catalogue)}
    assert by_id["E_STROKE_rct_2020"] == '("Stroke"[Mesh] NOT "Artificial Intelligence"[Mesh]) AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2020"[pdat])'
    assert by_id["K_DM_rct_2015"] == '"Diabetes Mellitus"[Mesh] AND "Humans"[Mesh] NOT (Review[pt] OR Editorial[pt] OR Letter[pt] OR Comment[pt] OR News[pt]) AND "Randomized Controlled Trial"[pt] AND ("2015"[pdat])'
    assert by_id["J_MI_rct_noprot_2024"] == '"Myocardial Infarction"[Mesh] AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] NOT "Clinical Trial Protocol"[pt] AND ("2024"[pdat])'
    assert by_id["I_STROKE_all_2019"] == '"stroke"[tiab] AND ("2019"[pdat])'
    assert by_id["I_STROKE_medline_2019"] == '"stroke"[tiab] AND medline[sb] AND ("2019"[pdat])'
    assert by_id["H_SUB_DL_rct_2019"] == '"Deep Learning"[Mesh] AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2019"[pdat])'
    assert by_id["F_AI_rct_2015"].startswith('("Artificial Intelligence"[Mesh:NoExp] OR "Expert Systems"[Mesh:NoExp]')
    assert by_id["F_AI_rct_2015"].endswith('"Robotics"[Mesh:NoExp]) AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2015"[pdat])')
    assert by_id["M_DIS_MENTAL_DISORDERS_den_2024"] == '"Mental Disorders"[Mesh] AND "Humans"[Mesh] AND ("2024"[pdat])'
    assert by_id["N_TECH_POINT_OF_CARE_TESTING_rct_2016"] == '"Point-of-Care Testing"[Mesh] AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2016"[pdat])'
    assert by_id["Y_TELE_prim_2022"] == '"Telemedicine"[Mesh] AND "Humans"[Mesh] AND "Journal Article"[pt] NOT (Review[pt] OR "Systematic Review"[pt] OR Meta-Analysis[pt] OR Editorial[pt] OR Comment[pt] OR Letter[pt]) AND ("2022"[pdat])'
    u = by_id["U_AI_den_2024"]
    assert u.startswith('"Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND ("Infections"[Mesh] OR "Neoplasms"[Mesh] OR')
    assert u.endswith('OR "Mental Disorders"[Mesh]) AND ("2024"[pdat])')
    assert u.count("[Mesh]") == 2 + 21


def test_registered_duplicates_across_families_are_kept(catalogue):
    dups = duplicate_terms(build_count_queries(catalogue))
    # CVD (A, B vs M) 20 cells plus four technology fields (A, B vs N) 80 cells
    assert len(dups) == 100
    for term, ids in dups.items():
        families = {i.split("_")[0] for i in ids}
        assert families <= {"A", "B", "M", "N"}


def test_list_queries_family_L(catalogue):
    specs = build_list_queries(catalogue)
    assert len(specs) == 6
    assert {s.year for s in specs} == {2024}
    by_id = {s.query_id: s.term for s in specs}
    assert by_id["L_STROKE_B_2024"] == '"Stroke"[Mesh] AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2024"[pdat])'
    assert by_id["L_AI_S_2024"] == WORKED_EXAMPLES[("R", "S")]
    assert by_id["L_STROKE_R_2024"] == '"Stroke"[Mesh] AND "Humans"[Mesh] AND medline[sb] NOT "Randomized Controlled Trial"[pt] NOT (randomized[tiab] OR randomised[tiab] OR randomly[tiab] OR placebo[tiab] OR trial[ti]) AND ("2024"[pdat])'


def test_smoke_query_is_diabetes_mellitus_2015_family_A(catalogue):
    s = smoke_query(catalogue)
    assert s.term == '"Diabetes Mellitus"[Mesh] AND "Humans"[Mesh] AND ("2015"[pdat])'
    assert smoke_reference_count(catalogue, "A", "den") == 18723
    assert smoke_reference_count(catalogue, "B", "rct") == 1405
    assert smoke_reference_count(catalogue, "R", "S") == 941
    b = smoke_query(catalogue, "B", "rct")
    assert b.term == '"Diabetes Mellitus"[Mesh] AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2015"[pdat])'
    r = smoke_query(catalogue, "R", "S")   # generic template applied to the smoke field, as in the Q18 check
    assert r.term == '"Diabetes Mellitus"[Mesh] AND "Humans"[Mesh] AND medline[sb] AND (randomized[tiab] OR randomised[tiab] OR randomly[tiab] OR placebo[tiab] OR trial[ti]) NOT "Randomized Controlled Trial"[pt] AND ("2015"[pdat])'
    with pytest.raises(CatalogueError):
        smoke_query(catalogue, "F", "den")  # AI-specific template: no Diabetes Mellitus smoke cell
    with pytest.raises(CatalogueError):
        smoke_query(catalogue, "U", "den")
    with pytest.raises(CatalogueError):
        smoke_query(catalogue, "W", "den")  # literal AI template without field placeholder: not a DM cell


def test_check_against_clean_excerpt_is_strict(catalogue):
    text = (FIXTURES / "preregistration_q12_excerpt.md").read_text(encoding="utf-8")
    report = check_against_preregistration(catalogue, text)
    assert report.strict_ok, [i.name for i in report.failures(strict=True)]


def test_check_against_raw_pdf_text_is_identical_up_to_line_wraps(catalogue):
    """The PDF rendering wraps long strings inside table cells; ignoring whitespace, every
    registered string of Q12 must be found in the registration text as distributed."""
    text = (FIXTURES / "preregistration_v2_0_pdf_text_p3-6.txt").read_text(encoding="utf-8")
    report = check_against_preregistration(catalogue, text)
    assert report.lenient_ok, [i.name for i in report.failures(strict=False)]


def test_check_detects_a_single_character_change(catalogue):
    text = (FIXTURES / "preregistration_q12_excerpt.md").read_text(encoding="utf-8")
    mutated = text.replace('"Randomized Controlled Trial"[pt]', '"Randomised Controlled Trial"[pt]')
    report = check_against_preregistration(catalogue, mutated)
    assert not report.strict_ok
    assert not report.lenient_ok
    names = {i.name for i in report.failures(strict=False)}
    assert "12.4 N_RCT" in names


def test_catalogue_validation_rejects_tampering(tmp_path, catalogue):
    bad = catalogue.text.replace("max_attempts: 6", "max_attempts: 7")
    p = tmp_path / "bad.yaml"
    p.write_text(bad, encoding="utf-8")
    with pytest.raises(CatalogueError):
        load_catalogue(p)
    bad2 = re.sub(r"(den: '\{F\} AND \"Humans\"\[Mesh\] AND \{YEAR\}')", "den: '{YEAR} AND {F}'", catalogue.text, count=1)
    p2 = tmp_path / "bad2.yaml"
    p2.write_text(bad2, encoding="utf-8")
    with pytest.raises(CatalogueError):
        load_catalogue(p2)
