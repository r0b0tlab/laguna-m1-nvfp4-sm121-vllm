#!/usr/bin/env bash
# GSM8K subset (default 100) via lm-evaluation-harness against running vLLM OpenAI API.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-30100}"
MODEL="${MODEL:-laguna-m1-nvfp4}"
LIMIT="${LIMIT:-100}"
NUM_FEWSHOT="${NUM_FEWSHOT:-5}"
GSM8K_TASK="${GSM8K_TASK:-gsm8k}"
NUM_CONCURRENT="${NUM_CONCURRENT:-2}"
VENV="${VENV:-$ROOT/.venv-lmeval}"

BASE_URL="http://127.0.0.1:${PORT}/v1/chat/completions"
RAW_DIR="$ROOT/benchmarks/lm_eval/raw"
mkdir -p "$RAW_DIR"

curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null || {
  echo "Server not up at :${PORT} — start laguna-m1-vllm first"
  exit 1
}

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Creating $VENV and installing lm-eval..."
  uv venv "$VENV" --python 3.12
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  uv pip install "lm-eval>=0.4.7"
else
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
fi

if ! python -m lm_eval --tasks list 2>/dev/null | grep -qx "$GSM8K_TASK"; then
  echo "Task $GSM8K_TASK not found; available gsm8k tasks:"
  python -m lm_eval --tasks list 2>/dev/null | grep -i gsm8k || true
  if python -m lm_eval --tasks list 2>/dev/null | grep -qx "gsm8k_cot"; then
    GSM8K_TASK=gsm8k_cot
    echo "Using GSM8K_TASK=$GSM8K_TASK"
  fi
fi

STAMP="$(date +%Y%m%dT%H%M%S)"
RAW_OUT="$RAW_DIR/gsm8k_100_${STAMP}.json"
LOG="$ROOT/evidence/gsm8k_100.log"

echo "=== GSM8K limit=$LIMIT fewshot=$NUM_FEWSHOT task=$GSM8K_TASK $(date -Is) ===" | tee "$LOG"

python -m lm_eval \
  --model local-chat-completions \
  --model_args "model=${MODEL},base_url=${BASE_URL},num_concurrent=${NUM_CONCURRENT},max_retries=3,tokenized_requests=False" \
  --tasks "$GSM8K_TASK" \
  --num_fewshot "$NUM_FEWSHOT" \
  --apply_chat_template \
  --batch_size auto \
  --limit "$LIMIT" \
  --gen_kwargs "max_gen_toks=2048,temperature=0" \
  --output_path "$RAW_OUT" 2>&1 | tee -a "$LOG"

python3 "$ROOT/scripts/extract_gsm8k_results.py" "$RAW_OUT"
echo "=== GSM8K done $(date -Is) ===" | tee -a "$LOG"