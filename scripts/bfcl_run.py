#!/usr/bin/env python3
"""Register Laguna M.1 on local vLLM and invoke bfcl generate/evaluate."""
from __future__ import annotations

import os
import subprocess
import sys


def register_model() -> str:
    from bfcl_eval.constants.model_config import MODEL_CONFIG_MAPPING, ModelConfig
    from bfcl_eval.model_handler.api_inference.openai_completion import OpenAICompletionsHandler

    registry = os.environ.get("BFCL_MODEL_REGISTRY", "laguna-m1-nvfp4-sm121-FC")
    api_model = os.environ.get("BFCL_VLLM_MODEL", "laguna-m1-nvfp4")
    MODEL_CONFIG_MAPPING[registry] = ModelConfig(
        model_name=api_model,
        display_name="Laguna M.1 NVFP4 SM121 (FC)",
        url="https://huggingface.co/poolside/Laguna-M.1-NVFP4",
        org="poolside",
        license="apache-2.0",
        model_handler=OpenAICompletionsHandler,
        is_fc_model=True,
        underscore_to_dot=False,
    )
    return registry


def main() -> int:
    os.environ.setdefault("OPENAI_API_KEY", "EMPTY")
    base = os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:30100/v1")
    os.environ["OPENAI_BASE_URL"] = base
    root = os.environ.get("BFCL_PROJECT_ROOT")
    if not root:
        print("Set BFCL_PROJECT_ROOT", file=sys.stderr)
        return 2
    registry = register_model()
    cats = os.environ.get("BFCL_TEST_CATEGORIES", "simple_python")
    cmd = sys.argv[1:] if len(sys.argv) > 1 else ["generate"]
    if cmd == ["generate"]:
        full = [
            "bfcl",
            "generate",
            "--model",
            registry,
            "--test-category",
            cats,
            "--skip-server-setup",
            "--num-threads",
            os.environ.get("BFCL_NUM_THREADS", "1"),
        ]
    elif cmd == ["evaluate"]:
        full = ["bfcl", "evaluate", "--model", registry, "--test-category", cats]
    else:
        full = ["bfcl", *cmd]
    print("Running:", " ".join(full), file=sys.stderr)
    return subprocess.call(full)


if __name__ == "__main__":
    raise SystemExit(main())