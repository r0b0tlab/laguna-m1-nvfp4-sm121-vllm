#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PORT=${PORT:-30100}
python3 scripts/http_chat_bench.py \
  --base-url "http://127.0.0.1:${PORT}/v1" \
  --model "${MODEL:-laguna-m1-nvfp4}" \
  --outdir benchmarks/concurrency \
  --concurrency 1 --concurrency 2 --concurrency 4 --concurrency 5 --concurrency 8 \
  --requests-per-concurrency 4 \
  --max-tokens 128 \
  --timeout 900