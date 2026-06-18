# Memory / VRAM ladder (single GB10 TP=1)

Fill after `scripts/serve.sh` bring-up attempts.

| max_model_len | KV dtype | gpu_memory_utilization | Load OK | Notes |
|---------------|----------|------------------------|---------|-------|
| 8192 | nvfp4 | 0.85 | TBD | v1 default |
| 16384 | nvfp4 | 0.85 | TBD | |
| 32768 | nvfp4 | 0.85 | TBD | |

If `nvfp4` KV fails on SM121, record error in `docs/NVFP4_KV_SM121.md` and run FP8 baseline at same lengths.