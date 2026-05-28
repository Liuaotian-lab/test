"""Problem Understanding Engine — v7.1.

AI-constrained problem understanding framework with deterministic evidence, validators and gates.
The package does not call a remote model by itself; it produces strict artifacts that can be
filled or reviewed by an external Agent, and provides a conservative heuristic fallback.
"""
from .orchestrator import understand_problem, understanding_gate, build_compat_signature

__all__ = ["understand_problem", "understanding_gate", "build_compat_signature"]
