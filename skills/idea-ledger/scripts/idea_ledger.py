#!/usr/bin/env python3
"""Idea Ledger v2.1 CLI: explicit routing over deterministic core and optional CI checks."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

from idea_ledger_core import (
    STATUSES,
    VERSION,
    LedgerError,
    accept_record,
    build_audit_jsonl,
    build_audit_page,
    build_audit_page_data,
    build_context,
    build_context_data,
    create_prd_template,
    create_record,
    ensure_root,
    init_project,
    list_records_data,
    load_payload,
    load_record,
    normalize_id,
    record_path,
    refresh_index,
    reject_record,
    render_record,
    revise_record,
    status_summary,
    validate_ledger,
)
from idea_ledger_ci import ci_check


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def emit(data: Any, *, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(json_safe(data), ensure_ascii=False, indent=2, sort_keys=True))
    elif isinstance(data, str):
        print(data)
    elif isinstance(data, Path):
        print(str(data))
    else:
        print(json.dumps(json_safe(data), ensure_ascii=False, indent=2, sort_keys=True))


def add_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", default=".", help="项目根目录，默认当前目录")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出（适用时）")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Idea Ledger v2.1：显式、项目内、可审计的产品决策记录")
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="显式初始化项目内账本；不修改 Git")
    add_root(p)

    p = sub.add_parser("new", help="从 JSON 创建 proposed 记录")
    add_root(p)
    p.add_argument("--input", required=True, help="JSON 文件路径，或 - 从 stdin 读取")

    p = sub.add_parser("revise", help="替换 proposed 记录内容")
    add_root(p)
    p.add_argument("--id", required=True)
    p.add_argument("--input", required=True, help="JSON 文件路径，或 - 从 stdin 读取")

    p = sub.add_parser("accept", help="用精确批准语句接受 proposed 记录")
    add_root(p)
    p.add_argument("--id", required=True)
    p.add_argument("--evidence", required=True, help="精确语句：批准 IDEA-0001 / APPROVE IDEA-0001")

    p = sub.add_parser("reject", help="拒绝 proposed 记录")
    add_root(p)
    p.add_argument("--id", required=True)
    p.add_argument("--reason", required=True)

    p = sub.add_parser("show", help="验证并输出单条记录")
    add_root(p)
    p.add_argument("--id", required=True)

    p = sub.add_parser("list", help="列出记录元数据")
    add_root(p)
    p.add_argument("--status", choices=sorted(STATUSES))

    p = sub.add_parser("status", help="显示账本状态")
    add_root(p)

    p = sub.add_parser("context", help="按相关性生成有界上下文；只输出候选，不宣称冲突结论")
    add_root(p)
    p.add_argument("--query", default="")
    p.add_argument("--limit", type=int)
    p.add_argument("--max-chars", type=int)
    p.add_argument("--include-proposed", action="store_true")

    p = sub.add_parser("audit", help="分页输出完整审计数据")
    add_root(p)
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--page-size", type=int, default=25)
    p.add_argument("--format", choices=("markdown", "json", "jsonl"), default="markdown")

    p = sub.add_parser("validate", help="验证 schema、全局关系图、终态、索引和 PRD 基线")
    add_root(p)

    p = sub.add_parser("refresh-index", help="在锁内重建确定性索引")
    add_root(p)

    p = sub.add_parser("prd-template", help="为生效 accepted 决策原子创建 PRD 骨架；不覆盖")
    add_root(p)
    p.add_argument("--id", required=True)

    p = sub.add_parser("ci-check", help="可选严格模式：验证账本及 Git 基准/分支历史")
    add_root(p)
    p.add_argument("--base-ref", help="例如 origin/main；省略时只做结构校验")
    p.add_argument("--require-trailer", action="store_true", help="要求代码提交含 footer trailer：Idea: IDEA-0001")

    return parser


def render_list(items: list[dict[str, Any]]) -> str:
    if not items:
        return "尚无匹配记录。"
    lines = ["编号\t记录状态\t生效状态\t兼容性/处置\t标题"]
    for item in items:
        lines.append(
            f"{item['id']}\t{item['status']}\t{item['effective_status']}\t"
            f"{item['compatibility']}/{item['disposition']}\t{item['title']}"
        )
    return "\n".join(lines)


def render_status(data: dict[str, Any]) -> str:
    counts = data["counts"]
    effective = data["effective_counts"]
    return "\n".join(
        [
            f"Idea Ledger {data['version']}（schema {data['schema']}）",
            f"记录总数：{data['records']}；下一编号：{data['next_id']}",
            "存储状态：" + "，".join(f"{key}={value}" for key, value in counts.items()),
            "生效状态：" + ("，".join(f"{key}={value}" for key, value in sorted(effective.items())) or "无"),
            f"关系图：{'有效' if data['graph_valid'] else '无效'}",
        ]
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = ensure_root(args.root)
        if args.command == "init":
            config = init_project(root)
            emit({"initialized": True, "root": str(root), "config": config}, as_json=args.json)
        elif args.command == "new":
            emit(create_record(root, load_payload(args.input)), as_json=args.json)
        elif args.command == "revise":
            emit(revise_record(root, args.id, load_payload(args.input)), as_json=args.json)
        elif args.command == "accept":
            emit(accept_record(root, args.id, args.evidence), as_json=args.json)
        elif args.command == "reject":
            emit(reject_record(root, args.id, args.reason), as_json=args.json)
        elif args.command == "show":
            path = record_path(root, args.id)
            if not path.exists():
                raise LedgerError(f"记录不存在：{normalize_id(args.id)}")
            meta = load_record(path)
            emit(meta if args.json else render_record(meta), as_json=args.json)
        elif args.command == "list":
            items = list_records_data(root, args.status)
            emit(items if args.json else render_list(items), as_json=args.json)
        elif args.command == "status":
            data = status_summary(root)
            emit(data if args.json else render_status(data), as_json=args.json)
        elif args.command == "context":
            if args.json:
                emit(
                    build_context_data(
                        root,
                        args.query,
                        limit=args.limit,
                        max_chars=args.max_chars,
                        include_proposed=args.include_proposed,
                    ),
                    as_json=True,
                )
            else:
                print(
                    build_context(
                        root,
                        args.query,
                        limit=args.limit,
                        max_chars=args.max_chars,
                        include_proposed=args.include_proposed,
                    ),
                    end="",
                )
        elif args.command == "audit":
            output_format = "json" if args.json else args.format
            if output_format == "json":
                emit(build_audit_page_data(root, args.page, args.page_size), as_json=True)
            elif output_format == "jsonl":
                print(build_audit_jsonl(root, args.page, args.page_size), end="")
            else:
                print(build_audit_page(root, args.page, args.page_size), end="")
        elif args.command == "validate":
            errors = validate_ledger(root)
            if errors:
                raise LedgerError("账本校验失败：\n- " + "\n- ".join(errors))
            emit({"valid": True, "root": str(root)}, as_json=args.json)
        elif args.command == "refresh-index":
            path = refresh_index(root)
            emit({"path": str(path), "refreshed": True} if args.json else path, as_json=args.json)
        elif args.command == "prd-template":
            path = create_prd_template(root, args.id)
            emit({"path": str(path), "created": True} if args.json else path, as_json=args.json)
        elif args.command == "ci-check":
            errors = ci_check(root, base_ref=args.base_ref, require_trailer=args.require_trailer)
            if errors:
                raise LedgerError("CI 校验失败：\n- " + "\n- ".join(errors))
            emit(
                {"valid": True, "base_ref": args.base_ref, "require_trailer": args.require_trailer},
                as_json=args.json,
            )
        else:  # pragma: no cover
            raise LedgerError(f"未知命令：{args.command}")
        return 0
    except (LedgerError, OSError, subprocess.SubprocessError, TypeError, ValueError) as exc:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        else:
            print(f"错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
