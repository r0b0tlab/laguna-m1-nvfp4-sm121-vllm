# Container runtime (canonical)

## Headline runtime (Laguna M.1 on SM121)

| Field | Value |
|-------|--------|
| **GHCR image** | `ghcr.io/r0b0tlab/vllm-dsv4-flash-gb10:cu130-sm121-arm64-dda4668b` |
| **Digest pin** | `sha256:6e2dfa4c48ac73965890a864dc1510017f42981e743b3f2834b4b189ad7712a8` |
| **Docker name** | `laguna-m1-vllm` |
| **Launch** | `scripts/serve_tp2_cluster.sh` |

This build ships **Laguna** (`LagunaForCausalLM`), **Poolside** `poolside_v1` tool/reasoning parsers, and native **NVFP4** MoE (**FlashInfer CUTLASS**). v1 reuses the proven DSV4 Flash GB10 SM121 image; Laguna-specific options are applied at **serve time** (model mount, KV dtype, TP=2 Ray, NCCL).

A dedicated `ghcr.io/r0b0tlab/vllm-laguna-m1-nvfp4-sm121` tag remains optional if defaults diverge.

## Dual GB10 (required for full M.1)

Single GB10 OOMs during MoE weight init (~113 GiB). Use **TP=2 + Ray**:

```bash
export MODEL_DIR=/path/to/Laguna-M.1-NVFP4
export IMAGE=ghcr.io/r0b0tlab/vllm-dsv4-flash-gb10:cu130-sm121-arm64-dda4668b
export NAME=laguna-m1-vllm
export PORT=30100
export KV_CACHE_DTYPE=nvfp4
export MAX_MODEL_LEN=8192
bash scripts/serve_tp2_cluster.sh
```

## Operations

```bash
docker ps --filter name=laguna-m1-vllm
docker logs -f laguna-m1-vllm
curl -s http://127.0.0.1:30100/health
```

Stop cluster (from `spark-vllm-docker`):

```bash
./launch-cluster.sh stop --name laguna-m1-vllm
```

## Single-node dev (not headline)

`scripts/serve.sh` — default `NAME=laguna-m1-vllm`. Do not publish single-node throughput as M.1 headline without OOM disclaimer.