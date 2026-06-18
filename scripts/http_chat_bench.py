#!/usr/bin/env python3
"""OpenAI-chat concurrency benchmark for Laguna M.1 on vLLM."""
from __future__ import annotations
import argparse, concurrent.futures, json, statistics, time, urllib.request
from pathlib import Path

PROMPTS = [
    "Summarize how NVFP4 MoE serving differs from dense FP16 on Blackwell SM121. Bullet points.",
    "List three checks before publishing a vLLM benchmark on GB10.",
    "Explain tool calling with poolside_v1 parsers in one short paragraph.",
    "Give a minimal deployment checklist for poolside/Laguna-M.1-NVFP4 on a single GPU.",
]

def post_json(url: str, payload: dict, timeout: int) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def one(base_url: str, model: str, idx: int, max_tokens: int, timeout: int) -> dict:
    prompt = PROMPTS[idx % len(PROMPTS)] + f"\nRequest id: {idx}."
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    start = time.perf_counter()
    err = None
    data = None
    try:
        data = post_json(base_url.rstrip('/') + "/chat/completions", payload, timeout)
    except Exception as e:
        err = repr(e)
    end = time.perf_counter()
    rec = {"idx": idx, "ok": err is None, "latency_s": end - start, "error": err}
    if data:
        msg = data.get("choices", [{}])[0].get("message", {})
        usage = data.get("usage") or {}
        rec.update({
            "finish_reason": data.get("choices", [{}])[0].get("finish_reason"),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "text_preview": (msg.get("content") or "")[:240],
        })
    return rec

def summarize(records: list[dict], wall_s: float, concurrency: int, max_tokens: int) -> dict:
    oks = [r for r in records if r.get("ok")]
    lats = [r["latency_s"] for r in oks]
    comp = sum(r.get("completion_tokens", 0) for r in oks)
    prompt = sum(r.get("prompt_tokens", 0) for r in oks)

    def pct(p):
        if not lats:
            return None
        vals = sorted(lats)
        k = min(len(vals) - 1, max(0, round((p / 100) * (len(vals) - 1))))
        return vals[k]

    return {
        "concurrency": concurrency,
        "max_tokens": max_tokens,
        "requests": len(records),
        "ok": len(oks),
        "errors": len(records) - len(oks),
        "wall_s": wall_s,
        "request_throughput_rps": len(oks) / wall_s if wall_s else 0,
        "output_tokens": comp,
        "prompt_tokens": prompt,
        "output_tps": comp / wall_s if wall_s else 0,
        "total_tps": (comp + prompt) / wall_s if wall_s else 0,
        "latency_avg_s": statistics.mean(lats) if lats else None,
        "latency_p50_s": pct(50),
        "latency_p90_s": pct(90),
        "latency_p95_s": pct(95),
        "latency_max_s": max(lats) if lats else None,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:30100/v1")
    ap.add_argument("--model", default="laguna-m1-nvfp4")
    ap.add_argument("--outdir", default="benchmarks/concurrency")
    ap.add_argument("--concurrency", type=int, action="append", default=[])
    ap.add_argument("--requests-per-concurrency", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=128)
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()
    ladder = args.concurrency or [1, 2, 4, 5, 8]
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    all_summaries = []
    for c in ladder:
        n = max(c, c * args.requests_per_concurrency)
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=c) as ex:
            futs = [ex.submit(one, args.base_url, args.model, i, args.max_tokens, args.timeout) for i in range(n)]
            records = [f.result() for f in concurrent.futures.as_completed(futs)]
        wall = time.perf_counter() - start
        summary = summarize(records, wall, c, args.max_tokens)
        payload = {"summary": summary, "records": sorted(records, key=lambda r: r["idx"])}
        (out / f"chat-concurrency-c{c}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(summary))
        all_summaries.append(summary)
    (out / "chat-concurrency-summary.json").write_text(json.dumps(all_summaries, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()