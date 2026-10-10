"""Generate every count query and every list query from the catalogue, exactly by composition
rule 12.2, and check the catalogue against the text of the registered preregistration and of
Protocol Amendment v3.0 (string identity).

Registered families (v2.0, Q12.6): A to K, M, N, Q, R, U, W, Y (counts) and L (lists).
Amendment families (v3.0, Section 4): DB, DC, MD, ME, GA, GD, GE, DV, QV, WV, KV, JV, RS (counts)
and LV (lists).

A query is the character-level concatenation of the template components with the year clause
("YYYY"[pdat]) always last. No string is composed in any other place of the package.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from . import gbd
from .catalogue import (
    AMENDMENT_FAMILY_CODES,
    AMENDMENT_LIST_FAMILY,
    GBD_FAMILIES,
    GBD_PANEL_SIZE,
    LIST_FAMILY,
    PROTECTED_FIELD,
    Catalogue,
    CatalogueError,
    _base_metric_of_rct_variant,
    mesh_headings,
    normalise_heading,
)


@dataclass(frozen=True)
class QuerySpec:
    """One count or list request: identity fields (12.10) plus the verbatim term."""

    query_id: str
    family: str
    field: str
    year: int
    metric: str
    term: str

    def as_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------------------------

def compose(cat: Catalogue, template: str, field_key: str, year: int) -> str:
    """Fill the placeholders of a family template for one field and year (12.2).

    Replacement is literal (str.replace), never str.format, so that brackets and quotes of the
    PubMed syntax can never be interpreted.
    """
    term = template
    if "{F}" in term:
        term = term.replace("{F}", cat.mesh_expression(field_key))
    if "{F_TIAB}" in term:
        term = term.replace("{F_TIAB}", cat.tiab_expression(field_key))
    if "{SUB}" in term:
        if field_key not in cat.subfields:
            raise CatalogueError(f"{field_key} is not a subfield")
        term = term.replace("{SUB}", cat.auxiliary[field_key])
    if "{HEADING}" in term:
        term = term.replace("{HEADING}", cat.panel_member(field_key).mesh)
    if "{DESCRIPTOR}" in term:
        term = term.replace("{DESCRIPTOR}", cat.panel_member(field_key).mesh)
    if "{G}" in term:
        term = term.replace("{G}", cat.gbd_member(field_key).expression)
    if "{F_AI_VOCAB2015}" in term:
        term = term.replace("{F_AI_VOCAB2015}", cat.auxiliary["F_AI_VOCAB2015"])
    if "{AI_TIAB_TERMS}" in term:
        term = term.replace("{AI_TIAB_TERMS}", cat.amendment_auxiliary["AI_TIAB_TERMS"])
    if "{CLIN_ANY}" in term:
        term = term.replace("{CLIN_ANY}", cat.clin_any)
    term = term.replace("{YEAR}", cat.year_clause(year))
    if "{" in term or "}" in term:
        raise CatalogueError(f"unresolved placeholder in composed query: {term}")
    return term


def _years_for(cat: Catalogue, family: dict, field_key: str) -> list[int]:
    if family.get("years") == "primary_year_only":
        return [cat.primary_year]
    if field_key in cat.fields:
        return cat.years_for_field(field_key)
    return cat.years_for_field("default")  # subfields, panel members and GBD members use the default window


def query_id(family: str, field: str, metric: str, year: int) -> str:
    return f"{family}_{field}_{metric}_{year}"


def _build(cat: Catalogue, codes: Iterable[str]) -> list[QuerySpec]:
    out: list[QuerySpec] = []
    for code in codes:
        fam = cat.family(code)
        for field_key in cat.field_group(fam["fields"]):
            for metric, template in fam["metrics"].items():
                for year in _years_for(cat, fam, field_key):
                    term = compose(cat, template, field_key, year)
                    out.append(QuerySpec(query_id(code, field_key, metric, year), code, field_key, year, metric, term))
    return out


def build_registered_count_queries(cat: Catalogue) -> list[QuerySpec]:
    """The 2,034 count queries of the registered catalogue (tag v1.0), in the order of tag v1.0:
    family letter, field (registered order), metric (catalogue order), year ascending."""
    out = _build(cat, sorted(cat.families))
    _assert_unique(out)
    return out


def build_amendment_count_queries(cat: Catalogue) -> list[QuerySpec]:
    """The count queries added by Amendment v3.0, in the order of its Section 4. GBD members that
    coincide with a named field are not queried again (Section 5.2), see shared_cells()."""
    out = _build(cat, list(cat.amendment_families))
    _assert_unique(out)
    return out


def build_count_queries(cat: Catalogue, families: Iterable[str] | None = None) -> list[QuerySpec]:
    """All count queries in a fixed, reproducible order: the registered catalogue first, exactly
    as in tag v1.0, then the amendment families in the order of the amendment.

    ``families`` restricts the run to some family codes (testing and reproduction tooling)."""
    if families:
        wanted = list(families)
        unknown = [c for c in wanted if c not in cat.families and c not in cat.amendment_families]
        if unknown:
            raise CatalogueError(f"unknown family code(s): {unknown}")
        codes = sorted(c for c in wanted if c in cat.families) + [c for c in cat.amendment_families if c in wanted]
    else:
        codes = list(cat.all_families())
    out = _build(cat, codes)
    _assert_unique(out)
    return out


# ---------------------------------------------------------------------------------------------
# Shared cells of GBD members that coincide with a named field (amendment, Section 5.2)
# ---------------------------------------------------------------------------------------------

def shared_cells(cat: Catalogue) -> list[dict]:
    """For every GBD member shared with a named field: which registered (or family DB) cell
    holds the count of each GBD cell. The composed strings are identical by construction, and
    this function proves it for every cell before returning."""
    out: list[dict] = []
    for member in cat.gbd_panel():
        if not member.shared_with:
            continue
        field_key = member.shared_with
        for code in GBD_FAMILIES:
            fam = cat.amendment_families[code]
            for metric, template in fam["metrics"].items():
                target = cat.amendment_shared_cells[code][metric]
                target_fam = cat.family(target["family"])
                if field_key not in cat.field_group(target_fam["fields"]):
                    raise CatalogueError(f"shared cell {code}/{metric} of {member.key}: {field_key} is not a field of family {target['family']}")
                for year in cat.years_for_field(field_key):
                    own = compose(cat, template, member.key, year)
                    held = compose(cat, target_fam["metrics"][target["metric"]], field_key, year)
                    if own != held:
                        raise CatalogueError(
                            f"shared cell {code}/{metric} of {member.key} ({year}) is not identical to "
                            f"{target['family']}/{target['metric']} of {field_key}: {own!r} vs {held!r}")
                    out.append({
                        "gbd_member": member.key,
                        "family": code,
                        "metric": metric,
                        "year": year,
                        "query": own,
                        "held_by_query_id": query_id(target["family"], field_key, target["metric"], year),
                        "held_by_family": target["family"],
                        "held_by_field": field_key,
                        "held_by_metric": target["metric"],
                    })
    return out


# ---------------------------------------------------------------------------------------------
# List queries (family L registered, family LV amendment)
# ---------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class ListSpec:
    key: str            # B_AI, DB_STROKE, ...
    list_family: str    # L or LV
    efetch: str         # all | sampled | none
    spec: QuerySpec


def build_list_specs(cat: Catalogue) -> list[ListSpec]:
    """Family L: the family B strings for AI and STROKE and the family R strings (S_f, R_f), 2024,
    in registered order. Family LV: the family DB string and the family E RCT string for STROKE
    and the two family RS strings, 2024.

    The list queries reuse the count templates verbatim; only the retrieval mode differs
    (retmax and retstart, or usehistory=y above 10,000 identifiers)."""
    out: list[ListSpec] = []
    year = int(cat.amendment_lists["year"])
    for entry in cat.amendment_lists["lists"]:
        template = cat.family(entry["family"])["metrics"][entry["metric"]]
        field_key = entry["field"]
        term = compose(cat, template, field_key, year)
        cell_key = entry["key"][: -len("_" + field_key)]
        spec = QuerySpec(query_id(entry["list_family"], field_key, cell_key, year), entry["list_family"], field_key, year, cell_key, term)
        out.append(ListSpec(entry["key"], entry["list_family"], entry["efetch"], spec))
    _assert_unique([x.spec for x in out])
    if len({x.key for x in out}) != len(out):
        raise CatalogueError("duplicate list keys")
    return out


def build_list_queries(cat: Catalogue) -> list[QuerySpec]:
    """Query specs of all PMID lists (six of family L, then four of family LV)."""
    return [x.spec for x in build_list_specs(cat)]


def build_registered_list_queries(cat: Catalogue) -> list[QuerySpec]:
    """The six family L list queries exactly as generated by tag v1.0 (registered section 'lists')."""
    out: list[QuerySpec] = []
    year = int(cat.lists["year"])
    for cell in cat.lists["cells"]:
        fam = cat.families[cell["family"]]
        template = fam["metrics"][cell["metric"]]
        for field_key in cat.field_group(cat.lists["fields"]):
            term = compose(cat, template, field_key, year)
            out.append(QuerySpec(query_id(LIST_FAMILY, field_key, cell["key"], year), LIST_FAMILY, field_key, year, cell["key"], term))
    _assert_unique(out)
    return out


# ---------------------------------------------------------------------------------------------
# Smoke test (registered) and amendment syntax check (publication year 2015 only)
# ---------------------------------------------------------------------------------------------

def smoke_query(cat: Catalogue, family: str | None = None, metric: str | None = None) -> QuerySpec:
    """The single smoke-test cell (Q9): Diabetes Mellitus 2015, family A by default.

    Before the freeze date this is the only cell that may be sent to PubMed. Field and year are
    fixed to the registered smoke cell; family and metric may vary within Diabetes Mellitus 2015."""
    spec = cat.smoke_test
    family = family or spec["family"]
    metric = metric or spec["metric"]
    field_key, year = spec["field"], int(spec["year"])
    fam = cat.families.get(family)
    if fam is None or metric not in fam["metrics"]:
        raise CatalogueError(f"family {family} / metric {metric} not in catalogue")
    template = fam["metrics"][metric]
    if field_key not in cat.field_group(fam["fields"]):
        # The registered smoke cell is defined by field and year, not by family. A generic field
        # template (placeholders {F}, {F_TIAB}, {YEAR} only) may be applied to Diabetes Mellitus 2015
        # even when the family is registered for other fields; the syntax check of Q18 did exactly
        # this for the family R strata (S 941, R 16,377). Templates bound to AI-specific
        # expressions cannot be turned into a smoke cell.
        generic = template.replace("{F_TIAB}", "").replace("{F}", "").replace("{YEAR}", "")
        has_field_placeholder = "{F}" in template or "{F_TIAB}" in template
        if "{" in generic or not has_field_placeholder:
            raise CatalogueError(f"family {family} does not contain the smoke field {field_key} and its template is not generic")
    term = compose(cat, template, field_key, year)
    return QuerySpec(query_id(family, field_key, metric, year), family, field_key, year, metric, term)


def smoke_reference_count(cat: Catalogue, family: str, metric: str) -> int | None:
    spec = cat.smoke_test
    if family == spec["family"] and metric == spec["metric"]:
        return int(spec["reference_count"])
    return (spec.get("other_reference_counts") or {}).get(f"{family}/{metric}")


@dataclass(frozen=True)
class SyntaxCheckItem:
    """One request of the amendment syntax check (publication year 2015 only)."""

    group: str                  # anchor | composition | gbd_descriptor
    check_id: str               # '<family>/<metric>' or 'GA/den:<GBD key>'
    family: str
    metric: str
    field: str                  # field key the query was composed for
    term: str                   # the string sent to PubMed
    note: str
    catalogue_query_id: str | None   # id of the identical catalogue cell, when one exists
    reference_count: int | None      # Q18 value for anchors

    def as_dict(self) -> dict:
        return asdict(self)


def build_syntax_check_plan(cat: Catalogue) -> list[SyntaxCheckItem]:
    """The requests of the amendment syntax check (amendment, Sections 1.4 and 8.3; rule of Q8, Q18).

    * anchors: registered smoke cells of Diabetes Mellitus 2015 that were disclosed in Q18;
    * compositions: one request per new composition, run with Diabetes Mellitus in place of
      Stroke wherever the field is not itself the object of the check;
    * gbd_descriptors: one request per GBD descriptor that is new relative to v2.0.

    Every request is restricted to publication year 2015 and none contains the Stroke expression.
    This function is pure; nothing is sent here."""
    sc = cat.amendment_syntax_check
    year = int(sc["year"])
    stand_in, replaced = sc["stand_in_field"], PROTECTED_FIELD
    stand_in_mesh, replaced_mesh = cat.fields[stand_in]["mesh"], cat.fields[replaced]["mesh"]
    catalogue_ids = {s.term: s.query_id for s in build_count_queries(cat)}
    items: list[SyntaxCheckItem] = []

    for a in sc["anchors"]:
        spec = smoke_query(cat, a["family"], a["metric"])
        items.append(SyntaxCheckItem(
            "anchor", f"{a['family']}/{a['metric']}", a["family"], a["metric"], stand_in, spec.term,
            "registered smoke cell of Diabetes Mellitus 2015, disclosed in Q18; re-read for the identities",
            catalogue_ids.get(spec.term), smoke_reference_count(cat, a["family"], a["metric"])))

    for c in sc["compositions"]:
        fam = cat.amendment_families[c["family"]]
        template = fam["metrics"][c["metric"]]
        if isinstance(fam["fields"], str) and stand_in in cat.field_group(fam["fields"]):
            term = compose(cat, template, stand_in, year)
            note = f"new composition; catalogue cell of {stand_in} {year}"
        else:
            original = compose(cat, template, replaced, year)
            if replaced_mesh not in original:
                raise CatalogueError(f"syntax check: {c['family']}/{c['metric']} does not contain the {replaced} expression")
            term = original.replace(replaced_mesh, stand_in_mesh)
            note = f"new composition; {stand_in} in place of {replaced} so that no {replaced} count is viewed"
        items.append(SyntaxCheckItem("composition", f"{c['family']}/{c['metric']}", c["family"], c["metric"], stand_in,
                                     term, note, catalogue_ids.get(term), None))

    g = sc["gbd_descriptors"]
    template = cat.amendment_families[g["family"]]["metrics"][g["metric"]]
    for member in cat.gbd_panel():
        if member.shared_with:
            continue  # the descriptor is registered (named field); nothing new to check
        term = compose(cat, template, member.key, year)
        items.append(SyntaxCheckItem("gbd_descriptor", f"{g['family']}/{g['metric']}:{member.key}", g["family"], g["metric"],
                                     member.key, term, f"new descriptor of the GBD panel: {member.cause}",
                                     catalogue_ids.get(term), None))

    # Hard rule of Q8 and Q18, enforced here and again by the caller before anything is sent.
    year_clause = cat.year_clause(year)
    for it in items:
        problem = syntax_check_violation(cat, it.term)
        if problem:
            raise CatalogueError(f"syntax check item {it.check_id} {problem}")
        if not it.term.endswith("AND " + year_clause):
            raise CatalogueError(f"syntax check item {it.check_id} is not restricted to publication year {year}")
    ids = [it.check_id for it in items]
    if len(set(ids)) != len(ids):
        raise CatalogueError("duplicate syntax check ids")
    return items


def syntax_check_violation(cat: Catalogue, term: str) -> str | None:
    """Why a string must not be sent before the freeze run (None: it may be sent in the syntax check).

    * exactly one year clause, the registered smoke year (2015), at the end;
    * no heading of the protected field (Stroke) in any spelling: PubMed ignores case and blanks;
    * no trial numerator within a field.
    The rule is fixed in code (catalogue.PROTECTED_FIELD); it is not read from the catalogue file."""
    year = int(cat.smoke_test["year"])
    year_clause = cat.year_clause(year)
    if len(PDAT_ANY_RE.findall(term)) != 1 or term.count("[pdat]") != 1 or not term.endswith(year_clause):
        return f"is not restricted to the single publication year {year}"
    protected = {normalise_heading(h) for h in mesh_headings(cat.fields[PROTECTED_FIELD]["mesh"])}
    if any(normalise_heading(h) in protected for h in mesh_headings(term)):
        return f"contains the {PROTECTED_FIELD} heading"
    return None


def _assert_unique(specs: list[QuerySpec]) -> None:
    """Query ids must be unique. Identical query strings across families are expected and kept:
    Cardiovascular Diseases is a named field (A, B) and a disease-panel heading (M); Diagnostic
    Imaging, Telemedicine, Decision Support Systems, Clinical and Mobile Applications are named
    fields (A, B) and technology-panel descriptors (N). The registration lists these cells in both
    families, so both are requested; the repeats double as within-run stability observations.
    The amendment adds one more group of this kind: the Cardiovascular Diseases heading of
    families MD and ME repeats the CVD cells of families D, DB and E."""
    ids = [s.query_id for s in specs]
    if len(set(ids)) != len(ids):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        raise CatalogueError(f"duplicate query ids: {dup[:5]}")


def duplicate_terms(specs: list[QuerySpec]) -> dict[str, list[str]]:
    """Map of query string to the ids that share it (informational)."""
    by_term: dict[str, list[str]] = {}
    for s in specs:
        by_term.setdefault(s.term, []).append(s.query_id)
    return {t: ids for t, ids in by_term.items() if len(ids) > 1}


# ---------------------------------------------------------------------------------------------
# Worked verbatim examples
# ---------------------------------------------------------------------------------------------

# 12.6 of the registration (AI, 2024), copied from the registration
WORKED_EXAMPLES: dict[tuple[str, str], str] = {
    ("A", "den"): '"Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND ("2024"[pdat])',
    ("B", "rct"): '"Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2024"[pdat])',
    ("G", "den"): '("artificial intelligence"[tiab] OR "machine learning"[tiab] OR "deep learning"[tiab] OR "neural network"[tiab] OR "neural networks"[tiab]) AND medline[sb] AND "Humans"[Mesh] AND ("2024"[pdat])',
    ("Q", "rct"): '"Artificial Intelligence"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2024"[pdat])',
    ("R", "S"): '"Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND medline[sb] AND (randomized[tiab] OR randomised[tiab] OR randomly[tiab] OR placebo[tiab] OR trial[ti]) NOT "Randomized Controlled Trial"[pt] AND ("2024"[pdat])',
    ("W", "den"): '("Artificial Intelligence"[Mesh] NOT "Robotics"[Mesh]) AND "Humans"[Mesh] AND ("2024"[pdat])',
}

# Section 4 of Amendment v3.0 (2024), copied from the amendment. Key: (family, field key, metric).
# The last example names a GBD member that is shared with the named field DM; its string is the
# registered family E cell of DM (amendment, Section 5.2).
WORKED_EXAMPLES_AMENDMENT: dict[tuple[str, str, str], str] = {
    ("DB", "STROKE", "rct"): '"Stroke"[Mesh] AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2024"[pdat])',
    ("E", "STROKE", "rct"): '("Stroke"[Mesh] NOT "Artificial Intelligence"[Mesh]) AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2024"[pdat])',
    ("D", "STROKE", "overlap"): '"Stroke"[Mesh] AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND ("2024"[pdat])',
    ("MD", "DIS_NEOPLASMS", "den"): '"Neoplasms"[Mesh] AND "Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND ("2024"[pdat])',
    ("GE", "DM", "rct"): '("Diabetes Mellitus"[Mesh] NOT "Artificial Intelligence"[Mesh]) AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2024"[pdat])',
}


# ---------------------------------------------------------------------------------------------
# Verbatim checks against the preregistration text and the amendment text
# ---------------------------------------------------------------------------------------------

@dataclass
class CheckItem:
    kind: str            # component | worked_example | template | generated_equals_example | ...
    name: str
    text: str
    strict: bool         # exact substring found in the source text
    lenient: bool        # found after removing all whitespace on both sides (line wraps in PDF text)


@dataclass
class CheckReport:
    items: list[CheckItem]

    @property
    def strict_ok(self) -> bool:
        return all(i.strict for i in self.items)

    @property
    def lenient_ok(self) -> bool:
        return all(i.lenient for i in self.items)

    def failures(self, strict: bool = True) -> list[CheckItem]:
        return [i for i in self.items if not (i.strict if strict else i.lenient)]

    def summary(self) -> str:
        n = len(self.items)
        s = sum(i.strict for i in self.items)
        l = sum(i.lenient for i in self.items)
        return f"{n} checks: {s} strict matches, {l} whitespace-insensitive matches"


def _squash(text: str) -> str:
    return "".join(text.split())


def check_against_preregistration(cat: Catalogue, prereg_text: str) -> CheckReport:
    """Confirm that every registered string in the catalogue occurs verbatim in the preregistration.

    Two levels are reported. 'strict' is an exact substring match and is the criterion for the
    Markdown registration file. 'lenient' ignores all whitespace on both sides and exists only
    because the PDF rendering wraps long strings inside table cells; it still detects every
    non-whitespace character difference.

    Unchanged from tag v1.0: 93 checks on the registered catalogue only.
    """
    text = prereg_text.replace("\r\n", "\n").replace("\r", "\n")
    squashed = _squash(text)
    items: list[CheckItem] = []

    def add(kind: str, name: str, s: str) -> None:
        items.append(CheckItem(kind, name, s, s in text, _squash(s) in squashed))

    # 12.3 field expressions
    for key, f in cat.fields.items():
        add("component", f"12.3 {key} mesh", f["mesh"])
        if f.get("tiab"):
            add("component", f"12.3 {key} tiab", f["tiab"])
    # 12.4 auxiliary expressions
    for key, expr in cat.auxiliary.items():
        add("component", f"12.4 {key}", expr)
    # 12.5 panels
    for which in ("disease", "technology"):
        for m in cat.panel(which):
            add("component", f"12.5 {which} {m.key}", m.mesh)
    # 12.6 base templates as written in the registration, (...) for the year clause
    for letter, fam in cat.families.items():
        first_metric, first_template = next(iter(fam["metrics"].items()))
        registered_form = first_template.replace("{YEAR}", "(...)")
        add("template", f"12.6 family {letter} {first_metric}", registered_form)
    # worked verbatim examples of 12.6
    for (letter, metric), example in WORKED_EXAMPLES.items():
        add("worked_example", f"12.6 example {letter}/{metric}", example)
    # generated queries must equal the worked examples character for character
    specs = {(s.family, s.metric): s for s in build_registered_count_queries(cat) if s.field == "AI" and s.year == 2024}
    for (letter, metric), example in WORKED_EXAMPLES.items():
        generated = specs[(letter, metric)].term
        ok = generated == example
        items.append(CheckItem("generated_equals_example", f"generated {letter}/{metric} == example", generated, ok, ok))

    return CheckReport(items)


RCT_MARKERS = ("the same with RCT", "each the same with RCT", "each the same with RCT inserted before the year clause")
RS_LABELS = {"S_ai": "S_STROKE_AI: ", "S_nonai": "S_STROKE_nonAI: "}


def section4_rows(text: str) -> dict[str, list[str]]:
    """The rows of the family table of Section 4: {family code: [the cells of each row found]}.
    A row is a line that begins with '| XX |', XX being two capital letters."""
    out: dict[str, list[str]] = {}
    for line in text.split("\n"):
        line = line.strip()
        m = re.match(r"^\| ([A-Z]{2}) \| .* \|$", line)
        if m and len(line[2:-2].split(" | ")) == 4:      # Family | Use | Template | Fields
            out.setdefault(m.group(1), []).append(line)
    return out


def check_against_amendment(cat: Catalogue, amendment_text: str, allow_test_fixture: bool = False) -> CheckReport:
    """Confirm that the catalogue addendum and the GBD panel are what Amendment v3.0 states.

    Section 4, family by family. The table must hold exactly one row per family of the addendum
    (and the row of family LV), and no row of another family. The template cell of a row is split
    at '; ': its templates, with (...) for the year clause, must be the templates of the catalogue
    for that family, all of them, in the same order, and nothing else; the note "the same with RCT"
    must stand in the row exactly when the catalogue holds RCT variants for the family, and every
    such variant must be derived by the stated rule. A template that is only part of a longer
    string, two exchanged templates, or a family that exists on one side only are differences.
    AI_TIAB_TERMS and the five worked examples are compared as strings; the generated queries must
    equal the examples.

    Section 5, GBD panel. The panel is final, has 20 members, is not the synthetic panel of the
    test suite, and its table stands in the amendment exactly as generated: the same rows, complete,
    in the same order, and no other row. The panel file must also agree with the deposited mapping
    table, ranking and export record (gbd.panel_file_problems), and the generated text of Section 5.7
    must stand in the amendment as one unchanged block that states the SHA-256 values of the current
    files, the particulars of the export record, the table of the panel file and the catalogue volume
    (gbd.amendment_block_check).

    Not covered by this check, because the amendment states them in prose: the PMID lists, the
    validation cells and the syntax-check plan of the addendum. They are covered by the test suite.
    ``allow_test_fixture`` is for the test suite only.
    """
    text = amendment_text.replace("\r\n", "\n").replace("\r", "\n")
    squashed = _squash(text)
    items: list[CheckItem] = []

    def add(kind: str, name: str, s: str) -> None:
        items.append(CheckItem(kind, name, s, s in text, _squash(s) in squashed))

    def flag(kind: str, name: str, shown: str, ok: bool) -> None:
        items.append(CheckItem(kind, name, shown, ok, ok))

    add("component", "Section 4 AI_TIAB_TERMS", cat.amendment_auxiliary["AI_TIAB_TERMS"])

    # ---- Section 4: the family table, row by row -----------------------------------------------------
    rows = section4_rows(text)
    expected_codes = list(cat.amendment_families) + [AMENDMENT_LIST_FAMILY]
    flag("family_set", f"Section 4 lists exactly the families {expected_codes}", str(list(rows)), list(rows) == expected_codes)
    for code, fam in cat.amendment_families.items():
        found = rows.get(code, [])
        if len(found) != 1:
            flag("family_row", f"Section 4 has one table row for family {code} (found {len(found)})", f"| {code} | ...", False)
            continue
        cells = found[0][2:-2].split(" | ")
        segments = [seg.strip() for seg in cells[2].split("; ")]
        markers = [seg for seg in segments if seg in RCT_MARKERS]
        in_text = [seg for seg in segments if seg not in RCT_MARKERS]
        base = {metric: template for metric, template in fam["metrics"].items() if _base_metric_of_rct_variant(metric, fam["metrics"]) is None}
        in_catalogue = [RS_LABELS.get(metric, "") * (code == "RS") + template.replace("{YEAR}", "(...)") for metric, template in base.items()]
        for i, (metric, template) in enumerate(base.items()):
            ok = i < len(in_text) and in_text[i] == in_catalogue[i]
            flag("template", f"Section 4 family {code} {metric}", in_catalogue[i], ok)
        flag("template_count", f"Section 4 row of family {code} holds {len(in_catalogue)} template(s) and nothing else (found {len(in_text)})",
             cells[2], len(in_text) == len(in_catalogue))
        has_variants = len(base) != len(fam["metrics"])
        flag("rct_marker", f"Section 4 row of family {code}: note 'the same with RCT' {'present' if has_variants else 'absent'}",
             "; ".join(markers) or "(no note)", len(markers) == (1 if has_variants else 0))
        for metric, template in fam["metrics"].items():
            b = _base_metric_of_rct_variant(metric, fam["metrics"])
            if b is not None:
                expected = fam["metrics"][b][: -len(" AND {YEAR}")] + ' AND "Randomized Controlled Trial"[pt] AND {YEAR}'
                flag("derived_rct_variant", f"family {code} {metric} == {b} with RCT before the year clause", template, template == expected)

    # ---- Section 4: worked examples -------------------------------------------------------------------
    for (code, field_key, metric), example in WORKED_EXAMPLES_AMENDMENT.items():
        items.append(CheckItem("worked_example", f"Section 4 example {code}/{field_key}/{metric}", example,
                               f": {example}\n" in text + "\n", _squash(f": {example}") in squashed))
    by_id = {s.query_id: s.term for s in build_count_queries(cat)}
    shared = {(c["family"], c["held_by_field"], c["metric"], c["year"]): c["held_by_query_id"] for c in shared_cells(cat)}
    for (code, field_key, metric), example in WORKED_EXAMPLES_AMENDMENT.items():
        qid = query_id(code, field_key, metric, 2024)
        if qid not in by_id:  # a GBD cell of a member shared with a named field
            qid = shared.get((code, field_key, metric, 2024), qid)
        generated = by_id.get(qid, "")
        flag("generated_equals_example", f"generated {code}/{field_key}/{metric} ({qid}) == example", generated, generated == example)

    # ---- Section 5: the GBD panel ---------------------------------------------------------------------
    flag("gbd_panel_status", f"GBD panel status is final (found: {cat.gbd_status})", cat.gbd_status, cat.gbd_is_final)
    members = cat.gbd_raw.get("members") or []
    flag("gbd_panel_size", f"GBD panel has {GBD_PANEL_SIZE} members (found: {len(members)})", str(len(members)), len(members) == GBD_PANEL_SIZE)
    if not allow_test_fixture:
        flag("gbd_panel_real", "GBD panel is not the synthetic panel of the test suite", str(cat.gbd_path), not cat.gbd_is_test_fixture)
    expected_rows = [gbd.table_row(m) for m in members]
    found_rows = gbd.table_rows_in_text(text)
    for m, row in zip(members, expected_rows):
        i = expected_rows.index(row)
        ok = i < len(found_rows) and found_rows[i] == row
        flag("gbd_panel_row", f"Section 5 panel row {i + 1}: {m['key']}", row, ok)
    flag("gbd_panel_table", f"Section 5 panel table has exactly these {len(expected_rows)} rows and no other (found {len(found_rows)})",
         f"{len(found_rows)} rows", len(found_rows) == len(expected_rows) and found_rows == expected_rows)
    if cat.gbd_is_final and not cat.gbd_is_test_fixture and cat.gbd_path is not None:
        field_by_mesh = {f["mesh"]: k for k, f in cat.fields.items()}
        problems = gbd.panel_file_problems(cat.gbd_raw, cat.gbd_path.resolve().parent.parent, field_by_mesh)
        flag("gbd_panel_files", "GBD panel file agrees with the deposited mapping table, ranking and export record",
             "; ".join(problems) or "agrees", not problems)
        current = [gbd.TABLE_HEADER, gbd.TABLE_RULE, *expected_rows,
                   gbd.volume_line(len(build_amendment_count_queries(cat)), len(build_count_queries(cat)))]
        strict, lenient, finding = gbd.amendment_block_check(cat.gbd_raw, cat.gbd_sha256(), cat.gbd_path.resolve().parent.parent, text,
                                                             required_lines=current)
        items.append(CheckItem("gbd_panel_block", f"Section 5.7 stands in the amendment as generated ({gbd.AMENDMENT_TABLE_FILE}): "
                               "text above the table, table, causes not in the panel, export line with SHA-256 values, catalogue volume",
                               finding, strict, lenient))

    return CheckReport(items)


def load_prereg_text(path: Path | str) -> str:
    """Read the registration or amendment text (Markdown or plain text). PDF must be converted to text first."""
    return Path(path).read_text(encoding="utf-8", errors="replace")


def count_summary(specs: list[QuerySpec]) -> dict[str, int]:
    """Number of queries per family, plus total."""
    out: dict[str, int] = {}
    for s in specs:
        out[s.family] = out.get(s.family, 0) + 1
    out["total"] = len(specs)
    return out


PDAT_YEAR_RE = re.compile(r'\("(\d{4})"\[pdat\]\)$')
PDAT_ANY_RE = re.compile(r'\("\d{4}"\[pdat\]\)')


def year_from_term(term: str) -> int:
    """Read the year back from a composed query (self-check that the year clause is last)."""
    m = PDAT_YEAR_RE.search(term)
    if not m:
        raise CatalogueError(f"query does not end with a year clause: {term}")
    return int(m.group(1))
