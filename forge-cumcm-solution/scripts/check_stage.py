#!/usr/bin/env python3
"""Submission safety net for the three-stage CUMCM workflow.

Checks that stage artifacts exist, the eight review reports are on file,
the final PDF is structurally readable, and official inputs are unchanged.
It deliberately does not judge mathematical quality; the stage instructions
and the independent review panel own semantic judgment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


STAGE_ROLES = {
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

STAGE_ARTIFACTS = {
    1: {
        "input-inventory", "research-record", "proposal-input-packet",
        "proposal-set", "proposal-selection", "task-matrix",
        "core-mechanism", "assumption-register", "model-interfaces",
        "method-map", "risk-register", "stage1-contract",
        "modeling-summary",
    },
    2: {
        "research-record", "code-bundle", "run-commands",
        "result-files", "constraint-certificate", "independent-validation",
        "sensitivity-analysis", "number-ledger", "figures-manifest",
        "reproduction-record", "data-validity-audit",
        "result-evidence-contract",
    },
    3: {
        "research-record", "editable-paper", "final-pdf",
        "consistency-audit", "submission-inventory", "integrity-audit",
        "paper-evidence-contract",
    },
}

PDF_PATTERNS = (
    rb"/Type\s*/Catalog\b", rb"/Type\s*/Pages\b",
    rb"/Type\s*/Page\b", rb"/Count\s+[1-9]\d*\b",
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def safe_file(root: Path, relative: object, label: str, errors: list[str]) -> Path | None:
    if not isinstance(relative, str) or not relative.strip():
        errors.append(f"{label}: path is required")
        return None
    raw = Path(relative.strip())
    if raw.is_absolute() or ".." in raw.parts:
        errors.append(f"{label}: path must stay inside the stage directory")
        return None
    resolved = (root / raw).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        errors.append(f"{label}: path escapes the stage directory")
        return None
    if not resolved.is_file():
        errors.append(f"{label}: file not found: {raw}")
        return None
    if resolved.stat().st_size == 0:
        errors.append(f"{label}: file must not be empty")
        return None
    return resolved


def validate_pdf(path: Path, errors: list[str]) -> None:
    content = path.read_bytes()
    if (
        path.suffix.lower() != ".pdf"
        or len(content) < 512
        or not content.startswith(b"%PDF-")
        or b"%%EOF" not in content[-1024:]
        or any(re.search(pattern, content) is None for pattern in PDF_PATTERNS)
        or b"stream" not in content
        or b"startxref" not in content
    ):
        errors.append("final-pdf: basic PDF/page-tree structure is invalid")


def check_trusted_inputs(path: Path, errors: list[str]) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"trusted-inputs: cannot read {path}: {exc}")
        return
    root = path.resolve().parent
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", stripped)
        if match is None:
            errors.append(f"trusted-inputs line {number}: expected '<sha256>  <path>'")
            continue
        expected, relative = match.group(1).lower(), match.group(2).strip()
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            errors.append(f"trusted-inputs line {number}: path escapes the checksum directory")
            continue
        if not target.is_file():
            errors.append(f"trusted-inputs: official input not found: {relative}")
            continue
        if digest(target) != expected:
            errors.append(f"trusted-inputs: official input changed since pinning: {relative}")


def validate(
    manifest_path: Path, expected_stage: int, trusted_inputs: Path | None,
) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"manifest: invalid JSON: {exc}"]
    if not isinstance(data, dict):
        return ["manifest: root must be an object"]
    root = manifest_path.parent.resolve()
    if data.get("stage") != expected_stage:
        errors.append("manifest: stage does not match --stage")

    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("manifest: artifacts must be a non-empty list")
        artifacts = []
    artifact_ids: set[str] = set()
    paths_by_id: dict[str, Path] = {}
    for index, item in enumerate(artifacts):
        label = f"artifacts[{index}]"
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip():
            errors.append(f"{label}: id is required")
            continue
        artifact_id = item["id"].strip()
        if artifact_id in artifact_ids:
            errors.append(f"{label}: duplicate artifact id {artifact_id}")
            continue
        artifact_ids.add(artifact_id)
        path = safe_file(root, item.get("path"), f"{label} ({artifact_id})", errors)
        if path is not None:
            paths_by_id[artifact_id] = path
    missing = STAGE_ARTIFACTS[expected_stage] - artifact_ids
    if missing:
        errors.append(f"missing required artifacts: {', '.join(sorted(missing))}")

    if expected_stage == 3 and "final-pdf" in paths_by_id:
        validate_pdf(paths_by_id["final-pdf"], errors)

    reviews = data.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        errors.append("manifest: reviews must be a non-empty list")
        reviews = []
    roles: set[str] = set()
    for index, review in enumerate(reviews):
        label = f"reviews[{index}]"
        if not isinstance(review, dict):
            errors.append(f"{label}: must be an object")
            continue
        role = review.get("role_id")
        if not isinstance(role, str) or not role.strip():
            errors.append(f"{label}: role_id is required")
            continue
        role = role.strip()
        if role in roles:
            errors.append(f"{label}: role {role} appears more than once")
            continue
        roles.add(role)
        safe_file(root, review.get("report"), f"{label} ({role})", errors)
    missing_roles = STAGE_ROLES[expected_stage] - roles
    if missing_roles:
        errors.append(f"missing review roles: {', '.join(sorted(missing_roles))}")
    if any(
        not role.startswith("ADDITIONAL-")
        for role in roles - STAGE_ROLES[expected_stage]
    ):
        errors.append("review roles outside the stage roster must use ADDITIONAL-* ids")

    if trusted_inputs is not None:
        check_trusted_inputs(trusted_inputs, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("stage-manifest.json"))
    parser.add_argument("--stage", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument(
        "--trusted-inputs", type=Path,
        help="sha256sum-style checksum file of official problem/data, pinned once when first read",
    )
    args = parser.parse_args()
    manifest = args.manifest.resolve()
    if not manifest.is_file():
        print(f"ERROR: manifest not found: {manifest}")
        return 1
    errors = validate(
        manifest, args.stage,
        args.trusted_inputs.resolve() if args.trusted_inputs else None,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"BLOCKED: {len(errors)} stage gate issue(s)")
        return 1
    print(f"PASS: stage {args.stage} gate passed; quality judgment belongs to the review panel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
