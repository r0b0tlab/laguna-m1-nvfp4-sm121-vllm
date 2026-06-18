#!/usr/bin/env bash
set -euo pipefail
PORT=${PORT:-30100}
BASE="http://127.0.0.1:${PORT}/v1"
MODEL=${MODEL:-laguna-m1-nvfp4}
curl -sf "${BASE}/models" >/dev/null || { echo "Server not up at $BASE"; exit 1; }
python3 - <<PY
import json, urllib.request
url = "${BASE}/chat/completions"
payload = {
  "model": "${MODEL}",
  "messages": [{"role": "user", "content": "What is 2+2? Reply with one number only."}],
  "max_tokens": 32,
  "temperature": 0,
}
req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=120) as r:
    data = json.loads(r.read())
print(json.dumps(data, indent=2)[:2000])
PY
echo "Smoke OK"