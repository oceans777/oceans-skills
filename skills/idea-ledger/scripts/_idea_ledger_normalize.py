#!/usr/bin/env python3
"""Metadata parsing and input normalization for Idea Ledger."""
from __future__ import annotations

from _idea_ledger_foundation import *
from _idea_ledger_paths import *

def parse_metadata(text: str, *, path: Path | None = None) -> dict[str, Any]:
    start = text.find(META_START)
    end = text.find(META_END)
    label = f"：{path}" if path else ""
    if start != 0 or end < 0:
        raise LedgerError(f"记录缺少或错置元数据块{label}")
    raw = text[start + len(META_START) : end].strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LedgerError(f"记录元数据 JSON 无效{label}：{exc}") from exc
    if not isinstance(data, dict):
        raise LedgerError(f"记录元数据必须是对象{label}")
    return data


def metadata_block(meta: dict[str, Any]) -> str:
    return f"{META_START}\n{json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True)}\n{META_END}"


def clean_string(
    value: Any,
    label: str,
    *,
    minimum: int = 1,
    maximum: int = 4000,
    single_line: bool = False,
) -> str:
    if not isinstance(value, str):
        raise LedgerError(f"{label} 必须是字符串。")
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"\s+", " ", normalized) if single_line else re.sub(r"[ \t]+", " ", normalized)
    if META_START in text or META_END in text or PRD_META_START in text or PRD_META_END in text:
        raise LedgerError(f"{label} 包含保留的元数据标记。")
    if len(text) < minimum:
        raise LedgerError(f"{label} 不能为空。")
    if len(text) > maximum:
        raise LedgerError(f"{label} 不能超过 {maximum} 个字符。")
    return text


def clean_optional_string(value: Any, label: str, *, maximum: int, single_line: bool = False) -> str | None:
    if value in (None, ""):
        return None
    return clean_string(value, label, maximum=maximum, single_line=single_line)


def clean_string_list(
    value: Any,
    label: str,
    *,
    required: bool = False,
    max_items: int = 30,
    item_max: int = 500,
) -> list[str]:
    if value is None:
        value = []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise LedgerError(f"{label} 必须是字符串数组。")
    items: list[str] = []
    seen: set[str] = set()
    for raw in value:
        item = clean_string(raw, label, maximum=item_max, single_line=True)
        if item not in seen:
            items.append(item)
            seen.add(item)
    if required and not items:
        raise LedgerError(f"{label} 至少需要一项。")
    if len(items) > max_items:
        raise LedgerError(f"{label} 最多 {max_items} 项。")
    return items


def clean_id_list(value: Any, label: str) -> list[str]:
    raw = clean_string_list(value, label, max_items=30, item_max=40)
    result: list[str] = []
    for item in raw:
        normalized = normalize_id(item)
        if normalized not in result:
            result.append(normalized)
    return result


def normalize_charter(value: Any, *, required: bool = True) -> dict[str, Any] | None:
    """Normalize the short governing charter used to generate all detailed fields."""
    if value is None:
        if required:
            raise LedgerError("charter（总纲领）不能为空。")
        return None
    if not isinstance(value, dict):
        raise LedgerError("charter（总纲领）必须是对象。")
    unknown = sorted(set(value) - CHARTER_FIELDS)
    missing = sorted(CHARTER_FIELDS - set(value))
    if unknown:
        raise LedgerError("charter 包含未知字段：" + "、".join(unknown))
    if missing:
        raise LedgerError("charter 缺少字段：" + "、".join(missing))
    return {
        "goal": clean_string(value.get("goal"), "charter.goal", maximum=240, single_line=True),
        "actors": clean_string_list(
            value.get("actors"), "charter.actors", required=True, max_items=5, item_max=80
        ),
        "scope": clean_string_list(
            value.get("scope"), "charter.scope", required=True, max_items=5, item_max=160
        ),
        "principles": clean_string_list(
            value.get("principles"), "charter.principles", required=True, max_items=5, item_max=200
        ),
        "non_goals": clean_string_list(
            value.get("non_goals"), "charter.non_goals", max_items=3, item_max=160
        ),
    }


def normalize_dependencies(value: Any, label: str = "depends_on") -> list[dict[str, str]]:
    if value is None:
        value = []
    if not isinstance(value, list):
        raise LedgerError(f"{label} 必须是数组。")
    result: list[dict[str, str]] = []
    seen: dict[str, str] = {}
    for raw in value:
        if isinstance(raw, str):
            idea_id = normalize_id(raw)
            mode = "lineage"
        elif isinstance(raw, dict):
            unknown = sorted(set(raw) - {"id", "mode"})
            missing = sorted({"id", "mode"} - set(raw))
            if unknown:
                raise LedgerError(f"{label} 项包含未知字段：" + "、".join(unknown))
            if missing:
                raise LedgerError(f"{label} 项缺少字段：" + "、".join(missing))
            idea_id = normalize_id(str(raw.get("id") or ""))
            mode = str(raw.get("mode") or "").strip().lower()
            if mode not in DEPENDENCY_MODES:
                raise LedgerError(f"{label}.mode 必须是 exact 或 lineage。")
        else:
            raise LedgerError(f"{label} 项必须是 IDEA 编号字符串或包含 id/mode 的对象。")
        previous = seen.get(idea_id)
        if previous and previous != mode:
            raise LedgerError(f"{label} 对 {idea_id} 同时声明了不同模式。")
        if not previous:
            seen[idea_id] = mode
            result.append({"id": idea_id, "mode": mode})
    if len(result) > 30:
        raise LedgerError(f"{label} 最多 30 项。")
    return result


def dependency_ids(meta: dict[str, Any]) -> list[str]:
    return [item["id"] for item in normalize_dependencies(meta.get("depends_on", []))]


def _normalize_new_conflict(value: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(value) - CONFLICT_FIELDS)
    missing = sorted(CONFLICT_FIELDS - set(value))
    if unknown:
        raise LedgerError("conflict 包含未知字段：" + "、".join(unknown))
    if missing:
        raise LedgerError("conflict 缺少字段：" + "、".join(missing))
    compatibility = str(value.get("compatibility") or "").strip().lower()
    if compatibility not in COMPATIBILITY_LEVELS:
        raise LedgerError("conflict.compatibility 必须是 compatible、duplicate、tension、incompatible 或 unknown。")
    disposition = str(value.get("disposition") or "").strip().lower()
    if disposition not in DISPOSITIONS:
        raise LedgerError("conflict.disposition 必须是 none、bounded、supersede 或 defer。")
    confidence = str(value.get("confidence") or "").strip().lower()
    if confidence not in CONFIDENCE_LEVELS:
        raise LedgerError("conflict.confidence 必须是 low、medium 或 high。")
    reviewed = clean_id_list(value.get("reviewed_ids", []), "conflict.reviewed_ids")
    conflicts = clean_id_list(value.get("conflicts_with", []), "conflict.conflicts_with")
    rationale = clean_string(value.get("rationale"), "conflict.rationale", maximum=3000)
    mitigation = clean_optional_string(value.get("mitigation"), "conflict.mitigation", maximum=3000)
    missing_review = sorted(set(conflicts) - set(reviewed))
    if missing_review:
        raise LedgerError("conflict.conflicts_with 必须同时列入 reviewed_ids：" + "、".join(missing_review))

    if compatibility == "compatible":
        if conflicts or disposition != "none":
            raise LedgerError("compatible 必须使用 disposition=none 且 conflicts_with 为空。")
        if mitigation is not None:
            raise LedgerError("compatible/none 不应提供 mitigation。")
    elif compatibility == "duplicate":
        if not conflicts or disposition != "defer":
            raise LedgerError("duplicate 必须引用 conflicts_with 并使用 disposition=defer。")
    elif compatibility == "tension":
        if not conflicts or disposition not in {"bounded", "defer"}:
            raise LedgerError("tension 必须引用 conflicts_with，并使用 bounded 或 defer。")
        if disposition == "bounded" and not mitigation:
            raise LedgerError("tension/bounded 必须提供 mitigation。")
    elif compatibility == "incompatible":
        if not conflicts or disposition not in {"supersede", "defer"}:
            raise LedgerError("incompatible 必须引用 conflicts_with，并使用 supersede 或 defer。")
        if disposition == "supersede" and not mitigation:
            raise LedgerError("incompatible/supersede 必须提供 mitigation，说明替代边界。")
    elif compatibility == "unknown":
        if disposition != "defer":
            raise LedgerError("unknown 必须使用 disposition=defer。")
    return {
        "compatibility": compatibility,
        "reviewed_ids": reviewed,
        "conflicts_with": conflicts,
        "rationale": rationale,
        "confidence": confidence,
        "disposition": disposition,
        "mitigation": mitigation,
    }


def _normalize_legacy_conflict(value: dict[str, Any], *, supersedes: Sequence[str] = ()) -> dict[str, Any]:
    unknown = sorted(set(value) - LEGACY_CONFLICT_FIELDS)
    missing = sorted(LEGACY_CONFLICT_FIELDS - set(value))
    if unknown:
        raise LedgerError("conflict 包含未知字段：" + "、".join(unknown))
    if missing:
        raise LedgerError("legacy conflict 缺少字段：" + "、".join(missing))
    kind = str(value.get("kind") or "").strip().lower()
    if kind not in LEGACY_CONFLICT_KINDS:
        raise LedgerError("legacy conflict.kind 无效。")
    confidence = str(value.get("confidence") or "").strip().lower()
    if confidence not in CONFIDENCE_LEVELS:
        raise LedgerError("conflict.confidence 必须是 low、medium 或 high。")
    related = clean_id_list(value.get("related_ids", []), "conflict.related_ids")
    rationale = clean_string(value.get("rationale"), "conflict.rationale", maximum=3000)
    resolution = clean_optional_string(value.get("resolution"), "conflict.resolution", maximum=3000)
    if kind in {"duplicate", "tension", "hard_conflict", "resolved"} and not related:
        raise LedgerError(f"conflict.kind={kind} 时必须提供 related_ids。")
    if kind == "resolved" and not resolution:
        raise LedgerError("conflict.kind=resolved 时必须提供 resolution。")

    if kind == "none":
        compatibility, conflicts, disposition, mitigation = "compatible", [], "none", None
    elif kind == "duplicate":
        compatibility, conflicts, disposition, mitigation = "duplicate", related, "defer", resolution
    elif kind == "tension":
        compatibility, conflicts = "tension", related
        disposition, mitigation = ("bounded", resolution) if resolution else ("defer", None)
    elif kind == "hard_conflict":
        compatibility, conflicts, disposition, mitigation = "incompatible", related, "defer", resolution
    elif kind == "resolved":
        compatibility, conflicts = ("incompatible", related) if supersedes else ("tension", related)
        disposition, mitigation = ("supersede", resolution) if supersedes else ("bounded", resolution)
    else:
        compatibility, conflicts, disposition, mitigation = "unknown", related, "defer", resolution
    return {
        "compatibility": compatibility,
        "reviewed_ids": related,
        "conflicts_with": conflicts,
        "rationale": rationale,
        "confidence": confidence,
        "disposition": disposition,
        "mitigation": mitigation,
    }


def conflict_is_legacy(value: Any) -> bool:
    return isinstance(value, dict) and "kind" in value


def normalize_conflict(value: Any, *, supersedes: Sequence[str] = ()) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LedgerError("conflict 必须是对象。")
    if "kind" in value:
        return _normalize_legacy_conflict(value, supersedes=supersedes)
    return _normalize_new_conflict(value)


def normalize_conflict_input(value: Any, *, supersedes: Sequence[str] = ()) -> dict[str, Any]:
    """Normalize old or new input to the current two-axis representation."""
    return normalize_conflict(value, supersedes=supersedes)


def load_payload(source: str) -> dict[str, Any]:
    if source == "-":
        raw = sys.stdin.read()
        label = "stdin"
    else:
        path = Path(source).expanduser()
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise LedgerError(f"无法读取输入文件：{path}：{exc}") from exc
        label = str(path)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LedgerError(f"输入 JSON 无效（{label}）：{exc}") from exc
    if not isinstance(data, dict):
        raise LedgerError("输入 JSON 顶层必须是对象。")
    return data


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "title",
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
        *OPTIONAL_RECORD_META_FIELDS,
    }
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise LedgerError("输入包含未知字段：" + "、".join(unknown))
    supersedes = clean_id_list(payload.get("supersedes", []), "supersedes")
    result: dict[str, Any] = {
        "title": clean_string(payload.get("title"), "title", maximum=120, single_line=True),
        "charter": normalize_charter(payload.get("charter"), required=True),
        "goal": clean_string(payload.get("goal"), "goal", maximum=3000),
        "decision": clean_string(payload.get("decision"), "decision", maximum=4000),
        "outcome": clean_string(payload.get("outcome"), "outcome", maximum=3000),
        "scope": clean_string_list(payload.get("scope"), "scope", required=True, max_items=20, item_max=120),
        "tags": clean_string_list(payload.get("tags", []), "tags", max_items=30, item_max=80),
        "constraints": clean_string_list(payload.get("constraints", []), "constraints", max_items=30, item_max=500),
        "acceptance_criteria": clean_string_list(
            payload.get("acceptance_criteria", []),
            "acceptance_criteria",
            required=True,
            max_items=30,
            item_max=500,
        ),
        "conflict": normalize_conflict_input(payload.get("conflict"), supersedes=supersedes),
        "supersedes": supersedes,
        "depends_on": normalize_dependencies(payload.get("depends_on", [])),
        "notes": clean_string_list(payload.get("notes", []), "notes", max_items=30, item_max=1000),
    }
    if "rationale" in payload:
        result["rationale"] = clean_optional_string(payload.get("rationale"), "rationale", maximum=4000)
    for field in ("alternatives_considered", "tradeoffs", "non_goals", "sources"):
        if field in payload:
            result[field] = clean_string_list(payload.get(field, []), field, max_items=30, item_max=1000)
    if "owner" in payload:
        result["owner"] = clean_optional_string(payload.get("owner"), "owner", maximum=200, single_line=True)
    if "review_at" in payload:
        review_at = payload.get("review_at")
        if review_at in (None, ""):
            result["review_at"] = None
        else:
            parse_timestamp(review_at, "review_at")
            result["review_at"] = str(review_at)
    return result

def parse_timestamp(value: Any, label: str) -> dt.datetime:
    if not isinstance(value, str) or not value:
        raise LedgerError(f"{label} 缺失或不是字符串。")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LedgerError(f"{label} 不是有效 ISO-8601 时间：{value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise LedgerError(f"{label} 必须包含时区偏移。")
    return parsed

__all__ = [name for name in globals() if not name.startswith("__")]
