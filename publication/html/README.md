# Publication HTML template

`publication/html/index.html` is **generated** — do not hand-edit for data changes. Edit `scripts/build_report.py` and regenerate.

## Purpose

Foundational **single-page benchmark report** for SM121 NVFP4 serve repos:

- Throughput ladder (c1–c8)
- lm-eval accuracy (GSM8K@100)
- Hermes agent micros (terminal + HumanEval compare)
- Thermals, KV tables, runtime pin, reproduce block

## Design system (CSS variables in `build_report.py`)

| Token | Role |
|-------|------|
| `--bg`, `--surface` | Flat light surfaces (no page gradients) |
| `--accent` / `--accent-text` | Teal headline metrics |
| `--border` | Tables, panels, overflow scroll |

## Sections & anchors

`#throughput` `#accuracy` `#agent` `#humaneval` `#thermals` `#kv` `#runtime` `#repro`

## Inputs (JSON)

- `benchmarks/run_meta.json` — topology, image, hermes/lm_eval pointers
- `benchmarks/concurrency/chat-concurrency-summary-nvfp4-kv.json`
- `benchmarks/kv_cache_metrics.json`
- `benchmarks/lm_eval/gsm8k_100_results.json`
- `benchmarks/lm_eval/humaneval_micro_results.json`
- `benchmarks/hermesbench/*_micro_results.json`

## Regenerate

```bash
python3 scripts/build_report.py
```

## Forking for another model

1. Copy `build_report.py` section builders; keep CSS block as template.
2. Point `run_meta.json` at your concurrency + accuracy artifacts.
3. Adjust hero title/badges in `main()` f-string.
4. Visually verify: mobile overflow, table scroll, print layout.