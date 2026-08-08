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
sys.path.insert(0, str(SCRIPT_DIR))

from check_stage_gate import ROLES, validate  # noqa: E402
from test_check_stage_gate import (  # noqa: E402
    build_checkpoint, build_manifest, hash_file, minimal_renderable_pdf,
    trusted_root_payload, write_json,
)


def run_cli(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-B", *arguments],
        cwd=SKILL_ROOT,
        text=True,
        capture_output=True,
        env=environment,
    )


class CLITests(unittest.TestCase):
    def test_validate_skill_cli_passes(self) -> None:
        result = run_cli([str(SCRIPT_DIR / "validate_skill.py")])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class RequiredScenarioTests(unittest.TestCase):
    def test_scenario_new_problem_three_stages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for stage in (1, 2, 3):
                path = build_manifest(root, stage)
                self.assertEqual(validate(path, stage, trusted_root_payload()), [])

    def test_scenario_continue_from_modeling(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = build_manifest(root, 2)
            self.assertEqual(validate(path, 2, trusted_root_payload()), [])

    def test_scenario_continue_from_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = build_manifest(root, 3)
            self.assertEqual(validate(path, 3, trusted_root_payload()), [])

    def test_scenario_paper_submission_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = build_manifest(root, 3)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(data["reviews"]), 8)
            self.assertEqual({item["role_id"] for item in data["reviews"]}, ROLES[3])
            self.assertEqual(validate(path, 3, trusted_root_payload()), [])

    def test_scenario_stage2_rollback_to_stage1(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = build_checkpoint(Path(temp), "BLOCKED")
            from check_stage_gate import validate_checkpoint
            self.assertEqual(validate_checkpoint(path, 1), [])

    def test_scenario_stage3_rollback_to_stage2(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = build_checkpoint(Path(temp), "BLOCKED", stage=2)
            from check_stage_gate import validate_checkpoint
            self.assertEqual(validate_checkpoint(path, 2), [])

    def test_scenario_missing_official_material_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = build_manifest(Path(temp), 1)
            errors = validate(path, 1, None)
            self.assertTrue(any("trusted-source-manifest" in error for error in errors))

    def test_scenario_review_score_blocks_advance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = build_manifest(Path(temp), 1)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["reviews"][0]["score"] = 99
            write_json(path, data)
            self.assertTrue(any(
                "100/100" in error
                for error in validate(path, 1, trusted_root_payload())
            ))

    def test_scenario_artifact_change_invalidates_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = build_manifest(root, 1)
            data = json.loads(path.read_text(encoding="utf-8"))
            artifact = next(
                item for item in data["artifacts"]
                if item["id"] == "task-matrix"
            )
            (root / artifact["path"]).write_text("changed after PASS", encoding="utf-8")
            self.assertTrue(any(
                "SHA-256 mismatch" in error
                for error in validate(path, 1, trusted_root_payload())
            ))

    def test_scenario_resume_after_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = build_checkpoint(Path(temp), "EXECUTING")
            from check_stage_gate import validate_checkpoint
            self.assertEqual(validate_checkpoint(path, 1), [])


class RealExecutionIntegrationTests(unittest.TestCase):
    def test_real_commands_rebuild_result_and_renderable_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_path = root / "data.json"
            solve_path = root / "solve.py"
            verify_path = root / "verify.py"
            reproduce_path = root / "reproduce.py"
            data_path.write_text('{"values":[1,2,3,4]}', encoding="utf-8")
            solve_path.write_text(
                "import json\nfrom pathlib import Path\n"
                "r=Path(__file__).parent\n"
                "d=json.loads((r/'data.json').read_text())\n"
                "(r/'result.json').write_text(json.dumps({'sum':sum(d['values'])}))\n",
                encoding="utf-8",
            )
            verify_path.write_text(
                "import json\nfrom pathlib import Path\n"
                "r=Path(__file__).parent\n"
                "v=json.loads((r/'result.json').read_text())['sum']\n"
                "assert v==10\nprint('verified',v)\n",
                encoding="utf-8",
            )
            reproduce_path.write_text(
                "import json, subprocess, sys\nfrom pathlib import Path\n"
                "r=Path(__file__).parent\n"
                "subprocess.run([sys.executable,str(r/'solve.py')],check=True)\n"
                "v=json.loads((r/'result.json').read_text())['sum']\n"
                "assert v==10\nprint('reproduced',v)\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            logs = []
            for script in (solve_path, verify_path, reproduce_path):
                result = subprocess.run(
                    [sys.executable, "-B", str(script)],
                    text=True, capture_output=True, env=environment,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                logs.append({
                    "command": f"{sys.executable} -B {script.name}",
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                })
            result_path = root / "result.json"
            self.assertEqual(
                json.loads(result_path.read_text(encoding="utf-8")), {"sum": 10}
            )
            first_hash = hash_file(result_path)
            subprocess.run(
                [sys.executable, "-B", str(reproduce_path)],
                check=True, capture_output=True, text=True, env=environment,
            )
            self.assertEqual(hash_file(result_path), first_hash)
            log_path = root / "run-log.json"
            write_json(log_path, logs)
            self.assertGreater(log_path.stat().st_size, 100)
            pdf = root / "paper.pdf"
            pdf.write_bytes(minimal_renderable_pdf())
            from check_stage_gate import validate_pdf
            errors: list[str] = []
            validate_pdf(pdf, errors)
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
