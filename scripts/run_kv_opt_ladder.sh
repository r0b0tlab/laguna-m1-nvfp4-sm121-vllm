#!/usr/bin/env bash
# NVFP4 KV ladder + throughput tuning (TP=2 Ray). Logs to evidence/kv-opt-ladder.log
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/evidence/kv-opt-ladder.log"
exec > >(tee -a "$LOG") 2>&1
echo "=== kv-opt ladder $(date -Is) ==="

export PORT=30100 NAME=laguna_tp2 MODEL=laguna-m1-nvfp4
export DISTRIBUTED_EXECUTOR_BACKEND=ray LOAD_FORMAT=safetensors
export ENFORCE_EAGER=0 CUDAGRAPH_MODE=PIECEWISE
export MAX_MODEL_LEN=8192 DISTRIBUTED_TIMEOUT_SECONDS=7200
export KV_BLOCK_SIZE=256

wait_api() {
  for i in $(seq 1 360); do
    curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null && return 0
    if (( i % 6 == 0 )); then
      echo "$(date -Is) wait API i=$i"
      docker logs "$NAME" 2>&1 | grep -iE 'error|nvfp4|Loading|Uvicorn|Application' | tail -5 || true
    fi
    sleep 30
  done
  return 1
}

record_kv_fail() {
  docker logs "$NAME" 2>&1 | tail -60 >>"$ROOT/docs/NVFP4_KV_SM121.md" || true
  echo -e "\n## Ladder run $(date -Is)\nSee evidence/kv-opt-ladder.log\n" >>"$ROOT/docs/NVFP4_KV_SM121.md"
}

run_profile() {
  local tag="$1"
  shift
  export "$@"
  echo "=== PROFILE $tag KV=$KV_CACHE_DTYPE util=$GPU_UTIL seqs=$MAX_NUM_SEQS batched=$MAX_BATCHED ==="
  cd "$ROOT"
  docker rm -f "$NAME" 2>/dev/null || true
  ssh -o BatchMode=yes r0b0tdgx@192.168.100.11 "docker rm -f $NAME 2>/dev/null" || true
  bash scripts/serve_tp2_cluster.sh
  sleep 20
  docker exec "$NAME" pgrep -f 'vllm serve' >/dev/null 2>&1 || bash scripts/ensure_vllm_after_ray.sh
  if ! wait_api; then
    echo "PROFILE $tag FAILED: API timeout"
    docker logs "$NAME" 2>&1 | tail -40
    return 1
  fi
  export NAME PORT
  bash scripts/verify_native_kernels.sh
  bash scripts/smoke_poolside_tools.sh
  bash scripts/capture_telemetry.sh &
  TEL=$!
  bash scripts/bench_concurrency.sh
  kill "$TEL" 2>/dev/null || true
  for c in 1 2 4 5 8; do
    src="$ROOT/benchmarks/concurrency/chat-concurrency-c${c}.json"
    [[ -f "$src" ]] && cp "$src" "$ROOT/benchmarks/concurrency/chat-concurrency-c${c}-${tag}.json"
  done
  [[ -f "$ROOT/benchmarks/concurrency/chat-concurrency-summary.json" ]] && \
    cp "$ROOT/benchmarks/concurrency/chat-concurrency-summary.json" \
       "$ROOT/benchmarks/concurrency/chat-concurrency-summary-${tag}.json"
  echo "=== PROFILE $tag OK ==="
}

# NVFP4 KV attempt
if run_profile "nvfp4-kv" \
  KV_CACHE_DTYPE=nvfp4 GPU_UTIL=0.85 MAX_NUM_SEQS=8 MAX_BATCHED=8192; then
  echo "NVFP4_KV_STATUS=pass"
  BEST_TAG=nvfp4-kv
  BEST_KV=nvfp4
else
  echo "NVFP4_KV_STATUS=failed"
  record_kv_fail
  run_profile "fp8-tuned" \
    KV_CACHE_DTYPE=fp8 GPU_UTIL=0.88 MAX_NUM_SEQS=16 MAX_BATCHED=16384
  BEST_TAG=fp8-tuned
  BEST_KV=fp8
fi

python3 <<PY
import json, pathlib
root = pathlib.Path("$ROOT")
meta = json.loads((root/"benchmarks/run_meta.json").read_text()) if (root/"benchmarks/run_meta.json").exists() else {}
meta["headline_profile"] = "$BEST_TAG"
meta["headline_kv"] = "$BEST_KV"
meta["L1_fp8"] = {"max_model_len": 8192, "gpu_util": 0.85, "max_num_seqs": 8}
meta["nvfp4_attempt"] = {"max_model_len": 8192, "kv_cache_dtype": "nvfp4"}
meta["fp8_tuned"] = {"max_model_len": 8192, "gpu_util": 0.88, "max_num_seqs": 16, "max_num_batched_tokens": 16384}
(root/"benchmarks/run_meta.json").write_text(json.dumps(meta, indent=2)+"\n")
PY

python3 "$ROOT/scripts/build_report.py"
cd "$ROOT" && git add benchmarks docs publication scripts evidence/kv-opt-ladder.log 2>/dev/null; \
  git add benchmarks docs publication scripts && \
  git commit -m "NVFP4 KV ladder + fp8 tuned profile ($BEST_TAG)" && git push origin main || true
echo "=== ladder done headline=$BEST_TAG kv=$BEST_KV ==="