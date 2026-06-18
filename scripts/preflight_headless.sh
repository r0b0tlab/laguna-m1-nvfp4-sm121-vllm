#!/usr/bin/env bash
# Mandatory gate before Laguna M.1 first load on GB10 (headless).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODEL_DIR="${MODEL_DIR:-/home/r0b0tdgx/models/llm/nvfp4/poolside/Laguna-M.1-NVFP4}"
MIN_AVAIL_GIB="${MIN_AVAIL_GIB:-90}"

fail() { echo "PREFLIGHT FAIL: $*" >&2; exit 1; }
ok() { echo "PREFLIGHT OK: $*"; }

[[ -f "$MODEL_DIR/config.json" ]] || fail "missing config.json at $MODEL_DIR"

if pgrep -af 'hf download.*Laguna-M.1-NVFP4|huggingface-cli download.*Laguna-M.1-NVFP4' >/dev/null 2>&1; then
  fail "HF download still running for Laguna — wait or stop before serve"
fi

INDEX="$MODEL_DIR/model.safetensors.index.json"
[[ -f "$INDEX" ]] || fail "missing model.safetensors.index.json"

python3 - <<PY || fail "weight shard verification failed"
import json, pathlib, sys
p = pathlib.Path("$MODEL_DIR")
idx = json.load(open(p / "model.safetensors.index.json"))
shards = sorted(set(idx.get("weight_map", {}).values()))
missing = [s for s in shards if not (p / s).exists()]
print(f"expected_shards={len(shards)} disk={len(list(p.glob('model-*.safetensors')))} missing={len(missing)}")
if missing:
    print("missing_files:", missing[:10], file=sys.stderr)
    sys.exit(1)
PY

avail=$(awk '/MemAvailable:/ {print int($2/1024/1024)}' /proc/meminfo)
echo "MemAvailable_GiB=$avail (min $MIN_AVAIL_GIB)"
[[ "$avail" -ge "$MIN_AVAIL_GIB" ]] || fail "MemAvailable ${avail}GiB < ${MIN_AVAIL_GIB}GiB — stop competitors or reboot headless"

if docker ps -a --format '{{.Names}}' | grep -q '^laguna-m1-vllm$'; then
  st=$(docker inspect -f '{{.State.Status}}' laguna-m1-vllm 2>/dev/null || echo missing)
  echo "laguna-m1-vllm status=$st (rm -f if exited/stale before relaunch)"
fi

if journalctl -k --since "30 min ago" 2>/dev/null | grep -qi 'oom-kill'; then
  echo "WARN: recent kernel oom-kill in last 30m — prefer reboot before first load" >&2
fi

ok "weights complete, download idle, memory gate passed"