# Minimal sanity suite (Laguna M.1)

Fast checks after **restart**, **image pull**, or **config change** — before c1–c8, GSM8K@100, or HumanEval micro.

Aligned with the **llm-benchmark-execution** campaign pattern: *health → tiny real-path canary → full suites*, and with this repo’s existing **post-serve** steps (`run_v1_pipeline.sh`, `run_tp2_finish_pipeline.sh`).

## Recommended minimal suite (≈3–8 min)

| Step | Script / check | What it proves | Typical time |
|------|----------------|----------------|--------------|
| **S0** | `curl -sf http://127.0.0.1:30100/v1/models` | API up, model id | &lt;1 s |
| **S1** | `bash scripts/verify_native_kernels.sh` | SM121 native MoE/KV (no MARLIN headline lie) | ~30 s |
| **S2** | `bash scripts/smoke_poolside_tools.sh` | Chat path, thinking model returns text | 1–2 min |
| **S3** | `bash scripts/run_hermes_terminal_micro.sh` | Real Hermes agent + terminal tools (**5/5** gate) | ~1–3 min |

**One-liner (S0–S3):**

```bash
bash scripts/run_sanity_suite.sh
```

Exit **0** only if S1–S3 pass (S0 inside S2).

### Why these four (not the full publish ladder)

| Full pre-publish (keep for releases) | Sanity (keep for day-to-day) |
|--------------------------------------|------------------------------|
| `bench_concurrency.sh` c1–c8 | — (too heavy for “is it alive?”) |
| GSM8K@100 (~1 h) | optional **GSM8K@5** tier (below) |
| HumanEval@10 ×2 (lm-eval + Hermes) | — (code-exec + long; use in publish only) |
| KV extract + HTML | — |

Prior SM121 / MoE pubs used the same **smoke → ladder** split: `smoke_poolside_tools.sh` before concurrency; Hermes **t01_terminal_smoke** is the agent analogue of a **terminal-bench canary** (real harness, tiny N).

## Optional tier B — math micro (≈+5–15 min)

When you need a **numeric** sanity signal without GSM8K@100:

```bash
LIMIT=5 NUM_CONCURRENT=1 bash scripts/run_gsm8k_100.sh
```

- Reuses `run_gsm8k_100.sh` with `LIMIT=5` (not committed as headline unless you copy into `baseline` / report).
- **Do not** overlap with concurrency bench or another lm-eval job on `:30100`.

## Out of scope for sanity

- BFCL (local/gitignored; long)
- Full **51-task** hermesbench
- HumanEval (needs `HF_ALLOW_CODE_EVAL=1` + `--confirm_run_unsafe_code`; keep for publish compare row)

## Artifacts

| Path | Purpose |
|------|---------|
| `evidence/sanity_suite.log` | Combined log from `run_sanity_suite.sh` |
| `benchmarks/hermesbench/terminal_micro_results.json` | S3 output (same as publish micro) |

## When to run

- After `serve_tp2_cluster.sh` / container recreate
- After GHCR image digest change
- Before starting GSM8K@100 or HumanEval background jobs

## Publish ladder (unchanged)

Sanity does **not** replace: concurrency → KV → GSM8K@100 → Hermes + HumanEval micro → `build_report.py` → `finish_publish.sh`. See `docs/BENCHMARKS.md`.