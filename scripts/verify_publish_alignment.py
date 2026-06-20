#!/usr/bin/env python3
"""Cross-check committed benchmarks vs run_meta, README headline table, and docs pins."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAILURES: list[str] = []
WARNINGS: list[str] = []

PIN_IMAGE = "ghcr.io/r0b0tlab/vllm-laguna-m1-nvfp4-sm121:cu130-sm121-arm64-dda4668b"
PIN_DIGEST_PREFIX = "sha256:6e2dfa4c48ac73965890a864dc1510017f42981e743b3f2834b4b189ad7712a8"


def load(path: Path):
    if path.is_file():
        return json.loads(path.read_text())
    FAILURES.append(f"missing: {path.relative_to(ROOT)}")
    return None


def check_close(name: str, a: float, b: float, tol: float = 0.02):
    if abs(a - b) > tol:
        FAILURES.append(f"{name}: {a} vs {b} (tol {tol})")


def main() -> int:
    meta = load(ROOT / "benchmarks/run_meta.json")
    conc = load(ROOT / "benchmarks/concurrency/chat-concurrency-summary-nvfp4-kv.json")
    gsm = load(ROOT / "benchmarks/lm_eval/gsm8k_100_results.json")
    kv = load(ROOT / "benchmarks/kv_cache_metrics.json")
    term = load(ROOT / "benchmarks/hermesbench/terminal_micro_results.json")
    he = load(ROOT / "benchmarks/hermesbench/humaneval_micro_results.json")

    if meta:
        if meta.get("image") != PIN_IMAGE:
            FAILURES.append(f"run_meta.image != {PIN_IMAGE}")
        if not str(meta.get("image_digest", "")).startswith(PIN_DIGEST_PREFIX[:20]):
            FAILURES.append("run_meta.image_digest mismatch")
        if "until GHCR alias" in meta.get("image_note", ""):
            WARNINGS.append("run_meta.image_note stale (mentions unpublished GHCR alias)")

    if conc and meta:
        by_c = {s["concurrency"]: s["output_tps"] for s in conc}
        c1, c8 = by_c.get(1), by_c.get(8)
        readme = (ROOT / "README.md").read_text()
        for label, val in [("c1", c1), ("c8", c8)]:
            if val is None:
                continue
            m = re.search(rf"\|\s*{label[1:]}\s*\|\s*([\d.]+)\s*\|", readme)
            if m:
                check_close(f"README {label}", float(m.group(1)), round(val, 2), 0.05)

    if gsm and meta:
        em = gsm.get("exact_match")
        meta_em = (meta.get("lm_eval") or {}).get("gsm8k_100", {}).get("exact_match")
        if em is not None and meta_em is not None and abs(em - meta_em) > 1e-9:
            FAILURES.append(f"GSM8K exact_match json {em} vs run_meta {meta_em}")

    if term:
        if term.get("passed") != 5 or term.get("total") != 5:
            FAILURES.append(f"terminal_micro expected 5/5 got {term.get('passed')}/{term.get('total')}")

    if he:
        if he.get("passed") != 10 or he.get("total") != 10:
            FAILURES.append(f"humaneval_micro expected 10/10 got {he.get('passed')}/{he.get('total')}")

    html = (ROOT / "publication/html/index.html").read_text(errors="replace")
    if PIN_IMAGE not in html:
        FAILURES.append("HTML missing canonical image string")
    if "BFCL" in html:
        FAILURES.append("HTML mentions BFCL (should be out of public story)")
    if "until GHCR alias" in html:
        WARNINGS.append("HTML run_meta embed has stale image_note — run build_report.py")

    for doc in ("docs/CONTAINER.md", "docs/BENCHMARKS.md", "AGENTS.md", "README.md"):
        text = (ROOT / doc).read_text()
        if "benchmarks + BFCL" in text or "+ BFCL" in text:
            FAILURES.append(f"{doc} mentions BFCL in repo tagline")
        if doc != "AGENTS.md" and PIN_IMAGE.split(":")[0] not in text and doc == "docs/CONTAINER.md":
            pass  # CONTAINER has full pin
        if "Flat dark background" in text:
            WARNINGS.append(f"{doc}: HTML gate says flat dark; report uses light theme")

    print("=== verify_publish_alignment ===")
    for w in WARNINGS:
        print(f"WARN: {w}")
    for f in FAILURES:
        print(f"FAIL: {f}")
    if not FAILURES and not WARNINGS:
        print("OK: artifacts and docs aligned")
    elif not FAILURES:
        print(f"OK with {len(WARNINGS)} warning(s)")
    else:
        print(f"FAILED: {len(FAILURES)} issue(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())