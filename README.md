# Laguna M.1 NVFP4 on SM121 (single GB10)

Optimized **vLLM** serving and benchmarks for [`poolside/Laguna-M.1-NVFP4`](https://huggingface.co/poolside/Laguna-M.1-NVFP4) on **NVIDIA GB10 / SM12.1**.

- **TP=2** on dual GB10 is **required** for full M.1 weights (single Spark OOM at ~113 GiB during MoE init — see `docs/MEMORY.md`).
- Headline config on TP=2: **NVFP4 weights** + **`--kv-cache-dtype fp8`** first boot (nvfp4 KV ladder after stable API).
- Agent metric (v1): **[BFCL](https://gorilla.cs.berkeley.edu/leaderboard.html)** via `bfcl-eval` + `--backend vllm` / `--skip-server-setup`.

## Quick start

```bash
export MODEL_DIR=/home/r0b0tdgx/models/llm/nvfp4/poolside/Laguna-M.1-NVFP4
export IMAGE=ghcr.io/r0b0tlab/vllm-dsv4-flash-gb10:cu130-sm121-arm64-dda4668b
export PORT=30100
export KV_CACHE_DTYPE=nvfp4
export MAX_MODEL_LEN=8192   # raise after VRAM ladder in docs/MEMORY.md
chmod +x scripts/serve.sh && ./scripts/serve.sh
```

Smoke:

```bash
bash scripts/smoke_poolside_tools.sh
```

## Benchmarks

```bash
./scripts/capture_telemetry.sh --session bench-c1 -- docker logs -f laguna-m1-vllm  # optional sidecar pattern
bash scripts/bench_concurrency.sh
bash scripts/run_bfcl_v1.sh
```

Results feed `publication/html/index.html`.

## Report

Open `publication/html/index.html` after `scripts/build_report.py`.

## Model

| Field | Value |
|-------|--------|
| HF | `poolside/Laguna-M.1-NVFP4` |
| Arch | `LagunaForCausalLM` — 225B total / 23B active MoE |
| Parsers | `poolside_v1` tool + reasoning |

## Credits

Poolside (Laguna), NVIDIA (NVFP4 / Blackwell), vLLM, FlashInfer, Berkeley BFCL, r0b0tlab.