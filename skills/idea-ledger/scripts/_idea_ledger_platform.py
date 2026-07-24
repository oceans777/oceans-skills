#!/usr/bin/env python3
"""Install narrowly scoped runtime compatibility before loading core modules."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable

import _idea_ledger_foundation as foundation


def _configure_utf8_stream(stream: object) -> None:
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="backslashreplace")


def install_platform_compatibility() -> None:
    """Normalize roots, streams, and the Windows-only descriptor mode gap.

    macOS commonly exposes ``/var`` through the ``/private/var`` symlink. A
    caller can therefore retain a non-canonical temporary-directory path while
    a child path resolves to the canonical form. Canonicalizing the root before
    the existing containment check prevents a safe child from being rejected.

    Windows does not expose ``os.fchmod``. File descriptor modes have no POSIX
    permission meaning there, so the atomic writer may safely use a no-op while
    retaining the real implementation on platforms that provide it.

    The CLI emits structured Chinese diagnostics. Explicit UTF-8 standard
    streams prevent Windows runners or redirected shells from replacing those
    diagnostics with literal ``\\u`` escapes.
    """

    _configure_utf8_stream(sys.stdout)
    _configure_utf8_stream(sys.stderr)

    if not hasattr(os, "fchmod"):
        def _fchmod_noop(_fd: int, _mode: int) -> None:
            return None

        setattr(os, "fchmod", _fchmod_noop)

    original: Callable[..., Path] = foundation.safe_project_path
    if getattr(original, "_idea_ledger_canonical_root", False):
        return

    def canonical_safe_project_path(root: Path, raw: str, label: str) -> Path:
        canonical_root = Path(root).expanduser().resolve()
        return original(canonical_root, raw, label)

    setattr(canonical_safe_project_path, "_idea_ledger_canonical_root", True)
    foundation.safe_project_path = canonical_safe_project_path
