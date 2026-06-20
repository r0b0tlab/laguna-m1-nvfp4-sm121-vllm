# Container runtime (canonical)

Laguna M.1 does **not** ship a separate `ghcr.io/.../vllm-laguna-m1-*` image in v1.

## Image

```
ghcr.io/r0b0tlab/vllm-dsv4-flash-gb10:cu130-sm121-arm64-dda4668b
```

This SM121 / cu130 / arm64 vLLM build includes **Laguna** (`LagunaForCausalLM`), **Poolside** tool/reasoning parsers, and native **NVFP4** MoE (FlashInfer CUTLASS). Laguna-specific behavior is selected at **serve time** (model path, `--tool-call-parser poolside_v1`, KV dtype, TP).

## Dual GB10 (required for full M.1)

Single GB10 OOMs during MoE weight init (~113 GiB). Use **TP=2 + Ray**:

```bash
export MODEL_DIR=/path/to/Laguna-M.1-NVFP4
export IMAGE=ghcr.io/r0b0tlab/vllm-dsv4-flash-gb10:cu130-sm121-arm64-dda4668b
bash scripts/serve_tp2_cluster.sh   # container name: laguna-m1-vllm
```

## Single-node dev (not headline)

`scripts/serve.sh` targets one GPU for smaller experiments; do not publish single-node throughput as M.1 headline without OOM disclaimer.

## Future

A dedicated `vllm-laguna-m1-nvfp4-sm121` tag is optional if serve flags diverge from the DSV4 image defaults.