#!/usr/bin/env python3
"""Build publication/html/index.html from benchmark JSON artifacts."""
from __future__ import annotations

import json
import re
import subprocess
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


def hermes_humaneval_html(meta: dict) -> str:
    hb = meta.get("hermesbench") or {}
    h = hb.get("humaneval_micro") or {}
    results_path = ROOT / "benchmarks" / "hermesbench" / "humaneval_micro_results.json"
    summary = load_json(results_path) if results_path.is_file() else None
    if not summary and not h.get("total"):
        return (
            '<p class="sub">Pending — run <code>scripts/run_hermes_humaneval_micro.sh</code> '
            "(see <code>docs/BENCHMARKS.md</code>).</p>"
        )
    passed = summary.get("passed") if summary else h.get("passed", 0)
    total = summary.get("total") if summary else h.get("total", 10)
    rate = summary.get("pass_rate") if summary else h.get("pass_at_1", 0)
    if rate is None and total:
        rate = passed / total
    rate_s = f"{100 * float(rate):.0f}%" if rate is not None else "—"
    rows = ""
    for t in (summary or {}).get("tasks") or []:
        tid = t.get("task_id", "").split("/")[-1]
        st = t.get("status", "—")
        cls = "status-pass" if st == "PASS" else ("status-fail" if st == "FAIL" else "")
        rows += f'<tr><td><code>{tid}</code></td><td class="{cls}">{st}</td></tr>\n'
    table = ""
    if rows:
        table = f"""<div class="table-wrap"><table class="data"><thead><tr>
<th>Task</th><th>Status</th>
</tr></thead><tbody>{rows}</tbody></table></div>"""
    return f"""<div class="stat-grid">
<div class="stat"><span class="sub">pass@1</span><b>{passed}/{total} ({rate_s})</b></div>
<div class="stat"><span class="sub">Category</span><b class="mono-sm">t13_humaneval_micro</b></div>
<div class="stat"><span class="sub">Harness</span><b>hermes-bench</b></div>
<div class="stat"><span class="sub">Mode</span><b>real-agent</b></div>
</div>
{table}
<p class="sub"><code>benchmarks/hermesbench/humaneval_micro_results.json</code> · n=10 micro subset</p>"""


def runtime_html(meta: dict) -> str:
    image = meta.get("image", "—")
    digest = meta.get("image_digest", "sha256:6e2dfa4…ad7712a8")
    lineage = meta.get("image_pull_alias", "")
    launch = meta.get("serve_script", "scripts/serve_tp2_cluster.sh")
    lineage_row = (
        f'<tr><th scope="row">Build lineage</th><td class="mono-sm">{lineage}</td></tr>\n'
        if lineage
        else ""
    )
    pkg_url = "https://github.com/orgs/r0b0tlab/packages/container/package/vllm-laguna-m1-nvfp4-sm121"
    return f"""<div class="table-wrap"><table class="data"><tbody>
<tr><th scope="row">GHCR package</th><td class="mono-sm">{image}</td></tr>
<tr><th scope="row">Pin (digest)</th><td class="mono-sm">{digest}</td></tr>
{lineage_row}<tr><th scope="row">Role</th><td>SM121 / cu130 / arm64 vLLM · Laguna weights + Poolside parsers at serve time (<code>{launch}</code>)</td></tr>
<tr><th scope="row">Container</th><td><code>{meta.get('container_name', 'laguna-m1-vllm')}</code> · TP=2 Ray · nvfp4 KV</td></tr>
</tbody></table></div>
<p class="sub">Published for this repo — separate from <code>vllm-dsv4-flash-gb10</code> (same digest, different GHCR package). <a href="{pkg_url}">Package page</a></p>
<p class="sub"><code>docs/CONTAINER.md</code> · <code>scripts/publish_ghcr_laguna_runtime.sh</code></p>"""


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


def usd_per_million_output_tokens(step: dict, avg_power_w: float, kwh_price: float) -> float | None:
    wall = step.get("wall_s") or 0
    out_tok = step.get("output_tokens") or 0
    if not out_tok or not wall:
        return None
    kwh = (avg_power_w * wall) / 3600 / 1000
    return (kwh * kwh_price / out_tok) * 1e6


def write_energy_cost_json(conc: list, meta: dict, kwh_price: float, avg_power: float) -> None:
    per_m = {}
    for s in conc or []:
        c = s.get("concurrency")
        v = usd_per_million_output_tokens(s, avg_power, kwh_price)
        if c is not None and v is not None:
            per_m[f"c{c}"] = round(v, 6)
    payload = {
        "electricity_usd_per_kwh": kwh_price,
        "avg_power_w": avg_power,
        "power_w_min": meta.get("power_w_min"),
        "power_w_max": meta.get("power_w_max"),
        "temp_c_avg": meta.get("temp_c_avg"),
        "gpu_util_pct_avg": meta.get("gpu_util_pct_avg"),
        "usd_per_million_output_tokens": per_m,
        "headline_profile": meta.get("headline_profile", "nvfp4-kv"),
        "note": "Power from telemetry during concurrency bench; cost = avg_power * wall_s / output_tokens.",
    }
    out = ROOT / "benchmarks" / "energy_cost_metrics.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def energy_cost_html(conc: list, kwh_price: float, avg_power: float, meta: dict) -> str:
    if not conc:
        return ""
    by_c = {s.get("concurrency"): s for s in conc}
    c1_cost = usd_per_million_output_tokens(by_c.get(1) or {}, avg_power, kwh_price)
    c8_cost = usd_per_million_output_tokens(by_c.get(8) or {}, avg_power, kwh_price)
    pmin = meta.get("power_w_min", "—")
    pmax = meta.get("power_w_max", "—")
    c1_s = f"${c1_cost:.4f}" if c1_cost is not None else "—"
    c8_s = f"${c8_cost:.4f}" if c8_cost is not None else "—"
    rows = ""
    for s in sorted(conc, key=lambda x: x.get("concurrency") or 0):
        c = s.get("concurrency")
        v = usd_per_million_output_tokens(s, avg_power, kwh_price)
        if v is None:
            continue
        rows += (
            f'<tr><td>c{c}</td><td class="num">{avg_power:.1f}</td>'
            f'<td class="num">{s.get("wall_s", 0):.1f} s</td>'
            f'<td class="num">{s.get("output_tokens", 0)}</td>'
            f'<td class="num">${v:.4f}</td></tr>\n'
        )
    table = ""
    if rows:
        table = f"""<div class="table-wrap"><table class="data"><thead><tr>
<th>Concurrency</th><th>Power (W)</th><th>Bench wall</th><th>Out tokens</th><th>$/M out tok</th>
</tr></thead><tbody>{rows}</tbody></table></div>"""
    return f"""<h3 class="anchor" id="energy" style="margin-top:22px;font-size:.9rem;font-weight:600">Power &amp; token cost</h3>
<section class="panel">
<div class="stat-grid">
<div class="stat"><span class="sub">Avg power (bench)</span><b>{avg_power} W</b></div>
<div class="stat"><span class="sub">Power min / max</span><b>{pmin} / {pmax} W</b></div>
<div class="stat"><span class="sub">Electricity rate</span><b>${kwh_price}/kWh</b></div>
<div class="stat"><span class="sub">$/M out @ c1</span><b class="mono-sm">{c1_s}</b></div>
<div class="stat"><span class="sub">$/M out @ c8</span><b class="mono-sm">{c8_s}</b></div>
</div>
{table}
<p class="sub">Estimated from telemetry <code>avg_power_w</code> × bench wall time ÷ output tokens. Artifact: <code>benchmarks/energy_cost_metrics.json</code></p>
</section>"""


def git_short_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=ROOT,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            .strip()
        )
    except Exception:
        return ""


def kpi_strip_html(conc: list, meta: dict) -> str:
    c1 = c8 = None
    for s in conc or []:
        if s.get("concurrency") == 1:
            c1 = s.get("output_tps")
        if s.get("concurrency") == 8:
            c8 = s.get("output_tps")
    lm = (meta.get("lm_eval") or {}).get("gsm8k_100") or {}
    em = lm.get("exact_match")
    em_s = f"{100 * em:.0f}%" if em is not None else "—"
    hb = meta.get("hermesbench") or {}
    term = hb.get("terminal_micro") or {}
    t_pass = term.get("passed")
    t_tot = term.get("total") or 5
    term_s = f"{t_pass}/{t_tot}" if t_pass is not None else "—"
    he = hb.get("humaneval_micro") or {}
    he_s = "—"
    if he.get("pass_at_1") is not None:
        he_s = f"{100 * float(he['pass_at_1']):.0f}%"
    c1_s = f"{c1:.2f}" if c1 is not None else "—"
    c8_s = f"{c8:.2f}" if c8 is not None else "—"
    kwh_price = float(meta.get("electricity_usd_per_kwh", 0.12))
    avg_power = float(meta.get("avg_power_w", 35))
    by_c = {s.get("concurrency"): s for s in (conc or [])}
    c1_cost = usd_per_million_output_tokens(by_c.get(1) or {}, avg_power, kwh_price)
    c8_cost = usd_per_million_output_tokens(by_c.get(8) or {}, avg_power, kwh_price)
    pwr_s = f"{avg_power:.0f} W"
    c1m_s = f"${c1_cost:.3f}" if c1_cost is not None else "—"
    c8m_s = f"${c8_cost:.3f}" if c8_cost is not None else "—"
    return f"""<div class="kpi-strip" role="list">
<div class="kpi" role="listitem"><span class="kpi-label">c1 out tok/s</span><span class="kpi-value">{c1_s}</span></div>
<div class="kpi" role="listitem"><span class="kpi-label">c8 out tok/s</span><span class="kpi-value kpi-highlight">{c8_s}</span></div>
<div class="kpi" role="listitem"><span class="kpi-label">Power (avg)</span><span class="kpi-value">{pwr_s}</span></div>
<div class="kpi" role="listitem"><span class="kpi-label">$/M out c1</span><span class="kpi-value">{c1m_s}</span></div>
<div class="kpi" role="listitem"><span class="kpi-label">$/M out c8</span><span class="kpi-value">{c8m_s}</span></div>
<div class="kpi" role="listitem"><span class="kpi-label">GSM8K@100</span><span class="kpi-value">{em_s}</span></div>
<div class="kpi" role="listitem"><span class="kpi-label">Hermes terminal</span><span class="kpi-value">{term_s}</span></div>
<div class="kpi" role="listitem"><span class="kpi-label">HumanEval (Hermes)</span><span class="kpi-value">{he_s}</span></div>
</div>"""


def nav_html() -> str:
    links = [
        ("throughput", "Throughput"),
        ("energy", "Power & cost"),
        ("accuracy", "GSM8K"),
        ("agent", "Agent"),
        ("humaneval", "HumanEval"),
        ("thermals", "Thermals"),
        ("kv", "KV cache"),
        ("runtime", "Runtime"),
        ("repro", "Reproduce"),
    ]
    items = "".join(f'<a href="#{aid}">{label}</a>' for aid, label in links)
    return f'<nav class="toc" aria-label="Report sections">{items}</nav>'


def repro_html(meta: dict) -> str:
    port = meta.get("port", 30100)
    return f"""<section class="panel" id="repro">
<p class="section-lead">Regenerate this page from committed JSON under <code>benchmarks/</code>.</p>
<pre class="mono-block repro-cmd">cd laguna-m1-nvfp4-sm121-vllm
bash scripts/bench_concurrency.sh
python3 scripts/extract_kv_metrics.py
bash scripts/run_gsm8k_100.sh
bash scripts/run_hermes_terminal_micro.sh
bash scripts/run_hermes_humaneval_micro.sh
python3 scripts/build_report.py</pre>
<p class="sub">Fast post-restart check: <code>bash scripts/run_sanity_suite.sh</code> · API <code>:{port}</code> · see <code>docs/BENCHMARKS.md</code></p>
</section>"""


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
    energy_html = energy_cost_html(conc, kwh_price, avg_power, meta)
    write_energy_cost_json(conc, meta, kwh_price, avg_power)
    temp_min = meta.get("temp_c_min", "—")
    temp_max = meta.get("temp_c_max", "—")
    temp_avg = meta.get("temp_c_avg", "—")
    util_avg = meta.get("gpu_util_pct_avg", "—")
    image = meta.get("image", "—")

    runtime_block = runtime_html(meta)
    gsm8k_block = gsm8k_html(meta)
    hermes_terminal_block = hermes_terminal_html(meta)
    humaneval_block = hermes_humaneval_html(meta)
    kpi_block = kpi_strip_html(conc, meta)
    nav_block = nav_html()
    repro_block = repro_html(meta)
    git_sha = git_short_sha()
    tel_rel = tel_path.relative_to(ROOT) if tel_path.is_relative_to(ROOT) else tel_path
    page_desc = f"NVFP4 serve report: {topology}, concurrency c1–c8, GSM8K@100, Hermes agent micros."

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{page_desc}">
<meta name="theme-color" content="#0f766e">
<meta name="generator" content="scripts/build_report.py">
<title>Laguna M.1 NVFP4 — SM121 Benchmark Report</title>
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
.eyebrow{{font-size:.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.1em;color:var(--accent-text);margin-bottom:8px}}
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
.skip-link{{position:absolute;left:-9999px;top:auto}}
.skip-link:focus{{left:16px;top:16px;z-index:99;background:var(--surface);padding:10px 14px;border-radius:var(--radius-sm);border:1px solid var(--border);box-shadow:var(--shadow)}}
.toc{{display:flex;flex-wrap:wrap;gap:8px 10px;margin:0 0 28px;padding:14px 16px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow)}}
.toc a{{color:var(--accent-text);text-decoration:none;font-size:.8125rem;font-weight:600;padding:6px 10px;border-radius:999px;background:var(--surface-muted);border:1px solid var(--border)}}
.toc a:hover{{background:var(--accent-soft);border-color:#99f6e4}}
.kpi-strip{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-top:20px;padding-top:20px;border-top:1px solid var(--border)}}
.kpi{{background:var(--surface-muted);border:1px solid var(--border);border-radius:var(--radius-sm);padding:12px 14px}}
.kpi-label{{display:block;font-size:.65rem;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted);margin-bottom:4px}}
.kpi-value{{font-size:1.35rem;font-weight:700;font-variant-numeric:tabular-nums;color:var(--text);font-family:ui-monospace,Menlo,monospace}}
.kpi-highlight{{color:var(--accent-text)}}
.section-lead{{color:var(--text-secondary);font-size:.9375rem;margin-bottom:12px}}
.compare-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:16px}}
.compare-card{{background:var(--surface-muted);border:1px solid var(--border);border-radius:var(--radius-sm);padding:18px 20px;text-align:center}}
.compare-card-accent{{border-color:#99f6e4;background:var(--accent-soft)}}
.compare-label{{display:block;font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted);margin-bottom:8px}}
.score-lg{{display:block;font-size:2rem;font-weight:700;font-variant-numeric:tabular-nums;color:var(--accent-text);line-height:1.1;margin-bottom:6px}}
.callout{{font-size:.875rem;padding:12px 14px;border-radius:var(--radius-sm);margin:12px 0 0}}
.callout-ok{{background:#ecfdf5;border:1px solid #a7f3d0;color:#047857}}
.callout-warn{{background:#fffbeb;border:1px solid #fde68a;color:#b45309}}
.repro-cmd{{background:var(--surface-muted);border:1px solid var(--border);border-radius:var(--radius-sm);padding:16px 18px;margin:0}}
.anchor{{scroll-margin-top:16px}}
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
  .toc{{gap:6px}}
  .kpi-value{{font-size:1.15rem}}
}}
@media print{{
  .toc{{display:none}}
  .panel,.hero{{box-shadow:none}}
  body{{background:#fff}}
}}
</style></head><body>
<a class="skip-link" href="#main">Skip to content</a>
<div class="wrap">
<header class="hero">
<p class="eyebrow">SM121 · NVFP4 MoE · Publication template</p>
<h1>Laguna M.1 NVFP4</h1>
<p class="sub">{subtitle}</p>
<p><span class="badge">poolside/Laguna-M.1-NVFP4</span><span class="badge">FLASHINFER_CUTLASS</span><span class="badge">nvfp4 KV</span></p>
{kpi_block}
</header>
{nav_block}
<main id="main">
<h2 class="anchor" id="throughput">Throughput</h2>
{throughput_html}
{energy_html}
<h2 class="anchor" id="accuracy">Accuracy (GSM8K)</h2>
<section class="panel">{gsm8k_block}</section>
<h2 class="anchor" id="agent">Agent tools (Hermes terminal)</h2>
<section class="panel">{hermes_terminal_block}</section>
<h2 class="anchor" id="humaneval">HumanEval micro (Hermes agent)</h2>
<section class="panel">{humaneval_block}</section>
<h2 class="anchor" id="thermals">Thermals &amp; power</h2>
<section class="panel">
<div class="stat-grid">
<div class="stat"><span class="sub">Temp min / max / avg</span><b>{temp_min} / {temp_max} / {temp_avg} °C</b></div>
<div class="stat"><span class="sub">Power avg (telemetry)</span><b>{avg_power} W</b></div>
<div class="stat"><span class="sub">Power min / max</span><b>{meta.get("power_w_min", "—")} / {meta.get("power_w_max", "—")} W</b></div>
<div class="stat"><span class="sub">GPU util</span><b>{util_avg}%</b></div>
<div class="stat"><span class="sub">Electricity</span><b>${kwh_price}/kWh</b></div>
<div class="stat"><span class="sub">Container</span><b class="mono-sm">{meta.get("container_name", "laguna-m1-vllm")}</b></div>
</div>
<p class="sub">Telemetry: <code>{tel_rel}</code></p>
</section>
<h2 class="anchor" id="kv">KV cache</h2>
<section class="panel">{kv_cache_html(kv_data)}</section>
<h2 class="anchor" id="runtime">Runtime (SM121)</h2>
<section class="panel">{runtime_block}</section>
<h2 class="anchor" id="repro">Reproduce</h2>
{repro_block}
<details class="panel"><summary>Environment JSON</summary><pre class="mono-block">{json.dumps(meta, indent=2)}</pre></details>
</main>
<footer class="foot">r0b0tlab/laguna-m1-nvfp4-sm121-vllm · SM121 GB10 · git {git_sha or "—"} · generated {ts}</footer>
</div></body></html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()