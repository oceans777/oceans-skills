#!/usr/bin/env python3
"""Record rendering and shape validation for Idea Ledger."""
from __future__ import annotations

from _idea_ledger_foundation import *
from _idea_ledger_paths import *
from _idea_ledger_normalize import *

def render_bullets(items: Sequence[str], *, empty: str = "无") -> list[str]:
    return [f"- {item}" for item in items] if items else [f"- {empty}"]


def _render_dependency(item: Any) -> str:
    if isinstance(item, str):
        return item
    normalized = normalize_dependencies([item])[0]
    return f"{normalized['id']}（{normalized['mode']}）"


def render_record(meta: dict[str, Any]) -> str:
    conflict = meta["conflict"]
    lines = [
        metadata_block(meta),
        "",
        f"# {meta['id']}：{meta['title']}",
        "",
        "## 目标",
        meta["goal"],
        "",
        "## 决策",
        meta["decision"],
        "",
    ]
    if "rationale" in meta:
        lines.extend(["## 决策依据", meta.get("rationale") or "未单独记录。", ""])
    lines.extend(
        [
            "## 预期结果",
            meta["outcome"],
            "",
            "## 范围",
            *render_bullets(meta["scope"]),
            "",
        ]
    )
    if "non_goals" in meta:
        lines.extend(["## 非目标", *render_bullets(meta.get("non_goals", [])), ""])
    lines.extend(["## 约束", *render_bullets(meta["constraints"]), ""])
    if "alternatives_considered" in meta:
        lines.extend(["## 备选方案", *render_bullets(meta.get("alternatives_considered", [])), ""])
    if "tradeoffs" in meta:
        lines.extend(["## 权衡", *render_bullets(meta.get("tradeoffs", [])), ""])
    lines.extend(["## 验收标准", *render_bullets(meta["acceptance_criteria"]), "", "## 冲突评估"])
    if conflict_is_legacy(conflict):
        lines.extend(
            [
                f"- 类型：{conflict['kind']}",
                f"- 相关编号：{'、'.join(conflict['related_ids']) if conflict['related_ids'] else '无'}",
                f"- 置信度：{conflict['confidence']}",
                f"- 依据：{conflict['rationale']}",
                f"- 化解方式：{conflict['resolution'] or '无'}",
            ]
        )
    else:
        lines.extend(
            [
                f"- 兼容性：{conflict['compatibility']}",
                f"- 已审查编号：{'、'.join(conflict['reviewed_ids']) if conflict['reviewed_ids'] else '无'}",
                f"- 冲突编号：{'、'.join(conflict['conflicts_with']) if conflict['conflicts_with'] else '无'}",
                f"- 处置：{conflict['disposition']}",
                f"- 置信度：{conflict['confidence']}",
                f"- 依据：{conflict['rationale']}",
                f"- 边界或缓解：{conflict['mitigation'] or '无'}",
            ]
        )
    depends = [_render_dependency(item) for item in meta["depends_on"]]
    lines.extend(
        [
            "",
            "## 关系",
            f"- 替代：{'、'.join(meta['supersedes']) if meta['supersedes'] else '无'}",
            f"- 依赖：{'、'.join(depends) if depends else '无'}",
            f"- 标签：{'、'.join(meta['tags']) if meta['tags'] else '无'}",
            "",
            "## 备注",
            *render_bullets(meta["notes"]),
            "",
        ]
    )
    if "sources" in meta:
        lines.extend(["## 来源", *render_bullets(meta.get("sources", [])), ""])
    if "owner" in meta or "review_at" in meta:
        lines.extend(
            [
                "## 所有者与复审",
                f"- 所有者：{meta.get('owner') or '未指定'}",
                f"- 复审时间：{meta.get('review_at') or '未指定'}",
                "",
            ]
        )
    return "\n".join(lines)
def conflict_is_approvable(meta: dict[str, Any]) -> tuple[bool, str]:
    conflict = normalize_conflict(meta.get("conflict"), supersedes=meta.get("supersedes", []))
    compatibility = conflict["compatibility"]
    disposition = conflict["disposition"]
    if compatibility == "compatible" and disposition == "none":
        return True, "compatible/none"
    if compatibility == "tension" and disposition == "bounded" and conflict.get("mitigation"):
        return True, "tension/bounded"
    if compatibility == "incompatible" and disposition == "supersede" and conflict.get("mitigation"):
        return True, "incompatible/supersede"
    return False, f"{compatibility}/{disposition}"


def _validate_optional_record_fields(meta: dict[str, Any], errors: list[str]) -> None:
    try:
        if "rationale" in meta:
            normalized = clean_optional_string(meta.get("rationale"), "rationale", maximum=4000)
            if meta.get("rationale") != normalized:
                errors.append("rationale 未规范化")
        for field in ("alternatives_considered", "tradeoffs", "non_goals", "sources"):
            if field in meta:
                normalized_list = clean_string_list(meta.get(field), field, max_items=30, item_max=1000)
                if meta.get(field) != normalized_list:
                    errors.append(f"{field} 未规范化")
        if "owner" in meta:
            owner = clean_optional_string(meta.get("owner"), "owner", maximum=200, single_line=True)
            if meta.get("owner") != owner:
                errors.append("owner 未规范化")
        if "review_at" in meta and meta.get("review_at") is not None:
            parse_timestamp(meta.get("review_at"), "review_at")
    except LedgerError as exc:
        errors.append(str(exc))


def validate_meta_shape(meta: dict[str, Any], *, expected_id: str | None = None) -> list[str]:
    errors: list[str] = []
    try:
        unknown = sorted(set(meta) - RECORD_META_FIELDS)
        missing = sorted(REQUIRED_RECORD_META_FIELDS - set(meta))
        if unknown:
            errors.append("元数据包含未知字段：" + "、".join(unknown))
        if missing:
            errors.append("元数据缺少字段：" + "、".join(missing))
        if meta.get("schema") != SCHEMA_VERSION:
            errors.append(f"schema 应为 {SCHEMA_VERSION}")
        idea_id = normalize_id(str(meta.get("id") or ""))
        if meta.get("id") != idea_id:
            errors.append(f"id 必须使用规范格式 {idea_id}")
        if expected_id and idea_id != expected_id:
            errors.append(f"文件名编号 {expected_id} 与元数据编号 {idea_id} 不一致")
        number = meta.get("number")
        expected_number = int(idea_id.split("-")[1])
        if type(number) is not int or number != expected_number:
            errors.append(f"number 应为 {expected_number}")
        status = meta.get("status")
        if status not in STATUSES:
            errors.append("status 无效")

        created_at = parse_timestamp(meta.get("created_at"), "created_at")
        updated_at = parse_timestamp(meta.get("updated_at"), "updated_at")
        if updated_at < created_at:
            errors.append("updated_at 早于 created_at")

        simple_values = {
            "title": clean_string(meta.get("title"), "title", maximum=120, single_line=True),
            "goal": clean_string(meta.get("goal"), "goal", maximum=3000),
            "decision": clean_string(meta.get("decision"), "decision", maximum=4000),
            "outcome": clean_string(meta.get("outcome"), "outcome", maximum=3000),
            "scope": clean_string_list(meta.get("scope"), "scope", required=True, max_items=20, item_max=120),
            "tags": clean_string_list(meta.get("tags"), "tags", max_items=30, item_max=80),
            "constraints": clean_string_list(meta.get("constraints"), "constraints", max_items=30, item_max=500),
            "acceptance_criteria": clean_string_list(
                meta.get("acceptance_criteria"), "acceptance_criteria", max_items=30, item_max=500
            ),
            "supersedes": clean_id_list(meta.get("supersedes"), "supersedes"),
            "notes": clean_string_list(meta.get("notes"), "notes", max_items=30, item_max=1000),
        }
        for key, value in simple_values.items():
            if meta.get(key) != value:
                errors.append(f"{key} 未规范化或与 schema 不符")

        conflict = normalize_conflict(meta.get("conflict"), supersedes=simple_values["supersedes"])
        if not conflict_is_legacy(meta.get("conflict")) and meta.get("conflict") != conflict:
            errors.append("conflict 未规范化")
        dependencies = normalize_dependencies(meta.get("depends_on"))
        if meta.get("depends_on") and all(isinstance(item, dict) for item in meta.get("depends_on", [])):
            if meta.get("depends_on") != dependencies:
                errors.append("depends_on 未规范化")

        _validate_optional_record_fields(meta, errors)

        approval = meta.get("approval")
        accepted_at_raw = meta.get("accepted_at")
        rejected_at_raw = meta.get("rejected_at")
        rejection_reason = meta.get("rejection_reason")
        if status == "proposed":
            if any(value is not None for value in (accepted_at_raw, rejected_at_raw, rejection_reason, approval)):
                errors.append("proposed 记录不得包含批准或拒绝终态字段")
        elif status == "accepted":
            accepted_at = parse_timestamp(accepted_at_raw, "accepted_at")
            if accepted_at < created_at:
                errors.append("accepted_at 不得早于 created_at")
            if updated_at != accepted_at:
                errors.append("accepted 记录必须满足 updated_at == accepted_at")
            if rejected_at_raw is not None or rejection_reason is not None:
                errors.append("accepted 记录不得包含拒绝字段")
            if not isinstance(approval, dict):
                errors.append("accepted 记录缺少显式批准记录")
            else:
                approval_unknown = sorted(set(approval) - APPROVAL_FIELDS)
                approval_missing = sorted(APPROVAL_FIELDS - set(approval))
                if approval_unknown:
                    errors.append("approval 包含未知字段：" + "、".join(approval_unknown))
                if approval_missing:
                    errors.append("approval 缺少字段：" + "、".join(approval_missing))
                if approval.get("method") != "explicit_phrase":
                    errors.append("approval.method 必须是 explicit_phrase")
                phrase = approval.get("recorded_phrase")
                allowed_phrases = {f"批准 {idea_id}".upper(), f"APPROVE {idea_id}"}
                if not isinstance(phrase, str) or phrase not in allowed_phrases:
                    errors.append("approval.recorded_phrase 与记录编号不匹配")
                if approval.get("actor_verified") is not False:
                    errors.append("approval.actor_verified 必须为 false；CLI 不认证说话者身份")
                recorded_at = parse_timestamp(approval.get("recorded_at"), "approval.recorded_at")
                if recorded_at != accepted_at:
                    errors.append("approval.recorded_at 应与 accepted_at 一致")
            approvable, classification = conflict_is_approvable(meta)
            if not approvable:
                errors.append(f"accepted 记录的冲突处置不可批准：{classification}")
        elif status == "rejected":
            rejected_at = parse_timestamp(rejected_at_raw, "rejected_at")
            if rejected_at < created_at:
                errors.append("rejected_at 不得早于 created_at")
            if updated_at != rejected_at:
                errors.append("rejected 记录必须满足 updated_at == rejected_at")
            if accepted_at_raw is not None or approval is not None:
                errors.append("rejected 记录不得包含批准字段")
            normalized_reason = clean_string(rejection_reason, "rejection_reason", maximum=2000)
            if rejection_reason != normalized_reason:
                errors.append("rejection_reason 未规范化")
    except LedgerError as exc:
        errors.append(str(exc))
    return errors

__all__ = [name for name in globals() if not name.startswith("__")]
