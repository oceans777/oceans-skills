#!/usr/bin/env python3
"""Optional, read-only Git/CI policy checks for Idea Ledger v2.1."""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence

from idea_ledger_core import (
    CONFIG_FILE,
    LedgerError,
    effective_status,
    load_config,
    load_records,
    normalize_id,
    parse_config_text,
    parse_metadata,
    read_managed_text,
    render_record,
    superseded_by_map,
    validate_ledger,
    validate_meta_shape,
)


def run_git(
    root: Path,
    args: Sequence[str],
    *,
    check: bool = True,
    timeout_seconds: float = 30.0,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
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


def resolve_git_commit(root: Path, ref: str) -> str | None:
    if not isinstance(ref, str) or not ref.strip() or "\x00" in ref:
        return None
    result = run_git(root, ["rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"], check=False)
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40,64}", value) else None


def git_file_at_ref(root: Path, commit: str, rel: str) -> str | None:
    if ":" in rel or "\x00" in rel or any(ord(char) < 32 for char in rel):
        raise LedgerError(f"Git 树路径无效：{rel!r}")
    result = run_git(root, ["show", f"{commit}:{rel}"], check=False)
    return result.stdout if result.returncode == 0 else None


def parse_name_status_z(raw: str) -> list[tuple[str, str, str | None]]:
    fields = raw.split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    result: list[tuple[str, str, str | None]] = []
    index = 0
    while index < len(fields):
        status_value = fields[index]
        index += 1
        if not status_value or index >= len(fields):
            raise LedgerError("无法解析 Git name-status 输出。")
        first = fields[index]
        index += 1
        second: str | None = None
        if status_value.startswith(("R", "C")):
            if index >= len(fields):
                raise LedgerError("无法解析 Git rename/copy 输出。")
            second = fields[index]
            index += 1
        result.append((status_value, first, second))
    return result


def is_exempt_path(path: str, config: dict[str, Any]) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    for prefix in config["policy_exempt_prefixes"]:
        if prefix.endswith("/"):
            bare = prefix.rstrip("/")
            if normalized == bare or normalized.startswith(prefix):
                return True
        elif normalized == prefix:
            return True
    return False


def load_base_config(root: Path, base_commit: str) -> dict[str, Any] | None:
    text = git_file_at_ref(root, base_commit, CONFIG_FILE)
    if text is None:
        return None
    return parse_config_text(root, text, label=f"基准 {CONFIG_FILE}")


def _canonical_record_name(path: str) -> tuple[str | None, str | None]:
    name = Path(path).name
    match = re.fullmatch(r"IDEA-(\d{4,})\.md", name)
    if not match:
        return None, f"记录文件名不规范：{path}"
    idea_id = f"IDEA-{int(match.group(1)):04d}"
    if name != f"{idea_id}.md":
        return None, f"记录文件名不规范：{path}；应为 {idea_id}.md"
    return idea_id, None


def _snapshot_records_at_commit(
    root: Path,
    commit: str,
    records_rel: str,
    cache: dict[str, tuple[dict[str, dict[str, Any]], list[str]]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    cached = cache.get(commit)
    if cached is not None:
        return cached
    result = run_git(root, ["ls-tree", "-r", "-z", "--name-only", commit, "--", records_rel], check=False)
    if result.returncode != 0:
        payload = ({}, [(result.stderr or result.stdout or f"无法读取 {commit[:12]} 的记录树").strip()])
        cache[commit] = payload
        return payload
    paths = [path for path in result.stdout.split("\0") if path]
    snapshot: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for path in paths:
        idea_id, name_error = _canonical_record_name(path)
        if name_error:
            errors.append(f"提交 {commit[:12]}：{name_error}")
            continue
        assert idea_id is not None
        text = git_file_at_ref(root, commit, path)
        if text is None:
            errors.append(f"提交 {commit[:12]} 无法读取记录：{path}")
            continue
        try:
            meta = parse_metadata(text)
            shape_errors = validate_meta_shape(meta, expected_id=idea_id)
        except LedgerError as exc:
            errors.append(f"提交 {commit[:12]} 的记录 {path} 无效：{exc}")
            continue
        if shape_errors:
            errors.append(f"提交 {commit[:12]} 的记录 {path} 无效：" + "；".join(shape_errors))
            continue
        if text != render_record(meta):
            errors.append(f"提交 {commit[:12]} 的记录正文与元数据不一致：{path}")
            continue
        if idea_id in snapshot:
            errors.append(f"提交 {commit[:12]} 存在重复编号：{idea_id}")
            continue
        snapshot[idea_id] = {
            "id": idea_id,
            "path": path,
            "text": text,
            "digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "meta": meta,
        }
    payload = (snapshot, errors)
    cache[commit] = payload
    return payload


def _worktree_snapshot(root: Path, config: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    try:
        records = load_records(root, config)
    except LedgerError as exc:
        return {}, [str(exc)]
    snapshot: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for item in records:
        meta = item["meta"]
        try:
            rel = item["path"].relative_to(root).as_posix()
            text = read_managed_text(item["path"], "Idea Ledger 记录")
        except (ValueError, LedgerError) as exc:
            errors.append(str(exc))
            continue
        snapshot[meta["id"]] = {
            "id": meta["id"],
            "path": rel,
            "text": text,
            "digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "meta": meta,
        }
    return snapshot, errors


def _compare_terminal_snapshots(
    parent: dict[str, dict[str, Any]],
    child: dict[str, dict[str, Any]],
    *,
    label: str,
) -> list[str]:
    errors: list[str] = []
    for idea_id, old in sorted(parent.items()):
        if old["meta"].get("status") not in {"accepted", "rejected"}:
            continue
        new = child.get(idea_id)
        if new is None:
            errors.append(f"终态记录不可删除或改名：{idea_id}（{label}）")
            continue
        if new["path"] != old["path"]:
            errors.append(f"终态记录不可改名：{idea_id}：{old['path']} -> {new['path']}（{label}）")
        if new["digest"] != old["digest"]:
            errors.append(f"终态记录不可原地修改：{idea_id}（{label}）")
    return errors


def _commit_ids(root: Path, revision_range: str) -> tuple[list[str], list[str]]:
    result = run_git(root, ["rev-list", "--reverse", "--topo-order", revision_range], check=False)
    if result.returncode != 0:
        return [], [(result.stderr or result.stdout or "无法枚举提交").strip()]
    return [line.strip() for line in result.stdout.splitlines() if line.strip()], []


def _validate_terminal_history(
    root: Path,
    merge_base: str,
    records_rel: str,
    cache: dict[str, tuple[dict[str, dict[str, Any]], list[str]]],
) -> list[str]:
    commits, errors = _commit_ids(root, f"{merge_base}..HEAD")
    for commit in commits:
        child, child_errors = _snapshot_records_at_commit(root, commit, records_rel, cache)
        errors.extend(child_errors)
        parents_result = run_git(root, ["show", "-s", "--format=%P", commit], check=False)
        if parents_result.returncode != 0:
            errors.append(f"无法读取提交 {commit[:12]} 的父提交。")
            continue
        parents = [value for value in parents_result.stdout.split() if value]
        for parent_commit in parents:
            parent, parent_errors = _snapshot_records_at_commit(root, parent_commit, records_rel, cache)
            errors.extend(parent_errors)
            errors.extend(
                _compare_terminal_snapshots(
                    parent,
                    child,
                    label=f"提交 {commit[:12]} 相对父提交 {parent_commit[:12]}",
                )
            )
    return errors


def _extract_idea_trailers(root: Path, message: str) -> list[str]:
    lines = message.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n").split("\n")
    blank_positions = [index for index, line in enumerate(lines) if not line.strip()]
    if not blank_positions:
        return []
    footer = lines[blank_positions[-1] + 1 :]
    if not any(re.match(r"^Idea\s*:", line, re.I) for line in footer):
        return []
    parsed = run_git(root, ["interpret-trailers", "--parse"], check=False, input_text=message)
    if parsed.returncode != 0:
        return []
    result: list[str] = []
    for line in parsed.stdout.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip().lower() == "idea":
            result.append(value.strip())
    return result


def _commit_changed_paths(root: Path, commit: str) -> tuple[list[str], str | None]:
    result = run_git(
        root,
        ["diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "-z", commit],
        check=False,
    )
    if result.returncode != 0:
        return [], (result.stderr or result.stdout or f"无法读取提交 {commit[:12]} 的路径").strip()
    return [path for path in result.stdout.split("\0") if path], None


def _record_effective_at_snapshot(snapshot: dict[str, dict[str, Any]], idea_id: str) -> bool:
    records = [{"path": Path(item["path"]), "meta": item["meta"]} for item in snapshot.values()]
    reverse = superseded_by_map(records)
    item = snapshot.get(idea_id)
    return bool(item and effective_status(item["meta"], reverse) == "accepted")


def ci_check(root: Path, *, base_ref: str | None, require_trailer: bool) -> list[str]:
    try:
        errors = validate_ledger(root)
    except LedgerError as exc:
        errors = [str(exc)]
    if not base_ref:
        return list(dict.fromkeys(errors))
    try:
        config = load_config(root)
    except LedgerError as exc:
        return list(dict.fromkeys(errors + [str(exc)]))
    repo_check = run_git(root, ["rev-parse", "--is-inside-work-tree"], check=False)
    if repo_check.returncode != 0:
        return list(dict.fromkeys(errors + ["ci-check --base-ref 需要 Git 仓库。"]))
    base_commit = resolve_git_commit(root, base_ref)
    if base_commit is None:
        return list(dict.fromkeys(errors + [f"Git 基准不存在或不是 commit：{base_ref}"]))
    merge_base_result = run_git(root, ["merge-base", base_commit, "HEAD"], check=False)
    merge_base = merge_base_result.stdout.strip()
    if merge_base_result.returncode != 0 or not re.fullmatch(r"[0-9a-fA-F]{40,64}", merge_base):
        return list(dict.fromkeys(errors + ["无法计算 base 与 HEAD 的 merge-base；请完整 fetch 目标分支历史。"]))

    try:
        base_config = load_base_config(root, base_commit)
    except LedgerError as exc:
        errors.append(str(exc))
        base_config = None
    policy_config = base_config or config
    if base_config is not None:
        critical_keys = (
            "schema",
            "records_dir",
            "index_file",
            "prd_dir",
            "policy_exempt_prefixes",
        )
        changed_keys = [key for key in critical_keys if config[key] != base_config[key]]
        if changed_keys:
            errors.append(
                "治理配置相对基准发生变化，严格检查拒绝同一变更自改规则：" + "、".join(changed_keys)
            )

    records_rel = str(policy_config["records_dir"]).replace("\\", "/")
    cache: dict[str, tuple[dict[str, dict[str, Any]], list[str]]] = {}
    base_snapshot, base_snapshot_errors = _snapshot_records_at_commit(root, base_commit, records_rel, cache)
    errors.extend(base_snapshot_errors)
    worktree_snapshot, worktree_errors = _worktree_snapshot(root, config)
    errors.extend(worktree_errors)
    errors.extend(_compare_terminal_snapshots(base_snapshot, worktree_snapshot, label=f"基准 {base_ref} 到当前工作树"))
    errors.extend(_validate_terminal_history(root, merge_base, records_rel, cache))

    # Keep a NUL-safe diff parse as a defense-in-depth check for baseline renames/deletions.
    diff = run_git(root, ["diff", "--name-status", "-z", base_commit, "HEAD", "--", records_rel], check=False)
    if diff.returncode != 0:
        errors.append((diff.stderr or diff.stdout or "无法比较基准记录").strip())
    else:
        try:
            parse_name_status_z(diff.stdout)
        except LedgerError as exc:
            errors.append(str(exc))

    if require_trailer:
        merges = run_git(root, ["rev-list", "--merges", f"{merge_base}..HEAD"], check=False)
        merge_commits = [line.strip() for line in merges.stdout.splitlines() if line.strip()]
        if merge_commits:
            errors.append(
                "--require-trailer 需要线性提交历史；检测到 merge commit："
                + "、".join(commit[:12] for commit in merge_commits)
                + "。请 rebase/squash，避免合并提交中的未归因改动。"
            )
        commits_result = run_git(root, ["rev-list", "--reverse", "--no-merges", f"{merge_base}..HEAD"], check=False)
        if commits_result.returncode != 0:
            errors.append((commits_result.stderr or commits_result.stdout or "无法枚举提交").strip())
            commit_ids: list[str] = []
        else:
            commit_ids = [line.strip() for line in commits_result.stdout.splitlines() if line.strip()]
        for commit in commit_ids:
            changed_paths, path_error = _commit_changed_paths(root, commit)
            if path_error:
                errors.append(path_error)
                continue
            changed = [path for path in changed_paths if not is_exempt_path(path, policy_config)]
            if not changed:
                continue
            message_result = run_git(root, ["show", "-s", "--format=%B", commit], check=False)
            if message_result.returncode != 0:
                errors.append(f"无法读取提交 {commit[:12]} 的消息。")
                continue
            raw_trailers = _extract_idea_trailers(root, message_result.stdout)
            if not raw_trailers:
                errors.append(f"提交 {commit[:12]} 修改了策略范围内文件但缺少 footer trailer `Idea: IDEA-0001`。")
                continue
            snapshot, snapshot_errors = _snapshot_records_at_commit(root, commit, records_rel, cache)
            errors.extend(snapshot_errors)
            for raw in raw_trailers:
                try:
                    idea_id = normalize_id(raw)
                except LedgerError:
                    errors.append(f"提交 {commit[:12]} 包含无效 Idea trailer：{raw!r}。")
                    continue
                if not _record_effective_at_snapshot(snapshot, idea_id):
                    errors.append(f"提交 {commit[:12]} 引用了当时不存在或非生效 accepted 的 {idea_id}。")
    return list(dict.fromkeys(errors))
