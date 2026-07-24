#!/usr/bin/env python3
"""Transactional ledger storage and validation for Idea Ledger."""
from __future__ import annotations

from _idea_ledger_foundation import *
from _idea_ledger_paths import *
from _idea_ledger_normalize import *
from _idea_ledger_records import *
from _idea_ledger_graph import *

def init_project(root: Path) -> dict[str, Any]:
    root = ensure_root(root)
    with ledger_lock(root):
        path = config_path(root)
        if path.exists():
            config = load_config(root)
        else:
            config = default_config()
            validate_config_topology(root, config, label="默认配置")
            atomic_write_json(path, config)
        ignore_path = safe_project_path(root, CONFIG_IGNORE_FILE, "config_ignore_file")
        ignore_text = ""
        if ignore_path.exists():
            ignore_text = read_managed_text(ignore_path, "Idea Ledger .gitignore")
        ignore_lines = [line.rstrip("\r\n") for line in ignore_text.splitlines()]
        if "ledger.lock" not in ignore_lines:
            suffix = "" if not ignore_text or ignore_text.endswith("\n") else "\n"
            atomic_write_text(ignore_path, ignore_text + suffix + "ledger.lock\n")
        records_dir(root, config).mkdir(parents=True, exist_ok=True)
        prd_dir(root, config).mkdir(parents=True, exist_ok=True)
        _refresh_index_unlocked(root, config=config)
        return config


def _write_candidate(
    root: Path,
    config: dict[str, Any],
    path: Path,
    meta: dict[str, Any],
    candidate: Sequence[dict[str, Any]],
    *,
    create_only: bool,
) -> None:
    _ensure_candidate_valid(candidate)
    prd_errors = validate_prd_baselines(root, config, candidate)
    if prd_errors:
        raise LedgerError(
            "候选账本状态会使 PRD 基线失效，拒绝写入；请先审查并归档或移出失效 PRD：\n- "
            + "\n- ".join(prd_errors)
        )
    text = render_record(meta)
    if create_only:
        atomic_create_text(path, text)
    else:
        atomic_write_text(path, text)
    _refresh_index_unlocked(root, config=config, records=candidate)


def create_record(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    root = ensure_root(root)
    config = load_config(root)
    normalized = normalize_payload(payload)
    with ledger_lock(root):
        existing_items = load_records(root, config)
        idea_id = next_id(root, config)
        now = utc_now()
        meta: dict[str, Any] = {
            "schema": SCHEMA_VERSION,
            "id": idea_id,
            "number": int(idea_id.split("-")[1]),
            "title": normalized["title"],
            "status": "proposed",
            "created_at": now,
            "updated_at": now,
            "accepted_at": None,
            "rejected_at": None,
            "rejection_reason": None,
            "approval": None,
            **{key: value for key, value in normalized.items() if key != "title"},
        }
        path = record_path(root, idea_id, config)
        candidate = _candidate_records(existing_items, meta, path)
        _write_candidate(root, config, path, meta, candidate, create_only=True)
        return {"id": idea_id, "path": str(path), "status": "proposed", "meta": meta}


def revise_record(root: Path, idea_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    root = ensure_root(root)
    config = load_config(root)
    idea_id = normalize_id(idea_id)
    normalized = normalize_payload(payload)
    with ledger_lock(root):
        existing_items = load_records(root, config)
        existing = {item["meta"]["id"]: item for item in existing_items}
        item = existing.get(idea_id)
        if not item:
            raise LedgerError(f"记录不存在：{idea_id}")
        meta = copy.deepcopy(item["meta"])
        if meta["status"] != "proposed":
            raise LedgerError(f"只有 proposed 记录可以 revise；{idea_id} 当前为 {meta['status']}。")
        for key in list(OPTIONAL_RECORD_META_FIELDS):
            meta.pop(key, None)
        for key, value in normalized.items():
            meta[key] = value
        meta["updated_at"] = utc_now()
        candidate = _candidate_records(existing_items, meta, item["path"])
        _write_candidate(root, config, item["path"], meta, candidate, create_only=False)
        return {"id": idea_id, "path": str(item["path"]), "status": "proposed", "meta": meta}


def normalize_approval_evidence(evidence: str) -> str:
    # Normalize whitespace and allow only trailing sentence punctuation.
    # Internal punctuation must not turn a different phrase into valid evidence.
    text = re.sub(r"\s+", " ", evidence.strip())
    text = re.sub(r"[，。！？!?,.;；]+$", "", text).rstrip()
    return text.upper()


def evidence_matches(idea_id: str, evidence: str) -> bool:
    normalized = normalize_approval_evidence(evidence)
    target = normalize_id(idea_id)
    return normalized in {f"批准 {target}".upper(), f"APPROVE {target}"}


def accept_record(root: Path, idea_id: str, evidence: str) -> dict[str, Any]:
    root = ensure_root(root)
    config = load_config(root)
    idea_id = normalize_id(idea_id)
    if not evidence_matches(idea_id, evidence):
        raise LedgerError(f"批准语句必须精确为“批准 {idea_id}”或“APPROVE {idea_id}”；“可以/继续/OK”无效。")
    with ledger_lock(root):
        existing_items = load_records(root, config)
        existing = {item["meta"]["id"]: item for item in existing_items}
        item = existing.get(idea_id)
        if not item:
            raise LedgerError(f"记录不存在：{idea_id}")
        meta = copy.deepcopy(item["meta"])
        if meta["status"] != "proposed":
            raise LedgerError(f"只有 proposed 记录可以批准；{idea_id} 当前为 {meta['status']}。")
        approvable, classification = conflict_is_approvable(meta)
        if not approvable:
            raise LedgerError(f"{idea_id} 的冲突处置为 {classification}，不能直接批准；先 revise 补充可执行处置。")
        now = utc_now()
        meta["status"] = "accepted"
        meta["accepted_at"] = now
        meta["updated_at"] = now
        meta["approval"] = {
            "method": "explicit_phrase",
            "recorded_phrase": normalize_approval_evidence(evidence),
            "actor_verified": False,
            "recorded_at": now,
        }
        candidate = _candidate_records(existing_items, meta, item["path"])
        _write_candidate(root, config, item["path"], meta, candidate, create_only=False)
        return {"id": idea_id, "path": str(item["path"]), "status": "accepted", "meta": meta}


def reject_record(root: Path, idea_id: str, reason: str) -> dict[str, Any]:
    root = ensure_root(root)
    config = load_config(root)
    idea_id = normalize_id(idea_id)
    reason = clean_string(reason, "reason", maximum=2000)
    with ledger_lock(root):
        existing_items = load_records(root, config)
        existing = {item["meta"]["id"]: item for item in existing_items}
        item = existing.get(idea_id)
        if not item:
            raise LedgerError(f"记录不存在：{idea_id}")
        meta = copy.deepcopy(item["meta"])
        if meta["status"] != "proposed":
            raise LedgerError(f"只有 proposed 记录可以拒绝；{idea_id} 当前为 {meta['status']}。")
        now = utc_now()
        meta["status"] = "rejected"
        meta["rejected_at"] = now
        meta["rejection_reason"] = reason
        meta["updated_at"] = now
        candidate = _candidate_records(existing_items, meta, item["path"])
        _write_candidate(root, config, item["path"], meta, candidate, create_only=False)
        return {"id": idea_id, "path": str(item["path"]), "status": "rejected", "meta": meta}


def render_index_for_validation(root: Path, config: dict[str, Any], records: Sequence[dict[str, Any]]) -> str:
    reverse = superseded_by_map(records)
    path = index_path(root, config)
    lines = [
        "# Idea Ledger",
        "",
        "> 本索引由 `idea_ledger.py refresh-index` 生成，请勿手工编辑。",
        "",
        "| 编号 | 标题 | 记录状态 | 生效状态 | 范围 | 兼容性/处置 | 替代 | 依赖 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in records:
        meta = item["meta"]
        conflict = normalize_conflict(meta["conflict"], supersedes=meta["supersedes"])
        title = str(meta["title"]).replace("|", "\\|")
        scope = "、".join(meta["scope"]).replace("|", "\\|")
        supersedes = "、".join(meta["supersedes"]) or "—"
        depends = "、".join(
            f"{dep['id']}:{dep['mode']}" for dep in normalize_dependencies(meta["depends_on"])
        ) or "—"
        link = os.path.relpath(item["path"], start=path.parent).replace(os.sep, "/")
        lines.append(
            f"| [{meta['id']}]({link}) | {title} | {meta['status']} | "
            f"{effective_status(meta, reverse)} | {scope} | "
            f"{conflict['compatibility']}/{conflict['disposition']} | {supersedes} | {depends} |"
        )
    if not records:
        lines.append("| — | 尚无记录 | — | — | — | — | — | — |")
    lines.extend(["", f"生成器版本：{VERSION}", ""])
    return "\n".join(lines)


def _refresh_index_unlocked(
    root: Path,
    *,
    config: dict[str, Any] | None = None,
    records: Sequence[dict[str, Any]] | None = None,
) -> Path:
    cfg = config or load_config(root)
    items = list(records) if records is not None else load_records(root, cfg)
    path = index_path(root, cfg)
    atomic_write_text(path, render_index_for_validation(root, cfg, items))
    return path


def refresh_index(root: Path, *, config: dict[str, Any] | None = None) -> Path:
    root = ensure_root(root)
    cfg = config or load_config(root)
    with ledger_lock(root):
        items = load_records(root, cfg)
        graph_errors = validate_graph_records(items)
        if graph_errors:
            raise LedgerError("账本关系图无效，拒绝刷新索引：\n- " + "\n- ".join(graph_errors))
        return _refresh_index_unlocked(root, config=cfg, records=items)


def record_digest(meta: dict[str, Any]) -> str:
    canonical = json.dumps(meta, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def prd_metadata_block(data: dict[str, Any]) -> str:
    return f"{PRD_META_START}\n{json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)}\n{PRD_META_END}"


def parse_prd_metadata(text: str, *, path: Path) -> dict[str, Any] | None:
    if not text.startswith(PRD_META_START):
        return None
    end = text.find(PRD_META_END)
    if end < 0:
        raise LedgerError(f"PRD 元数据块未闭合：{path}")
    raw = text[len(PRD_META_START) : end].strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LedgerError(f"PRD 元数据 JSON 无效：{path}：{exc}") from exc
    if not isinstance(data, dict):
        raise LedgerError(f"PRD 元数据必须是对象：{path}")
    return data


def validate_prd_baselines(root: Path, config: dict[str, Any], records: Sequence[dict[str, Any]]) -> list[str]:
    directory = prd_dir(root, config)
    if not directory.exists():
        return []
    mapping = {item["meta"]["id"]: item for item in records}
    reverse = superseded_by_map(records)
    errors: list[str] = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        match = PRD_FILE_RE.fullmatch(path.name)
        if not match:
            continue
        if path.is_symlink():
            errors.append(f"PRD 不得是符号链接：{path}")
            continue
        try:
            text = read_managed_text(path, "Idea Ledger PRD")
            metadata = parse_prd_metadata(text, path=path)
        except LedgerError as exc:
            errors.append(str(exc))
            continue
        # Legacy v2.0 PRDs had no metadata block; leave them readable without claiming validation.
        if metadata is None:
            continue
        expected_fields = {"schema", "idea_id", "idea_digest", "generated_at"}
        unknown = sorted(set(metadata) - expected_fields)
        missing = sorted(expected_fields - set(metadata))
        if unknown or missing:
            errors.append(
                f"PRD 元数据字段无效：{path}"
                + (f"；未知：{'、'.join(unknown)}" if unknown else "")
                + (f"；缺少：{'、'.join(missing)}" if missing else "")
            )
            continue
        if metadata.get("schema") != 1:
            errors.append(f"PRD 元数据 schema 应为 1：{path}")
        try:
            idea_id = normalize_id(str(metadata.get("idea_id") or ""))
            parse_timestamp(metadata.get("generated_at"), "generated_at")
        except LedgerError as exc:
            errors.append(f"{path}：{exc}")
            continue
        if idea_id != match.group(1):
            errors.append(f"PRD 文件名与 idea_id 不一致：{path}")
        item = mapping.get(idea_id)
        if not item:
            errors.append(f"PRD 基线记录不存在：{path} -> {idea_id}")
            continue
        effective = effective_status(item["meta"], reverse)
        if effective != "accepted":
            errors.append(f"PRD 基线已失效：{path} -> {idea_id}（{effective}）")
        expected_digest = record_digest(item["meta"])
        if metadata.get("idea_digest") != expected_digest:
            errors.append(f"PRD 基线摘要不匹配：{path}；请审查后重新生成或更新基线。")
    return errors


def validate_ledger(root: Path) -> list[str]:
    root = ensure_root(root)
    try:
        config = load_config(root)
    except LedgerError as exc:
        return [str(exc)]
    errors: list[str] = []
    records: list[dict[str, Any]] = []
    try:
        paths = list_record_paths(root, config)
    except LedgerError as exc:
        return [str(exc)]
    seen: set[str] = set()
    last_number = 0
    for path in paths:
        try:
            meta = load_record(path)
        except LedgerError as exc:
            errors.append(str(exc))
            continue
        idea_id = meta["id"]
        number = int(idea_id.split("-")[1])
        if idea_id in seen:
            errors.append(f"编号重复：{idea_id}")
        if number <= last_number:
            errors.append(f"编号顺序异常：{idea_id}")
        seen.add(idea_id)
        last_number = number
        records.append({"path": path, "meta": meta})
    errors.extend(validate_graph_records(records))
    expected = render_index_for_validation(root, config, records)
    path = index_path(root, config)
    if not path.exists():
        errors.append(f"索引不存在：{path}")
    else:
        try:
            actual = read_managed_text(path, "Idea Ledger 索引")
            if actual != expected:
                errors.append("INDEX.md 不是当前记录的确定性派生结果；运行 refresh-index。")
        except (OSError, LedgerError) as exc:
            errors.append(f"无法读取索引：{exc}")
    errors.extend(validate_prd_baselines(root, config, records))
    return list(dict.fromkeys(errors))

__all__ = [name for name in globals() if not name.startswith("__")]
