from _support import *

class RetrievalAuditAndPrdTests(LedgerCase):
    def setUp(self) -> None:
        super().setUp()
        self.init()

    def test_context_budget_includes_long_query(self) -> None:
        idea_id = str(self.new(self.payload())["id"])
        self.accept(idea_id)
        output = LEDGER.build_context(self.root, "查询" * 5000, max_chars=500)
        self.assertLessEqual(len(output), 500)
        self.assertIn("截断", output)

    def test_context_emits_minimal_record_when_full_record_is_too_large(self) -> None:
        long_decision = "D" * 3500
        idea_id = str(self.new(self.payload(long_decision=long_decision))["id"])
        self.accept(idea_id)
        output = LEDGER.build_context(self.root, idea_id, max_chars=650)
        self.assertLessEqual(len(output), 650)
        self.assertIn(idea_id, output)
        self.assertIn("最小摘要", output)

    def test_search_includes_ids_relationships_and_notes(self) -> None:
        first = str(self.new(self.payload("First", notes=["rare-orchid-token"]))["id"])
        self.accept(first)
        output = LEDGER.build_context(self.root, "rare-orchid-token", max_chars=2000)
        self.assertIn(first, output)
        output_by_id = LEDGER.build_context(self.root, first, max_chars=2000)
        self.assertIn(first, output_by_id)

    def test_audit_contains_complete_fields_and_jsonl(self) -> None:
        idea_id = str(self.new(self.payload())["id"])
        self.accept(idea_id)
        data = LEDGER.build_audit_page_data(self.root, 1, 25)
        record = data["records"][0]
        self.assertIn("approval", record["meta"])
        self.assertIn("constraints", record["meta"])
        self.assertIn("record_digest", record)
        jsonl = LEDGER.build_audit_jsonl(self.root, 1, 25)
        self.assertIn('"type": "page"', jsonl)
        self.assertIn('"type": "record"', jsonl)

    def test_show_validates_body_before_output(self) -> None:
        idea_id = str(self.new(self.payload())["id"])
        path = LEDGER.record_path(self.root, idea_id)
        path.write_text(path.read_text(encoding="utf-8") + "manual drift\n", encoding="utf-8")
        result = self.cli("show", "--id", idea_id, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("正文与机器元数据不一致", result.stderr)

    def test_json_path_commands_are_serializable(self) -> None:
        idea_id = str(self.new(self.payload())["id"])
        self.accept(idea_id)
        refresh = self.cli("refresh-index", "--json")
        self.assertTrue(json.loads(refresh.stdout)["refreshed"])
        prd = self.cli("prd-template", "--id", idea_id, "--json")
        self.assertTrue(json.loads(prd.stdout)["created"])

    def test_prd_is_atomic_no_overwrite_and_has_digest(self) -> None:
        idea_id = str(self.new(self.payload())["id"])
        self.accept(idea_id)
        path = LEDGER.create_prd_template(self.root, idea_id)
        original = path.read_text(encoding="utf-8")
        self.assertIn("idea_digest", original)
        with self.assertRaisesRegex(LEDGER.LedgerError, "拒绝覆盖"):
            LEDGER.create_prd_template(self.root, idea_id)
        self.assertEqual(original, path.read_text(encoding="utf-8"))
        self.assertEqual([], LEDGER.validate_ledger(self.root))

    def test_prd_staleness_is_blocked_before_supersession_write(self) -> None:
        old = str(self.new(self.payload("Old"))["id"])
        self.accept(old)
        LEDGER.create_prd_template(self.root, old)
        conflict = self.conflict(
            "incompatible",
            reviewed=[old],
            conflicts=[old],
            disposition="supersede",
            mitigation="Replace old.",
        )
        new = str(self.new(self.payload("New", conflict=conflict, supersedes=[old]))["id"])
        with self.assertRaisesRegex(LEDGER.LedgerError, "PRD 基线"):
            self.accept(new)
        self.assertEqual("proposed", LEDGER.load_record(LEDGER.record_path(self.root, new))["status"])
        self.assertEqual([], LEDGER.validate_ledger(self.root))

    def test_custom_index_links_are_relative(self) -> None:
        config_path = self.root / ".idea-ledger/config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["index_file"] = "governance/DECISIONS.md"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        idea_id = str(self.new(self.payload())["id"])
        index = (self.root / "governance/DECISIONS.md").read_text(encoding="utf-8")
        self.assertIn(f"../docs/idea-ledger/records/{idea_id}.md", index)

    def test_audit_page_clamps(self) -> None:
        self.new(self.payload())
        data = LEDGER.build_audit_page_data(self.root, 999, 25)
        self.assertEqual(1, data["page"])
        self.assertEqual(1, data["last_record"])
