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

python3 scripts/extract_kv_metrics.py
python3 scripts/build_report.py
if [[ "${PUSH_GITHUB:-1}" == "1" ]]; then
  git add benchmarks/kv_cache_metrics.json benchmarks/run_meta.json publication/html/index.html \
    README.md AGENTS.md .gitignore scripts/build_report.py scripts/finish_publish.sh 2>/dev/null || true
  if ! git diff --staged --quiet; then
    git commit -m "Laguna M.1: remove BFCL from public report; throughput + KV only"
    git push origin main
  fi
fi
echo "finish_publish done"