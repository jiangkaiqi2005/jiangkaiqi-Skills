from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import sys

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from check_skill_dev_gate import (  # noqa: E402
    REQUIRED_EVIDENCE, REQUIRED_ROLES, REQUIRED_SIMULATIONS,
    REQUIRED_VALIDATIONS, validate,
)


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_dev_manifest(root: Path) -> Path:
    """Build a complete frozen development-review package."""
    skill = root / "skill"
    (skill / "scripts").mkdir(parents=True)
    (skill / "tests").mkdir()
    skill_files = {
        "SKILL.md": "# Skill under review\n\nFrozen candidate instructions.\n",
        "scripts/check.py": "# frozen checker\nprint('ok')\n",
        "tests/test.py": "# frozen tests\nassert True\n",
    }
    for relative, content in skill_files.items():
        path = skill / relative
        path.write_text(content, encoding="utf-8")

    evidence_dir = root / "evidence"
    evidence_dir.mkdir()
    evidence_items = []
    for evidence_id in sorted(REQUIRED_EVIDENCE):
        path = evidence_dir / f"{evidence_id}.txt"
        path.write_text(
            f"{evidence_id}: frozen, non-empty, independently checkable evidence.\n",
            encoding="utf-8",
        )
        evidence_items.append({
            "id": evidence_id,
            "path": path.relative_to(root).as_posix(),
            "sha256": hash_file(path),
        })

    members = [
        {
            "scope": "skill", "path": relative,
            "sha256": hash_file(skill / relative),
        }
        for relative in sorted(skill_files)
    ]
    members.extend({
        "scope": "review", "path": item["path"], "sha256": item["sha256"],
    } for item in evidence_items)
    version_index = root / "skill-version-index.json"
    version_index.write_text(json.dumps({
        "schema_version": "1.0", "members": members,
    }, sort_keys=True), encoding="utf-8")
    version_id = hash_file(version_index)

    locations = [
        "SKILL.md#L1", "scripts/check.py#L1", "tests/test.py#L1",
        "SKILL.md#L3", "scripts/check.py#L2",
    ]
    reviews = []
    for index, role in enumerate(sorted(REQUIRED_ROLES)):
        sealed_at = f"2026-07-29T00:00:{index:02d}+08:00"
        provider_run = f"provider-run-{index}"
        reviewer_id = f"skill-dev-reviewer-{index}"
        report_path = root / f"skill-dev-review-{index}.json"
        report_path.write_text(json.dumps({
            "schema_version": "1.0",
            "role_id": role,
            "reviewer_id": reviewer_id,
            "provider_run_id": provider_run,
            "reviewed_version_id": version_id,
            "sealed_at": sealed_at,
            "criteria": [{
                "criterion": criterion,
                "score": 20,
                "justification":
                    "The frozen evidence directly supports this criterion and "
                    "the stated boundary was independently checked.",
                "evidence_locations": [locations[criterion - 1]],
            } for criterion in range(1, 6)],
            "fatal_findings": [], "major_findings": [], "minor_findings": [],
            "missing_evidence": [], "conclusion": "PASS",
        }), encoding="utf-8")
        reviews.append({
            "role_id": role,
            "reviewer_id": reviewer_id,
            "provider_run_id": provider_run,
            "sealed_at": sealed_at,
            "score": 100,
            "criteria": [20, 20, 20, 20, 20],
            "findings": [], "vetoes": [], "missing_evidence": [],
            "reviewed_version_id": version_id,
            "report_path": report_path.name,
            "report_sha256": hash_file(report_path),
            "evidence_locations": locations,
            "independence": {
                "did_not_modify": True,
                "did_not_view_other_reviews": True,
                "received_only_allowed_inputs": True,
                "initial_score_sealed_before_deliberation": True,
            },
        })

    deliberation_path = root / "skill-dev-deliberation.md"
    deliberation_path.write_text(
        "All initial reports were sealed before cross-questioning.\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "1.0",
        "status": "SKILL_DEVELOPMENT_PASS",
        "version_id": version_id,
        "version_index_path": version_index.name,
        "development_evidence": evidence_items,
        "validation_results": [{
            "id": validation_id,
            "command": f"python run {validation_id} against frozen candidate",
            "exit_code": 0,
            "evidence_id": "test-log" if validation_id != "e2e-simulation"
            else "e2e-log",
        } for validation_id in sorted(REQUIRED_VALIDATIONS)],
        "simulation_results": [{
            "id": simulation_id,
            "status": "PASS",
            "evidence_id": "e2e-log",
            "assertion":
                "The expected route, refusal, rollback, or recovery behavior "
                "was observed in the frozen fixture.",
        } for simulation_id in sorted(REQUIRED_SIMULATIONS)],
        "contributor_ids": ["developer-root"],
        "disallowed_reviewer_ids": ["prior-reviewer"],
        "disallowed_provider_run_ids": ["prior-provider-run"],
        "reviews": reviews,
        "review_deliberation": {
            "path": deliberation_path.name,
            "sha256": hash_file(deliberation_path),
            "started_at": "2026-07-29T00:01:00+08:00",
            "participant_roles": sorted(REQUIRED_ROLES),
            "unresolved_findings": [],
            "cross_questions": [{
                "raised_by_role": role,
                "status": "CLOSED",
                "resolution":
                    "This role challenged the frozen evidence, and the panel "
                    "closed the question with a traceable shared resolution.",
            } for role in sorted(REQUIRED_ROLES)],
        },
        "blockers": [],
    }
    manifest_path = root / "skill-development-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


class SkillDevGateTests(unittest.TestCase):
    def validate_root(self, root: Path, manifest: Path) -> list[str]:
        return validate(manifest, root / "skill")

    def test_positive_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = build_dev_manifest(root)
            self.assertEqual(self.validate_root(root, manifest), [])

    def test_missing_role_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = build_dev_manifest(root)
            data = load_manifest(manifest); data["reviews"].pop()
            write_manifest(manifest, data)
            self.assertTrue(any("missing required roles" in e for e in self.validate_root(root, manifest)))

    def test_score_or_finding_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = build_dev_manifest(root)
            data = load_manifest(manifest)
            data["reviews"][0]["score"] = 99
            data["reviews"][1]["findings"] = ["minor"]
            write_manifest(manifest, data)
            errors = self.validate_root(root, manifest)
            self.assertTrue(any("score must be 100" in e for e in errors))
            self.assertTrue(any("findings must be empty" in e for e in errors))

    def test_identity_alias_and_disallowed_reviewer_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = build_dev_manifest(root)
            data = load_manifest(manifest)
            data["reviews"][1]["reviewer_id"] = data["reviews"][0]["reviewer_id"].upper()
            data["reviews"][2]["reviewer_id"] = "prior-reviewer"
            data["reviews"][3]["provider_run_id"] = "prior-provider-run"
            write_manifest(manifest, data)
            errors = self.validate_root(root, manifest)
            self.assertGreaterEqual(sum("not independent" in e for e in errors), 2)
            self.assertTrue(any("unique and new" in e for e in errors))

    def test_contributor_cannot_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = build_dev_manifest(root)
            data = load_manifest(manifest)
            data["reviews"][0]["reviewer_id"] = "developer-root"
            write_manifest(manifest, data)
            self.assertTrue(any("not independent" in e for e in self.validate_root(root, manifest)))

    def test_independence_or_version_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = build_dev_manifest(root)
            data = load_manifest(manifest)
            data["reviews"][0]["independence"]["did_not_modify"] = False
            data["reviews"][1]["reviewed_version_id"] = "a" * 64
            write_manifest(manifest, data)
            errors = self.validate_root(root, manifest)
            self.assertTrue(any("independence" in e for e in errors))
            self.assertTrue(any("reviewed_version_id" in e for e in errors))

    def test_incomplete_or_tampered_version_index_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = build_dev_manifest(root)
            index = root / "skill-version-index.json"
            data = json.loads(index.read_text(encoding="utf-8"))
            data["members"].pop(0)
            index.write_text(json.dumps(data), encoding="utf-8")
            errors = self.validate_root(root, manifest)
            self.assertTrue(any("version_id does not match" in e for e in errors))
            self.assertTrue(any("exactly cover all substantive" in e for e in errors))

    def test_post_review_skill_change_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = build_dev_manifest(root)
            (root / "skill/SKILL.md").write_text("changed after review\n", encoding="utf-8")
            self.assertTrue(any("skill member mismatch" in e for e in self.validate_root(root, manifest)))

    def test_report_hash_content_and_locator_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = build_dev_manifest(root)
            data = load_manifest(manifest)
            report = root / data["reviews"][0]["report_path"]
            report_data = json.loads(report.read_text(encoding="utf-8"))
            report_data["criteria"][0]["justification"] = "ok"
            report_data["criteria"][1]["evidence_locations"] = ["SKILL.md#L999"]
            report.write_text(json.dumps(report_data), encoding="utf-8")
            data["reviews"][0]["report_sha256"] = hash_file(report)
            data["reviews"][0]["evidence_locations"] = [
                "SKILL.md#L1", "SKILL.md#L999", "tests/test.py#L1",
                "SKILL.md#L3", "scripts/check.py#L2",
            ]
            write_manifest(manifest, data)
            errors = self.validate_root(root, manifest)
            self.assertTrue(any("criterion[0] is incomplete" in e for e in errors))
            self.assertTrue(any("criterion[1] evidence is invalid" in e for e in errors))

    def test_missing_validation_or_simulation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = build_dev_manifest(root)
            data = load_manifest(manifest)
            data["validation_results"].pop()
            data["simulation_results"].pop()
            write_manifest(manifest, data)
            errors = self.validate_root(root, manifest)
            self.assertTrue(any("four required checks" in e for e in errors))
            self.assertTrue(any("all ten scenarios" in e for e in errors))

    def test_deliberation_order_and_unresolved_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = build_dev_manifest(root)
            data = load_manifest(manifest)
            data["review_deliberation"]["started_at"] = "2026-07-28T23:59:00+08:00"
            data["review_deliberation"]["unresolved_findings"] = ["conflict"]
            write_manifest(manifest, data)
            errors = self.validate_root(root, manifest)
            self.assertTrue(any("start after every" in e for e in errors))
            self.assertTrue(any("unresolved_findings" in e for e in errors))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = build_dev_manifest(root)
            data = load_manifest(manifest)
            data["review_deliberation"]["cross_questions"].pop()
            write_manifest(manifest, data)
            errors = self.validate_root(root, manifest)
            self.assertTrue(any("cross_questions" in e for e in errors))

    def test_naive_or_date_only_review_times_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = build_dev_manifest(root)
            data = load_manifest(manifest)
            data["reviews"][0]["sealed_at"] = "2026-07-29"
            data["reviews"][1]["sealed_at"] = "2026-07-29T00:00:01"
            data["review_deliberation"]["started_at"] = "2026-07-29T00:01:00"
            write_manifest(manifest, data)
            errors = self.validate_root(root, manifest)
            self.assertGreaterEqual(
                sum("sealed_at is invalid" in e for e in errors), 2
            )
            self.assertTrue(any("start after every" in e for e in errors))

    def test_status_and_blockers_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = build_dev_manifest(root)
            data = load_manifest(manifest)
            data["status"] = "SKILL_REVIEW_FAILED"
            data["blockers"] = ["missing independent reviewer"]
            write_manifest(manifest, data)
            errors = self.validate_root(root, manifest)
            self.assertTrue(any("status must be" in e for e in errors))
            self.assertTrue(any("blockers must be empty" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
