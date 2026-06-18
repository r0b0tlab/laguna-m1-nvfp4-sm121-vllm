#!/usr/bin/env python3
"""Build publication/html/index.html from benchmark JSON artifacts."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "publication" / "html" / "index.html"
KWH_PRICE = float(__import__("os").environ.get("ELECTRICITY_USD_PER_KWH", "0.12"))


def load_json(path: Path):
    if path.is_file():
        return json.loads(path.read_text())
    return None


def main():
    conc = load_json(ROOT / "benchmarks" / "concurrency" / "chat-concurrency-summary.json") or []
    bfcl_scores = list((ROOT / "benchmarks" / "bfcl" / "score").glob("**/*.json")) if (ROOT / "benchmarks" / "bfcl" / "score").exists() else []
    bfcl_summary = []
    for p in sorted(bfcl_scores)[:20]:
        try:
            bfcl_summary.append({"file": p.name, "data": json.loads(p.read_text())})
        except Exception:
            pass
    meta = load_json(ROOT / "benchmarks" / "run_meta.json") or {}
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    rows = ""
    for s in conc:
        c = s.get("concurrency")
        otps = s.get("output_tps")
        wall = s.get("wall_s") or 1
        out_tok = s.get("output_tokens") or 0
        power = meta.get("avg_power_w", 35)
        kwh = (power * wall) / 3600 / 1000
        cost = kwh * KWH_PRICE
        per_m = (cost / out_tok * 1e6) if out_tok else None
        otps_s = f"{otps:.2f}" if otps is not None else "—"
        per_m_s = f"{per_m:.4f}" if per_m is not None else "—"
        rows += f"<tr><td>c{c}</td><td>{otps_s}</td><td>{power:.0f} W†</td><td>{per_m_s}</td></tr>\n"

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Laguna M.1 NVFP4 — SM121 Report</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:ui-monospace,monospace;background:#0d1117;color:#c9d1d9;padding:16px;line-height:1.5;font-size:14px;overflow-x:hidden}}
h1{{color:#58a6ff;font-size:clamp(1.1rem,4vw,1.75rem)}}h2{{color:#79c0ff;font-size:1.1rem;margin:1.5rem 0 .75rem;border-bottom:1px solid #21262d;padding-bottom:.5rem}}
.sub{{color:#8b949e;margin:.5rem 0 1rem;font-size:.85rem}}.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:1rem;margin:.75rem 0}}
.table-wrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;min-width:480px;font-size:13px}}th,td{{padding:8px 10px;border-bottom:1px solid #21262d;text-align:left}}th{{color:#79c0ff}}
.badge{{display:inline-block;background:#238636;color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;margin:2px}}
</style></head><body>
<h1>Laguna M.1 NVFP4 on SM121</h1>
<p class="sub">Single GB10 · TP=1 · NVFP4 KV · vLLM · BFCL v1 · {ts}</p>
<p><span class="badge">poolside/Laguna-M.1-NVFP4</span> <span class="badge">BFCL public harness</span></p>
<h2>Throughput (chat completions)</h2>
<div class="table-wrap"><table><thead><tr><th>Concurrency</th><th>Output tok/s</th><th>Power</th><th>$/M out tok†</th></tr></thead><tbody>
{rows or '<tr><td colspan="4">Pending — run scripts/bench_concurrency.sh</td></tr>'}
</tbody></table></div>
<p class="sub">† Power from telemetry or meta default; electricity @ ${KWH_PRICE}/kWh.</p>
<h2>BFCL (function calling)</h2>
<div class="card"><pre style="white-space:pre-wrap;font-size:12px">{json.dumps(bfcl_summary, indent=2)[:8000] or 'Pending — run scripts/run_bfcl_v1.sh'}</pre></div>
<h2>Environment</h2>
<div class="card"><pre>{json.dumps(meta, indent=2)}</pre></div>
</body></html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()