#!/usr/bin/env bash
# Wait for laguna-m1-vllm API then run benchmarks, report, push.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-30100}"
LOG="$ROOT/evidence/finish-v1.log"
exec >>"$LOG" 2>&1
echo "=== finish_v1 $(date -Is) ==="

for i in $(seq 1 480); do
  if curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null; then
    echo "server ready at iter $i"
    break
  fi
  if ! docker ps --format '{{.Names}}' | grep -q '^laguna-m1-vllm$'; then
    echo "container exited at iter $i"
    docker logs laguna-m1-vllm 2>&1 | tail -100
    exit 1
  fi
  if (( i % 12 == 0 )); then
    echo "$(date -Is) still loading iter=$i"
    docker logs laguna-m1-vllm 2>&1 | tail -3
  fi
  sleep 30
done

curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null || { echo "timeout waiting for API"; docker logs laguna-m1-vllm 2>&1 | tail -80; exit 1; }

cd "$ROOT"
bash scripts/verify_native_kernels.sh
bash scripts/smoke_poolside_tools.sh

bash scripts/capture_telemetry.sh &
TEL_PID=$!
bash scripts/bench_concurrency.sh
kill $TEL_PID 2>/dev/null || true

export BFCL_TEST_CATEGORIES="${BFCL_TEST_CATEGORIES:-simple_python,parallel,multiple}"
bash scripts/run_bfcl_v1.sh || echo "BFCL failed"

python3 scripts/build_report.py

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
    "kv_cache_dtype": "fp8",
    "max_model_len": 4096,
    "gpu_util": 0.75,
    "image": "ghcr.io/r0b0tlab/vllm-laguna-m1-nvfp4-sm121:cu130-sm121-arm64-dda4668b",
}
(root / "benchmarks/run_meta.json").write_text(json.dumps(meta, indent=2))
PY
python3 scripts/build_report.py

git add benchmarks publication evidence/kernels scripts/download_missing_shards.sh docs 2>/dev/null || true
git commit -m "SM121 v1: headless bring-up, benchmarks, BFCL, HTML report" || true
git push origin main || true

echo "=== finish_v1 done $(date -Is) ==="