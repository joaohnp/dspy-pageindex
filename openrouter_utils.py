"""OpenRouter LLM utilities."""

import os

import dspy
from dotenv import load_dotenv

load_dotenv()


def get_openrouter_lm(model: str):
    """Create and configure a DSPy LM using OpenRouter.

    Args:
        model: Model name (e.g., "openrouter/minimax/minimax-m2.5")

    Returns:
        Configured dspy.LM instance
    """
    lm = dspy.LM(
        model=model,
        api_base=os.getenv("OPEN_ROUTER_BASE_URL"),
        api_key=os.getenv("OPEN_ROUTER_API_KEY"),
        max_tokens=80000,
        cache=False,
        temperature=1.0,
        extra_headers={"streaming": "True"},
    )
    return lm


def configure_lm(model: str = "openrouter/openai/gpt-4o"):
    """Configure DSPy with an OpenRouter LM.

    Args:
        model: Model name (default: openrouter/openai/gpt-4o)
    """
    lm = get_openrouter_lm(model)
    dspy.settings.configure(lm=lm)
