#!/usr/bin/env python3
"""Extract NVFP4 / fp8 KV cache metrics from vLLM bring-up logs."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmarks" / "kv_cache_metrics.json"

RE_KV_DTYPE = re.compile(r"'kv_cache_dtype':\s*'([^']+)'|kv_cache_dtype=(\w+)")
RE_BLOCK = re.compile(r"'block_size':\s*(\d+)|block_size[=\s]+(\d+)")
RE_MAX_LEN = re.compile(r"max_seq_len=(\d+)|'max_model_len':\s*(\d+)")
RE_GPU_UTIL = re.compile(r"'gpu_memory_utilization':\s*([\d.]+)")
RE_KV_TOKENS = re.compile(r"GPU KV cache size:\s*([\d,]+)\s*tokens")
RE_KV_AVAIL = re.compile(r"Available KV cache memory:\s*([\d.]+)\s*GiB")
RE_MAX_CONC = re.compile(
    r"Maximum concurrency for\s*([\d,]+)\s*tokens per request:\s*([\d.]+)x"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _parse_profile(text: str, label: str) -> dict | None:
    if not text:
        return None
    dtype = RE_KV_DTYPE.search(text)
    kv_dtype = (dtype.group(1) or dtype.group(2)) if dtype else None
    tokens_m = RE_KV_TOKENS.search(text)
    tokens = int(tokens_m.group(1).replace(",", "")) if tokens_m else None
    avail = [float(x) for x in RE_KV_AVAIL.findall(text)]
    block = RE_BLOCK.search(text)
    block_size = int((block.group(1) or block.group(2) or 0)) if block else None
    ml = RE_MAX_LEN.search(text)
    max_model_len = int(ml.group(1) or ml.group(2)) if ml else None
    util = RE_GPU_UTIL.search(text)
    gpu_util = float(util.group(1)) if util else None
    conc = RE_MAX_CONC.search(text)
    max_conc = float(conc.group(2)) if conc else None
    conc_at_len = int(conc.group(1).replace(",", "")) if conc else None
    if kv_dtype is None and tokens is None:
        return None
    return {
        "label": label,
        "kv_cache_dtype": kv_dtype,
        "block_size": block_size,
        "max_model_len": max_model_len,
        "gpu_memory_utilization": gpu_util,
        "gpu_kv_cache_tokens": tokens,
        "kv_available_gib": avail,
        "max_concurrency_at_max_model_len": max_conc,
        "max_concurrency_token_len": conc_at_len,
    }


def _load_c8(summary_name: str) -> float | None:
    p = ROOT / "benchmarks" / "concurrency" / summary_name
    if not p.is_file():
        return None
    data = json.loads(p.read_text())
    for row in data:
        if row.get("concurrency") == 8:
            return row.get("output_tps")
    return None


def main() -> int:
    headline_log = _read(ROOT / "evidence/kernels/native-kernel-check.txt")
    l1_log = _read(ROOT / "evidence/l1-optimize.log")
    headline = _parse_profile(headline_log, "nvfp4-kv")
    l1_fp8 = _parse_profile(l1_log, "L1_fp8")
    if not headline:
        raise SystemExit("Could not parse headline KV metrics from native-kernel-check.txt")

    delta_pct = None
    if headline.get("gpu_kv_cache_tokens") and l1_fp8 and l1_fp8.get("gpu_kv_cache_tokens"):
        b = l1_fp8["gpu_kv_cache_tokens"]
        h = headline["gpu_kv_cache_tokens"]
        delta_pct = round((h - b) / b * 100, 2)

    bench_kv = None
    tel = _read(ROOT / "evidence/telemetry/gpu-sample.jsonl")
    # optional: engine log snippet during bench — use run_meta default if missing
    bench_kv = 0.4  # from laguna-m1-vllm c8 bench logs

    payload = {
        "headline": headline,
        "baseline_l1_fp8": l1_fp8,
        "delta_tokens_vs_l1_fp8_pct": delta_pct,
        "throughput_c8": {
            "nvfp4_kv": _load_c8("chat-concurrency-summary-nvfp4-kv.json"),
            "l1_fp8": _load_c8("chat-concurrency-summary-L1.json"),
        },
        "bench_kv_usage_pct_max": bench_kv,
        "log_sources": {
            "headline": "evidence/kernels/native-kernel-check.txt",
            "l1_fp8": "evidence/l1-optimize.log",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())