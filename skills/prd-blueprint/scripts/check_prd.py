#!/usr/bin/env python3
"""只读检查总纲、需求正文和待发送总纲；不作语义或用户确认判断。"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

HEADINGS = ("一句话目的", "功能清单", "验收标准")
START = "<!-- 总纲开始 -->"
END = "<!-- 总纲结束 -->"
FEATURE = re.compile(r"^- (功能\d{2,})[：:]\s*(.+)$", re.MULTILINE)
ACCEPTANCE = re.compile(
    r"^- (验收\d{2,})\s*→\s*(功能\d{2,}(?:\s*[、,，]\s*功能\d{2,})*)[：:]\s*(.+)$",
    re.MULTILINE,
)


def canonical(text: str) -> str:
    """仅统一系统换行和最终换行；正文中的空格及标点必须一致。"""
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")


def sections(text: str, level: int) -> list[tuple[str, str]]:
    pattern = re.compile(r"^" + "#" * level + r" (.+)$", re.MULTILINE)
    found = list(pattern.finditer(text))
    return [
        (match.group(1).strip(), text[match.end():found[i + 1].start() if i + 1 < len(found) else len(text)].strip())
        for i, match in enumerate(found)
    ]


def repeated(ids: list[str]) -> list[str]:
    return sorted(key for key, count in Counter(ids).items() if count > 1)


def validate_documents(outline: str, prd: str, chat: str | None = None) -> list[str]:
    """返回结构错误；空列表不代表语义正确或宿主已经触发。"""
    errors: list[str] = []
    outline, prd = canonical(outline), canonical(prd)
    outline_sections = sections(outline, 2)
    if tuple(name for name, _ in outline_sections) != HEADINGS:
        errors.append("总纲必须且只能按顺序包含：一句话目的、功能清单、验收标准。")
        return errors
    data = dict(outline_sections)
    if not data[HEADINGS[0]]:
        errors.append("一句话目的不能为空。")
    if len(re.split(r"\n\s*\n", data[HEADINGS[0]])) > 1:
        errors.append("一句话目的须使用一个段落，不要在这里堆叠说明。")
    if re.search(r"^###\s+", outline, re.MULTILINE):
        errors.append("总纲不得增加三级细节章节；详细内容应放进需求正文。")

    features = FEATURE.findall(data[HEADINGS[1]])
    acceptances = ACCEPTANCE.findall(data[HEADINGS[2]])
    feature_ids = [row[0] for row in features]
    acceptance_ids = [row[0] for row in acceptances]
    if not features:
        errors.append("没有找到有效功能条目，格式应为：- 功能01：内容。")
    if not acceptances:
        errors.append("没有找到有效验收条目，格式应为：- 验收01 → 功能01：内容。")
    for label, ids in (("功能", feature_ids), ("验收", acceptance_ids)):
        if dup := repeated(ids):
            errors.append(f"总纲{label}编号重复：{'、'.join(dup)}。")
    for heading, pattern in ((HEADINGS[1], FEATURE), (HEADINGS[2], ACCEPTANCE)):
        for line in data[heading].splitlines():
            if re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", line) and not pattern.fullmatch(line):
                errors.append(f"{heading}条目格式不正确：{line}")

    covered: set[str] = set()
    known_features, known_acceptances = set(feature_ids), set(acceptance_ids)
    for aid, refs, _ in acceptances:
        targets = set(re.findall(r"功能\d{2,}", refs))
        covered.update(targets)
        if missing := targets - known_features:
            errors.append(f"{aid}引用了不存在的功能：{'、'.join(sorted(missing))}。")
    if missing := known_features - covered:
        errors.append(f"功能缺少对应验收：{'、'.join(sorted(missing))}。")

    body = prd
    if prd.count(START) != 1 or prd.count(END) != 1 or prd.find(START) > prd.find(END):
        errors.append("需求正文必须包含且仅包含一对顺序正确的总纲镜像标记。")
    else:
        left, rest = prd.split(START, 1)
        mirror, right = rest.split(END, 1)
        # 允许标记相邻的空行；不改写任何实际总纲正文。
        mirror = mirror.strip("\n")
        if canonical(mirror) != outline:
            errors.append("需求正文中的总纲镜像与独立总纲不一致。")
        body = left + right

    detail_sections = sections(body, 3)
    for prefix, expected in (("功能", known_features), ("验收", known_acceptances)):
        detailed: list[str] = []
        for title, content in detail_sections:
            match = re.match(r"^(" + prefix + r"\d{2,})(?:\s|$)", title)
            if match:
                detailed.append(match.group(1))
                if not content:
                    errors.append(f"{match.group(1)}的详细章节为空。")
        if dup := repeated(detailed):
            errors.append(f"详细{prefix}编号重复：{'、'.join(dup)}。")
        actual = set(detailed)
        if missing := expected - actual:
            errors.append(f"缺少详细{prefix}章节：{'、'.join(sorted(missing))}。")
        if extra := actual - expected:
            errors.append(f"正文含总纲没有的{prefix}编号：{'、'.join(sorted(extra))}。")

    if chat is not None and canonical(chat) != outline:
        errors.append("待发送的对话总纲与独立总纲不一致。")
    return errors


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outline", required=True, type=Path, help="独立总纲路径")
    parser.add_argument("--prd", required=True, type=Path, help="完整需求文档路径")
    parser.add_argument("--chat", type=Path, help="待发送总纲文本路径；不是整个最终回答")
    args = parser.parse_args()
    try:
        errors = validate_documents(read_text(args.outline), read_text(args.prd), read_text(args.chat) if args.chat else None)
    except (OSError, UnicodeError) as exc:
        print(f"读取失败：{exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"不通过：{error}")
        return 1
    print("通过：规定章节、功能与验收编号、详细章节覆盖和总纲镜像一致。")
    print("通过：待发送总纲文本与文件一致。" if args.chat else "未检查：未提供待发送总纲文本。")
    print("范围限制：只验证结构；未证明语义忠实、用户确认、宿主触发或目标产品验收通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
