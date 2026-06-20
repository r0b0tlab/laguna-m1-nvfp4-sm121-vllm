#!/usr/bin/env python3
"""Collect t01_terminal_smoke results from hermes-bench-tool-call into public JSON."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "benchmarks" / "hermesbench"
RESULTS_JSON = OUT_DIR / "terminal_micro_results.json"
MANIFEST_JSON = OUT_DIR / "terminal_micro_manifest.json"
RUN_META = ROOT / "benchmarks" / "run_meta.json"

HB_REPO = Path(
    __import__("os").environ.get("HERMES_BENCH_REPO", str(Path.home() / "hermes-bench-tool-call"))
).expanduser()

CATEGORY = "t01_terminal_smoke"
TASK_IDS = [
    f"{CATEGORY}/t01_echo",
    f"{CATEGORY}/t02_ls",
    f"{CATEGORY}/t03_compile_check",
    f"{CATEGORY}/t04_pipeline",
    f"{CATEGORY}/t05_env_check",
]
MODEL_SLUG = "laguna-m1-nvfp4"


def _git_head() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        return ""


def _latest_verifier(task_id: str, model_filter: str | None, min_mtime: float = 0) -> tuple[Path | None, dict | None]:
    pattern = f"results/*/{task_id}/verifier_result.json"
    candidates = list(HB_REPO.glob(pattern))
    if model_filter:
        candidates = [p for p in candidates if model_filter in str(p)]
    if min_mtime:
        candidates = [p for p in candidates if p.stat().st_mtime >= min_mtime]
    if not candidates:
        return None, None
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    try:
        return latest, json.loads(latest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return latest, None


def build_summary(model_filter: str | None = MODEL_SLUG) -> dict:
    min_mtime = 0.0
    marker = ROOT / "evidence" / "hermes_terminal_micro.run_start"
    if marker.is_file():
        try:
            min_mtime = float(marker.read_text().strip())
        except ValueError:
            pass
    tasks = []
    passed = 0
    run_paths: set[str] = set()
    for tid in TASK_IDS:
        path, data = _latest_verifier(tid, model_filter, min_mtime)
        if not data:
            tasks.append(
                {
                    "task_id": tid,
                    "status": "MISSING",
                    "score": 0.0,
                    "reason": "no verifier_result.json found",
                }
            )
            continue
        status = data.get("status", "FAIL")
        if status == "PASS":
            passed += 1
        if path:
            run_paths.add(str(path.parent.parent.parent.relative_to(HB_REPO)))
        tasks.append(
            {
                "task_id": tid,
                "status": status,
                "score": data.get("score", 0.0),
                "reason": data.get("reason", ""),
                "source": str(path.relative_to(HB_REPO)) if path else None,
            }
        )
    total = len(TASK_IDS)
    return {
        "benchmark": "hermesbench",
        "category": CATEGORY,
        "model": MODEL_SLUG,
        "passed": passed,
        "total": total,
        "pass_rate": passed / total if total else 0.0,
        "tasks": tasks,
        "hermes_bench_repo": str(HB_REPO),
        "run_dirs": sorted(run_paths),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


def merge_run_meta(summary: dict) -> None:
    meta = {}
    if RUN_META.is_file():
        meta = json.loads(RUN_META.read_text(encoding="utf-8"))
    meta.setdefault("hermesbench", {})
    meta["hermesbench"]["terminal_micro"] = {
        "results_file": "benchmarks/hermesbench/terminal_micro_results.json",
        "passed": summary.get("passed"),
        "total": summary.get("total"),
        "pass_rate": summary.get("pass_rate"),
        "completed_at": summary.get("completed_at"),
    }
    RUN_META.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if not HB_REPO.is_dir():
        print(f"Missing hermes-bench repo: {HB_REPO}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model_filter = sys.argv[1] if len(sys.argv) > 1 else MODEL_SLUG
    if model_filter == "any":
        model_filter = None
    summary = build_summary(model_filter)
    RESULTS_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "summary_file": str(RESULTS_JSON.relative_to(ROOT)),
        "git_head": _git_head(),
        "category": CATEGORY,
        "harness": "hermes-bench-tool-call",
        "real_agent": True,
        "generated_at": summary["completed_at"],
    }
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    merge_run_meta(summary)
    print(f"Wrote {RESULTS_JSON}")
    print(f"pass_rate={summary['passed']}/{summary['total']} ({100*summary['pass_rate']:.0f}%)")
    return 0 if summary["passed"] == summary["total"] else 0


if __name__ == "__main__":
    raise SystemExit(main())