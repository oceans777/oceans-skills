#!/usr/bin/env python3
"""Context, audit, PRD, and status projections for Idea Ledger."""
from __future__ import annotations

from _idea_ledger_foundation import *
from _idea_ledger_paths import *
from _idea_ledger_normalize import *
from _idea_ledger_records import *
from _idea_ledger_graph import *
from _idea_ledger_storage import *

def text_features(text: str) -> set[str]:
    lower = text.lower()
    features = set(re.findall(r"[a-z0-9][a-z0-9_.-]{1,}", lower))
    for run in re.findall(r"[\u3400-\u9fff]+", lower):
        if len(run) <= 2:
            features.add(run)
        else:
            features.update(run[i : i + 2] for i in range(len(run) - 1))
            features.update(run[i : i + 3] for i in range(len(run) - 2))
    return features


def searchable_text(meta: dict[str, Any]) -> str:
    conflict = normalize_conflict(meta["conflict"], supersedes=meta["supersedes"])
    dependencies = normalize_dependencies(meta["depends_on"])
    parts: list[str] = [
        meta["id"],
        meta["title"],
        meta["goal"],
        meta["decision"],
        meta["outcome"],
        conflict["rationale"],
        conflict.get("mitigation") or "",
        *(meta["scope"]),
        *(meta["tags"]),
        *(meta["constraints"]),
        *(meta["acceptance_criteria"]),
        *(meta["notes"]),
        *(meta["supersedes"]),
        *(conflict["reviewed_ids"]),
        *(conflict["conflicts_with"]),
        *(dep["id"] for dep in dependencies),
    ]
    for field in ("rationale", "owner"):
        if meta.get(field):
            parts.append(str(meta[field]))
    for field in ("alternatives_considered", "tradeoffs", "non_goals", "sources"):
        parts.extend(meta.get(field, []))
    return "\n".join(str(part) for part in parts if part)


def relevance_score(meta: dict[str, Any], query: str) -> float:
    if not query.strip():
        return 0.0
    query_features = text_features(query)
    item_features = text_features(searchable_text(meta))
    if not query_features or not item_features:
        return 0.0
    overlap = query_features & item_features
    score = len(overlap) / max(1, len(query_features))
    q_lower = query.lower()
    score += sum(0.4 for value in meta["scope"] if value.lower() in q_lower)
    score += sum(0.3 for value in meta["tags"] if value.lower() in q_lower)
    if meta["id"].lower() in q_lower:
        score += 1.0
    if meta["title"].lower() in q_lower or q_lower in meta["title"].lower():
        score += 0.5
    return score


def _context_record_data(
    meta: dict[str, Any],
    reverse: dict[str, list[str]],
    mapping: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    conflict = normalize_conflict(meta["conflict"], supersedes=meta["supersedes"])
    resolved, dependency_errors = resolved_dependencies_for(meta, mapping, reverse)
    data: dict[str, Any] = {
        "id": meta["id"],
        "title": meta["title"],
        "status": meta["status"],
        "effective_status": effective_status(meta, reverse),
        "scope": meta["scope"],
        "tags": meta["tags"],
        "goal": meta["goal"],
        "decision": meta["decision"],
        "outcome": meta["outcome"],
        "constraints": meta["constraints"],
        "acceptance_criteria": meta["acceptance_criteria"],
        "conflict": conflict,
        "supersedes": meta["supersedes"],
        "depends_on": normalize_dependencies(meta["depends_on"]),
        "resolved_dependencies": resolved,
        "dependency_errors": dependency_errors,
        "notes": meta["notes"],
    }
    for field in OPTIONAL_RECORD_META_FIELDS:
        if field in meta:
            data[field] = meta[field]
    return data


def _context_snippet(data: dict[str, Any], *, minimal: bool) -> str:
    if minimal:
        decision = str(data["decision"])
        if len(decision) > 220:
            decision = decision[:219] + "…"
        return "\n".join(
            [
                f"### {data['id']}｜{data['title']}",
                f"- 状态：{data['status']}（生效：{data['effective_status']}）",
                f"- 决策：{decision}",
            ]
        )
    conflict = data["conflict"]
    dependency_text = "、".join(
        f"{item['id']}:{item['mode']}" for item in data["depends_on"]
    ) or "无"
    lines = [
        f"### {data['id']}｜{data['title']}",
        f"- 状态：{data['status']}（生效：{data['effective_status']}）",
        f"- 范围：{'、'.join(data['scope'])}",
        f"- 标签：{'、'.join(data['tags']) if data['tags'] else '无'}",
        f"- 目标：{data['goal']}",
        f"- 决策：{data['decision']}",
        f"- 结果：{data['outcome']}",
        f"- 冲突：{conflict['compatibility']}/{conflict['disposition']}；"
        f"已审查：{'、'.join(conflict['reviewed_ids']) if conflict['reviewed_ids'] else '无'}；"
        f"冲突：{'、'.join(conflict['conflicts_with']) if conflict['conflicts_with'] else '无'}；"
        f"置信度：{conflict['confidence']}；依据：{conflict['rationale']}；"
        f"边界：{conflict['mitigation'] or '无'}",
        f"- 关系：替代 {'、'.join(data['supersedes']) if data['supersedes'] else '无'}；依赖 {dependency_text}",
        f"- 约束：{'；'.join(data['constraints']) if data['constraints'] else '无'}",
        f"- 验收：{'；'.join(data['acceptance_criteria']) if data['acceptance_criteria'] else '无'}",
    ]
    if data.get("rationale"):
        lines.append(f"- 决策依据：{data['rationale']}")
    if data.get("notes"):
        lines.append(f"- 备注：{'；'.join(data['notes'])}")
    return "\n".join(lines)


def build_context_data(
    root: Path,
    query: str,
    *,
    limit: int | None = None,
    max_chars: int | None = None,
    include_proposed: bool = False,
) -> dict[str, Any]:
    config = load_config(root)
    records = load_records(root, config)
    reverse = superseded_by_map(records)
    mapping = {item["meta"]["id"]: item for item in records}
    default_limit = int(config["max_related_records"])
    default_chars = int(config["max_context_chars"])
    limit = default_limit if limit is None else max(1, min(limit, 100))
    max_chars = default_chars if max_chars is None else max(500, min(max_chars, 200000))
    eligible = [
        item
        for item in records
        if effective_status(item["meta"], reverse) == "accepted"
        or (include_proposed and item["meta"]["status"] == "proposed")
    ]
    scored = [(relevance_score(item["meta"], query), item) for item in eligible]
    ranked = [
        item
        for _, item in sorted(
            scored,
            key=lambda pair: (pair[0], int(pair[1]["meta"]["number"])),
            reverse=True,
        )
    ]
    if query.strip():
        positive = [item for score, item in scored if score > 0]
        positive_ids = {item["meta"]["id"] for item in positive}
        ranked_positive = [item for item in ranked if item["meta"]["id"] in positive_ids]
        ranked = ranked_positive or ranked[: min(3, len(ranked))]
    selected = ranked[:limit]
    normalized_query = re.sub(r"\s+", " ", query.strip())
    query_display = normalized_query
    query_truncated = False
    query_limit = max(80, min(300, max_chars // 4))
    if len(query_display) > query_limit:
        query_display = query_display[: max(1, query_limit - 1)] + "…"
        query_truncated = True
    data_records = [_context_record_data(item["meta"], reverse, mapping) for item in selected]
    return {
        "query": normalized_query,
        "query_display": query_display or "（未提供，按最近记录）",
        "query_truncated": query_truncated,
        "selected_count": len(selected),
        "available_count": len(eligible),
        "max_chars": max_chars,
        "records": data_records,
    }


def render_context_data(data: dict[str, Any]) -> str:
    max_chars = int(data["max_chars"])
    header = "\n".join(
        [
            "# Idea Ledger 相关决策上下文",
            "",
            f"查询：{data['query_display']}",
            f"候选：{data['selected_count']} / 可用记录 {data['available_count']}",
            "说明：以下是确定性检索候选，不等于语义冲突结论；必须引用具体记录再判断。",
            "",
        ]
    )
    if len(header) >= max_chars:
        return (header[: max_chars - 1] + "…")[:max_chars]
    snippets: list[str] = []
    emitted = 0
    degraded = 0
    # Reserve a footer before selecting content.
    footer_reserve = 90
    for record in data["records"]:
        full = _context_snippet(record, minimal=False) + "\n\n"
        minimal = _context_snippet(record, minimal=True) + "\n\n"
        current_len = len(header) + sum(len(item) for item in snippets)
        if current_len + len(full) + footer_reserve <= max_chars:
            snippets.append(full)
            emitted += 1
        elif current_len + len(minimal) + footer_reserve <= max_chars:
            snippets.append(minimal)
            emitted += 1
            degraded += 1
        else:
            break
    truncated = emitted < data["selected_count"] or degraded > 0 or data["query_truncated"]
    if emitted == 0:
        fallback = "无可用记录，或上下文预算不足。\n"
        if len(header) + len(fallback) + footer_reserve <= max_chars:
            snippets.append(fallback)
    footer = (
        f"截断：{'是' if truncated else '否'}；已输出 {emitted}/{data['selected_count']} 条"
        + (f"；其中 {degraded} 条为最小摘要" if degraded else "")
        + "。\n"
    )
    result = header + "".join(snippets) + footer
    if len(result) > max_chars:
        result = result[: max_chars - 1] + "…"
    return result


def build_context(
    root: Path,
    query: str,
    *,
    limit: int | None = None,
    max_chars: int | None = None,
    include_proposed: bool = False,
) -> str:
    return render_context_data(
        build_context_data(
            root,
            query,
            limit=limit,
            max_chars=max_chars,
            include_proposed=include_proposed,
        )
    )


def build_audit_page_data(root: Path, page: int, page_size: int) -> dict[str, Any]:
    config = load_config(root)
    records = load_records(root, config)
    reverse = superseded_by_map(records)
    mapping = {item["meta"]["id"]: item for item in records}
    page_size = max(1, min(page_size, 100))
    total_pages = max(1, (len(records) + page_size - 1) // page_size)
    page = min(max(1, page), total_pages)
    start = (page - 1) * page_size
    selected = records[start : start + page_size]
    payload_records: list[dict[str, Any]] = []
    for item in selected:
        meta = copy.deepcopy(item["meta"])
        resolved, dependency_errors = resolved_dependencies_for(meta, mapping, reverse)
        payload_records.append(
            {
                "meta": meta,
                "effective_status": effective_status(meta, reverse),
                "superseded_by": reverse.get(meta["id"], []),
                "canonical_conflict": normalize_conflict(meta["conflict"], supersedes=meta["supersedes"]),
                "canonical_dependencies": normalize_dependencies(meta["depends_on"]),
                "resolved_dependencies": resolved,
                "dependency_errors": dependency_errors,
                "record_digest": record_digest(meta),
            }
        )
    return {
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "total_records": len(records),
        "first_record": start + 1 if records else 0,
        "last_record": min(start + page_size, len(records)) if records else 0,
        "next_page": page + 1 if page < total_pages else None,
        "records": payload_records,
    }


def build_audit_page(root: Path, page: int, page_size: int) -> str:
    data = build_audit_page_data(root, page, page_size)
    lines = [
        "# Idea Ledger 全量审计页",
        "",
        f"页码：{data['page']}/{data['total_pages']}；记录：{data['first_record']}-{data['last_record']}/{data['total_records']}",
        "说明：每条记录以下以完整 JSON 输出；这不代表脚本完成了语义冲突判断。",
        "",
    ]
    for record in data["records"]:
        meta = record["meta"]
        lines.extend(
            [
                f"## {meta['id']}｜{meta['title']}",
                "",
                "```json",
                json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def build_audit_jsonl(root: Path, page: int, page_size: int) -> str:
    data = build_audit_page_data(root, page, page_size)
    page_meta = {key: value for key, value in data.items() if key != "records"}
    lines = [json.dumps({"type": "page", **page_meta}, ensure_ascii=False, sort_keys=True)]
    lines.extend(
        json.dumps({"type": "record", **record}, ensure_ascii=False, sort_keys=True)
        for record in data["records"]
    )
    return "\n".join(lines) + "\n"


def create_prd_template(root: Path, idea_id: str) -> Path:
    root = ensure_root(root)
    config = load_config(root)
    idea_id = normalize_id(idea_id)
    with ledger_lock(root):
        records = load_records(root, config)
        mapping = {item["meta"]["id"]: item for item in records}
        item = mapping.get(idea_id)
        if not item:
            raise LedgerError(f"记录不存在：{idea_id}")
        reverse = superseded_by_map(records)
        meta = item["meta"]
        effective = effective_status(meta, reverse)
        if effective != "accepted":
            raise LedgerError(f"只能为当前生效的 accepted 决策创建 PRD；{idea_id} 为 {effective}。")
        path = prd_dir(root, config) / f"PRD-{idea_id}.md"
        prd_meta = {
            "schema": 1,
            "idea_id": idea_id,
            "idea_digest": record_digest(meta),
            "generated_at": utc_now(),
        }
        criteria = "\n".join(f"- [ ] {entry}" for entry in meta["acceptance_criteria"]) or "- [ ] 待补充"
        constraints = "\n".join(f"- {entry}" for entry in meta["constraints"]) or "- 无"
        non_goals = "\n".join(f"- {entry}" for entry in meta.get("non_goals", [])) or "- 待补充"
        text = f"""{prd_metadata_block(prd_meta)}

# PRD：{idea_id}｜{meta['title']}

> 决策基线：`{idea_id}`；摘要：`{prd_meta['idea_digest']}`。本文件不得悄悄改变其目标、决策或预期结果；变化应创建新的 Idea Ledger 记录。

## 1. 背景与问题
待补充。

## 2. 决策基线
- 目标：{meta['goal']}
- 决策：{meta['decision']}
- 预期结果：{meta['outcome']}
- 决策依据：{meta.get('rationale') or '参见 Idea Ledger 记录'}

## 3. 范围与非范围
- 范围：{'、'.join(meta['scope'])}
- 非范围：
{non_goals}

## 4. 用户与场景
待补充。

## 5. 功能需求
待补充。

## 6. 约束
{constraints}

## 7. 验收标准
{criteria}

## 8. 风险、观测与回滚
待补充。
"""
        atomic_create_text(path, text)
        return path


def list_records_data(root: Path, status: str | None = None) -> list[dict[str, Any]]:
    config = load_config(root)
    records = load_records(root, config)
    reverse = superseded_by_map(records)
    result: list[dict[str, Any]] = []
    for item in records:
        meta = item["meta"]
        if status and meta["status"] != status:
            continue
        conflict = normalize_conflict(meta["conflict"], supersedes=meta["supersedes"])
        result.append(
            {
                "id": meta["id"],
                "title": meta["title"],
                "status": meta["status"],
                "effective_status": effective_status(meta, reverse),
                "compatibility": conflict["compatibility"],
                "disposition": conflict["disposition"],
                "path": str(item["path"]),
            }
        )
    return result


def status_summary(root: Path) -> dict[str, Any]:
    config = load_config(root)
    records = load_records(root, config)
    reverse = superseded_by_map(records)
    counts = {status: 0 for status in sorted(STATUSES)}
    effective_counts: dict[str, int] = {}
    for item in records:
        meta = item["meta"]
        counts[meta["status"]] += 1
        effective = effective_status(meta, reverse)
        effective_counts[effective] = effective_counts.get(effective, 0) + 1
    validation_errors = validate_graph_records(records)
    return {
        "version": VERSION,
        "schema": SCHEMA_VERSION,
        "records": len(records),
        "counts": counts,
        "effective_counts": effective_counts,
        "latest_id": records[-1]["meta"]["id"] if records else None,
        "next_id": next_id(root, config),
        "graph_valid": not validation_errors,
        "graph_errors": validation_errors,
        "config": config,
    }

__all__ = [name for name in globals() if not name.startswith("__")]
