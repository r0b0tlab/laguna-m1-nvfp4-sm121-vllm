#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/evidence/tp2-bringup.log"
exec >>"$LOG" 2>&1
echo "=== bringup wait $(date -Is) ==="
PORT="${PORT:-30100}"
NAME="${NAME:-laguna_tp2}"
for i in $(seq 1 480); do
  if curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
    echo "API ready iter=$i"
    cd "$ROOT"
    export NAME PORT
    bash scripts/verify_native_kernels.sh
    bash scripts/smoke_poolside_tools.sh
    echo "=== bringup done $(date -Is) ==="
    exit 0
  fi
  st=$(docker inspect -f '{{.State.Status}}' "$NAME" 2>/dev/null || echo missing)
  if [[ "$st" == "exited" ]]; then
    echo "container exited at iter=$i"
    docker logs "$NAME" 2>&1 | tail -80
    exit 1
  fi
  if (( i % 12 == 0 )); then
    echo "$(date -Is) waiting iter=$i status=$st"
    docker logs "$NAME" 2>&1 | tail -8 || true
  fi
  sleep 30
done
echo "timeout waiting for API"
docker logs "$NAME" 2>&1 | tail -60
exit 1