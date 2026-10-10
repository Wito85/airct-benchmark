"""Load and validate config/catalogue.yaml, the verbatim query catalogue of Q12, and its
addendum for Protocol Amendment v3.0 (new query families, GBD panel, validation cells).

The catalogue is data, not code. This module only reads it, checks its structure and exposes
typed accessors. Nothing in here may alter a registered string.

Layout of the catalogue file since pipeline v1.1.0
* The first ``amendment.registered_prefix_chars`` characters are the registered catalogue of tag
  v1.0, unchanged. The loader verifies their SHA-256 on every start.
* Everything after that is the addendum of Amendment v3.0 (keys starting with ``amendment``).
* The GBD panel (Amendment v3.0, Section 5) lives in its own file, ``config/gbd_panel.yaml``,
  which is generated from the reconciled mapping table by ``scripts/gbd_panel.py`` and is never
  edited by hand.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOGUE_PATH = PACKAGE_ROOT / "config" / "catalogue.yaml"

USED_FAMILY_LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "M", "N", "Q", "R", "U", "W", "Y"]
UNUSED_FAMILY_LETTERS = ["P", "S", "T", "V", "X"]
LIST_FAMILY = "L"      # PMID lists, handled by queries.build_list_queries
EFETCH_FAMILY = "O"    # efetch XML, handled by run.py lists mode
TEMPLATE_PLACEHOLDERS = ("{F}", "{F_TIAB}", "{SUB}", "{HEADING}", "{DESCRIPTOR}", "{F_AI_VOCAB2015}", "{CLIN_ANY}", "{YEAR}")

# Amendment v3.0, Section 4: two-letter codes for all new families.
AMENDMENT_FAMILY_CODES = ["DB", "DC", "MD", "ME", "GA", "GD", "GE", "DV", "QV", "WV", "KV", "JV", "RS"]
AMENDMENT_LIST_FAMILY = "LV"
AMENDMENT_TEMPLATE_PLACEHOLDERS = TEMPLATE_PLACEHOLDERS + ("{G}", "{AI_TIAB_TERMS}")
GBD_FAMILIES = ("GA", "GD", "GE")
GBD_PANEL_SIZE = 20
RCT_CLAUSE = ' AND "Randomized Controlled Trial"[pt]'
CT_CLAUSE = ' AND "Clinical Trial"[pt]'

# The registered catalogue of tag v1.0 (commit b68eb65): length in characters and SHA-256 of
# config/catalogue.yaml as released. Pinned here, in code, so that the file cannot certify itself.
REGISTERED_PREFIX_CHARS = 20150
REGISTERED_PREFIX_SHA256 = "f58bbbe612bab8fff2649aacff5b3b8ae85fc0c2b1803658bb187ac17982d394"
ADDENDUM_KEYS = ["amendment", "amendment_auxiliary", "amendment_named_field_ui", "amendment_families", "amendment_shared_cells",
                 "amendment_lists", "amendment_sampling", "amendment_syntax_check"]
# The field whose counts must not be viewed before the freeze run, and the registered smoke field
# that stands in for it in the syntax check (Q8, Q18). Fixed in code.
PROTECTED_FIELD = "STROKE"

# A GBD panel expression is one exploded MeSH descriptor, "<Heading>"[Mesh], or, where the mapping
# rule of the amendment says so, one descriptor with another removed, written in the form that is
# registered for F_AI_NOROB: ("<Heading>"[Mesh] NOT "<Heading>"[Mesh]).
_MESH_TERM = r'"[A-Za-z0-9][A-Za-z0-9 ,\'\-/().&]*"\[Mesh\]'
GBD_EXPRESSION_RE = re.compile(rf"^(?:{_MESH_TERM}|\({_MESH_TERM} NOT {_MESH_TERM}\))$")
GBD_KEY_RE = re.compile(r"^GBD_[A-Z0-9_]+$")


class CatalogueError(ValueError):
    """Raised when the catalogue file is structurally invalid."""


class _StrictLoader(yaml.SafeLoader):
    """YAML loader that refuses a mapping with a repeated key. With the standard loader the last
    occurrence wins silently, so that a second 'fields:' or 'smoke_test:' block appended to the
    file would replace a registered section without touching the registered text."""


def _construct_mapping_no_duplicates(loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise CatalogueError(f"duplicate key {key!r} in YAML (line {key_node.start_mark.line + 1}); a key may occur only once")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping_no_duplicates)


def strict_yaml(text: str, what: str) -> Any:
    try:
        return yaml.load(text, Loader=_StrictLoader)  # noqa: S506 (a SafeLoader subclass)
    except yaml.YAMLError as exc:
        raise CatalogueError(f"{what} is not valid YAML: {exc}") from exc


def normalise_heading(heading: str) -> str:
    """PubMed matches MeSH headings without regard to case or surrounding blanks."""
    return " ".join(str(heading).split()).casefold()


def mesh_headings(expression: str) -> list[str]:
    """The quoted headings of all [Mesh] and [Mesh:NoExp] terms of an expression, as written."""
    return re.findall(r'"([^"]*)"\[Mesh(?::NoExp)?\]', expression, flags=re.IGNORECASE)


@dataclass(frozen=True)
class PanelMember:
    key: str
    label: str
    mesh: str
    in_trajectory: bool


@dataclass(frozen=True)
class GbdMember:
    """One member of the GBD panel (Amendment v3.0, Section 5)."""

    rank: int                 # rank among all Level 3 causes by global DALYs 2023 (export)
    key: str                  # GBD_<CAUSE>, used as the field key of families GA, GD, GE
    cause: str                # GBD cause name as exported
    expression: str           # verbatim PubMed expression, see GBD_EXPRESSION_RE
    mesh_ui: str              # MeSH unique identifier(s) of the descriptor(s), for the record
    in_trajectory: bool       # False: descriptor introduced after 2015 (Q13 panel rule)
    shared_with: str | None   # key of the named field whose registered cells hold the counts
    date_introduced: str = ""
    scope_relation: str = ""
    inclusion_note: str = ""


@dataclass
class Catalogue:
    """Typed view of catalogue.yaml."""

    raw: dict[str, Any]
    path: Path | None = None
    text: str = field(default="", repr=False)
    gbd_raw: dict[str, Any] = field(default_factory=dict)
    gbd_path: Path | None = None
    gbd_text: str = field(default="", repr=False)

    # ---- basic sections -------------------------------------------------------------------
    @property
    def eutils(self) -> dict[str, Any]:
        return self.raw["eutils"]

    @property
    def freeze(self) -> dict[str, Any]:
        return self.raw["freeze"]

    @property
    def smoke_test(self) -> dict[str, Any]:
        return self.raw["smoke_test"]

    @property
    def sampling(self) -> dict[str, Any]:
        """Registered sampling section of v2.0 (kept for reference; superseded by amendment_sampling)."""
        return self.raw["sampling"]

    @property
    def identifiers(self) -> dict[str, Any]:
        return self.raw["identifiers"]

    @property
    def registration(self) -> dict[str, Any]:
        return self.raw["registration"]

    @property
    def fields(self) -> dict[str, dict[str, Any]]:
        return self.raw["fields"]

    @property
    def auxiliary(self) -> dict[str, str]:
        return self.raw["auxiliary"]

    @property
    def families(self) -> dict[str, dict[str, Any]]:
        """Registered families of v2.0 (single letters)."""
        return self.raw["families"]

    @property
    def lists(self) -> dict[str, Any]:
        """Registered family L section of v2.0 (kept for reference; superseded by amendment_lists)."""
        return self.raw["lists"]

    @property
    def clin_any(self) -> str:
        return self.raw["clin_any"]

    @property
    def year_clause_template(self) -> str:
        return self.raw["year_clause_template"]

    @property
    def primary_year(self) -> int:
        return int(self.raw["years"]["primary_year"])

    @property
    def subfields(self) -> dict[str, dict[str, Any]]:
        return self.raw["subfields"]

    # ---- amendment v3.0 -------------------------------------------------------------------
    @property
    def amendment(self) -> dict[str, Any]:
        return self.raw["amendment"]

    @property
    def amendment_auxiliary(self) -> dict[str, str]:
        return self.raw["amendment_auxiliary"]

    @property
    def amendment_named_field_ui(self) -> dict[str, str]:
        """MeSH unique identifiers of the named fields that a GBD cause can coincide with (Section 5.2)."""
        return self.raw["amendment_named_field_ui"]

    @property
    def amendment_families(self) -> dict[str, dict[str, Any]]:
        """New families of Amendment v3.0 (two-letter codes), in the order of its Section 4."""
        return self.raw["amendment_families"]

    @property
    def amendment_shared_cells(self) -> dict[str, dict[str, dict[str, str]]]:
        return self.raw["amendment_shared_cells"]

    @property
    def amendment_lists(self) -> dict[str, Any]:
        return self.raw["amendment_lists"]

    @property
    def amendment_sampling(self) -> dict[str, Any]:
        return self.raw["amendment_sampling"]

    @property
    def amendment_syntax_check(self) -> dict[str, Any]:
        return self.raw["amendment_syntax_check"]

    def all_families(self) -> dict[str, dict[str, Any]]:
        """Registered families in the order of tag v1.0 (sorted letters), then the amendment
        families in the order of the amendment. The first 2,034 queries of a run are therefore
        the registered catalogue of v1.0 in its original order."""
        out = {letter: self.families[letter] for letter in sorted(self.families)}
        out.update(self.amendment_families)
        return out

    def family(self, code: str) -> dict[str, Any]:
        if code in self.families:
            return self.families[code]
        if code in self.amendment_families:
            return self.amendment_families[code]
        raise CatalogueError(f"unknown family: {code}")

    # ---- GBD panel ------------------------------------------------------------------------
    @property
    def gbd_status(self) -> str:
        return str(self.gbd_raw.get("status", "missing"))

    @property
    def gbd_is_final(self) -> bool:
        return self.gbd_status == "final"

    @property
    def gbd_is_test_fixture(self) -> bool:
        """True for the synthetic panel of the test suite, which must never be sent to PubMed."""
        return bool(self.gbd_raw.get("test_fixture", False))

    def gbd_panel(self) -> list[GbdMember]:
        return [
            GbdMember(
                rank=int(m["rank"]),
                key=str(m["key"]),
                cause=str(m["cause"]),
                expression=str(m["expression"]),
                mesh_ui=str(m.get("mesh_ui", "")),
                in_trajectory=bool(m["in_trajectory"]),
                shared_with=(str(m["shared_with"]) if m.get("shared_with") else None),
                date_introduced=str(m.get("date_introduced", "")),
                scope_relation=str(m.get("scope_relation", "")),
                inclusion_note=str(m.get("inclusion_note", "")),
            )
            for m in (self.gbd_raw.get("members") or [])
        ]

    def gbd_member(self, key: str) -> GbdMember:
        for m in self.gbd_panel():
            if m.key == key:
                return m
        raise CatalogueError(f"unknown GBD panel member: {key}")

    def gbd_sha256(self) -> str:
        return hashlib.sha256(self.gbd_text.encode("utf-8")).hexdigest()

    # ---- derived accessors ----------------------------------------------------------------
    def field_group(self, name: str | list) -> list[str]:
        """Resolve a family 'fields' entry: a group name, 'subfields', a panel name, or a literal list.

        'panel_gbd' lists the GBD members that are queried, i.e. all members except those shared
        with a named field (Amendment v3.0, Section 5.2)."""
        if isinstance(name, list):
            return list(name)
        if name in self.raw["field_groups"]:
            return list(self.raw["field_groups"][name])
        if name == "subfields":
            return list(self.subfields.keys())
        if name == "panel_disease":
            return [m.key for m in self.panel("disease")]
        if name == "panel_technology":
            return [m.key for m in self.panel("technology")]
        if name == "panel_gbd":
            return [m.key for m in self.gbd_panel() if not m.shared_with]
        raise CatalogueError(f"unknown field group: {name}")

    def panel(self, which: str) -> list[PanelMember]:
        return [PanelMember(m["key"], m["label"], m["mesh"], bool(m["in_trajectory"])) for m in self.raw["panels"][which]]

    def panel_member(self, key: str) -> PanelMember:
        for which in ("disease", "technology"):
            for m in self.panel(which):
                if m.key == key:
                    return m
        raise CatalogueError(f"unknown panel member: {key}")

    def years_for_field(self, field_key: str) -> list[int]:
        """Publication-year window of a field (Q13): 2015 to 2024, COVID 2020 to 2024."""
        spec = self.raw["years"].get(field_key) or self.raw["years"]["default"]
        return list(range(int(spec["start"]), int(spec["end"]) + 1))

    def year_clause(self, year: int) -> str:
        """("YYYY"[pdat]) with YYYY replaced (12.4 YEAR)."""
        if not (1000 <= int(year) <= 9999):
            raise CatalogueError(f"year out of range: {year}")
        return self.year_clause_template.replace("YYYY", str(int(year)))

    def mesh_expression(self, field_key: str) -> str:
        """The MeSH expression for a named field, subfield, panel member or GBD member key."""
        if field_key in self.fields:
            return self.fields[field_key]["mesh"]
        if field_key in self.subfields:
            return self.auxiliary[field_key]
        if field_key.startswith("GBD_"):
            return self.gbd_member(field_key).expression
        return self.panel_member(field_key).mesh

    def tiab_expression(self, field_key: str) -> str:
        expr = self.fields[field_key].get("tiab")
        if not expr:
            raise CatalogueError(f"field {field_key} has no text-word expression")
        return expr

    def api_key_env(self) -> str:
        return self.eutils.get("api_key_env", "NCBI_API_KEY")


def load_catalogue(path: Path | str | None = None, gbd_panel_path: Path | str | None = None) -> Catalogue:
    """Load and validate the catalogue and the GBD panel file. Raises CatalogueError on structural problems.

    ``gbd_panel_path`` overrides the panel file named in the catalogue (used by the test suite)."""
    path = Path(path) if path else DEFAULT_CATALOGUE_PATH
    text = path.read_text(encoding="utf-8")
    raw = strict_yaml(text, f"catalogue file {path}")
    if not isinstance(raw, dict):
        raise CatalogueError("catalogue file is not a YAML mapping")
    if "amendment" not in raw:
        raise CatalogueError("catalogue has no 'amendment' section (pipeline v1.1.0 needs the addendum of Amendment v3.0)")
    gbd_path = Path(gbd_panel_path) if gbd_panel_path else path.parent / str(raw["amendment"].get("gbd_panel_file", "gbd_panel.yaml"))
    if not gbd_path.is_file():
        raise CatalogueError(f"GBD panel file not found: {gbd_path} (generate it with scripts/gbd_panel.py)")
    gbd_text = gbd_path.read_text(encoding="utf-8")
    gbd_raw = strict_yaml(gbd_text, f"GBD panel file {gbd_path}") or {}
    if not isinstance(gbd_raw, dict):
        raise CatalogueError(f"GBD panel file {gbd_path} is not a YAML mapping")
    cat = Catalogue(raw=raw, path=path, text=text, gbd_raw=gbd_raw, gbd_path=gbd_path, gbd_text=gbd_text)
    validate_catalogue(cat)
    return cat


def validate_catalogue(cat: Catalogue) -> None:
    """Structural checks. Content identity with the registration and with the amendment is
    checked in queries.check_against_preregistration and queries.check_against_amendment."""
    _validate_registered(cat)
    _validate_amendment(cat)
    _validate_gbd_panel(cat)


def _validate_registered(cat: Catalogue) -> None:
    """Checks of tag v1.0, unchanged."""
    required = ["registration", "eutils", "freeze", "smoke_test", "years", "year_clause_template", "fields",
                "field_groups", "auxiliary", "subfields", "panels", "clin_any", "families", "lists", "sampling",
                "identifiers"]
    missing = [k for k in required if k not in cat.raw]
    if missing:
        raise CatalogueError(f"catalogue missing sections: {missing}")

    letters = sorted(cat.families.keys())
    if letters != sorted(USED_FAMILY_LETTERS):
        raise CatalogueError(f"family letters {letters} differ from registered set {sorted(USED_FAMILY_LETTERS)}")
    for bad in UNUSED_FAMILY_LETTERS + [LIST_FAMILY, EFETCH_FAMILY]:
        if bad in cat.families:
            raise CatalogueError(f"family letter {bad} must not appear as a count family")

    if len(cat.panel("disease")) != 21:
        raise CatalogueError("disease panel must have 21 members")
    if len(cat.panel("technology")) != 9:
        raise CatalogueError("technology panel must have 9 members")
    keys = [m.key for m in cat.panel("disease")] + [m.key for m in cat.panel("technology")]
    if len(set(keys)) != len(keys):
        raise CatalogueError("panel member keys must be unique")

    expected_clin_any = "(" + " OR ".join(m.mesh for m in cat.panel("disease")) + ")"
    if cat.clin_any != expected_clin_any:
        raise CatalogueError("clin_any is not the OR-disjunction of the 21 disease-panel headings in registered order")

    if len(cat.field_group("named_fields")) != 10:
        raise CatalogueError("named_fields must list ten fields")
    if len(cat.field_group("comparators")) != 9:
        raise CatalogueError("comparators must list nine fields")
    for f in cat.field_group("named_fields"):
        if f not in cat.fields:
            raise CatalogueError(f"named field {f} not defined")
    for f in cat.field_group("tiab_fields") + cat.field_group("completeness_fields"):
        if not cat.fields[f].get("tiab"):
            raise CatalogueError(f"field {f} needs a text-word expression")

    for letter, fam in cat.families.items():
        if "metrics" not in fam or not fam["metrics"]:
            raise CatalogueError(f"family {letter} has no metrics")
        cat.field_group(fam["fields"])  # raises on unknown group
        for metric, template in fam["metrics"].items():
            _check_template(letter, metric, template, TEMPLATE_PLACEHOLDERS)

    if cat.year_clause_template != cat.auxiliary["YEAR"]:
        raise CatalogueError("year_clause_template must equal auxiliary YEAR")
    if int(cat.sampling["seed"]) != 20260904:
        raise CatalogueError("sampling seed must be 20260904 (Q13)")
    if int(cat.eutils["max_attempts"]) != 6 or list(cat.eutils["backoff_seconds"]) != [1, 2, 4, 8, 16, 32]:
        raise CatalogueError("retry schedule must be 1, 2, 4, 8, 16, 32 seconds with six attempts (Q9)")


def _check_template(family: str, metric: str, template: str, allowed: tuple[str, ...]) -> None:
    if not template.endswith("{YEAR}"):
        raise CatalogueError(f"family {family} metric {metric}: the year clause must be last (12.2)")
    if "  " in template:
        raise CatalogueError(f"family {family} metric {metric}: double space in template")
    for token in _placeholders_in(template):
        if token not in allowed:
            raise CatalogueError(f"family {family} metric {metric}: unknown placeholder {token}")


def _validate_amendment(cat: Catalogue) -> None:
    missing = [k for k in ADDENDUM_KEYS if k not in cat.raw]
    if missing:
        raise CatalogueError(f"catalogue missing amendment sections: {missing}")

    # 1. The registered catalogue of tag v1.0 is an unchanged prefix of this file. Length and hash
    #    are constants of this module; the values written in the file must repeat them.
    n = REGISTERED_PREFIX_CHARS
    digest = hashlib.sha256(cat.text[:n].encode("utf-8")).hexdigest()
    if digest != REGISTERED_PREFIX_SHA256:
        raise CatalogueError(
            "the registered part of config/catalogue.yaml (tag v1.0) was modified: SHA-256 of the first "
            f"{n} characters is {digest}, expected {REGISTERED_PREFIX_SHA256}. "
            "The registered catalogue must never be edited; restore it from tag v1.0."
        )
    if int(cat.amendment["registered_prefix_chars"]) != n or cat.amendment["registered_prefix_sha256"] != REGISTERED_PREFIX_SHA256:
        raise CatalogueError("amendment.registered_prefix_chars and registered_prefix_sha256 must state the values of tag v1.0")
    registered = strict_yaml(cat.text[:n], "the registered part of the catalogue") or {}
    #    Nothing after the prefix may redefine a registered section, and nothing but the addendum may follow it.
    for key, value in registered.items():
        if cat.raw.get(key) != value:
            raise CatalogueError(f"the registered section {key!r} is changed by text that follows the registered part of the catalogue")
    foreign = [k for k in cat.raw if k not in registered and k not in ADDENDUM_KEYS]
    if foreign or [k for k in registered if k.startswith("amendment")]:
        raise CatalogueError(f"unexpected top-level sections in the catalogue: {foreign}; after the registered part only "
                             f"the sections {ADDENDUM_KEYS} are allowed")

    # 2. Auxiliary expression of the amendment equals the registered text-word expression of AI.
    if cat.amendment_auxiliary.get("AI_TIAB_TERMS") != cat.fields["AI"]["tiab"]:
        raise CatalogueError("AI_TIAB_TERMS must equal the registered text-word expression of AI (12.3)")

    # 3. Family codes: exactly the codes of the amendment, in its order, distinct from every registered letter.
    codes = list(cat.amendment_families.keys())
    if codes != AMENDMENT_FAMILY_CODES:
        raise CatalogueError(f"amendment family codes {codes} differ from the amendment (Section 4): {AMENDMENT_FAMILY_CODES}")
    for code in codes + [AMENDMENT_LIST_FAMILY]:
        if len(code) != 2 or code in cat.families or code in UNUSED_FAMILY_LETTERS:
            raise CatalogueError(f"amendment family code {code} must be a new two-letter code")

    # 4. Templates: year clause last, known placeholders, only registered components, RCT variants derived by rule.
    components = _registered_components(cat)
    for code, fam in cat.amendment_families.items():
        if "metrics" not in fam or not fam["metrics"]:
            raise CatalogueError(f"family {code} has no metrics")
        group = fam["fields"]
        if group != "panel_gbd":
            cat.field_group(group)  # raises on unknown group
        for metric, template in fam["metrics"].items():
            _check_template(code, metric, template, AMENDMENT_TEMPLATE_PLACEHOLDERS)
            residual = _residual(template, components)
            if residual:
                raise CatalogueError(
                    f"family {code} metric {metric}: template contains text that is neither a registered "
                    f"component nor a connector: {residual!r}")
            if template.count("(") != template.count(")"):
                raise CatalogueError(f"family {code} metric {metric}: unbalanced parentheses")
        for metric, template in fam["metrics"].items():
            base = _base_metric_of_rct_variant(metric, fam["metrics"])
            if base is not None:
                expected = fam["metrics"][base][: -len(" AND {YEAR}")] + RCT_CLAUSE + " AND {YEAR}"
                if template != expected:
                    raise CatalogueError(
                        f"family {code} metric {metric} is not 'the same with RCT' as {base}: the RCT clause "
                        "must be inserted directly before the year clause (amendment, Section 4)")
            # A metric named ai... selects the field WITH an AI definition, one named nonai... the field
            # WITHOUT it: the name and the template must not drift apart (two swapped templates would
            # still be found in the amendment text).
            stem = metric[2:] if metric.startswith("S_") else metric
            if stem.startswith("nonai") and not re.match(r'^\("Stroke"\[Mesh\] (AND medline\[sb\] )?NOT ', template):
                raise CatalogueError(f"family {code} metric {metric}: a nonai metric must begin with (\"Stroke\"[Mesh] ... NOT <AI definition>")
            if stem.startswith("ai") and not template.startswith('"Stroke"[Mesh] AND '):
                raise CatalogueError(f"family {code} metric {metric}: an ai metric must begin with \"Stroke\"[Mesh] AND <AI definition>")

    # 5. Shared cells of GBD members that coincide with a named field.
    shared = cat.amendment_shared_cells
    if sorted(shared) != sorted(GBD_FAMILIES):
        raise CatalogueError(f"amendment_shared_cells must cover exactly the families {list(GBD_FAMILIES)}")
    for code in GBD_FAMILIES:
        if sorted(shared[code]) != sorted(cat.amendment_families[code]["metrics"]):
            raise CatalogueError(f"amendment_shared_cells.{code} must name every metric of family {code}")
        for metric, target in shared[code].items():
            if target["metric"] not in cat.family(target["family"])["metrics"]:
                raise CatalogueError(f"amendment_shared_cells.{code}.{metric}: unknown target {target}")

    # 6. Lists and sampling.
    lists = cat.amendment_lists
    if int(lists["year"]) != cat.primary_year:
        raise CatalogueError("amendment_lists.year must be the primary year")
    keys = [x["key"] for x in lists["lists"]]
    if len(set(keys)) != len(keys):
        raise CatalogueError("amendment_lists keys must be unique")
    for x in lists["lists"]:
        if x["list_family"] not in (LIST_FAMILY, AMENDMENT_LIST_FAMILY):
            raise CatalogueError(f"list {x['key']}: list_family must be L or LV")
        if x["metric"] not in cat.family(x["family"])["metrics"]:
            raise CatalogueError(f"list {x['key']}: unknown family or metric")
        if x["field"] not in cat.fields:
            raise CatalogueError(f"list {x['key']}: unknown field {x['field']}")
        if not x["key"].endswith("_" + x["field"]):
            raise CatalogueError(f"list {x['key']}: the key must end with _<FIELD>")
        if x.get("efetch") not in ("all", "sampled", "none"):
            raise CatalogueError(f"list {x['key']}: efetch must be all, sampled or none")
    registered_l = [(c["family"], c["metric"], f) for c in cat.lists["cells"] for f in cat.field_group(cat.lists["fields"])]
    addendum_l = [(x["family"], x["metric"], x["field"]) for x in lists["lists"] if x["list_family"] == LIST_FAMILY]
    if addendum_l != registered_l:
        raise CatalogueError("the family L entries of amendment_lists must repeat the registered family L lists in registered order")
    for part in lists.get("partitions", []):
        for k in [part["whole"], *part["parts"]]:
            if k not in keys:
                raise CatalogueError(f"partition refers to unknown list {k}")

    samp = cat.amendment_sampling
    if int(samp["seed"]) != 20260904:
        raise CatalogueError("amendment_sampling.seed must be 20260904 (Q13)")
    if int(samp["pilot_per_cell"]) != int(cat.sampling["pilot_per_cell"]):
        raise CatalogueError("amendment_sampling.pilot_per_cell must equal the registered pilot size")
    cells = [c["cell"] for c in samp["cells"]]
    if len(set(cells)) != len(cells):
        raise CatalogueError("amendment_sampling cell names must be unique")
    efetch_all = {x["key"] for x in lists["lists"] if x["efetch"] == "all"}
    for c in samp["cells"]:
        if c["list"] not in keys:
            raise CatalogueError(f"cell {c['cell']}: unknown list {c['list']}")
        if c.get("xml_from") and c["xml_from"] not in efetch_all:
            raise CatalogueError(f"cell {c['cell']}: xml_from must name a list that is fetched completely")
        if int(c["sample_size"]) <= 0:
            raise CatalogueError(f"cell {c['cell']}: sample_size must be positive")

    # 7. Syntax check plan: registered smoke year, registered smoke field as stand-in, known cells only.
    sc = cat.amendment_syntax_check
    if int(sc["year"]) != int(cat.smoke_test["year"]) or sc["stand_in_field"] != cat.smoke_test["field"]:
        raise CatalogueError("amendment_syntax_check must use the registered smoke year and smoke field (Q8, Q18)")
    if sc["replaced_field"] != PROTECTED_FIELD:
        raise CatalogueError(f"amendment_syntax_check.replaced_field must be {PROTECTED_FIELD}")
    q18 = {f"{cat.smoke_test['family']}/{cat.smoke_test['metric']}"} | set(cat.smoke_test.get("other_reference_counts") or {})
    for a in sc["anchors"]:
        if a["family"] not in cat.families or a["metric"] not in cat.families[a["family"]]["metrics"]:
            raise CatalogueError(f"syntax check anchor {a} is not a registered cell")
        if f"{a['family']}/{a['metric']}" not in q18:
            raise CatalogueError(f"syntax check anchor {a} has no value disclosed in Q18; only disclosed smoke cells may be read again")
        if RCT_CLAUSE in cat.families[a["family"]]["metrics"][a["metric"]]:
            raise CatalogueError(f"syntax check anchor {a} is an RCT numerator; RCT numerators are not read in the syntax check")
    for c in sc["compositions"]:
        if c["family"] not in cat.amendment_families or c["metric"] not in cat.amendment_families[c["family"]]["metrics"]:
            raise CatalogueError(f"syntax check composition {c} is not an amendment cell")
        template = cat.amendment_families[c["family"]]["metrics"][c["metric"]]
        if RCT_CLAUSE in template or CT_CLAUSE in template:
            # Amendment v3.0, Sections 1.4 and 8.2: no within-field RCT count is viewed before the freeze run.
            raise CatalogueError(f"syntax check composition {c} is a within-field trial numerator; it must not be run before the "
                                 "freeze run (amendment, Sections 1.4 and 8.2)")
    g = sc["gbd_descriptors"]
    if g["family"] not in GBD_FAMILIES or g["metric"] not in cat.amendment_families[g["family"]]["metrics"]:
        raise CatalogueError("syntax check gbd_descriptors must name a metric of a GBD family")
    known = {f"{a['family']}/{a['metric']}" for a in sc["anchors"]} | {f"{c['family']}/{c['metric']}" for c in sc["compositions"]}
    for ident in sc.get("identities", []):
        if ident["type"] not in ("equal", "at_most"):
            raise CatalogueError(f"syntax check identity {ident['name']!r}: unknown type")
        for term in list(ident["left"]) + list(ident["right"]):
            if str(term).lstrip("-") not in known:
                raise CatalogueError(f"syntax check identity {ident['name']!r} refers to unknown cell {term}")


def _validate_gbd_panel(cat: Catalogue) -> None:
    """The GBD panel file. A provisional panel may be loaded (development, tests of other
    families); the online modes that need the panel refuse to run unless it is final."""
    status = cat.gbd_status
    if status not in ("final", "provisional"):
        raise CatalogueError(f"GBD panel file {cat.gbd_path}: status must be 'final' or 'provisional', found {status!r}")
    try:
        members = cat.gbd_panel()
    except (KeyError, TypeError, ValueError) as exc:
        raise CatalogueError(f"GBD panel file {cat.gbd_path}: a member lacks a field or has a malformed value ({exc!r}); "
                             "the file is generated by scripts/gbd_panel.py and must not be edited by hand") from exc
    if status == "final" and len(members) != GBD_PANEL_SIZE:
        raise CatalogueError(f"a final GBD panel must have exactly {GBD_PANEL_SIZE} members, found {len(members)}")
    if len(members) > GBD_PANEL_SIZE:
        raise CatalogueError(f"the GBD panel must not have more than {GBD_PANEL_SIZE} members")
    if status == "final" and not cat.gbd_is_test_fixture:
        # A final panel carries the evidence of how it was made: two raters, the ranking, the raw export.
        source = cat.gbd_raw.get("source") or {}
        if not str(source.get("raters", "")).strip():
            raise CatalogueError(f"GBD panel file {cat.gbd_path}: a final panel must name the two raters (written by 'reconcile')")
        for key in ("mapping_table_sha256", "ranking_sha256", "raw_export_sha256"):
            if not re.fullmatch(r"[0-9a-f]{64}", str(source.get(key, ""))):
                raise CatalogueError(f"GBD panel file {cat.gbd_path}: a final panel must state {key} "
                                     "(written by 'rank' and 'reconcile' of scripts/gbd_panel.py)")
    keys = [m.key for m in members]
    if len(set(keys)) != len(keys):
        raise CatalogueError("GBD panel keys must be unique")
    ranks = [m.rank for m in members]
    if ranks != sorted(ranks) or len(set(ranks)) != len(ranks):
        raise CatalogueError("GBD panel members must be listed in ascending rank order without ties")
    expressions = [m.expression for m in members]
    if len({normalise_heading(e) for e in expressions}) != len(expressions):
        raise CatalogueError("two GBD panel members share one expression")
    other_keys = set(cat.fields) | set(cat.subfields) | {m.key for w in ("disease", "technology") for m in cat.panel(w)}
    comparators = cat.field_group("comparators")
    registered_headings = {normalise_heading(h): h for f in cat.fields.values() for h in mesh_headings(f["mesh"])}
    field_ui = {str(ui): key for key, ui in cat.amendment_named_field_ui.items()}
    for key in field_ui.values():
        if key not in comparators:
            raise CatalogueError(f"amendment_named_field_ui names {key}, which is not one of the nine comparators")
    default_years = cat.years_for_field("default")
    for m in members:
        if not GBD_KEY_RE.match(m.key) or m.key in other_keys:
            raise CatalogueError(f"GBD panel key {m.key!r} is not of the form GBD_<CAUSE>")
        if not GBD_EXPRESSION_RE.match(m.expression):
            raise CatalogueError(
                f"GBD panel member {m.key}: expression {m.expression!r} is neither \"<Heading>\"[Mesh] nor "
                "(\"<Heading>\"[Mesh] NOT \"<Heading>\"[Mesh])")
        # PubMed ignores case and surrounding blanks in a heading. A heading that names a registered
        # field must therefore be written exactly as registered, or the field would not be recognised.
        for heading in mesh_headings(m.expression):
            canonical = registered_headings.get(normalise_heading(heading))
            if canonical is not None and heading != canonical:
                raise CatalogueError(f"GBD panel member {m.key}: the heading {heading!r} is the registered heading {canonical!r} "
                                     "in another spelling; write it exactly as registered")
        same = [k for k, f in cat.fields.items() if f["mesh"] == m.expression]
        first_ui = (re.findall(r"D\d+", m.mesh_ui) or [""])[0]
        if m.shared_with:
            if m.shared_with not in comparators:
                raise CatalogueError(f"GBD panel member {m.key}: shared_with must be one of the nine comparators")
            if cat.fields[m.shared_with]["mesh"] != m.expression:
                raise CatalogueError(f"GBD panel member {m.key}: expression differs from the named field {m.shared_with}")
            if cat.years_for_field(m.shared_with) != default_years and m.in_trajectory:
                # Amendment, Section 5.2: a member shared with a named field of a shorter year window (COVID-19,
                # 2020 to 2024) shares the cells of that window only. It has no cell for the years before the
                # window and therefore no trajectory (panel rule of Q13: 2024 and pooled windows only).
                raise CatalogueError(f"GBD panel member {m.key} is shared with {m.shared_with}, whose year window is shorter than "
                                     "2015 to 2024; such a member has cells for that window only and must not be part of the "
                                     "trajectory (in_trajectory: false)")
        elif same:
            raise CatalogueError(
                f"GBD panel member {m.key} has the expression of the named field {same[0]}; set shared_with "
                "so that its cells are shared and not queried again (amendment, Section 5.2)")
        elif m.expression.startswith('"') and first_ui in field_ui:
            # another name (an entry term) of the descriptor of a named field: PubMed maps it to that field
            raise CatalogueError(f"GBD panel member {m.key}: {m.expression} has the MeSH unique identifier {first_ui} of the named "
                                 f"field {field_ui[first_ui]}; use the expression of the named field (amendment, Section 5.2)")


def _registered_components(cat: Catalogue) -> list[str]:
    """Every registered string that may appear literally inside an amendment template, longest first."""
    comps = {f["mesh"] for f in cat.fields.values()}
    comps |= {v for k, v in cat.auxiliary.items() if k != "YEAR"}
    comps.add('"Robotics"[Mesh]')  # part of the registered F_AI_NOROB; listed for clarity
    return sorted(comps, key=len, reverse=True)


def _residual(template: str, components: list[str]) -> str:
    """What is left of a template after removing placeholders, registered components and the
    connectors AND, NOT and parentheses. Empty for a well-formed amendment template."""
    rest = template
    for token in _placeholders_in(template):
        rest = rest.replace(token, " ")
    for comp in components:
        rest = rest.replace(comp, " ")
    rest = re.sub(r"\b(AND|NOT)\b", " ", rest)
    rest = rest.replace("(", " ").replace(")", " ")
    return rest.strip()


def _base_metric_of_rct_variant(metric: str, metrics: dict[str, str]) -> str | None:
    """'rct' is the RCT variant of 'den'; '<x>_rct' of '<x>_den'. None when there is no such pair."""
    if metric == "rct" and "den" in metrics:
        return "den"
    if metric.endswith("_rct") and metric[: -len("_rct")] + "_den" in metrics:
        return metric[: -len("_rct")] + "_den"
    return None


def _placeholders_in(template: str) -> list[str]:
    out, i = [], 0
    while True:
        i = template.find("{", i)
        if i < 0:
            return out
        j = template.find("}", i)
        if j < 0:
            raise CatalogueError(f"unbalanced brace in template: {template}")
        out.append(template[i : j + 1])
        i = j + 1
