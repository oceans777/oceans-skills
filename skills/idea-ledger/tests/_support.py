from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = SKILL_ROOT / "scripts"
SCRIPT = SCRIPT_DIR / "idea_ledger.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import idea_ledger_core as LEDGER  # noqa: E402
import idea_ledger_ci as LEDGER_CI  # noqa: E402


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    input_text: str | None = None,
    check: bool = True,
    timeout: float = 20,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    result = subprocess.run(
        args,
        cwd=cwd,
        input=input_text,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        check=False,
        timeout=timeout,
        env=env,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"command failed: {args}\ncode={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


class LedgerCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="idea-ledger-v22-test-")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def cli(self, *args: str, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, str(SCRIPT), *args, "--root", str(self.root)], input_text=input_text, check=check)

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return run(["git", "-C", str(self.root), *args], check=check)

    def init_git(self) -> None:
        self.git("init", "-q")
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.com")

    def init(self) -> None:
        LEDGER.init_project(self.root)

    def conflict(
        self,
        compatibility: str = "compatible",
        *,
        reviewed: list[str] | None = None,
        conflicts: list[str] | None = None,
        disposition: str = "none",
        mitigation: str | None = None,
        confidence: str = "high",
    ) -> dict[str, object]:
        return {
            "compatibility": compatibility,
            "reviewed_ids": reviewed or [],
            "conflicts_with": conflicts or [],
            "rationale": "Relevant clauses and scope were reviewed.",
            "confidence": confidence,
            "disposition": disposition,
            "mitigation": mitigation,
        }

    def payload(
        self,
        title: str = "Local-first workspace",
        *,
        word: str = "local",
        conflict: dict[str, object] | None = None,
        supersedes: list[str] | None = None,
        depends_on: list[object] | None = None,
        notes: list[str] | None = None,
        long_decision: str | None = None,
    ) -> dict[str, object]:
        return {
            "title": title,
            "charter": {
                "goal": f"Give operators a clear {word} product rule.",
                "actors": ["Product administrators", "Operators"],
                "scope": [f"The {word} behavior", "Its user-visible boundary"],
                "principles": ["Detailed design and acceptance criteria must follow this charter."],
                "non_goals": ["Implementation details are not decided in the charter."],
            },
            "goal": f"Deliver {word} behavior safely.",
            "decision": long_decision or f"Use the reviewed {word} policy for this scope.",
            "rationale": f"The {word} policy balances the stated user and operational needs.",
            "outcome": f"Users observe the intended {word} result.",
            "scope": [word, "product"],
            "tags": [word],
            "constraints": ["Do not weaken the stated boundary."],
            "acceptance_criteria": [f"The {word} behavior is observable."],
            "conflict": conflict or self.conflict(),
            "supersedes": supersedes or [],
            "depends_on": depends_on or [],
            "notes": notes or [],
            "alternatives_considered": ["Keep the current behavior unchanged."],
            "tradeoffs": ["More explicit governance in exchange for additional record detail."],
            "non_goals": ["This decision does not authenticate approvers."],
            "sources": ["Internal product review"],
            "owner": "Product",
            "review_at": None,
        }

    def new(self, payload: dict[str, object]) -> dict[str, object]:
        return LEDGER.create_record(self.root, payload)

    def accept(self, idea_id: str) -> dict[str, object]:
        return LEDGER.accept_record(self.root, idea_id, f"批准 {idea_id}")

    def reject(self, idea_id: str, reason: str = "Not selected.") -> dict[str, object]:
        return LEDGER.reject_record(self.root, idea_id, reason)

    def commit_all(self, message: str, body: str | None = None) -> None:
        self.git("add", ".")
        args = ["commit", "-q", "-m", message]
        if body is not None:
            args += ["-m", body]
        self.git(*args)


class CiCase(LedgerCase):
    def setUp(self) -> None:
        super().setUp()
        self.init_git()
        self.init()
        self.commit_all("chore: initialize ledger")

    def accepted_and_committed(self, title: str = "Decision") -> str:
        idea_id = str(self.new(self.payload(title))["id"])
        self.accept(idea_id)
        self.commit_all(f"idea: accept {idea_id}")
        return idea_id

    def rewrite_terminal(self, idea_id: str, field: str, value: str) -> None:
        path = LEDGER.record_path(self.root, idea_id)
        meta = LEDGER.load_record(path)
        meta[field] = value
        path.write_text(LEDGER.render_record(meta), encoding="utf-8", newline="\n")
        LEDGER.refresh_index(self.root)
