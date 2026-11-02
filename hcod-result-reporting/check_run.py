#!/usr/bin/env python3
"""按 hcod-result-reporting 的目录契约校验 run 目录（交付前自检的唯一依据）。

用法：check_run.py <run_dir> [<run_dir> ...]
      check_run.py --work-dirs <repo>/work_dirs   # 校验其下全部 run，并检查根目录
退出码 0 表示全部通过。

检查项：
- run.json 可解析，status 合法；best.checkpoint 文件、best.eval 目录存在。
- run 根目录只有契约条目；run 内没有 .py、__pycache__ 和流程审计文件（running 时允许流程文件）。
- eval/ 子目录名符合 <ckpt>_e<epoch>_<split>[_<variant>]，且含 summary.json。
- report/ 下 summary.json、report.html、analysis.md 存在、非空、不是软链接。
- report/summary.json 与 run.json 的 report_source 字节一致。
- report.html 不引用外部脚本/样式，相对引用不越出 report/ 且文件存在。
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT_ALLOWED = {"run.json", "config.yaml", "config.py", "train", "checkpoints", "eval", "analysis", "report"}
STATUSES = {"running", "done", "failed"}
EVAL_NAME = re.compile(r"^[a-z0-9_]+?_e\d+_(val|test)(_[a-z0-9]+)*$")
AUDIT_NAME = re.compile(
    r"(\.pid$|\.lock$|^queue|^launch|acceptance|^review|^rework|receipt|^cleanup|inventory"
    r"|verification|_status\.json$|^status\.json$|jobs?\.json$|_audit\.json$)", re.I
)
EXTERNAL_REF = re.compile(r"""<(script|link)[^>]+(src|href)\s*=\s*["']https?://""", re.I)
LOCAL_REF = re.compile(r"""(?<![-\w])(?:src|href)\s*=\s*["']([^"'#]+)["']""", re.I)


def check_run(run: Path) -> list[str]:
    errs = []
    manifest = run / "run.json"
    try:
        meta = json.loads(manifest.read_text())
    except Exception as exc:  # noqa: BLE001
        return [f"run.json 无法读取：{exc}"]
    status = meta.get("status")
    if status not in STATUSES:
        errs.append(f"run.json status 非法：{status!r}")

    for entry in run.iterdir():
        if entry.name not in ROOT_ALLOWED:
            errs.append(f"根目录有契约外条目：{entry.name}")
    for path in run.rglob("*"):
        if path.parent == run and path.name == "config.py":
            continue
        if path.suffix == ".py" or path.name == "__pycache__":
            errs.append(f"run 内有代码：{path.relative_to(run)}")
        elif status != "running" and AUDIT_NAME.search(path.name):
            errs.append(f"run 内有流程审计文件：{path.relative_to(run)}")

    eval_dir = run / "eval"
    if eval_dir.is_dir():
        for sub in eval_dir.iterdir():
            if not EVAL_NAME.match(sub.name):
                errs.append(f"eval 目录名不合规：{sub.name}")
            if not (sub / "summary.json").is_file():
                errs.append(f"eval/{sub.name} 缺 summary.json")

    if status == "running":
        return errs

    best = meta.get("best") or {}
    if not best.get("checkpoint") or not (run / best["checkpoint"]).is_file():
        errs.append(f"best.checkpoint 不存在：{best.get('checkpoint')}")
    if not best.get("eval") or not (run / best["eval"]).is_dir():
        errs.append(f"best.eval 不存在：{best.get('eval')}")

    report = run / "report"
    for name in ("summary.json", "report.html", "analysis.md"):
        f = report / name
        if f.is_symlink():
            errs.append(f"report/{name} 是软链接")
        elif not f.is_file() or f.stat().st_size == 0:
            errs.append(f"report/{name} 缺失或为空")
    source = meta.get("report_source")
    if not source or not (run / source).is_file():
        errs.append(f"report_source 不存在：{source}")
    elif (report / "summary.json").is_file() and (run / source).read_bytes() != (report / "summary.json").read_bytes():
        errs.append(f"report/summary.json 与 {source} 不一致")
    html = report / "report.html"
    if html.is_file():
        text = html.read_text(errors="replace")
        if EXTERNAL_REF.search(text):
            errs.append("report.html 引用了外部脚本或样式")
        for ref in LOCAL_REF.findall(text):
            if re.match(r"^(https?:|data:|mailto:|javascript:)", ref):
                continue
            target = (report / ref).resolve()
            if report.resolve() not in target.parents or not target.exists():
                errs.append(f"report.html 的相对引用越出 report/ 或不存在：{ref}")
    return errs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="*", type=Path)
    parser.add_argument("--work-dirs", type=Path)
    args = parser.parse_args()
    runs = list(args.runs)
    failed = 0
    if args.work_dirs:
        for entry in sorted(args.work_dirs.iterdir()):
            if entry.name == ".gitkeep":
                continue
            if entry.is_dir() and (entry / "run.json").exists():
                runs.append(entry)
            else:
                print(f"FAIL {args.work_dirs}: 根目录有非 run 条目 {entry.name}")
                failed += 1
    for run in runs:
        errs = check_run(run)
        if errs:
            failed += 1
            print(f"FAIL {run}")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"ok   {run}")
    print(f"{len(runs)} 个 run，{failed} 项不通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
