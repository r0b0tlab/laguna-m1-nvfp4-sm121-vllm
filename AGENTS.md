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
| `PORT` | `30100` | BFCL uses `OPENAI_BASE_URL` |

## Benchmark gate (v1)

1. **Throughput:** `scripts/bench_concurrency.sh` — c1–c8; headline JSON `benchmarks/concurrency/chat-concurrency-summary-nvfp4-kv.json`.
2. **Telemetry:** `scripts/capture_telemetry.sh` during bench → `evidence/telemetry/gpu-sample.jsonl`.
3. **Agent:** `scripts/run_bfcl_v1.sh` — categories in `configs/bfcl_v1_categories.txt` (v1 may omit `live_*` if offline).
4. **Report:** `python3 scripts/build_report.py` → `publication/html/index.html`.
5. **Regression:** >10% drop vs FP8-KV baseline on c1 output tok/s blocks calling config optimized.

## BFCL

- Venv: `pip install 'bfcl-eval==2025.12.17' soundfile`
- Registration runs **in-process** via `scripts/bfcl_run.py` (do not call bare `bfcl` CLI for custom model).
- Serve must be up before BFCL.

## HTML gate

Visually verify `publication/html/index.html` (tables, overflow, mobile). Flat dark background, no gradients. Subtitle must match `benchmarks/run_meta.json` topology (dual GB10 TP=2).

## Out of scope on public main

Demo videos, HyperFrames, render pipelines.

## PR checklist

- [ ] `scripts/verify_native_kernels.sh` PASS
- [ ] KV dtype documented
- [ ] BFCL scores under `benchmarks/bfcl/score/`
- [ ] Raw JSON in `benchmarks/`
- [ ] `docs/CONTAINER.md` image pin accurate