#!/usr/bin/env python3
"""Extract hermes-bench HumanEval micro results."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HB = Path(__import__("os").environ.get("HERMES_BENCH_REPO", str(Path.home() / "hermes-bench-tool-call"))).expanduser()
OUT = ROOT / "benchmarks" / "hermesbench"
RESULTS = OUT / "humaneval_micro_results.json"
MANIFEST = OUT / "humaneval_micro_manifest.json"
RUN_META = ROOT / "benchmarks" / "run_meta.json"
CATEGORY = "t13_humaneval_micro"
TASK_IDS = []


def _load_task_ids() -> list[str]:
    m = ROOT / "benchmarks" / "hermesbench" / "humaneval_micro_task_manifest.json"
    if m.is_file():
        data = json.loads(m.read_text(encoding="utf-8"))
        return [t["task_id"] for t in data.get("tasks", [])]
    return [
        f"{CATEGORY}/human_eval_0",
        f"{CATEGORY}/human_eval_1",
    ]


def main() -> int:
    min_mtime = 0.0
    marker = ROOT / "evidence" / "hermes_humaneval_micro.run_start"
    if marker.is_file():
        try:
            min_mtime = float(marker.read_text().strip())
        except ValueError:
            pass
    model_filter = sys.argv[1] if len(sys.argv) > 1 else "laguna-m1-nvfp4"
    task_ids = _load_task_ids()
    tasks = []
    passed = 0
    run_dirs: set[str] = set()
    for tid in task_ids:
        cands = list(HB.glob(f"results/*/{tid}/verifier_result.json"))
        if model_filter:
            cands = [p for p in cands if model_filter in str(p)]
        if min_mtime:
            cands = [p for p in cands if p.stat().st_mtime >= min_mtime]
        if not cands:
            tasks.append({"task_id": tid, "status": "MISSING"})
            continue
        latest = max(cands, key=lambda p: p.stat().st_mtime)
        v = json.loads(latest.read_text(encoding="utf-8"))
        st = v.get("status", "FAIL")
        if st == "PASS":
            passed += 1
        run_dirs.add(str(latest.parent.parent.parent.relative_to(HB)))
        tasks.append(
            {
                "task_id": tid,
                "status": st,
                "reason": v.get("reason", ""),
                "source": str(latest.relative_to(HB)),
            }
        )
    total = len(task_ids)
    summary = {
        "benchmark": "humaneval",
        "mode": "hermes_agent",
        "category": CATEGORY,
        "model": model_filter,
        "passed": passed,
        "total": total,
        "pass_rate": passed / total if total else 0.0,
        "pass_at_1": passed / total if total else 0.0,
        "tasks": tasks,
        "run_dirs": sorted(run_dirs),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    MANIFEST.write_text(
        json.dumps({"summary_file": str(RESULTS.relative_to(ROOT)), "category": CATEGORY}, indent=2) + "\n",
        encoding="utf-8",
    )
    meta = json.loads(RUN_META.read_text()) if RUN_META.is_file() else {}
    meta.setdefault("hermesbench", {})
    meta["hermesbench"]["humaneval_micro"] = {
        "results_file": "benchmarks/hermesbench/humaneval_micro_results.json",
        "pass_at_1": summary["pass_at_1"],
        "passed": passed,
        "total": total,
    }
    RUN_META.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"pass@1={passed}/{total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())