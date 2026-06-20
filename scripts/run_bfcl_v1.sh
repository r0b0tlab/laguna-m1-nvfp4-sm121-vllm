#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export BFCL_PROJECT_ROOT="${BFCL_PROJECT_ROOT:-$ROOT/benchmarks/bfcl}"
export PORT="${PORT:-30100}"
export OPENAI_BASE_URL="http://127.0.0.1:${PORT}/v1"
export OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"
export BFCL_VLLM_MODEL="${BFCL_VLLM_MODEL:-laguna-m1-nvfp4}"
export BFCL_TEST_CATEGORIES="${BFCL_TEST_CATEGORIES:-$(tr '\n' ',' < "$ROOT/configs/bfcl_v1_categories.txt" | sed 's/,$//')}"
mkdir -p "$BFCL_PROJECT_ROOT"
if [[ ! -f "$BFCL_PROJECT_ROOT/.env" ]]; then
  {
    echo "OPENAI_API_KEY=${OPENAI_API_KEY}"
    echo "OPENAI_BASE_URL=${OPENAI_BASE_URL}"
  } > "$BFCL_PROJECT_ROOT/.env"
fi
curl -sf "${OPENAI_BASE_URL}/models" >/dev/null || { echo "Start vLLM first (scripts/serve.sh)"; exit 1; }
source "$ROOT/.venv/bin/activate"
python3 "$ROOT/scripts/bfcl_run.py" generate
python3 "$ROOT/scripts/bfcl_run.py" evaluate
python3 "$ROOT/scripts/build_report.py"
echo "BFCL results under $BFCL_PROJECT_ROOT/result and score/"
if [[ "${PUSH_GITHUB:-0}" == "1" ]]; then
  cd "$ROOT"
  git add AGENTS.md README.md benchmarks/ publication/html/index.html scripts/bfcl_run.py scripts/build_report.py scripts/capture_telemetry.sh docs/CONTAINER.md requirements-bfcl.txt configs/bfcl_v1_categories.txt evidence/bfcl-run.log 2>/dev/null || true
  git add benchmarks/bfcl/score benchmarks/bfcl/result 2>/dev/null || true
  if ! git diff --staged --quiet; then
    git commit -m "Laguna M.1: BFCL scores + HTML report (auto-publish)"
    git push origin main
  fi
fi