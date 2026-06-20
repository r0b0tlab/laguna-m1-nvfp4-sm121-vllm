# New session handoff — Laguna M.1 NVFP4 SM121

**Updated:** 2026-06-20 · **Git:** `94d3c91` on `main`

Read this first, then `AGENTS.md` and `benchmarks/run_meta.json`.

---

## What shipped (v1 publish-ready)

| Area | State |
|------|--------|
| **Serve** | `laguna-m1-vllm`, `:30100`, TP=2 Ray, nvfp4 KV, `scripts/serve_tp2_cluster.sh` |
| **Image** | `ghcr.io/r0b0tlab/vllm-laguna-m1-nvfp4-sm121:cu130-sm121-arm64-dda4668b` |
| **Digest** | `sha256:6e2dfa4c48ac73965890a864dc1510017f42981e743b3f2834b4b189ad7712a8` |
| **Lineage** | Same layers as `vllm-dsv4-flash-gb10` tag — DSV4 package **not** overwritten |
| **Throughput** | c1 **11.41** → c8 **48.98** out tok/s (`chat-concurrency-summary-nvfp4-kv.json`) |
| **KV** | **507,904** tokens headline (`kv_cache_metrics.json`) |
| **GSM8K@100** | **97%** flexible exact_match |
| **Hermes terminal** | **5/5** (`t01_terminal_smoke`) |
| **Hermes HumanEval** | **10/10** (`t13_humaneval_micro`) — **only** public coding story |
| **Power / cost** | Avg **33 W**, **$0.12/kWh** → c1 **$0.096/M** out, c8 **$0.022/M** (`energy_cost_metrics.json` + HTML `#energy`) |
| **HTML** | Light theme template, hero KPIs, nav, `publication/html/README.md` |
| **Alignment** | `python3 scripts/verify_publish_alignment.py` |

**Report (raw.githack):**  
`https://raw.githack.com/r0b0tlab/laguna-m1-nvfp4-sm121-vllm/75fff28/publication/html/index.html`

**Repo:** https://github.com/r0b0tlab/laguna-m1-nvfp4-sm121-vllm  
**Description:** no BFCL in GitHub description (slug never had BFCL).

---

## Quick health (run on Spark)

```bash
docker ps --filter name=laguna-m1-vllm
curl -s http://127.0.0.1:30100/health
python3 scripts/verify_publish_alignment.py
```

---

## Publish path

```bash
# Optional: SKIP_GSM8K=1 SKIP_HERMES_*=1 if artifacts already fresh
bash scripts/finish_publish.sh
```

Sanity suite (`scripts/run_sanity_suite.sh`) is **manual** — not default in `finish_publish.sh`. See `docs/SANITY_SUITE.md`.

---

## Open / optional next work

1. **GHCR public** — package may still be private; UI: org package → Public + link repo (`docs/GHCR_PACKAGE.md`).
2. **Minimal lm-eval sanity** — research small suite; standalone HumanEval needs unsafe flag + Poolside reasoning handling (0/10 standalone — not published).
3. **MATH-500**, **CUDA FULL vs PIECEWISE A/B**, **`t08_execute_code`** micro.
4. **Wiki** — `~/wiki/sessions/summaries/20260620_laguna-m1-v1-publish-prep.md`.

---

## Out of scope on public `main`

- BFCL harness (`benchmarks/bfcl/` gitignored)
- Standalone lm-eval HumanEval compare row in HTML
- Demo videos / HyperFrames

---

## Inference quirk

Laguna often returns empty `content` with **`reasoning`** field — Hermes micros handle this; raw lm-eval HumanEval may need fence/reasoning post-process if revived.

---

## Key paths

| Path | Role |
|------|------|
| `scripts/build_report.py` | HTML + `energy_cost_metrics.json` |
| `scripts/finish_publish.sh` | Stage, verify, commit, push |
| `docs/CONTAINER.md` | Pull/run |
| `docs/BENCHMARKS.md` | Full bench order |
| `~/hermes-bench-tool-call` | Hermes bench tasks |
| `~/wiki/START_HERE.md` | Device wiki entry |