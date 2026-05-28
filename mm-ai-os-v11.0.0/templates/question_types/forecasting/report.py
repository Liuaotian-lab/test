from __future__ import annotations


def _format_metrics(result: dict) -> str:
    lines = []
    if isinstance(result.get("objective_value"), (int, float)):
        lines.append(f"- objective_value: `{result.get('objective_value')}`")
    metrics = result.get("metrics") or {}
    if isinstance(metrics, dict):
        for key, value in metrics.items():
            if isinstance(value, (int, float, str)):
                lines.append(f"- metrics.{key}: `{value}`")
    return "\n".join(lines) if lines else "- objective_value: `not_provided`"


def render_report(result: dict) -> str:
    qid = result.get("question_id", "__QUESTION__")
    quality = result.get("quality_level", "unknown")
    metrics = _format_metrics(result)
    method = result.get("method") or result.get("solver_name") or "not_provided"
    return (
        f"# {qid} Solution Report\n\n"
        f"## Result Summary\n\n"
        f"- status: `{result.get('status')}`\n"
        f"- quality_level: `{quality}`\n"
        f"- method: `{method}`\n"
        f"{metrics}\n\n"
        "## Verification Notes\n\n"
        "The report was generated from the structured solver output. Before final submission, "
        "replace this section with problem-specific modeling assumptions, derivations, validation evidence, "
        "and sensitivity analysis. Numeric conclusion fields above are intentionally mirrored from solution_real.json "
        "so report-consistency-check can bind paper claims to machine-readable results.\n"
    )
