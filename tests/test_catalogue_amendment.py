"""Structure of the catalogue addendum of Amendment v3.0 and of the GBD panel file.

The registered catalogue of tag v1.0 must stay an unchanged prefix of config/catalogue.yaml and
nothing after it may change a registered section; the addendum may only combine registered
components; the panel file must be consistent with both."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
import yaml

from airct_benchmark.catalogue import (
    ADDENDUM_KEYS,
    AMENDMENT_FAMILY_CODES,
    DEFAULT_CATALOGUE_PATH,
    GBD_EXPRESSION_RE,
    PROTECTED_FIELD,
    REGISTERED_PREFIX_CHARS,
    REGISTERED_PREFIX_SHA256,
    CatalogueError,
    load_catalogue,
    mesh_headings,
    normalise_heading,
)
from conftest import FIXTURE_PANEL

# SHA-256 of config/catalogue.yaml of tag v1.0 (b68eb65), computed from a checkout of that tag.
V1_0_CATALOGUE_SHA256 = "f58bbbe612bab8fff2649aacff5b3b8ae85fc0c2b1803658bb187ac17982d394"
V1_0_CATALOGUE_CHARS = 20150
REGISTERED_PART = "the registered part of config/catalogue.yaml"


def write(tmp_path: Path, text: str, name: str = "catalogue.yaml") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def panel_with(tmp_path: Path, edit) -> Path:
    raw = yaml.safe_load(FIXTURE_PANEL.read_text(encoding="utf-8"))
    edit(raw)
    return write(tmp_path, yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), "panel.yaml")


# ---- the registered catalogue -------------------------------------------------------------------------

def test_registered_catalogue_of_tag_v1_0_is_an_unchanged_prefix(catalogue):
    text = DEFAULT_CATALOGUE_PATH.read_text(encoding="utf-8")
    assert (REGISTERED_PREFIX_CHARS, REGISTERED_PREFIX_SHA256) == (V1_0_CATALOGUE_CHARS, V1_0_CATALOGUE_SHA256)   # pinned in code
    assert hashlib.sha256(text[:V1_0_CATALOGUE_CHARS].encode("utf-8")).hexdigest() == V1_0_CATALOGUE_SHA256
    assert catalogue.amendment["registered_prefix_chars"] == V1_0_CATALOGUE_CHARS
    assert catalogue.amendment["registered_prefix_sha256"] == V1_0_CATALOGUE_SHA256
    registered = yaml.safe_load(text[:V1_0_CATALOGUE_CHARS])
    assert not [k for k in registered if k.startswith("amendment")]
    assert [k for k in catalogue.raw if k not in registered] == ADDENDUM_KEYS
    for key, value in registered.items():
        assert catalogue.raw[key] == value, key          # no registered section is redefined further down


def test_any_edit_of_the_registered_part_is_refused(tmp_path, catalogue):
    text = catalogue.text
    for old, new in (('"Stroke"[Mesh]', '"Stroke"[Majr]'), ("reference_count: 18723", "reference_count: 18724"),
                     ("# Q13: study window", "# Q13: study window "), ("# Q13: study window", "# Q13: study window (edited)")):
        assert old in text[:V1_0_CATALOGUE_CHARS]
        with pytest.raises(CatalogueError, match=REGISTERED_PART):
            load_catalogue(write(tmp_path, text.replace(old, new, 1)), FIXTURE_PANEL)


def test_the_file_cannot_certify_an_edited_registered_part(tmp_path, catalogue):
    """Length and hash of the registered part are constants of the code. Rewriting the values that
    the file states about itself does not make an edited catalogue acceptable."""
    edited = catalogue.text.replace('"Stroke"[Mesh]', '"Stroke"[Majr]', 1)
    new_hash = hashlib.sha256(edited[:V1_0_CATALOGUE_CHARS].encode("utf-8")).hexdigest()
    with pytest.raises(CatalogueError, match=REGISTERED_PART):
        load_catalogue(write(tmp_path, edited.replace(V1_0_CATALOGUE_SHA256, new_hash)), FIXTURE_PANEL)
    with pytest.raises(CatalogueError, match="must state the values of tag v1.0"):
        load_catalogue(write(tmp_path, catalogue.text.replace("registered_prefix_chars: 20150", "registered_prefix_chars: 0")), FIXTURE_PANEL)


def test_text_after_the_registered_part_cannot_change_a_registered_section(tmp_path, catalogue):
    """YAML would let a repeated key win silently: a second 'smoke_test', 'freeze' or 'fields' block
    appended to the file would replace the registered one while the registered text stays intact."""
    text = catalogue.text
    appended = {
        "\nsmoke_test:\n  field: 'DM'\n  family: 'A'\n  metric: 'den'\n  year: 2024\n  reference_count: 1\n  reference_source: 'x'\n": "duplicate key 'smoke_test'",
        "\nfreeze:\n  date: '2026-01-01'\n  runs: ['A', 'B']\n  csv_name_template: 'x'\n": "duplicate key 'freeze'",
        "\nfields:\n  AI: {mesh: '\"Artificial Intelligence\"[Mesh]'}\n": "duplicate key 'fields'",
        "\nextra_section:\n  anything: 1\n": "unexpected top-level sections",
    }
    for block, message in appended.items():
        with pytest.raises(CatalogueError, match=message):
            load_catalogue(write(tmp_path, text + block), FIXTURE_PANEL)
    # a repeated family inside the addendum is refused as well
    doubled = text.replace("  DC:\n    use: 'overlap Clinical Trial numerators (S4)'", "  DB:\n    use: 'overlap Clinical Trial numerators (S4)'", 1)
    with pytest.raises(CatalogueError, match="duplicate key 'DB'"):
        load_catalogue(write(tmp_path, doubled), FIXTURE_PANEL)


# ---- the addendum -------------------------------------------------------------------------------------

def test_addendum_templates_must_follow_the_rules_of_section_4(tmp_path, catalogue):
    text = catalogue.text

    def refused(old: str, new: str, match: str) -> None:
        assert text.count(old) >= 1, old
        with pytest.raises(CatalogueError, match=match):
            load_catalogue(write(tmp_path, text.replace(old, new, 1)), FIXTURE_PANEL)

    # the RCT variant must be the base template with the RCT clause directly before the year clause
    refused('''      rct: '{HEADING} AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND {YEAR}'
  ME:''', '''      rct: '{HEADING} AND "Humans"[Mesh] AND "Artificial Intelligence"[Mesh] AND "Randomized Controlled Trial"[pt] AND {YEAR}'
  ME:''', "is not 'the same with RCT'")
    # a string that is not a registered component cannot enter a template
    refused('''ct: '{F} AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND "Clinical Trial"[pt] AND {YEAR}\'''',
            '''ct: '{F} AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND "Controlled Clinical Trial"[pt] AND {YEAR}\'''',
            "neither a registered component nor a connector")
    # the year clause is always last
    refused('''ai_den: '"Stroke"[Mesh] AND "Artificial Intelligence"[Mesh] AND {YEAR}\'''',
            '''ai_den: '{YEAR} AND "Stroke"[Mesh] AND "Artificial Intelligence"[Mesh]\'''', "year clause must be last")
    # AI_TIAB_TERMS is the registered text-word expression of AI
    refused('''AI_TIAB_TERMS: '("artificial intelligence"[tiab] OR''', '''AI_TIAB_TERMS: '("artificial-intelligence"[tiab] OR''', "AI_TIAB_TERMS must equal")
    # family codes and their order are those of the amendment
    refused("  DC:\n    use:", "  DX:\n    use:", "differ from the amendment")
    # sampling seed and the registered smoke cell of the syntax check cannot be changed
    refused("amendment_sampling:\n  seed: 20260904", "amendment_sampling:\n  seed: 20260905", "seed must be 20260904")
    refused("amendment_syntax_check:\n  year: 2015", "amendment_syntax_check:\n  year: 2024", "registered smoke year")
    refused("  stand_in_field: DM", "  stand_in_field: MI", "registered smoke year and smoke field")
    assert list(catalogue.amendment_families) == AMENDMENT_FAMILY_CODES


def test_metric_names_and_templates_cannot_be_exchanged(tmp_path, catalogue):
    """Two exchanged templates would both still stand in the amendment text; the name of a metric
    (ai..., nonai...) must say what its template selects."""
    text = catalogue.text
    s_ai = next(l for l in text.split("\n") if l.startswith("      S_ai: "))
    s_nonai = next(l for l in text.split("\n") if l.startswith("      S_nonai: "))
    swapped = text.replace(s_ai, "@@").replace(s_nonai, s_ai.replace("S_ai:", "S_nonai:")).replace("@@", s_nonai.replace("S_nonai:", "S_ai:"))
    assert swapped != text
    with pytest.raises(CatalogueError, match="family RS metric S_(ai|nonai)"):
        load_catalogue(write(tmp_path, swapped), FIXTURE_PANEL)
    kv = text.index("  KV:")
    ai = next(l for l in text[kv:].split("\n") if l.startswith("      ai_den: "))
    with pytest.raises(CatalogueError, match="family KV metric ai_den: an ai metric must begin with"):
        load_catalogue(write(tmp_path, text.replace(ai, ai.replace('\'"Stroke"[Mesh] AND "Artificial Intelligence"[Mesh]',
                                                                   '\'("Stroke"[Mesh] NOT "Artificial Intelligence"[Mesh])'))), FIXTURE_PANEL)


def test_syntax_check_plan_cannot_hold_trial_numerators_or_another_protected_field(tmp_path, catalogue):
    """Amendment v3.0, Sections 1.4 and 8.2: no within-field RCT count is viewed before the freeze run."""
    text = catalogue.text
    plan = catalogue.amendment_syntax_check
    for c in plan["compositions"]:
        template = catalogue.amendment_families[c["family"]]["metrics"][c["metric"]]
        assert ' AND "Randomized Controlled Trial"[pt]' not in template and ' AND "Clinical Trial"[pt]' not in template
    assert {c["family"] for c in plan["compositions"]} == {"DV", "QV", "WV", "KV", "RS"}
    assert [f"{a['family']}/{a['metric']}" for a in plan["anchors"]] == ["A/den", "E/den", "K/den", "R/S"]
    assert plan["replaced_field"] == PROTECTED_FIELD == "STROKE"

    def refused(old: str, new: str, match: str) -> None:
        assert text.count(old) == 1, old
        with pytest.raises(CatalogueError, match=match):
            load_catalogue(write(tmp_path, text.replace(old, new)), FIXTURE_PANEL)

    first = "    - {family: DV, metric: ai_vocab_den}\n"
    for family, metric in (("DB", "rct"), ("DC", "ct"), ("JV", "ai_rct_noprot"), ("JV", "nonai_rct_noprot"), ("DV", "ai_vocab_rct"), ("KV", "nonai_rct")):
        refused(first, f"    - {{family: {family}, metric: {metric}}}\n" + first, "within-field trial numerator")
    refused("    - {family: A, metric: den}\n", "    - {family: A, metric: den}\n    - {family: B, metric: rct}\n", "RCT numerator")
    refused("    - {family: A, metric: den}\n", "    - {family: A, metric: den}\n    - {family: C, metric: ct}\n", "no value disclosed in Q18")
    refused("  replaced_field: STROKE", "  replaced_field: MI", "replaced_field must be STROKE")


# ---- the GBD panel file -----------------------------------------------------------------------------

def test_gbd_panel_file_is_validated(tmp_path, catalogue):
    def refused(edit, match: str) -> None:
        with pytest.raises(CatalogueError, match=match):
            load_catalogue(gbd_panel_path=panel_with(tmp_path, edit))

    refused(lambda r: r.update(status="draft"), "status must be 'final' or 'provisional'")
    refused(lambda r: r["members"].pop(), "exactly 20 members")
    refused(lambda r: r["members"].append({**r["members"][-1], "rank": 99, "key": "GBD_EXTRA", "expression": '"Asthma"[Mesh]'}), "exactly 20 members")
    refused(lambda r: r["members"][5].update(rank=1), "ascending rank order")
    refused(lambda r: r["members"][5].update(key=r["members"][6]["key"]), "keys must be unique")
    refused(lambda r: r["members"][5].update(expression=r["members"][6]["expression"]), "share one expression")
    refused(lambda r: r["members"][5].update(expression=r["members"][6]["expression"].lower().replace("[mesh]", "[Mesh]")), "share one expression|another spelling")
    refused(lambda r: r["members"][5].update(expression="Malaria[Mesh]"), "is neither")
    refused(lambda r: r["members"][5].update(expression='"Malaria"[Mesh] OR "Tuberculosis"[Mesh]'), "is neither")
    refused(lambda r: r["members"][5].update(key="MALARIA"), "not of the form GBD_")
    refused(lambda r: r["members"][5].pop("expression"), "lacks a field or has a malformed value")
    refused(lambda r: r["members"][5].update(rank="seven"), "lacks a field or has a malformed value")
    # a member with the expression of a named field must share that field's cells
    refused(lambda r: r["members"][2].update(shared_with=None), "set shared_with")
    refused(lambda r: r["members"][2].update(shared_with="DM"), "differs from the named field DM")
    refused(lambda r: r["members"][5].update(expression='"Myocardial Infarction"[Mesh]'), "set shared_with")
    refused(lambda r: r["members"][5].update(shared_with="AI"), "one of the nine comparators")
    # COVID-19 is a named field with the year window 2020 to 2024: as a panel member it shares that window and has no trajectory
    refused(lambda r: r["members"][5].update(expression='"COVID-19"[Mesh]', mesh_ui="D000086382", shared_with="COVID", in_trajectory=True),
            "must not be part of the trajectory")
    refused(lambda r: r["members"][5].update(expression='"COVID-19"[Mesh]', mesh_ui="D000086382", shared_with=None), "set shared_with")
    refused(lambda r: r["members"][5].update(expression='"SARS-CoV-2 Infection"[Mesh]', mesh_ui="D000086382"),
            "has the MeSH unique identifier D000086382 of the named field COVID")
    with pytest.raises(CatalogueError, match="GBD panel file not found"):
        load_catalogue(gbd_panel_path=tmp_path / "missing.yaml")
    with pytest.raises(CatalogueError, match="duplicate key 'status'"):
        load_catalogue(gbd_panel_path=write(tmp_path, FIXTURE_PANEL.read_text(encoding="utf-8") + "status: provisional\n", "twice.yaml"))

    # a provisional panel may be shorter (development), but never longer than 20
    short = load_catalogue(gbd_panel_path=panel_with(tmp_path, lambda r: (r.update(status="provisional"), r["members"].pop())))
    assert short.gbd_status == "provisional" and not short.gbd_is_final and len(short.gbd_panel()) == 19
    assert catalogue.gbd_is_final and catalogue.gbd_is_test_fixture and len(catalogue.gbd_sha256()) == 64


def test_a_named_field_cannot_enter_the_panel_under_another_spelling_or_name(tmp_path):
    """PubMed ignores case and blanks in a heading and maps another name of a descriptor (an entry
    term) to the descriptor. Stroke written differently would be queried as a GBD member, also in
    the syntax check of publication year 2015."""
    def refused(edit, match: str) -> None:
        with pytest.raises(CatalogueError, match=match):
            load_catalogue(gbd_panel_path=panel_with(tmp_path, edit))

    refused(lambda r: r["members"][2].update(expression='"stroke"[Mesh]', shared_with=None), "another spelling")
    refused(lambda r: r["members"][2].update(expression='"Stroke "[Mesh]', shared_with=None), "another spelling|is neither")
    refused(lambda r: r["members"][5].update(expression='("Cerebrovascular Disorders"[Mesh] NOT "stroke"[Mesh])'), "another spelling")
    refused(lambda r: r["members"][5].update(expression='"diabetes mellitus"[Mesh]'), "another spelling|share one expression")
    refused(lambda r: r["members"][4].update(expression='"diabetes mellitus"[Mesh]', shared_with=None), "another spelling")
    # an entry term of Stroke: another string, the same descriptor (same MeSH unique identifier)
    refused(lambda r: r["members"][2].update(expression='"Cerebrovascular Accident"[Mesh]', shared_with=None), "unique identifier D020521 of the named field STROKE")
    assert normalise_heading("  Stroke ") == normalise_heading("STROKE") == "stroke"
    assert mesh_headings('("Pneumonia"[Mesh] NOT "COVID-19"[Mesh]) AND "Robotics"[Mesh:NoExp]') == ["Pneumonia", "COVID-19", "Robotics"]


def test_a_final_panel_must_carry_its_provenance(tmp_path):
    """Only the synthetic panel of the test suite may be final without raters and hashes."""
    def unmark(r):
        r.pop("test_fixture")

    with pytest.raises(CatalogueError, match="must state ranking_sha256"):
        load_catalogue(gbd_panel_path=panel_with(tmp_path, unmark))
    with pytest.raises(CatalogueError, match="must name the two raters"):
        load_catalogue(gbd_panel_path=panel_with(tmp_path, lambda r: (unmark(r), r["source"].update(raters=""))))
    complete = panel_with(tmp_path, lambda r: (unmark(r), r["source"].update(ranking_sha256="a" * 64, raw_export_sha256="b" * 64)))
    assert load_catalogue(gbd_panel_path=complete).gbd_is_final


def test_gbd_expression_forms():
    ok = ['"Malaria"[Mesh]', '"Infant, Newborn, Diseases"[Mesh]', '"Alzheimer Disease"[Mesh]', '"HIV Infections"[Mesh]',
          '"Anemia, Iron-Deficiency"[Mesh]', '"Pulmonary Disease, Chronic Obstructive"[Mesh]', '("Pneumonia"[Mesh] NOT "COVID-19"[Mesh])']
    bad = ['Malaria[Mesh]', '"Malaria"[Majr]', '"Malaria"[Mesh:NoExp]', '"Malaria"[Mesh] ', '"Malaria"[Mesh] NOT "COVID-19"[Mesh]',
           '("Malaria"[Mesh] OR "Tuberculosis"[Mesh])', '“Malaria”[Mesh]', '"Malaria"[MeSH Terms]', '("Pneumonia"[Mesh] NOT "COVID-19"[Mesh]) AND x']
    assert all(GBD_EXPRESSION_RE.match(e) for e in ok)
    assert not any(GBD_EXPRESSION_RE.match(e) for e in bad)


def test_repository_panel_file_loads_whatever_its_status():
    """config/gbd_panel.yaml is provisional until the export and the reconciliation are done and
    final afterwards; in both states it must load, and a final panel must be the real one."""
    cat = load_catalogue()
    assert cat.gbd_status in ("provisional", "final")
    assert not cat.gbd_is_test_fixture
    assert len(cat.gbd_panel()) <= 20
    if cat.gbd_is_final:
        assert len(cat.gbd_panel()) == 20
        assert re.fullmatch(r"[0-9a-f]{64}", cat.gbd_raw["source"]["mapping_table_sha256"])
        assert cat.gbd_raw["source"]["raters"]


def test_covid_19_as_a_panel_member_shares_the_cells_of_its_registered_window(tmp_path, catalogue):
    """Amendment v3.0, Section 5.2 (decision of 8 October 2026): COVID-19 is a GBD 2023 Level 3 cause and a named field
    with the year window 2020 to 2024. As a panel member it keeps the registered descriptor, shares the registered
    cells of that window and is not queried again; for the years before the window it has no cell."""
    from airct_benchmark.queries import build_amendment_count_queries, build_count_queries, build_syntax_check_plan, shared_cells

    def covid(raw: dict) -> None:
        member = raw["members"][5]
        assert not member["shared_with"]
        member.update(key="GBD_COVID_19", cause="COVID-19", expression='"COVID-19"[Mesh]', mesh_ui="D000086382",
                      date_introduced="2021-01-01", in_trajectory=False, shared_with="COVID", scope_relation="exact",
                      inclusion_note="Named field COVID; cells are shared for its registered year window 2020 to 2024.")

    cat = load_catalogue(gbd_panel_path=panel_with(tmp_path, covid))
    assert "GBD_COVID_19" not in cat.field_group("panel_gbd") and len(cat.field_group("panel_gbd")) == 17
    assert cat.amendment_named_field_ui["COVID"] == "D000086382"

    cells = [c for c in shared_cells(cat) if c["gbd_member"] == "GBD_COVID_19"]
    assert sorted({c["year"] for c in cells}) == [2020, 2021, 2022, 2023, 2024] and len(cells) == 6 * 5
    held = {(c["family"], c["metric"], c["year"]): c["held_by_query_id"] for c in cells}
    assert held[("GA", "den", 2020)] == "A_COVID_den_2020" and held[("GA", "rct", 2024)] == "B_COVID_rct_2024"
    assert held[("GD", "den", 2024)] == "D_COVID_overlap_2024" and held[("GD", "rct", 2024)] == "DB_COVID_rct_2024"
    assert held[("GE", "den", 2022)] == "E_COVID_den_2022" and held[("GE", "rct", 2022)] == "E_COVID_rct_2022"
    registered = {q.query_id: q.term for q in build_count_queries(cat)}
    assert all(registered[c["held_by_query_id"]] == c["query"] for c in cells)          # the shared strings are requested once, as registered

    # nothing is requested for the member itself, in no year; the other members are unchanged
    added = build_amendment_count_queries(cat)
    assert not [q for q in added if q.field == "GBD_COVID_19"]
    assert len(added) == len(build_amendment_count_queries(catalogue)) - 3 * 2 * 10
    descriptors = [i for i in build_syntax_check_plan(cat) if i.group == "gbd_descriptor"]
    assert len(descriptors) == 17 and not [i for i in descriptors if "GBD_COVID_19" in i.check_id]   # a registered descriptor is not checked again
