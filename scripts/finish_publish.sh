#!/usr/bin/env bash
# Regenerate HTML and push main.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CANONICAL=laguna-m1-vllm
LEGACY=laguna_tp2
if docker ps -a --format '{{.Names}}' | grep -qx "$LEGACY"; then
  if ! docker ps -a --format '{{.Names}}' | grep -qx "$CANONICAL"; then
    docker rename "$LEGACY" "$CANONICAL" && echo "renamed $LEGACY -> $CANONICAL"
  fi
fi

# Pre-publish accuracy (GSM8K@100) unless skipped or results already fresh
SKIP_GSM8K="${SKIP_GSM8K:-0}"
GSM8K_RESULTS="$ROOT/benchmarks/lm_eval/gsm8k_100_results.json"
if [[ "$SKIP_GSM8K" != "1" ]]; then
  if [[ "${FORCE_GSM8K:-0}" == "1" ]] || [[ ! -f "$GSM8K_RESULTS" ]]; then
    bash "$ROOT/scripts/run_gsm8k_100.sh"
  else
    echo "GSM8K results exist — set FORCE_GSM8K=1 to re-run"
  fi
fi

python3 scripts/extract_kv_metrics.py
python3 scripts/build_report.py
if [[ "${PUSH_GITHUB:-1}" == "1" ]]; then
  git add benchmarks/kv_cache_metrics.json benchmarks/run_meta.json \
    benchmarks/lm_eval/gsm8k_100_results.json benchmarks/lm_eval/gsm8k_100_manifest.json \
    publication/html/index.html \
    README.md AGENTS.md docs/BENCHMARKS.md .gitignore \
    scripts/build_report.py scripts/finish_publish.sh scripts/run_gsm8k_100.sh \
    scripts/extract_gsm8k_results.py 2>/dev/null || true
  if ! git diff --staged --quiet; then
    git commit -m "Laguna M.1: GSM8K@100 + throughput/KV HTML report"
    git push origin main
  fi
fi
echo "finish_publish done"