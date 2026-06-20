"""Shared HumanEval execution helpers (stdlib-only for hermes verifiers)."""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path


def extract_python_completion(text: str) -> str:
    """Best-effort extract completion body from model output."""
    if not text:
        return ""
    blocks = re.findall(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if blocks:
        return blocks[-1].strip()
    # fallback: strip prompt-like prefix if model echoed def
    return text.strip()


def build_program(prompt: str, completion: str) -> str:
    comp = extract_python_completion(completion)
    if "def " in comp:
        return comp
    return prompt + comp


def run_humaneval_check(
    prompt: str,
    completion: str,
    test: str,
    entry_point: str,
    timeout_s: int = 15,
) -> tuple[bool, str]:
    program = build_program(prompt, completion)
    script = f"""import sys
{program}
{test}
check({entry_point})
print("OK")
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        path = f.name
    try:
        r = subprocess.run(
            [sys.executable, path],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        if r.returncode == 0 and "OK" in r.stdout:
            return True, "ok"
        err = (r.stderr or r.stdout or "").strip()[:500]
        return False, err or f"exit {r.returncode}"
    except subprocess.TimeoutExpired:
        return False, "timeout"
    finally:
        Path(path).unlink(missing_ok=True)


def text_from_trace(trace: list[dict]) -> str:
    parts = []
    for msg in trace:
        if msg.get("role") != "assistant":
            continue
        for key in ("content", "reasoning", "reasoning_content"):
            v = msg.get(key)
            if isinstance(v, str) and v.strip():
                parts.append(v)
    return "\n".join(parts)