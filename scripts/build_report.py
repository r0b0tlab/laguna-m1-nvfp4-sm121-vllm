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


def gsm8k_html(meta: dict) -> str:
    lm = meta.get("lm_eval") or {}
    g = lm.get("gsm8k_100") or {}
    results_path = ROOT / "benchmarks" / "lm_eval" / "gsm8k_100_results.json"
    summary = load_json(results_path) if results_path.is_file() else None
    if not summary and not g.get("exact_match"):
        return (
            '<p class="sub">Pending — run <code>scripts/run_gsm8k_100.sh</code> '
            "before publish (see <code>docs/BENCHMARKS.md</code>).</p>"
        )
    em = summary.get("exact_match") if summary else g.get("exact_match")
    stderr = summary.get("exact_match_stderr") if summary else g.get("exact_match_stderr")
    limit = summary.get("limit") if summary else g.get("limit", 100)
    task = summary.get("task_id") if summary else g.get("task_id", "gsm8k")
    few = summary.get("num_fewshot") if summary else 5
    em_s = f"{100 * em:.1f}%" if em is not None else "—"
    stderr_s = f"± {100 * stderr:.1f}%" if stderr is not None else ""
    return f"""<div class="stat-grid">
<div class="stat"><span class="sub">GSM8K exact_match</span><b>{em_s}</b></div>
<div class="stat"><span class="sub">Subset</span><b>n={limit}</b></div>
<div class="stat"><span class="sub">Few-shot</span><b>{few}</b></div>
<div class="stat"><span class="sub">Task</span><b class="mono-sm">{task}</b></div>
</div>
<p class="sub">lm-evaluation-harness · OpenAI GSM8K test subset {stderr_s} · <code>benchmarks/lm_eval/gsm8k_100_results.json</code></p>"""


def hermes_terminal_html(meta: dict) -> str:
    hb = meta.get("hermesbench") or {}
    h = hb.get("terminal_micro") or {}
    results_path = ROOT / "benchmarks" / "hermesbench" / "terminal_micro_results.json"
    summary = load_json(results_path) if results_path.is_file() else None
    if not summary and not h.get("total"):
        return (
            '<p class="sub">Pending — run <code>scripts/run_hermes_terminal_micro.sh</code> '
            "(see <code>docs/BENCHMARKS.md</code>).</p>"
        )
    passed = summary.get("passed") if summary else h.get("passed", 0)
    total = summary.get("total") if summary else h.get("total", 5)
    rate = summary.get("pass_rate") if summary else h.get("pass_rate", 0)
    rate_s = f"{100 * rate:.0f}%" if rate is not None else "—"
    rows = ""
    for t in (summary or {}).get("tasks") or []:
        tid = t.get("task_id", "").split("/")[-1]
        st = t.get("status", "—")
        cls = "status-pass" if st == "PASS" else ("status-fail" if st == "FAIL" else "")
        rows += f"<tr><td><code>{tid}</code></td><td class=\"{cls}\">{st}</td></tr>\n"
    table = ""
    if rows:
        table = f"""<div class="table-wrap"><table class="data"><thead><tr>
<th>Task</th><th>Status</th>
</tr></thead><tbody>{rows}</tbody></table></div>"""
    return f"""<div class="stat-grid">
<div class="stat"><span class="sub">Pass rate</span><b>{passed}/{total} ({rate_s})</b></div>
<div class="stat"><span class="sub">Category</span><b class="mono-sm">t01_terminal_smoke</b></div>
<div class="stat"><span class="sub">Harness</span><b>hermes-bench</b></div>
<div class="stat"><span class="sub">Mode</span><b>real-agent</b></div>
</div>
{table}
<p class="sub"><code>benchmarks/hermesbench/terminal_micro_results.json</code></p>"""


def runtime_html(meta: dict) -> str:
    image = meta.get("image", "—")
    digest = meta.get("image_digest", "sha256:6e2dfa4…ad7712a8")
    alias = meta.get("image_pull_alias", "")
    launch = meta.get("serve_script", "scripts/serve_tp2_cluster.sh")
    alias_row = (
        f'<tr><th scope="row">Pull alias</th><td class="mono-sm">{alias}</td></tr>\n'
        if alias
        else ""
    )
    return f"""<div class="table-wrap"><table class="data"><tbody>
<tr><th scope="row">Registry image</th><td class="mono-sm">{image}</td></tr>
{alias_row}<tr><th scope="row">Pin (digest)</th><td class="mono-sm">{digest}</td></tr>
<tr><th scope="row">Role</th><td>SM121 / cu130 / arm64 vLLM · LagunaForCausalLM · Poolside parsers · NVFP4 MoE (FlashInfer CUTLASS)</td></tr>
<tr><th scope="row">Headline launch</th><td><code>{launch}</code> · <code>{meta.get('container_name', 'laguna-m1-vllm')}</code></td></tr>
</tbody></table></div>
<p class="sub">Pull alias is the same SM121 build until the Laguna repository tag is on GHCR.</p>
<p class="sub"><code>docs/CONTAINER.md</code></p>"""


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
        highlight = ' class="peak"' if otps == peak else ""
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

    runtime_block = runtime_html(meta)
    gsm8k_block = gsm8k_html(meta)
    hermes_terminal_block = hermes_terminal_html(meta)

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Laguna M.1 NVFP4 — SM121 Report</title>
<style>
:root{{
  --bg:#f4f5f7;--surface:#fff;--surface-muted:#f9fafb;--text:#111827;--text-secondary:#4b5563;
  --text-muted:#6b7280;--border:#e5e7eb;--border-strong:#d1d5db;--accent:#0d9488;--accent-soft:#ccfbf1;
  --accent-text:#0f766e;--peak:#eff6ff;--peak-text:#1d4ed8;--code-bg:#f3f4f6;--shadow:0 1px 2px rgba(17,24,39,.06),0 4px 16px rgba(17,24,39,.04);
  --radius:12px;--radius-sm:8px;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{
  font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  background:var(--bg);color:var(--text);line-height:1.6;font-size:15px;
  -webkit-font-smoothing:antialiased;
}}
.wrap{{max-width:880px;margin:0 auto;padding:32px 20px 56px}}
.hero{{
  background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:28px 28px 24px;margin-bottom:36px;box-shadow:var(--shadow);
}}
h1{{font-size:clamp(1.5rem,4vw,2.125rem);font-weight:700;letter-spacing:-.03em;color:var(--text);line-height:1.2}}
h2{{
  color:var(--text);font-size:.8125rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;
  margin:36px 0 14px;padding-bottom:8px;border-bottom:1px solid var(--border);
}}
.sub{{color:var(--text-muted);margin:.4rem 0 .65rem;font-size:.875rem;line-height:1.5}}
code{{
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.8em;
  background:var(--code-bg);color:#374151;padding:2px 7px;border-radius:6px;border:1px solid var(--border);
}}
.panel{{
  background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:20px 22px;margin-bottom:10px;box-shadow:var(--shadow);
}}
.badge{{
  display:inline-block;background:var(--accent-soft);color:var(--accent-text);
  border:1px solid #99f6e4;padding:5px 12px;border-radius:999px;font-size:.7rem;font-weight:600;
  margin:6px 8px 0 0;letter-spacing:.02em;
}}
.table-wrap{{overflow-x:auto;margin-top:14px;-webkit-overflow-scrolling:touch;border-radius:var(--radius-sm);border:1px solid var(--border)}}
table.data{{width:100%;border-collapse:collapse;min-width:420px;font-size:.875rem;background:var(--surface)}}
table.data th{{
  color:var(--text-secondary);font-weight:600;text-align:left;padding:11px 14px;
  border-bottom:1px solid var(--border-strong);background:var(--surface-muted);font-size:.75rem;text-transform:uppercase;letter-spacing:.04em;
}}
table.data td{{padding:11px 14px;border-bottom:1px solid var(--border);color:var(--text)}}
table.data tbody tr:last-child td{{border-bottom:none}}
table.data tr.peak td{{background:var(--peak);color:var(--peak-text);font-weight:600}}
.num{{font-variant-numeric:tabular-nums;font-family:ui-monospace,Menlo,monospace}}
.status-pass{{color:#047857;font-weight:600;font-variant-numeric:tabular-nums}}
.status-fail{{color:#b91c1c;font-weight:600}}
.stat-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:12px}}
.stat{{
  background:var(--surface-muted);border:1px solid var(--border);border-radius:var(--radius-sm);padding:14px 16px;
}}
.stat .sub{{margin:0 0 6px;font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted)}}
.stat b{{color:var(--accent-text);display:block;font-size:1.125rem;margin-top:2px;font-variant-numeric:tabular-nums;font-weight:700}}
.mono-sm{{font-family:ui-monospace,Menlo,monospace;font-size:.72rem;word-break:break-all;color:var(--text-secondary)}}
.mono-block{{
  font-size:.75rem;overflow-x:auto;padding:14px 0;color:var(--text-secondary);
  font-family:ui-monospace,Menlo,monospace;line-height:1.45;
}}
.chart{{margin-bottom:18px;padding:4px 0}}
.bar-row{{display:grid;grid-template-columns:40px 1fr 56px;align-items:center;gap:12px;margin:8px 0}}
.bar-label{{color:var(--text-muted);font-size:.8rem;font-family:ui-monospace,monospace;font-weight:500}}
.bar-track{{height:8px;background:var(--code-bg);border-radius:99px;overflow:hidden;border:1px solid var(--border)}}
.bar-fill{{height:100%;background:var(--accent);border-radius:99px;min-width:3px}}
.bar-val{{text-align:right;font-size:.8rem;color:var(--text-secondary);font-family:ui-monospace,monospace;font-weight:600}}
details.panel summary{{
  cursor:pointer;color:var(--text-secondary);font-size:.875rem;font-weight:500;padding:2px 0;list-style:none;
}}
details.panel summary::-webkit-details-marker{{display:none}}
details.panel summary::before{{content:"▸ ";color:var(--accent)}}
details[open].panel summary::before{{content:"▾ "}}
details[open].panel summary{{margin-bottom:10px;color:var(--text)}}
.foot{{
  margin-top:40px;padding-top:20px;border-top:1px solid var(--border);
  color:var(--text-muted);font-size:.8rem;text-align:center;
}}
table.data th[scope="row"]{{
  width:30%;color:var(--text-muted);font-weight:500;background:var(--surface-muted);
  border-bottom:1px solid var(--border);font-size:.8125rem;text-transform:none;letter-spacing:0;
}}
@media(max-width:520px){{
  .wrap{{padding:20px 14px 40px}}
  .hero{{padding:20px 18px}}
  .bar-row{{grid-template-columns:32px 1fr 48px}}
  table.data{{min-width:340px}}
}}
</style></head><body>
<div class="wrap">
<header class="hero">
<h1>Laguna M.1 NVFP4</h1>
<p class="sub">{subtitle}</p>
<p><span class="badge">poolside/Laguna-M.1-NVFP4</span><span class="badge">FLASHINFER_CUTLASS</span></p>
</header>
<h2>Throughput</h2>
{throughput_html}
<h2>Accuracy (GSM8K)</h2>
<section class="panel">{gsm8k_block}</section>
<h2>Agent tools (Hermes terminal)</h2>
<section class="panel">{hermes_terminal_block}</section>
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
<h2>Runtime (SM121)</h2>
<section class="panel">{runtime_block}</section>
<details class="panel"><summary>Environment JSON</summary><pre class="mono-block">{json.dumps(meta, indent=2)}</pre></details>
<footer class="foot">r0b0tlab/laguna-m1-nvfp4-sm121-vllm · SM121 GB10 · generated {ts}</footer>
</div></body></html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()