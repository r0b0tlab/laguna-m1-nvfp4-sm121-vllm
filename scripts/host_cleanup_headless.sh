#!/usr/bin/env bash
# GB10 headless prep for large MoE load — keeps Laguna hf download + wait_weights_then_v1.
set -euo pipefail
LOG="${1:-/home/r0b0tdgx/projects/laguna-m1-nvfp4-sm121-vllm/evidence/host-cleanup.log}"
exec > >(tee -a "$LOG") 2>&1
echo "=== host cleanup $(date -Is) ==="

KEEP_PATTERNS='hf download.*Laguna-M.1-NVFP4|wait_weights_then_v1|run_v1_pipeline'

free -h | head -2

# User services (not needed for inference)
systemctl --user stop hermes-gateway.service 2>/dev/null || true
systemctl --user stop snap.snap-store.snap-store.service 2>/dev/null || true

# Obvious desktop bloat (ignore errors if gdm already stopping)
pkill -f snap-store 2>/dev/null || true
pkill -f gnome-control-center 2>/dev/null || true
pkill -f evolution-alarm-notify 2>/dev/null || true
pkill -f gnome-terminal-server 2>/dev/null || true

# Stop display manager (kills GNOME shell, Xorg, mutter, etc.)
if systemctl is-active --quiet gdm3 2>/dev/null; then
  sudo systemctl stop gdm3
  echo "gdm3 stopped"
elif systemctl is-active --quiet gdm 2>/dev/null; then
  sudo systemctl stop gdm
  echo "gdm stopped"
else
  echo "gdm already inactive"
fi

# Optional: multi-user target if gdm respawns (usually not needed after stop)
# sudo systemctl isolate multi-user.target

# Stop idle inference containers (none should be running pre-serve)
docker ps -q | while read -r id; do
  name=$(docker inspect -f '{{.Names}}' "$id" 2>/dev/null || echo "")
  case "$name" in
    *laguna*) echo "keep docker $name" ;;
    *) echo "stopping docker $name"; docker stop "$id" 2>/dev/null || true ;;
  esac
done

sync
if [[ -w /proc/sys/vm/drop_caches ]]; then
  echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null
  echo "page cache dropped"
fi

echo "--- kept processes ---"
pgrep -af "$KEEP_PATTERNS" || echo "(none matched — check manually)"

echo "--- after ---"
free -h | head -2
echo "=== done $(date -Is) ==="