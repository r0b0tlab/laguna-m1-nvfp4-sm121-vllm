#!/usr/bin/env python3
"""Register Laguna M.1 on local vLLM and invoke bfcl generate/evaluate in-process."""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace


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


def _categories() -> list[str]:
    raw = os.environ.get("BFCL_TEST_CATEGORIES", "simple_python")
    return [c.strip() for c in raw.split(",") if c.strip()]


def main() -> int:
    os.environ.setdefault("OPENAI_API_KEY", "EMPTY")
    base = os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:30100/v1")
    os.environ["OPENAI_BASE_URL"] = base
    if not os.environ.get("BFCL_PROJECT_ROOT"):
        print("Set BFCL_PROJECT_ROOT", file=sys.stderr)
        return 2

    from dotenv import load_dotenv
    from bfcl_eval.constants.eval_config import DOTENV_PATH
    from bfcl_eval._llm_response_generation import main as generation_main
    from bfcl_eval.eval_checker.eval_runner import main as evaluation_main

    load_dotenv(dotenv_path=DOTENV_PATH, verbose=True, override=True)
    registry = register_model()
    cats = _categories()
    cmd = sys.argv[1:] if len(sys.argv) > 1 else ["generate"]

    if cmd == ["generate"]:
        args = SimpleNamespace(
            model=[registry],
            test_category=cats,
            temperature=0.001,
            include_input_log=False,
            exclude_state_log=False,
            num_gpus=1,
            num_threads=int(os.environ.get("BFCL_NUM_THREADS", "1")),
            gpu_memory_utilization=0.9,
            backend="vllm",
            skip_server_setup=True,
            local_model_path=None,
            result_dir=None,
            allow_overwrite=os.environ.get("BFCL_ALLOW_OVERWRITE", "0") == "1",
            run_ids=False,
        )
        print("generate:", registry, cats, file=sys.stderr)
        generation_main(args)
        return 0

    if cmd == ["evaluate"]:
        print("evaluate:", registry, cats, file=sys.stderr)
        evaluation_main([registry], cats, None, None, False)
        return 0

    print("Usage: bfcl_run.py generate|evaluate", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())