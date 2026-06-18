#!/usr/bin/env bash
# Conservative first boot for Laguna M.1 on single GB10 (unified memory).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
bash scripts/preflight_headless.sh

export GPU_UTIL="${GPU_UTIL:-0.75}"
export MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
export MAX_NUM_SEQS="${MAX_NUM_SEQS:-4}"
export MAX_BATCHED="${MAX_BATCHED:-4096}"
export KV_CACHE_DTYPE="${KV_CACHE_DTYPE:-fp8}"
export ENFORCE_EAGER="${ENFORCE_EAGER:-1}"
export PORT="${PORT:-30100}"

echo "First-boot serve: util=$GPU_UTIL len=$MAX_MODEL_LEN seqs=$MAX_NUM_SEQS kv=$KV_CACHE_DTYPE eager=$ENFORCE_EAGER"
exec ./scripts/serve.sh