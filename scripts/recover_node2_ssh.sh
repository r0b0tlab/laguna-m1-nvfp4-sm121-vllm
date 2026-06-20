#!/usr/bin/env bash
# Recover Spark B (192.168.100.11) when SSH banner hangs after wedged vLLM/NCCL load.
set -euo pipefail
WORKER_IPS=(192.168.100.11 192.168.100.15)
SSH_KEY="${SSH_KEY:-/home/r0b0tdgx/.ssh/id_ed25519_shared}"
MAC="${WORKER_MAC:-48:21:0b:96:89:ad}"
IFACE="${WOL_IFACE:-enp1s0f0np0}"

echo "=== node2 recovery $(date -Is) ==="

for ip in "${WORKER_IPS[@]}"; do
  if ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=8 "r0b0tdgx@${ip}" 'hostname' 2>/dev/null; then
    echo "SSH OK on $ip"
    ssh -i "$SSH_KEY" -o BatchMode=yes "r0b0tdgx@${ip}" \
      'docker rm -f laguna-m1-vllm laguna_tp2 2>/dev/null; sudo rm -f /dev/shm/*vllm* /dev/shm/*ray* 2>/dev/null; sudo systemctl restart ssh || true'
    exit 0
  fi
done

if command -v wakeonlan >/dev/null 2>&1; then
  echo "Sending Wake-on-LAN to $MAC via $IFACE"
  wakeonlan -i 192.168.100.255 -p 9 "$MAC" || wakeonlan "$MAC"
fi

echo "SSH still down. On Spark B console run:"
echo "  sudo reboot"
echo "Or from Spark B keyboard: docker rm -f laguna-m1-vllm laguna_tp2; sudo systemctl restart ssh"
exit 1