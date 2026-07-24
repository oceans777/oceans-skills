from _support import *

class SafetyAndConfigTests(LedgerCase):
    def test_init_has_no_git_side_effect(self) -> None:
        self.init()
        self.assertFalse((self.root / ".git").exists())
        self.assertTrue((self.root / ".idea-ledger/config.json").exists())
        self.assertFalse((self.root / ".githooks").exists())

    def test_init_preserves_existing_hooks_path(self) -> None:
        self.init_git()
        hooks = self.root / ".custom-hooks"
        hooks.mkdir()
        (hooks / "pre-push").write_text("#!/bin/sh\n", encoding="utf-8")
        self.git("config", "core.hooksPath", ".custom-hooks")
        before = self.git("config", "--get", "core.hooksPath").stdout.strip()
        self.init()
        self.assertEqual(before, self.git("config", "--get", "core.hooksPath").stdout.strip())

    def test_read_only_command_does_not_initialize(self) -> None:
        result = self.cli("status", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / ".idea-ledger").exists())

    def test_package_has_no_hooks_or_installer(self) -> None:
        self.assertFalse((SKILL_ROOT / "hooks").exists())
        self.assertFalse((SKILL_ROOT / "install.py").exists())
        self.assertFalse((SKILL_ROOT / "install.sh").exists())
        codex = json.loads((SKILL_ROOT / "assets/plugin-manifests/codex-plugin.json").read_text(encoding="utf-8"))
        claude = json.loads((SKILL_ROOT / "assets/plugin-manifests/claude-plugin.json").read_text(encoding="utf-8"))
        self.assertNotIn("hooks", codex)
        self.assertNotIn("hooks", claude)

    def test_lock_is_exclusive_and_reusable(self) -> None:
        self.init()
        with LEDGER.ledger_lock(self.root):
            with self.assertRaises(LEDGER.LedgerError):
                with LEDGER.ledger_lock(self.root, timeout_seconds=0.05):
                    pass
        with LEDGER.ledger_lock(self.root, timeout_seconds=0.1):
            pass

    def test_record_symlink_is_rejected(self) -> None:
        self.init()
        with tempfile.TemporaryDirectory(prefix="idea-ledger-outside-") as outside:
            target = Path(outside) / "secret"
            target.write_text("secret", encoding="utf-8")
            link = self.root / "docs/idea-ledger/records/IDEA-0001.md"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError) as exc:  # pragma: no cover
                self.skipTest(str(exc))
            with self.assertRaisesRegex(LEDGER.LedgerError, "符号链接"):
                LEDGER.status_summary(self.root)
            self.assertEqual("secret", target.read_text(encoding="utf-8"))

    def test_config_unknown_field_is_rejected(self) -> None:
        self.init()
        path = self.root / ".idea-ledger/config.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["magic"] = True
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(LEDGER.LedgerError, "未知字段"):
            LEDGER.load_config(self.root)

    def test_config_path_collisions_are_rejected(self) -> None:
        self.init()
        path = self.root / ".idea-ledger/config.json"
        base = json.loads(path.read_text(encoding="utf-8"))
        cases = [
            {"index_file": ".idea-ledger/config.json"},
            {"index_file": "docs/idea-ledger/records/INDEX.md"},
            {"prd_dir": "docs/idea-ledger/records/prd"},
            {"records_dir": "docs/prd/records"},
        ]
        for patch in cases:
            data = dict(base)
            data.update(patch)
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(LEDGER.LedgerError, msg=str(patch)):
                LEDGER.load_config(self.root)

    def test_config_rejects_colon_and_control_characters(self) -> None:
        self.init()
        path = self.root / ".idea-ledger/config.json"
        base = json.loads(path.read_text(encoding="utf-8"))
        for invalid in ["docs/:magic/records", "docs/records\nother"]:
            data = dict(base)
            data["records_dir"] = invalid
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(LEDGER.LedgerError):
                LEDGER.load_config(self.root)

    def test_policy_exemption_preserves_dot_prefix(self) -> None:
        config = {"policy_exempt_prefixes": [".github/", "README.md"]}
        self.assertTrue(LEDGER_CI.is_exempt_path(".github/workflows/check.yml", config))
        self.assertTrue(LEDGER_CI.is_exempt_path("./.github/workflows/check.yml", config))
        self.assertFalse(LEDGER_CI.is_exempt_path("github/workflows/check.yml", config))
        self.assertFalse(LEDGER_CI.is_exempt_path("README.md.bak", config))
