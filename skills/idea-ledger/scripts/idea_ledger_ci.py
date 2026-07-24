#!/usr/bin/env python3
"""Canonical-root facade for optional, read-only Idea Ledger CI checks."""
from __future__ import annotations

from pathlib import Path

from _idea_ledger_ci_core import *
from _idea_ledger_ci_core import ci_check as _ci_check


def ci_check(root: Path, *, base_ref: str | None, require_trailer: bool) -> list[str]:
    """Run strict checks with the same canonical project root as the CLI."""
    canonical_root = Path(root).expanduser().resolve()
    return _ci_check(canonical_root, base_ref=base_ref, require_trailer=require_trailer)
