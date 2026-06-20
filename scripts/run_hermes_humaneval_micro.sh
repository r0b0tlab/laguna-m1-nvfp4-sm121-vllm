#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HB_REPO="${HERMES_BENCH_REPO:-$HOME/hermes-bench-tool-call}"
PORT="${PORT:-30100}"
MODEL="${MODEL:-laguna-m1-nvfp4}"
LIMIT="${HUMANEVAL_MICRO_LIMIT:-10}"
LOG="$ROOT/evidence/hermes_humaneval_micro.log"

curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null || exit 1
export OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"
export HERMES_BENCH_REPO="$HB_REPO"
export HUMANEVAL_MICRO_LIMIT="$LIMIT"

python3 "$ROOT/scripts/generate_humaneval_hermes_tasks.py"

echo "=== hermes HumanEval micro limit=$LIMIT $(date -Is) ===" | tee "$LOG"
date +%s > "$ROOT/evidence/hermes_humaneval_micro.run_start"
cd "$HB_REPO"
python3 -m hermesbench run \
  --category t13_humaneval_micro \
  --model "$MODEL" \
  --base-url "http://127.0.0.1:${PORT}/v1" \
  --real-agent 2>&1 | tee -a "$LOG"

python3 "$ROOT/scripts/extract_hermes_humaneval_results.py" "$MODEL"
echo "=== hermes humaneval micro done $(date -Is) ===" | tee -a "$LOG"