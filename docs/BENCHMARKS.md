# Benchmarks — Laguna M.1 NVFP4 (SM121)

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

## Report

```bash
python3 scripts/build_report.py
# publication/html/index.html
```

## Normal publish sequence

```bash
bash scripts/bench_concurrency.sh
python3 scripts/extract_kv_metrics.py
bash scripts/run_gsm8k_100.sh
python3 scripts/build_report.py
bash scripts/finish_publish.sh
```

BFCL and full MATH-500 are out of scope on public `main` (local only if needed).