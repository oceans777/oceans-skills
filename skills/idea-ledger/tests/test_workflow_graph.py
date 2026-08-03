from _support import *

class WorkflowAndGraphTests(LedgerCase):
    def setUp(self) -> None:
        super().setUp()
        self.init()

    def test_generic_approval_is_rejected_and_exact_phrase_remains_valid(self) -> None:
        idea_id = str(self.new(self.payload())["id"])
        with self.assertRaisesRegex(LEDGER.LedgerError, "natural_language_intent"):
            LEDGER.accept_record(self.root, idea_id, "可以")
        with self.assertRaisesRegex(LEDGER.LedgerError, "模糊"):
            LEDGER.accept_record(
                self.root,
                idea_id,
                "可以",
                approval_mode="natural_language_intent",
            )
        accepted = LEDGER.accept_record(self.root, idea_id, f"批准  {idea_id}。")
        self.assertEqual("accepted", accepted["status"])

    def test_unambiguous_natural_language_approval_preserves_raw_message(self) -> None:
        idea_id = str(self.new(self.payload())["id"])
        message = "就按刚才这个方案执行"
        accepted = LEDGER.accept_record(
            self.root,
            idea_id,
            message,
            approval_mode="natural_language_intent",
        )
        approval = accepted["meta"]["approval"]
        self.assertEqual("natural_language_intent", approval["method"])
        self.assertEqual(message, approval["recorded_message"])
        self.assertEqual(idea_id, approval["resolved_record"])
        self.assertEqual([], LEDGER.validate_ledger(self.root))

    def test_unnamed_natural_language_approval_requires_single_proposal(self) -> None:
        first = str(self.new(self.payload("First"))["id"])
        second = str(self.new(self.payload("Second"))["id"])
        with self.assertRaisesRegex(LEDGER.LedgerError, "消歧"):
            LEDGER.accept_record(
                self.root,
                first,
                "就按刚才这个方案执行",
                approval_mode="natural_language_intent",
            )
        with self.assertRaisesRegex(LEDGER.LedgerError, "目标.*不一致"):
            LEDGER.accept_record(
                self.root,
                first,
                f"就按 {second} 这个方案执行",
                approval_mode="natural_language_intent",
            )
        with self.assertRaisesRegex(LEDGER.LedgerError, "模糊"):
            LEDGER.accept_record(
                self.root,
                first,
                f"同意 {first}",
                approval_mode="natural_language_intent",
            )
        accepted = LEDGER.accept_record(
            self.root,
            first,
            f"就按 {first} 这个方案执行",
            approval_mode="natural_language_intent",
        )
        self.assertEqual("accepted", accepted["status"])
        self.assertEqual("proposed", LEDGER.load_record(LEDGER.record_path(self.root, second))["status"])

    def test_new_and_revised_proposals_require_acceptance_criteria(self) -> None:
        payload = self.payload()
        payload["acceptance_criteria"] = []
        with self.assertRaisesRegex(LEDGER.LedgerError, "至少需要一项"):
            self.new(payload)

        idea_id = str(self.new(self.payload("Existing"))["id"])
        revised = self.payload("Existing revised")
        revised["acceptance_criteria"] = []
        with self.assertRaisesRegex(LEDGER.LedgerError, "至少需要一项"):
            LEDGER.revise_record(self.root, idea_id, revised)

    def test_new_and_revised_proposals_require_a_governing_charter(self) -> None:
        payload = self.payload()
        payload.pop("charter")
        with self.assertRaisesRegex(LEDGER.LedgerError, "总纲领"):
            self.new(payload)

        idea_id = str(self.new(self.payload("Existing"))["id"])
        revised = self.payload("Existing revised")
        revised.pop("charter")
        with self.assertRaisesRegex(LEDGER.LedgerError, "总纲领"):
            LEDGER.revise_record(self.root, idea_id, revised)

    def test_charter_is_compact_and_precedes_generated_detail(self) -> None:
        payload = self.payload()
        payload["charter"]["scope"] = [f"scope-{index}" for index in range(6)]
        with self.assertRaisesRegex(LEDGER.LedgerError, "最多 5 项"):
            self.new(payload)

        payload = self.payload()
        payload["charter"]["goal"] = "line one\nline two"
        result = self.new(payload)
        text = LEDGER.record_path(self.root, str(result["id"])).read_text(encoding="utf-8")
        self.assertLess(text.index("## 总纲领（管理员与操作者先看）"), text.index("## 具体方案"))
        self.assertLess(text.index("## 具体方案"), text.index("## 验收标准"))

    def test_legacy_record_without_charter_remains_valid(self) -> None:
        idea_id = str(self.new(self.payload())["id"])
        path = LEDGER.record_path(self.root, idea_id)
        meta = LEDGER.load_record(path)
        meta.pop("charter")
        path.write_text(LEDGER.render_record(meta), encoding="utf-8", newline="\n")
        LEDGER.refresh_index(self.root)
        self.assertEqual([], LEDGER.validate_ledger(self.root))

    def test_legacy_proposal_without_acceptance_criteria_cannot_be_accepted(self) -> None:
        idea_id = str(self.new(self.payload())["id"])
        path = LEDGER.record_path(self.root, idea_id)
        meta = LEDGER.load_record(path)
        meta["acceptance_criteria"] = []
        path.write_text(LEDGER.render_record(meta), encoding="utf-8", newline="\n")
        LEDGER.refresh_index(self.root)
        with self.assertRaisesRegex(LEDGER.LedgerError, "缺少验收标准"):
            self.accept(idea_id)

    def test_unresolved_conflicts_cannot_be_accepted(self) -> None:
        first = str(self.new(self.payload("Existing"))["id"])
        self.accept(first)
        for compatibility in ("duplicate", "incompatible", "unknown"):
            conflict = self.conflict(
                compatibility,
                reviewed=[first],
                conflicts=[first] if compatibility != "unknown" else [],
                disposition="defer",
            )
            idea_id = str(self.new(self.payload(compatibility, conflict=conflict))["id"])
            with self.assertRaisesRegex(LEDGER.LedgerError, "不能直接批准"):
                self.accept(idea_id)

    def test_tension_requires_bounded_mitigation(self) -> None:
        first = str(self.new(self.payload("Existing"))["id"])
        self.accept(first)
        bad = self.conflict("tension", reviewed=[first], conflicts=[first], disposition="bounded")
        with self.assertRaisesRegex(LEDGER.LedgerError, "mitigation"):
            self.new(self.payload("Bad tension", conflict=bad))

    def test_terminal_records_are_not_revisable(self) -> None:
        accepted = str(self.new(self.payload("Accepted"))["id"])
        self.accept(accepted)
        rejected = str(self.new(self.payload("Rejected"))["id"])
        self.reject(rejected)
        for idea_id in (accepted, rejected):
            with self.assertRaisesRegex(LEDGER.LedgerError, "只有 proposed"):
                LEDGER.revise_record(self.root, idea_id, self.payload("Changed"))

    def test_superseded_is_derived_without_mutating_old_record(self) -> None:
        old_id = str(self.new(self.payload("Old"))["id"])
        self.accept(old_id)
        old_text = LEDGER.record_path(self.root, old_id).read_text(encoding="utf-8")
        conflict = self.conflict(
            "incompatible",
            reviewed=[old_id],
            conflicts=[old_id],
            disposition="supersede",
            mitigation="The new record fully replaces the old policy.",
        )
        new_id = str(self.new(self.payload("New", conflict=conflict, supersedes=[old_id]))["id"])
        self.accept(new_id)
        self.assertEqual(old_text, LEDGER.record_path(self.root, old_id).read_text(encoding="utf-8"))
        self.assertEqual("superseded", LEDGER.status_summary(self.root)["effective_counts"] and LEDGER.effective_status(
            LEDGER.load_record(LEDGER.record_path(self.root, old_id)),
            LEDGER.superseded_by_map(LEDGER.load_records(self.root)),
        ))

    def test_lineage_dependency_follows_supersession_without_invalidating_ledger(self) -> None:
        base = str(self.new(self.payload("Base"))["id"])
        self.accept(base)
        dependent = str(
            self.new(self.payload("Dependent", depends_on=[{"id": base, "mode": "lineage"}]))["id"]
        )
        self.accept(dependent)
        conflict = self.conflict(
            "incompatible",
            reviewed=[base],
            conflicts=[base],
            disposition="supersede",
            mitigation="Replace the base while preserving its lineage contract.",
        )
        successor = str(self.new(self.payload("Successor", conflict=conflict, supersedes=[base]))["id"])
        self.accept(successor)
        self.assertEqual([], LEDGER.validate_ledger(self.root))
        mapping = {item["meta"]["id"]: item for item in LEDGER.load_records(self.root)}
        reverse = LEDGER.superseded_by_map(list(mapping.values()))
        resolved, errors = LEDGER.resolved_dependencies_for(mapping[dependent]["meta"], mapping, reverse)
        self.assertEqual([], errors)
        self.assertEqual(successor, resolved[0]["resolved_id"])

    def test_exact_dependency_blocks_supersession_before_write(self) -> None:
        base = str(self.new(self.payload("Base"))["id"])
        self.accept(base)
        dependent = str(
            self.new(self.payload("Exact dependent", depends_on=[{"id": base, "mode": "exact"}]))["id"]
        )
        self.accept(dependent)
        conflict = self.conflict(
            "incompatible",
            reviewed=[base],
            conflicts=[base],
            disposition="supersede",
            mitigation="Replace base.",
        )
        successor = str(self.new(self.payload("Successor", conflict=conflict, supersedes=[base]))["id"])
        with self.assertRaisesRegex(LEDGER.LedgerError, "exact 依赖"):
            self.accept(successor)
        self.assertEqual("proposed", LEDGER.load_record(LEDGER.record_path(self.root, successor))["status"])
        self.assertEqual([], LEDGER.validate_ledger(self.root))

    def test_superseded_historical_exact_dependency_no_longer_blocks(self) -> None:
        base = str(self.new(self.payload("Base"))["id"])
        self.accept(base)
        dependent = str(
            self.new(self.payload("Exact dependent", depends_on=[{"id": base, "mode": "exact"}]))["id"]
        )
        self.accept(dependent)
        dep_conflict = self.conflict(
            "incompatible",
            reviewed=[dependent],
            conflicts=[dependent],
            disposition="supersede",
            mitigation="Replace the dependent decision.",
        )
        replacement = str(
            self.new(self.payload("Replacement", conflict=dep_conflict, supersedes=[dependent]))["id"]
        )
        self.accept(replacement)
        base_conflict = self.conflict(
            "incompatible",
            reviewed=[base],
            conflicts=[base],
            disposition="supersede",
            mitigation="Replace the base after its exact dependent became historical.",
        )
        successor = str(self.new(self.payload("Base successor", conflict=base_conflict, supersedes=[base]))["id"])
        self.accept(successor)
        self.assertEqual([], LEDGER.validate_ledger(self.root))

    def test_relation_sets_are_disjoint(self) -> None:
        base = str(self.new(self.payload("Base"))["id"])
        self.accept(base)
        conflict = self.conflict(
            "incompatible",
            reviewed=[base],
            conflicts=[base],
            disposition="supersede",
            mitigation="Replace it.",
        )
        with self.assertRaisesRegex(LEDGER.LedgerError, "supersedes 与 depends_on"):
            self.new(
                self.payload(
                    "Invalid",
                    conflict=conflict,
                    supersedes=[base],
                    depends_on=[{"id": base, "mode": "lineage"}],
                )
            )

    def test_conflict_and_dependency_sets_are_disjoint(self) -> None:
        base = str(self.new(self.payload("Base"))["id"])
        self.accept(base)
        conflict = self.conflict(
            "tension",
            reviewed=[base],
            conflicts=[base],
            disposition="bounded",
            mitigation="Use separate scopes.",
        )
        with self.assertRaisesRegex(LEDGER.LedgerError, "conflicts_with 与 depends_on"):
            self.new(self.payload("Invalid", conflict=conflict, depends_on=[base]))

    def test_candidate_cycle_is_blocked(self) -> None:
        base = str(self.new(self.payload("Base"))["id"])
        self.accept(base)
        dependent = str(self.new(self.payload("Dependent", depends_on=[base]))["id"])
        self.accept(dependent)
        conflict = self.conflict(
            "incompatible",
            reviewed=[base],
            conflicts=[base],
            disposition="supersede",
            mitigation="Replace base.",
        )
        successor = str(
            self.new(
                self.payload(
                    "Cycle successor",
                    conflict=conflict,
                    supersedes=[base],
                    depends_on=[{"id": dependent, "mode": "lineage"}],
                )
            )["id"]
        )
        with self.assertRaisesRegex(LEDGER.LedgerError, "存在环"):
            self.accept(successor)
        self.assertEqual("proposed", LEDGER.load_record(LEDGER.record_path(self.root, successor))["status"])

    def test_parallel_superseders_are_blocked_at_second_acceptance(self) -> None:
        base = str(self.new(self.payload("Base"))["id"])
        self.accept(base)
        def replacement(title: str) -> str:
            conflict = self.conflict(
                "incompatible",
                reviewed=[base],
                conflicts=[base],
                disposition="supersede",
                mitigation="Replace base.",
            )
            return str(self.new(self.payload(title, conflict=conflict, supersedes=[base]))["id"])
        first, second = replacement("First"), replacement("Second")
        self.accept(first)
        with self.assertRaisesRegex(LEDGER.LedgerError, "多个 accepted"):
            self.accept(second)
        self.assertEqual("proposed", LEDGER.load_record(LEDGER.record_path(self.root, second))["status"])

    def test_manual_accepted_incompatible_record_is_detected(self) -> None:
        idea_id = str(self.new(self.payload())["id"])
        path = LEDGER.record_path(self.root, idea_id)
        meta = LEDGER.load_record(path)
        now = LEDGER.utc_now()
        meta["status"] = "accepted"
        meta["accepted_at"] = now
        meta["updated_at"] = now
        meta["approval"] = {
            "method": "explicit_phrase",
            "recorded_phrase": f"批准 {idea_id}",
            "actor_verified": False,
            "recorded_at": now,
        }
        meta["conflict"] = self.conflict("incompatible", reviewed=[], conflicts=[], disposition="defer")
        path.write_text(LEDGER.render_record(meta), encoding="utf-8", newline="\n")
        errors = LEDGER.validate_ledger(self.root)
        self.assertTrue(any("不可批准" in error or "incompatible" in error for error in errors))

    def test_terminal_timestamp_must_equal_updated_at(self) -> None:
        idea_id = str(self.new(self.payload())["id"])
        self.accept(idea_id)
        path = LEDGER.record_path(self.root, idea_id)
        meta = LEDGER.load_record(path)
        import datetime as _dt
        accepted_at = LEDGER.parse_timestamp(meta["accepted_at"], "accepted_at")
        meta["updated_at"] = (accepted_at + _dt.timedelta(seconds=1)).isoformat()
        path.write_text(LEDGER.render_record(meta), encoding="utf-8", newline="\n")
        self.assertTrue(any("updated_at == accepted_at" in error for error in LEDGER.validate_ledger(self.root)))

    def test_noncanonical_record_filename_is_rejected(self) -> None:
        idea_id = str(self.new(self.payload())["id"])
        canonical = LEDGER.record_path(self.root, idea_id)
        canonical.rename(canonical.with_name("IDEA-00001.md"))
        with self.assertRaisesRegex(LEDGER.LedgerError, "文件名"):
            LEDGER.status_summary(self.root)

    def test_legacy_conflict_and_string_dependency_remain_readable(self) -> None:
        base = str(self.new(self.payload("Base"))["id"])
        self.accept(base)
        old = self.payload("Legacy")
        old["conflict"] = {
            "kind": "none",
            "related_ids": [base],
            "rationale": "The legacy record reviewed the existing decision.",
            "confidence": "high",
            "resolution": None,
        }
        old["depends_on"] = [base]
        legacy_id = str(self.new(old)["id"])
        # New writes normalize the old input, so additionally verify the canonical parser's legacy branch.
        meta = LEDGER.load_record(LEDGER.record_path(self.root, legacy_id))
        meta["conflict"] = {
            "kind": "none",
            "related_ids": [base],
            "rationale": "The legacy record reviewed the existing decision.",
            "confidence": "high",
            "resolution": None,
        }
        meta["depends_on"] = [base]
        path = LEDGER.record_path(self.root, legacy_id)
        path.write_text(LEDGER.render_record(meta), encoding="utf-8", newline="\n")
        LEDGER.refresh_index(self.root)
        self.assertEqual([], LEDGER.validate_ledger(self.root))
