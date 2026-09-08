"""OpenAI client construction for the Vehicle EDA harness."""

from __future__ import annotations

import os
from typing import Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"


def create_openai_client(model: str | None = None) -> tuple[Any, str]:
    """Create an OpenAI client from environment-based credentials."""
    if OpenAI is None:
        raise RuntimeError("The 'openai' package is not installed. Install it with 'pip install openai'.")

    # Set these in the terminal before running main.py:
    # export OPENAI_API_KEY="your-openai-api-key"
    # export OPENAI_MODEL="gpt-4.1-mini"
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required for the OpenAI provider. "
            "Set it in your shell environment before running the harness."
        )

    return OpenAI(api_key=api_key), model or os.environ.get(
        "OPENAI_MODEL", DEFAULT_OPENAI_MODEL
    )
