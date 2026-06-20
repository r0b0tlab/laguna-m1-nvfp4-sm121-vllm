#!/usr/bin/env bash
# HumanEval@N standalone via lm-eval (humaneval_instruct, pass@1).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-30100}"
MODEL="${MODEL:-laguna-m1-nvfp4}"
LIMIT="${LIMIT:-10}"
TASK="${HUMANEVAL_TASK:-humaneval_instruct}"
NUM_CONCURRENT="${NUM_CONCURRENT:-2}"
VENV="${VENV:-$ROOT/.venv-lmeval}"

BASE_URL="http://127.0.0.1:${PORT}/v1/chat/completions"
RAW_DIR="$ROOT/benchmarks/lm_eval/raw"
mkdir -p "$RAW_DIR"

curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null || { echo "Server not up"; exit 1; }

source "$VENV/bin/activate"
python -c "import tenacity" 2>/dev/null || uv pip install "lm-eval[api]>=0.4.7"

STAMP="$(date +%Y%m%dT%H%M%S)"
RAW_OUT="$RAW_DIR/humaneval_micro_${STAMP}.json"
LOG="$ROOT/evidence/humaneval_micro.log"

echo "=== HumanEval standalone limit=$LIMIT task=$TASK $(date -Is) ===" | tee "$LOG"

python -m lm_eval \
  --model local-chat-completions \
  --model_args "model=${MODEL},base_url=${BASE_URL},num_concurrent=${NUM_CONCURRENT},max_retries=3,tokenized_requests=False" \
  --tasks "$TASK" \
  --apply_chat_template \
  --batch_size auto \
  --limit "$LIMIT" \
  --output_path "$RAW_OUT" 2>&1 | tee -a "$LOG"

LATEST="$(ls -t "$RAW_DIR"/humaneval_micro_*.json 2>/dev/null | head -1)"
python3 "$ROOT/scripts/extract_humaneval_results.py" "$LATEST"
echo "=== HumanEval standalone done $(date -Is) ===" | tee -a "$LOG"