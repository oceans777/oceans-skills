"""技能文档契约回归；不执行目标网站，也不证明模型遵循指令。"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def contract_errors(root):
    errors = []
    main = (root / 'SKILL.md').read_text(encoding='utf-8')
    checks = (root / 'references/checks.md').read_text(encoding='utf-8')
    maintenance = (root / 'references/experience-maintenance.md').read_text(encoding='utf-8')
    if not main.startswith('---\nname: audit-ai-generation-site\ndescription:'):
        errors.append('metadata')
    for mode in ('inspect-only', 'authorized-repair', 'update-experience'):
        if mode not in main:
            errors.append('mode:' + mode)
    for link in re.findall(r'\]\((references/[^)]+)\)', main):
        if not (root / link).is_file():
            errors.append('missing-reference:' + link)
    ids = re.findall(r'^## ([A-Z]+-\d{2}) ', checks, re.M)
    if not ids or len(ids) != len(set(ids)):
        errors.append('check-ids')
    for section in re.split(r'^## ', checks, flags=re.M)[1:]:
        for field in ('适用：', '来源/证据状态：', '症状：', '检查：', '修复方向：', '回归：'):
            if field not in section:
                errors.append('missing-field:' + field)
    for boundary in ('inspect-only（默认）', 'not-verified', 'mock', '不能声称真实付款', '真实收费请求'):
        if boundary not in main:
            errors.append('boundary:' + boundary)
    for field in ('evidence_status:', 'applicability:', 'dedup_key:', 'supersedes:', 'review_state:', 'candidate 与 active'):
        if field not in maintenance:
            errors.append('maintenance:' + field)
    return errors


class ContractTests(unittest.TestCase):
    def test_package_contract(self):
        self.assertEqual(contract_errors(ROOT), [])

    def test_unique_ids(self):
        ids = re.findall(r'^## ([A-Z]+-\d{2}) ', (ROOT / 'references/checks.md').read_text(encoding='utf-8'), re.M)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({'PAY-01', 'CREDIT-01', 'JOB-01', 'JOB-02', 'PRIVACY-01'} <= set(ids))

    def test_source_attribution(self):
        source = (ROOT / 'references/source-case.md').read_text(encoding='utf-8')
        self.assertIn('https://x.com/xuxuanzhou/status/2112129349071831259', source)
        self.assertIn('case-claim', source)
        self.assertIn('不是已验证的因果分析', source)

    def test_no_permanent_installation_ban(self):
        maintenance = (ROOT / 'references/experience-maintenance.md').read_text(encoding='utf-8')
        self.assertIn('未来安装由用户另行指定目标和范围', maintenance)
        self.assertNotIn('也不应发布到个人 ChatGPT Skill 接口', maintenance)

    def test_scenarios_are_explicitly_unexecuted(self):
        cases = json.loads((ROOT / 'tests/scenarios.json').read_text(encoding='utf-8'))
        self.assertGreaterEqual(len(cases), 5)
        self.assertEqual(len({c['id'] for c in cases}), len(cases))
        for case in cases:
            self.assertEqual(case['execution_status'], 'not-run')
            self.assertTrue(case['prompt'] and case['expected'] and case['must_not'])

    def test_new_well_formed_check_is_accepted(self):
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'skill'
            shutil.copytree(ROOT, target)
            file = target / 'references/checks.md'
            text = file.read_text(encoding='utf-8')
            example = re.split(r'^## ', text, flags=re.M)[1]
            file.write_text(text + '\n## ' + example.replace('PAY-01', 'NEW-01', 1), encoding='utf-8')
            self.assertEqual(contract_errors(target), [])

    def test_mutation_duplicate_check_rejected(self):
        self.check_mutation('references/checks.md', '## PAY-01 ', '## JOB-01 ', 'check-ids')

    def test_mutation_missing_evidence_boundary_rejected(self):
        self.check_mutation('SKILL.md', '不能声称真实付款', '可以声称真实付款', 'boundary:不能声称真实付款')

    def test_mutation_missing_review_state_rejected(self):
        self.check_mutation('references/experience-maintenance.md', 'review_state:', 'draft_state:', 'maintenance:review_state:')

    def check_mutation(self, path, before, after, expected):
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'skill'
            shutil.copytree(ROOT, target)
            file = target / path
            text = file.read_text(encoding='utf-8')
            self.assertIn(before, text)
            file.write_text(text.replace(before, after, 1), encoding='utf-8')
            self.assertIn(expected, contract_errors(target))


if __name__ == '__main__':
    unittest.main()
