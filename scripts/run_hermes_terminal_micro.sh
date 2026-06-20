#!/usr/bin/env bash
# Hermes-bench terminal micro: t01_terminal_smoke (5 tasks), real hermes-agent.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HB_REPO="${HERMES_BENCH_REPO:-$HOME/hermes-bench-tool-call}"
PORT="${PORT:-30100}"
MODEL="${MODEL:-laguna-m1-nvfp4}"
BASE_URL="http://127.0.0.1:${PORT}/v1"
LOG="$ROOT/evidence/hermes_terminal_micro.log"

curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null || {
  echo "Server not up at :${PORT}"
  exit 1
}

if [[ ! -d "$HB_REPO" ]]; then
  echo "Missing $HB_REPO — clone github.com/am423/hermes-bench-tool-call"
  exit 1
fi

export OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"
export HERMES_BENCH_REPO="$HB_REPO"

echo "=== hermesbench $MODEL t01_terminal_smoke $(date -Is) ===" | tee "$LOG"
date +%s > "$ROOT/evidence/hermes_terminal_micro.run_start"
cd "$HB_REPO"
python3 -m hermesbench run \
  --category t01_terminal_smoke \
  --model "$MODEL" \
  --base-url "$BASE_URL" \
  --real-agent 2>&1 | tee -a "$LOG"

python3 "$ROOT/scripts/extract_hermes_terminal_results.py" "$MODEL"
echo "=== hermes terminal micro done $(date -Is) ===" | tee -a "$LOG"