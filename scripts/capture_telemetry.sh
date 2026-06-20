#!/usr/bin/env bash
# Sample GPU telemetry during a benchmark (GB10).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${OUT:-$ROOT/evidence/telemetry/gpu-sample.jsonl}"
DURATION="${DURATION:-120}"
INTERVAL="${INTERVAL:-2}"
mkdir -p "$(dirname "$OUT")"
echo "{\"event\":\"start\",\"ts\":\"$(date -Is)\",\"duration_s\":$DURATION}" >>"$OUT"
end=$((SECONDS + DURATION))
while (( SECONDS < end )); do
  if nvidia-smi --query-gpu=temperature.gpu,power.draw,utilization.gpu,memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | \
    awk -F', ' -v ts="$(date -Is)" '{gsub(/ /,"",$1); printf "{\"ts\":\"%s\",\"temp_c\":%s,\"power_w\":%s,\"gpu_util_pct\":%s,\"mem_used_mib\":%s}\n", ts,$1,$2,$3,$4}' >>"$OUT"; then
    :
  else
    echo "{\"ts\":\"$(date -Is)\",\"error\":\"nvidia-smi failed\"}" >>"$OUT"
  fi
  sleep "$INTERVAL"
done
echo "{\"event\":\"end\",\"ts\":\"$(date -Is)\"}" >>"$OUT"
echo "Wrote $OUT"