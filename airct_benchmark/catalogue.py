"""Load and validate config/catalogue.yaml, the verbatim query catalogue of Q12.

The catalogue is data, not code. This module only reads it, checks its structure and exposes
typed accessors. Nothing in here may alter a registered string.
"""

from __future__ import annotations

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


class CatalogueError(ValueError):
    """Raised when the catalogue file is structurally invalid."""


@dataclass(frozen=True)
class PanelMember:
    key: str
    label: str
    mesh: str
    in_trajectory: bool


@dataclass
class Catalogue:
    """Typed view of catalogue.yaml."""

    raw: dict[str, Any]
    path: Path | None = None
    text: str = field(default="", repr=False)

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
        return self.raw["families"]

    @property
    def lists(self) -> dict[str, Any]:
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

    # ---- derived accessors ----------------------------------------------------------------
    def field_group(self, name: str | list) -> list[str]:
        """Resolve a family 'fields' entry: a group name, 'subfields', a panel name, or a literal list."""
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
        """The MeSH expression for a named field, subfield or panel member key."""
        if field_key in self.fields:
            return self.fields[field_key]["mesh"]
        if field_key in self.subfields:
            return self.auxiliary[field_key]
        return self.panel_member(field_key).mesh

    def tiab_expression(self, field_key: str) -> str:
        expr = self.fields[field_key].get("tiab")
        if not expr:
            raise CatalogueError(f"field {field_key} has no text-word expression")
        return expr

    def api_key_env(self) -> str:
        return self.eutils.get("api_key_env", "NCBI_API_KEY")


def load_catalogue(path: Path | str | None = None) -> Catalogue:
    """Load and validate the catalogue. Raises CatalogueError on structural problems."""
    path = Path(path) if path else DEFAULT_CATALOGUE_PATH
    text = path.read_text(encoding="utf-8")
    raw = yaml.safe_load(text)
    cat = Catalogue(raw=raw, path=path, text=text)
    validate_catalogue(cat)
    return cat


def validate_catalogue(cat: Catalogue) -> None:
    """Structural checks. Content identity with the registration is checked in queries.check_against_preregistration."""
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
            if not template.endswith("{YEAR}"):
                raise CatalogueError(f"family {letter} metric {metric}: the year clause must be last (12.2)")
            if "  " in template:
                raise CatalogueError(f"family {letter} metric {metric}: double space in template")
            for token in _placeholders_in(template):
                if token not in TEMPLATE_PLACEHOLDERS:
                    raise CatalogueError(f"family {letter} metric {metric}: unknown placeholder {token}")

    if cat.year_clause_template != cat.auxiliary["YEAR"]:
        raise CatalogueError("year_clause_template must equal auxiliary YEAR")
    if int(cat.sampling["seed"]) != 20260904:
        raise CatalogueError("sampling seed must be 20260904 (Q13)")
    if int(cat.eutils["max_attempts"]) != 6 or list(cat.eutils["backoff_seconds"]) != [1, 2, 4, 8, 16, 32]:
        raise CatalogueError("retry schedule must be 1, 2, 4, 8, 16, 32 seconds with six attempts (Q9)")


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
