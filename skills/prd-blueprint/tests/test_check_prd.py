"""离线结构回归，不冒充宿主触发或语义测试。"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_prd import START, END, validate_documents

OUTLINE = """# 示例总纲

## 一句话目的
让用户只读查看自己的材料。

## 功能清单
- 功能01：展示材料，不允许编辑。
- 功能02：保留可追溯记录。

## 验收标准
- 验收01 → 功能01：打开材料后能查看，编辑操作不可用。
- 验收02 → 功能02：重新打开后记录仍存在。
"""
DETAIL = """
## 详细功能
### 功能01 展示
只读查看材料。
### 功能02 记录
重新打开后保留记录。
## 详细验收
### 验收01 只读验证
打开并检查只读状态。
### 验收02 重开验证
关闭再打开并比对记录。
"""


def full(outline=OUTLINE, detail=DETAIL):
    return f"# 详细需求\n\n{START}\n{outline.rstrip()}\n{END}\n{detail}"


class StructureTests(unittest.TestCase):
    def test_valid_documents(self):
        self.assertEqual(validate_documents(OUTLINE, full(), OUTLINE), [])

    def test_three_headings_only(self):
        changed = OUTLINE + "\n## 额外章节\n不该存在。\n"
        self.assertTrue(validate_documents(changed, full(changed)))

    def test_heading_order(self):
        changed = OUTLINE.replace("## 一句话目的", "## 功能清单", 1)
        self.assertTrue(validate_documents(changed, full(changed)))

    def test_duplicate_feature(self):
        changed = OUTLINE.replace("- 功能02：", "- 功能01：")
        self.assertTrue(any("编号重复" in x for x in validate_documents(changed, full(changed))))

    def test_duplicate_acceptance(self):
        changed = OUTLINE.replace("- 验收02", "- 验收01")
        self.assertTrue(any("编号重复" in x for x in validate_documents(changed, full(changed))))

    def test_unknown_feature_reference(self):
        changed = OUTLINE.replace("验收02 → 功能02", "验收02 → 功能99")
        self.assertTrue(any("不存在的功能" in x for x in validate_documents(changed, full(changed))))

    def test_feature_without_acceptance(self):
        changed = OUTLINE.replace("- 功能02：保留可追溯记录。", "- 功能02：保留可追溯记录。\n- 功能03：导出。")
        self.assertTrue(any("缺少对应验收" in x for x in validate_documents(changed, full(changed))))

    def test_missing_detail(self):
        changed = DETAIL.replace("### 功能02 记录\n重新打开后保留记录。\n", "")
        self.assertTrue(any("缺少详细功能章节" in x for x in validate_documents(OUTLINE, full(detail=changed))))

    def test_extra_detail(self):
        changed = DETAIL + "\n### 功能99 未约定功能\n自动公开发布。\n"
        self.assertTrue(any("总纲没有的功能编号" in x for x in validate_documents(OUTLINE, full(detail=changed))))

    def test_missing_acceptance_detail(self):
        changed = DETAIL.replace("### 验收02 重开验证\n关闭再打开并比对记录。\n", "")
        self.assertTrue(any("缺少详细验收章节" in x for x in validate_documents(OUTLINE, full(detail=changed))))

    def test_mirror_mismatch(self):
        changed = full().replace("让用户只读查看自己的材料。", "让用户编辑材料。")
        self.assertTrue(any("镜像与独立总纲不一致" in x for x in validate_documents(OUTLINE, changed)))

    def test_chat_mismatch(self):
        self.assertTrue(any("待发送" in x for x in validate_documents(OUTLINE, full(), OUTLINE.replace("只读", "编辑"))))

    def test_missing_marker(self):
        self.assertTrue(any("镜像标记" in x for x in validate_documents(OUTLINE, full().replace(END, ""))))

    def test_duplicate_marker(self):
        self.assertTrue(any("镜像标记" in x for x in validate_documents(OUTLINE, full() + END)))

    def test_crlf_and_final_newline(self):
        self.assertEqual(validate_documents(OUTLINE.replace("\n", "\r\n"), full(), OUTLINE.rstrip("\n")), [])

    def test_multiple_feature_acceptance(self):
        changed = OUTLINE.replace("验收02 → 功能02", "验收02 → 功能01、功能02")
        self.assertEqual(validate_documents(changed, full(changed), changed), [])

    def test_empty_goal(self):
        changed = OUTLINE.replace("让用户只读查看自己的材料。", "")
        self.assertTrue(any("目的不能为空" in x for x in validate_documents(changed, full(changed))))

    def test_malformed_numbered_row(self):
        changed = OUTLINE.replace("- 功能02：", "- 无编号条目：")
        self.assertTrue(any("条目格式" in x for x in validate_documents(changed, full(changed))))

    def test_no_level_three_detail_in_outline(self):
        changed = OUTLINE.replace("## 验收标准", "### 技术细节\n额外细节。\n\n## 验收标准")
        self.assertTrue(any("三级细节" in x for x in validate_documents(changed, full(changed))))

    def test_cli_failure_exit_codes(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "check_prd.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = root / "outline.md", root / "prd.md"
            a.write_text(OUTLINE, encoding="utf-8")
            b.write_text(full().replace(END, ""), encoding="utf-8")
            cmd = [sys.executable, str(script), "--outline", str(a), "--prd", str(b)]
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 1)
            a.unlink()
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 2)


if __name__ == "__main__":
    unittest.main()
