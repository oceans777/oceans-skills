from _support import *

class CiPolicyTests(CiCase):
    def test_base_accepted_record_mutation_is_detected(self) -> None:
        idea_id = self.accepted_and_committed()
        self.git("tag", "base")
        self.rewrite_terminal(idea_id, "goal", "Rewritten accepted goal.")
        errors = LEDGER_CI.ci_check(self.root, base_ref="base", require_trailer=False)
        self.assertTrue(any("终态记录不可原地修改" in error for error in errors))

    def test_base_rejected_record_mutation_is_detected(self) -> None:
        idea_id = str(self.new(self.payload("Rejected"))["id"])
        self.reject(idea_id)
        self.commit_all("idea: reject")
        self.git("tag", "base")
        self.rewrite_terminal(idea_id, "goal", "Rewritten rejected goal.")
        errors = LEDGER_CI.ci_check(self.root, base_ref="base", require_trailer=False)
        self.assertTrue(any("终态记录不可原地修改" in error for error in errors))

    def test_branch_new_terminal_then_modified_is_detected(self) -> None:
        self.git("tag", "base")
        idea_id = self.accepted_and_committed("Branch decision")
        self.rewrite_terminal(idea_id, "goal", "Changed after acceptance.")
        self.commit_all("rewrite branch accepted record")
        errors = LEDGER_CI.ci_check(self.root, base_ref="base", require_trailer=False)
        self.assertTrue(any("终态记录不可原地修改" in error for error in errors))

    def test_terminal_modified_then_restored_still_fails_history(self) -> None:
        idea_id = self.accepted_and_committed()
        self.git("tag", "base")
        path = LEDGER.record_path(self.root, idea_id)
        original = path.read_text(encoding="utf-8")
        self.rewrite_terminal(idea_id, "goal", "Temporary illegal rewrite.")
        self.commit_all("temporary rewrite")
        path.write_text(original, encoding="utf-8", newline="\n")
        LEDGER.refresh_index(self.root)
        self.commit_all("restore bytes")
        errors = LEDGER_CI.ci_check(self.root, base_ref="base", require_trailer=False)
        self.assertTrue(any("终态记录不可原地修改" in error for error in errors))

    def test_subject_line_is_not_accepted_as_footer_trailer(self) -> None:
        idea_id = self.accepted_and_committed()
        self.git("tag", "base")
        (self.root / "app.py").write_text("print('x')\n", encoding="utf-8")
        self.commit_all(f"Idea: {idea_id}")
        errors = LEDGER_CI.ci_check(self.root, base_ref="base", require_trailer=True)
        self.assertTrue(any("缺少 footer trailer" in error for error in errors))

    def test_valid_footer_trailer_passes(self) -> None:
        idea_id = self.accepted_and_committed()
        self.git("tag", "base")
        (self.root / "app.py").write_text("print('x')\n", encoding="utf-8")
        self.commit_all("feat: app", f"Idea: {idea_id}")
        self.assertEqual([], LEDGER_CI.ci_check(self.root, base_ref="base", require_trailer=True))

    def test_dot_directory_exemption_needs_no_trailer(self) -> None:
        self.git("tag", "base")
        workflow = self.root / ".github/workflows/check.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("name: check\n", encoding="utf-8")
        self.commit_all("chore: workflow")
        self.assertEqual([], LEDGER_CI.ci_check(self.root, base_ref="base", require_trailer=True))

    def test_policy_self_modification_is_rejected(self) -> None:
        self.git("tag", "base")
        path = self.root / ".idea-ledger/config.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        config["policy_exempt_prefixes"].append("src/")
        path.write_text(json.dumps(config), encoding="utf-8")
        self.commit_all("weaken policy")
        errors = LEDGER_CI.ci_check(self.root, base_ref="base", require_trailer=False)
        self.assertTrue(any("自改规则" in error for error in errors))

    def test_trailer_mode_rejects_merge_commits(self) -> None:
        idea_id = self.accepted_and_committed()
        self.git("tag", "base")
        self.git("checkout", "-q", "-b", "side")
        workflow = self.root / ".github/side.yml"
        workflow.parent.mkdir(exist_ok=True)
        workflow.write_text("name: side\n", encoding="utf-8")
        self.commit_all("chore: side")
        self.git("checkout", "-q", "-b", "work", "base")
        (self.root / "app.py").write_text("print('x')\n", encoding="utf-8")
        self.commit_all("feat: app", f"Idea: {idea_id}")
        self.git("merge", "--no-ff", "-q", "side", "-m", "merge side")
        errors = LEDGER_CI.ci_check(self.root, base_ref="base", require_trailer=True)
        self.assertTrue(any("线性提交历史" in error for error in errors))

    def test_trailer_cannot_reference_decision_accepted_only_later(self) -> None:
        self.git("tag", "base")
        proposed = str(self.new(self.payload("Future"))["id"])
        self.commit_all("idea: propose future")
        (self.root / "app.py").write_text("print('x')\n", encoding="utf-8")
        self.commit_all("feat: app", f"Idea: {proposed}")
        self.accept(proposed)
        self.commit_all("idea: accept future")
        errors = LEDGER_CI.ci_check(self.root, base_ref="base", require_trailer=True)
        self.assertTrue(any("当时不存在或非生效 accepted" in error for error in errors))
