"""Generate every count query (families A to K, M, N, Q, R, U, W, Y) and every list query
(family L) from the catalogue, exactly by composition rule 12.2, and check the catalogue
against the text of the registered preregistration (string identity, Step 3).

A query is the character-level concatenation of the template components with the year clause
("YYYY"[pdat]) always last. No string is composed in any other place of the package.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from .catalogue import Catalogue, CatalogueError


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
    if "{F_AI_VOCAB2015}" in term:
        term = term.replace("{F_AI_VOCAB2015}", cat.auxiliary["F_AI_VOCAB2015"])
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
    return cat.years_for_field("default")  # subfields and panel members use the default window


def query_id(family: str, field: str, metric: str, year: int) -> str:
    return f"{family}_{field}_{metric}_{year}"


def build_count_queries(cat: Catalogue, families: Iterable[str] | None = None) -> list[QuerySpec]:
    """All count queries of the catalogue in a fixed, reproducible order:
    family letter, field (registered order), metric (catalogue order), year ascending."""
    out: list[QuerySpec] = []
    letters = list(families) if families else list(cat.families.keys())
    for letter in sorted(letters):
        fam = cat.families[letter]
        for field_key in cat.field_group(fam["fields"]):
            for metric, template in fam["metrics"].items():
                for year in _years_for(cat, fam, field_key):
                    term = compose(cat, template, field_key, year)
                    out.append(QuerySpec(query_id(letter, field_key, metric, year), letter, field_key, year, metric, term))
    _assert_unique(out)
    return out


def build_list_queries(cat: Catalogue) -> list[QuerySpec]:
    """Family L: the family B strings for AI and STROKE and the family R strings (S_f, R_f), 2024.

    The list queries reuse the count templates verbatim; only the retrieval mode differs
    (retmax and retstart, or usehistory=y above 10,000 identifiers)."""
    out: list[QuerySpec] = []
    year = int(cat.lists["year"])
    for cell in cat.lists["cells"]:
        fam = cat.families[cell["family"]]
        template = fam["metrics"][cell["metric"]]
        for field_key in cat.field_group(cat.lists["fields"]):
            term = compose(cat, template, field_key, year)
            out.append(QuerySpec(query_id("L", field_key, cell["key"], year), "L", field_key, year, cell["key"], term))
    _assert_unique(out)
    return out


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


def _assert_unique(specs: list[QuerySpec]) -> None:
    """Query ids must be unique. Identical query strings across families are expected and kept:
    Cardiovascular Diseases is a named field (A, B) and a disease-panel heading (M); Diagnostic
    Imaging, Telemedicine, Decision Support Systems, Clinical and Mobile Applications are named
    fields (A, B) and technology-panel descriptors (N). The registration lists these cells in both
    families, so both are requested; the repeats double as within-run stability observations."""
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
# Worked verbatim examples of 12.6 (AI, 2024), copied from the registration
# ---------------------------------------------------------------------------------------------

WORKED_EXAMPLES: dict[tuple[str, str], str] = {
    ("A", "den"): '"Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND ("2024"[pdat])',
    ("B", "rct"): '"Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2024"[pdat])',
    ("G", "den"): '("artificial intelligence"[tiab] OR "machine learning"[tiab] OR "deep learning"[tiab] OR "neural network"[tiab] OR "neural networks"[tiab]) AND medline[sb] AND "Humans"[Mesh] AND ("2024"[pdat])',
    ("Q", "rct"): '"Artificial Intelligence"[Mesh] AND "Randomized Controlled Trial"[pt] AND ("2024"[pdat])',
    ("R", "S"): '"Artificial Intelligence"[Mesh] AND "Humans"[Mesh] AND medline[sb] AND (randomized[tiab] OR randomised[tiab] OR randomly[tiab] OR placebo[tiab] OR trial[ti]) NOT "Randomized Controlled Trial"[pt] AND ("2024"[pdat])',
    ("W", "den"): '("Artificial Intelligence"[Mesh] NOT "Robotics"[Mesh]) AND "Humans"[Mesh] AND ("2024"[pdat])',
}


# ---------------------------------------------------------------------------------------------
# Verbatim check against the preregistration text (Step 3 code review)
# ---------------------------------------------------------------------------------------------

@dataclass
class CheckItem:
    kind: str            # component | worked_example | template | generated_equals_example
    name: str
    text: str
    strict: bool         # exact substring found in the registration text
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
    specs = {(s.family, s.metric): s for s in build_count_queries(cat) if s.field == "AI" and s.year == 2024}
    for (letter, metric), example in WORKED_EXAMPLES.items():
        generated = specs[(letter, metric)].term
        ok = generated == example
        items.append(CheckItem("generated_equals_example", f"generated {letter}/{metric} == example", generated, ok, ok))

    return CheckReport(items)


def load_prereg_text(path: Path | str) -> str:
    """Read the registration text (Markdown or plain text). PDF must be converted to text first."""
    return Path(path).read_text(encoding="utf-8", errors="replace")


def count_summary(specs: list[QuerySpec]) -> dict[str, int]:
    """Number of queries per family, plus total."""
    out: dict[str, int] = {}
    for s in specs:
        out[s.family] = out.get(s.family, 0) + 1
    out["total"] = len(specs)
    return out


PDAT_YEAR_RE = re.compile(r'\("(\d{4})"\[pdat\]\)$')


def year_from_term(term: str) -> int:
    """Read the year back from a composed query (self-check that the year clause is last)."""
    m = PDAT_YEAR_RE.search(term)
    if not m:
        raise CatalogueError(f"query does not end with a year clause: {term}")
    return int(m.group(1))
