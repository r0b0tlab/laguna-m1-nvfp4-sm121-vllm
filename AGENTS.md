# AGENTS.md — Laguna M.1 NVFP4 on SM121 (vLLM)

Instructions for agents serving or benchmarking `poolside/Laguna-M.1-NVFP4` on a **single GB10**, TP=1.

## One rule

**Never publish MARLIN, emulation, or FP8-KV results as “NVFP4 KV optimized” without labeling the baseline.**

Publishable SM121-native claims require `evidence/native-kernel-check.txt` showing:

- GPU capability `(12, 1)`
- No MARLIN / unsupported-quant fallback in load logs
- Requested `--kv-cache-dtype nvfp4` reflected in server config (or documented blocker in `docs/NVFP4_KV_SM121.md`)

## Canonical serve

Use `scripts/serve.sh` only. Do not invent flags.

Required Poolside flags (already in script):

- `--tool-call-parser poolside_v1`
- `--reasoning-parser poolside_v1`
- `--enable-auto-tool-choice`
- `--default-chat-template-kwargs '{"enable_thinking": true}'`

Env:

| Var | Default | Notes |
|-----|---------|--------|
| `MODEL_DIR` | local HF checkout | Read-only mount at `/model` |
| `KV_CACHE_DTYPE` | `nvfp4` | If OOM, lower `MAX_MODEL_LEN` before switching KV |
| `MAX_MODEL_LEN` | ladder-tested | See `docs/MEMORY.md` |
| `GPU_UTIL` | `0.85` | GB10: prefer 0.85 over 0.70 |
| `PORT` | `30100` | BFCL uses `REMOTE_OPENAI_BASE_URL` |

## Benchmark gate (v1)

1. **Throughput:** `scripts/bench_concurrency.sh` — c1, c2, c4, c5, c8 minimum; JSON under `benchmarks/concurrency/`.
2. **Telemetry:** GPU temp, power (W), util — `evidence/telemetry/` for any run >2 min.
3. **Agent:** `scripts/run_bfcl_v1.sh` only — public BFCL categories in `configs/bfcl_v1_categories.txt`. No private “Laguna v2” prompts.
4. **Regression:** >10% drop vs FP8-KV baseline on c1 output tok/s blocks calling config optimized.

## BFCL

- Install: `pip install 'bfcl-eval==2025.12.17'` (project `.venv`).
- Serve must be up before BFCL.
- Run `scripts/run_bfcl_v1.sh` — registers `laguna-m1-nvfp4-sm121-FC` and uses `OPENAI_BASE_URL=http://127.0.0.1:${PORT}/v1`.
- `BFCL_VLLM_MODEL` must match `--served-model-name` (default `laguna-m1-nvfp4`).

## HTML gate

Visually verify `publication/html/index.html` (tables, overflow, mobile). Flat dark background, no gradients.

## Out of scope on public main

Demo videos, HyperFrames, render pipelines.

## Expansion (not v1)

Dual GB10 TP=2, DFlash, full SWE-bench — separate milestones; do not mix into v1 headline numbers.

## PR checklist

- [ ] `scripts/verify_native_kernels.sh` PASS
- [ ] KV dtype documented
- [ ] BFCL category list committed
- [ ] Raw JSON in `benchmarks/`