#!/usr/bin/env python3
"""Normalize lm-eval GSM8K output into committed summary + manifest; merge run_meta."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "benchmarks" / "lm_eval"
RESULTS = OUT_DIR / "gsm8k_100_results.json"
MANIFEST = OUT_DIR / "gsm8k_100_manifest.json"
RUN_META = ROOT / "benchmarks" / "run_meta.json"


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


def _find_metric(results: dict) -> tuple[str, float | None, float | None]:
    """Return (task_key, exact_match, stderr) from lm-eval results blob."""
    inner = results.get("results") or results
    if not isinstance(inner, dict):
        return "", None, None
    for task_key, task_res in inner.items():
        if "gsm8k" not in task_key.lower():
            continue
        if not isinstance(task_res, dict):
            continue
        for k, v in task_res.items():
            if "exact_match" in k and isinstance(v, (int, float)):
                stderr_key = k.replace("exact_match", "exact_match_stderr")
                stderr = task_res.get(stderr_key)
                if stderr is None:
                    for sk, sv in task_res.items():
                        if "stderr" in sk and "exact" in sk:
                            stderr = sv
                            break
                return task_key, float(v), float(stderr) if stderr is not None else None
    return "", None, None


def extract(raw_path: Path) -> dict:
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    config = data.get("config") or {}
    model_args = config.get("model_args") or ""
    task_key, em, stderr = _find_metric(data)

    limit = config.get("limit")
    if limit is None:
        limit = 100

    summary = {
        "benchmark": "gsm8k",
        "limit": limit,
        "num_fewshot": config.get("num_fewshot", 5),
        "metric": "exact_match",
        "exact_match": em,
        "exact_match_stderr": stderr,
        "task_id": task_key or config.get("task") or "gsm8k",
        "harness": "lm-evaluation-harness",
        "harness_version": data.get("lm_eval_version") or data.get("version"),
        "model": _model_from_args(model_args) or config.get("model"),
        "base_url": _base_url_from_args(model_args),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "raw_file": str(raw_path.relative_to(ROOT)) if raw_path.is_relative_to(ROOT) else str(raw_path),
    }
    return summary


def _model_from_args(model_args: str) -> str | None:
    for part in model_args.split(","):
        if part.strip().startswith("model="):
            return part.split("=", 1)[1].strip()
    return None


def _base_url_from_args(model_args: str) -> str | None:
    for part in model_args.split(","):
        if part.strip().startswith("base_url="):
            return part.split("=", 1)[1].strip()
    return None


def write_manifest(summary: dict, raw_path: Path) -> dict:
    meta = {}
    if RUN_META.is_file():
        meta = json.loads(RUN_META.read_text(encoding="utf-8"))
    manifest = {
        "summary_file": str(RESULTS.relative_to(ROOT)),
        "raw_file": summary.get("raw_file"),
        "git_head": _git_head(),
        "headline_profile": meta.get("headline_profile"),
        "topology": meta.get("topology"),
        "image": meta.get("image"),
        "task": summary.get("task_id"),
        "num_fewshot": summary.get("num_fewshot"),
        "limit": summary.get("limit"),
        "generated_at": summary.get("completed_at"),
    }
    return manifest


def merge_run_meta(summary: dict) -> None:
    meta = {}
    if RUN_META.is_file():
        meta = json.loads(RUN_META.read_text(encoding="utf-8"))
    meta.setdefault("lm_eval", {})
    meta["lm_eval"]["gsm8k_100"] = {
        "results_file": "benchmarks/lm_eval/gsm8k_100_results.json",
        "manifest_file": "benchmarks/lm_eval/gsm8k_100_manifest.json",
        "exact_match": summary.get("exact_match"),
        "exact_match_stderr": summary.get("exact_match_stderr"),
        "limit": summary.get("limit"),
        "task_id": summary.get("task_id"),
        "completed_at": summary.get("completed_at"),
    }
    RUN_META.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if raw_arg:
        raw_path = Path(raw_arg)
        if not raw_path.is_absolute():
            raw_path = ROOT / raw_path
    else:
        raw_dir = OUT_DIR / "raw"
        candidates = sorted(raw_dir.glob("gsm8k_100_*.json"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            print("No raw gsm8k_100_*.json in benchmarks/lm_eval/raw/", file=sys.stderr)
            return 1
        raw_path = candidates[-1]

    if not raw_path.is_file():
        print(f"Missing {raw_path}", file=sys.stderr)
        return 1

    summary = extract(raw_path)
    if summary.get("exact_match") is None:
        print("Warning: could not parse exact_match from raw results", file=sys.stderr)

    RESULTS.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    manifest = write_manifest(summary, raw_path)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    merge_run_meta(summary)
    print(f"Wrote {RESULTS}")
    print(f"exact_match={summary.get('exact_match')} stderr={summary.get('exact_match_stderr')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())