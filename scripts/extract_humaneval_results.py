#!/usr/bin/env python3
"""Normalize lm-eval HumanEval output."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "benchmarks" / "lm_eval"
RESULTS = OUT_DIR / "humaneval_micro_results.json"
MANIFEST = OUT_DIR / "humaneval_micro_manifest.json"
RUN_META = ROOT / "benchmarks" / "run_meta.json"


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return ""


def _find_pass_at_k(data: dict) -> tuple[float | None, float | None, str]:
    inner = data.get("results") or {}
    for task_key, task_res in inner.items():
        if "humaneval" not in task_key.lower():
            continue
        if not isinstance(task_res, dict):
            continue
        for k, v in task_res.items():
            if "pass_at" in k.lower() and "stderr" not in k.lower() and isinstance(v, (int, float)):
                stderr = None
                for sk, sv in task_res.items():
                    if "stderr" in sk.lower() and "pass" in sk.lower():
                        stderr = sv
                        break
                return float(v), float(stderr) if stderr is not None else None, task_key
    return None, None, ""


def main() -> int:
    raw_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if raw_arg:
        raw_path = Path(raw_arg)
        if not raw_path.is_absolute():
            raw_path = ROOT / raw_path
    else:
        cands = sorted(OUT_DIR.glob("raw/humaneval_micro_*.json"), key=lambda p: p.stat().st_mtime)
        if not cands:
            print("No humaneval_micro raw json", file=sys.stderr)
            return 1
        raw_path = cands[-1]

    data = json.loads(raw_path.read_text(encoding="utf-8"))
    config = data.get("config") or {}
    configs = data.get("configs") or {}
    pass_k, stderr, task_key = _find_pass_at_k(data)
    limit = config.get("limit")
    if limit is None:
        for cfg in configs.values():
            sl = (data.get("results") or {}).get(cfg.get("task", ""), {}).get("sample_len")
            if sl:
                limit = sl
                break
    if limit is None:
        limit = 10

    summary = {
        "benchmark": "humaneval",
        "mode": "standalone_lm_eval",
        "limit": limit,
        "pass_at_1": pass_k,
        "pass_at_1_stderr": stderr,
        "task_id": task_key or config.get("task") or "humaneval_instruct",
        "harness": "lm-evaluation-harness",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "raw_file": str(raw_path.relative_to(ROOT)) if raw_path.is_relative_to(ROOT) else str(raw_path),
    }
    RESULTS.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    MANIFEST.write_text(
        json.dumps(
            {
                "summary_file": str(RESULTS.relative_to(ROOT)),
                "git_head": _git_head(),
                "task": summary["task_id"],
                "limit": limit,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    meta = json.loads(RUN_META.read_text()) if RUN_META.is_file() else {}
    meta.setdefault("lm_eval", {})
    meta["lm_eval"]["humaneval_micro"] = {
        "results_file": "benchmarks/lm_eval/humaneval_micro_results.json",
        "pass_at_1": pass_k,
        "limit": limit,
    }
    RUN_META.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"pass@1={pass_k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())