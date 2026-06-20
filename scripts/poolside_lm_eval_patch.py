"""Patch lm-eval LocalChatCompletion to use Poolside/vLLM `reasoning` when `content` is empty."""
from __future__ import annotations

from typing import Dict, List, Union

from lm_eval.models.openai_completions import LocalChatCompletion


def _message_text(message: dict) -> str | None:
    content = message.get("content")
    if content is not None and str(content).strip():
        return str(content)
    for key in ("reasoning", "reasoning_content"):
        alt = message.get(key)
        if alt is not None and str(alt).strip():
            return str(alt)
    return content if content is not None else None


@staticmethod
def parse_generations_poolside(
    outputs: Union[Dict, List[Dict]], **kwargs
) -> List[str | None]:
    res: List[str | None] = []
    if not isinstance(outputs, list):
        outputs = [outputs]
    for out in outputs:
        tmp = [None] * len(out["choices"])
        for choice in out["choices"]:
            msg = choice.get("message") or {}
            tmp[choice["index"]] = _message_text(msg)
        res.extend(tmp)
    return res


LocalChatCompletion.parse_generations = parse_generations_poolside  # type: ignore[method-assign]