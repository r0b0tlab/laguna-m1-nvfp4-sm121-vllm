# Laguna M.1 NVFP4 on SM121 (dual GB10)

Optimized **vLLM** serving and benchmarks for [`poolside/Laguna-M.1-NVFP4`](https://huggingface.co/poolside/Laguna-M.1-NVFP4) on **NVIDIA GB10 / SM12.1**.

- **TP=2** on dual GB10 is **required** for full M.1 weights (single Spark OOM at ~113 GiB during MoE init — see `docs/MEMORY.md`).
- **Headline:** NVFP4 weights + **`--kv-cache-dtype nvfp4`** on TP=2 (`laguna-m1-vllm`, port `30100`).
- **Container:** reuses [`docs/CONTAINER.md`](docs/CONTAINER.md) DSV4 SM121 image (no separate Laguna GHCR tag in v1).
- **Agent metric:** **[BFCL](https://gorilla.cs.berkeley.edu/leaderboard.html)** via `bfcl-eval` + `scripts/bfcl_run.py` (in-process model registration).

## Quick start (dual GB10)

```bash
export MODEL_DIR=/path/to/Laguna-M.1-NVFP4
export IMAGE=ghcr.io/r0b0tlab/vllm-dsv4-flash-gb10:cu130-sm121-arm64-dda4668b
export PORT=30100
export KV_CACHE_DTYPE=nvfp4
export MAX_MODEL_LEN=8192
bash scripts/serve_tp2_cluster.sh
```

Smoke:

```bash
bash scripts/smoke_poolside_tools.sh
```

## Benchmarks

```bash
./scripts/capture_telemetry.sh   # optional during bench
bash scripts/bench_concurrency.sh
bash scripts/run_bfcl_v1.sh
python3 scripts/build_report.py
```

Report: [`publication/html/index.html`](publication/html/index.html) (GitHub Pages: enable Pages from `/publication/html` if desired).

## Headline throughput (nvfp4-kv, TP=2)

| c | Output tok/s |
|---|-------------|
| 1 | 11.41 |
| 8 | 48.98 |

Full table + thermals + BFCL in the HTML report.

## Model

| Field | Value |
|-------|--------|
| HF | `poolside/Laguna-M.1-NVFP4` |
| Arch | `LagunaForCausalLM` — 225B total / 23B active MoE |
| Parsers | `poolside_v1` tool + reasoning |

## Credits

Poolside (Laguna), NVIDIA (NVFP4 / Blackwell), vLLM, FlashInfer, Berkeley BFCL, r0b0tlab.