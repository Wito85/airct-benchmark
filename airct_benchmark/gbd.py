"""GBD panel: the rules that turn a reconciled mapping table into the panel (Amendment v3.0,
Section 5), shared by scripts/gbd_panel.py, which builds the panel, and by the identity check,
which verifies it independently of the script that wrote it.

Pure functions on files of the repository. Nothing in here contacts a server.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from pathlib import Path
from typing import Iterable

PANEL_SIZE = 20
KEPT = "kept for mapping"
MAPPED = "mapped"
RULE_D = "excluded rule (d)"
RECONCILIATION_VALUES = ("agreed independently", "agreed after discussion")
MEMBER_KEYS = ["rank", "key", "cause", "expression", "mesh_ui", "date_introduced", "in_trajectory", "shared_with",
               "scope_relation", "inclusion_note"]

TABLE_HEADER = ("| Rank 2023 | GBD Level 3 cause | Query expression (verbatim) | MeSH UI | Introduced | Scope relation | "
                "Stated over- or under-inclusion | Cells |")
TABLE_RULE = "|---|---|---|---|---|---|---|---|"
AMENDMENT_TABLE_FILE = "data/gbd/gbd_panel_amendment_table.md"   # the generated text of Section 5.7, relative to the repository root

_MESH_TERM = r'"[A-Za-z0-9][A-Za-z0-9 ,\'\-/().&]*"\[Mesh\]'
EXPRESSION_RE = re.compile(rf"^(?:{_MESH_TERM}|\({_MESH_TERM} NOT {_MESH_TERM}\))$")
_TABLE_ROW_RE = re.compile(r"^\| (\d+) \| (.*) \|$")


class GbdPanelError(ValueError):
    """The mapping table, the ranking or the export record do not support the panel."""


# ---------------------------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------------------------

def sha256_text(path: Path | str) -> str:
    """SHA-256 of a text file's content with LF line endings (UTF-8): the same value on every
    platform and after every checkout, and the value the pipeline writes into the frozen files."""
    return hashlib.sha256(Path(path).read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def read_csv_dicts_from_text(text: str) -> list[dict]:
    """Rows of CSV text as dicts. Comma or semicolon separated; cell values are stripped."""
    text = text.lstrip("\ufeff")
    first_line = text.split("\n", 1)[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter)
    return [{(k or "").strip(): ("" if v is None else str(v).strip()) for k, v in r.items()} for r in reader]


def read_csv_dicts(path: Path | str) -> list[dict]:
    """Rows of a CSV file as dicts. Comma or semicolon separated, with or without a byte order mark."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return read_csv_dicts_from_text(fh.read())


def norm_name(name: str) -> str:
    """Spelling-insensitive key of a cause name: 'Ischaemic heart disease' equals 'Ischemic heart
    disease', 'Diarrhoeal diseases' equals 'Diarrheal diseases'."""
    s = str(name).strip().lower().replace("ae", "e").replace("oe", "e")
    return re.sub(r"[^a-z0-9]+", "", s)


def gbd_key(cause: str) -> str:
    """GBD_<CAUSE> in upper case; apostrophes are dropped, every other run of non-alphanumeric
    characters becomes one underscore: 'HIV/AIDS' gives GBD_HIV_AIDS, "Alzheimer's disease and
    other dementias" gives GBD_ALZHEIMERS_DISEASE_AND_OTHER_DEMENTIAS."""
    s = str(cause).replace("'", "").replace("’", "")
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").upper()
    return "GBD_" + s


def one_line(text: str) -> str:
    """A cell value on one line: line breaks and repeated blanks become one blank."""
    return " ".join(str(text or "").split())


def rank_of(value: str) -> int:
    """A rank cell as an integer ('7', '7.0'); raises GbdPanelError for anything else."""
    s = str(value).strip()
    if re.fullmatch(r"\d+(\.0+)?", s):
        return int(s.split(".")[0])
    raise GbdPanelError(f"rank {value!r} is not a whole number")


# ---------------------------------------------------------------------------------------------
# mapping table -> panel members
# ---------------------------------------------------------------------------------------------

def raters_of_mapping(rows: list[dict]) -> tuple[str, str]:
    """The two rater keys of a reconciled mapping table (columns choice_<key>)."""
    keys = [c[len("choice_"):] for c in (rows[0].keys() if rows else []) if c.startswith("choice_")]
    if len(keys) != 2 or keys[0] == keys[1] or not all(keys):
        raise GbdPanelError("the mapping table has no two columns choice_<rater>; it was not written by 'reconcile'")
    return keys[0], keys[1]


def check_reconciled(rows: list[dict]) -> tuple[str, str]:
    """A mapping table supports a FINAL panel only if every row records two independent choices
    and how they were reconciled. Returns the two rater keys."""
    r1, r2 = raters_of_mapping(rows)
    for r in rows:
        if r.get("reconciliation") not in RECONCILIATION_VALUES or not r.get(f"choice_{r1}") or not r.get(f"choice_{r2}"):
            raise GbdPanelError(f"mapping row '{r.get('gbd_cause')}' records no reconciled choice of the two raters")
    return r1, r2


def members_from_mapping(rows: list[dict], field_by_mesh: dict[str, str], size: int = PANEL_SIZE) -> list[dict]:
    """The panel: the first ``size`` mapped causes of the mapping table in rank order."""
    needed = ["rank", "gbd_cause", "decision", "expression", "mesh_ui", "date_introduced", "scope_relation", "inclusion_note"]
    if not rows or any(k not in rows[0] for k in needed):
        raise GbdPanelError(f"the mapping table lacks columns; needed: {needed}")
    ordered = sorted(rows, key=lambda r: rank_of(r["rank"]))
    ranks = [rank_of(r["rank"]) for r in ordered]
    if len(set(ranks)) != len(ranks):
        raise GbdPanelError("two rows of the mapping table have the same rank")
    members: list[dict] = []
    for r in ordered:
        if r["decision"] == RULE_D:
            continue
        if r["decision"] != MAPPED:
            raise GbdPanelError(f"mapping row '{r['gbd_cause']}': decision must be '{MAPPED}' or '{RULE_D}', found {r['decision']!r}")
        if not EXPRESSION_RE.match(r["expression"]):
            raise GbdPanelError(f"mapping row '{r['gbd_cause']}': expression {r['expression']!r} is not of the allowed form")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["date_introduced"]):
            raise GbdPanelError(f"mapping row '{r['gbd_cause']}': date_introduced must be YYYY-MM-DD (MeSH Browser, Date Introduced), "
                                f"found {r['date_introduced']!r}")
        if not re.fullmatch(r"D\d+( NOT D\d+)?", r["mesh_ui"]):
            raise GbdPanelError(f"mapping row '{r['gbd_cause']}': mesh_ui must be a MeSH unique identifier (D and digits), found {r['mesh_ui']!r}")
        shared = field_by_mesh.get(r["expression"])
        if shared == "AI":
            raise GbdPanelError("a GBD cause cannot be mapped to the AI field expression")
        members.append({
            "rank": rank_of(r["rank"]), "key": gbd_key(r["gbd_cause"]), "cause": one_line(r["gbd_cause"]), "expression": r["expression"],
            "mesh_ui": r["mesh_ui"], "date_introduced": r["date_introduced"], "in_trajectory": int(r["date_introduced"][:4]) <= 2015,
            "shared_with": shared, "scope_relation": one_line(r["scope_relation"]), "inclusion_note": one_line(r["inclusion_note"]),
        })
        if len(members) == size:
            break
    return members


def problems_against_ranking(rows: list[dict], ranking: list[dict], last_rank: int | None = None) -> list[str]:
    """Check a mapping table (or the rows of a rater sheet) against the deposited ranking.

    * every row is a cause of the ranking, with the rank of the ranking, that passed rules (a) to (c);
    * the rows are exactly the first causes of the ranking that passed those rules: none is skipped
      (up to ``last_rank`` when given, otherwise up to the last row).
    """
    problems: list[str] = []
    by_name = {norm_name(r["cause_name"]): r for r in ranking}
    seen: set[str] = set()
    for r in rows:
        name = norm_name(r["gbd_cause"])
        x = by_name.get(name)
        if x is None:
            problems.append(f"'{r['gbd_cause']}' is not a cause of the ranking")
            continue
        if name in seen:
            problems.append(f"'{r['gbd_cause']}' occurs twice")
        seen.add(name)
        try:
            rank = rank_of(r["rank"])
        except GbdPanelError as exc:
            problems.append(f"'{r['gbd_cause']}': {exc}")
            continue
        if rank != rank_of(x["rank"]):
            problems.append(f"'{r['gbd_cause']}' has rank {rank}, the ranking says {x['rank']}")
        if x["panel_rule_result"] != KEPT:
            problems.append(f"'{r['gbd_cause']}' is excluded by the ranking ({x.get('exclusion_reason', '')}) and cannot be mapped")
    if problems:
        return problems
    limit = last_rank if last_rank is not None else max((rank_of(r["rank"]) for r in rows), default=0)
    for x in sorted(ranking, key=lambda r: rank_of(r["rank"])):
        if rank_of(x["rank"]) <= limit and x["panel_rule_result"] == KEPT and norm_name(x["cause_name"]) not in seen:
            problems.append(f"'{x['cause_name']}' (rank {x['rank']}) passed rules (a) to (c) but is missing; no cause may be skipped")
    return problems


# ---------------------------------------------------------------------------------------------
# table for the amendment
# ---------------------------------------------------------------------------------------------

def cells_label(member: dict) -> str:
    if member.get("shared_with"):
        return f"shared with {member['shared_with']}"
    return "queried" if member.get("in_trajectory") else "queried; 2024 and pooled windows only"


def table_row(member: dict) -> str:
    """One row of the panel table of the amendment (Section 5), exactly as it has to stand there."""
    cell = lambda v: one_line(v).replace("|", "/")   # noqa: E731
    return (f"| {member['rank']} | {cell(member['cause'])} | {member['expression']} | {member['mesh_ui']} | "
            f"{str(member['date_introduced'])[:4]} | {cell(member['scope_relation'])} | {cell(member['inclusion_note'])} | "
            f"{cells_label(member)} |")


def table_rows_in_text(text: str) -> list[str]:
    """Every line of a text that is a row of a panel table: eight cells, the first a rank, the
    third a query expression. Other tables of the amendment do not match."""
    out = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = line.strip()
        m = _TABLE_ROW_RE.match(line)
        if not m:
            continue
        cells = line[2:-2].split(" | ")
        if len(cells) == 8 and EXPRESSION_RE.match(cells[2].strip()):
            out.append(line)
    return out


def volume_line(n_additional: int, n_total: int) -> str:
    """The last line of the generated text of Section 5.7: the catalogue volume with the panel."""
    return f"Catalogue volume with this panel: {n_additional:,} additional count requests, {n_total:,} per run."


def amendment_block(root: Path) -> str:
    """The text of Section 5.7 as generated by scripts/gbd_panel.py (AMENDMENT_TABLE_FILE under ``root``):
    from its first line that is not an HTML comment to its last line, with LF line endings and without
    blanks at line ends. Empty if the file does not exist or holds no text."""
    path = Path(root) / AMENDMENT_TABLE_FILE
    if not path.is_file():
        return ""
    content = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = [line.rstrip() for line in content.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and (not lines[0] or lines[0].startswith("<!--")):
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _first_difference(block: str, text: str) -> str:
    """Where a text stops following the generated block (for the message of amendment_block_check)."""
    lo, hi = 0, len(block)
    while lo < hi:                                   # the longest beginning of the block that stands in the text
        mid = (lo + hi + 1) // 2
        if block[:mid] in text:
            lo = mid
        else:
            hi = mid - 1
    first_line = block.split("\n", 1)[0]
    if lo < min(len(first_line), 20):
        return f"the generated text does not begin anywhere in the amendment; its first line is \"{first_line[:120]}\""
    line_no = block.count("\n", 0, lo) + 1
    column = lo - (block.rfind("\n", 0, lo) + 1) + 1
    at = text.find(block[:lo]) + lo

    def around(s: str, i: int) -> str:
        return one_line(s[max(0, i - 40): i + 40].replace("\n", " / "))

    return (f"first difference in line {line_no} of the generated text, at character {column}: there the generated text reads "
            f"\"{around(block, lo)}\" and the amendment \"{around(text, at)}\" (a line break is shown as /)")


def amendment_block_check(panel: dict, panel_sha256: str, root: Path, amendment_text: str,
                          required_lines: Iterable[str] = ()) -> tuple[bool, bool, str]:
    """Does Section 5.7 stand in the amendment as generated? Returns (strict, up to whitespace, finding).

    The rows of the table are compared with the panel file one by one elsewhere. This check covers the
    text around them, which a reader cannot verify by eye: the causes ranked above the last member that
    are not in the panel, the export line with the SHA-256 values, and the catalogue volume.

    The amendment is compared with the deposited file AMENDMENT_TABLE_FILE, not with a text composed
    anew. The file is therefore tested first: it must state the SHA-256 of the panel file as it is now
    and of the mapping table, the ranking and the raw export that the panel file names; the date, person,
    permalink and hierarchy hash of the export record; and every line of ``required_lines`` (the table
    of the panel file and the catalogue volume, as the caller computes them now). A file that fails one
    of these was not written for this panel. The raters named in the file must be those of the panel
    file. The list of causes that are not in the panel is not composed anew here;
    'python scripts/gbd_panel.py build --status final' writes the file again from the mapping table
    and the ranking, and is run before this check.

    Strict: the block stands in the amendment, line for line, in one piece (line endings and blanks at
    line ends do not count). Text on the same line before its first or after its last line is not noticed."""
    remedy = "run 'python scripts/gbd_panel.py build --status final' and paste the new text into the amendment"
    block = amendment_block(root)
    if not block:
        return False, False, f"{AMENDMENT_TABLE_FILE} not found or without text; {remedy}"
    source = panel.get("source") or {}
    stated = [panel_sha256] + [str(source.get(k) or "") for k in ("mapping_table_sha256", "ranking_sha256", "raw_export_sha256")]
    if not all(h and h in block for h in stated):
        return False, False, (f"{AMENDMENT_TABLE_FILE} does not state the SHA-256 of the current panel file, mapping table, ranking "
                              f"and raw export; {remedy}")
    raters = str(source.get("raters") or "")
    if raters and f"by the rule of 5.3 by {raters}." not in block:
        return False, False, f"{AMENDMENT_TABLE_FILE} does not name the raters of the panel file ({raters}); {remedy}"
    record_path = Path(root) / "data" / "gbd" / "gbd_export_record.json"
    try:
        record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.is_file() else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        record = {}
    named = [str(record.get(k) or "") for k in ("export_date", "exported_by", "permalink")]
    named.append(str((record.get("cause_hierarchy") or {}).get("sha256") or ""))
    if not all(v in block for v in named if v):
        return False, False, (f"{AMENDMENT_TABLE_FILE} does not state the export date, person, permalink and hierarchy hash of "
                              f"data/gbd/gbd_export_record.json; {remedy}")
    block_lines = block.split("\n")
    if not all(line in block_lines for line in required_lines):
        return False, False, (f"{AMENDMENT_TABLE_FILE} does not hold the table of the panel file and the catalogue volume as they "
                              f"are now; {remedy}")

    text = "\n".join(line.rstrip() for line in amendment_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
    squash = lambda s: "".join(s.split())   # noqa: E731
    strict, lenient = block in text, squash(block) in squash(text)
    if strict:
        return True, True, "as generated"
    return False, lenient, (_first_difference(block, text) + f"; paste the text of {AMENDMENT_TABLE_FILE} into the amendment again, unchanged")


# ---------------------------------------------------------------------------------------------
# verification of a final panel against the deposited files
# ---------------------------------------------------------------------------------------------

def panel_file_problems(panel: dict, root: Path, field_by_mesh: dict[str, str]) -> list[str]:
    """Why a final panel file is NOT supported by the files deposited next to it (empty list: it is).

    ``root`` is the repository root (the folder that holds config/ and data/). Checked: the mapping
    table exists, has the stated hash, is a reconciled table of two raters, and yields exactly the
    members of the panel file; the ranking exists, has the stated hash, and the mapping table agrees
    with it (ranks, exclusions, no cause skipped); the export record exists and names the same
    ranking and the same raw export."""
    problems: list[str] = []
    source = panel.get("source") or {}
    mapping_path = root / str(source.get("mapping_table", ""))
    ranking_path = root / "data" / "gbd" / "gbd2023_level3_ranking.csv"
    record_path = root / "data" / "gbd" / "gbd_export_record.json"

    if not source.get("mapping_table") or not mapping_path.is_file():
        return [f"mapping table not found: {source.get('mapping_table')!r} (relative to {root})"]
    if sha256_text(mapping_path) != source.get("mapping_table_sha256"):
        problems.append("the mapping table has another SHA-256 than the panel file states")
    rows = read_csv_dicts(mapping_path)
    try:
        r1, r2 = check_reconciled(rows)
        if str(source.get("raters", "")) != f"{r1} and {r2}":
            problems.append(f"the panel file names the raters {source.get('raters')!r}, the mapping table {r1} and {r2}")
        expected = members_from_mapping(rows, field_by_mesh)
    except GbdPanelError as exc:
        return problems + [str(exc)]
    actual = [{k: m.get(k) for k in MEMBER_KEYS} for m in (panel.get("members") or [])]
    if actual != expected:
        differing = [e["cause"] for e, a in zip(expected, actual) if e != a] or ["number of members"]
        problems.append(f"the members of the panel file are not the first {PANEL_SIZE} mapped causes of the mapping table "
                        f"(differences: {differing[:5]})")

    if not ranking_path.is_file():
        problems.append(f"ranking not found: {ranking_path.relative_to(root).as_posix()}")
    else:
        if sha256_text(ranking_path) != source.get("ranking_sha256"):
            problems.append("the ranking has another SHA-256 than the panel file states")
        try:
            problems += problems_against_ranking(rows, read_csv_dicts(ranking_path))
        except (GbdPanelError, KeyError) as exc:
            problems.append(f"the ranking cannot be compared with the mapping table: {exc}")

    if not record_path.is_file():
        problems.append(f"export record not found: {record_path.relative_to(root).as_posix()}")
    else:
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return problems + [f"export record is not valid JSON: {exc}"]
        if ranking_path.is_file() and (record.get("ranking_public") or {}).get("sha256") != sha256_text(ranking_path):
            problems.append("the export record names another ranking (SHA-256) than the one deposited; run 'rank' again")
        if (record.get("raw_export") or {}).get("sha256") != source.get("raw_export_sha256"):
            problems.append("the export record names another raw export (SHA-256) than the panel file")
        for key in ("exported_by", "export_date", "permalink"):
            if not str(record.get(key, "")).strip() or str(record.get(key, "")).startswith("["):
                problems.append(f"the export record does not state {key}")
    return problems
