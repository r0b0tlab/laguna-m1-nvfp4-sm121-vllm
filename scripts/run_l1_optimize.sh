#!/usr/bin/env bash
# L1 optimized serve (8192, graphs, 0.85 util) + bench. Run after L0 e2e or when API stable.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/evidence/l1-optimize.log"
exec > >(tee -a "$LOG") 2>&1
echo "=== L1 optimize $(date -Is) ==="

# Wait for L0 e2e bench to release API (optional)
while pgrep -f 'run_tp2_e2e_pipeline|http_chat_bench' >/dev/null 2>&1; do
  echo "waiting for L0 e2e bench to finish..."
  sleep 30
done

export PORT=30100 NAME=laguna_tp2 MODEL=laguna-m1-nvfp4
export ENFORCE_EAGER=0 CUDAGRAPH_MODE=PIECEWISE
export MAX_MODEL_LEN=8192 MAX_NUM_SEQS=8 MAX_BATCHED=8192 GPU_UTIL=0.85
export KV_CACHE_DTYPE=fp8 LOAD_FORMAT=safetensors DISTRIBUTED_EXECUTOR_BACKEND=ray

cd "$ROOT"
bash scripts/serve_tp2_cluster.sh

# launch-cluster Ray mode may not start vllm (exec-script); ensure serve runs
sleep 15
if ! docker exec "$NAME" pgrep -f 'vllm serve' >/dev/null 2>&1; then
  echo "starting vllm in head container (post-Ray)"
  docker cp "$ROOT/../spark-vllm-docker/examples/laguna-m1-launch.sh" "$NAME:/workspace/exec-script.sh" 2>/dev/null || \
    docker cp "/home/r0b0tdgx/spark-vllm-docker/examples/laguna-m1-launch.sh" "$NAME:/workspace/exec-script.sh"
  docker exec "$NAME" chmod +x /workspace/exec-script.sh
  docker exec -d "$NAME" bash -c 'export ENFORCE_EAGER=0 CUDAGRAPH_MODE=PIECEWISE MAX_MODEL_LEN=8192 MAX_NUM_SEQS=8 MAX_BATCHED=8192 GPU_UTIL=0.85 KV_CACHE_DTYPE=fp8 PORT=30100; /workspace/exec-script.sh >> /proc/1/fd/1 2>&1'
fi

for i in $(seq 1 480); do
  if curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null; then
    echo "L1 API ready iter=$i"
    break
  fi
  if (( i % 6 == 0 )); then
    echo "$(date -Is) waiting L1 API iter=$i"
    docker logs laguna_tp2 2>&1 | grep 'Loading safetensors' | tail -1 || true
  fi
  sleep 30
done
curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null || exit 1

bash scripts/verify_native_kernels.sh
bash scripts/smoke_poolside_tools.sh

export OPT_PROFILE=L1
mkdir -p benchmarks/concurrency
bash scripts/capture_telemetry.sh &
TEL=$!
bash scripts/bench_concurrency.sh
kill "$TEL" 2>/dev/null || true
for f in benchmarks/concurrency/*.json; do
  [[ -f "$f" && "$f" != *-L0.json && "$f" != *-L1.json ]] && cp "$f" "${f%.json}-L1.json" || true
done

python3 - <<'PY'
import json, glob, pathlib
root = pathlib.Path("/home/r0b0tdgx/projects/laguna-m1-nvfp4-sm121-vllm/benchmarks/concurrency")
def load(pat):
    for p in sorted(root.glob(pat)):
        return json.loads(p.read_text())
    return None
l0 = load("*-L0.json") or load("chat-concurrency-c1.json")
l1 = load("*-L1.json")
if l0 and l1 and l0.get("concurrency")==1 and l1.get("concurrency")==1:
    r = l1["output_tps"]/l0["output_tps"]
    print(f"L1/L0 c1 output_tps ratio: {r:.3f}")
    if r < 0.9:
        print("WARN: >10% regression vs L0")
PY

echo "=== L1 done $(date -Is) ==="