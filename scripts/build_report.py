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


def bfcl_table(scores_dir: Path) -> tuple[str, list]:
    rows = []
    summary = []
    if scores_dir.is_dir():
        for p in sorted(scores_dir.glob("**/*.json")):
            try:
                data = json.loads(p.read_text())
                summary.append({"file": p.name, "data": data})
                if isinstance(data, dict):
                    acc = data.get("accuracy") or data.get("overall_accuracy")
                    cat = data.get("test_category") or p.stem
                    if acc is not None:
                        rows.append((cat, acc))
            except Exception:
                pass
    if not rows and summary:
        for item in summary:
            d = item.get("data")
            if isinstance(d, dict):
                for k, v in d.items():
                    if isinstance(v, (int, float)) and "acc" in k.lower():
                        rows.append((k, v))
    html_rows = ""
    for cat, acc in rows[:30]:
        pct = f"{acc * 100:.1f}%" if isinstance(acc, float) and acc <= 1 else str(acc)
        html_rows += f"<tr><td>{cat}</td><td>{pct}</td></tr>\n"
    return html_rows, summary


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
            f"<td>{tp.get('l1_fp8') or '—'}</td></tr>\n"
        )
    if h_tok:
        rows += (
            f"<tr><td>nvfp4-kv</td><td>{h.get('kv_cache_dtype', 'nvfp4')}</td>"
            f"<td>{fmt_tokens(h_tok)}</td><td>{tp.get('nvfp4_kv') or '—'}</td></tr>\n"
        )
    table = f"""<div class="table-wrap"><table><thead><tr>
<th>Profile</th><th>KV dtype</th><th>GPU KV tokens</th><th>c8 out tok/s</th>
</tr></thead><tbody>{rows or '<tr><td colspan="4">—</td></tr>'}</tbody></table></div>"""

    extra = ""
    if delta is not None:
        extra += f'<p class="sub">Δ tokens vs L1 fp8: <b>{delta:+.2f}%</b></p>'
    if bench_use is not None:
        extra += f'<p class="sub">Peak GPU KV usage @ c8 bench: <b>{bench_use}%</b></p>'
    return stats + table + extra


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
        f"{topology} · NVFP4 weights · KV {kv} · vLLM · BFCL v1 · {ts}"
    )

    rows = ""
    for s in conc:
        c = s.get("concurrency")
        otps = s.get("output_tps")
        wall = s.get("wall_s") or 1
        out_tok = s.get("output_tokens") or 0
        power = avg_power
        kwh = (power * wall) / 3600 / 1000
        cost = kwh * kwh_price
        per_m = (cost / out_tok * 1e6) if out_tok else None
        otps_s = f"{otps:.2f}" if otps is not None else "—"
        per_m_s = f"{per_m:.4f}" if per_m is not None else "—"
        rows += (
            f"<tr><td>c{c}</td><td>{otps_s}</td>"
            f"<td>{power:.1f} W</td><td>{per_m_s}</td></tr>\n"
        )

    bfcl_rows, bfcl_summary = bfcl_table(ROOT / "benchmarks" / "bfcl" / "score")
    bfcl_pending = '<tr><td colspan="2">Pending — run scripts/run_bfcl_v1.sh</td></tr>'
    bfcl_block = (
        '<div class="table-wrap"><table><thead><tr><th>Category</th><th>Score</th></tr></thead><tbody>\n'
        + (bfcl_rows or bfcl_pending)
        + "</tbody></table></div>"
    )
    if not bfcl_rows and bfcl_summary:
        bfcl_block += (
            f'<div class="card"><pre style="white-space:pre-wrap;font-size:12px">'
            f"{json.dumps(bfcl_summary, indent=2)[:6000]}</pre></div>"
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
*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:ui-monospace,monospace;background:#0d1117;color:#c9d1d9;padding:16px;line-height:1.5;font-size:14px;overflow-x:hidden}}
h1{{color:#58a6ff;font-size:clamp(1.1rem,4vw,1.75rem)}}h2{{color:#79c0ff;font-size:1.1rem;margin:1.5rem 0 .75rem;border-bottom:1px solid #21262d;padding-bottom:.5rem}}
.sub{{color:#8b949e;margin:.5rem 0 1rem;font-size:.85rem}}.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:1rem;margin:.75rem 0;overflow-x:auto}}
.table-wrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;min-width:480px;font-size:13px}}th,td{{padding:8px 10px;border-bottom:1px solid #21262d;text-align:left}}th{{color:#79c0ff}}
.badge{{display:inline-block;background:#238636;color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;margin:2px}}
.stat-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:.5rem 0}}
.stat{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px}}.stat b{{color:#58a6ff;display:block;font-size:1.1rem}}
</style></head><body>
<h1>Laguna M.1 NVFP4 on SM121</h1>
<p class="sub">{subtitle}</p>
<p><span class="badge">poolside/Laguna-M.1-NVFP4</span> <span class="badge">FLASHINFER_CUTLASS MoE</span> <span class="badge">BFCL public harness</span></p>
<h2>Throughput (chat completions)</h2>
<p class="sub">Profile: <code>{meta.get("headline_profile", "nvfp4-kv")}</code> · source: <code>{conc_path.name}</code></p>
<div class="table-wrap"><table><thead><tr><th>Concurrency</th><th>Output tok/s</th><th>Power (avg)</th><th>$/M out tok</th></tr></thead><tbody>
{rows or '<tr><td colspan="4">Pending — run scripts/bench_concurrency.sh</td></tr>'}
</tbody></table></div>
<p class="sub">Electricity @ ${kwh_price}/kWh; power from GPU telemetry during loaded bench.</p>
<h2>Thermals &amp; power (telemetry)</h2>
<div class="stat-grid">
<div class="stat"><span class="sub">Temp min / max / avg</span><b>{temp_min} / {temp_max} / {temp_avg} °C</b></div>
<div class="stat"><span class="sub">Power avg (loaded)</span><b>{avg_power} W</b></div>
<div class="stat"><span class="sub">GPU util avg</span><b>{util_avg}%</b></div>
<div class="stat"><span class="sub">Container</span><b style="font-size:.75rem">{meta.get("container_name", "laguna_tp2")}</b></div>
</div>
<p class="sub">Source: <code>{tel_path.relative_to(ROOT) if tel_path.is_relative_to(ROOT) else tel_path}</code></p>
<h2>KV cache</h2>
{kv_cache_html(kv_data)}
<h2>BFCL (function calling)</h2>
{bfcl_block}
<h2>Runtime image</h2>
<div class="card"><p style="font-size:12px;word-break:break-all">{image}</p>
<p class="sub">{meta.get("image_note", "")}</p></div>
<h2>Environment</h2>
<div class="card"><pre>{json.dumps(meta, indent=2)}</pre></div>
</body></html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()