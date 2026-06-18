#!/usr/bin/env bash
set -euo pipefail
SRC="${SRC:-/home/r0b0tdgx/models/llm/nvfp4/poolside/Laguna-M.1-NVFP4}"
DST_HOST="${DST_HOST:-r0b0tdgx@192.168.100.11}"
SSH_KEY="${SSH_KEY:-/home/r0b0tdgx/.ssh/id_ed25519_shared}"
LOG="${LOG:-/home/r0b0tdgx/projects/laguna-m1-nvfp4-sm121-vllm/evidence/rsync-node2.log}"
exec >>"$LOG" 2>&1
echo "=== rsync to node2 $(date -Is) ==="
ssh -i "$SSH_KEY" -o BatchMode=yes "$DST_HOST" "mkdir -p '$SRC'"
rsync -az --partial --info=stats2 \
  -e "ssh -i $SSH_KEY -o BatchMode=yes" \
  "$SRC/" "$DST_HOST:$SRC/"
echo "=== rsync done $(date -Is) ==="
bash /home/r0b0tdgx/projects/laguna-m1-nvfp4-sm121-vllm/scripts/preflight_headless.sh 2>/dev/null || true