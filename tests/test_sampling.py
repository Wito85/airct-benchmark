import random

from airct_benchmark.sampling import (
    SEED,
    draw_all_cells,
    draw_cell,
    replace_missing,
    seeded_sequence,
    write_cell_csvs,
)


def test_seed_is_the_registered_one():
    assert SEED == 20260904


def test_seeded_sequence_equals_registered_call_on_sorted_list():
    pmids = [30000000 + i * 7 for i in range(500)]
    shuffled = list(pmids)
    random.Random(1).shuffle(shuffled)
    expected = random.Random(20260904).sample(sorted(pmids), k=len(pmids))
    assert seeded_sequence(shuffled) == expected
    assert seeded_sequence(pmids) == expected                       # order of input irrelevant
    assert seeded_sequence(pmids + pmids[:10]) == expected           # duplicates removed


def test_u_cell_pilot_drawn_first_then_200_formal_then_reserve():
    pop = list(range(1, 1001))
    s = draw_cell("U-AI", "S_AI", pop, 200, pilot_size=20)
    seq = seeded_sequence(pop)
    assert s.pilot == seq[:20]
    assert s.formal == seq[20:220]
    assert s.reserve == seq[220:]
    assert len(set(s.pilot) | set(s.formal)) == 220
    assert s.population_size == 1000 and s.notes == []
    # the formal set is disjoint from the pilot and identical to the registered sample of the
    # first 220 elements minus the pilot
    assert set(s.formal).isdisjoint(s.pilot)


def test_v_cell_census_when_population_at_most_200():
    pop = list(range(100, 300))                                     # exactly 200 records
    s = draw_cell("V-AI", "B_AI", pop, 200, pilot_size=20, take_all_if_at_most=200)
    assert s.rule == "census"
    assert s.formal == sorted(pop) and s.pilot == [] and s.reserve == []
    assert any("census" in n for n in s.notes)
    # 201 records: seeded sample of 200 with pilot first
    pop2 = list(range(100, 301))
    s2 = draw_cell("V-STROKE", "B_STROKE", pop2, 200, pilot_size=20, take_all_if_at_most=200)
    assert s2.rule != "census"
    assert len(s2.pilot) == 20 and len(s2.formal) == 181            # only 201 - 20 available
    assert any("formal shortfall" in n for n in s2.notes)


def test_replacement_follows_the_seeded_sequence():
    pop = list(range(1, 501))
    s = draw_cell("R-AI", "R_AI", pop, 50, pilot_size=20)
    seq = seeded_sequence(pop)
    missing_formal, missing_pilot = s.formal[3], s.pilot[0]
    added = replace_missing(s, [missing_formal, missing_pilot, 999999])   # 999999 not in the draw
    assert added == [seq[70], seq[71]]
    assert missing_formal not in s.formal and seq[70] in s.formal
    assert missing_pilot not in s.pilot and seq[71] in s.pilot
    assert len(s.formal) == 50 and len(s.pilot) == 20
    assert s.replacements == [
        {"missing": missing_formal, "replacement": seq[70], "set": "formal"},
        {"missing": missing_pilot, "replacement": seq[71], "set": "pilot"},
    ]
    census = draw_cell("V-AI", "B_AI", list(range(1, 51)), 200, take_all_if_at_most=200)
    assert replace_missing(census, [7]) == []
    assert census.replacements == [{"missing": 7, "replacement": None, "set": "formal"}]


def test_draw_all_cells_from_catalogue_config(catalogue, tmp_path):
    lists = {
        "B_AI": list(range(1, 151)),          # 150 RCT-tagged AI records: census
        "B_STROKE": list(range(1, 1201)),      # 1,200: sample of 200
        "S_AI": list(range(1, 3001)),
        "S_STROKE": list(range(1, 3001)),
        "R_AI": list(range(1, 20001)),
        "R_STROKE": list(range(1, 20001)),
    }
    samples = draw_all_cells(lists, catalogue.raw["sampling"])
    by_cell = {s.cell: s for s in samples}
    assert list(by_cell) == ["V-AI", "V-STROKE", "U-AI", "U-STROKE", "R-AI", "R-STROKE"]
    assert by_cell["V-AI"].rule == "census" and len(by_cell["V-AI"].formal) == 150
    assert len(by_cell["V-STROKE"].pilot) == 20 and len(by_cell["V-STROKE"].formal) == 200
    assert len(by_cell["U-AI"].formal) == 200 and len(by_cell["U-STROKE"].formal) == 200
    assert len(by_cell["R-AI"].formal) == 50 and len(by_cell["R-STROKE"].formal) == 50
    assert by_cell["U-AI"].formal == by_cell["U-STROKE"].formal   # same population, same seed: same draw
    paths = write_cell_csvs(samples, tmp_path)
    assert len(paths) == 6
    text = paths[1].read_text(encoding="utf-8").splitlines()
    assert text[0] == "cell,set,order,pmid"
    assert text[1].startswith("V-STROKE,pilot,1,")
    assert text[21].startswith("V-STROKE,formal,1,")
    assert len(text) == 1 + 20 + 200


def test_draw_cells_of_amendment_v3_0(catalogue, tmp_path):
    """Section 6.1: the STROKE cells are split by AI status; a V-cell or U-cell with 200 records or
    fewer is rated completely, a larger one is a seeded sample of 200 with 20 pilot records first."""
    from airct_benchmark.sampling import draw_cells

    lists = {
        "B_AI": list(range(1, 151)),               # 150: census
        "B_STROKE": list(range(1, 1201)),
        "S_AI": list(range(1, 3001)),
        "S_STROKE": list(range(1, 3001)),
        "R_AI": list(range(1, 20001)),
        "R_STROKE": list(range(1, 20001)),
        "DB_STROKE": list(range(1, 201)),          # exactly 200: census
        "ERCT_STROKE": list(range(201, 1201)),     # 1,000: sample of 200
        "SAI_STROKE": list(range(1, 202)),         # 201: sample (only 181 left after the pilot, flagged)
        "SNONAI_STROKE": list(range(202, 3001)),
    }
    samples = draw_cells(lists, catalogue.amendment_sampling)
    by_cell = {s.cell: s for s in samples}
    assert list(by_cell) == ["V-AI", "V-STROKE-AI", "V-STROKE-nonAI", "U-AI", "U-STROKE-AI", "U-STROKE-nonAI", "R-AI", "R-STROKE"]
    assert by_cell["V-AI"].rule == "census" and len(by_cell["V-AI"].formal) == 150 and by_cell["V-AI"].pilot == []
    assert by_cell["V-STROKE-AI"].rule == "census" and by_cell["V-STROKE-AI"].formal == list(range(1, 201))
    assert by_cell["V-STROKE-AI"].source_list == "DB_STROKE"
    seq = seeded_sequence(range(201, 1201))
    assert by_cell["V-STROKE-nonAI"].pilot == seq[:20] and by_cell["V-STROKE-nonAI"].formal == seq[20:220]
    assert by_cell["V-STROKE-nonAI"].reserve == seq[220:]
    assert len(by_cell["U-AI"].pilot) == 20 and len(by_cell["U-AI"].formal) == 200
    assert by_cell["U-STROKE-AI"].rule != "census" and len(by_cell["U-STROKE-AI"].formal) == 181
    assert any("formal shortfall" in n for n in by_cell["U-STROKE-AI"].notes)
    assert len(by_cell["U-STROKE-nonAI"].formal) == 200 and by_cell["U-STROKE-nonAI"].population_size == 2799
    assert len(by_cell["R-AI"].formal) == 50 and len(by_cell["R-STROKE"].formal) == 50
    # the unchanged cells of v2.0 are drawn exactly as the registered function draws them
    registered = {s.cell: s for s in draw_all_cells(lists, catalogue.raw["sampling"])}
    for cell in ("V-AI", "U-AI", "R-AI", "R-STROKE"):
        assert (by_cell[cell].pilot, by_cell[cell].formal) == (registered[cell].pilot, registered[cell].formal), cell
    paths = write_cell_csvs(samples, tmp_path)
    assert [p.name for p in paths] == [f"sample_{c}.csv" for c in by_cell]
