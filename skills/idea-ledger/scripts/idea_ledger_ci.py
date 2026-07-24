#!/usr/bin/env python3
"""Canonical-root and UTF-8 facade for optional Idea Ledger CI checks."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Sequence

import _idea_ledger_ci_core as _core
from _idea_ledger_ci_core import *


def run_git(
    root: Path,
    args: Sequence[str],
    *,
    check: bool = True,
    timeout_seconds: float = 30.0,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run read-only Git commands with deterministic UTF-8 text handling."""
    env = os.environ.copy()
    env.update(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
            "PAGER": "cat",
            "GIT_LITERAL_PATHSPECS": "1",
        }
    )
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        encoding="utf-8",
        errors="strict",
        input=input_text,
        capture_output=True,
        check=False,
        timeout=timeout_seconds,
        env=env,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "Git 命令失败").strip()
        raise LedgerError(detail)
    return result


_core.run_git = run_git
_ci_check = _core.ci_check


def ci_check(root: Path, *, base_ref: str | None, require_trailer: bool) -> list[str]:
    """Run strict checks with the same canonical project root as the CLI."""
    canonical_root = Path(root).expanduser().resolve()
    return _ci_check(canonical_root, base_ref=base_ref, require_trailer=require_trailer)
