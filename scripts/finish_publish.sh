#!/usr/bin/env bash
# Regenerate HTML (KV + BFCL) and push main. Run after BFCL completes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 scripts/extract_kv_metrics.py
python3 scripts/build_report.py
if [[ "${PUSH_GITHUB:-1}" == "1" ]]; then
  git add benchmarks/kv_cache_metrics.json publication/html/index.html benchmarks/bfcl/ scripts/extract_kv_metrics.py scripts/build_report.py scripts/run_bfcl_v1.sh scripts/finish_publish.sh 2>/dev/null || true
  git add benchmarks/bfcl/score benchmarks/bfcl/result evidence/bfcl-run.log 2>/dev/null || true
  if ! git diff --staged --quiet; then
    git commit -m "Laguna M.1: KV cache metrics in HTML + BFCL report"
    git push origin main
  fi
fi
echo "finish_publish done"