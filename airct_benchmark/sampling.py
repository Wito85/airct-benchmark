"""Validation and stratum sampling (Q13, Q14) on the frozen Run A PMID lists of 2024.

Registered rules
* Sampling by Python random.Random(20260904).sample on the PMID list sorted ascending.
* V-AI, V-STROKE: all records of the RCT-tagged list if 200 or fewer, otherwise a simple random
  sample of 200.
* U-AI, U-STROKE: simple random samples of 200 from the enriched untagged strata S_f.
* R-check: 50 records each from the remainder strata R_f (plausibility check only).
* Pilot: 20 additional records per cell, drawn first, codebook calibration only, not in the formal set.
* Q14: a PMID whose XML cannot be retrieved is replaced by the next PMID in the seeded sampling sequence.

Implementation decision I1 (documented for the SAP): the seeded sampling sequence of a cell is one
call ``random.Random(20260904).sample(sorted_pmids, k=len(sorted_pmids))``, i.e. a complete
seeded ordering of the cell's population produced by the registered function on the registered
input. The pilot is its first 20 elements, the formal set the following ones, and replacements
(Q14) continue along the same sequence. This satisfies "drawn first" and "next PMID in the seeded
sampling sequence" literally and makes every draw reproducible from the frozen list alone.
Edge cases (census cells with 200 or fewer records, populations smaller than pilot plus formal
size) are handled as stated in ``draw_cell`` and flagged in the report for the SAP.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable

SEED = 20260904


@dataclass
class CellSample:
    cell: str
    source_list: str
    population_size: int
    rule: str
    pilot: list[int]
    formal: list[int]
    reserve: list[int] = field(default_factory=list)
    replacements: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def requested(self) -> list[int]:
        return list(self.pilot) + list(self.formal)


def seeded_sequence(pmids: Iterable[int], seed: int = SEED) -> list[int]:
    """Complete seeded ordering: random.Random(seed).sample(sorted_population, k=len(population))."""
    population = sorted({int(p) for p in pmids})
    rng = random.Random(seed)
    return rng.sample(population, k=len(population))


def draw_cell(
    cell: str,
    source_list: str,
    pmids: Iterable[int],
    formal_size: int,
    *,
    pilot_size: int = 20,
    take_all_if_at_most: int | None = None,
    seed: int = SEED,
) -> CellSample:
    """Draw pilot and formal set for one cell.

    * Census rule (V-cells): if ``take_all_if_at_most`` is set and the population is at most that
      size, the formal set is the whole population in ascending PMID order and no pilot is drawn
      from this cell (there are no additional records); this is flagged.
    * Otherwise the seeded sequence is used: pilot = first ``pilot_size``, formal = next
      ``formal_size``, reserve = the rest (replacement queue, Q14). Shortfalls are flagged.
    """
    population = sorted({int(p) for p in pmids})
    n = len(population)
    notes: list[str] = []

    if take_all_if_at_most is not None and n <= take_all_if_at_most:
        notes.append(f"census: population {n} is at most {take_all_if_at_most}; all records enter the formal set; "
                     "no additional pilot records exist in this cell (SAP decides on pilot material)")
        return CellSample(cell, source_list, n, "census", pilot=[], formal=population, reserve=[], notes=notes)

    seq = seeded_sequence(population, seed)
    pilot = seq[:pilot_size]
    formal = seq[pilot_size : pilot_size + formal_size]
    reserve = seq[pilot_size + formal_size :]
    if len(pilot) < pilot_size:
        notes.append(f"pilot shortfall: {len(pilot)} of {pilot_size} available")
    if len(formal) < formal_size:
        notes.append(f"formal shortfall: {len(formal)} of {formal_size} available after the pilot")
    if not reserve:
        notes.append("no reserve for replacements")
    return CellSample(cell, source_list, n, f"seeded sample (pilot {pilot_size} first, then {formal_size})",
                      pilot=pilot, formal=formal, reserve=reserve, notes=notes)


def replace_missing(sample: CellSample, missing: Iterable[int]) -> list[int]:
    """Q14: replace unretrievable PMIDs by the next PMIDs of the seeded sequence.

    Applies to pilot and formal draws of sampled cells; census cells have no reserve and record
    the PMID as missing. Returns the list of newly added PMIDs (to be fetched)."""
    added: list[int] = []
    for pmid in missing:
        pmid = int(pmid)
        target = "formal" if pmid in sample.formal else "pilot" if pmid in sample.pilot else None
        if target is None:
            continue
        if not sample.reserve:
            sample.notes.append(f"PMID {pmid} missing and no reserve left; recorded as missing")
            sample.replacements.append({"missing": pmid, "replacement": None, "set": target})
            continue
        new = sample.reserve.pop(0)
        getattr(sample, target).remove(pmid)
        getattr(sample, target).append(new)
        sample.replacements.append({"missing": pmid, "replacement": new, "set": target})
        added.append(new)
    return added


def draw_all_cells(lists: dict[str, list[int]], config: dict) -> list[CellSample]:
    """Draw every registered cell from the frozen lists.

    ``lists`` maps list keys to ascending PMID lists: 'B_AI', 'B_STROKE', 'S_AI', 'S_STROKE',
    'R_AI', 'R_STROKE'. ``config`` is the catalogue's ``sampling`` section."""
    seed = int(config["seed"])
    pilot = int(config["pilot_per_cell"])
    v, u, r = config["v_cells"], config["u_cells"], config["r_check"]
    out: list[CellSample] = []
    for fld in ("AI", "STROKE"):
        out.append(draw_cell(f"V-{fld}", f"{v['list']}_{fld}", lists[f"{v['list']}_{fld}"], int(v["sample_size"]),
                             pilot_size=pilot, take_all_if_at_most=int(v["take_all_if_at_most"]), seed=seed))
    for fld in ("AI", "STROKE"):
        out.append(draw_cell(f"U-{fld}", f"{u['list']}_{fld}", lists[f"{u['list']}_{fld}"], int(u["sample_size"]),
                             pilot_size=pilot, seed=seed))
    for fld in ("AI", "STROKE"):
        out.append(draw_cell(f"R-{fld}", f"{r['list']}_{fld}", lists[f"{r['list']}_{fld}"], int(r["sample_size"]),
                             pilot_size=pilot, seed=seed))
    return out


def write_cell_csvs(samples: list[CellSample], out_dir: Path | str) -> list[Path]:
    """One CSV per cell with columns cell, set (pilot|formal), order, pmid."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for s in samples:
        path = out_dir / f"sample_{s.cell}.csv"
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["cell", "set", "order", "pmid"])
            for i, p in enumerate(s.pilot, 1):
                w.writerow([s.cell, "pilot", i, p])
            for i, p in enumerate(s.formal, 1):
                w.writerow([s.cell, "formal", i, p])
        paths.append(path)
    return paths
