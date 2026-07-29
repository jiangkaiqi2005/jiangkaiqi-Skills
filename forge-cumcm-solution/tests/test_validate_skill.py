from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = SKILL_ROOT / "scripts"
import sys

sys.path.insert(0, str(SCRIPT_DIR))
from validate_skill import validate  # noqa: E402


class ValidateSkillTests(unittest.TestCase):
    def test_current_package_passes(self) -> None:
        self.assertEqual(validate(SKILL_ROOT), [])

    def test_todo_and_extra_yaml_key_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / "skill"
            shutil.copytree(SKILL_ROOT, copy)
            skill = copy / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\nTODO\n", encoding="utf-8")
            metadata_path = copy / "agents/openai.yaml"
            metadata_path.write_text(
                metadata_path.read_text(encoding="utf-8")
                + "\npolicy:\n  allow_implicit_invocation: true\n",
                encoding="utf-8",
            )
            errors = validate(copy)
            self.assertTrue(any("TODO" in error for error in errors))
            self.assertTrue(any("only interface" in error for error in errors))

    def test_guide_snapshot_tampering_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / "skill"
            shutil.copytree(SKILL_ROOT, copy)
            snapshot = copy / "references/cumcm-guide-v1.0.md"
            snapshot.write_text(
                snapshot.read_text(encoding="utf-8") + "\nchanged\n",
                encoding="utf-8",
            )
            errors = validate(copy)
            self.assertTrue(any(
                "bundled guide snapshot SHA-256" in error for error in errors
            ))

    def test_traceability_stage_anchor_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / "skill"
            shutil.copytree(SKILL_ROOT, copy)
            trace = copy / "references/guide-traceability.md"
            trace.write_text(
                trace.read_text(encoding="utf-8").replace(
                    "阶段三 §4 一致性审计",
                    "阶段三 §9 不存在的终检",
                ),
                encoding="utf-8",
            )
            errors = validate(copy)
            self.assertTrue(any(
                "missing required review/contract token" in error
                for error in errors
            ))

    def test_dynamic_proposal_and_separate_final_review_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / "skill"
            shutil.copytree(SKILL_ROOT, copy)
            tournament = copy / "references/stage1-proposal-tournament.md"
            tournament.write_text(
                tournament.read_text(encoding="utf-8")
                .replace("ADDITIONAL-PROPOSER-*", "REMOVED-DYNAMIC-PROPOSER", 1)
                .replace("不充当终审", "直接充当终审"),
                encoding="utf-8",
            )
            errors = validate(copy)
            self.assertTrue(any(
                "references/stage1-proposal-tournament.md" in error
                and "missing required review/contract token" in error
                for error in errors
            ))


if __name__ == "__main__":
    unittest.main()
