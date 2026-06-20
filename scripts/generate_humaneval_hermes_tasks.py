#!/usr/bin/env python3
"""Install HumanEval micro tasks into hermes-bench-tool-call."""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HB = Path(__import__("os").environ.get("HERMES_BENCH_REPO", str(Path.home() / "hermes-bench-tool-call"))).expanduser()
CATEGORY = "t13_humaneval_micro"
LIMIT = int(__import__("os").environ.get("HUMANEVAL_MICRO_LIMIT", "10"))
VERIFIER_SRC = ROOT / "scripts" / "hermes_humaneval_verifier.py"

TASK_YAML = """id: {task_id}
name: \"HumanEval {he_id}\"
version: 1
difficulty: 2
tags: [humaneval, coding, execute_code]

prompt: |
  Complete this Python function. You may use `execute_code` or `terminal` to test.
  Reply with the full solution in a ```python code block when finished.

  ```python
{prompt_indented}
  ```

allowed_tools:
  - execute_code
  - terminal

forbidden_tools: []

max_turns: 12
max_tokens: 4096
timeout_seconds: 180
isolated_network: true

fixture:
  source: {fixture_source}
  globs: [\"**/*\"]

sampling:
  temperature: 0.0
  top_p: 1.0
  top_k: -1
  seed: 42

resource_limits:
  max_memory_mb: 2048
  max_processes: 128
  max_file_size_mb: 100
  max_worktree_mb: 500

hermes_plugins: []

latency_injection_ms:
  terminal: 0
  read_file: 0
  patch: 0

model_endpoint:
  type: openai_chat_completions
  required_fields: [tools, tool_choice]
  forbidden_fields: [logprobs]

verifier:
  module: verifier
  fn: verify
  timeout_seconds: 30
"""


def _slug(he_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", he_id).strip("_").lower()


def main() -> int:
    try:
        from datasets import load_dataset
    except ImportError:
        print("pip install datasets", file=sys.stderr)
        return 1

    ds = load_dataset("openai/openai_humaneval", split="test")
    n = min(LIMIT, len(ds))
    cat_root = HB / "tasks" / CATEGORY
    fix_root = HB / "fixtures" / "humaneval_micro"
    cat_root.mkdir(parents=True, exist_ok=True)
    fix_root.mkdir(parents=True, exist_ok=True)

    manifest = []
    for i in range(n):
        row = ds[i]
        he_id = row["task_id"]
        slug = _slug(he_id)
        task_id = f"{CATEGORY}/{slug}"
        fixture_source = f"humaneval_micro/{slug}"
        fix_dir = fix_root / slug
        fix_dir.mkdir(parents=True, exist_ok=True)
        (fix_dir / "humaneval.json").write_text(
            json.dumps(
                {
                    "task_id": he_id,
                    "prompt": row["prompt"],
                    "test": row["test"],
                    "entry_point": row["entry_point"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        task_dir = cat_root / slug
        task_dir.mkdir(parents=True, exist_ok=True)
        prompt_indented = "\n".join("  " + ln for ln in row["prompt"].splitlines())
        (task_dir / "task.yaml").write_text(
            TASK_YAML.format(
                task_id=task_id,
                he_id=he_id,
                prompt_indented=prompt_indented,
                fixture_source=fixture_source,
            ),
            encoding="utf-8",
        )
        shutil.copy2(VERIFIER_SRC, task_dir / "verifier.py")
        manifest.append({"task_id": task_id, "he_id": he_id})

    out = ROOT / "benchmarks" / "hermesbench" / "humaneval_micro_task_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"category": CATEGORY, "tasks": manifest}, indent=2) + "\n")
    print(f"Installed {n} tasks under {cat_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())