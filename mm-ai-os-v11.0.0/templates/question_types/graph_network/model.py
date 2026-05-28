from __future__ import annotations


def build_model(context: dict) -> dict:
    """Build a lightweight model specification.

    Replace this with a question-specific mathematical model.
    """
    return {
        "model_name": "generic_model",
        "variables": [],
        "constraints": [],
        "objective": None,
        "context_keys": sorted(context.keys())
    }
