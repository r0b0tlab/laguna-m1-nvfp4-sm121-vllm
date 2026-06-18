# Laguna M.1 NVFP4 — memory / topology

## Single GB10 TP=1: **does not load** (verified 2026-06-18)

During `FusedMoE` NVFP4 weight creation, vLLM allocated **~113.15 GiB** PyTorch memory on a **121.69 GiB** unified pool and failed with:

`torch.OutOfMemoryError: Tried to allocate 512.00 MiB` (742 MiB free).

Conservative settings still OOM during **weight init** (not KV):

- `gpu_memory_utilization=0.75`, `max_model_len=4096`, `kv_cache_dtype=fp8`, `--enforce-eager`

**Conclusion:** Full `poolside/Laguna-M.1-NVFP4` (~124 GiB on disk, 225B-class MoE) requires **TP=2 across two GB10** nodes with the model mounted at the same path on both hosts.

## Dual GB10 TP=2 (active path)

| Setting | First boot |
|---------|------------|
| `tensor_parallel_size` | 2 |
| `distributed_executor_backend` | `mp` |
| `GPU_UTIL` | 0.82 |
| `MAX_MODEL_LEN` | 4096 |
| `KV_CACHE_DTYPE` | fp8 |
| `ENFORCE_EAGER` | 1 |
| NCCL | `NCCL_IB_GID_INDEX=3`, RoCE `rocep1s0f0`, `enp1s0f0np0` |

Launch: `scripts/serve_tp2_cluster.sh` (uses `spark-vllm-docker/launch-cluster.sh`).

Nodes: **192.168.100.10** (head), **192.168.100.11** (worker). Model path on **both**:

`/home/r0b0tdgx/models/llm/nvfp4/poolside/Laguna-M.1-NVFP4` → `/mnt/model`

## Ladder (after stable API)

1. fp8 KV @ 4096  
2. fp8 KV @ 8192  
3. nvfp4 KV @ 8192 if SM121 KV path works (see `docs/NVFP4_KV_SM121.md`)