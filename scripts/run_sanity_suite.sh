#!/usr/bin/env bash
# Minimal post-serve sanity: native kernels + API smoke + Hermes terminal micro (5 tasks).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LOG="${LOG:-$ROOT/evidence/sanity_suite.log}"
PORT="${PORT:-30100}"

exec > >(tee -a "$LOG") 2>&1
echo "=== sanity suite start $(date -Is) port=$PORT ==="

curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null || {
  echo "FAIL: API not up on :${PORT}"
  exit 1
}

bash "$ROOT/scripts/verify_native_kernels.sh"
bash "$ROOT/scripts/smoke_poolside_tools.sh"
bash "$ROOT/scripts/run_hermes_terminal_micro.sh"
python3 "$ROOT/scripts/extract_hermes_terminal_results.py"

echo "=== sanity suite PASS $(date -Is) ==="