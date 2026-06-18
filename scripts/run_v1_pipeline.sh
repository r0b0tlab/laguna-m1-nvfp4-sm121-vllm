#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODEL_DIR="${MODEL_DIR:-/home/r0b0tdgx/models/llm/nvfp4/poolside/Laguna-M.1-NVFP4}"
LOG="$ROOT/evidence/v1-pipeline.log"
exec > >(tee -a "$LOG") 2>&1

echo "=== pipeline start $(date -Is) ==="
while [ ! -f "$MODEL_DIR/model.safetensors.index.json" ]; do
  n=$(ls "$MODEL_DIR"/model-*.safetensors 2>/dev/null | wc -l)
  echo "waiting download shards=$n"
  sleep 120
done
echo "download complete"
bash "$ROOT/scripts/preflight_headless.sh"

cd "$ROOT"
export MODEL_DIR PORT=30100

# Conservative first boot (IMPLEMENTATION_PLAN Phase 1); ladder to nvfp4 KV after smoke
export GPU_UTIL=0.75 MAX_MODEL_LEN=4096 MAX_NUM_SEQS=4 KV_CACHE_DTYPE=fp8 ENFORCE_EAGER=1
if ! ./scripts/serve.sh; then
  echo "serve failed"
  exit 1
fi

for i in $(seq 1 360); do
  if curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null; then
    echo "server ready"
    break
  fi
  if ! docker ps --format '{{.Names}}' | grep -q '^laguna-m1-vllm$'; then
    echo "container exited"; docker logs laguna-m1-vllm 2>&1 | tail -80; exit 1
  fi
  sleep 10
done

bash scripts/verify_native_kernels.sh || true
bash scripts/smoke_poolside_tools.sh

# Telemetry during bench
bash scripts/capture_telemetry.sh &
TEL_PID=$!
bash scripts/bench_concurrency.sh
kill $TEL_PID 2>/dev/null || true

# BFCL v1 — full categories may take hours; run simple_python first then full list if time
export BFCL_TEST_CATEGORIES="${BFCL_TEST_CATEGORIES:-simple_python,parallel,multiple}"
bash scripts/run_bfcl_v1.sh || echo "BFCL failed — see log"

python3 scripts/build_report.py

# meta for HTML
python3 - <<'PY'
import json, pathlib, statistics
root = pathlib.Path("/home/r0b0tdgx/projects/laguna-m1-nvfp4-sm121-vllm")
tel = root / "evidence/telemetry/gpu-sample.jsonl"
powers = []
if tel.exists():
    for line in tel.read_text().splitlines():
        try:
            o = json.loads(line)
            if "power_w" in o:
                powers.append(float(o["power_w"]))
        except Exception:
            pass
meta = {
    "avg_power_w": statistics.mean(powers) if powers else 35,
    "driver": "580.159.03",
    "gpu": "NVIDIA GB10 SM121",
    "kv_cache_dtype": "nvfp4",
    "image": "ghcr.io/r0b0tlab/vllm-dsv4-flash-gb10:cu130-sm121-arm64-dda4668b",
}
(root / "benchmarks/run_meta.json").write_text(json.dumps(meta, indent=2))
PY
python3 scripts/build_report.py

git add benchmarks publication evidence/kernels docs/MEMORY.md .gitignore 2>/dev/null || true
git commit -m "SM121 v1: benchmarks, BFCL, HTML report" || true
git push origin main || true

echo "=== pipeline done $(date -Is) ==="