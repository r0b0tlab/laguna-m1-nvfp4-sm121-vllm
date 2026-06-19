#!/usr/bin/env bash
# Auto-launch Laguna TP=2 when Spark B SSH recovers. Idempotent.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/evidence/auto-tp2.log"
LOCK=/tmp/laguna_auto_tp2.lock
exec >>"$LOG" 2>&1
echo "=== auto check $(date -Is) ==="

flock -n "$LOCK" bash -c '
  if curl -sf http://127.0.0.1:30100/v1/models >/dev/null 2>&1; then
    echo "API already up"
    exit 0
  fi
  if docker ps --filter name=laguna_tp2 --filter status=running -q | grep -q .; then
    echo "laguna_tp2 already running (load in progress) — skip relaunch"
    exit 0
  fi
  if ! ssh -i /home/r0b0tdgx/.ssh/id_ed25519_shared -o BatchMode=yes -o ConnectTimeout=12 r0b0tdgx@192.168.100.11 hostname >/dev/null 2>&1; then
    echo "node2 SSH down — skip"
    exit 0
  fi
  echo "node2 SSH up — launching TP=2 Ray"
  docker rm -f laguna_tp2 2>/dev/null || true
  ssh -i /home/r0b0tdgx/.ssh/id_ed25519_shared -o BatchMode=yes r0b0tdgx@192.168.100.11 "docker rm -f laguna_tp2 2>/dev/null; sudo rm -f /dev/shm/*vllm* /dev/shm/*ray* 2>/dev/null" || true
  bash "'"$ROOT"'/scripts/serve_tp2_cluster.sh"
' || echo "another auto-tp2 holder running"