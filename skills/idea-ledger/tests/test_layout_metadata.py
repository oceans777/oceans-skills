from _support import *

class RepositoryLayoutTests(unittest.TestCase):
    def test_skill_is_self_contained(self) -> None:
        for relative in (
            "SKILL.md",
            "LICENSE",
            "VERSION",
            "scripts/idea_ledger.py",
            "references/record-schema.md",
            "agents/openai.yaml",
            "assets/plugin-manifests/codex-plugin.json",
            "assets/plugin-manifests/claude-plugin.json",
        ):
            self.assertTrue((SKILL_ROOT / relative).is_file(), relative)

    def test_direct_install_entrypoint_runs(self) -> None:
        result = run([sys.executable, str(SKILL_ROOT / "scripts/idea_ledger.py"), "--version"])
        self.assertIn("2.2.0", result.stdout)


class MetadataPolicyTests(unittest.TestCase):
    def test_invocation_is_implicit_on_both_platforms(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        openai = (SKILL_ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertNotIn("disable-model-invocation", skill)
        self.assertIn("allow_implicit_invocation: true", openai)
        self.assertIn("Automatically review and manage material product decisions", skill)
        self.assertIn("Implicit use may analyze and draft without persistence", skill)

    def test_codex_manifest_has_matching_author_and_developer(self) -> None:
        manifest = json.loads((SKILL_ROOT / "assets/plugin-manifests/codex-plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["author"]["name"], manifest["interface"]["developerName"])
        self.assertEqual("2.2.0", manifest["version"])

    def test_eval_cases_cover_implicit_routing_and_safe_approval(self) -> None:
        cases = json.loads((SKILL_ROOT / "tests/eval-cases.json").read_text(encoding="utf-8"))
        self.assertEqual("implicit_when_material", cases["invocation_policy"])
        self.assertTrue(any(not prompt.startswith(("$idea-ledger", "/idea-ledger")) for prompt in cases["positive"]))
        self.assertIn("继续", cases["approval_negative"])
        self.assertTrue(any("IDEA-" in prompt for prompt in cases["approval_positive"]))
