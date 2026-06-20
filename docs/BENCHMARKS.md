# Benchmarks — Laguna M.1 NVFP4 (SM121)

**Fast sanity (post-restart):** `docs/SANITY_SUITE.md` · `bash scripts/run_sanity_suite.sh`

## Throughput (publish gate)

```bash
bash scripts/capture_telemetry.sh &   # optional during bench
TEL=$!
bash scripts/bench_concurrency.sh
kill $TEL 2>/dev/null || true
python3 scripts/extract_kv_metrics.py
```

Headline JSON: `benchmarks/concurrency/chat-concurrency-summary-nvfp4-kv.json` (c1–c8).

## Accuracy — GSM8K@100 (pre-publish)

Runs **before** `build_report.py` / `finish_publish.sh` in the normal workflow.

```bash
# Requires laguna-m1-vllm on :30100
bash scripts/run_gsm8k_100.sh
```

| Env | Default | Notes |
|-----|---------|--------|
| `LIMIT` | `100` | lm-eval `--limit` |
| `NUM_FEWSHOT` | `5` | Standard GSM8K few-shot |
| `GSM8K_TASK` | `gsm8k` | Auto-fallback to `gsm8k_cot` if needed |
| `NUM_CONCURRENT` | `2` | Avoid overloading TP=2 + thinking |
| `VENV` | `.venv-lmeval` | Local lm-evaluation-harness |

**Committed artifacts**

- `benchmarks/lm_eval/gsm8k_100_results.json` — `exact_match`, stderr, task id
- `benchmarks/lm_eval/gsm8k_100_manifest.json` — repro metadata
- `benchmarks/run_meta.json` — `lm_eval.gsm8k_100` pointer

Raw lm-eval JSON: `benchmarks/lm_eval/raw/` (gitignored).

**Regression:** document baseline in `benchmarks/lm_eval/baseline_gsm8k_100.json`; >10% relative drop in `exact_match` triggers review before push.

## Agent — Hermes terminal micro (pre-publish)

`~/hermes-bench-tool-call` — category **`t01_terminal_smoke`** (5 tasks), **`--real-agent`**.

```bash
bash scripts/run_hermes_terminal_micro.sh
```

| Env | Default |
|-----|---------|
| `HERMES_BENCH_REPO` | `~/hermes-bench-tool-call` |
| `PORT` | `30100` |
| `MODEL` | `laguna-m1-nvfp4` |

**Committed:** `benchmarks/hermesbench/terminal_micro_results.json`, `terminal_micro_manifest.json`

## HumanEval micro (Hermes agent)

Default **n=10** problems — real Hermes agent + hermes-bench verifiers (`t13_humaneval_micro`).

```bash
bash scripts/run_hermes_humaneval_micro.sh
```

| Env | Default |
|-----|---------|
| `HUMANEVAL_MICRO_LIMIT` / `LIMIT` | `10` |
| `HERMES_BENCH_REPO` | `~/hermes-bench-tool-call` |

**Committed:** `benchmarks/hermesbench/humaneval_micro_results.json`, `humaneval_micro_manifest.json`

Standalone lm-eval HumanEval (`scripts/run_humaneval_micro.sh`) is **local-only** on thinking models — not part of the public HTML story.

## Report

```bash
python3 scripts/build_report.py
# publication/html/index.html
```

**Alignment check (before push):**

```bash
python3 scripts/verify_publish_alignment.py
```

## Normal publish sequence

```bash
bash scripts/bench_concurrency.sh
python3 scripts/extract_kv_metrics.py
bash scripts/run_gsm8k_100.sh
bash scripts/run_hermes_terminal_micro.sh
bash scripts/run_hermes_humaneval_micro.sh
python3 scripts/build_report.py
bash scripts/finish_publish.sh
```

BFCL and full MATH-500 are out of scope on public `main` (local only if needed).