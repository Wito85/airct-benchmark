import hashlib
import re

import pytest

from airct_benchmark.catalogue import AMENDMENT_FAMILY_CODES, CatalogueError, USED_FAMILY_LETTERS, load_catalogue
from airct_benchmark.queries import (
    WORKED_EXAMPLES,
    WORKED_EXAMPLES_AMENDMENT,
    build_amendment_count_queries,
    build_count_queries,
    build_list_queries,
    build_list_specs,
    build_registered_count_queries,
    build_registered_list_queries,
    build_syntax_check_plan,
    check_against_amendment,
    check_against_preregistration,
    count_summary,
    duplicate_terms,
    shared_cells,
    smoke_query,
    smoke_reference_count,
    syntax_check_violation,
    year_from_term,
)
from conftest import FIXTURE_AMENDMENT, FIXTURE_PANEL, FIXTURES

EXPECTED_PER_FAMILY = {
    "A": 95, "B": 95, "C": 95, "D": 85, "E": 255, "F": 20, "G": 110, "H": 80, "I": 40,
    "J": 95, "K": 190, "M": 420, "N": 180, "Q": 40, "R": 4, "U": 20, "W": 20, "Y": 190,
}
# Amendment v3.0, Section 4. GA, GD, GE: 18 queried members (20 minus Stroke and Diabetes Mellitus,
# whose cells are shared with the registered families) x 2 metrics x 10 years.
EXPECTED_PER_AMENDMENT_FAMILY = {
    "DB": 85, "DC": 85, "MD": 420, "ME": 420, "GA": 360, "GD": 360, "GE": 360,
    "DV": 80, "QV": 40, "WV": 20, "KV": 40, "JV": 20, "RS": 2,
}
# SHA-256 of the query list of tag v1.0 (b68eb65), one line per query: id, family, field, year,
# metric, term, tab separated. Computed from a checkout of tag v1.0 on 7 October 2026.
V1_0_COUNT_QUERIES_SHA256 = "6c3f367f7f4d858939314c2c873aee64a394dedd369915221e5119082a3f9882"
V1_0_LIST_QUERIES_SHA256 = "b37945a83f8d9737f6f92b12f73e43d3afcc4830ee14c73a1bd0b7a59e38f8de"


def _digest(specs) -> str:
    blob = "\n".join(f"{s.query_id}\t{s.family}\t{s.field}\t{s.year}\t{s.metric}\t{s.term}" for s in specs) + "\n"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


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
    for fam, n in {**EXPECTED_PER_FAMILY, **EXPECTED_PER_AMENDMENT_FAMILY}.items():
        assert summary[fam] == n, fam
    assert sum(EXPECTED_PER_FAMILY.values()) == 2034 and sum(EXPECTED_PER_AMENDMENT_FAMILY.values()) == 2292
    assert summary["total"] == 2034 + 2292 == 4326
    assert len({s.query_id for s in specs}) == 4326
    assert set(summary) - {"total"} == set(EXPECTED_PER_FAMILY) | set(EXPECTED_PER_AMENDMENT_FAMILY)


def test_registered_block_is_the_query_list_of_tag_v1_0_and_comes_first(catalogue):
    """The amendment adds queries; it must not change, reorder or drop a single registered one."""
    registered = build_registered_count_queries(catalogue)
    assert len(registered) == 2034
    assert _digest(registered) == V1_0_COUNT_QUERIES_SHA256
    everything = build_count_queries(catalogue)
    assert everything[:2034] == registered
    assert everything[2034:] == build_amendment_count_queries(catalogue)
    assert [s.family for s in everything[2034:]][0] == "DB"
    seen = []
    for s in everything[2034:]:
        if s.family not in seen:
            seen.append(s.family)
    assert seen == AMENDMENT_FAMILY_CODES
    assert _digest(build_registered_list_queries(catalogue)) == V1_0_LIST_QUERIES_SHA256
    assert build_list_queries(catalogue)[:6] == build_registered_list_queries(catalogue)


def test_family_restriction_keeps_the_fixed_order_and_rejects_unknown_codes(catalogue):
    specs = build_count_queries(catalogue, ["GA", "B", "DB", "A"])
    assert [f for f in dict.fromkeys(s.family for s in specs)] == ["A", "B", "DB", "GA"]
    assert len(specs) == 95 + 95 + 85 + 360
    with pytest.raises(CatalogueError):
        build_count_queries(catalogue, ["A", "ZZ"])


def test_worked_examples_reproduced_character_for_character(catalogue):
    specs = {(s.family, s.metric): s for s in build_count_queries(catalogue) if s.field == "AI" and s.year == 2024}
    for key, example in WORKED_EXAMPLES.items():
        assert specs[key].term == example, key


def test_amendment_worked_examples_reproduced_character_for_character(catalogue):
    by_id = {s.query_id: s.term for s in build_count_queries(catalogue)}
    assert by_id["DB_STROKE_rct_2024"] == WORKED_EXAMPLES_AMENDMENT[("DB", "STROKE", "rct")]
    assert by_id["E_STROKE_rct_2024"] == WORKED_EXAMPLES_AMENDMENT[("E", "STROKE", "rct")]
    assert by_id["D_STROKE_overlap_2024"] == WORKED_EXAMPLES_AMENDMENT[("D", "STROKE", "overlap")]
    assert by_id["MD_DIS_NEOPLASMS_den_2024"] == WORKED_EXAMPLES_AMENDMENT[("MD", "DIS_NEOPLASMS", "den")]
    # family GE, descriptor Diabetes Mellitus: a shared cell, held by the registered family E cell of DM
    assert "GE_GBD_DIABETES_MELLITUS_rct_2024" not in by_id
    assert by_id["E_DM_rct_2024"] == WORKED_EXAMPLES_AMENDMENT[("GE", "DM", "rct")]


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
    dups = duplicate_terms(build_registered_count_queries(catalogue))
    # CVD (A, B vs M) 20 cells plus four technology fields (A, B vs N) 80 cells
    assert len(dups) == 100
    for term, ids in dups.items():
        families = {i.split("_")[0] for i in ids}
        assert families <= {"A", "B", "M", "N"}


def test_amendment_adds_exactly_the_cardiovascular_heading_repeats(catalogue):
    """The Cardiovascular Diseases heading of families MD and ME repeats the CVD cells of
    families D, DB and E (40 strings). No other string is requested twice by the amendment."""
    dups = duplicate_terms(build_count_queries(catalogue))
    assert len(dups) == 100 + 40
    new = {t: ids for t, ids in dups.items() if any(i.split("_")[0] in AMENDMENT_FAMILY_CODES for i in ids)}
    assert len(new) == 40
    for term, ids in new.items():
        assert '"Cardiovascular Diseases"[Mesh]' in term
        assert len(ids) == 2 and {i.split("_")[0] for i in ids} in ({"D", "MD"}, {"DB", "MD"}, {"E", "ME"})


def test_list_queries_family_L(catalogue):
    specs = build_list_queries(catalogue)
    assert len(specs) == 10
    assert [s.family for s in specs] == ["L"] * 6 + ["LV"] * 4
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


# ---- Amendment v3.0: new families -----------------------------------------------------------------

def test_amendment_family_composition(catalogue):
    by_id = {s.query_id: s.term for s in build_count_queries(catalogue)}
    ai, hum, rct = '"Artificial Intelligence"[Mesh]', '"Humans"[Mesh]', '"Randomized Controlled Trial"[pt]'
    assert by_id["DB_COVID_rct_2020"] == f'"COVID-19"[Mesh] AND {ai} AND {hum} AND {rct} AND ("2020"[pdat])'
    assert "DB_COVID_rct_2019" not in by_id                      # COVID window 2020 to 2024
    assert by_id["DC_MI_ct_2018"] == f'"Myocardial Infarction"[Mesh] AND {ai} AND {hum} AND "Clinical Trial"[pt] AND ("2018"[pdat])'
    assert by_id["MD_DIS_MENTAL_DISORDERS_rct_2021"] == f'"Mental Disorders"[Mesh] AND {ai} AND {hum} AND {rct} AND ("2021"[pdat])'
    assert by_id["ME_DIS_NEOPLASMS_den_2015"] == f'("Neoplasms"[Mesh] NOT {ai}) AND {hum} AND ("2015"[pdat])'
    assert by_id["ME_DIS_NEOPLASMS_rct_2015"] == f'("Neoplasms"[Mesh] NOT {ai}) AND {hum} AND {rct} AND ("2015"[pdat])'
    assert by_id["GA_GBD_MALARIA_den_2024"] == f'"Malaria"[Mesh] AND {hum} AND ("2024"[pdat])'
    assert by_id["GA_GBD_MALARIA_rct_2024"] == f'"Malaria"[Mesh] AND {hum} AND {rct} AND ("2024"[pdat])'
    assert by_id["GD_GBD_HIV_AIDS_den_2016"] == f'"HIV Infections"[Mesh] AND {ai} AND {hum} AND ("2016"[pdat])'
    assert by_id["GE_GBD_TUBERCULOSIS_rct_2019"] == f'("Tuberculosis"[Mesh] NOT {ai}) AND {hum} AND {rct} AND ("2019"[pdat])'
    # a member whose expression removes a descriptor keeps its own parentheses inside every template
    lri = '("Pneumonia"[Mesh] NOT "COVID-19"[Mesh])'
    assert by_id["GA_GBD_LOWER_RESPIRATORY_INFECTIONS_den_2022"] == f'{lri} AND {hum} AND ("2022"[pdat])'
    assert by_id["GD_GBD_LOWER_RESPIRATORY_INFECTIONS_rct_2022"] == f'{lri} AND {ai} AND {hum} AND {rct} AND ("2022"[pdat])'
    assert by_id["GE_GBD_LOWER_RESPIRATORY_INFECTIONS_den_2022"] == f'({lri} NOT {ai}) AND {hum} AND ("2022"[pdat])'
    vocab = catalogue.auxiliary["F_AI_VOCAB2015"]
    tiab = catalogue.fields["AI"]["tiab"]
    assert by_id["DV_STROKE_ai_vocab_rct_2017"] == f'"Stroke"[Mesh] AND {vocab} AND {hum} AND {rct} AND ("2017"[pdat])'
    assert by_id["DV_STROKE_nonai_vocab_den_2017"] == f'("Stroke"[Mesh] NOT {vocab}) AND {hum} AND ("2017"[pdat])'
    assert by_id["DV_STROKE_ai_tiab_den_2024"] == f'"Stroke"[Mesh] AND medline[sb] AND {tiab} AND {hum} AND ("2024"[pdat])'
    assert by_id["DV_STROKE_nonai_tiab_rct_2024"] == f'("Stroke"[Mesh] AND medline[sb] NOT {tiab}) AND {hum} AND {rct} AND ("2024"[pdat])'
    assert by_id["QV_STROKE_ai_den_2024"] == f'"Stroke"[Mesh] AND {ai} AND ("2024"[pdat])'
    assert by_id["QV_STROKE_nonai_rct_2024"] == f'("Stroke"[Mesh] NOT {ai}) AND {rct} AND ("2024"[pdat])'
    assert by_id["WV_STROKE_ai_norob_rct_2023"] == f'"Stroke"[Mesh] AND ({ai} NOT "Robotics"[Mesh]) AND {hum} AND {rct} AND ("2023"[pdat])'
    x = "(Review[pt] OR Editorial[pt] OR Letter[pt] OR Comment[pt] OR News[pt])"
    assert by_id["KV_STROKE_ai_rct_2024"] == f'"Stroke"[Mesh] AND {ai} AND {hum} NOT {x} AND {rct} AND ("2024"[pdat])'
    assert by_id["KV_STROKE_nonai_den_2024"] == f'("Stroke"[Mesh] NOT {ai}) AND {hum} NOT {x} AND ("2024"[pdat])'
    assert by_id["JV_STROKE_ai_rct_noprot_2024"] == f'"Stroke"[Mesh] AND {ai} AND {hum} AND {rct} NOT "Clinical Trial Protocol"[pt] AND ("2024"[pdat])'
    assert by_id["JV_STROKE_nonai_rct_noprot_2015"] == f'("Stroke"[Mesh] NOT {ai}) AND {hum} AND {rct} NOT "Clinical Trial Protocol"[pt] AND ("2015"[pdat])'
    s = "(randomized[tiab] OR randomised[tiab] OR randomly[tiab] OR placebo[tiab] OR trial[ti])"
    assert by_id["RS_STROKE_S_ai_2024"] == f'"Stroke"[Mesh] AND {ai} AND {hum} AND medline[sb] AND {s} NOT {rct} AND ("2024"[pdat])'
    assert by_id["RS_STROKE_S_nonai_2024"] == f'("Stroke"[Mesh] NOT {ai}) AND {hum} AND medline[sb] AND {s} NOT {rct} AND ("2024"[pdat])'
    assert {s_.year for s_ in build_count_queries(catalogue) if s_.family == "RS"} == {2024}


def test_within_field_cells_partition_the_registered_cells_by_construction(catalogue):
    """For every comparator and year the amendment cell 'field AND AI' and the registered cell
    'field NOT AI' differ from the registered denominator only in the AI clause, so that
    D + E(den) = A and DB + E(rct) = B hold for any database state (integrity checks of the SAP)."""
    by_id = {s.query_id: s.term for s in build_count_queries(catalogue)}
    ai = '"Artificial Intelligence"[Mesh]'
    for f in catalogue.field_group("comparators"):
        mesh = catalogue.fields[f]["mesh"]
        for y in catalogue.years_for_field(f):
            assert by_id[f"A_{f}_den_{y}"] == by_id[f"D_{f}_overlap_{y}"].replace(f" AND {ai}", "", 1)
            assert by_id[f"E_{f}_den_{y}"] == by_id[f"A_{f}_den_{y}"].replace(mesh, f"({mesh} NOT {ai})", 1)
            assert by_id[f"B_{f}_rct_{y}"] == by_id[f"DB_{f}_rct_{y}"].replace(f" AND {ai}", "", 1)
            assert by_id[f"E_{f}_rct_{y}"] == by_id[f"B_{f}_rct_{y}"].replace(mesh, f"({mesh} NOT {ai})", 1)
    for m in catalogue.panel("disease"):
        for y in range(2015, 2025):
            assert by_id[f"M_{m.key}_den_{y}"] == by_id[f"MD_{m.key}_den_{y}"].replace(f" AND {ai}", "", 1)
            assert by_id[f"ME_{m.key}_rct_{y}"] == by_id[f"M_{m.key}_rct_{y}"].replace(m.mesh, f"({m.mesh} NOT {ai})", 1)
    for g in catalogue.gbd_panel():
        if g.shared_with:
            continue
        for y in range(2015, 2025):
            assert by_id[f"GA_{g.key}_den_{y}"] == by_id[f"GD_{g.key}_den_{y}"].replace(f" AND {ai}", "", 1)
            assert by_id[f"GE_{g.key}_rct_{y}"] == by_id[f"GA_{g.key}_rct_{y}"].replace(g.expression, f"({g.expression} NOT {ai})", 1)


def test_gbd_members_shared_with_named_fields_are_not_queried_again(catalogue):
    panel = catalogue.gbd_panel()
    assert len(panel) == 20
    shared = [m for m in panel if m.shared_with]
    assert [(m.key, m.shared_with) for m in shared] == [("GBD_STROKE", "STROKE"), ("GBD_DIABETES_MELLITUS", "DM")]
    assert len(catalogue.field_group("panel_gbd")) == 18
    queried_fields = {s.field for s in build_count_queries(catalogue) if s.family in ("GA", "GD", "GE")}
    assert "GBD_STROKE" not in queried_fields and "GBD_DIABETES_MELLITUS" not in queried_fields

    cells = shared_cells(catalogue)
    assert len(cells) == 2 * 3 * 2 * 10            # two members, three families, two metrics, ten years
    by_id = {s.query_id: s.term for s in build_count_queries(catalogue)}
    for c in cells:
        assert by_id[c["held_by_query_id"]] == c["query"]          # the holding cell is requested and identical
    target = {(c["family"], c["metric"]): (c["held_by_family"], c["held_by_metric"]) for c in cells}
    assert target == {("GA", "den"): ("A", "den"), ("GA", "rct"): ("B", "rct"), ("GD", "den"): ("D", "overlap"),
                      ("GD", "rct"): ("DB", "rct"), ("GE", "den"): ("E", "den"), ("GE", "rct"): ("E", "rct")}
    one = next(c for c in cells if c["gbd_member"] == "GBD_STROKE" and c["family"] == "GD" and c["metric"] == "rct" and c["year"] == 2024)
    assert one["held_by_query_id"] == "DB_STROKE_rct_2024"
    assert one["query"] == WORKED_EXAMPLES_AMENDMENT[("DB", "STROKE", "rct")]


def test_member_introduced_after_2015_is_flagged_but_still_retrieved_for_all_years(catalogue):
    late = catalogue.gbd_member("GBD_SYNTHETIC_CAUSE_TEST_FIXTURE")
    assert late.in_trajectory is False
    years = sorted({s.year for s in build_count_queries(catalogue) if s.field == late.key and s.family == "GA" and s.metric == "den"})
    assert years == list(range(2015, 2025))            # the panel rule of Q13 is applied in the analysis, not at retrieval


def test_list_queries_family_LV(catalogue):
    specs = {x.key: x for x in build_list_specs(catalogue)}
    assert list(specs) == ["B_AI", "B_STROKE", "S_AI", "S_STROKE", "R_AI", "R_STROKE",
                           "DB_STROKE", "ERCT_STROKE", "SAI_STROKE", "SNONAI_STROKE"]
    by_id = {s.query_id: s.term for s in build_count_queries(catalogue)}
    assert specs["DB_STROKE"].spec.query_id == "LV_STROKE_DB_2024" and specs["DB_STROKE"].spec.term == by_id["DB_STROKE_rct_2024"]
    assert specs["ERCT_STROKE"].spec.query_id == "LV_STROKE_ERCT_2024" and specs["ERCT_STROKE"].spec.term == by_id["E_STROKE_rct_2024"]
    assert specs["SAI_STROKE"].spec.term == by_id["RS_STROKE_S_ai_2024"]
    assert specs["SNONAI_STROKE"].spec.term == by_id["RS_STROKE_S_nonai_2024"]
    assert [specs[k].efetch for k in ("B_AI", "B_STROKE", "S_STROKE", "DB_STROKE")] == ["all", "all", "none", "sampled"]


# ---- Amendment v3.0: identity with the amendment text -------------------------------------------------

def amendment_check(cat, text: str):
    return check_against_amendment(cat, text, allow_test_fixture=True)


def failing(cat, text: str) -> set[str]:
    return {i.name.split(" (found")[0] for i in amendment_check(cat, text).failures(strict=False)}


def test_check_against_amendment_excerpt_is_strict(catalogue):
    report = amendment_check(catalogue, FIXTURE_AMENDMENT.read_text(encoding="utf-8"))
    assert report.strict_ok, [i.name for i in report.failures(strict=True)]
    kinds = [i.kind for i in report.items]
    assert {k: kinds.count(k) for k in dict.fromkeys(kinds)} == {
        "component": 1, "family_set": 1, "template": 20, "template_count": 13, "rct_marker": 13, "derived_rct_variant": 14,
        "worked_example": 5, "generated_equals_example": 5, "gbd_panel_status": 1, "gbd_panel_size": 1, "gbd_panel_row": 20,
        "gbd_panel_table": 1}
    assert len(report.items) == 95
    # outside the test suite the synthetic panel never passes
    real = check_against_amendment(catalogue, FIXTURE_AMENDMENT.read_text(encoding="utf-8"))
    assert [i.kind for i in real.failures(strict=False)] == ["gbd_panel_real"]


def test_check_against_amendment_detects_changes_in_the_text(catalogue):
    text = FIXTURE_AMENDMENT.read_text(encoding="utf-8")

    def changed(old: str, new: str) -> set[str]:
        assert text.count(old) == 1, old
        return failing(catalogue, text.replace(old, new))

    # one character in a template of Section 4
    assert changed('NOT "Clinical Trial Protocol"[pt] AND (...); ("Stroke"', 'NOT "Clinical Trial Protocols"[pt] AND (...); ("Stroke"') == {
        "Section 4 family JV ai_rct_noprot"}
    # a worked example
    assert changed('Family MD, heading Neoplasms: "Neoplasms"[Mesh] AND', 'Family MD, heading Neoplasms: "Neoplasm"[Mesh] AND') == {
        "Section 4 example MD/DIS_NEOPLASMS/den"}
    # the note "the same with RCT" removed from a family that has RCT variants, or added to one that has none
    assert changed('{G} AND "Humans"[Mesh] AND (...); the same with RCT | 20 GBD descriptors |', '{G} AND "Humans"[Mesh] AND (...) | 20 GBD descriptors |') == {
        "Section 4 row of family GA: note 'the same with RCT' present"}
    assert changed('"Clinical Trial"[pt] AND (...) | nine comparators |', '"Clinical Trial"[pt] AND (...); the same with RCT | nine comparators |') == {
        "Section 4 row of family DC: note 'the same with RCT' absent"}
    # an additional template in a row, a family missing, a family added
    assert "Section 4 row of family WV holds 1 template(s) and nothing else" in changed(
        '(E13) | "Stroke"[Mesh] AND ("Artificial Intelligence"[Mesh] NOT "Robotics"[Mesh])',
        '(E13) | "Stroke"[Mesh] AND "Robotics"[Mesh] AND (...); "Stroke"[Mesh] AND ("Artificial Intelligence"[Mesh] NOT "Robotics"[Mesh])')
    row_wv = next(l for l in text.split("\n") if l.startswith("| WV |"))
    assert any(n.startswith("Section 4 lists exactly the families") for n in failing(catalogue, text.replace(row_wv + "\n", "")))
    assert any(n.startswith("Section 4 lists exactly the families") for n in failing(catalogue, text.replace(row_wv, row_wv + "\n" + row_wv.replace("| WV |", "| ZZ |"))))
    # the two templates of a row exchanged
    row_qv = next(l for l in text.split("\n") if l.startswith("| QV |"))
    first, second = '"Stroke"[Mesh] AND "Artificial Intelligence"[Mesh] AND (...)', '("Stroke"[Mesh] NOT "Artificial Intelligence"[Mesh]) AND (...)'
    exchanged = row_qv.replace(first, "@@").replace(second, first).replace("@@", second)
    assert failing(catalogue, text.replace(row_qv, exchanged)) == {"Section 4 family QV ai_den", "Section 4 family QV nonai_den"}


def test_check_against_amendment_detects_changes_in_the_catalogue(tmp_path, catalogue):
    """A catalogue template that is only part of the template of the amendment, or has a leading
    blank, is found as a substring of the text; the row-by-row comparison refuses it."""
    text = FIXTURE_AMENDMENT.read_text(encoding="utf-8")

    def with_catalogue(old: str, new: str) -> set[str]:
        assert catalogue.text.count(old) == 1, old
        path = tmp_path / "catalogue.yaml"
        path.write_text(catalogue.text.replace(old, new), encoding="utf-8")
        return failing(load_catalogue(path, FIXTURE_PANEL), text)

    # family DC without its field: one field-independent query for all 85 cells
    assert "Section 4 family DC ct" in with_catalogue("""      ct: '{F} AND "Artificial Intelligence"[Mesh] AND""", """      ct: '"Artificial Intelligence"[Mesh] AND""")
    # family ME reduced to the human-subject clause
    names = with_catalogue("""      den: '({HEADING} NOT "Artificial Intelligence"[Mesh]) AND "Humans"[Mesh] AND {YEAR}'
      rct: '({HEADING} NOT "Artificial Intelligence"[Mesh]) AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND {YEAR}'""",
                           """      den: '"Humans"[Mesh] AND {YEAR}'
      rct: '"Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND {YEAR}'""")
    assert "Section 4 family ME den" in names
    # the same in a GBD family is refused even earlier: the shared cells are no longer identical to the cells that hold them
    with pytest.raises(CatalogueError, match="shared cell GA/den of GBD_STROKE"):
        with_catalogue("""      den: '{G} AND "Humans"[Mesh] AND {YEAR}'
      rct: '{G} AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND {YEAR}'""",
                       """      den: '"Humans"[Mesh] AND {YEAR}'
      rct: '"Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND {YEAR}'""")
    # a leading blank
    assert "Section 4 family DC ct" in with_catalogue("""      ct: '{F} AND "Artificial Intelligence"[Mesh] AND""", """      ct: ' {F} AND "Artificial Intelligence"[Mesh] AND""")
    with pytest.raises(CatalogueError, match="family WV metric ai_norob_den"):          # refused by the loader already
        with_catalogue("""ai_norob_den: '"Stroke"[Mesh] AND (""", """ai_norob_den: ' "Stroke"[Mesh] AND (""")


def test_check_against_amendment_compares_the_complete_panel_table(catalogue):
    text = FIXTURE_AMENDMENT.read_text(encoding="utf-8")
    row = next(l for l in text.split("\n") if l.startswith("| 15 | Malaria |"))

    def changed(new_row: str) -> set[str]:
        return failing(catalogue, text.replace(row, new_row))

    table = "Section 5 panel table has exactly these 20 rows and no other"
    member = "Section 5 panel row 13: GBD_MALARIA"
    assert changed(row.replace('"Malaria"[Mesh]', '"Malaria, Falciparum"[Mesh]')) == {member, table}      # the expression
    assert changed(row.replace("| 15 |", "| 16 |")) == {member, table}                                    # the rank
    assert changed(row.replace("D008288", "D000001")) == {member, table}                                  # the unique identifier
    assert changed(row.replace("| 1960 |", "| 2016 |")) == {member, table}                                # the year
    assert changed(row.replace("| queried |", "| shared with MI |")) == {member, table}                   # the cells
    assert changed(row + "\n" + row.replace("| 15 | Malaria |", "| 99 | Road injuries |")) >= {table}      # a row too many
    assert table in changed("")                                                                           # a row missing
    # the rows of the panel standing in another table as well do not make the panel table right
    assert table in failing(catalogue, text.replace(row, row.replace("| 15 |", "| 16 |")) + "\n\nAnother table:\n\n" + row + "\n")
    # two rows exchanged
    other = next(l for l in text.split("\n") if l.startswith("| 16 | Tracheal"))
    exchanged = text.replace(row, "@@").replace(other, row).replace("@@", other)
    assert failing(catalogue, exchanged) == {member, "Section 5 panel row 14: GBD_TRACHEAL_BRONCHUS_AND_LUNG_CANCER", table}


def test_check_against_amendment_requires_the_final_panel(tmp_path):
    provisional = tmp_path / "gbd_panel.yaml"
    provisional.write_text(FIXTURE_PANEL.read_text(encoding="utf-8").replace("status: final", "status: provisional"), encoding="utf-8")
    cat = load_catalogue(gbd_panel_path=provisional)
    report = amendment_check(cat, FIXTURE_AMENDMENT.read_text(encoding="utf-8"))
    assert not report.strict_ok
    assert [i.kind for i in report.failures(strict=False)] == ["gbd_panel_status"]


# ---- Amendment v3.0: syntax check plan (publication year 2015 only) -----------------------------------

def test_syntax_check_plan_is_2015_only_without_stroke_and_without_trial_numerators(catalogue):
    plan = build_syntax_check_plan(catalogue)
    groups = [it.group for it in plan]
    assert groups.count("anchor") == 4 and groups.count("composition") == 11 and groups.count("gbd_descriptor") == 18
    for it in plan:
        assert it.term.endswith('AND ("2015"[pdat])')
        assert it.term.count("[pdat]") == 1
        assert "stroke" not in it.term.lower()
        assert "2024" not in it.term
        assert syntax_check_violation(catalogue, it.term) is None
        # Amendment v3.0, Sections 1.4 and 8.2: no trial numerator within a field is viewed before the freeze run
        assert ' AND "Randomized Controlled Trial"[pt]' not in it.term and ' AND "Clinical Trial"[pt]' not in it.term
    by_id = {it.check_id: it for it in plan}
    assert not [k for k in by_id if k.split("/")[0] in ("DB", "DC", "JV", "B", "J")]
    assert by_id["A/den"].term == '"Diabetes Mellitus"[Mesh] AND "Humans"[Mesh] AND ("2015"[pdat])'
    assert by_id["A/den"].reference_count == 18723 and by_id["R/S"].reference_count == 941
    assert by_id["A/den"].catalogue_query_id == "A_DM_den_2015" and by_id["E/den"].catalogue_query_id == "E_DM_den_2015"
    assert by_id["R/S"].catalogue_query_id is None                      # family R is registered for AI and STROKE only
    # Stroke-only families are run with Diabetes Mellitus in place of Stroke; they are no catalogue cells
    assert by_id["KV/ai_den"].term == ('"Diabetes Mellitus"[Mesh] AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] NOT '
                                       '(Review[pt] OR Editorial[pt] OR Letter[pt] OR Comment[pt] OR News[pt]) AND ("2015"[pdat])')
    assert by_id["KV/ai_den"].catalogue_query_id is None
    assert by_id["RS/S_nonai"].term.startswith('("Diabetes Mellitus"[Mesh] NOT "Artificial Intelligence"[Mesh]) AND "Humans"[Mesh] AND medline[sb]')
    assert by_id["RS/S_nonai"].term.count("[pt]") == 1 and ' NOT "Randomized Controlled Trial"[pt] AND ' in by_id["RS/S_nonai"].term
    # one request per GBD descriptor that is new relative to v2.0; shared members are not checked again
    gbd = [it for it in plan if it.group == "gbd_descriptor"]
    assert all(it.catalogue_query_id == f"GA_{it.field}_den_2015" for it in gbd)
    assert "GA/den:GBD_STROKE" not in by_id and "GA/den:GBD_DIABETES_MELLITUS" not in by_id
    assert by_id["GA/den:GBD_MALARIA"].term == '"Malaria"[Mesh] AND "Humans"[Mesh] AND ("2015"[pdat])'


def test_syntax_check_rule_is_enforced_on_every_string(catalogue):
    ok = '"Malaria"[Mesh] AND "Humans"[Mesh] AND ("2015"[pdat])'
    assert syntax_check_violation(catalogue, ok) is None
    for bad in ('"Malaria"[Mesh] AND "Humans"[Mesh] AND ("2024"[pdat])',
                '"Malaria"[Mesh] AND ("2014"[pdat]) AND "Humans"[Mesh] AND ("2015"[pdat])',
                '"Malaria"[Mesh] AND "Humans"[Mesh] AND ("2015"[pdat]) OR ("2024"[pdat])',
                '"Malaria"[Mesh] AND "Humans"[Mesh] AND "2014:2024"[pdat] AND ("2015"[pdat])',
                '"Malaria"[Mesh] AND "Humans"[Mesh]'):
        assert "single publication year 2015" in syntax_check_violation(catalogue, bad), bad
    for bad in ('"Stroke"[Mesh] AND "Humans"[Mesh] AND ("2015"[pdat])', '"stroke"[Mesh] AND "Humans"[Mesh] AND ("2015"[pdat])',
                '"STROKE"[mesh] AND "Humans"[Mesh] AND ("2015"[pdat])', '" Stroke "[Mesh:NoExp] AND ("2015"[pdat])',
                '("Cerebrovascular Disorders"[Mesh] NOT "stroke"[Mesh]) AND "Humans"[Mesh] AND ("2015"[pdat])'):
        assert "STROKE heading" in syntax_check_violation(catalogue, bad), bad
