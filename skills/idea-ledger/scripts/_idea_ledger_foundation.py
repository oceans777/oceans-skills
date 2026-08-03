#!/usr/bin/env python3
"""Deterministic, project-local storage and validation for Idea Ledger v2.3.

The core module performs no Git subprocesses and never initializes, stages,
commits, resets, restores, cleans, or rewrites repository configuration.
"""
from __future__ import annotations

import contextlib
import copy
import datetime as dt
import errno
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterator, Sequence

try:  # POSIX
    import fcntl  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised on Windows
    fcntl = None  # type: ignore[assignment]

try:  # Windows
    import msvcrt  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised on POSIX
    msvcrt = None  # type: ignore[assignment]

VERSION = "2.3.0"
# Schema 2 remains readable so v2.0 ledgers do not require an in-place rewrite.
SCHEMA_VERSION = 2
CONFIG_DIR = ".idea-ledger"
CONFIG_FILE = f"{CONFIG_DIR}/config.json"
LOCK_FILE = f"{CONFIG_DIR}/ledger.lock"
CONFIG_IGNORE_FILE = f"{CONFIG_DIR}/.gitignore"
DEFAULT_RECORDS_DIR = "docs/idea-ledger/records"
DEFAULT_INDEX_FILE = "docs/idea-ledger/INDEX.md"
DEFAULT_PRD_DIR = "docs/prd"
META_START = "<!-- IDEA_LEDGER_V2"
META_END = "IDEA_LEDGER_V2 -->"
PRD_META_START = "<!-- IDEA_LEDGER_PRD_V1"
PRD_META_END = "IDEA_LEDGER_PRD_V1 -->"
ID_RE = re.compile(r"^IDEA-(\d{4,})$")
RECORD_FILE_RE = re.compile(r"^IDEA-(\d{4,})\.md$")
PRD_FILE_RE = re.compile(r"^PRD-(IDEA-\d{4,})\.md$")
STATUSES = {"proposed", "accepted", "rejected"}
CONFIDENCE_LEVELS = {"low", "medium", "high"}
COMPATIBILITY_LEVELS = {"compatible", "duplicate", "tension", "incompatible", "unknown"}
DISPOSITIONS = {"none", "bounded", "supersede", "defer"}
DEPENDENCY_MODES = {"exact", "lineage"}
LEGACY_CONFLICT_KINDS = {"none", "duplicate", "tension", "hard_conflict", "resolved", "unknown"}

DEFAULT_CONFIG: dict[str, Any] = {
    "schema": SCHEMA_VERSION,
    "version": VERSION,
    "records_dir": DEFAULT_RECORDS_DIR,
    "index_file": DEFAULT_INDEX_FILE,
    "prd_dir": DEFAULT_PRD_DIR,
    "max_related_records": 8,
    "max_context_chars": 12000,
    "policy_exempt_prefixes": [
        ".idea-ledger/",
        "docs/idea-ledger/",
        "docs/prd/",
        ".github/",
    ],
}

LEGACY_CONFLICT_FIELDS = {"kind", "related_ids", "rationale", "confidence", "resolution"}
CONFLICT_FIELDS = {
    "compatibility",
    "reviewed_ids",
    "conflicts_with",
    "rationale",
    "confidence",
    "disposition",
    "mitigation",
}
APPROVAL_METHODS = {"explicit_phrase", "natural_language_intent"}
APPROVAL_COMMON_FIELDS = {"method", "actor_verified", "recorded_at"}
EXPLICIT_APPROVAL_FIELDS = APPROVAL_COMMON_FIELDS | {"recorded_phrase"}
NATURAL_LANGUAGE_APPROVAL_FIELDS = APPROVAL_COMMON_FIELDS | {"recorded_message", "resolved_record"}
APPROVAL_FIELDS = EXPLICIT_APPROVAL_FIELDS | NATURAL_LANGUAGE_APPROVAL_FIELDS
REQUIRED_RECORD_META_FIELDS = {
    "schema",
    "id",
    "number",
    "title",
    "status",
    "created_at",
    "updated_at",
    "accepted_at",
    "rejected_at",
    "rejection_reason",
    "approval",
    "goal",
    "decision",
    "outcome",
    "scope",
    "tags",
    "constraints",
    "acceptance_criteria",
    "conflict",
    "supersedes",
    "depends_on",
    "notes",
}
OPTIONAL_RECORD_META_FIELDS = {
    "charter",
    "rationale",
    "alternatives_considered",
    "tradeoffs",
    "non_goals",
    "sources",
    "owner",
    "review_at",
}
CHARTER_FIELDS = {"goal", "actors", "scope", "principles", "non_goals"}
RECORD_META_FIELDS = REQUIRED_RECORD_META_FIELDS | OPTIONAL_RECORD_META_FIELDS


class LedgerError(RuntimeError):
    """Expected user-facing validation or workflow error."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def default_config() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_CONFIG)


def normalize_id(value: str) -> str:
    value = value.strip().upper().replace("_", "-").replace(" ", "-")
    match = re.fullmatch(r"IDEA-?(\d+)", value)
    if not match:
        raise LedgerError(f"无效编号：{value!r}，应为 IDEA-0001。")
    return f"IDEA-{int(match.group(1)):04d}"


def ensure_root(root: Path | str) -> Path:
    path = Path(root).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise LedgerError(f"项目目录不存在或不是目录：{path}")
    return path


def _contains_control(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in value)


def _ensure_no_symlink_components(root: Path, candidate: Path, label: str) -> None:
    current = root
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:  # pragma: no cover - guarded by caller
        raise LedgerError(f"{label} 超出项目目录：{candidate}") from exc
    for part in relative.parts:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise LedgerError(f"无法检查{label}路径：{current}：{exc}") from exc
        if stat.S_ISLNK(info.st_mode):
            raise LedgerError(f"{label} 的路径组件不得是符号链接：{current}")


def safe_project_path(root: Path, raw: str, label: str) -> Path:
    if not isinstance(raw, str) or not raw.strip() or "\x00" in raw or _contains_control(raw):
        raise LedgerError(f"{label} 必须是非空、无控制字符的项目内相对路径。")
    # Colons are rejected for cross-platform portability and unambiguous Git tree lookups.
    if ":" in raw:
        raise LedgerError(f"{label} 不得包含冒号：{raw}")
    rel = Path(raw)
    if rel.is_absolute() or ".." in rel.parts:
        raise LedgerError(f"{label} 必须是项目内相对路径：{raw}")
    candidate = root / rel
    _ensure_no_symlink_components(root, candidate, label)
    target = candidate.resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise LedgerError(f"{label} 超出项目目录：{raw}") from exc
    if target == root:
        raise LedgerError(f"{label} 不得指向项目根目录：{raw}")
    return target


def _is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _validate_existing_kind(path: Path, label: str, *, directory: bool) -> None:
    if not path.exists():
        return
    info = path.lstat()
    if directory and not stat.S_ISDIR(info.st_mode):
        raise LedgerError(f"{label} 必须是目录：{path}")
    if not directory and not stat.S_ISREG(info.st_mode):
        raise LedgerError(f"{label} 必须是普通文件：{path}")


def validate_config_topology(root: Path, config: dict[str, Any], *, label: str) -> None:
    records = safe_project_path(root, str(config["records_dir"]), "records_dir")
    index = safe_project_path(root, str(config["index_file"]), "index_file")
    prds = safe_project_path(root, str(config["prd_dir"]), "prd_dir")
    config_state_dir = safe_project_path(root, CONFIG_DIR, "config_dir")
    reserved = {
        safe_project_path(root, CONFIG_FILE, "config_file"),
        safe_project_path(root, LOCK_FILE, "lock_file"),
        safe_project_path(root, CONFIG_IGNORE_FILE, "config_ignore_file"),
    }

    _validate_existing_kind(records, "records_dir", directory=True)
    _validate_existing_kind(prds, "prd_dir", directory=True)
    _validate_existing_kind(index, "index_file", directory=False)

    if _is_within(records, prds) or _is_within(prds, records):
        raise LedgerError(f"{label} 中 records_dir 与 prd_dir 不得相同或互相嵌套。")
    if _is_within(index, records) or _is_within(index, prds):
        raise LedgerError(f"{label} 中 index_file 不得位于 records_dir 或 prd_dir 内。")
    if _is_within(records, config_state_dir) or _is_within(prds, config_state_dir) or _is_within(index, config_state_dir):
        raise LedgerError(f"{label} 的记录、索引和 PRD 路径不得位于 {CONFIG_DIR}/ 内。")
    if index in reserved:
        raise LedgerError(f"{label} 的 index_file 与保留治理文件冲突：{index}")
    for directory, directory_label in ((records, "records_dir"), (prds, "prd_dir")):
        clashes = [path for path in reserved if _is_within(path, directory)]
        if clashes:
            raise LedgerError(
                f"{label} 的 {directory_label} 会覆盖保留治理文件："
                + "、".join(str(path) for path in sorted(clashes))
            )


def read_managed_text(path: Path, label: str) -> str:
    """Read a managed regular file without following a final-component symlink."""
    if path.is_symlink():
        raise LedgerError(f"{label} 不得是符号链接：{path}")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except FileNotFoundError as exc:
        raise LedgerError(f"文件不存在：{path}") from exc
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise LedgerError(f"{label} 不得是符号链接：{path}") from exc
        raise LedgerError(f"无法读取{label}：{path}：{exc}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise LedgerError(f"{label} 必须是普通文件：{path}")
        with os.fdopen(fd, "r", encoding="utf-8", newline="") as handle:
            fd = -1
            return handle.read()
    finally:
        if fd >= 0:
            os.close(fd)


def atomic_write_text(path: Path, text: str) -> None:
    """Atomically replace a managed regular file using an unguessable temp file."""
    if path.is_symlink():
        raise LedgerError(f"拒绝覆盖符号链接：{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = 0o644
    try:
        info = path.lstat()
    except FileNotFoundError:
        pass
    else:
        if not stat.S_ISREG(info.st_mode):
            raise LedgerError(f"拒绝覆盖非普通文件：{path}")
        mode = stat.S_IMODE(info.st_mode)
    fd = -1
    temp_path: Path | None = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.tmp-", dir=str(path.parent))
        temp_path = Path(temp_name)
        with contextlib.suppress(OSError):
            os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            fd = -1
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if fd >= 0:
            os.close(fd)
        if temp_path is not None:
            with contextlib.suppress(FileNotFoundError):
                temp_path.unlink()


def atomic_create_text(path: Path, text: str, *, mode: int = 0o644) -> None:
    """Create a file exactly once; never overwrite an existing path."""
    if path.is_symlink():
        raise LedgerError(f"拒绝创建到符号链接：{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, mode)
    except FileExistsError as exc:
        raise LedgerError(f"文件已存在，拒绝覆盖：{path}") from exc
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise LedgerError(f"拒绝创建到符号链接：{path}") from exc
        raise LedgerError(f"无法创建文件：{path}：{exc}") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            fd = -1
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if fd >= 0:
            os.close(fd)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def read_json_object(path: Path, *, label: str = "JSON 文件") -> dict[str, Any]:
    text = read_managed_text(path, label)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LedgerError(f"JSON 无效：{path}：{exc}") from exc
    if not isinstance(data, dict):
        raise LedgerError(f"JSON 顶层必须是对象：{path}")
    return data


def normalize_policy_prefix(value: Any) -> str:
    if not isinstance(value, str):
        raise LedgerError("policy_exempt_prefixes 必须是字符串数组。")
    raw = value.strip().replace("\\", "/")
    if not raw or "\x00" in raw or _contains_control(raw) or raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        raise LedgerError(f"无效策略豁免前缀：{value!r}")
    keep_trailing_slash = raw.endswith("/")
    parts = [part for part in raw.split("/") if part not in {"", "."}]
    if not parts or any(part == ".." for part in parts):
        raise LedgerError(f"无效策略豁免前缀：{value!r}")
    normalized = "/".join(parts)
    return normalized + ("/" if keep_trailing_slash else "")


def normalize_config(root: Path, config: dict[str, Any], *, label: str = "config.json") -> dict[str, Any]:
    unknown = sorted(set(config) - set(DEFAULT_CONFIG))
    if unknown:
        raise LedgerError(f"{label} 包含未知字段：" + "、".join(unknown))
    merged = default_config()
    merged.update(config)
    if merged.get("schema") != SCHEMA_VERSION:
        raise LedgerError(
            f"不支持的账本 schema={merged.get('schema')!r}；v1 项目请先阅读 references/migration-v1.md。"
        )
    if not isinstance(merged.get("version"), str) or not str(merged["version"]).strip():
        raise LedgerError(f"{label} 的 version 必须是非空字符串。")
    for key in ("records_dir", "index_file", "prd_dir"):
        value = merged.get(key)
        if not isinstance(value, str):
            raise LedgerError(f"{label} 的 {key} 必须是字符串。")
        safe_project_path(root, value, key)
    for key, minimum, maximum in (
        ("max_related_records", 1, 100),
        ("max_context_chars", 500, 200000),
    ):
        value = merged.get(key)
        if type(value) is not int or not minimum <= value <= maximum:
            raise LedgerError(f"{label} 的 {key} 必须是 {minimum}..{maximum} 的整数。")
    prefixes = merged.get("policy_exempt_prefixes")
    if not isinstance(prefixes, list) or not 1 <= len(prefixes) <= 100:
        raise LedgerError(f"{label} 的 policy_exempt_prefixes 必须包含 1..100 个字符串。")
    normalized_prefixes: list[str] = []
    for value in prefixes:
        normalized = normalize_policy_prefix(value)
        if normalized not in normalized_prefixes:
            normalized_prefixes.append(normalized)
    merged["policy_exempt_prefixes"] = normalized_prefixes
    validate_config_topology(root, merged, label=label)
    return merged

__all__ = [name for name in globals() if not name.startswith("__")]
