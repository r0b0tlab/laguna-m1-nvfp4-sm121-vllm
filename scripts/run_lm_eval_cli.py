#!/usr/bin/env python3
"""Run lm_eval CLI with Poolside reasoning→content patch applied in-process."""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import poolside_lm_eval_patch  # noqa: F401,E402

from lm_eval.__main__ import cli_evaluate  # noqa: E402

if __name__ == "__main__":
    cli_evaluate()