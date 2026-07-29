#!/usr/bin/env python3
"""Validate a frozen Skill-development review package.

Passing is necessary, not sufficient: this script verifies structure, hashes,
evidence and ordering, while independent reviewers remain responsible for
semantic judgment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from gate_common import parse_instant

HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
LOCATOR = re.compile(r"^L(\d+)(?:-L(\d+))?$")
REQUIRED_ROLES = {
    "SKILL-ARCHITECTURE", "SKILL-INSTRUCTION", "SKILL-CUMCM-JUDGE",
    "SKILL-GUIDE-FIDELITY", "SKILL-WORKFLOW", "SKILL-REVIEW-DESIGN",
    "SKILL-GATE", "SKILL-EXECUTABILITY", "SKILL-TESTING",
    "SKILL-EVIDENCE", "SKILL-CONTEXT", "SKILL-REDTEAM",
}
REQUIRED_EVIDENCE = {
    "file-tree", "change-record", "test-log", "e2e-log", "known-limitations",
}
REQUIRED_VALIDATIONS = {
    "official-quick-validate", "custom-validate", "unit-regression",
    "e2e-simulation",
}
REQUIRED_SIMULATIONS = {
    "new-problem-three-stages", "continue-from-modeling",
    "continue-from-code", "paper-submission-review",
    "stage2-rollback-to-stage1", "stage3-rollback-to-stage2",
    "missing-official-material-blocked", "review-score-blocks-advance",
    "artifact-change-invalidates-pass", "resume-after-interruption",
}
IGNORED_PARTS = {"__pycache__", ".pytest_cache"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest().lower()


def normalized_id(value: object) -> str | None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
    ):
        return None
    return value.casefold()


def parse_time(value: object) -> object | None:
    return parse_instant(value)


def safe_file(root: Path, relative: object) -> Path | None:
    if not isinstance(relative, str) or not relative:
        return None
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        return None
    resolved = (root / raw).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    return resolved if resolved.is_file() else None


def substantive_skill_files(skill_root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in skill_root.rglob("*"):
        if (
            not path.is_file()
            or any(part in IGNORED_PARTS for part in path.parts)
            or path.suffix.lower() == ".pyc"
        ):
            continue
        relative = path.relative_to(skill_root).as_posix()
        result[relative] = digest(path)
    return result


def validate_locator(
    skill_root: Path, location: object, frozen_paths: set[str],
) -> bool:
    if not isinstance(location, str) or "#" not in location:
        return False
    relative, locator = location.split("#", 1)
    if relative not in frozen_paths:
        return False
    path = safe_file(skill_root, relative)
    if path is None or path.stat().st_size == 0:
        return False
    line_match = LOCATOR.fullmatch(locator)
    if line_match:
        start = int(line_match.group(1))
        end = int(line_match.group(2) or start)
        return 1 <= start <= end <= len(path.read_bytes().splitlines())
    if not locator.startswith("/"):
        return False
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"))
        for raw_token in locator[1:].split("/"):
            token = raw_token.replace("~1", "/").replace("~0", "~")
            value = value[int(token)] if isinstance(value, list) else value[token]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError,
            IndexError, ValueError, TypeError):
        return False
    return True


def validate(manifest_path: Path, skill_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"cannot read manifest: {exc}"]
    if not isinstance(data, dict):
        return ["manifest root must be an object"]
    workspace = manifest_path.parent.resolve()
    if skill_root is None or not skill_root.is_dir():
        errors.append("skill_root is required and must be a directory")
        return errors
    skill_root = skill_root.resolve()

    if data.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    if data.get("status") != "SKILL_DEVELOPMENT_PASS":
        errors.append("status must be SKILL_DEVELOPMENT_PASS")
    version_id = data.get("version_id")
    if not isinstance(version_id, str) or not HEX64.fullmatch(version_id):
        errors.append("version_id must be a 64-hex SHA-256")

    evidence_items = data.get("development_evidence")
    evidence_by_id: dict[str, dict] = {}
    if not isinstance(evidence_items, list):
        errors.append("development_evidence must be a list")
    else:
        for index, item in enumerate(evidence_items):
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                errors.append(f"development_evidence[{index}] is invalid")
                continue
            evidence_by_id[item["id"]] = item
            path = safe_file(workspace, item.get("path"))
            expected = item.get("sha256")
            if path is None or path.stat().st_size == 0:
                errors.append(f"development_evidence[{index}] file is missing/empty")
            elif not isinstance(expected, str) or not HEX64.fullmatch(expected):
                errors.append(f"development_evidence[{index}] sha256 is invalid")
            elif digest(path) != expected.lower():
                errors.append(f"development_evidence[{index}] sha256 mismatch")
        missing = REQUIRED_EVIDENCE - set(evidence_by_id)
        if missing:
            errors.append(f"missing development evidence: {', '.join(sorted(missing))}")

    version_index_path = safe_file(workspace, data.get("version_index_path"))
    frozen_skill_paths: set[str] = set()
    if version_index_path is None:
        errors.append("version index file not found")
    else:
        if isinstance(version_id, str) and HEX64.fullmatch(version_id):
            if digest(version_index_path) != version_id.lower():
                errors.append("version_id does not match version index hash")
        try:
            version_index = json.loads(version_index_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"version index is invalid: {exc}")
            version_index = {}
        members = version_index.get("members") if isinstance(version_index, dict) else None
        if (
            not isinstance(version_index, dict)
            or version_index.get("schema_version") != "1.0"
            or not isinstance(members, list)
        ):
            errors.append("version index must be schema_version 1.0 with members")
        else:
            indexed_skill: dict[str, str] = {}
            indexed_evidence: dict[str, str] = {}
            seen_keys: set[tuple[str, str]] = set()
            for index, member in enumerate(members):
                if not isinstance(member, dict):
                    errors.append(f"version index member[{index}] is invalid")
                    continue
                scope, relative, expected = (
                    member.get("scope"), member.get("path"), member.get("sha256")
                )
                key = (str(scope), str(relative))
                if key in seen_keys:
                    errors.append(f"version index member[{index}] is duplicated")
                seen_keys.add(key)
                if not isinstance(expected, str) or not HEX64.fullmatch(expected):
                    errors.append(f"version index member[{index}] sha256 is invalid")
                    continue
                if scope == "skill":
                    path = safe_file(skill_root, relative)
                    if path is None or digest(path) != expected.lower():
                        errors.append(f"version index skill member mismatch: {relative}")
                    elif isinstance(relative, str):
                        indexed_skill[relative] = expected.lower()
                        frozen_skill_paths.add(relative)
                elif scope == "review":
                    path = safe_file(workspace, relative)
                    if path is None or digest(path) != expected.lower():
                        errors.append(f"version index review member mismatch: {relative}")
                    elif isinstance(relative, str):
                        indexed_evidence[relative] = expected.lower()
                else:
                    errors.append(f"version index member[{index}] has invalid scope")
            if indexed_skill != substantive_skill_files(skill_root):
                errors.append("version index must exactly cover all substantive Skill files")
            required_review_paths = {
                item.get("path"): str(item.get("sha256", "")).lower()
                for item in evidence_by_id.values()
                if isinstance(item.get("path"), str)
            }
            if indexed_evidence != required_review_paths:
                errors.append("version index review members must exactly cover development_evidence")

    validations = data.get("validation_results")
    seen_validations: set[str] = set()
    if not isinstance(validations, list):
        errors.append("validation_results must be a list")
    else:
        for index, item in enumerate(validations):
            if not isinstance(item, dict):
                errors.append(f"validation_results[{index}] is invalid")
                continue
            validation_id = item.get("id")
            if isinstance(validation_id, str):
                seen_validations.add(validation_id)
            if (
                not isinstance(item.get("command"), str)
                or len(item["command"].strip()) < 10
                or item.get("exit_code") != 0
                or item.get("evidence_id") not in evidence_by_id
            ):
                errors.append(f"validation_results[{index}] is incomplete or failed")
        if seen_validations != REQUIRED_VALIDATIONS:
            errors.append("validation_results must exactly cover the four required checks")

    simulations = data.get("simulation_results")
    seen_simulations: set[str] = set()
    if not isinstance(simulations, list):
        errors.append("simulation_results must be a list")
    else:
        for index, item in enumerate(simulations):
            if not isinstance(item, dict):
                errors.append(f"simulation_results[{index}] is invalid")
                continue
            simulation_id = item.get("id")
            if isinstance(simulation_id, str):
                seen_simulations.add(simulation_id)
            if (
                item.get("status") != "PASS"
                or item.get("evidence_id") not in evidence_by_id
                or not isinstance(item.get("assertion"), str)
                or len(item["assertion"].strip()) < 20
            ):
                errors.append(f"simulation_results[{index}] is incomplete or failed")
        if seen_simulations != REQUIRED_SIMULATIONS:
            errors.append("simulation_results must exactly cover all ten scenarios")

    contributors = data.get("contributor_ids")
    prior_reviewers = data.get("disallowed_reviewer_ids", [])
    prior_provider_runs = data.get("disallowed_provider_run_ids", [])
    contributor_ids = {
        value for item in contributors or []
        if (value := normalized_id(item)) is not None
    } if isinstance(contributors, list) else set()
    disallowed_ids = {
        value for item in prior_reviewers
        if (value := normalized_id(item)) is not None
    } if isinstance(prior_reviewers, list) else set()
    disallowed_provider_ids = {
        value for item in prior_provider_runs
        if (value := normalized_id(item)) is not None
    } if isinstance(prior_provider_runs, list) else set()
    if not contributor_ids:
        errors.append("contributor_ids must identify the candidate modifiers")
    if not isinstance(prior_reviewers, list):
        errors.append("disallowed_reviewer_ids must be a list")
    if not isinstance(prior_provider_runs, list):
        errors.append("disallowed_provider_run_ids must be a list")

    reviews = data.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        errors.append("reviews must be a non-empty list")
        return errors
    seen_roles: set[str] = set()
    seen_reviewer_ids: set[str] = set()
    seen_provider_runs: set[str] = set()
    sealed_times: list[datetime] = []
    for index, review in enumerate(reviews):
        label = f"reviews[{index}]"
        if not isinstance(review, dict):
            errors.append(f"{label} must be an object")
            continue
        role = normalized_id(review.get("role_id"))
        reviewer = normalized_id(review.get("reviewer_id"))
        provider_run = normalized_id(review.get("provider_run_id"))
        if role is None or (role.upper() not in REQUIRED_ROLES and
                            not role.upper().startswith("additional-".upper())):
            errors.append(f"{label} role_id is invalid")
        elif role in seen_roles:
            errors.append(f"{label} duplicate role")
        else:
            seen_roles.add(role)
        if reviewer is None:
            errors.append(f"{label} reviewer_id is invalid")
        elif reviewer in seen_reviewer_ids | contributor_ids | disallowed_ids:
            errors.append(f"{label} reviewer_id is reused or not independent")
        else:
            seen_reviewer_ids.add(reviewer)
        if (
            provider_run is None
            or provider_run in seen_provider_runs
            or provider_run in disallowed_provider_ids
        ):
            errors.append(f"{label} provider_run_id must be unique and new")
        else:
            seen_provider_runs.add(provider_run)
        sealed_at = parse_time(review.get("sealed_at"))
        if sealed_at is None:
            errors.append(f"{label} sealed_at is invalid")
        else:
            sealed_times.append(sealed_at)
        if review.get("score") != 100:
            errors.append(f"{label} score must be 100")
        if review.get("criteria") != [20, 20, 20, 20, 20]:
            errors.append(f"{label} criteria must be [20, 20, 20, 20, 20]")
        for field in ("findings", "vetoes", "missing_evidence"):
            if review.get(field) != []:
                errors.append(f"{label} {field} must be empty")
        if review.get("reviewed_version_id") != version_id:
            errors.append(f"{label} reviewed_version_id mismatch")
        independence = review.get("independence")
        if not isinstance(independence, dict) or any(
            independence.get(field) is not True
            for field in (
                "did_not_modify", "did_not_view_other_reviews",
                "received_only_allowed_inputs",
                "initial_score_sealed_before_deliberation",
            )
        ):
            errors.append(f"{label} independence declaration is incomplete")
        report = safe_file(workspace, review.get("report_path"))
        report_hash = review.get("report_sha256")
        if report is None:
            errors.append(f"{label} report is missing")
            continue
        if (
            not isinstance(report_hash, str)
            or not HEX64.fullmatch(report_hash)
            or digest(report) != report_hash.lower()
        ):
            errors.append(f"{label} report_sha256 mismatch")
        try:
            report_data = json.loads(report.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            errors.append(f"{label} report must be valid JSON")
            continue
        criteria = report_data.get("criteria") if isinstance(report_data, dict) else None
        if (
            not isinstance(report_data, dict)
            or normalized_id(report_data.get("role_id")) != role
            or normalized_id(report_data.get("reviewer_id")) != reviewer
            or normalized_id(report_data.get("provider_run_id")) != provider_run
            or report_data.get("reviewed_version_id") != version_id
            or report_data.get("conclusion") != "PASS"
            or report_data.get("sealed_at") != review.get("sealed_at")
            or not isinstance(criteria, list)
            or len(criteria) != 5
        ):
            errors.append(f"{label} report identity/version/conclusion is invalid")
            continue
        report_locations: list[str] = []
        for criterion_index, criterion in enumerate(criteria):
            locations = criterion.get("evidence_locations") if isinstance(criterion, dict) else None
            if (
                not isinstance(criterion, dict)
                or criterion.get("score") != 20
                or not isinstance(criterion.get("justification"), str)
                or len(criterion["justification"].strip()) < 40
                or not isinstance(locations, list)
                or not locations
            ):
                errors.append(f"{label} criterion[{criterion_index}] is incomplete")
                continue
            for location in locations:
                if not validate_locator(skill_root, location, frozen_skill_paths):
                    errors.append(f"{label} criterion[{criterion_index}] evidence is invalid")
                elif isinstance(location, str):
                    report_locations.append(location)
        if len({loc.split("#", 1)[0] for loc in report_locations}) < 3:
            errors.append(f"{label} evidence must span at least three Skill files")
        if review.get("evidence_locations") != report_locations:
            errors.append(f"{label} manifest/report evidence locations must match")
        for field in (
            "fatal_findings", "major_findings", "minor_findings",
            "missing_evidence",
        ):
            if report_data.get(field) != []:
                errors.append(f"{label} report {field} must be empty")

    missing_roles = {role.casefold() for role in REQUIRED_ROLES} - seen_roles
    if missing_roles:
        errors.append(f"missing required roles: {', '.join(sorted(missing_roles))}")

    deliberation = data.get("review_deliberation")
    if not isinstance(deliberation, dict):
        errors.append("review_deliberation is missing")
    else:
        path = safe_file(workspace, deliberation.get("path"))
        expected = deliberation.get("sha256")
        if (
            path is None or path.stat().st_size == 0
            or not isinstance(expected, str) or not HEX64.fullmatch(expected)
            or digest(path) != expected.lower()
        ):
            errors.append("review_deliberation file/hash is invalid")
        started_at = parse_time(deliberation.get("started_at"))
        if started_at is None or any(started_at <= value for value in sealed_times):
            errors.append("review_deliberation must start after every initial report was sealed")
        participants = {
            value for item in deliberation.get("participant_roles", [])
            if (value := normalized_id(item)) is not None
        }
        if participants != seen_roles:
            errors.append("review_deliberation participants must match review roles")
        if deliberation.get("unresolved_findings") != []:
            errors.append("review_deliberation unresolved_findings must be empty")
        questions = deliberation.get("cross_questions")
        if (
            not isinstance(questions, list)
            or not questions
            or {
                normalized_id(item.get("raised_by_role"))
                for item in questions
                if isinstance(item, dict)
            } != seen_roles
            or any(
                not isinstance(item, dict)
                or item.get("status") != "CLOSED"
                or normalized_id(item.get("raised_by_role")) not in seen_roles
                or not isinstance(item.get("resolution"), str)
                or len(item["resolution"].strip()) < 20
                for item in questions
            )
        ):
            errors.append("review_deliberation cross_questions are incomplete")

    if data.get("blockers") != []:
        errors.append("blockers must be empty")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a Skill development review manifest."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--skill-root", type=Path, required=True)
    args = parser.parse_args()
    errors = validate(args.manifest.resolve(), args.skill_root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"BLOCKED: {len(errors)} skill development gate issue(s)")
        return 1
    print("PASS: skill development manifest satisfies the mechanical gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
