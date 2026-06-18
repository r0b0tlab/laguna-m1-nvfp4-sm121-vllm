#!/usr/bin/env bash
set -euo pipefail
MODEL_DIR="${MODEL_DIR:-/home/r0b0tdgx/models/llm/nvfp4/poolside/Laguna-M.1-NVFP4}"
LOG="${LOG:-/home/r0b0tdgx/projects/laguna-m1-nvfp4-sm121-vllm/evidence/download-missing.log}"
exec >>"$LOG" 2>&1
echo "=== missing shard download $(date -Is) ==="
MISSING=(
  model-00008-of-00028.safetensors
  model-00024-of-00028.safetensors
  model-00025-of-00028.safetensors
  model-00026-of-00028.safetensors
  model-00027-of-00028.safetensors
)
for f in "${MISSING[@]}"; do
  if [[ -f "$MODEL_DIR/$f" ]]; then
    echo "skip existing $f"
    continue
  fi
  echo "fetch $f"
  ~/.local/bin/hf download poolside/Laguna-M.1-NVFP4 "$f" --local-dir "$MODEL_DIR"
done
n=$(ls "$MODEL_DIR"/model-*.safetensors | wc -l)
echo "shards_on_disk=$n"
bash /home/r0b0tdgx/projects/laguna-m1-nvfp4-sm121-vllm/scripts/preflight_headless.sh
echo "=== done $(date -Is) ==="