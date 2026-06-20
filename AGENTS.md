# Laguna M.1 NVFP4 on SM121 (vLLM)

Instructions for agents serving or benchmarking `poolside/Laguna-M.1-NVFP4` on **dual GB10 TP=2** (headline) or single GB10 (dev only — full weights OOM).

## One rule

**Never publish MARLIN, emulation, or FP8-KV results as “NVFP4 KV optimized” without labeling the baseline.**

Publishable SM121-native claims require `evidence/kernels/native-kernel-check.txt` showing:

- GPU capability `(12, 1)`
- No MARLIN / unsupported-quant fallback in load logs
- Requested `--kv-cache-dtype nvfp4` reflected in server config (or documented blocker in `docs/NVFP4_KV_SM121.md`)

## Canonical serve

**Headline:** `scripts/serve_tp2_cluster.sh` → container `laguna-m1-vllm`, port `30100`, **TP=2 Ray**, NVFP4 KV.

**Runtime image:** see `docs/CONTAINER.md` — reuses `ghcr.io/r0b0tlab/vllm-dsv4-flash-gb10:cu130-sm121-arm64-dda4668b`.

Required Poolside flags (in serve scripts):

- `--tool-call-parser poolside_v1`
- `--reasoning-parser poolside_v1`
- `--enable-auto-tool-choice`
- `--default-chat-template-kwargs '{"enable_thinking": true}'`

Env:

| Var | Default | Notes |
|-----|---------|--------|
| `MODEL_DIR` | local HF checkout | Read-only mount at `/mnt/model` (TP=2) |
| `KV_CACHE_DTYPE` | `nvfp4` | Headline after ladder; `fp8` for first boot |
| `MAX_MODEL_LEN` | `8192` | See `docs/MEMORY.md` |
| `GPU_UTIL` | `0.85` | GB10: prefer 0.85 over 0.70 |
| `PORT` | `30100` | OpenAI-compatible API |
| `NAME` | `laguna-m1-vllm` | Docker container (`launch-cluster.sh --name`) |

## Benchmark gate (v1)

1. **Throughput:** `scripts/bench_concurrency.sh` — c1–c8; headline JSON `benchmarks/concurrency/chat-concurrency-summary-nvfp4-kv.json`.
2. **Telemetry:** `scripts/capture_telemetry.sh` during bench → `evidence/telemetry/gpu-sample.jsonl`.
3. **KV metrics:** `scripts/extract_kv_metrics.py` → `benchmarks/kv_cache_metrics.json`.
4. **Report:** `python3 scripts/build_report.py` → `publication/html/index.html`.
5. **Regression:** >10% drop vs FP8-KV baseline on c1 output tok/s blocks calling config optimized.

## HTML gate

Visually verify `publication/html/index.html` (tables, overflow, mobile). Flat dark background, no gradients. Subtitle must match `benchmarks/run_meta.json` topology (dual GB10 TP=2).

## Out of scope on public main

Demo videos, HyperFrames, render pipelines, **BFCL harness results** (local-only under `benchmarks/bfcl/`, gitignored).

## PR checklist

- [ ] `scripts/verify_native_kernels.sh` PASS
- [ ] KV dtype documented
- [ ] Raw concurrency JSON in `benchmarks/concurrency/`
- [ ] `docs/CONTAINER.md` image pin accurate