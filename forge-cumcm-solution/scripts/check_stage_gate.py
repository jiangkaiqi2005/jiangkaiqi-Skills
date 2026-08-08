#!/usr/bin/env python3
"""Lean mechanical gate for the three-stage CUMCM workflow.

This script protects provenance, ordering, review independence and visibility.
It deliberately does not judge mathematical quality or force one answer shape;
the stage instructions and independent reviewers own semantic judgment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from gate_common import (
    instant_after, instant_equal, parse_instant,
)


HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
GUIDE_SHA256 = "c90b0294a83f6b20995f499c309fa5d2c988cf110ae67aa8f27f543325ffea82"
WORKFLOW_STEPS = (
    "LOAD_GUIDE",
    "BUILD_EXECUTION_CONTRACT",
    "HIGH_QUALITY_EXECUTION",
    "EXECUTOR_SELF_REVIEW",
    "FREEZE_CANDIDATE",
    "INDEPENDENT_BLIND_REVIEW",
)
VISIBILITY_BY_STAGE_STATUS = {
    "NOT_STARTED": "INTERNAL_WORKING",
    "EXECUTING": "INTERNAL_WORKING",
    "SELF_REVIEW": "INTERNAL_SELF_REVIEW",
    "EXPERT_REVIEW": "INTERNAL_EXPERT_REVIEW",
    "REVISION": "INTERNAL_REVISION",
    "BLOCKED": "BLOCKED",
    "PASS": "USER_VISIBLE_PASS",
}
ROLES = {
    1: {
        "S1-JUDGE", "S1-DOMAIN", "S1-PROBLEM", "S1-RIGOR",
        "S1-INNOVATION", "S1-IDENTIFIABILITY", "S1-SIMPLE", "S1-REDTEAM",
    },
    2: {
        "S2-NUMERICAL", "S2-ENGINEERING", "S2-EXPERIMENT", "S2-DATA",
        "S2-PERFORMANCE", "S2-REPRODUCIBILITY", "S2-VISUALIZATION",
        "S2-MODEL-CODE",
    },
    3: {
        "S3-JUDGE", "S3-ARGUMENT", "S3-ABSTRACT", "S3-VISUAL",
        "S3-CONSISTENCY", "S3-CITATION-COMPLIANCE", "S3-TYPESETTING",
        "S3-ANON-REDTEAM",
    },
}
ARTIFACTS = {
    1: {
        "input-inventory", "research-record", "proposal-input-packet",
        "proposal-set", "proposal-selection", "task-matrix",
        "core-mechanism", "assumption-register", "model-interfaces",
        "method-map", "risk-register", "stage1-contract",
        "modeling-summary", "version-index", "execution-record",
        "stage-workflow-record",
    },
    2: {
        "research-record", "code-bundle", "run-commands",
        "result-files", "constraint-certificate", "independent-validation",
        "sensitivity-analysis", "number-ledger", "figures-manifest",
        "reproduction-record", "data-validity-audit",
        "result-evidence-contract", "execution-record", "version-index",
        "stage-workflow-record",
    },
    3: {
        "research-record", "editable-paper", "final-pdf",
        "consistency-audit", "submission-inventory", "integrity-audit",
        "paper-evidence-contract", "execution-record", "version-index",
        "stage-workflow-record",
    },
}
GATE_CHECKS = {
    1: {
        "inputs_readable", "official_rules_checked", "task_closed",
        "interfaces_closed", "method_feasible",
    },
    2: {
        "baseline_passed", "all_questions_answered", "constraints_passed",
        "independent_validation_passed", "core_results_reproduced",
        "numbers_consistent", "data_validity_closed",
    },
    3: {
        "official_template_checked", "all_questions_present",
        "numbers_consistent", "render_review_passed", "submission_complete",
        "integrity_passed",
    },
}
GUIDE_SECTIONS = {
    1: {"0", "1", "2", "8", "9", "10", "23", "24"},
    2: {"0", "3", "4", "8", "9", "10", "23", "24"},
    3: {"0", "5", "6", "7", "9", "10", "23", "24"},
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest().lower()


def normalized_id(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        return None
    return value.casefold()


def load_json(path: Path, label: str, errors: list[str]) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label}: invalid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label}: root must be an object")
        return None
    return value


def safe_file(root: Path, relative: object, label: str, errors: list[str]) -> Path | None:
    if not isinstance(relative, str) or not relative:
        errors.append(f"{label}: relative path is required")
        return None
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        errors.append(f"{label}: path must stay inside the work package")
        return None
    resolved = (root / raw).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label}: path escapes the work package")
        return None
    if not resolved.is_file():
        errors.append(f"{label}: file not found")
        return None
    return resolved


def validate_pdf(path: Path, errors: list[str]) -> None:
    content = path.read_bytes()
    patterns = (
        rb"/Type\s*/Catalog\b", rb"/Type\s*/Pages\b",
        rb"/Type\s*/Page\b", rb"/Count\s+[1-9]\d*\b",
    )
    if (
        path.suffix.lower() != ".pdf"
        or len(content) < 512
        or not content.startswith(b"%PDF-")
        or b"%%EOF" not in content[-1024:]
        or any(re.search(pattern, content) is None for pattern in patterns)
        or b"stream" not in content
        or b"startxref" not in content
    ):
        errors.append("final-pdf: basic PDF/page-tree structure is invalid")


def validate_trust_payload(
    trust: dict, errors: list[str], source_root: Path | None = None,
) -> None:
    attestations = trust.get("attestations")
    reviewer_ids = {
        normalized_id(item.get("reviewer_id"))
        for item in attestations or [] if isinstance(item, dict)
    }
    provider_ids = {
        normalized_id(item.get("provider_run_id"))
        for item in attestations or [] if isinstance(item, dict)
    }
    files = trust.get("official_files")
    questions = trust.get("official_question_ids")
    if (
        trust.get("schema_version") != "1.0"
        or not isinstance(questions, list)
        or not questions
        or len(set(questions)) != len(questions)
        or not isinstance(attestations, list)
        or len(attestations) < 2
        or None in reviewer_ids
        or None in provider_ids
        or len(reviewer_ids) < 2
        or len(provider_ids) < 2
        or not isinstance(files, list)
        or not files
    ):
        errors.append(
            "trusted-source-manifest: official files, questions, and two "
            "independent attestations are required"
        )
        return
    for index, item in enumerate(files):
        label = f"trusted-source-manifest.official_files[{index}]"
        attested_by = {
            normalized_id(value) for value in item.get("attested_by", [])
        } if isinstance(item, dict) else set()
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not item["id"].strip()
            or not isinstance(item.get("kind"), str)
            or not item["kind"].strip()
            or not isinstance(item.get("path"), str)
            or not item["path"].strip()
            or not isinstance(item.get("sha256"), str)
            or not HEX64.fullmatch(item["sha256"])
            or not isinstance(item.get("question_ids"), list)
            or not set(item["question_ids"]).issubset(set(questions))
            or len(attested_by) < 2
            or not attested_by.issubset(reviewer_ids)
        ):
            errors.append(f"{label}: file identity/hash/attestations are incomplete")
            continue
        if source_root is not None:
            raw = Path(item["path"])
            resolved = (source_root / raw).resolve()
            try:
                resolved.relative_to(source_root.resolve())
            except ValueError:
                errors.append(f"{label}: path escapes the trust-root directory")
                continue
            if not resolved.is_file() or digest(resolved) != item["sha256"].lower():
                errors.append(f"{label}: official file is missing or hash-mismatched")


def read_trust_root(path: Path | None, package_root: Path, errors: list[str]) -> dict | None:
    if path is None or not path.is_file():
        errors.append("trusted-source-manifest is required")
        return None
    try:
        path.resolve().relative_to(package_root.resolve())
    except ValueError:
        pass
    else:
        errors.append("trusted-source-manifest must be outside the work package")
        return None
    trust = load_json(path, "trusted-source-manifest", errors)
    if trust is None:
        return None
    validate_trust_payload(trust, errors, path.parent)
    return trust


def collect_files(
    data: dict, root: Path, stage: int, errors: list[str],
) -> tuple[dict[str, Path], dict[str, Path], set[str]]:
    inputs: dict[str, Path] = {}
    artifacts: dict[str, Path] = {}
    frozen_paths: set[str] = set()
    for group_name, target in (("inputs", inputs), ("artifacts", artifacts)):
        group = data.get(group_name)
        if not isinstance(group, list) or not group:
            errors.append(f"{group_name} must be a non-empty list")
            continue
        for index, item in enumerate(group):
            label = f"{group_name}[{index}]"
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                errors.append(f"{label}: id/object is invalid")
                continue
            item_id = item["id"]
            if item_id in target:
                errors.append(f"{label}: duplicate id {item_id}")
                continue
            path = safe_file(root, item.get("path"), label, errors)
            if path is None:
                continue
            expected = item.get("sha256")
            if (
                not isinstance(expected, str)
                or HEX64.fullmatch(expected) is None
                or digest(path) != expected.lower()
            ):
                errors.append(f"{label}: SHA-256 mismatch")
            if path.stat().st_size == 0:
                errors.append(f"{label}: file must not be empty")
            if group_name == "artifacts":
                expected_status = "OPERATIONAL" if item_id == "stage-workflow-record" else "VERIFIED"
                if item.get("status") != expected_status:
                    errors.append(f"{label}: artifact status must be {expected_status}")
            target[item_id] = path
            if item_id not in {"version-index", "stage-workflow-record"}:
                frozen_paths.add(item["path"])
    missing = ARTIFACTS[stage] - set(artifacts)
    if missing:
        errors.append(f"missing required artifacts: {', '.join(sorted(missing))}")
    return inputs, artifacts, frozen_paths


def validate_version_index(
    path: Path, data: dict, stage: int, root: Path, errors: list[str],
) -> None:
    index = load_json(path, "version-index", errors)
    if index is None:
        return
    expected: list[dict[str, str]] = []
    for group_name, kind in (("inputs", "input"), ("artifacts", "artifact")):
        for item in data.get(group_name, []):
            if (
                isinstance(item, dict)
                and item.get("id") not in {"version-index", "stage-workflow-record"}
                and all(isinstance(item.get(key), str) for key in ("id", "path", "sha256"))
            ):
                expected.append({
                    "kind": kind,
                    "id": item["id"],
                    "path": item["path"],
                    "sha256": item["sha256"].lower(),
                })
    expected.sort(key=lambda item: (item["path"], item["kind"], item["id"]))
    if (
        index.get("schema_version") != "1.0"
        or index.get("stage") != stage
        or index.get("members") != expected
    ):
        errors.append("version-index must exactly cover the frozen inputs and artifacts")
    version = data.get("version_id")
    if not isinstance(version, str) or HEX64.fullmatch(version) is None:
        errors.append("version_id must be a SHA-256")
    elif digest(path) != version.lower():
        errors.append("version_id must equal the SHA-256 of version-index")


def validate_evidence_location(
    root: Path, location: object, frozen_paths: set[str], errors: list[str],
) -> None:
    if not isinstance(location, str) or "#" not in location:
        errors.append("review evidence location must use relative/path#locator")
        return
    relative, locator = location.split("#", 1)
    if relative not in frozen_paths:
        errors.append(f"review evidence is not frozen: {relative}")
        return
    path = safe_file(root, relative, "review evidence", errors)
    if path is None:
        return
    line_match = re.fullmatch(r"L(\d+)(?:-L(\d+))?", locator)
    if line_match:
        start = int(line_match.group(1))
        end = int(line_match.group(2) or start)
        if not (1 <= start <= end <= len(path.read_bytes().splitlines())):
            errors.append(f"review evidence line locator is invalid: {location}")
        return
    if not locator.startswith("/"):
        errors.append(f"review evidence locator is invalid: {location}")
        return
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"))
        for raw in locator[1:].split("/"):
            token = raw.replace("~1", "/").replace("~0", "~")
            value = value[int(token)] if isinstance(value, list) else value[token]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
        errors.append(f"review evidence JSON pointer is invalid: {location}")


def validate_reviews(
    data: dict, root: Path, stage: int, version: str,
    frozen_paths: set[str], errors: list[str],
) -> tuple[set[str], set[str], list[object], set[str]]:
    reviews = data.get("reviews")
    if not isinstance(reviews, list):
        errors.append("reviews must be a list")
        return set(), set(), [], set()
    roles: list[str] = []
    reviewers: set[str] = set()
    providers: set[str] = set()
    sealed: list[object] = []
    for index, review in enumerate(reviews):
        label = f"reviews[{index}]"
        if not isinstance(review, dict):
            errors.append(f"{label}: must be an object")
            continue
        role = review.get("role_id")
        reviewer = normalized_id(review.get("reviewer_id"))
        provider = normalized_id(review.get("provider_run_id"))
        if not isinstance(role, str):
            errors.append(f"{label}: role_id is invalid")
            continue
        roles.append(role)
        if reviewer is None or reviewer in reviewers:
            errors.append(f"{label}: reviewer_id is invalid or reused")
        else:
            reviewers.add(reviewer)
        if provider is None or provider in providers:
            errors.append(f"{label}: provider_run_id is invalid or reused")
        else:
            providers.add(provider)
        instant = parse_instant(review.get("sealed_at"))
        if instant is None:
            errors.append(f"{label}: sealed_at must be a complete timezone-aware instant")
        else:
            sealed.append(instant)
        if (
            review.get("score") != 100
            or review.get("criteria") != [20, 20, 20, 20, 20]
            or review.get("findings") != []
            or review.get("vetoes") != []
            or review.get("reviewed_version_id") != version
        ):
            errors.append(f"{label}: only a defect-free 100/100 report can pass")
        independence = review.get("independence")
        if not isinstance(independence, dict) or any(
            independence.get(field) is not True
            for field in (
                "did_not_modify", "did_not_view_other_reviews",
                "received_only_allowed_inputs",
                "initial_score_sealed_before_deliberation",
            )
        ):
            errors.append(f"{label}: independence declaration is incomplete")
        report = safe_file(root, review.get("report_path"), f"{label}.report", errors)
        if report is None:
            continue
        report_hash = review.get("report_sha256")
        if (
            not isinstance(report_hash, str)
            or HEX64.fullmatch(report_hash) is None
            or digest(report) != report_hash.lower()
        ):
            errors.append(f"{label}: report SHA-256 mismatch")
        report_data = load_json(report, f"{label}.report", errors)
        if report_data is None:
            continue
        criteria = report_data.get("criteria")
        if (
            report_data.get("role_id") != role
            or normalized_id(report_data.get("reviewer_id")) != reviewer
            or normalized_id(report_data.get("provider_run_id")) != provider
            or report_data.get("reviewed_version_id") != version
            or report_data.get("conclusion") != "PASS"
            or not instant_equal(report_data.get("sealed_at"), review.get("sealed_at"))
            or not isinstance(criteria, list)
            or len(criteria) != 5
            or any(
                not isinstance(item, dict)
                or item.get("score") != 20
                or not isinstance(item.get("justification"), str)
                or len(item["justification"].strip()) < 40
                or not isinstance(item.get("evidence_locations"), list)
                or not item["evidence_locations"]
                for item in criteria
            )
            or any(
                report_data.get(field) != []
                for field in (
                    "fatal_findings", "major_findings", "minor_findings",
                    "missing_evidence",
                )
            )
        ):
            errors.append(f"{label}: report content is incomplete or inconsistent")
            continue
        locations = [
            location
            for item in criteria
            for location in item["evidence_locations"]
        ]
        for location in locations:
            validate_evidence_location(root, location, frozen_paths, errors)
        if len({location.split("#", 1)[0] for location in locations if "#" in location}) < 3:
            errors.append(f"{label}: evidence must span at least three frozen artifacts")
        if review.get("evidence_locations") != locations:
            errors.append(f"{label}: manifest/report evidence locations must match")
    role_set = set(roles)
    if len(roles) != len(role_set):
        errors.append("review roles must not repeat")
    if not ROLES[stage].issubset(role_set):
        errors.append("review role set is missing a required stage role")
    if any(role not in ROLES[stage] and not role.startswith("ADDITIONAL-") for role in role_set):
        errors.append("dynamic roles must use ADDITIONAL-* IDs")
    return reviewers, providers, sealed, role_set


def validate_deliberation(
    data: dict, root: Path, role_set: set[str], sealed: list[object],
    errors: list[str],
) -> object | None:
    record = data.get("review_deliberation")
    if not isinstance(record, dict):
        errors.append("review_deliberation must be an object")
        return None
    path = safe_file(root, record.get("path"), "review_deliberation", errors)
    expected = record.get("sha256")
    if (
        path is None
        or not isinstance(expected, str)
        or HEX64.fullmatch(expected) is None
        or digest(path) != expected.lower()
    ):
        errors.append("review_deliberation file/hash is invalid")
    started = parse_instant(record.get("started_at"))
    if started is None or not sealed or any(started <= value for value in sealed):
        errors.append("review_deliberation must start after every initial report seal")
    if set(record.get("participant_roles", [])) != role_set:
        errors.append("review_deliberation participants must match review roles")
    if record.get("unresolved_findings") != []:
        errors.append("review_deliberation unresolved_findings must be empty")
    questions = record.get("cross_questions")
    if (
        not isinstance(questions, list)
        or {
            item.get("raised_by_role") for item in questions if isinstance(item, dict)
        } != role_set
        or any(
            not isinstance(item, dict)
            or item.get("status") != "CLOSED"
            or not isinstance(item.get("resolution"), str)
            or len(item["resolution"].strip()) < 20
            for item in questions
        )
    ):
        errors.append("review_deliberation cross-questions are incomplete")
    return started


def validate_execution_record(
    path: Path, stage: int, artifact_ids: set[str],
    role_set: set[str], official_question_ids: set[str], errors: list[str],
) -> object | None:
    record = load_json(path, "execution-record", errors)
    if record is None:
        return None
    if (
        record.get("schema_version") != "1.0"
        or record.get("stage") != stage
        or str(record.get("guide_snapshot_sha256", "")).lower() != GUIDE_SHA256
        or not GUIDE_SECTIONS[stage].issubset(set(record.get("guide_sections", [])))
    ):
        errors.append("execution-record: guide identity/sections are incomplete")
    applications = record.get("guide_applications")
    if (
        not isinstance(applications, list)
        or not applications
        or any(
            not isinstance(item, dict)
            or not isinstance(item.get("guide_section"), str)
            or not isinstance(item.get("current_task_action"), str)
            or not set(item.get("evidence_artifact_ids", [])).issubset(artifact_ids)
            or not item.get("evidence_artifact_ids")
            for item in applications
        )
    ):
        errors.append("execution-record: guide rules were not applied to execution")
    contract = record.get("execution_contract")
    contract_questions = [
        item.get("question_id")
        for item in contract or [] if isinstance(item, dict)
    ]
    if (
        not isinstance(contract, list)
        or not contract
        or len(contract_questions) != len(set(contract_questions))
        or set(contract_questions) != official_question_ids
        or any(
            not isinstance(item, dict)
            or not isinstance(item.get("question_id"), str)
            or not item["question_id"].strip()
            or not isinstance(item.get("task"), str)
            or not isinstance(item.get("acceptance"), str)
            or item.get("status") != "COMPLETE"
            or not set(item.get("evidence_artifact_ids", [])).issubset(artifact_ids)
            or not item.get("evidence_artifact_ids")
            for item in contract
        )
    ):
        errors.append("execution-record: execution contract is incomplete")
    self_review = record.get("self_review")
    self_roles = self_review.get("roles") if isinstance(self_review, dict) else None
    if (
        not isinstance(self_roles, list)
        or {item.get("role_id") for item in self_roles if isinstance(item, dict)} != role_set
        or any(
            not isinstance(item, dict)
            or item.get("criteria") != [20, 20, 20, 20, 20]
            or item.get("findings") != []
            or not set(item.get("evidence_artifact_ids", [])).issubset(artifact_ids)
            or not item.get("evidence_artifact_ids")
            for item in self_roles
        )
    ):
        errors.append("execution-record: executor self-review is incomplete")
    steps = record.get("steps")
    step_times: list[object] = []
    expected_steps = WORKFLOW_STEPS[:5]
    if (
        not isinstance(steps, list)
        or [item.get("name") if isinstance(item, dict) else None for item in steps]
        != list(expected_steps)
    ):
        errors.append("execution-record: five pre-review milestones are required")
    else:
        for item in steps:
            instant = parse_instant(item.get("completed_at"))
            if instant is None:
                errors.append("execution-record: milestone time is invalid")
            step_times.append(instant)
        if any(
            left is None or right is None or left >= right
            for left, right in zip(step_times, step_times[1:])
        ):
            errors.append("execution-record: milestone times are not ordered")
    frozen_at = record.get("candidate_frozen_at")
    if (
        len(step_times) != len(expected_steps)
        or not instant_equal(
            frozen_at,
            steps[4].get("completed_at") if isinstance(steps, list) else None,
        )
    ):
        errors.append("execution-record: candidate freeze time is invalid")
    return frozen_at


def validate_workflow(
    path: Path, stage: int, artifact_ids: set[str], role_set: set[str],
    sealed: list[object], deliberation_started: object | None,
    frozen_at: object | None, errors: list[str],
) -> None:
    record = load_json(path, "stage-workflow-record", errors)
    if record is None:
        return
    plan = record.get("review_plan")
    if (
        record.get("schema_version") != "1.0"
        or record.get("stage") != stage
        or not isinstance(plan, dict)
        or set(plan.get("required_role_ids", [])) != ROLES[stage]
        or set(plan.get("additional_role_ids", [])) != (role_set - ROLES[stage])
    ):
        errors.append("stage-workflow-record: review role plan is incomplete")
    review_started = record.get("review_started_at")
    review_completed = record.get("review_completed_at")
    if (
        not instant_after(review_started, frozen_at)
        or deliberation_started is None
        or any(value <= parse_instant(review_started) for value in sealed)
        or parse_instant(review_completed) is None
        or parse_instant(review_completed) < deliberation_started
    ):
        errors.append("stage-workflow-record: freeze/review/deliberation order is invalid")


def collect_prior_identity(
    path: Path, field: str, errors: list[str], visited: set[Path] | None = None,
) -> set[str]:
    visited = visited or set()
    resolved = path.resolve()
    if resolved in visited:
        errors.append("prior_stage chain contains a cycle")
        return set()
    visited.add(resolved)
    data = load_json(resolved, "prior_stage", errors)
    if data is None:
        return set()
    values = {
        normalized_id(item.get(field))
        for item in data.get("reviews", []) if isinstance(item, dict)
    }
    result = {value for value in values if value is not None}
    prior = data.get("prior_stage")
    if isinstance(prior, dict):
        prior_path = safe_file(resolved.parent, prior.get("manifest_path"), "prior_stage", errors)
        if prior_path is not None:
            result.update(collect_prior_identity(prior_path, field, errors, visited))
    return result


def validate_prior_stage(
    manifest_path: Path, data: dict, stage: int,
    reviewers: set[str], providers: set[str], trust_root: Path | dict,
    errors: list[str],
) -> None:
    if stage == 1:
        return
    prior = data.get("prior_stage")
    if not isinstance(prior, dict):
        errors.append("prior_stage is required")
        return
    prior_path = safe_file(
        manifest_path.parent, prior.get("manifest_path"), "prior_stage", errors
    )
    if prior_path is None:
        return
    if (
        not isinstance(prior.get("sha256"), str)
        or digest(prior_path) != prior["sha256"].lower()
    ):
        errors.append("prior_stage SHA-256 mismatch")
    prior_data = load_json(prior_path, "prior_stage", errors)
    if (
        prior_data is None
        or prior_data.get("stage") != stage - 1
        or prior_data.get("stage_status") != "PASS"
        or prior_data.get("visibility_status") != "USER_VISIBLE_PASS"
        or prior_data.get("version_id") != prior.get("version_id")
    ):
        errors.append("prior_stage is not a matching visible PASS")
    if reviewers.intersection(
        collect_prior_identity(prior_path, "reviewer_id", errors)
    ):
        errors.append("reviewer_id values must be disjoint across stages")
    if providers.intersection(
        collect_prior_identity(prior_path, "provider_run_id", errors)
    ):
        errors.append("provider_run_id values must be disjoint across stages")
    for error in validate(prior_path, stage - 1, trust_root):
        errors.append(f"prior_stage: {error}")


def validate(
    manifest_path: Path, expected_stage: int,
    trust_root_path: Path | dict | None = None,
) -> list[str]:
    errors: list[str] = []
    data = load_json(manifest_path, "manifest", errors)
    if data is None:
        return errors
    root = manifest_path.parent.resolve()
    if (
        data.get("schema_version") != "1.0"
        or data.get("stage") != expected_stage
    ):
        errors.append("manifest schema_version/stage mismatch")
    stage_status = data.get("stage_status")
    visibility = data.get("visibility_status")
    if stage_status != "PASS" or visibility != "USER_VISIBLE_PASS":
        errors.append("PASS gate requires PASS and USER_VISIBLE_PASS")
    if visibility != VISIBILITY_BY_STAGE_STATUS.get(stage_status):
        errors.append("stage_status/visibility_status mismatch")
    if data.get("blockers") != []:
        errors.append("PASS gate requires an empty blockers list")
    trust_path = trust_root_path if isinstance(trust_root_path, Path) else None
    trust = (
        trust_root_path
        if isinstance(trust_root_path, dict)
        else read_trust_root(trust_path, root, errors)
    )
    if not isinstance(trust, dict):
        return errors
    if isinstance(trust_root_path, dict):
        validate_trust_payload(trust, errors)
    inputs, artifacts, frozen_paths = collect_files(data, root, expected_stage, errors)
    if "version-index" in artifacts:
        validate_version_index(
            artifacts["version-index"], data, expected_stage, root, errors
        )
    if expected_stage == 3 and "final-pdf" in artifacts:
        validate_pdf(artifacts["final-pdf"], errors)
    checks = data.get("gate_checks")
    if not isinstance(checks, dict) or set(checks) != GATE_CHECKS[expected_stage]:
        errors.append("gate_checks must exactly cover the stage checks")
    else:
        for key, item in checks.items():
            if (
                not isinstance(item, dict)
                or item.get("passed") is not True
                or parse_instant(item.get("checked_at")) is None
                or not isinstance(item.get("validator_id"), str)
                or not item["validator_id"].strip()
                or not set(item.get("evidence_artifact_ids", [])).issubset(
                    set(artifacts) - {"stage-workflow-record"}
                )
                or not item.get("evidence_artifact_ids")
            ):
                errors.append(f"gate_checks.{key} is incomplete")
    version = data.get("version_id")
    reviewers, providers, sealed, role_set = validate_reviews(
        data, root, expected_stage, str(version), frozen_paths, errors
    )
    deliberation_started = validate_deliberation(
        data, root, role_set, sealed, errors
    )
    execution_record = artifacts.get("execution-record")
    frozen_at = None
    if execution_record is not None:
        frozen_at = validate_execution_record(
            execution_record, expected_stage, set(artifacts), role_set,
            set(trust.get("official_question_ids", [])), errors,
        )
    workflow = artifacts.get("stage-workflow-record")
    if workflow is not None:
        validate_workflow(
            workflow, expected_stage, set(artifacts), role_set,
            sealed, deliberation_started, frozen_at, errors,
        )
    validate_prior_stage(
        manifest_path, data, expected_stage, reviewers, providers,
        trust_root_path if isinstance(trust_root_path, (Path, dict)) else trust,
        errors,
    )
    return errors


def validate_checkpoint(manifest_path: Path, expected_stage: int) -> list[str]:
    errors: list[str] = []
    data = load_json(manifest_path, "checkpoint", errors)
    if data is None:
        return errors
    state = data.get("stage_status")
    if (
        data.get("schema_version") != "1.0"
        or data.get("stage") != expected_stage
        or state == "PASS"
        or state not in VISIBILITY_BY_STAGE_STATUS
        or data.get("visibility_status") != VISIBILITY_BY_STAGE_STATUS.get(state)
    ):
        errors.append("checkpoint must use a valid non-PASS state/visibility")
    checkpoint = data.get("checkpoint")
    if not isinstance(checkpoint, dict):
        errors.append("checkpoint object is required")
        return errors
    if (
        parse_instant(checkpoint.get("saved_at")) is None
        or not isinstance(checkpoint.get("next_action"), str)
        or not checkpoint["next_action"].strip()
        or checkpoint.get("resume_from") not in VISIBILITY_BY_STAGE_STATUS
        or checkpoint.get("resume_from") == "PASS"
    ):
        errors.append("checkpoint saved_at/next_action/resume_from are incomplete")
    blockers = data.get("blockers")
    if state == "BLOCKED":
        if (
            not isinstance(blockers, list)
            or not blockers
            or any(
                not isinstance(item, dict)
                or not all(
                    isinstance(item.get(field), str) and item[field].strip()
                    for field in (
                        "category", "reason", "required_material",
                        "resume_condition",
                    )
                )
                or not isinstance(item.get("affected_ids"), list)
                or not item["affected_ids"]
                for item in blockers
            )
        ):
            errors.append("BLOCKED checkpoint requires non-empty structured blockers")
    elif blockers:
        errors.append("non-BLOCKED checkpoint cannot carry blockers")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("stage-manifest.json"))
    parser.add_argument("--stage", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--trusted-source-manifest", type=Path)
    parser.add_argument("--checkpoint", action="store_true")
    args = parser.parse_args()
    manifest = args.manifest.resolve()
    if args.checkpoint:
        errors = validate_checkpoint(manifest, args.stage)
        prefix = "BLOCKED"
    else:
        errors = validate(
            manifest,
            args.stage,
            args.trusted_source_manifest.resolve()
            if args.trusted_source_manifest else None,
        )
        prefix = "BLOCKED"
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"{prefix}: {len(errors)} stage gate issue(s)")
        return 1
    if args.checkpoint:
        print("BLOCKED: checkpoint is valid and resumable; stage PASS is not granted")
        return 1
    print(f"PASS: stage {args.stage} mechanical gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
