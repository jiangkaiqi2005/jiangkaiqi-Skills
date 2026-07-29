#!/usr/bin/env python3
"""Validate the forge-cumcm-solution package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


EXPECTED_GUIDE_HASH = "C90B0294A83F6B20995F499C309FA5D2C988CF110AE67AA8F27F543325FFEA82"
EXPECTED_SKILLS = {
    "SKILL.md": "forge-cumcm-solution",
    "stages/01-modeling/SKILL.md": "forge-cumcm-modeling",
    "stages/02-solving/SKILL.md": "forge-cumcm-solving",
    "stages/03-paper/SKILL.md": "forge-cumcm-paper",
}
REQUIRED_FILES = [
    "agents/openai.yaml",
    "references/cross-stage-contract.md",
    "references/method-routing.md",
    "references/stage1-proposal-tournament.md",
    "references/review-rubrics.md",
    "references/guide-traceability.md",
    "references/cumcm-guide-v1.0.md",
    "references/skill-dev-review.md",
    "scripts/check_stage_gate.py",
    "scripts/gate_common.py",
    "scripts/check_skill_dev_gate.py",
    "scripts/validate_skill.py",
    "scripts/script-integrity.json",
]


def load_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not match:
        raise ValueError("missing YAML frontmatter")
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.startswith((" ", "\t")) or ":" not in line:
            raise ValueError("frontmatter must be a flat key-value mapping")
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if not key or key in data:
            raise ValueError("frontmatter contains an empty or duplicate key")
        if value.startswith('"') and value.endswith('"'):
            value = json.loads(value)
        data[key] = value
    return data, text


def load_openai_yaml(path: Path) -> dict:
    """Parse the deliberately tiny agents/openai.yaml without dependencies."""
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines or lines[0].strip() != "interface:":
        raise ValueError("expected a single interface mapping")
    values: dict[str, str] = {}
    for line in lines[1:]:
        if not line.startswith("  "):
            raise ValueError("only interface fields are allowed")
        if line.startswith(("   ", "\t")) or ":" not in line:
            raise ValueError("interface fields must use exactly two spaces")
        key, raw = line.strip().split(":", 1)
        if not key or key in values:
            raise ValueError("empty or duplicate interface key")
        raw = raw.strip()
        if not (raw.startswith('"') and raw.endswith('"')):
            raise ValueError("interface strings must be quoted")
        value = json.loads(raw)
        if not isinstance(value, str):
            raise ValueError("interface values must be strings")
        values[key] = value
    return {"interface": values}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def check_links(path: Path, root: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = target.split("#", 1)[0].strip()
        if not target or re.match(r"^[a-z]+://", target, re.I):
            continue
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{path.relative_to(root)}: link escapes skill root: {target}")
            continue
        if not resolved.exists():
            errors.append(f"{path.relative_to(root)}: broken link: {target}")


def validate(root: Path, source: Path | None = None) -> list[str]:
    errors: list[str] = []
    if not root.is_dir():
        return [f"skill directory not found: {root}"]

    for relative in [*EXPECTED_SKILLS, *REQUIRED_FILES]:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    for relative, expected_name in EXPECTED_SKILLS.items():
        path = root / relative
        if not path.is_file():
            continue
        try:
            data, text = load_frontmatter(path)
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{relative}: {exc}")
            continue
        if set(data) != {"name", "description"}:
            errors.append(f"{relative}: frontmatter keys must be exactly name, description")
        if data.get("name") != expected_name:
            errors.append(f"{relative}: expected name {expected_name!r}")
        if not isinstance(data.get("description"), str) or len(data["description"].strip()) < 30:
            errors.append(f"{relative}: description is incomplete")
        if "TODO" in text:
            errors.append(f"{relative}: contains TODO")

    main = root / "SKILL.md"
    if main.is_file():
        main_text = main.read_text(encoding="utf-8")
        if len(main_text.splitlines()) > 500:
            errors.append("SKILL.md exceeds 500 lines")
        for token in (
            "执行是本 Skill 的主体",
            "每阶段的执行循环",
            "八席独立评审与迭代",
            "不再增加 27 席",
            "stages/01-modeling/SKILL.md",
            "stages/02-solving/SKILL.md",
            "stages/03-paper/SKILL.md",
            "scripts/check_stage_gate.py",
            "BLOCKED",
        ):
            if token not in main_text:
                errors.append(f"SKILL.md missing required route/contract: {token}")

    required_tokens = {
        "stages/01-modeling/SKILL.md": (
            "official-requirements", "stage1-contract",
            "执行合同", "执行者预审", "八席评审",
            "多路独立方案与论文融合", "至少八个独立方案 Agent",
            "proposal-input-packet", "proposal-set", "proposal-selection",
        ),
        "stages/02-solving/SKILL.md": (
            "执行合同", "执行者预审", "八席评审",
            "result-evidence-contract", "answer_kind",
        ),
        "stages/03-paper/SKILL.md": (
            "写作合同", "执行者预审", "八席终审",
            "paper-evidence-contract", "不再设置 27 席",
        ),
        "references/review-rubrics.md": (
            "交叉质询", "致命问题", "主要问题", "次要问题", "ADDITIONAL-*",
            "S1-JUDGE", "S1-DOMAIN", "S1-PROBLEM", "S1-RIGOR",
            "S1-INNOVATION", "S1-IDENTIFIABILITY", "S1-SIMPLE", "S1-REDTEAM",
            "S2-NUMERICAL", "S2-ENGINEERING", "S2-EXPERIMENT", "S2-DATA",
            "S2-PERFORMANCE", "S2-REPRODUCIBILITY", "S2-VISUALIZATION",
            "S2-MODEL-CODE", "S3-JUDGE", "S3-ARGUMENT", "S3-ABSTRACT",
            "S3-VISUAL", "S3-CONSISTENCY", "S3-CITATION-COMPLIANCE",
            "S3-TYPESETTING", "S3-ANON-REDTEAM",
            "多路方案盲评选优", "不充当终审",
        ),
        "references/stage1-proposal-tournament.md": (
            "P1", "P8", "pre-search-reasoning",
            "S1-JUDGE", "S1-DOMAIN", "S1-PROBLEM", "S1-RIGOR",
            "S1-INNOVATION", "S1-IDENTIFIABILITY", "S1-SIMPLE", "S1-REDTEAM",
            "candidate_total", "100 × 选优评委数", "winner_id",
            "不能替代原始证据", "选优分数只回答",
            "ADDITIONAL-PROPOSER-*", "不充当终审",
        ),
        "references/cross-stage-contract.md": (
            "execution-record", "stage-workflow-record", "answer_kind",
            "NUMERIC", "CATEGORICAL", "TEXT", "PROOF", "PLAN", "FILE",
            "provider_run_id", "USER_VISIBLE_PASS",
            "proposal-input-packet", "proposal-set", "proposal-selection",
        ),
        "references/guide-traceability.md": (
            "阶段一 §2 闭合题意",
            "阶段一 §4 路由算法与验证",
            "阶段二 §2 实际运行",
            "阶段二 §4 建立逐问证据链",
            "阶段三 §2 按评委阅读路径成文",
            "阶段三 §4 一致性审计",
        ),
    }
    for relative, tokens in required_tokens.items():
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            if token not in text:
                errors.append(f"{relative}: missing required review/contract token: {token}")

    yaml_path = root / "agents/openai.yaml"
    if yaml_path.is_file():
        try:
            metadata = load_openai_yaml(yaml_path)
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"agents/openai.yaml: {exc}")
        else:
            if not isinstance(metadata, dict) or set(metadata) != {"interface"}:
                errors.append("agents/openai.yaml must contain only interface")
            else:
                interface = metadata["interface"]
                expected_keys = {"display_name", "short_description", "default_prompt"}
                if not isinstance(interface, dict) or set(interface) != expected_keys:
                    errors.append("agents/openai.yaml interface keys are invalid")
                else:
                    short = interface["short_description"]
                    prompt = interface["default_prompt"]
                    if not isinstance(short, str) or not 25 <= len(short) <= 64:
                        errors.append("short_description must be 25-64 characters")
                    if not isinstance(prompt, str) or "$forge-cumcm-solution" not in prompt:
                        errors.append("default_prompt must mention $forge-cumcm-solution")
                    elif "暂停" not in prompt or "端到端" not in prompt:
                        errors.append(
                            "default_prompt must state the default pause and explicit "
                            "end-to-end exception"
                        )

    all_text_paths = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".yaml", ".py"}
    ]
    absolute_patterns = [
        re.compile(r"[A-Za-z]:\\"),
        re.compile(r"/(?:Users|home)/"),
    ]
    forbidden = [
        "不少于15000字",
        "每张图片的文字说明应不少于100字",
        "SCI/Nature风格",
        "超时时，应加长等待时间",
        "必须主动询问：Python 或 MATLAB",
        "FINAL-ARCHITECTURE",
        "FINAL-INSTRUCTION",
        "FINAL-EVIDENCE",
        "最终二十七席",
        "最终 27 席",
        "51 席",
    ]
    for path in all_text_paths:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"{path.relative_to(root)}: invalid UTF-8: {exc}")
            continue
        if path.suffix.lower() in {".md", ".yaml"} and "TODO" in text:
            errors.append(f"{path.relative_to(root)}: contains TODO")
        if path.suffix.lower() in {".md", ".yaml"}:
            for pattern in absolute_patterns:
                if pattern.search(text):
                    errors.append(f"{path.relative_to(root)}: leaks an absolute local path")
        if path.suffix.lower() in {".md", ".yaml"}:
            for phrase in forbidden:
                if phrase in text:
                    errors.append(f"{path.relative_to(root)}: contains legacy rule: {phrase}")
        if path.suffix.lower() == ".md":
            check_links(path, root, errors)

    trace = root / "references/guide-traceability.md"
    if trace.is_file() and EXPECTED_GUIDE_HASH not in trace.read_text(encoding="utf-8"):
        errors.append("guide traceability hash is missing or changed")
    guide_snapshot = root / "references/cumcm-guide-v1.0.md"
    if guide_snapshot.is_file() and sha256(guide_snapshot) != EXPECTED_GUIDE_HASH:
        errors.append("bundled guide snapshot SHA-256 does not match the audited version")
    if source is not None:
        if not source.is_file():
            errors.append(f"guide source not found: {source}")
        elif sha256(source) != EXPECTED_GUIDE_HASH:
            errors.append("guide source SHA-256 does not match the audited version")
        elif guide_snapshot.is_file() and source.read_bytes() != guide_snapshot.read_bytes():
            errors.append("bundled guide snapshot is not byte-identical to the source")

    for unwanted in ("README.md", "assets", "tools"):
        if (root / unwanted).exists():
            errors.append(f"extraneous or vendored legacy content present: {unwanted}")
    invalid_init = list(root.rglob("*.invalid-init-encoding"))
    if invalid_init:
        errors.append("invalid initializer artifacts remain")
    cache_artifacts = [
        path for path in root.rglob("*")
        if any(part in {"__pycache__", ".pytest_cache"} for part in path.parts)
        or path.suffix.lower() == ".pyc"
    ]
    if cache_artifacts:
        errors.append("cache or compiled Python artifacts remain in the Skill package")

    script_hashes = {
        "scripts/check_stage_gate.py": None,
        "scripts/gate_common.py": None,
        "scripts/validate_skill.py": None,
        "scripts/check_skill_dev_gate.py": None,
    }
    for script_relative in script_hashes:
        script_path = root / script_relative
        if script_path.is_file():
            script_hashes[script_relative] = sha256(script_path)
    integrity_record = root / "scripts" / "script-integrity.json"
    if integrity_record.is_file():
        try:
            recorded = json.loads(integrity_record.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"script-integrity.json: invalid JSON: {exc}")
        else:
            if not isinstance(recorded, dict) or set(recorded) != set(script_hashes):
                errors.append(
                    "script-integrity.json must exactly list every protected script"
                )
            else:
                for script_relative, actual in script_hashes.items():
                    expected_hash = recorded.get(script_relative)
                    if actual is None or expected_hash != actual:
                        errors.append(
                            f"{script_relative}: script integrity hash mismatch "
                            "(possible tampering)"
                        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    errors = validate(args.skill_dir.resolve(), args.source.resolve() if args.source else None)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"FAILED: {len(errors)} issue(s)")
        return 1
    print("PASS: forge-cumcm-solution structure and contracts are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
