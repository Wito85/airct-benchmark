"""SHA-256 manifest of every file in an output directory (Q9). Format of `sha256sum`, so that
`sha256sum -c MANIFEST_SHA256.txt` verifies a deposit."""

from __future__ import annotations

from pathlib import Path

from .util import sha256_file

MANIFEST_NAME = "MANIFEST_SHA256.txt"


def write_manifest(root: Path | str, name: str = MANIFEST_NAME) -> Path:
    root = Path(root)
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.name != name)
    lines = [f"{sha256_file(p)}  {p.relative_to(root).as_posix()}" for p in files]
    path = root / name
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return path


def verify_manifest(root: Path | str, name: str = MANIFEST_NAME) -> list[str]:
    """Return a list of problems (empty when every listed file matches)."""
    root = Path(root)
    problems: list[str] = []
    for line in (root / name).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        p = root / rel
        if not p.is_file():
            problems.append(f"missing: {rel}")
        elif sha256_file(p) != digest:
            problems.append(f"hash mismatch: {rel}")
    return problems
