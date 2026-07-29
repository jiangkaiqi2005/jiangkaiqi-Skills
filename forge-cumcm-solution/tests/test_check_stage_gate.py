from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from check_stage_gate import (  # noqa: E402
    ARTIFACTS, GATE_CHECKS, GUIDE_SECTIONS, GUIDE_SHA256, ROLES,
    VISIBILITY_BY_STAGE_STATUS, WORKFLOW_STEPS, validate, validate_checkpoint,
    validate_pdf,
)


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def iso(minute: int, second: int = 0, offset_hours: int = 8) -> str:
    value = datetime(
        2026, 7, 29, 0, minute, second,
        tzinfo=timezone(timedelta(hours=offset_hours)),
    )
    return value.isoformat()


def minimal_renderable_pdf(compact: bool = False) -> bytes:
    type_token = b"/Type/" if compact else b"/Type /"
    text = b"BT /F1 12 Tf 72 720 Td (CUMCM verified result.) Tj ET"
    objects = [
        b"<< " + type_token + b"Catalog /Pages 2 0 R >>",
        b"<< " + type_token + b"Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< " + type_token
            + b"Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            + b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< " + type_token + b"Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(text)).encode() + b" >>\nstream\n"
        + text + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode()
    )
    return bytes(output)


def trusted_root_payload(
    official_path: str = "official-problem.txt",
    official_hash: str = "a" * 64,
    question_ids: tuple[str, ...] = ("Q1",),
) -> dict:
    return {
        "schema_version": "1.0",
        "official_question_ids": list(question_ids),
        "official_files": [{
            "id": "official-problem",
            "kind": "problem",
            "path": official_path,
            "sha256": official_hash,
            "question_ids": list(question_ids),
            "attested_by": ["official-checker-a", "official-checker-b"],
        }],
        "attestations": [
            {
                "reviewer_id": "official-checker-a",
                "provider_run_id": "official-provider-a",
            },
            {
                "reviewer_id": "official-checker-b",
                "provider_run_id": "official-provider-b",
            },
        ],
    }


def artifact_payload(stage: int, artifact_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "stage": stage,
        "id": artifact_id,
        "status": "VERIFIED",
        "evidence": {
            "purpose": f"Concrete evidence for {artifact_id}",
            "answer_kind": "TEXT" if artifact_id == "result-evidence-contract" else "MIXED",
        },
    }


def build_manifest(
    root: Path, stage: int, additional_roles: tuple[str, ...] = (),
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    prior_path = build_manifest(root, stage - 1) if stage > 1 else None
    input_path = root / f"stage{stage}-official-input.txt"
    input_path.write_text(
        f"Official stage {stage} input with one complete question.", encoding="utf-8"
    )
    inputs = [{
        "id": "official-input",
        "path": input_path.name,
        "sha256": hash_file(input_path),
    }]
    prior_record = None
    if prior_path is not None:
        prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
        inputs.append({
            "id": "prior-stage-manifest",
            "path": prior_path.name,
            "sha256": hash_file(prior_path),
        })
        prior_record = {
            "manifest_path": prior_path.name,
            "sha256": hash_file(prior_path),
            "version_id": prior_data["version_id"],
        }

    artifacts: list[dict] = []
    artifact_paths: dict[str, Path] = {}
    role_set = set(ROLES[stage]) | set(additional_roles)
    for artifact_id in sorted(
        ARTIFACTS[stage] - {
            "version-index", "execution-record", "stage-workflow-record",
        }
    ):
        suffix = ".pdf" if artifact_id == "final-pdf" else ".json"
        path = root / f"stage{stage}-{artifact_id}{suffix}"
        if artifact_id == "final-pdf":
            path.write_bytes(minimal_renderable_pdf())
        else:
            write_json(path, artifact_payload(stage, artifact_id))
        artifact_paths[artifact_id] = path
        artifacts.append({
            "id": artifact_id,
            "path": path.name,
            "sha256": hash_file(path),
            "status": "VERIFIED",
        })

    anchor_id = next(iter(artifact_paths))
    execution_path = root / f"stage{stage}-execution.json"
    execution = {
        "schema_version": "1.0",
        "stage": stage,
        "guide_snapshot_sha256": GUIDE_SHA256.upper(),
        "guide_sections": sorted(GUIDE_SECTIONS[stage]),
        "guide_applications": [{
            "guide_section": section,
            "current_task_action": (
                f"Apply guide section {section} to the current stage task and "
                "verify its concrete evidence before candidate freeze."
            ),
            "evidence_artifact_ids": [anchor_id],
        } for section in sorted(GUIDE_SECTIONS[stage])],
        "execution_contract": [{
            "question_id": "Q1",
            "task": "Complete the current official question with the stage method and evidence chain.",
            "acceptance": "The frozen artifact answers the task and can be independently checked.",
            "status": "COMPLETE",
            "evidence_artifact_ids": [anchor_id],
        }],
        "self_review": {
            "roles": [{
                "role_id": role,
                "criteria": [20, 20, 20, 20, 20],
                "findings": [],
                "evidence_artifact_ids": [anchor_id],
            } for role in sorted(role_set)]
        },
        "candidate_frozen_at": iso(5),
        "steps": [
            {
                "sequence": index + 1,
                "name": name,
                "status": "COMPLETE",
                "actor_id": "executor",
                "completed_at": iso((1, 2, 3, 4, 5)[index]),
                "evidence_artifact_ids": [anchor_id],
            }
            for index, name in enumerate(WORKFLOW_STEPS[:5])
        ],
    }
    write_json(execution_path, execution)
    artifact_paths["execution-record"] = execution_path
    artifacts.append({
        "id": "execution-record",
        "path": execution_path.name,
        "sha256": hash_file(execution_path),
        "status": "VERIFIED",
    })

    index_members = [
        {
            "kind": "input",
            "id": item["id"],
            "path": item["path"],
            "sha256": item["sha256"],
        }
        for item in inputs
    ] + [
        {
            "kind": "artifact",
            "id": item["id"],
            "path": item["path"],
            "sha256": item["sha256"],
        }
        for item in artifacts
    ]
    index_members.sort(key=lambda item: (item["path"], item["kind"], item["id"]))
    index_path = root / f"stage{stage}-version-index.json"
    write_json(index_path, {
        "schema_version": "1.0",
        "stage": stage,
        "members": index_members,
    })
    version = hash_file(index_path)
    artifacts.append({
        "id": "version-index",
        "path": index_path.name,
        "sha256": hash_file(index_path),
        "status": "VERIFIED",
    })

    evidence_paths = [
        path.name for artifact_id, path in sorted(artifact_paths.items())
    ][:3]
    reviews: list[dict] = []
    providers: list[str] = []
    for index, role in enumerate(sorted(role_set)):
        reviewer = f"stage{stage}-reviewer-{index}"
        provider = f"stage{stage}-provider-{index}"
        providers.append(provider)
        sealed = iso(6, index)
        locations = [
            location
            for _ in range(5)
            for location in (
                f"{evidence_paths[0]}#/stage",
                f"{evidence_paths[1]}#/id",
                f"{evidence_paths[2]}#/status",
            )
        ]
        report = {
            "role_id": role,
            "reviewer_id": reviewer,
            "provider_run_id": provider,
            "reviewed_version_id": version,
            "conclusion": "PASS",
            "sealed_at": sealed,
            "criteria": [
                {
                    "criterion": f"criterion-{criterion}",
                    "score": 20,
                    "justification": (
                        "The frozen execution evidence directly supports this "
                        "criterion, and no defect was found within the stated "
                        "stage scope and independent review boundary."
                    ),
                    "evidence_locations": [
                        f"{evidence_paths[0]}#/stage",
                        f"{evidence_paths[1]}#/id",
                        f"{evidence_paths[2]}#/status",
                    ],
                }
                for criterion in range(5)
            ],
            "fatal_findings": [],
            "major_findings": [],
            "minor_findings": [],
            "missing_evidence": [],
        }
        report_path = root / f"stage{stage}-review-{index}.json"
        write_json(report_path, report)
        reviews.append({
            "role_id": role,
            "reviewer_id": reviewer,
            "provider_run_id": provider,
            "sealed_at": sealed,
            "criteria": [20, 20, 20, 20, 20],
            "score": 100,
            "findings": [],
            "vetoes": [],
            "reviewed_version_id": version,
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

    deliberation_path = root / f"stage{stage}-deliberation.json"
    write_json(deliberation_path, {
        "status": "CLOSED",
        "roles": sorted(role_set),
    })
    deliberation = {
        "path": deliberation_path.name,
        "sha256": hash_file(deliberation_path),
        "started_at": iso(8),
        "participant_roles": sorted(role_set),
        "unresolved_findings": [],
        "cross_questions": [
            {
                "raised_by_role": role,
                "status": "CLOSED",
                "resolution": "The cited frozen evidence resolves the independent question.",
            }
            for role in sorted(role_set)
        ],
    }

    workflow_path = root / f"stage{stage}-workflow.json"
    workflow = {
        "schema_version": "1.0",
        "stage": stage,
        "review_plan": {
            "required_role_ids": sorted(ROLES[stage]),
            "additional_role_ids": sorted(set(additional_roles)),
        },
        "review_started_at": iso(5, 30),
        "review_completed_at": iso(14),
        "state_history": [
            {"state": "NOT_STARTED", "at": iso(0), "actor_id": "executor"},
            {"state": "EXECUTING", "at": iso(0, 30), "actor_id": "executor"},
            {"state": "SELF_REVIEW", "at": iso(3, 30), "actor_id": "executor"},
            {"state": "EXPERT_REVIEW", "at": iso(5, 30), "actor_id": "executor"},
            {"state": "PASS", "at": iso(13), "actor_id": "gate"},
        ],
    }
    write_json(workflow_path, workflow)
    artifacts.append({
        "id": "stage-workflow-record",
        "path": workflow_path.name,
        "sha256": hash_file(workflow_path),
        "status": "OPERATIONAL",
    })

    manifest = {
        "schema_version": "1.0",
        "stage": stage,
        "stage_status": "PASS",
        "visibility_status": "USER_VISIBLE_PASS",
        "version_id": version,
        "inputs": inputs,
        "artifacts": artifacts,
        "gate_checks": {
            key: {
                "passed": True,
                "validator_id": f"validator-{key}",
                "checked_at": iso(4, 30),
                "evidence_artifact_ids": [next(iter(artifact_paths))],
            }
            for key in GATE_CHECKS[stage]
        },
        "blockers": [],
        "reviews": reviews,
        "review_deliberation": deliberation,
    }
    if prior_record is not None:
        manifest["prior_stage"] = prior_record
    manifest_path = root / f"stage{stage}-manifest.json"
    write_json(manifest_path, manifest)
    return manifest_path


def update_workflow_hash(root: Path, manifest_path: Path) -> None:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    item = next(
        value for value in data["artifacts"]
        if value["id"] == "stage-workflow-record"
    )
    item["sha256"] = hash_file(root / item["path"])
    write_json(manifest_path, data)


def update_frozen_artifact_and_version(
    root: Path, manifest_path: Path, artifact_id: str,
) -> None:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact = next(
        item for item in data["artifacts"] if item["id"] == artifact_id
    )
    artifact["sha256"] = hash_file(root / artifact["path"])
    index = next(
        item for item in data["artifacts"] if item["id"] == "version-index"
    )
    index_path = root / index["path"]
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    member = next(
        item for item in index_data["members"] if item["id"] == artifact_id
    )
    member["sha256"] = artifact["sha256"]
    write_json(index_path, index_data)
    index["sha256"] = hash_file(index_path)
    data["version_id"] = index["sha256"]
    for review in data["reviews"]:
        review["reviewed_version_id"] = data["version_id"]
        report_path = root / review["report_path"]
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["reviewed_version_id"] = data["version_id"]
        write_json(report_path, report)
        review["report_sha256"] = hash_file(report_path)
    write_json(manifest_path, data)


def build_checkpoint(
    root: Path, state_history: list[str], final_state: str, stage: int = 1,
) -> Path:
    source = root / "checkpoint-input.txt"
    source.write_text("frozen official input", encoding="utf-8")
    completed = root / "checkpoint-completed.json"
    write_json(completed, {"status": "VERIFIED", "question_id": "Q1"})
    blockers = [{
        "category": "evidence",
        "reason": "The required independent evidence is currently unavailable.",
        "required_material": "Provide the missing independent evidence file.",
        "affected_ids": ["Q1"],
        "resume_condition": "Verify the new evidence and resume from the frozen input.",
    }] if final_state == "BLOCKED" else []
    times = [iso(index) for index in range(len(state_history))]
    data = {
        "schema_version": "1.0",
        "stage": stage,
        "stage_status": final_state,
        "visibility_status": VISIBILITY_BY_STAGE_STATUS[final_state],
        "state_history": [
            {"state": state, "at": at, "actor_id": "executor"}
            for state, at in zip(state_history, times)
        ],
        "blockers": blockers,
        "checkpoint": {
            "saved_at": iso(len(state_history)),
            "actor_id": "executor",
            "environment": "Python 3 verified environment",
            "next_action": "Continue from the frozen input after the condition is met.",
            "resume_from": "EXECUTING",
            "last_trusted_version_id": None,
            "completed_steps": ["LOAD_GUIDE"],
            "completed_artifacts": [{
                "id": "input-inventory",
                "path": completed.name,
                "sha256": hash_file(completed),
            }],
            "frozen_inputs": [{
                "path": source.name,
                "sha256": hash_file(source),
            }],
            "blocker_handling": {
                "status": "COMPLETE",
                "entered_at": times[-1],
                "blocker_indices": list(range(len(blockers))),
            } if final_state == "BLOCKED" else None,
        },
    }
    path = root / "checkpoint.json"
    write_json(path, data)
    return path


class StageGateTests(unittest.TestCase):
    def test_stage1_requires_proposal_tournament_artifacts(self) -> None:
        self.assertTrue({
            "proposal-input-packet", "proposal-set", "proposal-selection",
        }.issubset(ARTIFACTS[1]))

    def test_positive_manifests_and_only_eight_stage_three_roles(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for stage in (1, 2, 3):
                manifest = build_manifest(root, stage)
                self.assertEqual(validate(manifest, stage, trusted_root_payload()), [])
            data = json.loads((root / "stage3-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual({item["role_id"] for item in data["reviews"]}, ROLES[3])
            self.assertEqual(len(data["reviews"]), 8)
            self.assertNotIn("stage_reviews", data)

    def test_dynamic_role_requires_matching_plan_and_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = build_manifest(root, 1, ("ADDITIONAL-GEOMETRY",))
            self.assertEqual(validate(manifest, 1, trusted_root_payload()), [])
            data = json.loads(manifest.read_text(encoding="utf-8"))
            workflow_item = next(
                item for item in data["artifacts"]
                if item["id"] == "stage-workflow-record"
            )
            workflow_path = root / workflow_item["path"]
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            workflow["review_plan"]["additional_role_ids"] = []
            write_json(workflow_path, workflow)
            update_workflow_hash(root, manifest)
            errors = validate(manifest, 1, trusted_root_payload())
            self.assertTrue(any("review role plan" in error for error in errors))

    def test_tampered_artifact_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = build_manifest(root, 1)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            path = root / next(
                item["path"] for item in data["artifacts"]
                if item["id"] == "task-matrix"
            )
            path.write_text("tampered", encoding="utf-8")
            self.assertTrue(any(
                "SHA-256 mismatch" in error
                for error in validate(manifest, 1, trusted_root_payload())
            ))

    def test_execution_record_change_invalidates_frozen_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = build_manifest(root, 1)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            item = next(
                value for value in data["artifacts"]
                if value["id"] == "execution-record"
            )
            path = root / item["path"]
            execution = json.loads(path.read_text(encoding="utf-8"))
            execution["post_review_mutation"] = True
            write_json(path, execution)
            item["sha256"] = hash_file(path)
            write_json(manifest, data)
            errors = validate(manifest, 1, trusted_root_payload())
            self.assertTrue(any(
                "version-index must exactly cover" in error
                for error in errors
            ))

    def test_score_findings_and_reused_provider_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = build_manifest(root, 1)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["reviews"][0]["score"] = 99
            data["reviews"][0]["findings"] = ["one real defect"]
            data["reviews"][1]["provider_run_id"] = data["reviews"][0]["provider_run_id"]
            write_json(manifest, data)
            errors = validate(manifest, 1, trusted_root_payload())
            self.assertTrue(any("100/100" in error for error in errors))
            self.assertTrue(any("provider_run_id" in error for error in errors))

    def test_cross_timezone_and_date_only_timestamps_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = build_manifest(root, 1)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            review = data["reviews"][0]
            report_path = root / review["report_path"]
            report = json.loads(report_path.read_text(encoding="utf-8"))
            review["sealed_at"] = "2026-07-29T01:00:00+00:00"
            report["sealed_at"] = review["sealed_at"]
            write_json(report_path, report)
            review["report_sha256"] = hash_file(report_path)
            data["review_deliberation"]["started_at"] = "2026-07-29T08:30:00+08:00"
            data["gate_checks"][next(iter(GATE_CHECKS[1]))]["checked_at"] = "2026-07-29"
            write_json(manifest, data)
            errors = validate(manifest, 1, trusted_root_payload())
            self.assertTrue(any("after every initial report seal" in error for error in errors))
            self.assertTrue(any("gate_checks" in error for error in errors))

    def test_state_history_cannot_claim_review_or_pass_before_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = build_manifest(root, 1)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            item = next(
                value for value in data["artifacts"]
                if value["id"] == "stage-workflow-record"
            )
            path = root / item["path"]
            workflow = json.loads(path.read_text(encoding="utf-8"))
            workflow["state_history"] = [
                {"state": "NOT_STARTED", "at": iso(0), "actor_id": "executor"},
                {"state": "EXECUTING", "at": iso(0, 30), "actor_id": "executor"},
                {"state": "SELF_REVIEW", "at": iso(1), "actor_id": "executor"},
                {"state": "EXPERT_REVIEW", "at": iso(2), "actor_id": "executor"},
                {"state": "PASS", "at": iso(3), "actor_id": "gate"},
            ]
            write_json(path, workflow)
            update_workflow_hash(root, manifest)
            self.assertTrue(any(
                "state history does not prove PASS" in error
                for error in validate(manifest, 1, trusted_root_payload())
            ))

    def test_guide_application_is_execution_evidence_not_read_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = build_manifest(root, 1)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            item = next(
                value for value in data["artifacts"]
                if value["id"] == "execution-record"
            )
            path = root / item["path"]
            execution = json.loads(path.read_text(encoding="utf-8"))
            execution["guide_applications"] = []
            write_json(path, execution)
            update_frozen_artifact_and_version(root, manifest, "execution-record")
            self.assertTrue(any(
                "guide rules were not applied" in error
                for error in validate(manifest, 1, trusted_root_payload())
            ))

    def test_execution_contract_must_cover_every_official_question(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = build_manifest(root, 1)
            errors = validate(
                manifest,
                1,
                trusted_root_payload(question_ids=("Q1", "Q2")),
            )
            self.assertTrue(any(
                "execution contract is incomplete" in error for error in errors
            ))

    def test_non_numeric_answer_shape_is_not_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = build_manifest(root, 2)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            contract = next(
                item for item in data["artifacts"]
                if item["id"] == "result-evidence-contract"
            )
            path = root / contract["path"]
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["answer"] = {
                "question_id": "Q1",
                "answer_kind": "PROOF",
                "summary": "A non-numeric proof answer supported by the frozen artifact.",
            }
            write_json(path, payload)
            contract["sha256"] = hash_file(path)
            index = next(
                item for item in data["artifacts"] if item["id"] == "version-index"
            )
            index_path = root / index["path"]
            index_data = json.loads(index_path.read_text(encoding="utf-8"))
            member = next(
                item for item in index_data["members"]
                if item["id"] == "result-evidence-contract"
            )
            member["sha256"] = contract["sha256"]
            write_json(index_path, index_data)
            index["sha256"] = hash_file(index_path)
            data["version_id"] = hash_file(index_path)
            for review in data["reviews"]:
                review["reviewed_version_id"] = data["version_id"]
                report_path = root / review["report_path"]
                report = json.loads(report_path.read_text(encoding="utf-8"))
                report["reviewed_version_id"] = data["version_id"]
                write_json(report_path, report)
                review["report_sha256"] = hash_file(report_path)
            write_json(manifest, data)
            self.assertEqual(validate(manifest, 2, trusted_root_payload()), [])

    def test_fake_pdf_rejected_and_compact_valid_pdf_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            valid = root / "valid.pdf"
            valid.write_bytes(minimal_renderable_pdf(compact=True))
            errors: list[str] = []
            validate_pdf(valid, errors)
            self.assertEqual(errors, [])
            fake = root / "fake.pdf"
            fake.write_bytes(b"%PDF-1.4\n<< /Type/Page >>\n%%EOF\n")
            validate_pdf(fake, errors)
            self.assertTrue(any("basic PDF" in error for error in errors))

    def test_pass_can_transition_to_blocked_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = build_checkpoint(
                Path(temp),
                ["NOT_STARTED", "EXECUTING", "SELF_REVIEW", "EXPERT_REVIEW", "PASS", "BLOCKED"],
                "BLOCKED",
            )
            self.assertEqual(validate_checkpoint(path, 1), [])

    def test_resume_checkpoint_requires_blocked_to_executing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = build_checkpoint(
                Path(temp),
                ["NOT_STARTED", "EXECUTING", "BLOCKED", "EXECUTING"],
                "EXECUTING",
            )
            self.assertEqual(validate_checkpoint(path, 1), [])

    def test_checkpoint_requires_initial_state_and_completed_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = build_checkpoint(root, ["BLOCKED"], "BLOCKED")
            data = json.loads(path.read_text(encoding="utf-8"))
            data["checkpoint"]["completed_steps"] = []
            write_json(path, data)
            errors = validate_checkpoint(path, 1)
            self.assertTrue(any("state history/timing" in error for error in errors))
            self.assertTrue(any("completed-work" in error for error in errors))

    def test_cli_requires_external_trust_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            outer = Path(temp)
            package = outer / "package"
            manifest = build_manifest(package, 1)
            official = outer / "official-problem.txt"
            official.write_text("Official problem Q1.", encoding="utf-8")
            trust = outer / "trust.json"
            write_json(
                trust,
                trusted_root_payload(official.name, hash_file(official)),
            )
            environment = os.environ.copy()
            environment["PYTHONUTF8"] = "1"
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT_DIR / "check_stage_gate.py"),
                    "--manifest", str(manifest), "--stage", "1",
                    "--trusted-source-manifest", str(trust),
                ],
                text=True, capture_output=True, env=environment,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            official.write_text("tampered official problem", encoding="utf-8")
            tampered = subprocess.run(
                [
                    sys.executable, str(SCRIPT_DIR / "check_stage_gate.py"),
                    "--manifest", str(manifest), "--stage", "1",
                    "--trusted-source-manifest", str(trust),
                ],
                text=True, capture_output=True, env=environment,
            )
            self.assertNotEqual(tampered.returncode, 0)
            self.assertIn("hash-mismatched", tampered.stdout)


if __name__ == "__main__":
    unittest.main()
