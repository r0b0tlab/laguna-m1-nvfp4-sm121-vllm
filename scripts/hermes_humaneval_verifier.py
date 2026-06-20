"""HumanEval micro verifier for hermes-bench task dirs."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

LAGUNA_SCRIPTS = Path("/home/r0b0tdgx/projects/laguna-m1-nvfp4-sm121-vllm/scripts")
if LAGUNA_SCRIPTS.is_dir():
    sys.path.insert(0, str(LAGUNA_SCRIPTS))

from humaneval_runtime import run_humaneval_check, text_from_trace  # noqa: E402


@dataclass
class VerifierResult:
    status: Literal["PASS", "FAIL", "SKIPPED", "BUDGET_EXCEEDED", "VERIFIER_ERROR"]
    score: float = 1.0
    reason: str = ""
    details: dict = field(default_factory=dict)


def verify(worktree: Path, trace: list[dict]) -> VerifierResult:
    prob_path = worktree / "humaneval.json"
    if not prob_path.is_file():
        return VerifierResult(status="VERIFIER_ERROR", reason="missing humaneval.json")
    prob = json.loads(prob_path.read_text(encoding="utf-8"))
    text = text_from_trace(trace)
    ok, reason = run_humaneval_check(
        prob["prompt"], text, prob["test"], prob["entry_point"]
    )
    if ok:
        return VerifierResult(status="PASS", reason="ok")
    return VerifierResult(status="FAIL", reason=reason)