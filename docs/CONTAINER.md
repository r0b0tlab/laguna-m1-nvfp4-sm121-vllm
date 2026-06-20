# Container runtime (canonical)

## Headline registry image

| Field | Value |
|-------|--------|
| **Registry image** | `ghcr.io/r0b0tlab/vllm-laguna-m1-nvfp4-sm121:cu130-sm121-arm64-dda4668b` |
| **Pull alias (same digest)** | `ghcr.io/r0b0tlab/vllm-dsv4-flash-gb10:cu130-sm121-arm64-dda4668b` |
| **Digest pin** | `sha256:6e2dfa4c48ac73965890a864dc1510017f42981e743b3f2834b4b189ad7712a8` |
| **Docker name** | `laguna-m1-vllm` |
| **Launch** | `scripts/serve_tp2_cluster.sh` |

LagunaForCausalLM, Poolside parsers, FlashInfer CUTLASS NVFP4 MoE. Serve-time: weights, KV dtype, TP=2 Ray.

If pull on the Laguna name fails, set `IMAGE` to the **pull alias** (same digest).

## Dual GB10

```bash
export MODEL_DIR=/path/to/Laguna-M.1-NVFP4
export IMAGE=ghcr.io/r0b0tlab/vllm-laguna-m1-nvfp4-sm121:cu130-sm121-arm64-dda4668b
export NAME=laguna-m1-vllm
export PORT=30100
export KV_CACHE_DTYPE=nvfp4
export MAX_MODEL_LEN=8192
bash scripts/serve_tp2_cluster.sh
```

## Single-node dev

`scripts/serve.sh` — same default `IMAGE`.