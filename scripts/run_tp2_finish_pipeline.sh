#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/evidence/tp2-finish-pipeline.log"
exec >>"$LOG" 2>&1
echo "=== tp2 pipeline $(date -Is) ==="

bash "$ROOT/scripts/sync_weights_to_node2.sh"
bash "$ROOT/scripts/serve_tp2_cluster.sh"
sleep 15

PORT=30100
for i in $(seq 1 480); do
  if curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null; then
    echo "TP=2 server ready iter=$i"
    break
  fi
  if (( i % 12 == 0 )); then
    echo "$(date -Is) waiting API iter=$i"
    docker logs "${NAME:-laguna-m1-vllm}" 2>&1 | tail -5 || true
  fi
  sleep 30
done
curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null || exit 1

cd "$ROOT"
export PORT NAME=${NAME:-laguna-m1-vllm}
bash scripts/verify_native_kernels.sh || true
bash scripts/smoke_poolside_tools.sh
bash scripts/capture_telemetry.sh &
TEL=$!
bash scripts/bench_concurrency.sh
kill $TEL 2>/dev/null || true
python3 scripts/extract_kv_metrics.py
if [[ "${SKIP_GSM8K:-0}" != "1" ]]; then
  bash scripts/run_gsm8k_100.sh
fi
python3 scripts/build_report.py
git add benchmarks publication docs scripts evidence/kernels 2>/dev/null || true
git commit -m "Laguna M.1 TP=2: concurrency, GSM8K@100 gate, HTML report" || true
git push origin main || true
echo "=== tp2 pipeline done $(date -Is) ==="