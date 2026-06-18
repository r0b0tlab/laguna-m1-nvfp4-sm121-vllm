#!/usr/bin/env bash
# Wait for full weights + idle HF download, then run v1 pipeline (headless-safe).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODEL_DIR="${MODEL_DIR:-/home/r0b0tdgx/models/llm/nvfp4/poolside/Laguna-M.1-NVFP4}"
LOG="$ROOT/evidence/wait-then-v1.log"
exec >>"$LOG" 2>&1

echo "=== wait_weights_then_v1 $(date -Is) ==="

while true; do
  if pgrep -af 'hf download.*Laguna-M.1-NVFP4' >/dev/null 2>&1; then
    n=$(ls "$MODEL_DIR"/model-*.safetensors 2>/dev/null | wc -l)
    echo "$(date -Is) hf download active shards=$n"
    sleep 60
    continue
  fi
  if bash "$ROOT/scripts/preflight_headless.sh" 2>/dev/null; then
    echo "preflight passed — starting pipeline"
    break
  fi
  n=$(ls "$MODEL_DIR"/model-*.safetensors 2>/dev/null | wc -l)
  echo "$(date -Is) preflight not ready shards=$n"
  sleep 120
done

cd "$ROOT"
exec ./scripts/run_v1_pipeline.sh