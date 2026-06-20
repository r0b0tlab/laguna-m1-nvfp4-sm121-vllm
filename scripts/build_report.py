#!/usr/bin/env python3
"""Build publication/html/index.html from benchmark JSON artifacts."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "publication" / "html" / "index.html"


def load_json(path: Path):
    if path.is_file():
        return json.loads(path.read_text())
    return None


def parse_telemetry_jsonl(path: Path) -> dict:
    temps, powers, utils = [], [], []
    if not path.is_file():
        return {}
    for line in path.read_text().splitlines():
        if "temp_c" not in line:
            continue
        m_t = re.search(r"temp_c[\"']?\s*:\s*(\d+)", line)
        m_p = re.search(r"power_w[\"']?\s*:\s*([\d.]+)", line)
        m_u = re.search(r"gpu_util_pct[\"']?\s*:\s*(\d+)", line)
        if m_t:
            temps.append(int(m_t.group(1)))
        if m_p:
            powers.append(float(m_p.group(1)))
        if m_u:
            utils.append(int(m_u.group(1)))
    out = {}
    if temps:
        out["temp_c_min"] = min(temps)
        out["temp_c_max"] = max(temps)
        out["temp_c_avg"] = round(mean(temps), 1)
    if powers:
        out["avg_power_w"] = round(mean(powers), 2)
        out["power_w_min"] = round(min(powers), 2)
        out["power_w_max"] = round(max(powers), 2)
    if utils:
        out["gpu_util_pct_avg"] = round(mean(utils), 1)
    return out


def kv_cache_html(kv_data: dict | None) -> str:
    if not kv_data:
        return '<p class="sub">KV metrics pending — run scripts/extract_kv_metrics.py</p>'
    h = kv_data.get("headline") or {}
    b = kv_data.get("baseline_l1_fp8") or {}
    tp = kv_data.get("throughput_c8") or {}
    delta = kv_data.get("delta_tokens_vs_l1_fp8_pct")
    bench_use = kv_data.get("bench_kv_usage_pct_max")

    def fmt_tokens(n):
        return f"{n:,}" if isinstance(n, int) else "—"

    avail = h.get("kv_available_gib") or []
    avail_s = " / ".join(f"{x:.2f}" for x in avail) if avail else "—"

    stats = f"""
<div class="stat-grid">
<div class="stat"><span class="sub">KV dtype</span><b>{h.get('kv_cache_dtype', '—')}</b></div>
<div class="stat"><span class="sub">GPU KV tokens</span><b>{fmt_tokens(h.get('gpu_kv_cache_tokens'))}</b></div>
<div class="stat"><span class="sub">KV memory (GiB)</span><b style="font-size:.85rem">{avail_s}</b></div>
<div class="stat"><span class="sub">max_model_len</span><b>{h.get('max_model_len', '—')}</b></div>
<div class="stat"><span class="sub">block_size</span><b>{h.get('block_size', '—')}</b></div>
<div class="stat"><span class="sub">Max conc @ len</span><b>{h.get('max_concurrency_at_max_model_len') or '—'}×</b></div>
</div>"""

    h_tok = h.get("gpu_kv_cache_tokens")
    b_tok = b.get("gpu_kv_cache_tokens")
    rows = ""
    if b_tok:
        rows += (
            f"<tr><td>L1 fp8</td><td>fp8</td><td>{fmt_tokens(b_tok)}</td>"
            f"<td>{tp.get('l1_fp8') and round(tp['l1_fp8'], 2) or '—'}</td></tr>\n"
        )
    if h_tok:
        rows += (
            f"<tr><td>nvfp4-kv</td><td>{h.get('kv_cache_dtype', 'nvfp4')}</td>"
            f"<td>{fmt_tokens(h_tok)}</td><td>{tp.get('nvfp4_kv') and round(tp['nvfp4_kv'], 2) or '—'}</td></tr>\n"
        )
    table = f"""<div class="table-wrap"><table class="data"><thead><tr>
<th>Profile</th><th>KV dtype</th><th>GPU KV tokens</th><th>c8 out tok/s</th>
</tr></thead><tbody>{rows or '<tr><td colspan="4">—</td></tr>'}</tbody></table></div>"""

    extra = ""
    if delta is not None:
        extra += f'<p class="sub">Δ tokens vs L1 fp8: <b>{delta:+.2f}%</b></p>'
    if bench_use is not None:
        extra += f'<p class="sub">Peak GPU KV usage @ c8 bench: <b>{bench_use}%</b></p>'
    return stats + table + extra


def throughput_section(conc: list, conc_path_name: str, profile: str, kwh_price: float, avg_power: float) -> str:
    if not conc:
        return '<p class="sub">Pending — run scripts/bench_concurrency.sh</p>'
    peak = max((s.get("output_tps") or 0) for s in conc) or 1
    rows = ""
    bars = ""
    for s in conc:
        c = s.get("concurrency")
        otps = s.get("output_tps") or 0
        wall = s.get("wall_s") or 1
        out_tok = s.get("output_tokens") or 0
        kwh = (avg_power * wall) / 3600 / 1000
        cost = kwh * kwh_price
        per_m = (cost / out_tok * 1e6) if out_tok else None
        otps_s = f"{otps:.2f}" if otps is not None else "—"
        per_m_s = f"{per_m:.4f}" if per_m is not None else "—"
        pct = min(100, int(100 * otps / peak)) if peak else 0
        highlight = " class=\"peak\"" if otps == peak else ""
        rows += (
            f"<tr{highlight}><td>c{c}</td><td class=\"num\">{otps_s}</td>"
            f"<td class=\"num\">{avg_power:.1f} W</td><td class=\"num\">{per_m_s}</td></tr>\n"
        )
        bars += (
            f'<div class="bar-row"><span class="bar-label">c{c}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>'
            f'<span class="bar-val">{otps_s}</span></div>\n'
        )
    return f"""<p class="sub">Profile: <code>{profile}</code> · <code>{conc_path_name}</code></p>
<section class="panel">
<div class="chart">{bars}</div>
<div class="table-wrap"><table class="data"><thead><tr>
<th>Concurrency</th><th>Output tok/s</th><th>Power</th><th>$/M out tok</th>
</tr></thead><tbody>{rows}</tbody></table></div>
</section>
<p class="sub">Electricity @ ${kwh_price}/kWh · telemetry power during loaded bench.</p>"""


def main():
    meta = load_json(ROOT / "benchmarks" / "run_meta.json") or {}
    conc_name = meta.get("concurrency_summary_file", "chat-concurrency-summary.json")
    conc_path = ROOT / "benchmarks" / "concurrency" / conc_name
    if not conc_path.is_file():
        conc_path = ROOT / "benchmarks" / "concurrency" / "chat-concurrency-summary-nvfp4-kv.json"
    conc = load_json(conc_path) or []

    kv_path = ROOT / "benchmarks" / "kv_cache_metrics.json"
    kv_data = load_json(kv_path)

    tel_path = ROOT / meta.get("telemetry_file", "evidence/telemetry/gpu-sample.jsonl")
    tel = parse_telemetry_jsonl(tel_path)
    for k, v in tel.items():
        meta.setdefault(k, v)

    kwh_price = float(meta.get("electricity_usd_per_kwh", 0.12))
    avg_power = float(meta.get("avg_power_w", 35))
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    headline = meta.get("headline") or {}
    kv = headline.get("kv_cache_dtype") or meta.get("headline_kv", "nvfp4")
    tp = headline.get("tensor_parallel_size", 2)
    topology = meta.get("topology", f"dual GB10 TP={tp} Ray")
    subtitle = (
        f"{topology} · NVFP4 weights · KV {kv} · vLLM · {ts}"
    )

    throughput_html = throughput_section(
        conc,
        conc_path.name,
        meta.get("headline_profile", "nvfp4-kv"),
        kwh_price,
        avg_power,
    )
    temp_min = meta.get("temp_c_min", "—")
    temp_max = meta.get("temp_c_max", "—")
    temp_avg = meta.get("temp_c_avg", "—")
    util_avg = meta.get("gpu_util_pct_avg", "—")
    image = meta.get("image", "—")

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Laguna M.1 NVFP4 — SM121 Report</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:"Segoe UI",system-ui,-apple-system,sans-serif;background:#0a0e14;color:#e6edf3;line-height:1.55;font-size:15px}}
.wrap{{max-width:920px;margin:0 auto;padding:20px 16px 48px}}
.hero{{border:1px solid #30363d;border-left:4px solid #58a6ff;background:#0d1117;border-radius:12px;padding:20px 22px;margin-bottom:28px}}
h1{{font-size:clamp(1.35rem,4vw,2rem);font-weight:650;letter-spacing:-.02em;color:#f0f6fc}}
h2{{color:#79c0ff;font-size:1rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;margin:28px 0 12px}}
.sub{{color:#8b949e;margin:.35rem 0 .75rem;font-size:.875rem}}
code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.82em;background:#21262d;padding:2px 6px;border-radius:4px}}
.panel{{background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:16px 18px;margin-bottom:8px}}
.card p{{margin:.5rem 0}}
.badge{{display:inline-block;background:#1f3d2a;color:#3fb950;border:1px solid #238636;padding:4px 10px;border-radius:999px;font-size:.75rem;font-weight:600;margin:4px 6px 0 0}}
.table-wrap{{overflow-x:auto;margin-top:12px;-webkit-overflow-scrolling:touch}}
table.data{{width:100%;border-collapse:collapse;min-width:420px;font-size:.9rem}}
table.data th{{color:#79c0ff;font-weight:600;text-align:left;padding:10px 12px;border-bottom:2px solid #30363d;background:#161b22}}
table.data td{{padding:10px 12px;border-bottom:1px solid #21262d}}
table.data tr.peak td{{background:#132033;color:#79c0ff}}
.num{{font-variant-numeric:tabular-nums;font-family:ui-monospace,Menlo,monospace}}
.stat-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}
.stat{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px}}
.stat b{{color:#58a6ff;display:block;font-size:1.15rem;margin-top:4px;font-variant-numeric:tabular-nums}}
.mono-sm{{font-family:ui-monospace,Menlo,monospace;font-size:.72rem;word-break:break-all}}
.mono-block{{font-size:.75rem;overflow-x:auto;padding:12px 0;color:#adbac7}}
.chart{{margin-bottom:16px}}
.bar-row{{display:grid;grid-template-columns:36px 1fr 52px;align-items:center;gap:10px;margin:6px 0}}
.bar-label{{color:#8b949e;font-size:.8rem;font-family:ui-monospace,monospace}}
.bar-track{{height:10px;background:#21262d;border-radius:5px;overflow:hidden}}
.bar-fill{{height:100%;background:#388bfd;border-radius:5px;min-width:2px}}
.bar-val{{text-align:right;font-size:.8rem;color:#c9d1d9;font-family:ui-monospace,monospace}}
details summary{{cursor:pointer;color:#8b949e;font-size:.9rem;padding:4px 0}}
details[open] summary{{margin-bottom:8px;color:#c9d1d9}}
.foot{{margin-top:32px;padding-top:16px;border-top:1px solid #21262d;color:#6e7681;font-size:.8rem;text-align:center}}
@media(max-width:520px){{.bar-row{{grid-template-columns:28px 1fr 44px}}table.data{{min-width:360px}}}}
</style></head><body>
<div class="wrap">
<header class="hero">
<h1>Laguna M.1 NVFP4</h1>
<p class="sub">{subtitle}</p>
<p><span class="badge">poolside/Laguna-M.1-NVFP4</span><span class="badge">FLASHINFER_CUTLASS</span></p>
</header>
<h2>Throughput</h2>
{throughput_html}
<h2>Thermals &amp; power</h2>
<section class="panel">
<div class="stat-grid">
<div class="stat"><span class="sub">Temp min / max / avg</span><b>{temp_min} / {temp_max} / {temp_avg} °C</b></div>
<div class="stat"><span class="sub">Power avg</span><b>{avg_power} W</b></div>
<div class="stat"><span class="sub">GPU util</span><b>{util_avg}%</b></div>
<div class="stat"><span class="sub">Container</span><b class="mono-sm">{meta.get("container_name", "laguna-m1-vllm")}</b></div>
</div>
<p class="sub">Telemetry: <code>{tel_path.relative_to(ROOT) if tel_path.is_relative_to(ROOT) else tel_path}</code></p>
</section>
<h2>KV cache</h2>
<section class="panel">{kv_cache_html(kv_data)}</section>
<h2>Runtime</h2>
<section class="panel card"><p class="mono-sm">{image}</p><p class="sub">{meta.get("image_note", "")}</p></section>
<details class="panel"><summary>Environment JSON</summary><pre class="mono-block">{json.dumps(meta, indent=2)}</pre></details>
<footer class="foot">r0b0tlab/laguna-m1-nvfp4-sm121-vllm · SM121 GB10 · generated {ts}</footer>
</div></body></html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()