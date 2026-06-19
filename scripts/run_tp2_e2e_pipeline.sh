#!/usr/bin/env bash
# End-to-end after stable API: benches → optional KV/ctx ladder relaunch → BFCL → HTML.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/evidence/e2e-pipeline.log"
exec > >(tee -a "$LOG") 2>&1
echo "=== e2e pipeline $(date -Is) ==="

export PORT="${PORT:-30100}"
export NAME="${NAME:-laguna_tp2}"
export MODEL="${MODEL:-laguna-m1-nvfp4}"

curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null || { echo "API not ready"; exit 1; }

cd "$ROOT"
if [[ "${SKIP_VERIFY:-0}" != "1" ]]; then
  bash scripts/verify_native_kernels.sh
  bash scripts/smoke_poolside_tools.sh
fi

# L0: first-boot config (fp8 KV @ 4096, eager)
export OPT_PROFILE="${OPT_PROFILE:-L0}"
mkdir -p benchmarks/concurrency
bash scripts/capture_telemetry.sh &
TEL=$!
bash scripts/bench_concurrency.sh
kill "$TEL" 2>/dev/null || true
for f in benchmarks/concurrency/*.json; do
  [[ -f "$f" && "$f" != *-L0.json && "$f" != *-L1.json ]] && cp "$f" "${f%.json}-${OPT_PROFILE}.json" || true
done

# L1 optimized serve (only if OPT_RELUNCH=1 and L0 c1 OK)
if [[ "${OPT_RELAUNCH:-0}" == "1" ]]; then
  echo "=== relaunch L1: PIECEWISE graphs, 8192, gpu 0.85, max_seqs 8 ==="
  export ENFORCE_EAGER=0
  export CUDAGRAPH_MODE=PIECEWISE
  export MAX_MODEL_LEN=8192
  export MAX_NUM_SEQS=8
  export MAX_BATCHED=8192
  export GPU_UTIL=0.85
  bash scripts/serve_tp2_cluster.sh
  for i in $(seq 1 360); do
    curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null && break
    sleep 30
  done
  export OPT_PROFILE=L1
  bash scripts/bench_concurrency.sh
fi

export BFCL_TEST_CATEGORIES="${BFCL_TEST_CATEGORIES:-simple_python,parallel,multiple}"
bash scripts/run_bfcl_v1.sh || true
python3 scripts/build_report.py

git add benchmarks publication evidence docs 2>/dev/null || true
git commit -m "SM121 TP=2 Ray: e2e benches BFCL HTML (${OPT_PROFILE})" || true
git push origin main || true
echo "=== e2e done $(date -Is) ==="