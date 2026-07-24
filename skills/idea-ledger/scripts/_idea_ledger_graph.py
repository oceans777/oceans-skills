#!/usr/bin/env python3
"""Relationship and dependency graph validation for Idea Ledger."""
from __future__ import annotations

from _idea_ledger_foundation import *
from _idea_ledger_paths import *
from _idea_ledger_normalize import *
from _idea_ledger_records import *

def load_record(path: Path, *, check_render: bool = True) -> dict[str, Any]:
    text = read_managed_text(path, "Idea Ledger 记录")
    meta = parse_metadata(text, path=path)
    match = RECORD_FILE_RE.fullmatch(path.name)
    expected_id = f"IDEA-{int(match.group(1)):04d}" if match else None
    if expected_id and path.name != f"{expected_id}.md":
        raise LedgerError(f"记录文件名不规范：{path.name}；应为 {expected_id}.md")
    errors = validate_meta_shape(meta, expected_id=expected_id)
    if errors:
        raise LedgerError(f"记录无效：{path}\n- " + "\n- ".join(errors))
    if check_render and text != render_record(meta):
        raise LedgerError(f"记录正文与机器元数据不一致：{path}；请勿手工编辑，proposed 记录请用 revise。")
    return meta


def load_records(root: Path, config: dict[str, Any] | None = None, *, strict: bool = True) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in list_record_paths(root, config):
        if strict:
            meta = load_record(path)
        else:
            text = read_managed_text(path, "Idea Ledger 记录")
            meta = parse_metadata(text, path=path)
        result.append({"path": path, "meta": meta})
    return result


def record_map(root: Path, config: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    return {item["meta"]["id"]: item for item in load_records(root, config)}


def next_id(root: Path, config: dict[str, Any] | None = None) -> str:
    numbers = [int(RECORD_FILE_RE.fullmatch(path.name).group(1)) for path in list_record_paths(root, config)]  # type: ignore[union-attr]
    return f"IDEA-{(max(numbers) + 1) if numbers else 1:04d}"


def superseded_by_map(records: Sequence[dict[str, Any]]) -> dict[str, list[str]]:
    reverse: dict[str, list[str]] = {}
    for item in records:
        meta = item.get("meta", item)
        if meta.get("status") != "accepted":
            continue
        for target in meta.get("supersedes", []):
            reverse.setdefault(target, []).append(meta["id"])
    for values in reverse.values():
        values.sort(key=lambda value: int(value.split("-")[1]))
    return reverse


def effective_status(meta: dict[str, Any], superseded_by: dict[str, list[str]]) -> str:
    if meta.get("status") == "accepted" and superseded_by.get(meta["id"]):
        return "superseded"
    return str(meta.get("status"))


def _lineage_target(
    start_id: str,
    mapping: dict[str, dict[str, Any]],
    reverse: dict[str, list[str]],
) -> tuple[str | None, str | None]:
    current = start_id
    seen: set[str] = set()
    while True:
        if current in seen:
            return None, "supersedes 链存在环"
        seen.add(current)
        successors = reverse.get(current, [])
        if len(successors) > 1:
            return None, f"{current} 有多个生效后继：{'、'.join(successors)}"
        if not successors:
            target = mapping.get(current)
            if target and effective_status(target["meta"], reverse) == "accepted":
                return current, None
            return None, f"{current} 无法解析到当前生效 accepted 决策"
        current = successors[0]


def resolved_dependencies_for(
    meta: dict[str, Any],
    mapping: dict[str, dict[str, Any]],
    reverse: dict[str, list[str]],
) -> tuple[list[dict[str, str]], list[str]]:
    resolved: list[dict[str, str]] = []
    errors: list[str] = []
    for dependency in normalize_dependencies(meta.get("depends_on", [])):
        target_id = dependency["id"]
        mode = dependency["mode"]
        if mode == "exact":
            target = mapping.get(target_id)
            if not target or effective_status(target["meta"], reverse) != "accepted":
                errors.append(f"exact 依赖 {target_id} 不是当前生效 accepted")
                continue
            resolved_id = target_id
        else:
            resolved_id, error = _lineage_target(target_id, mapping, reverse)
            if error or resolved_id is None:
                errors.append(f"lineage 依赖 {target_id}：{error}")
                continue
        resolved.append({"declared_id": target_id, "mode": mode, "resolved_id": resolved_id})
    return resolved, errors


def _detect_dependency_cycles(graph: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> None:
        marker = state.get(node, 0)
        if marker == 2:
            return
        if marker == 1:
            try:
                index = stack.index(node)
            except ValueError:
                index = 0
            cycle = stack[index:] + [node]
            errors.append("生效依赖图存在环：" + " -> ".join(cycle))
            return
        state[node] = 1
        stack.append(node)
        for target in sorted(graph.get(node, set())):
            visit(target)
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        visit(node)
    return list(dict.fromkeys(errors))


def validate_graph_records(records: Sequence[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    mapping: dict[str, dict[str, Any]] = {}
    for item in records:
        meta = item["meta"]
        if meta["id"] in mapping:
            errors.append(f"编号重复：{meta['id']}")
        mapping[meta["id"]] = item

    for item in records:
        meta = item["meta"]
        idea_id = meta["id"]
        try:
            conflict = normalize_conflict(meta["conflict"], supersedes=meta["supersedes"])
            dependencies = normalize_dependencies(meta["depends_on"])
        except LedgerError as exc:
            errors.append(f"{idea_id}：{exc}")
            continue
        dependency_set = {dep["id"] for dep in dependencies}
        supersedes = set(meta["supersedes"])
        conflicts = set(conflict["conflicts_with"])
        reviewed = set(conflict["reviewed_ids"])
        refs = reviewed | supersedes | dependency_set
        if idea_id in refs:
            errors.append(f"{idea_id} 不能引用自身。")
        missing = sorted(ref for ref in refs if ref not in mapping)
        if missing:
            errors.append(f"{idea_id} 引用了不存在的编号：" + "、".join(missing))
        overlap = sorted(supersedes & dependency_set)
        if overlap:
            errors.append(f"{idea_id} 的 supersedes 与 depends_on 不得重叠：" + "、".join(overlap))
        overlap = sorted(conflicts & dependency_set)
        if overlap:
            errors.append(f"{idea_id} 的 conflicts_with 与 depends_on 不得重叠：" + "、".join(overlap))
        if conflict["disposition"] == "supersede":
            if supersedes != conflicts:
                errors.append(f"{idea_id} 使用 supersede 处置时，supersedes 必须与 conflicts_with 完全一致。")
        elif supersedes:
            errors.append(f"{idea_id} 声明 supersedes 时 conflict.disposition 必须是 supersede。")
        for target in sorted(supersedes):
            target_item = mapping.get(target)
            if not target_item:
                continue
            if target_item["meta"].get("status") != "accepted":
                errors.append(f"{idea_id} 只能替代 stored status=accepted 的记录：{target}")
            if int(target.split("-")[1]) >= int(idea_id.split("-")[1]):
                errors.append(f"{idea_id} 只能替代更早编号：{target}")

    reverse = superseded_by_map(records)
    for target, successors in sorted(reverse.items()):
        if len(successors) > 1:
            errors.append(f"{target} 被多个 accepted 决策并行替代：" + "、".join(successors))

    active = [item for item in records if effective_status(item["meta"], reverse) == "accepted"]
    dependency_graph: dict[str, set[str]] = {item["meta"]["id"]: set() for item in active}
    for item in active:
        meta = item["meta"]
        resolved, dependency_errors = resolved_dependencies_for(meta, mapping, reverse)
        for error in dependency_errors:
            errors.append(f"{meta['id']}：{error}")
        for dependency in resolved:
            target = dependency["resolved_id"]
            dependency_graph[meta["id"]].add(target)
            if target == meta["id"]:
                errors.append(f"{meta['id']} 的依赖解析回自身。")
    errors.extend(_detect_dependency_cycles(dependency_graph))
    return list(dict.fromkeys(errors))


def validate_references(meta: dict[str, Any], existing: dict[str, dict[str, Any]], *, self_id: str | None = None) -> None:
    """Compatibility wrapper used by callers that validate one candidate in a graph."""
    candidate = []
    replaced = False
    for idea_id, item in existing.items():
        if self_id and idea_id == self_id:
            candidate.append({"path": item["path"], "meta": meta})
            replaced = True
        else:
            candidate.append(item)
    if self_id and not replaced:
        candidate.append({"path": Path(f"{self_id}.md"), "meta": meta})
    errors = validate_graph_records(candidate)
    if errors:
        raise LedgerError("；".join(errors))


def validate_acceptance_dependencies(meta: dict[str, Any], existing: dict[str, dict[str, Any]]) -> None:
    candidate: list[dict[str, Any]] = []
    for idea_id, item in existing.items():
        candidate.append({"path": item["path"], "meta": meta if idea_id == meta["id"] else item["meta"]})
    errors = validate_graph_records(candidate)
    dependency_errors = [error for error in errors if "依赖" in error or "depends_on" in error]
    if dependency_errors:
        raise LedgerError("；".join(dependency_errors))


def _candidate_records(
    existing_items: Sequence[dict[str, Any]],
    meta: dict[str, Any],
    path: Path,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    replaced = False
    for item in existing_items:
        if item["meta"]["id"] == meta["id"]:
            result.append({"path": path, "meta": meta})
            replaced = True
        else:
            result.append(item)
    if not replaced:
        result.append({"path": path, "meta": meta})
    return sorted(result, key=lambda item: int(item["meta"]["number"]))


def _ensure_candidate_valid(candidate: Sequence[dict[str, Any]]) -> None:
    errors: list[str] = []
    for item in candidate:
        shape_errors = validate_meta_shape(item["meta"], expected_id=item["meta"]["id"])
        errors.extend(f"{item['meta']['id']}：{error}" for error in shape_errors)
    errors.extend(validate_graph_records(candidate))
    if errors:
        raise LedgerError("候选账本状态无效：\n- " + "\n- ".join(dict.fromkeys(errors)))

__all__ = [name for name in globals() if not name.startswith("__")]
