# NVFP4 KV on SM121 (Laguna M.1)

## Checkpoint default

`poolside/Laguna-M.1-NVFP4` declares `kv_cache_scheme.num_bits: 8` (FP8-calibrated KV). First TP=2 boot uses `--kv-cache-dtype fp8`.

## nvfp4 KV ladder (after stable fp8 API)

1. Restart with `KV_CACHE_DTYPE=nvfp4` in launch env.
2. Pass if: server starts, logs show nvfp4 KV active, smoke + tool-call OK, no `NotImplementedError` / `TllmGenFmhaRunner SM12.1`.
3. If blocked: headline stays **fp8 KV**; cite log excerpt here.

## Step 3.7 precedent

NVFP4 KV failed on SM12.1 via `TllmGenFmhaRunner` (FlashInfer). Laguna uses FLASHINFER attention — behavior may differ; verify empirically.