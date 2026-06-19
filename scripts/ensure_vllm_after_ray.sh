#!/usr/bin/env bash
# After launch-cluster (Ray): copy fixed launch script and start vllm if missing.
set -euo pipefail
NAME="${NAME:-laguna_tp2}"
SPARK="${SPARK:-/home/r0b0tdgx/spark-vllm-docker}"
LAUNCH="$SPARK/examples/laguna-m1-launch.sh"
[[ -f "$LAUNCH" ]] || exit 0
sleep 5
if docker exec "$NAME" pgrep -f 'vllm serve' >/dev/null 2>&1; then
  echo "vllm already running in $NAME"
  exit 0
fi
docker cp "$LAUNCH" "$NAME:/workspace/exec-script.sh"
docker exec "$NAME" chmod +x /workspace/exec-script.sh
docker exec -d "$NAME" bash -c '/workspace/exec-script.sh >> /proc/1/fd/1 2>&1'
echo "dispatched vllm in $NAME"