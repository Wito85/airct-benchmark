"""Small shared helpers: UTC time, secret redaction, git metadata, hashing."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def utc_now() -> datetime:
    """Current time as an aware UTC datetime."""
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime | None = None) -> str:
    """ISO 8601 UTC timestamp with a Z suffix and second precision, e.g. 2026-10-12T08:00:00Z."""
    dt = dt or utc_now()
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_compact(dt: datetime | None = None) -> str:
    """Compact UTC timestamp for file names, e.g. 20261012T080000Z (with microseconds for uniqueness)."""
    dt = dt or utc_now()
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def utc_compact_seconds(dt: datetime | None = None) -> str:
    """Compact UTC timestamp with second precision for file names, e.g. 20261012T080000Z."""
    dt = dt or utc_now()
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_date(dt: datetime | None = None) -> str:
    """UTC calendar date as YYYYMMDD."""
    dt = dt or utc_now()
    return dt.astimezone(timezone.utc).strftime("%Y%m%d")


class Redactor:
    """Removes a secret (the NCBI API key) from any text before it is logged or stored.

    The key is never written to disk, never printed and never included in exception text.
    """

    def __init__(self, secrets: Iterable[str] = ()):
        self._secrets = [s for s in secrets if s]

    def __call__(self, text: Any) -> str:
        text = str(text)
        for secret in self._secrets:
            text = text.replace(secret, "***REDACTED***")
        # Belt and braces: also strip any api_key=... parameter that slipped through.
        text = re.sub(r"(api_key=)[^&\s\"']+", r"\1***REDACTED***", text)
        return text

    def params(self, params: dict) -> dict:
        """Copy of a parameter dict with api_key removed (for raw-response storage)."""
        return {k: v for k, v in params.items() if k != "api_key"}


def git_metadata(cwd: Path | str | None = None) -> dict:
    """Commit hash and dirty flag of the working tree, or 'unknown' outside a git checkout."""
    meta = {"commit": "unknown", "dirty": None, "describe": "unknown"}
    try:
        kw = {"cwd": str(cwd) if cwd else None, "stderr": subprocess.DEVNULL, "text": True}
        meta["commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], **kw).strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], **kw).strip()
        meta["dirty"] = bool(status)
        try:
            meta["describe"] = subprocess.check_output(["git", "describe", "--tags", "--always"], **kw).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass
    return meta


def sha256_file(path: Path | str, chunk_size: int = 1 << 20) -> str:
    """Hex SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    """Hex SHA-256 of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path | str, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2, sort_keys=False)
        fh.write("\n")


def read_json(path: Path | str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def safe_filename(text: str) -> str:
    """Restrict a label to [A-Za-z0-9._-] for use in file names."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text)


def env_api_key(env_var: str = "NCBI_API_KEY") -> str | None:
    """The API key from the environment, or None. Never stored anywhere else."""
    key = os.environ.get(env_var, "").strip()
    return key or None
